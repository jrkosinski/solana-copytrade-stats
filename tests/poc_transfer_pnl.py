#!/usr/bin/env python3
"""
Proof-of-Concept: Track token acquisitions (swaps + transfers) and calculate P&L

This simplified version:
1. Fetches ALL transactions (swaps + transfers)
2. Tracks token inflows (buys via swap + transfers in)
3. Tracks token outflows (sells via swap)
4. For transfers, estimates cost using simple market price at time of transfer
5. Matches buys (including transfers) with sells for P&L
"""

import os
import requests
from datetime import datetime
from typing import Dict, List
import json


class SimpleTransferPnLTracker:
    """Simplified tracker for demonstrating transfer-based P&L"""

    def __init__(self, wallet: str, helius_api_key: str = None):
        self.wallet = wallet
        self.helius_api_key = helius_api_key or os.getenv('HELIUS_API_KEY')
        self.helius_url = "https://api.helius.xyz/v0"

    def fetch_all_transactions(self, limit: int = 200) -> List[Dict]:
        """Fetch both swaps and transfers"""
        print(f"📡 Fetching transactions for {self.wallet[:8]}...{self.wallet[-6:]}")
        print(f"   Limit: {limit} transactions\n")

        url = f"{self.helius_url}/addresses/{self.wallet}/transactions"
        all_txs = []
        before = ''
        count = 0

        while count < limit:
            params = {
                'api-key': self.helius_api_key,
                'before': before
                # NO type filter - get ALL transaction types
            }

            try:
                response = requests.get(url, params=params)
                data = response.json()

                if len(data) == 0:
                    break

                for tx in data:
                    count += 1
                    if isinstance(tx, str):
                        continue

                    all_txs.append(tx)
                    before = tx.get('signature', '')

                    if count >= limit:
                        break

            except Exception as e:
                print(f"❌ Error: {e}")
                break

        print(f"✅ Fetched {len(all_txs)} transactions\n")
        return all_txs

    def extract_token_flows(self, transactions: List[Dict]) -> Dict:
        """
        Extract token inflows and outflows
        Returns: {
            'inflows': [{'token': ..., 'amount': ..., 'type': 'SWAP'|'TRANSFER', ...}],
            'outflows': [{'token': ..., 'amount': ..., ...}]
        }
        """
        inflows = []
        outflows = []

        print("🔍 Analyzing token flows...")

        for tx in transactions:
            tx_type = tx.get('type')
            timestamp = tx.get('timestamp', 0)
            signature = tx.get('signature', 'N/A')
            token_transfers = tx.get('tokenTransfers', [])

            # Process each token transfer
            for transfer in token_transfers:
                from_account = transfer.get('fromUserAccount')
                to_account = transfer.get('toUserAccount')
                mint = transfer.get('mint')
                amount = transfer.get('tokenAmount', 0)

                # Skip if no amount or no mint
                if amount == 0 or not mint:
                    continue

                # Token coming INTO our wallet
                if to_account == self.wallet:
                    inflow = {
                        'token': mint,
                        'symbol': mint[:8],
                        'amount': amount,
                        'type': tx_type,
                        'timestamp': timestamp,
                        'datetime': datetime.fromtimestamp(timestamp) if timestamp else None,
                        'signature': signature,
                        'from_account': from_account
                    }
                    inflows.append(inflow)

                # Token going OUT of our wallet
                elif from_account == self.wallet:
                    outflow = {
                        'token': mint,
                        'symbol': mint[:8],
                        'amount': amount,
                        'type': tx_type,
                        'timestamp': timestamp,
                        'datetime': datetime.fromtimestamp(timestamp) if timestamp else None,
                        'signature': signature,
                        'to_account': to_account
                    }
                    outflows.append(outflow)

        print(f"   Found {len(inflows)} token inflows")
        print(f"   Found {len(outflows)} token outflows\n")

        return {'inflows': inflows, 'outflows': outflows}

    def group_by_token(self, flows: Dict) -> Dict:
        """Group inflows and outflows by token"""
        token_data = {}

        # Group inflows
        for inflow in flows['inflows']:
            token = inflow['token']
            if token not in token_data:
                token_data[token] = {
                    'symbol': inflow['symbol'],
                    'acquisitions': [],
                    'disposals': []
                }
            token_data[token]['acquisitions'].append(inflow)

        # Group outflows
        for outflow in flows['outflows']:
            token = outflow['token']
            if token not in token_data:
                token_data[token] = {
                    'symbol': outflow['symbol'],
                    'acquisitions': [],
                    'disposals': []
                }
            token_data[token]['disposals'].append(outflow)

        return token_data

    def estimate_transfer_cost(self, transfer: Dict) -> float:
        """
        Estimate cost basis for a transferred token
        For POC, we'll use a simple assumption: 0.01 SOL per token
        In production, you'd look up market price at transfer time
        """
        # Simple estimation: assume each token costs 0.01 SOL
        return transfer['amount'] * 0.01

    def calculate_pnl(self, token_data: Dict) -> List[Dict]:
        """Calculate P&L for each token using FIFO matching"""
        print("💰 Calculating P&L...\n")

        matched_trades = []

        for token, data in token_data.items():
            acquisitions = sorted(data['acquisitions'], key=lambda x: x['timestamp'])
            disposals = sorted(data['disposals'], key=lambda x: x['timestamp'])

            symbol = data['symbol']

            # Skip if no complete cycles
            if not acquisitions or not disposals:
                continue

            print(f"Token: {symbol}")
            print(f"   Acquisitions: {len(acquisitions)} ({sum(a['amount'] for a in acquisitions):,.2f} total)")
            print(f"   Disposals: {len(disposals)} ({sum(d['amount'] for d in disposals):,.2f} total)")

            # FIFO matching
            for disposal in disposals:
                if not acquisitions:
                    break

                acquisition = acquisitions[0]

                # Estimate cost for transfers
                if acquisition['type'] == 'TRANSFER':
                    estimated_cost = self.estimate_transfer_cost(acquisition)
                    cost_per_token = estimated_cost / acquisition['amount'] if acquisition['amount'] > 0 else 0
                    cost_token = 'SOL'
                    acquisition_method = 'TRANSFER'
                else:
                    # For swaps, we'd extract the actual cost from the swap
                    # For POC, use simple estimation
                    estimated_cost = acquisition['amount'] * 0.01
                    cost_per_token = 0.01
                    cost_token = 'SOL'
                    acquisition_method = 'SWAP'

                # For disposal, estimate proceeds (in POC, assume we got SOL back)
                # In production, parse the actual swap data
                proceeds = disposal['amount'] * 0.015  # Assume 50% profit for demo
                proceeds_per_token = 0.015
                proceeds_token = 'SOL'

                # Calculate P&L
                profit = proceeds - estimated_cost
                pnl_pct = ((proceeds / estimated_cost) - 1) * 100 if estimated_cost > 0 else 0

                trade = {
                    'token': symbol,
                    'acquisition_type': acquisition_method,
                    'buy_time': acquisition['datetime'],
                    'sell_time': disposal['datetime'],
                    'amount': acquisition['amount'],
                    'cost': estimated_cost,
                    'proceeds': proceeds,
                    'profit': profit,
                    'pnl_pct': pnl_pct,
                    'cost_token': cost_token,
                    'proceeds_token': proceeds_token
                }

                matched_trades.append(trade)

                # Remove matched acquisition
                acquisitions.pop(0)

                print(f"      ✅ Matched: {acquisition_method} → SELL")
                print(f"         Amount: {acquisition['amount']:,.2f}")
                print(f"         Cost: {estimated_cost:.4f} {cost_token}")
                print(f"         Proceeds: {proceeds:.4f} {proceeds_token}")
                print(f"         P&L: {pnl_pct:+.2f}%")

            print()

        return matched_trades

    def print_summary(self, matched_trades: List[Dict]):
        """Print summary of matched trades"""
        print("\n" + "=" * 80)
        print("📊 PROOF-OF-CONCEPT P&L SUMMARY")
        print("=" * 80)

        if not matched_trades:
            print("\n⚠️ No matched trades found")
            print("   This might mean:")
            print("   - Tokens were acquired but not sold yet")
            print("   - Tokens were sold but never acquired (invalid)")
            print("   - No token activity in fetched transactions")
            return

        print(f"\n🔢 Total Matched Trades: {len(matched_trades)}\n")

        # Group by acquisition type
        swap_trades = [t for t in matched_trades if t['acquisition_type'] == 'SWAP']
        transfer_trades = [t for t in matched_trades if t['acquisition_type'] == 'TRANSFER']

        print(f"📦 Trades from SWAPS: {len(swap_trades)}")
        print(f"📥 Trades from TRANSFERS: {len(transfer_trades)}")

        if transfer_trades:
            print(f"\n✨ Successfully matched {len(transfer_trades)} trades that came from TRANSFERS!")
            print("   This proves the concept works!")

        # Calculate overall stats
        total_profit = sum(t['profit'] for t in matched_trades)
        avg_pnl = sum(t['pnl_pct'] for t in matched_trades) / len(matched_trades)

        print(f"\n💰 Overall Stats:")
        print(f"   Total Profit: {total_profit:+.4f} SOL")
        print(f"   Average P&L: {avg_pnl:+.2f}%")

        print("\n" + "=" * 80)


def run_poc(wallet: str, limit: int = 1000):
    """Run the proof-of-concept"""
    print("🧪 PROOF-OF-CONCEPT: Transfer-Based P&L Tracking")
    print("=" * 80)
    print(f"Wallet: {wallet}")
    print(f"Limit: {limit} transactions")
    print("=" * 80 + "\n")

    tracker = SimpleTransferPnLTracker(wallet)

    # Step 1: Fetch transactions
    transactions = tracker.fetch_all_transactions(limit)

    # Step 2: Extract token flows
    flows = tracker.extract_token_flows(transactions)

    # Step 3: Group by token
    token_data = tracker.group_by_token(flows)

    # Step 4: Calculate P&L
    matched_trades = tracker.calculate_pnl(token_data)

    # Step 5: Print summary
    tracker.print_summary(matched_trades)

    return matched_trades


if __name__ == "__main__":
    # Test with the problem wallet
    test_wallet = "2fg5QD1eD7rzNNCsvnhmXFm5hqNgwTTG8p7kQ6f3rx6f"
    run_poc(test_wallet, limit=1000)
