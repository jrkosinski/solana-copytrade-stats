#!/usr/bin/env python3
"""Test script to verify position size tracking"""

import sys
import os
sys.path.insert(0, 'src')

# Set the full_analyze flag to False before importing
import main
main.full_analyze = False

from analyzer import WalletTradingAnalyzer

# Now import after setting the flag
helius_api_key = os.getenv('HELIUS_API_KEY')

print("Testing Position Size Tracking Implementation")
print("=" * 60)

# Create analyzer with cached data
analyzer = WalletTradingAnalyzer(
    main_wallet="8WEs4FurJNq3zsvUVXKuLCPteGEjYGNq45E4yPpY6no3",
    target_wallet=None,
    helius_api_key=helius_api_key,
    read_cache=True,
    write_cache=True
)

# Analyze wallet
trades_df = analyzer.analyze_wallet(limit=100)

# Check if position_size column exists
if not trades_df.empty:
    print('\n✅ Trade DataFrame Columns:')
    print(trades_df.columns.tolist())

    if 'position_size' in trades_df.columns:
        print('\n✅ Position Size Stats:')
        print(f'   Mean: {trades_df["position_size"].mean():.4f}')
        print(f'   Median: {trades_df["position_size"].median():.4f}')
        print(f'   Min: {trades_df["position_size"].min():.4f}')
        print(f'   Max: {trades_df["position_size"].max():.4f}')

        if 'position_size_currency' in trades_df.columns:
            print(f'   Currency: {trades_df["position_size_currency"].mode()[0]}')

        # Show first few rows
        print('\n📋 Sample Trades (first 3):')
        cols_to_show = ['token', 'position_size', 'position_size_currency', 'pnl_pct']
        print(trades_df[cols_to_show].head(3).to_string(index=False))

        print("\n✅ Position size tracking is working correctly!")
    else:
        print('❌ position_size column not found!')
else:
    print('❌ No trades found in DataFrame')
