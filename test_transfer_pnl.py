#!/usr/bin/env python3
import os
import sys
sys.path.insert(0, 'src')
from analyzer import SolanaCopyTradingAnalyzer

wallet = "2fg5QD1eD7rzNNCsvnhmXFm5hqNgwTTG8p7kQ6f3rx6f"
helius_api_key = os.getenv('HELIUS_API_KEY')

print("Testing transfer cost estimation...\n")

analyzer = SolanaCopyTradingAnalyzer(
    main_wallet=wallet,
    target_wallet=None,
    helius_api_key=helius_api_key,
    use_cache=False
)

# Analyze with limited transactions
trades_df = analyzer.analyze_wallet(limit=1000)

print("\n" + "=" * 80)
print("RESULTS:")
print("=" * 80)

if not trades_df.empty:
    print(f"\nTotal matched trades: {len(trades_df)}")
    
    # Show trades with their P&L
    for idx, trade in trades_df.iterrows():
        print(f"\n{idx + 1}. {trade['token']}:")
        print(f"   Cost: {trade['cost']:.6f} {trade['cost_token']}")
        print(f"   Proceeds: {trade['proceeds']:.6f} {trade['proceeds_token']}")
        print(f"   P&L: {trade['pnl_pct']:.2f}%")
        print(f"   Buy sig: {trade['buy_sig'][:20]}...")
else:
    print("\nNo matched trades found")
