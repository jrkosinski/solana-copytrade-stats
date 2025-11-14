#!/usr/bin/env python3
"""
Token Inflow Tracker - Find how and when tokens entered a wallet

This utility tracks:
- Token transfers IN (received from other wallets)
- Token swaps that bought the token
- The source and timing of token acquisitions
"""

import requests
import os
from datetime import datetime
from typing import Dict, List
import json


class TokenInflowTracker:
    """Track how tokens entered a wallet"""

    def __init__(self, wallet: str, helius_api_key: str = None):
        self.wallet = wallet
        self.helius_api_key = helius_api_key or os.getenv('HELIUS_API_KEY')
        self.helius_url = "https://api.helius.xyz/v0"

    def track_token_inflows(self, limit: int = 1000) -> Dict[str, List[Dict]]:
        """
        Track all token inflows to the wallet

        Args:
            limit: Maximum number of transactions to check

        Returns:
            Dictionary mapping token addresses to list of inflow events
        """
        print(f"🔍 Tracking token inflows for {self.wallet[:8]}...{self.wallet[-6:]}")
        print(f"   Checking up to {limit} transactions...\n")

        url = f"{self.helius_url}/addresses/{self.wallet}/transactions"

        # Track inflows by token
        token_inflows = {}
        tx_count = 0
        before = ''

        # Fetch ALL transaction types (not just SWAP)
        while tx_count < limit:
            params = {
                'api-key': self.helius_api_key,
                'before': before
                # NO type filter - we want to see ALL transactions
            }

            try:
                response = requests.get(url, params=params)
                data = response.json()

                if len(data) == 0:
                    break

                for tx in data:
                    tx_count += 1

                    if tx_count % 100 == 0:
                        print(f"   Processed {tx_count} transactions...")

                    if isinstance(tx, str):
                        continue

                    # Get transaction details
                    sig = tx.get('signature', 'N/A')
                    tx_type = tx.get('type', 'UNKNOWN')
                    timestamp = tx.get('timestamp', 0)
                    token_transfers = tx.get('tokenTransfers', [])

                    # Look for tokens coming INTO this wallet
                    for transfer in token_transfers:
                        to_account = transfer.get('toUserAccount')

                        # Only track transfers TO our wallet
                        if to_account == self.wallet:
                            mint = transfer.get('mint')
                            amount = transfer.get('tokenAmount', 0)
                            from_account = transfer.get('fromUserAccount', 'Unknown')

                            if mint not in token_inflows:
                                token_inflows[mint] = {
                                    'symbol': self._get_token_symbol(transfer, tx),
                                    'total_received': 0,
                                    'inflows': []
                                }

                            token_inflows[mint]['total_received'] += amount
                            token_inflows[mint]['inflows'].append({
                                'signature': sig,
                                'type': tx_type,
                                'timestamp': timestamp,
                                'datetime': datetime.fromtimestamp(timestamp),
                                'amount': amount,
                                'from_account': from_account,
                                'from_short': f"{from_account[:8]}...{from_account[-6:]}" if len(from_account) > 20 else from_account
                            })

                    # Update cursor for pagination
                    before = tx.get('signature', '')

                    if tx_count >= limit:
                        break

            except Exception as e:
                print(f"❌ Error fetching transactions: {e}")
                break

        print(f"\n✅ Processed {tx_count} total transactions")
        return token_inflows

    def _get_token_symbol(self, transfer: Dict, tx: Dict) -> str:
        """Extract token symbol from transfer or transaction data"""
        # Try to get symbol from various places
        mint = transfer.get('mint', 'Unknown')

        # Common token mappings
        known_tokens = {
            'So11111111111111111111111111111111111111112': 'SOL',
            'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v': 'USDC',
            'Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB': 'USDT',
        }

        if mint in known_tokens:
            return known_tokens[mint]

        # Use first 8 chars of mint as symbol
        return mint[:8] if len(mint) > 8 else mint

    def print_report(self, token_inflows: Dict[str, List[Dict]]):
        """Print a formatted report of token inflows"""
        print("\n" + "=" * 80)
        print("📊 TOKEN INFLOW REPORT")
        print("=" * 80)

        if not token_inflows:
            print("\n⚠️ No token inflows found")
            return

        print(f"\n🔢 Found {len(token_inflows)} unique tokens received\n")

        for mint, data in sorted(token_inflows.items(),
                                 key=lambda x: x[1]['total_received'],
                                 reverse=True):
            symbol = data['symbol']
            total = data['total_received']
            inflows = data['inflows']

            print(f"\n{'='*80}")
            print(f"Token: {symbol}")
            print(f"Mint: {mint}")
            print(f"Total Received: {total:,.2f}")
            print(f"Number of Inflows: {len(inflows)}")
            print(f"{'-'*80}")

            # Show each inflow event
            for i, inflow in enumerate(inflows, 1):
                print(f"\n  #{i} - {inflow['type']}")
                print(f"     Amount:    {inflow['amount']:,.2f}")
                print(f"     From:      {inflow['from_short']}")
                print(f"     Time:      {inflow['datetime']}")
                print(f"     Signature: {inflow['signature'][:16]}...")

        print("\n" + "=" * 80)

    def export_to_json(self, token_inflows: Dict, filename: str = None):
        """Export token inflows to JSON file"""
        if filename is None:
            filename = f"token_inflows_{self.wallet[:8]}_{datetime.now().strftime('%Y%m%d_%H%M')}.json"

        # Convert datetime objects to strings for JSON serialization
        export_data = {}
        for mint, data in token_inflows.items():
            export_data[mint] = {
                'symbol': data['symbol'],
                'total_received': data['total_received'],
                'inflows': [
                    {
                        **inflow,
                        'datetime': inflow['datetime'].isoformat()
                    }
                    for inflow in data['inflows']
                ]
            }

        with open(filename, 'w') as f:
            json.dump(export_data, f, indent=2)

        print(f"\n✅ Exported to {filename}")


def analyze_token_inflows(wallet: str, limit: int = 1000):
    """
    Convenience function to analyze token inflows for a wallet

    Args:
        wallet: Wallet address to analyze
        limit: Maximum number of transactions to check
    """
    tracker = TokenInflowTracker(wallet)
    inflows = tracker.track_token_inflows(limit)
    tracker.print_report(inflows)
    tracker.export_to_json(inflows)
    return inflows


if __name__ == "__main__":
    # Example usage
    test_wallet = "2fg5QD1eD7rzNNCsvnhmXFm5hqNgwTTG8p7kQ6f3rx6f"
    analyze_token_inflows(test_wallet, limit=500)
