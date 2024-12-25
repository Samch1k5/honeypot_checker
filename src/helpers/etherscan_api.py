# src/helpers/etherscan_api.py

"""
Etherscan API Helper Module.

This module provides functionality to interact with the Etherscan API,
including fetching contract ABI and checking contract verification status.
"""

import json
import os
from typing import Dict
import requests
from dotenv import load_dotenv
from config import logger


class ContractNotVerifiedError(Exception):
    """
    Exception raised when a contract's source code is not verified on Etherscan.
    """

    def __init__(self, contract_address: str):
        self.contract_address = contract_address
        self.message = (
            f"Contract source code not verified for address {contract_address}"
        )
        super().__init__(self.message)


class EtherscanAPI:
    """
    A class to interact with the Etherscan API for fetching contract details.
    """
    BASE_URL = "https://api.etherscan.io/api"

    def __init__(self):
        """
        Initializes the EtherscanAPI class and loads the API key from environment variables.
        """
        load_dotenv()
        self.etherscan_api_key = os.getenv('ETHERSCAN_API_KEY')
        if not self.etherscan_api_key:
            logger.fatal("Etherscan API key not found in environment variables.")

    def get_contract_abi(self, contract_address: str) -> Dict:
        """
        Fetches the ABI for a given contract address from Etherscan.

        :param contract_address: The Ethereum address of the contract.
        :return: A dictionary containing the contract's ABI.
        """
        url = (
            f"{self.BASE_URL}?module=contract&action=getabi&address="
            f"{contract_address}&apikey={self.etherscan_api_key}"
        )
        try:
            response = requests.get(url, timeout=60)
            if response.status_code == 200:
                result = response.json()
                if result["status"] == "1":
                    return json.loads(result["result"])
                logger.fatal("Contract source code not verified for address %s",
                             contract_address)
                return {
                    "error": True,
                    "message": ("Contract source code not verified for address %s",
                                contract_address)
                }
            logger.fatal("Failed to fetch ABI: HTTP %s",
                         response.status_code)
            return {
                "error": True,
                "message": ("Contract source code not verified for address %s",
                            contract_address)
            }
        except requests.exceptions.ProxyError as e:
            logger.fatal("Failed to fetch ABI: %s",
                         e)
            return {
                "error": True,
                "message": ("Contract source code not verified for address %s",
                            contract_address)
            }

    def is_contract_verified(self, contract_address: str) -> bool:
        """
        Checks if a contract is verified on Etherscan.

        :param contract_address: The Ethereum address of the contract.
        :return: True if the contract is verified, False otherwise.
        """
        try:
            self.get_contract_abi(contract_address)
            return True
        except ContractNotVerifiedError:
            return False
