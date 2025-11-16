"""
Investigate token transfers to understand the transfer chain:
(a) What wallet were tokens transferred from?
(b) Where did that wallet get them? (via swap or another transfer)
"""

import os
import requests
from typing import Dict, List

# Helius API key
HELIUS_API_KEY = os.getenv('HELIUS_API_KEY')

def fetch_transactions(wallet: str, limit: int = 100) -> List[Dict]:
    """Fetch transactions for a wallet using Helius API"""
    url = f"https://api.helius.xyz/v0/addresses/{wallet}/transactions"
    params = {
        'api-key': HELIUS_API_KEY,
        'limit': limit,
        'type': 'TRANSFER'  # Only fetch transfers
    }

    response = requests.get(url, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error fetching transactions: {response.status_code}")
        return []

def analyze_transfer_chain(target_wallet: str, limit: int = 100):
    """
    Analyze transfer chain for tokens received by target wallet

    For each token transfer INTO target_wallet:
    (a) Identify the sender wallet
    (b) Look up how the sender wallet acquired those tokens (swap or transfer)
    """

    print(f"\n{'='*80}")
    print(f"🔍 TRANSFER CHAIN ANALYSIS")
    print(f"{'='*80}")
    print(f"Target Wallet: {target_wallet}")
    print(f"{'='*80}\n")

    # Step 1: Get all transfers INTO the target wallet
    print("Step 1: Fetching transfers INTO target wallet...")
    txs = fetch_transactions(target_wallet, limit)
    print(f"Found {len(txs)} TRANSFER transactions\n")

    transfers_in = []

    for tx in txs:
        token_transfers = tx.get('tokenTransfers', [])

        for transfer in token_transfers:
            # Check if this transfer is TO our target wallet
            if transfer.get('toUserAccount') == target_wallet:
                from_account = transfer.get('fromUserAccount')
                token_mint = transfer.get('mint')
                token_symbol = transfer.get('tokenSymbol', 'Unknown')
                amount = transfer.get('tokenAmount', 0)

                transfers_in.append({
                    'signature': tx.get('signature'),
                    'timestamp': tx.get('timestamp'),
                    'from_account': from_account,
                    'token_mint': token_mint,
                    'token_symbol': token_symbol,
                    'amount': amount
                })

    print(f"Found {len(transfers_in)} token inflows via TRANSFER\n")

    # Step 2: For each sender, look up how THEY acquired the token
    print("Step 2: Investigating sender wallets to find acquisition method...\n")

    # Group by sender to avoid duplicate lookups
    by_sender = {}
    for transfer in transfers_in:
        sender = transfer['from_account']
        if sender not in by_sender:
            by_sender[sender] = []
        by_sender[sender].append(transfer)

    print(f"Unique sender wallets: {len(by_sender)}\n")

    for sender_wallet, transfers in by_sender.items():
        print(f"\n{'='*80}")
        print(f"📤 SENDER: {sender_wallet}")
        print(f"{'='*80}")
        print(f"Transferred {len(transfers)} token(s) to {target_wallet[:16]}...")

        for t in transfers:
            print(f"\n  Token: {t['token_symbol']}")
            print(f"  Amount: {t['amount']:.4f}")
            print(f"  Signature: {t['signature']}")

        # Now look up how sender acquired these tokens
        print(f"\n  🔍 Looking up how sender acquired these tokens...")
        sender_txs = fetch_all_transactions(sender_wallet, limit=100)

        # For each token the sender transferred to us, find where they got it
        for t in transfers:
            token_mint = t['token_mint']
            token_symbol = t['token_symbol']
            transfer_timestamp = t['timestamp']

            print(f"\n  Tracking {token_symbol} ({token_mint[:8]}...):")

            # Look for transactions where sender received this token BEFORE transferring it
            acquisitions = []

            for sender_tx in sender_txs:
                # Only look at transactions BEFORE the transfer to target
                if sender_tx.get('timestamp', 0) >= transfer_timestamp:
                    continue

                tx_type = sender_tx.get('type')
                token_transfers_sender = sender_tx.get('tokenTransfers', [])

                for transfer_sender in token_transfers_sender:
                    # Did sender receive this token mint?
                    if (transfer_sender.get('mint') == token_mint and
                        transfer_sender.get('toUserAccount') == sender_wallet):

                        acquisitions.append({
                            'type': tx_type,
                            'signature': sender_tx.get('signature'),
                            'timestamp': sender_tx.get('timestamp'),
                            'amount': transfer_sender.get('tokenAmount', 0),
                            'from': transfer_sender.get('fromUserAccount', 'Unknown')
                        })

            if acquisitions:
                # Show the most recent acquisition (closest to the transfer)
                latest = max(acquisitions, key=lambda x: x['timestamp'])
                print(f"    ✅ Found acquisition: {latest['type']}")
                print(f"       Amount: {latest['amount']:.4f}")
                print(f"       From: {latest['from'][:16]}...")
                print(f"       Signature: {latest['signature']}")

                # If there are multiple acquisitions, show summary
                if len(acquisitions) > 1:
                    print(f"    Note: Found {len(acquisitions)} total acquisitions")
                    swap_count = sum(1 for a in acquisitions if a['type'] == 'SWAP')
                    transfer_count = sum(1 for a in acquisitions if a['type'] == 'TRANSFER')
                    print(f"          {swap_count} via SWAP, {transfer_count} via TRANSFER")

                # If the sender got it via TRANSFER (not SWAP), trace one more level back
                if latest['type'] == 'TRANSFER':
                    print(f"\n    🔗 Tracing one more level back...")
                    second_sender = latest['from']
                    print(f"       Checking wallet: {second_sender[:16]}...")

                    # Fetch transactions for the second sender
                    second_sender_txs = fetch_all_transactions(second_sender, limit=100)

                    # Look for how THEY acquired the token
                    second_acquisitions = []
                    for second_tx in second_sender_txs:
                        # Only look at transactions BEFORE the transfer
                        if second_tx.get('timestamp', 0) >= latest['timestamp']:
                            continue

                        second_tx_type = second_tx.get('type')
                        second_token_transfers = second_tx.get('tokenTransfers', [])

                        for second_transfer in second_token_transfers:
                            if (second_transfer.get('mint') == token_mint and
                                second_transfer.get('toUserAccount') == second_sender):

                                second_acquisitions.append({
                                    'type': second_tx_type,
                                    'signature': second_tx.get('signature'),
                                    'timestamp': second_tx.get('timestamp'),
                                    'amount': second_transfer.get('tokenAmount', 0),
                                    'from': second_transfer.get('fromUserAccount', 'Unknown')
                                })

                    if second_acquisitions:
                        second_latest = max(second_acquisitions, key=lambda x: x['timestamp'])
                        print(f"       ✅ Second-level acquisition: {second_latest['type']}")
                        print(f"          Amount: {second_latest['amount']:.4f}")
                        print(f"          From: {second_latest['from'][:16]}...")
                        print(f"          Signature: {second_latest['signature']}")
                    else:
                        print(f"       ❌ No second-level acquisition found")
            else:
                print(f"    ❌ No acquisition found (may be outside lookback window)")

def fetch_all_transactions(wallet: str, limit: int = 200) -> List[Dict]:
    """Fetch all transaction types for a wallet"""
    url = f"https://api.helius.xyz/v0/addresses/{wallet}/transactions"
    params = {
        'api-key': HELIUS_API_KEY,
        'limit': limit
    }

    response = requests.get(url, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error fetching transactions for {wallet[:16]}...: {response.status_code}")
        print(f"Response: {response.text[:200]}")
        return []


if __name__ == "__main__":
    # Test with the wallet from the conversation
    wallet = "2fg5QD1eD7rzNNCsvnhmXFm5hqNgwTTG8p7kQ6f3rx6f"

    analyze_transfer_chain(wallet, limit=100)
