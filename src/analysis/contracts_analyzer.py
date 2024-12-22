# src/contracts_analyzer.py

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
        self.message = "Can't analyze contract"
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
            Dict[str, Union[str, bool, float]]):
        """
        Analyzes a contract for taxes, gas usage, and operational limits.

        :param abi: The ABI of the smart contract.
        :param contract_address: The Ethereum address of the contract.
        :return: A dictionary containing analysis results.
        """
        try:
            contract = self.web3.eth.contract(address=contract_address, abi=abi)

            buy_tax = self.infer_tax(contract_address, action="buy")
            print(f"Buy tax for {contract_address}: {buy_tax}")

            sell_tax = self.infer_tax(contract_address, action="sell")
            print(f"Sell tax for {contract_address}: {sell_tax}")

            transfer_tax = self.infer_tax(contract_address, action="transfer")
            print(f"Transfer tax for {contract_address}: {transfer_tax}")

            gas_metrics = self.calculate_gas_metrics(contract_address)
            print(f"Gas metrics for {contract_address}: {gas_metrics}")

            limits_detected = self.detect_limits(contract)
            print(f"Limits detected for {contract_address}: {limits_detected}")

            return {
                "buy_tax": buy_tax,
                "sell_tax": sell_tax,
                "transfer_tax": transfer_tax,
                "average_gas": gas_metrics["average_gas"],
                "buy_gas": gas_metrics["buy_gas"],
                "sell_gas": gas_metrics["sell_gas"],
                "limits_detected": limits_detected,
            }
        except Exception as error:
            print(f"Error analyzing contract {contract_address}: {error}")
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
                f"&page=1&offset=1000&sort=desc&apikey={self.etherscan_api_key}"
            )
            response = requests.get(url, timeout=60)
            if response.status_code == 200:
                result = response.json()
                if result["status"] == "1":
                    transactions = result["result"]

                    total_tax = 0
                    tax_count = 0

                    for tx in transactions:
                        gas_price = int(tx["gasPrice"])
                        gas_used = int(tx["gasUsed"])

                        if int(tx["value"]) <= 0:
                            continue

                        tax_value = (gas_price * gas_used) / int(tx["value"])

                        if tax_value > 1:
                            continue

                        if action == "buy" and tx["to"] != contract_address:
                            total_tax += tax_value
                            tax_count += 1
                        elif action == "sell" and tx["from"] != contract_address:
                            total_tax += tax_value
                            tax_count += 1
                        elif (action == "transfer" and tx["from"] != contract_address
                              and tx["to"] != contract_address):
                            total_tax += tax_value
                            tax_count += 1

                    if tax_count > 0:
                        return round(total_tax / tax_count * 100, 2)
                    return 0.0
                return "No relevant transactions found"
            print(f"HTTP error for tax inference: {response.status_code}")
            return f"HTTP error: {response.status_code}"
        except Exception as error:
            print(f"Error inferring tax for {contract_address}: {error}")
            raise ValueError("Error inferring taxes") from error

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
                    f"&page={page}&offset=1000&sort=desc&apikey={self.etherscan_api_key}"
                )
                response = requests.get(url, timeout=60)
                if response.status_code != 200:
                    break

                result = response.json()
                if result["status"] != "1":
                    break

                transactions = result["result"]

                for tx in transactions:
                    if int(tx["value"]) <= 0:
                        continue
                    print()

                    gas_used = int(tx["gasUsed"])
                    total_gas += gas_used
                    gas_count += 1

                    if (tx.get("contractAddress", "").lower() ==
                            contract_address.lower() and tx["from"]):
                        total_buy_gas += gas_used

                    if (tx.get("contractAddress", "").lower() ==
                            contract_address.lower() and tx["to"]):
                        total_sell_gas += gas_used

            average_gas = total_gas / gas_count if gas_count > 0 else 0
            print(f"Calculated Gas Metrics for {contract_address}: {{'average_gas': {average_gas},"
                  f" 'buy_gas': {total_buy_gas}, 'sell_gas': {total_sell_gas}}}")
            return {
                "average_gas": average_gas,
                "buy_gas": total_buy_gas,
                "sell_gas": total_sell_gas,
            }
        except Exception as error:
            print(f"Error calculating gas metrics for {contract_address}: {error}")
            raise ValueError("Error calculating gas metrics") from error

    def detect_limits(self, contract: Web3().eth.contract) -> bool:
        """
        Detect operational limits by calling contract methods or analyzing behavior.

        :param contract: The smart contract instance.
        :return: True if limits are detected, False otherwise.
        """
        try:
            if hasattr(contract.functions, 'maxTxAmount'):
                max_tx_amount = contract.functions.maxTxAmount().call()
                return max_tx_amount < self.web3.to_wei(1, 'ether')
            return False
        except Exception as error:
            print(f"Error detecting limits for contract {contract.address}: {error}")
            raise ValueError("Error detecting limits") from error
