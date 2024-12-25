# src/honeypot_checker.py

"""
HoneyPot Checker module.

This is the main module of the project.
Gets all the data from other scripts and basically combine it.
"""

import json
import os
from typing import Union, Any
from dotenv import load_dotenv
from helpers.etherscan_api import EtherscanAPI
from analysis.contracts_analyzer import ContractsAnalyzer
from analysis.wallet_analyzer import WalletAnalyzer
from utils import validate_address
from config import logger

load_dotenv()


class TokenCannotBeAnalyzed(Exception):
    """
    Exception raised when a token address can't be analyzed.
    """

    def __init__(self):
        self.message = (
            "Token address can't be analyzed"
        )
        super().__init__(self.message)


class HoneypotChecker:
    """
    Main class for checking if token is honeypot.
    """
    def __init__(self):
        self.etherscan = EtherscanAPI()
        self.contracts_analyzer = ContractsAnalyzer(web3_provider=os.getenv("WEB3_PROVIDER_URL"))
        self.wallet_analyzer = WalletAnalyzer()

    def analyze_address(self, address: str) -> dict:
        """
        Combine all the data and give response on token.

        :param address: token address.
        :return: result in dict.
        """
        if not validate_address(address):
            return {"error": "Invalid Ethereum address"}

        try:
            results = self.analyze_from_outer_scope(address)

            return {
                "token_address": address,
                "source_code_status": "open_source" if results[0] else "not_verified",
                **results[1],
                **results[2]
            }
        except ValueError as e:
            logger.fatal("Token cannot be analyzed: %s", e)
            return None

    def analyze_from_outer_scope(self, address: str) -> (
            tuple)[bool, dict[str, Union[str, bool]], Any]:
        """
        Getting all the data on address from outer scope.

        :param address: token address.
        :return: result variables.
        """
        is_verified = self.etherscan.is_contract_verified(address)

        abi = self.etherscan.get_contract_abi(address)
        contract_analysis = self.contracts_analyzer.analyze_contract(abi, address)

        wallet_analysis = self.wallet_analyzer.analyze_holders(address)

        return is_verified, contract_analysis, wallet_analysis


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        logger.info("Usage: python honeypot_checker.py <ethereum_address>")
        sys.exit(1)

    try:
        checker = HoneypotChecker()
        analysis = checker.analyze_address(sys.argv[1])
        logger.info(json.dumps(analysis, indent=4))
    except ValueError as e:
        logger.fatal("Can't analyze this coin: %s", e)
        sys.exit(1)
