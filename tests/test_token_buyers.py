#!/usr/bin/env python3
"""
Test script for the get_wallets_that_bought_token_in_block_range function
"""

import os
from src.utils import get_wallets_that_bought_token_in_block_range

# Get API key
helius_api_key = os.getenv('HELIUS_API_KEY')

if not helius_api_key:
    print("ERROR: HELIUS_API_KEY environment variable not set")
    exit(1)

# Example: Find wallets that bought a specific token around a certain slot
# You can replace these with actual values from your bot's trades
token_mint = "F2rgvoWN6AM5U82BxV6AxXTLq3CJmTbF7bu7Yssxpump"  # Example token
start_slot = 372916770  # Example slot (block number)
num_blocks = 10  # Check 10 blocks (small test)

print("=" * 80)
print("Testing: Find wallets that bought a token in a block range")
print("=" * 80)

# Test BUYs
print("\n--- Testing BUYS ---")
result_buys = get_wallets_that_bought_token_in_block_range(
    token_mint=token_mint,
    start_slot=start_slot,
    num_blocks=num_blocks,
    helius_api_key=helius_api_key,
    direction="buy"
)

print(f"\nResults:")
print(f"  Unique wallets: {len(result_buys['wallets'])}")
print(f"  Total trades: {result_buys['total_trades']}")

if result_buys['trades']:
    print(f"\nFirst few trades:")
    for i, trade in enumerate(result_buys['trades'][:5], 1):
        print(f"  {i}. Wallet: {trade['wallet'][:8]}... at slot {trade['slot']} ({trade['amount']:.4f} tokens)")

# Test SELLs
print("\n--- Testing SELLS ---")
result_sells = get_wallets_that_bought_token_in_block_range(
    token_mint=token_mint,
    start_slot=start_slot,
    num_blocks=num_blocks,
    helius_api_key=helius_api_key,
    direction="sell"
)

print(f"\nResults:")
print(f"  Unique wallets: {len(result_sells['wallets'])}")
print(f"  Total trades: {result_sells['total_trades']}")

if result_sells['trades']:
    print(f"\nFirst few trades:")
    for i, trade in enumerate(result_sells['trades'][:5], 1):
        print(f"  {i}. Wallet: {trade['wallet'][:8]}... at slot {trade['slot']} ({trade['amount']:.4f} tokens)")

print("\n" + "=" * 80)
