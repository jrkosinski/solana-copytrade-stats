# Copy-Trading Target Finder

## Overview

This tool analyzes a copytrading bot's trade history to identify the wallet(s) it's likely copying. It works by finding wallets that consistently traded the same tokens shortly before the bot.

## How It Works

1. **Fetch bot's trade history** - Gets all completed buy/sell pairs from the bot
2. **Analyze temporal correlation** - For each trade pair:
   - Looks backwards N blocks from the bot's buy to find who bought first
   - Looks backwards N blocks from the bot's sell to find who sold first
   - Finds wallets that appear in BOTH the buy and sell windows
3. **Score candidates** - Wallets that match across multiple trade pairs get higher scores
4. **Rank results** - Returns ranked list of likely copy targets

## Usage

### Quick Start (Standalone Script)

```bash
python3 find_copy_target.py
```

Edit the configuration at the top of the file:
- `BOT_WALLET`: The bot wallet to analyze
- `LOOKBACK_BLOCKS`: How many blocks to look backwards (10-50 recommended)
- `MIN_CORRELATION_SCORE`: Minimum matches required (2-5 recommended)

### From Python Code

```python
from src.main import find_copy_target

# Simple usage
result = find_copy_target("9EibckQ6Jdfnhb4uAG352KaepYXspRrcNwFjC7xkvRXx")

# Advanced usage with custom parameters
result = find_copy_target(
    main_wallet="9EibckQ6Jdfnhb4uAG352KaepYXspRrcNwFjC7xkvRXx",
    lookback_blocks=15,           # Look 15 blocks back
    min_correlation_score=3,      # Require at least 3 matches
    num_trades_to_analyze=10,     # Analyze 10 trade pairs
    limit=200                     # Fetch 200 transactions from bot
)

# Print top candidates
for candidate in result['candidates'][:5]:
    print(f"{candidate['wallet']}: {candidate['score']} matches")
    print(f"  Tokens: {', '.join(candidate['tokens_traded'])}")
    print(f"  Avg latency: {candidate['avg_buy_latency_slots']:.1f} slots")
```

### Direct API Usage

```python
from src.utils import find_copy_trading_targets

# Manually provide trade data
bot_trades = [
    {
        'token_address': 'ABC...',
        'buy_slot': 373351211,
        'sell_slot': 373351320,
        'token': 'TOKEN1'
    },
    # ... more trades
]

result = find_copy_trading_targets(
    bot_trades=bot_trades,
    helius_api_key=os.getenv('HELIUS_API_KEY'),
    lookback_blocks=20,
    min_correlation_score=2,
    bot_wallet="9EibckQ6..."  # Exclude bot from results
)
```

## Result Structure

```python
{
    'candidates': [
        {
            'wallet': 'BhBc8k...',
            'score': 5,                          # Number of matched trade pairs
            'tokens_traded': ['TOKEN1', 'TOKEN2'],
            'num_tokens': 2,
            'avg_buy_latency_slots': 7.5,       # Avg blocks between target buy and bot buy
            'avg_sell_latency_slots': 5.5,      # Avg blocks between target sell and bot sell
            'buy_matches': [...],               # Detailed buy match data
            'sell_matches': [...]               # Detailed sell match data
        }
    ],
    'analysis': [...],  # Per-trade-pair breakdown
    'summary': {
        'total_candidates': 3,
        'trade_pairs_analyzed': 10,
        'lookback_blocks': 20,
        'min_correlation_score': 2
    }
}
```

## Parameters Guide

### `lookback_blocks`
- **Small (5-10)**: Faster, catches very close copying (tight latency)
- **Medium (10-30)**: Balanced, good for most cases
- **Large (30-50)**: Slower, catches bots with higher latency

### `min_correlation_score`
- **Low (1-2)**: More candidates, more false positives
- **Medium (3-5)**: Balanced, good signal-to-noise
- **High (5+)**: Very strict, only consistent patterns

### `num_trades_to_analyze`
- Start small (3-5) for testing
- Use 10-20 for good accuracy
- Use 50+ for comprehensive analysis (slower)

## Performance Notes

- Each block fetch takes ~100-200ms
- Analyzing 1 trade pair with lookback=10 requires ~20 block fetches (~2-4 seconds)
- Analyzing 10 trade pairs: ~20-40 seconds
- Use smaller parameters for faster results, larger for higher confidence

## Interpreting Results

### Good Indicators of a True Copy Target:
- ✅ Score ≥ 5 (appears in many trade pairs)
- ✅ Consistent latency (e.g., always 5-10 slots)
- ✅ Trades multiple different tokens
- ✅ Low latency (< 20 slots = fast copying)

### Potential False Positives:
- ⚠️ Score = 1-2 (could be coincidence)
- ⚠️ Very high latency (> 50 slots = might not be copying)
- ⚠️ Only trades one token (could be market maker)

## Next Steps After Finding Candidates

1. **Verify with full analysis**:
   ```python
   from src.main import full_solana_analysis
   full_solana_analysis(bot_wallet, candidate_wallet, 1000)
   ```

2. **Check latency consistency**: Look at the `buy_matches` and `sell_matches` arrays to see if latency is consistent

3. **Compare P/L patterns**: See if bot and target have similar profit/loss patterns

4. **Manual verification**: Check a few transactions on Solscan to confirm the bot traded after the candidate

## Limitations

- Requires the bot to have completed buy/sell pairs
- Only works for spot trading (not futures/perps)
- May miss targets if lookback window is too small
- Popular tokens may have many traders (more noise)
- Helius API rate limits may slow down large analyses

## Example Output

```
🏆 TOP CANDIDATES (score >= 2):

1. BhBc8kbkgzXHmv79mPHCCVfpdZwanYabPR939g8foje6
   Score: 5 matches across 3 tokens
   Tokens: TOKEN1, TOKEN2, TOKEN3
   Avg latency: 7.5 slots (buy), 5.5 slots (sell)

2. Gg5xSmrpDGrhFJKQ2V4psfL78AV4EPzK5vwwriYtcEzs
   Score: 3 matches across 2 tokens
   Tokens: TOKEN1, TOKEN2
   Avg latency: 10.0 slots (buy), 10.0 slots (sell)
```

## Troubleshooting

**"No candidates found"**
- Try lowering `min_correlation_score` to 1
- Increase `lookback_blocks` to 30-50
- Analyze more trades with `num_trades_to_analyze`

**"Taking too long"**
- Reduce `lookback_blocks` to 5-10
- Reduce `num_trades_to_analyze` to 3-5
- Check your internet connection (API calls)

**"Only finding the bot itself"**
- This is a bug - make sure you pass `bot_wallet` parameter
- Should be fixed in latest version

## Files

- `src/utils.py`: Core functions (`get_wallets_that_bought_token_in_block_range`, `find_copy_trading_targets`)
- `src/main.py`: Convenience wrapper (`find_copy_target`)
- `find_copy_target.py`: Standalone script
- `test_token_buyers.py`: Unit tests for block range search
