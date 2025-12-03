#!/usr/bin/env python3
"""
Debug script to check what transactions are actually being processed by the analyzer
"""
import os
import sys
sys.path.insert(0, 'src')
from analyzer import SolanaCopyTradingAnalyzer

wallet = "2fg5QD1eD7rzNNCsvnhmXFm5hqNgwTTG8p7kQ6f3rx6f"
helius_api_key = os.getenv('HELIUS_API_KEY')

print("🔍 Debugging analyzer transaction processing")
print("=" * 80)

# Create analyzer
analyzer = SolanaCopyTradingAnalyzer(
    main_wallet=wallet,
    target_wallet=None,
    helius_api_key=helius_api_key,
    use_cache=False
)

# Fetch just a few transactions to see what's happening
print("\nFetching 200 transactions...")
trades = analyzer._fetch_trades_helius(wallet, limit=5000, include_transfers=True)

print(f"\n✅ Fetched and processed: {len(trades)} valid trade records")

# Count by type
swaps = sum(1 for t in trades if not t.get('is_transfer'))
transfers = sum(1 for t in trades if t.get('is_transfer'))

print(f"   SWAPs: {swaps}")
print(f"   TRANSFERs: {transfers}")

# Show first few transfers
print("\n📋 First 5 transfer records:")
transfer_count = 0
for trade in trades:
    if trade.get('is_transfer') and transfer_count < 5:
        print(f"\n  Transfer {transfer_count + 1}:")
        print(f"    Token: {trade.get('token_out_symbol')}")
        print(f"    Amount: {trade.get('token_out_amount')}")
        print(f"    From: {trade.get('from_account', 'Unknown')[:20]}...")
        print(f"    Signature: {trade.get('signature')[:20]}...")
        transfer_count += 1

print("\n" + "=" * 80)
