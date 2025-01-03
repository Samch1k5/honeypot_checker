# src/contracts_analyzer.py

import os
import time
import secrets
import requests
from typing import Dict, Union
from dotenv import load_dotenv
from eth_account import Account
from web3 import Web3
from web3.exceptions import ContractLogicError
from eth_abi import decode

from config import logger

# Константы
UNISWAP_V2_ROUTER_ADDRESS = "0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D"  # Uniswap V2 Router (Ethereum Mainnet)
WETH_ADDRESS = "0xC02aaa39b223FE8D0A0e5C4F27ead9083C756Cc2"         # WETH (Ethereum Mainnet)

UNISWAP_V2_ROUTER_ABI = [
    {
        "name": "swapExactETHForTokens",
        "type": "function",
        "inputs": [
            {"type": "uint256", "name": "amountOutMin"},
            {"type": "address[]", "name": "path"},
            {"type": "address", "name": "to"},
            {"type": "uint256", "name": "deadline"}
        ],
        "outputs": [
            {"type": "uint256[]", "name": "amounts"}
        ],
        "stateMutability": "payable"
    },
    {
        "name": "swapExactTokensForETH",
        "type": "function",
        "inputs": [
            {"type": "uint256", "name": "amountIn"},
            {"type": "uint256", "name": "amountOutMin"},
            {"type": "address[]", "name": "path"},
            {"type": "address", "name": "to"},
            {"type": "uint256", "name": "deadline"}
        ],
        "outputs": [
            {"type": "uint256[]", "name": "amounts"}
        ],
        "stateMutability": "nonpayable"
    }
]

# Мини-ABI для обычного ERC-20 transfer
ERC20_ABI = [
    {
        "constant": False,
        "inputs": [
            {"name": "_to", "type": "address"},
            {"name": "_value", "type": "uint256"}
        ],
        "name": "transfer",
        "outputs": [{"name": "success", "type": "bool"}],
        "type": "function"
    }
]

class ContractCannotBeAnalyzed(Exception):
    def __init__(self):
        super().__init__("Can't analyze contract")


class ContractsAnalyzer:
    def __init__(self, web3_provider: str):
        self.web3 = Web3(Web3.HTTPProvider(web3_provider))
        load_dotenv()
        self.etherscan_api_key = os.getenv("ETHERSCAN_API_KEY")
        if not self.etherscan_api_key:
            logger.fatal("Etherscan API key not found in environment variables.")

        # Инициализируем Uniswap V2 Router
        self.uniswap_router = self.web3.eth.contract(
            address=self.web3.to_checksum_address(UNISWAP_V2_ROUTER_ADDRESS),
            abi=UNISWAP_V2_ROUTER_ABI
        )

    def analyze_contract(self, abi: Dict, contract_address: str) -> Dict[str, Union[str, bool, float]]:
        """
        Пример "анализатора": возвращаем гипотетический buy_tax, sell_tax, transfer_tax.
        Условно делаем через self.infer_tax(...).
        """
        buy_tax = self.infer_tax(contract_address, "buy")
        sell_tax = self.infer_tax(contract_address, "sell")
        transfer_tax = self.infer_tax(contract_address, "transfer")

        return {
            "buy_tax": buy_tax,
            "sell_tax": sell_tax,
            "transfer_tax": transfer_tax
        }

    def infer_tax(self, contract_address: str, action: str) -> Union[str, float]:
        """
        Пробуем "симулировать" налог для: buy, sell, transfer.
        """

        if action == "buy":
            tokens_got = self.simulate_uniswap_buy(contract_address, self.web3.to_wei(0.01, 'ether'))
            return tokens_got

        elif action == "sell":
            eth_got = self.simulate_uniswap_sell(contract_address, 10 * (10 ** 18))
            return eth_got

        elif action == "transfer":
            success = self.simulate_basic_transfer(contract_address, 10 * (10 ** 18))
            return 0.0 if success else "transfer revert"

        return 0.0

    def simulate_uniswap_buy(self, token_address: str, eth_amount_wei: int) -> float:
        """
        «Симулируем» покупку токена через swapExactETHForTokens на Uniswap V2 Router (eth_call).
        Возвращаем количество купленных токенов (uint256) в float.
        """
        buyer_priv_key = "0x" + secrets.token_hex(32)
        buyer_account = Account.from_key(buyer_priv_key)
        buyer_address = buyer_account.address

        path = [
            self.web3.to_checksum_address(WETH_ADDRESS),
            self.web3.to_checksum_address(token_address)
        ]
        deadline = int(time.time()) + 300

        built_tx = self.uniswap_router.functions.swapExactETHForTokens(
            0,
            path,
            buyer_address,
            deadline
        ).buildTransaction({
            "from": buyer_address,
            "value": eth_amount_wei,
        })

        call_tx = {
            "to": UNISWAP_V2_ROUTER_ADDRESS,
            "from": buyer_address,
            "data": built_tx["data"],
            "value": eth_amount_wei,
            "gas": 500000,
            "gasPrice": 0
        }

        try:
            result = self.web3.eth.call(call_tx)
            return_values = decode(["uint256[]"], result)
            amounts_list = return_values[0]
            if len(amounts_list) < 2:
                return 0.0
            return float(amounts_list[-1])
        except ContractLogicError as e:
            logger.warning("Swap simulation revert (buy): %s", e)
            return 0.0
        except Exception as e:
            logger.warning("Swap simulation error (buy): %s", e)
            return 0.0

    def simulate_uniswap_sell(self, token_address: str, token_amount_wei: int) -> float:
        """
        «Симулируем» продажу токена через swapExactTokensForETH (eth_call).
        Возвращаем, сколько ETH получится. Аналогично - нужно 'approve' на Router.
        """
        seller_priv_key = "0x" + secrets.token_hex(32)
        seller_account = Account.from_key(seller_priv_key)
        seller_address = seller_account.address

        token_contract = self.web3.eth.contract(
            address=self.web3.to_checksum_address(token_address),
            abi=ERC20_ABI
        )

        try:
            approve_tx = token_contract.functions.transfer(
                self.web3.to_checksum_address(seller_address),
                0
            ).buildTransaction({"from": seller_address})
            call_tx_approve = {
                "to": token_address,
                "from": seller_address,
                "data": approve_tx["data"],
                "value": 0,
                "gas": 300000,
                "gasPrice": 0
            }
            self.web3.eth.call(call_tx_approve)
        except ContractLogicError as e:
            logger.warning("Approve simulation revert (sell): %s", e)
            return 0.0
        except Exception as e:
            logger.warning("Approve simulation error (sell): %s", e)
            return 0.0

        path = [
            self.web3.to_checksum_address(token_address),
            self.web3.to_checksum_address(WETH_ADDRESS)
        ]
        deadline = int(time.time()) + 300

        built_tx = self.uniswap_router.functions.swapExactTokensForETH(
            token_amount_wei,
            0,
            path,
            seller_address,
            deadline
        ).buildTransaction({
            "from": seller_address
        })

        call_tx_swap = {
            "to": UNISWAP_V2_ROUTER_ADDRESS,
            "from": seller_address,
            "data": built_tx["data"],
            "value": 0,
            "gas": 700000,
            "gasPrice": 0
        }

        try:
            result = self.web3.eth.call(call_tx_swap)
            return_values = decode(["uint256[]"], result)
            amounts_list = return_values[0]
            if len(amounts_list) < 2:
                return 0.0
            eth_out = amounts_list[-1]
            return float(eth_out)
        except ContractLogicError as e:
            logger.warning("Swap simulation revert (sell): %s", e)
            return 0.0
        except Exception as e:
            logger.warning("Swap simulation error (sell): %s", e)
            return 0.0

    def simulate_basic_transfer(self, token_address: str, token_amount_wei: int) -> bool:
        """
        Псевдо-симуляция обычного transfer(...) у стандартного ERC-20.
        Возвращаем True, если не было revert, иначе False.
        """
        priv_key = "0x" + secrets.token_hex(32)
        acc = Account.from_key(priv_key)
        from_address = acc.address

        token_contract = self.web3.eth.contract(
            address=self.web3.to_checksum_address(token_address),
            abi=ERC20_ABI
        )

        built_tx = token_contract.functions.transfer(
            self.web3.to_checksum_address("0x1111111111111111111111111111111111111111"),
            token_amount_wei
        ).buildTransaction({"from": from_address})

        call_tx = {
            "to": token_address,
            "from": from_address,
            "data": built_tx["data"],
            "value": 0,
            "gas": 300000,
            "gasPrice": 0
        }
        try:
            self.web3.eth.call(call_tx)
            return True
        except ContractLogicError as e:
            logger.warning("Transfer revert: %s", e)
            return False
        except Exception as e:
            logger.warning("Transfer error: %s", e)
            return False
