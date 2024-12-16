# src/analysis/contracts_analyzer.py

"""
Contracts Analyzer Module.

This module provides functionality to analyze smart contracts by fetching transaction data,
infer taxes (buy, sell, transfer), and detect operational limits.
"""

import os
from typing import Dict, Union
import requests
from web3 import Web3
from dotenv import load_dotenv


class ContractCannotBeAnalyzed(Exception):
    """
    Exception raised while analyzing contract gets an error.
    """

    def __init__(self):
        self.message = (
            "Can't analyze contract"
        )
        super().__init__(self.message)


class ContractsAnalyzer:
    """
    A class to analyze Ethereum smart contracts for taxes and operational limits.
    """

    def __init__(self, web3_provider: str):
        """
        Initializes the ContractsAnalyzer class with a Web3 provider.

        :param web3_provider: URL of the Web3 provider (e.g., Infura or Alchemy).
        """
        self.web3 = Web3(Web3.HTTPProvider(web3_provider))
        load_dotenv()
        self.etherscan_api_key = os.getenv("ETHERSCAN_API_KEY")
        if not self.etherscan_api_key:
            raise ValueError("Etherscan API key not found in environment variables.")

    def analyze_contract(self, abi: Dict, contract_address: str) -> (
            Dict)[str, Union[str, bool, float]]:
        """
        Analyzes a contract for taxes, gas usage, and operational limits.

        :param abi: The ABI of the smart contract.
        :param contract_address: The Ethereum address of the contract.
        :return: A dictionary containing analysis results.
        """
        contract = self.web3.eth.contract(address=contract_address, abi=abi)
        try:
            buy_tax = self.infer_tax(contract_address, action="buy")
            sell_tax = self.infer_tax(contract_address, action="sell")
            transfer_tax = self.infer_tax(contract_address, action="transfer")
            gas_metrics = self.calculate_gas_metrics(contract_address)
            return {
                "buy_tax": buy_tax,
                "sell_tax": sell_tax,
                "transfer_tax": transfer_tax,
                "average_gas": gas_metrics["average_gas"],
                "buy_gas": gas_metrics["buy_gas"],
                "sell_gas": gas_metrics["sell_gas"],
                "limits_detected": self.detect_limits(contract),
            }
        except Exception as error:
            raise ValueError("Error analyzing contract") from error

    def infer_tax(self, contract_address: str, action: str) -> Union[str, float]:
        """
        Infer taxes (buy, sell, transfer) based on transaction data from Etherscan.

        :param contract_address: Address of the token contract.
        :param action: Type of action ('buy', 'sell', 'transfer').
        :return: Estimated tax percentage or an error message.
        """
        try:
            url = (
                f"https://api.etherscan.io/api?module=account&"
                f"action=tokentx&contractaddress={contract_address}" 
                f"&page=1&offset=100&sort=desc&apikey={self.etherscan_api_key}"
            )
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                result = response.json()
                if result["status"] == "1":
                    transactions = result["result"]

                    total_tax = 0
                    tax_count = 0

                    for tx in transactions:
                        gas_price = int(tx["gasPrice"])
                        gas_used = int(tx["gasUsed"])

                        # Skip irrelevant or unrealistic transactions
                        if (int(tx["value"]) <= 0 or int(tx["value"]) <
                                self.web3.to_wei(0.0001, 'ether')):
                            continue

                        # Tax estimation logic based on transaction type
                        if action == "buy" and tx["to"] != contract_address:
                            total_tax += (gas_price * gas_used) / int(tx["value"])
                            tax_count += 1
                        elif action == "sell" and tx["from"] != contract_address:
                            total_tax += (gas_price * gas_used) / int(tx["value"])
                            tax_count += 1
                        elif (action == "transfer" and tx["from"] != contract_address and
                              tx["to"] != contract_address):
                            total_tax += (gas_price * gas_used) / int(tx["value"])
                            tax_count += 1

                    if tax_count > 0:
                        # Cap maximum tax to prevent unrealistic results
                        average_tax = min(round(total_tax / tax_count * 100, 2), 100)
                        return average_tax
                    return "0%"  # Explicitly return 0% if no tax-like transactions are found
                return f"Etherscan API error: {result.get('message', 'Unknown error')}"
            return f"HTTP error: {response.status_code}"
        except Exception as error:
            raise ContractCannotBeAnalyzed() from error

    def calculate_gas_metrics(self, contract_address: str) -> Dict[str, float]:
        """
        Calculate gas metrics for buy and sell transactions.

        :param contract_address: Address of the token contract.
        :return: A dictionary containing total buy/sell gas and average gas usage.
        """
        try:
            total_gas = 0
            total_buy_gas = 0
            total_sell_gas = 0
            gas_count = 0

            for page in range(1, 4):
                url = (
                    f"https://api.etherscan.io/api?module=account&"
                    f"action=tokentx&contractaddress={contract_address}"
                    f"&page={page}&offset=100&sort=desc&apikey={self.etherscan_api_key}"
                )
                response = requests.get(url, timeout=10)
                if response.status_code != 200:
                    break

                result = response.json()
                if result["status"] != "1":
                    break

                transactions = result["result"]

                for tx in transactions:
                    if int(tx["value"]) <= 0:
                        continue

                    total_gas += int(tx["gasUsed"])
                    gas_count += 1

                    if tx["to"].lower() == contract_address.lower():
                        total_buy_gas += int(tx["gasUsed"])
                    elif tx["from"].lower() == contract_address.lower():
                        total_sell_gas += int(tx["gasUsed"])

            average_gas = total_gas / gas_count if gas_count > 0 else 0
            return {
                "average_gas": average_gas,
                "buy_gas": total_buy_gas,
                "sell_gas": total_sell_gas,
            }
        except Exception as error:
            raise ContractCannotBeAnalyzed() from error

    def detect_limits(self, contract: Web3().eth.contract) -> bool:
        """
        Detect operational limits by calling contract methods or analyzing behavior.

        :param contract: The smart contract instance.
        :return: True if limits are detected, False otherwise.
        """
        try:
            if hasattr(contract.functions, 'maxTxAmount'):
                max_tx_amount = contract.functions.maxTxAmount().call()
                return max_tx_amount < self.web3.to_wei(1, 'ether')  # Example threshold
            return False
        except Exception as error:
            raise ContractCannotBeAnalyzed() from error
