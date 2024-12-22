# src/wallet_analyzer.py

"""
Wallet Analyzer module.

This module analyzes wallets for total holders and suspicious holders.
"""

import os
from collections import defaultdict
from typing import Dict, Union
import requests
from dotenv import load_dotenv


class WalletAnalyzer:
    """
    Main class for analyzing given wallets.
    """

    def __init__(self):
        load_dotenv()
        self.etherscan_api_key = os.getenv("ETHERSCAN_API_KEY")
        if not self.etherscan_api_key:
            raise ValueError("Etherscan API key not found in environment variables")

    def analyze_holders(self, token_address: str) -> Dict[str, Union[int, bool]]:
        """
        Analyze wallet holders of the given token for suspicious behavior.

        :param token_address: The Ethereum address of the token.
        :return: A dictionary with analysis results.
        """
        try:
            holders_data = self.get_token_holders(token_address)
            holders_count = len(holders_data)
            total_supply = sum(data["balance"] for data in holders_data.values())

            suspicious_wallets = self.detect_suspicious_wallets(holders_data, total_supply)
            suspicious_ratio = len(suspicious_wallets) / holders_count if holders_count > 0 else 0

            suspicious_threshold = 0.15  # >15% suspicious wallets is concerning
            low_holder_threshold = 100  # Tokens with <100 holders are suspicious
            high_concentration_threshold = 0.7  # Concentration >70% among suspicious wallets

            concentration_score = sum(
                data["balance"] for address, data in holders_data.items()
                if address in suspicious_wallets
            ) / total_supply if total_supply > 0 else 0

            print(f"Token Address: {token_address}")
            print(f"Holders Count: {holders_count}")
            print(f"Suspicious Ratio: {suspicious_ratio}")
            print(f"Concentration Score: {concentration_score}")
            print(f"Suspicious Wallets: {len(suspicious_wallets)}")

            # Honeypot-specific flags
            is_whitelisted = token_address in [
                "0xdAC17F958D2ee523a2206206994597C13D831ec7",  # USDT
                "0xA0b86991C6218b36c1d19D4a2e9Eb0cE3606eb48"   # USDC
            ]

            if is_whitelisted:
                is_honeypot = False
            elif (
                    holders_count < low_holder_threshold or
                    suspicious_ratio > suspicious_threshold or
                    concentration_score > high_concentration_threshold
            ):
                is_honeypot = True
            else:
                is_honeypot = False

            print(f"Is Honeypot: {is_honeypot}")

            return {
                "holders_analyzed": holders_count,
                "siphoned_wallets": len(suspicious_wallets),
                "is_honeypot": is_honeypot
            }
        except Exception as e:
            print(f"Error analyzing wallets for {token_address}: {e}")
            raise ValueError("Error analyzing wallets") from e

    def get_token_holders(self, token_address):
        """
        Fetch token holders using the Etherscan API.

        :param token_address: The Ethereum address of the token.
        :return: A dictionary of holder addresses with their balances and transaction details.
        """
        page = 1
        holder_data = defaultdict(lambda: {"balance": 0, "incoming": 0, "outgoing": 0})

        while True:
            url = (f"https://api.etherscan.io/api?module=account&"
                   f"action=tokentx&contractaddress={token_address}"
                   f"&page={page}&offset=10000&sort=asc&apikey={self.etherscan_api_key}")
            response = requests.get(url, timeout=60)

            if response.status_code == 200:
                result = response.json()
                if result["status"] != "1" or not result["result"]:
                    break

                transactions = result["result"]

                for tx in transactions:
                    to_address = tx["to"].lower()
                    from_address = tx["from"].lower()
                    value = int(tx["value"])

                    holder_data[to_address]["balance"] += value
                    holder_data[to_address]["incoming"] += 1

                    holder_data[from_address]["balance"] -= value
                    holder_data[from_address]["outgoing"] += 1

                page += 1
            else:
                print(f"Error fetching holders for {token_address}: HTTP {response.status_code}")
                raise ConnectionError(f"Failed to fetch holders: HTTP {response.status_code}")

        # Remove addresses with zero balance
        return {k: v for k, v in holder_data.items() if v["balance"] > 0}

    @staticmethod
    def detect_suspicious_wallets(holders_data, total_supply):
        """
        Identify suspicious wallets based on stricter criteria.

        :param holders_data: data about analyzed wallets.
        :param total_supply: total supply of all analyzed wallets.
        :return: list of suspicious wallets.
        """
        suspicious_wallets = []

        small_wallet_threshold = total_supply * 0.001  # 0.1% of total supply
        high_balance_threshold = total_supply * 0.05  # 5% of total supply

        for address, data in holders_data.items():
            balance = data["balance"]
            incoming = data["incoming"]
            outgoing = data["outgoing"]

            if (
                    balance > high_balance_threshold or
                    (incoming > 5 and outgoing == 0 and balance > small_wallet_threshold)
            ):
                suspicious_wallets.append(address)

        return suspicious_wallets
