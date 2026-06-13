import os
import asyncio
from typing import Dict, List, Optional
from dataclasses import dataclass
from web3 import Web3


@dataclass
class Wallet:
    address: str
    private_key: str
    name: str
    balance: float = 0.0
    active: bool = True


class MultiWalletManager:
    def __init__(self, rpc_url: str = "https://polygon-rpc.com"):
        self.wallets: Dict[str, Wallet] = {}
        self.web3 = Web3(Web3.HTTPProvider(rpc_url))
        self._load_wallets()

    def _load_wallets(self):
        wallets_config = os.getenv('WALLETS', '')
        if not wallets_config:
            return
        
        for i, wallet_data in enumerate(wallets_config.split(';')):
            if wallet_data:
                parts = wallet_data.split(',')
                if len(parts) >= 2:
                    name = parts[0] if len(parts) >= 3 else f"Wallet_{i+1}"
                    address = parts[-2]
                    private_key = parts[-1]
                    self.wallets[address] = Wallet(
                        address=address,
                        private_key=private_key,
                        name=name
                    )

    def add_wallet(self, name: str, address: str, private_key: str) -> bool:
        if not self.web3.is_address(address):
            return False
        self.wallets[address] = Wallet(
            address=address,
            private_key=private_key,
            name=name
        )
        return True

    def remove_wallet(self, address: str) -> bool:
        if address in self.wallets:
            del self.wallets[address]
            return True
        return False

    async def get_balances(self) -> Dict[str, float]:
        balances = {}
        for address in self.wallets:
            try:
                balance = self.web3.eth.get_balance(address)
                balances[address] = self.web3.from_wei(balance, 'ether')
            except:
                balances[address] = 0.0
        return balances

    async def distribute_funds(self, from_wallet: str, amount: float) -> Dict[str, str]:
        if from_wallet not in self.wallets:
            return {"error": "Source wallet not found"}
        
        sender = self.wallets[from_wallet]
        per_wallet = amount / (len(self.wallets) - 1)
        
        results = {}
        for address, wallet in self.wallets.items():
            if address != from_wallet and wallet.active:
                try:
                    tx = {
                        'to': address,
                        'value': self.web3.to_wei(per_wallet, 'ether'),
                        'gas': 21000,
                        'gasPrice': self.web3.eth.gas_price,
                        'nonce': self.web3.eth.get_transaction_count(sender.address)
                    }
                    signed = self.web3.eth.account.sign_transaction(tx, sender.private_key)
                    tx_hash = self.web3.eth.send_raw_transaction(signed.raw_transaction)
                    results[address] = self.web3.to_hex(tx_hash)
                except Exception as e:
                    results[address] = f"Error: {str(e)}"
        
        return results

    def get_wallet(self, address: str) -> Optional[Wallet]:
        return self.wallets.get(address)

    def list_wallets(self) -> List[dict]:
        return [
            {
                "address": w.address,
                "name": w.name,
                "balance": w.balance,
                "active": w.active
            }
            for w in self.wallets.values()
        ]

    def set_active(self, address: str, active: bool) -> bool:
        if address in self.wallets:
            self.wallets[address].active = active
            return True
        return False