# src/utils.py

"""
Utils module
"""

from eth_utils import is_address


def validate_address(address):
    """
    Validating address.

    :param address: token address.
    """
    return is_address(address)
