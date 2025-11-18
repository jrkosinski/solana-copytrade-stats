"""
Utility Functions - Shared helper functions for Solana trading analysis

This module provides utility functions used across multiple modules,
including URL generation, formatting helpers, and common calculations.
"""

from typing import Dict
import time


def get_solscan_url(signature: str) -> str:
    """
    Generate Solscan URL for transaction verification

    Args:
        signature: Transaction signature hash

    Returns:
        Full Solscan.io URL for the transaction
    """
    return f"https://solscan.io/tx/{signature}"

def print_trade_match(trade: Dict, trade_num: int):
    """
    Print formatted trade match details to console

    Args:
        trade: Dictionary containing matched trade details (buy/sell pair with P/L)
        trade_num: Sequential trade number for display

    Expected trade dictionary format:
        - token (str): Token symbol
        - token_address (str): Token mint address
        - hold_seconds (float): Duration of hold in seconds
        - hold_days (float): Duration of hold in days
        - buy_time (datetime): When position was opened
        - sell_time (datetime): When position was closed
        - buy_amount (float): Amount of tokens bought
        - sell_amount (float): Amount of tokens sold
        - amount_traded (float): Minimum of buy/sell amount
        - cost (float): Total cost of position
        - cost_token (str): Currency used for cost
        - cost_per_token (float): Cost per token
        - proceeds (float): Total proceeds from sale
        - proceeds_token (str): Currency received
        - proceeds_per_token (float): Proceeds per token
        - profit (float): Net profit/loss
        - pnl_pct (float): Profit/loss percentage
    """

    # Calculate hold duration in a readable format
    hold_seconds = trade['hold_seconds']
    if hold_seconds < 60:
        duration_str = f"{hold_seconds:.1f}s"
    elif hold_seconds < 3600:
        duration_str = f"{hold_seconds / 60:.1f}m"
    elif hold_seconds < 86400:
        duration_str = f"{hold_seconds / 3600:.1f}h"
    else:
        days = hold_seconds / 86400
        if days < 7:
            duration_str = f"{days:.1f}d"
        else:
            duration_str = f"{days / 7:.1f}w"

    # Format profit/loss with color indicators
    profit_raw = trade['profit']
    pnl_pct = trade['pnl_pct']
    profit_indicator = "+" if profit_raw >= 0 else ""
    pnl_indicator = "+" if pnl_pct >= 0 else ""

    # Check if amounts match
    amount_mismatch = trade['buy_amount'] != trade['sell_amount']
    amount_warning = " ⚠️ PARTIAL" if amount_mismatch else ""

    # Print formatted output
    printsave(f"\n{'='*70}")
    printsave(f"Trade #{trade_num} - {trade['token']}{amount_warning}")
    printsave(f"{'='*70}")
    printsave(f"Token:         {trade['token']} ({trade['token_address']})")
    printsave(f"Hold Duration: {duration_str} ({trade['hold_days']:.2f} days)")
    printsave(f"Buy Time:      {trade['buy_time'].strftime('%Y-%m-%d %H:%M:%S')}")
    printsave(f"Sell Time:     {trade['sell_time'].strftime('%Y-%m-%d %H:%M:%S')}")
    printsave(f"---")
    printsave(f"Buy Amount:    {trade['buy_amount']:.4f} {trade['token']}")
    printsave(f"Sell Amount:   {trade['sell_amount']:.4f} {trade['token']}")
    if amount_mismatch:
        printsave(f"Amount Traded: {trade['amount_traded']:.4f} {trade['token']} (min of buy/sell)")
    printsave(f"---")
    printsave(f"Cost:          {trade['cost']:.4f} {trade['cost_token']} ({trade['cost_per_token']:.8f} per token)")
    printsave(f"Proceeds:      {trade['proceeds']:.4f} {trade['proceeds_token']} ({trade['proceeds_per_token']:.8f} per token)")
    printsave(f"---")
    printsave(f"PROFIT:        {profit_indicator}{profit_raw:.4f} {trade['proceeds_token']} ({pnl_indicator}{pnl_pct:.2f}%)")
    printsave(f"{'='*70}")

def get_wallets_that_bought_token_in_block_range(
    token_mint: str,
    start_slot: int,
    num_blocks: int,
    helius_api_key: str,
    direction: str = "buy"
) -> Dict:
    """
    Find all wallets that traded (bought or sold) a specific token within a block range.

    This is useful for identifying potential copy-trading targets by finding wallets
    that traded the same token shortly before a bot's trade.

    IMPORTANT: This function uses the Solana RPC getBlock method which can be
    rate-limited and slow for large block ranges. Use small ranges (5-50 blocks).

    Args:
        token_mint: Token mint address to search for
        start_slot: Starting slot number (block number)
        num_blocks: Number of blocks to check forward from start_slot
        helius_api_key: Helius API key for making requests
        direction: Either "buy" or "sell" to specify trade direction

    Returns:
        Dictionary with:
        - wallets: Set of wallet addresses that traded this token
        - trades: List of trade details (wallet, slot, amount, etc.)
        - total_trades: Total number of trades found

    Example:
        >>> result = get_wallets_that_bought_token_in_block_range(
        ...     "So11111111111111111111111111111111111111112",  # SOL
        ...     372916770,
        ...     50,
        ...     api_key,
        ...     "buy"
        ... )
        >>> printsave(f"Found {len(result['wallets'])} unique wallets")
        >>> printsave(f"Total trades: {result['total_trades']}")
    """
    import requests

    if direction not in ["buy", "sell"]:
        raise ValueError("direction must be 'buy' or 'sell'")

    printsave(f"🔍 Searching for {direction}s of token {token_mint[:8]}...")
    printsave(f"   Slot range: {start_slot} to {start_slot + num_blocks}")
    printsave(f"   ⚠️  This may take a while for large block ranges...")

    time.sleep(0.2)
    helius_url = f"https://mainnet.helius-rpc.com/?api-key={helius_api_key}"
    end_slot = start_slot + num_blocks

    wallets = set()
    trades = []

    # Strategy: Fetch each block in the range and look for transactions involving the token
    # This is more reliable but slower - only use for small block ranges

    try:
        for slot in range(start_slot, end_slot + 1):
            # Fetch the block
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getBlock",
                "params": [
                    slot,
                    {
                        "encoding": "jsonParsed",
                        "transactionDetails": "full",
                        "maxSupportedTransactionVersion": 0
                    }
                ]
            }

            response = requests.post(helius_url, json=payload)
            response.raise_for_status()
            data = response.json()

            # Check if block exists
            if 'result' not in data or data['result'] is None:
                continue  # Block might be skipped (no transactions)

            block = data['result']
            transactions = block.get('transactions', [])

            # Process each transaction in the block
            for tx in transactions:
                tx_meta = tx.get('meta', {})
                tx_message = tx.get('transaction', {}).get('message', {})

                # Skip failed transactions
                if tx_meta.get('err'):
                    continue

                # Get signature
                signatures = tx.get('transaction', {}).get('signatures', [])
                signature = signatures[0] if signatures else None

                # Look for token transfers involving our token
                post_token_balances = tx_meta.get('postTokenBalances', [])
                pre_token_balances = tx_meta.get('preTokenBalances', [])

                # Create a map of account index to balance changes
                token_changes = {}

                for pre_bal in pre_token_balances:
                    if pre_bal.get('mint') == token_mint:
                        account_index = pre_bal.get('accountIndex')
                        token_changes[account_index] = {
                            'pre': pre_bal.get('uiTokenAmount', {}).get('uiAmount', 0),
                            'post': 0,
                            'owner': pre_bal.get('owner')
                        }

                for post_bal in post_token_balances:
                    if post_bal.get('mint') == token_mint:
                        account_index = post_bal.get('accountIndex')
                        if account_index not in token_changes:
                            token_changes[account_index] = {
                                'pre': 0,
                                'owner': post_bal.get('owner')
                            }
                        token_changes[account_index]['post'] = post_bal.get('uiTokenAmount', {}).get('uiAmount', 0)
                        token_changes[account_index]['owner'] = post_bal.get('owner')

                # Analyze token balance changes to determine buyers/sellers
                for account_index, change in token_changes.items():
                    delta = change['post'] - change['pre']
                    owner = change['owner']

                    # Determine if this is a buy or sell
                    is_buy = delta > 0  # Balance increased = bought
                    is_sell = delta < 0  # Balance decreased = sold

                    # Check if this matches our desired direction
                    if (direction == "buy" and is_buy) or (direction == "sell" and is_sell):
                        wallets.add(owner)
                        trades.append({
                            'wallet': owner,
                            'slot': slot,
                            'timestamp': block.get('blockTime'),
                            'signature': signature,
                            'amount': abs(delta),
                            'direction': direction,
                            'token_mint': token_mint
                        })

            # Progress indicator
            printsave(f"   Progress: {slot - start_slot}/{num_blocks} blocks processed...")

        printsave(f"   ✅ Found {len(wallets)} unique wallets with {len(trades)} {direction} trades")

        return {
            'wallets': wallets,
            'trades': trades,
            'total_trades': len(trades)
        }

    except requests.exceptions.RequestException as e:
        printsave(f"   ❌ Error fetching data from Solana RPC: {e}")
        return {
            'wallets': wallets,
            'trades': trades,
            'total_trades': 0
        }
    except Exception as e:
        printsave(f"   ❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return {
            'wallets': wallets,
            'trades': trades,
            'total_trades': 0
        }

def find_copy_trading_targets(
    bot_trades: list,
    helius_api_key: str,
    lookback_blocks: int = 20,
    min_correlation_score: int = 3,
    bot_wallet: str = None
) -> Dict:
    """
    Analyze a bot's matched trade pairs to identify potential copy-trading targets.

    This works by finding wallets that traded the same tokens in the same direction
    (buy/sell) shortly before the bot's trades. Wallets that appear consistently
    across multiple trade pairs are likely copy targets.

    Args:
        bot_trades: List of bot's matched trade pairs (buy/sell pairs)
                   Each trade should have:
                   - token_address: Token mint
                   - buy_slot: Slot number of bot's buy
                   - sell_slot: Slot number of bot's sell
                   - token: Token symbol (for display)
        helius_api_key: Helius API key
        lookback_blocks: How many blocks to look backwards from bot's trade
        min_correlation_score: Minimum number of trade pairs a wallet must appear in

    Returns:
        Dictionary with:
        - candidates: List of candidate wallets with correlation scores
        - analysis: Detailed breakdown per trade pair
        - summary: Overall statistics

    Example:
        >>> bot_trades = [
        ...     {'token_address': 'ABC...', 'buy_slot': 100, 'sell_slot': 200, 'token': 'TOKEN1'},
        ...     {'token_address': 'DEF...', 'buy_slot': 150, 'sell_slot': 250, 'token': 'TOKEN2'}
        ... ]
        >>> result = find_copy_trading_targets(bot_trades, api_key, lookback_blocks=20)
        >>> for candidate in result['candidates'][:5]:
        ...     printsave(f"{candidate['wallet']}: {candidate['score']} matches")
    """
    from collections import defaultdict

    printsave("=" * 80)
    printsave("🔍 COPY-TRADING TARGET DETECTION")
    printsave("=" * 80)
    printsave(f"Analyzing {len(bot_trades)} trade pairs from bot")
    printsave(f"Looking back {lookback_blocks} blocks before each trade")
    printsave(f"Minimum correlation score: {min_correlation_score}")
    printsave("=" * 80)

    # Track wallet correlation scores
    wallet_scores = defaultdict(int)
    wallet_details = defaultdict(lambda: {
        'buy_matches': [],
        'sell_matches': [],
        'tokens': set()
    })

    trade_pair_analysis = []

    # Analyze each trade pair
    for i, trade in enumerate(bot_trades, 1):
        token_mint = trade.get('token_address')
        token_symbol = trade.get('token', 'Unknown')
        buy_slot = trade.get('buy_slot')
        sell_slot = trade.get('sell_slot')

        printsave(f"\n[{i}/{len(bot_trades)}] Analyzing {token_symbol} (slot {buy_slot} -> {sell_slot})")

        # Find wallets that bought this token before the bot's buy
        printsave(f"  🔍 Finding buys before bot's buy at slot {buy_slot}...")
        buy_candidates = get_wallets_that_bought_token_in_block_range(
            token_mint=token_mint,
            start_slot=buy_slot - lookback_blocks,
            num_blocks=lookback_blocks,
            helius_api_key=helius_api_key,
            direction="buy"
        )

        # Find wallets that sold this token before the bot's sell
        printsave(f"  🔍 Finding sells before bot's sell at slot {sell_slot}...")
        sell_candidates = get_wallets_that_bought_token_in_block_range(
            token_mint=token_mint,
            start_slot=sell_slot - lookback_blocks,
            num_blocks=lookback_blocks,
            helius_api_key=helius_api_key,
            direction="sell"
        )

        # Find intersection: wallets that both bought AND sold
        buy_wallets = buy_candidates['wallets']
        sell_wallets = sell_candidates['wallets']
        matching_wallets = buy_wallets & sell_wallets

        printsave(f"  ✅ Found {len(buy_wallets)} buyers, {len(sell_wallets)} sellers")
        printsave(f"  🎯 {len(matching_wallets)} wallets matched BOTH buy and sell")

        # Calculate latency for each matching wallet and sort by buy latency
        wallet_latencies = []
        for w in matching_wallets:
            buy_trade = next((t for t in buy_candidates['trades'] if t['wallet'] == w), None)
            sell_trade = next((t for t in sell_candidates['trades'] if t['wallet'] == w), None)

            buy_latency = buy_slot - buy_trade['slot'] if buy_trade else 0
            sell_latency = sell_slot - sell_trade['slot'] if sell_trade else 0

            wallet_latencies.append({
                'wallet': w,
                'buy_latency': buy_latency,
                'sell_latency': sell_latency
            })

        # Sort by buy latency (ascending - smallest latency first)
        wallet_latencies.sort(key=lambda x: x['buy_latency'])

        # Print sorted wallets with latency info
        for wl in wallet_latencies:
            printsave(f"     {wl['wallet']} - Buy latency: {wl['buy_latency']} slots, Sell latency: {wl['sell_latency']} slots")

        # Update scores for matching wallets (exclude the bot's own wallet)
        for wallet in matching_wallets:
            # Skip if this is the bot's own wallet
            if bot_wallet and wallet == bot_wallet:
                continue

            wallet_scores[wallet] += 1
            wallet_details[wallet]['tokens'].add(token_symbol)

            # Find the actual trades for this wallet
            buy_trade = next((t for t in buy_candidates['trades'] if t['wallet'] == wallet), None)
            sell_trade = next((t for t in sell_candidates['trades'] if t['wallet'] == wallet), None)

            if buy_trade:
                wallet_details[wallet]['buy_matches'].append({
                    'token': token_symbol,
                    'bot_slot': buy_slot,
                    'target_slot': buy_trade['slot'],
                    'latency_slots': buy_slot - buy_trade['slot']
                })

            if sell_trade:
                wallet_details[wallet]['sell_matches'].append({
                    'token': token_symbol,
                    'bot_slot': sell_slot,
                    'target_slot': sell_trade['slot'],
                    'latency_slots': sell_slot - sell_trade['slot']
                })

        trade_pair_analysis.append({
            'token': token_symbol,
            'token_address': token_mint,
            'buy_slot': buy_slot,
            'sell_slot': sell_slot,
            'buy_candidates': len(buy_wallets),
            'sell_candidates': len(sell_wallets),
            'matching_wallets': len(matching_wallets),
            'matches': list(matching_wallets)
        })

    # Build ranked candidate list
    candidates = []
    for wallet, score in wallet_scores.items():
        if score >= min_correlation_score:
            details = wallet_details[wallet]

            # Calculate average latency
            buy_latencies = [m['latency_slots'] for m in details['buy_matches']]
            sell_latencies = [m['latency_slots'] for m in details['sell_matches']]

            avg_buy_latency = sum(buy_latencies) / len(buy_latencies) if buy_latencies else 0
            avg_sell_latency = sum(sell_latencies) / len(sell_latencies) if sell_latencies else 0

            candidates.append({
                'wallet': wallet,
                'score': score,
                'tokens_traded': list(details['tokens']),
                'num_tokens': len(details['tokens']),
                'avg_buy_latency_slots': avg_buy_latency,
                'avg_sell_latency_slots': avg_sell_latency,
                'buy_matches': details['buy_matches'],
                'sell_matches': details['sell_matches']
            })

    # Sort by score (highest first)
    candidates.sort(key=lambda x: x['score'], reverse=True)

    # Print summary
    printsave("\n" + "=" * 80)
    printsave("📊 RESULTS SUMMARY")
    printsave("=" * 80)
    printsave(f"Total candidates found: {len(candidates)}")
    printsave(f"Trade pairs analyzed: {len(bot_trades)}")

    if candidates:
        printsave(f"\n🏆 TOP CANDIDATES (score >= {min_correlation_score}):")
        for i, candidate in enumerate(candidates[:10], 1):
            printsave(f"\n{i}. {candidate['wallet']}")
            printsave(f"   Score: {candidate['score']} matches across {candidate['num_tokens']} tokens")
            printsave(f"   Tokens: {', '.join(candidate['tokens_traded'][:5])}")
            printsave(f"   Avg latency: {candidate['avg_buy_latency_slots']:.1f} slots (buy), {candidate['avg_sell_latency_slots']:.1f} slots (sell)")
    else:
        printsave("\n⚠️ No candidates found with correlation score >= {min_correlation_score}")
        printsave("   Try lowering min_correlation_score or increasing lookback_blocks")

    printsave("=" * 80)

    return {
        'candidates': candidates,
        'analysis': trade_pair_analysis,
        'summary': {
            'total_candidates': len(candidates),
            'trade_pairs_analyzed': len(bot_trades),
            'lookback_blocks': lookback_blocks,
            'min_correlation_score': min_correlation_score
        }
    }

def printsave(s, filename: str = 'record.txt', overwrite: bool = False): 
    print(s)
    save_to_file(f"{s}\n", filename)

def print_transaction_analysis(result: Dict):
    """
    Print formatted transaction analysis results

    Args:
        result: Transaction analysis dictionary
    """

    if not result.get('success'):
        printsave(f"❌ Transaction Error: {result.get('error', 'Unknown error')}")
        return

    printsave(f"✅ Transaction Status: SUCCESS")
    printsave(f"📅 Timestamp: {result['datetime']}")

    slot = result.get('slot')
    if slot is not None:
        printsave(f"🎰 Slot: {slot}")

    slot_leader = result.get('slot_leader')
    if slot_leader:
        printsave(f"👑 Slot Leader: {slot_leader[:8]}...{slot_leader[-6:]}")
        printsave(f"   Full Address: {slot_leader}")

    printsave(f"💸 Fee: {result['fee']:.6f} SOL")
    if result.get('type'):
        printsave(f"🔖 Type: {result['type']}")

    printsave(f"\n{'='*80}")
    printsave(f"👥 PARTICIPANTS ({len(result['participants'])})")
    printsave(f"{'='*80}")
    for i, participant in enumerate(result['participants'], 1):
        printsave(f"{i}. {participant}")

    if not result['swaps']:
        printsave(f"\n⚠️ No swaps detected in this transaction")
        return

    printsave(f"\n{'='*80}")
    printsave(f"🔄 SWAPS DETECTED ({len(result['swaps'])})")
    printsave(f"{'='*80}")

    for i, swap in enumerate(result['swaps'], 1):
        printsave(f"\n--- Swap #{i} ---")
        printsave(f"Trader: {swap['trader_short']}")
        printsave(f"Full Address: {swap['trader']}")

        printsave(f"\n  📤 SOLD (What was traded away):")
        for token in swap['tokens_sold']:
            printsave(f"    • {token['amount']:.8f} {token['symbol']}")
            printsave(f"      Mint: {token['mint']}")

        printsave(f"\n  📥 BOUGHT (What was received):")
        for token in swap['tokens_bought']:
            printsave(f"    • {token['amount']:.8f} {token['symbol']}")
            printsave(f"      Mint: {token['mint']}")

        if 'exchange_rate' in swap:
            printsave(f"\n  💱 Exchange Rate:")
            printsave(f"    {swap['exchange_rate']['description']}")

    printsave(f"\n{'='*80}")
    printsave(f"🔗 View on Solscan: https://solscan.io/tx/{result['signature']}")
    printsave(f"{'='*80}\n")

def save_to_file(text: str, filename: str, overwrite: bool=False):
    flag = 'w'
    if not overwrite:
        flag = 'a'
    with open(filename, flag) as f:
        f.write(text)
