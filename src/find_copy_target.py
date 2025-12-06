#!/usr/bin/env python3
"""
Find potential copy-trading targets for a bot by analyzing its trade history
"""

import os
from analyzer import WalletTradeAnalyzer
from utils import find_copy_trading_targets
from utils import printsave

# Configuration
BOT_WALLET = "9EibckQ6Jdfnhb4uAG352KaepYXspRrcNwFjC7xkvRXx"  # The bot you want to analyze
LOOKBACK_BLOCKS = 25  # How many blocks to look before each trade (smaller = faster)
MIN_CORRELATION_SCORE = 2  # Minimum matches required (lower = more candidates)
LIMIT = 1000  # How many transactions to fetch from bot (start small)

printsave("=" * 80, overwrite=True)
printsave("🤖 COPY-TRADING TARGET FINDER")
printsave("=" * 80)
printsave(f"Bot wallet: {BOT_WALLET}")
printsave(f"Lookback blocks: {LOOKBACK_BLOCKS}")
printsave(f"Min correlation score: {MIN_CORRELATION_SCORE}")
printsave("=" * 80)

# Step 1: Analyze the bot's wallet to get matched trades
printsave("\n📊 STEP 1: Analyzing bot's trade history...")
printsave("=" * 80)

analyzer = WalletTradeAnalyzer(
    wallet_address=BOT_WALLET,
    target_wallet=None,
    read_cache=True,
    write_cache=True
)

trades_df = analyzer.analyze(limit=LIMIT)

# Get matched trades from analyzer
matched_trades = analyzer.trades

if not matched_trades:
    printsave("\n❌ No matched trade pairs found for this bot")
    printsave("   The bot may not have completed any buy/sell cycles yet")
    exit(1)

printsave(f"\n✅ Found {len(matched_trades)} matched trade pairs")

# Step 2: Find potential copy targets
printsave("\n🔍 STEP 2: Finding potential copy-trading targets...")
printsave("=" * 80)

# Use a subset of trades for testing (to avoid rate limits)
# You can increase this or remove the limit for full analysis
num_trades_to_analyze = min(3, len(matched_trades))  # Start with just 3 trades
printsave(f"\nAnalyzing first {num_trades_to_analyze} trades (to avoid rate limits)")
printsave("TIP: Increase this number for more comprehensive results\n")


for trade in matched_trades:
    printsave(trade['token'])



result = find_copy_trading_targets(
    bot_trades=matched_trades,
    helius_api_key=os.getenv('HELIUS_API_KEY'),
    lookback_blocks=LOOKBACK_BLOCKS,
    min_correlation_score=MIN_CORRELATION_SCORE,
    bot_wallet=BOT_WALLET  # Exclude the bot itself from results
)

# Step 3: Save results
printsave("\n💾 STEP 3: Saving results...")

if result['candidates']:
    import json
    from datetime import datetime

    filename = f"./csv/copy_targets_{BOT_WALLET[:8]}_{datetime.now().strftime('%Y%m%d_%H%M')}.json"

    with open(filename, 'w') as f:
        json.dump(result, f, indent=2, default=str)

    printsave(f"✅ Results saved to {filename}")

    # Print actionable next steps
    printsave("\n" + "=" * 80)
    printsave("🎯 NEXT STEPS")
    printsave("=" * 80)
    printsave("\nTop candidate to investigate:")
    top = result['candidates'][0]
    printsave(f"  Wallet: {top['wallet']}")
    printsave(f"  Score: {top['score']} matches")
    printsave(f"  Tokens: {', '.join(top['tokens_traded'])}")

    printsave("\nTo verify this is the real target, you can:")
    printsave(f"  1. Re-run the main analyzer with target wallet:")
    printsave(f"     full_solana_analysis('{BOT_WALLET}', '{top['wallet']}', 1000)")
    printsave(f"  2. Check if the latency patterns match (avg {top['avg_buy_latency_slots']:.0f} slots)")
    printsave(f"  3. Compare P/L patterns between bot and target")
else:
    printsave("⚠️ No candidates found - try adjusting parameters:")
    printsave(f"   - Increase lookback_blocks (current: {LOOKBACK_BLOCKS})")
    printsave(f"   - Decrease min_correlation_score (current: {MIN_CORRELATION_SCORE})")
    printsave(f"   - Analyze more trades (current: {num_trades_to_analyze})")

printsave("\n" + "=" * 80)
printsave("✅ Analysis complete!")
printsave("=" * 80)
