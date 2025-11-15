#!/usr/bin/env python3
"""
Compare what POC sees vs what Analyzer sees in terms of token flows
"""
import os
import requests

wallet = "2fg5QD1eD7rzNNCsvnhmXFm5hqNgwTTG8p7kQ6f3rx6f"
helius_api_key = os.getenv('HELIUS_API_KEY')
helius_url = "https://api.helius.xyz/v0"

print("🔬 Diagnostic: Comparing POC vs Analyzer transaction processing")
print("=" * 80)

# Fetch transactions (same as both POC and Analyzer do)
url = f"{helius_url}/addresses/{wallet}/transactions"
all_txs = []
before = ''
limit = 1000
count = 0

print(f"📡 Fetching {limit} transactions...\n")

while count < limit:
    params = {
        'api-key': helius_api_key,
        'before': before
    }

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

print(f"✅ Fetched {len(all_txs)} transactions\n")

# Simulate POC logic
print("📦 POC-style processing (iterates through tokenTransfers):")
poc_inflows = []
poc_outflows = []

for tx in all_txs:
    token_transfers = tx.get('tokenTransfers', [])
    for transfer in token_transfers:
        from_account = transfer.get('fromUserAccount')
        to_account = transfer.get('toUserAccount')
        mint = transfer.get('mint')
        amount = transfer.get('tokenAmount', 0)

        if amount == 0 or not mint:
            continue

        if to_account == wallet:
            poc_inflows.append({'token': mint, 'amount': amount, 'tx_type': tx.get('type')})
        elif from_account == wallet:
            poc_outflows.append({'token': mint, 'amount': amount, 'tx_type': tx.get('type')})

print(f"  Inflows:  {len(poc_inflows)}")
print(f"  Outflows: {len(poc_outflows)}")

# Count by transaction type
poc_swap_inflows = sum(1 for x in poc_inflows if x['tx_type'] == 'SWAP')
poc_swap_outflows = sum(1 for x in poc_outflows if x['tx_type'] == 'SWAP')
poc_transfer_inflows = sum(1 for x in poc_inflows if x['tx_type'] == 'TRANSFER')
poc_transfer_outflows = sum(1 for x in poc_outflows if x['tx_type'] == 'TRANSFER')

print(f"    SWAP inflows: {poc_swap_inflows}, SWAP outflows: {poc_swap_outflows}")
print(f"    TRANSFER inflows: {poc_transfer_inflows}, TRANSFER outflows: {poc_transfer_outflows}")

# Simulate Analyzer logic
print("\n🔧 Analyzer-style processing (checks tx_type first, then tokenTransfers):")
analyzer_trades = []

for tx in all_txs:
    tx_type = tx.get('type')

    if tx_type not in ['SWAP', 'TRANSFER']:
        continue

    token_transfers = tx.get('tokenTransfers', [])

    if tx_type == 'TRANSFER':
        # Analyzer skips if no tokenTransfers
        if not token_transfers:
            continue

        # Only care about tokens coming IN for transfers
        token_out_by_mint = {}
        for transfer in token_transfers:
            if transfer.get('toUserAccount') == wallet:
                mint = transfer.get('mint')
                amount = transfer.get('tokenAmount', 0)
                if mint and amount > 0:
                    if mint not in token_out_by_mint:
                        token_out_by_mint[mint] = 0
                    token_out_by_mint[mint] += amount

        if token_out_by_mint:
            analyzer_trades.append({'type': 'TRANSFER', 'tokens': len(token_out_by_mint)})

    elif tx_type == 'SWAP':
        token_in_by_mint = {}
        token_out_by_mint = {}

        for transfer in token_transfers:
            mint = transfer.get('mint')
            amount = transfer.get('tokenAmount', 0)

            if transfer.get('fromUserAccount') == wallet:
                if mint not in token_in_by_mint:
                    token_in_by_mint[mint] = 0
                token_in_by_mint[mint] += amount
            elif transfer.get('toUserAccount') == wallet:
                if mint not in token_out_by_mint:
                    token_out_by_mint[mint] = 0
                token_out_by_mint[mint] += amount

        if token_in_by_mint and token_out_by_mint:
            analyzer_trades.append({'type': 'SWAP'})

analyzer_swaps = sum(1 for t in analyzer_trades if t['type'] == 'SWAP')
analyzer_transfers = sum(1 for t in analyzer_trades if t['type'] == 'TRANSFER')

print(f"  Valid trades: {len(analyzer_trades)}")
print(f"    SWAPs: {analyzer_swaps}")
print(f"    TRANSFERs: {analyzer_transfers}")

print("\n" + "=" * 80)
print("🔍 Key Differences:")
print(f"  POC would process {len(poc_inflows)} token inflows (SWAP + TRANSFER combined)")
print(f"  Analyzer would create {len(analyzer_trades)} trade records")
print(f"  Difference: {len(poc_inflows) - len(analyzer_trades)}")
print("=" * 80)
