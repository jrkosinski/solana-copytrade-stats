"""
Trading Reporter - Report generation utilities for trading analysis

This module provides report generation functionality for analyzing trading performance,
including comprehensive statistics, risk metrics, and behavioral analysis.
"""

import pandas as pd
import numpy as np
from typing import Dict


class TradingReporter:
    """
    Generates comprehensive analysis reports for trading performance

    Expected DataFrame formats:

    trades_df (pandas.DataFrame):
        Required columns:
        - token (str): Token symbol
        - buy_time (datetime): When position was opened
        - sell_time (datetime): When position was closed
        - hold_seconds (float): Duration of position in seconds
        - hold_days (float): Duration of position in days
        - cost (float): Cost of entering position
        - proceeds (float): Proceeds from closing position
        - profit (float): Net profit/loss
        - pnl_pct (float): Profit/loss as percentage
        - largest_buy_pct (float): Largest single buy as % of total position
        - largest_sell_pct (float): Largest single sell as % of total position
        - num_buys (int): Number of buy transactions for this token
        - num_sells (int): Number of sell transactions for this token

    latency_df (pandas.DataFrame):
        Required columns:
        - direction (str): 'BUY' or 'SELL'
        - token (str): Token symbol
        - slot_latency (float): Copy latency in slots
        - time_latency (float): Copy latency in seconds
        - bot_sig (str): Bot transaction signature
        - target_sig (str): Target transaction signature
        - bot_slot (int): Bot transaction slot
        - target_slot (int): Target transaction slot
    """

    def __init__(self, main_wallet: str, target_wallet: str = None):
        """
        Initialize the reporter

        Args:
            main_wallet: Main wallet address being analyzed
            target_wallet: Optional target wallet for comparison
        """
        self.main_wallet = main_wallet
        self.target_wallet = target_wallet

    def generate_report(self, trades_df: pd.DataFrame, latency_df: pd.DataFrame = None,
                       bot_txs_count: int = 0):
        """
        Generate comprehensive analysis report with statistics and metrics

        Args:
            trades_df: DataFrame containing trade data (see class docstring for format)
            latency_df: Optional DataFrame containing latency data
            bot_txs_count: Number of raw transactions processed

        Prints detailed statistics including:
        - Overall trade counts and date ranges
        - Profit/loss statistics (mean, median, win rate)
        - Risk metrics (Sharpe ratio, drawdown, draw-up)
        - Hold time statistics
        - Entry behavior (buy aggressiveness, buy fragmentation)
        - Exit behavior (dump aggressiveness, sell fragmentation)
        - Copy latency statistics (if target wallet provided)
        """

        print("\n" + "=" * 80)
        print("📊 SOLANA COPY-TRADING BOT PERFORMANCE REPORT")
        print("=" * 80)

        if not trades_df.empty:

            if not trades_df.empty:
                print("\n📈 Overall Statistics:")
                print(f"   Total Matched Trades: {len(trades_df)}")
                print(f"   Trades in Analysis: {len(trades_df)}")
                print(f"   Unique Tokens Traded: {trades_df['token'].nunique()}")
                print(f"   Date Range: {trades_df['buy_time'].min()} to {trades_df['sell_time'].max()}")

                print("\n💰 Profit/Loss Statistics (Filtered):")
                print(f"   Average P/L per trade: {trades_df['pnl_pct'].mean():.2f}%")
                print(f"   Median P/L per trade: {trades_df['pnl_pct'].median():.2f}%")
                print(f"   Best Trade: {trades_df['pnl_pct'].max():.2f}%")
                print(f"   Worst Trade: {trades_df['pnl_pct'].min():.2f}%")
                print(f"   Win Rate: {(trades_df['pnl_pct'] > 0).mean() * 100:.1f}%")

                # Calculate and display risk metrics
                risk_metrics = self._calculate_risk_metrics(trades_df)
                print("\n📊 Risk Metrics:")
                print(f"   Sharpe Ratio: {risk_metrics['sharpe_ratio']:.2f}")
                print(f"   Max Drawdown: {risk_metrics['max_drawdown']:.2f}%")
                print(f"   Max Drawdown Duration: {risk_metrics['max_drawdown_duration']:.2f} days")
                print(f"   Max Draw-up: {risk_metrics['max_drawup']:.2f}%")
                print(f"   Max Draw-up Duration: {risk_metrics['max_drawup_duration']:.2f} days")

                print("\n⏰ Hold Time Statistics:")
                print(f"   Average Hold Time: {trades_df['hold_days'].mean():.2f} days")
                print(f"   Median Hold Time: {trades_df['hold_days'].median():.2f} days")
                print(f"   Shortest Hold: {trades_df['hold_seconds'].min() / 60:.1f} minutes")
                print(f"   Longest Hold: {trades_df['hold_days'].max():.1f} days")

                print("\n📥 Entry Behavior:")
                print(f"   Average Largest Buy: {trades_df['largest_buy_pct'].mean():.1f}% of position")
                print(f"   Median Largest Buy: {trades_df['largest_buy_pct'].median():.1f}% of position")
                print(f"   Average Buys per Token: {trades_df['num_buys'].mean():.1f}")

                # Categorize entry behavior
                instant_buys = (trades_df['largest_buy_pct'] == 100).sum()
                partial_entries = ((trades_df['largest_buy_pct'] >= 50) & (trades_df['largest_buy_pct'] < 100)).sum()
                gradual_entries = (trades_df['largest_buy_pct'] < 50).sum()
                print(f"   Instant Buy-ins (100%): {instant_buys} ({instant_buys/len(trades_df)*100:.1f}%)")
                print(f"   Partial Entries (50-99%): {partial_entries} ({partial_entries/len(trades_df)*100:.1f}%)")
                print(f"   Gradual Entries (<50%): {gradual_entries} ({gradual_entries/len(trades_df)*100:.1f}%)")

                print("\n🔄 Exit Behavior:")
                print(f"   Average Largest Sell: {trades_df['largest_sell_pct'].mean():.1f}% of position")
                print(f"   Median Largest Sell: {trades_df['largest_sell_pct'].median():.1f}% of position")
                print(f"   Average Sells per Token: {trades_df['num_sells'].mean():.1f}")

                # Categorize exit behavior
                instant_dumps = (trades_df['largest_sell_pct'] == 100).sum()
                partial_exits = ((trades_df['largest_sell_pct'] >= 50) & (trades_df['largest_sell_pct'] < 100)).sum()
                gradual_exits = (trades_df['largest_sell_pct'] < 50).sum()
                print(f"   Instant Dumps (100%): {instant_dumps} ({instant_dumps/len(trades_df)*100:.1f}%)")
                print(f"   Partial Exits (50-99%): {partial_exits} ({partial_exits/len(trades_df)*100:.1f}%)")
                print(f"   Gradual Exits (<50%): {gradual_exits} ({gradual_exits/len(trades_df)*100:.1f}%)")
        else:
            print("\n⚠️ No matched trades found")
            print("   Raw transaction count:", bot_txs_count)

        if latency_df is not None and not latency_df.empty:
            print("\n⚡ Copy Latency Statistics:")
            print(f"   Total Matched Swaps: {len(latency_df)}")

            # Count by direction
            buys = len(latency_df[latency_df['direction'] == 'BUY'])
            sells = len(latency_df[latency_df['direction'] == 'SELL'])
            print(f"   Matched Buys: {buys}")
            print(f"   Matched Sells: {sells}")

            print(f"\n   Average Slot Latency: {latency_df['slot_latency'].mean():.1f} slots")
            print(f"   Median Slot Latency: {latency_df['slot_latency'].median():.0f} slots")
            print(f"   Average Time Latency: {latency_df['time_latency'].mean():.1f} seconds")
            print(f"   Fastest Copy: {latency_df['slot_latency'].min()} slots")
            print(f"   Slowest Copy: {latency_df['slot_latency'].max()} slots")

            # Estimate latency in milliseconds (Solana slot time ~400ms)
            avg_ms = latency_df['slot_latency'].mean() * 400
            print(f"   Estimated Avg Latency: ~{avg_ms:.0f}ms")

            # Detailed breakdown of matched trades
            print("\n📋 Matched Trade Details:")
            for idx, row in latency_df.iterrows():
                direction_emoji = "🟢" if row['direction'] == 'BUY' else "🔴"
                print(f"\n   {direction_emoji} {row['direction']} {row['token']}")
                print(f"      Bot Signature:    {row['bot_sig']}")
                print(f"      Target Signature: {row['target_sig']}")
                print(f"      Slot Latency:     {row['slot_latency']} slots ({row['time_latency']:.1f}s)")
                print(f"      Bot Slot:         {row['bot_slot']}")
                print(f"      Target Slot:      {row['target_slot']}")

    def _calculate_risk_metrics(self, trades_df: pd.DataFrame) -> Dict[str, float]:
        """
        Calculate Sharpe ratio, max drawdown, and max draw-up from trades

        Args:
            trades_df: DataFrame containing trade data

        Returns:
            Dict containing:
                - sharpe_ratio: Annualized Sharpe ratio (assuming 0% risk-free rate)
                - max_drawdown: Maximum drawdown percentage
                - max_drawdown_duration: Duration of max drawdown in days
                - max_drawup: Maximum draw-up percentage (most account was up)
                - max_drawup_duration: Duration of max draw-up in days
        """
        if trades_df.empty:
            return {
                'sharpe_ratio': 0.0,
                'max_drawdown': 0.0,
                'max_drawdown_duration': 0.0,
                'max_drawup': 0.0,
                'max_drawup_duration': 0.0
            }

        # Sort trades by sell time
        df_sorted = trades_df.sort_values('sell_time').copy()

        # Calculate cumulative returns (as percentage points)
        df_sorted['cumulative_pnl'] = df_sorted['pnl_pct'].cumsum()

        # Calculate Sharpe Ratio
        # Using returns (pnl_pct) as the periodic returns
        returns = df_sorted['pnl_pct'].values

        if len(returns) > 1:
            mean_return = np.mean(returns)
            std_return = np.std(returns, ddof=1)

            if std_return > 0:
                # Calculate average trade frequency to annualize
                time_diff = (df_sorted['sell_time'].max() - df_sorted['sell_time'].min()).total_seconds()
                days_elapsed = time_diff / 86400

                if days_elapsed > 0:
                    trades_per_day = len(returns) / days_elapsed
                    trades_per_year = trades_per_day * 365

                    # Annualized Sharpe ratio
                    sharpe_ratio = (mean_return / std_return) * np.sqrt(trades_per_year)
                else:
                    sharpe_ratio = 0.0
            else:
                sharpe_ratio = 0.0
        else:
            sharpe_ratio = 0.0

        # Calculate Maximum Drawdown
        cumulative = df_sorted['cumulative_pnl'].values
        running_max = np.maximum.accumulate(cumulative)
        drawdown = cumulative - running_max

        max_drawdown = np.min(drawdown)

        # Calculate max drawdown duration
        max_dd_duration = 0.0
        if max_drawdown < 0:
            # Find the index of max drawdown
            max_dd_idx = np.argmin(drawdown)

            # Find the peak before this drawdown
            peak_idx = np.argmax(cumulative[:max_dd_idx + 1])

            if peak_idx < max_dd_idx:
                duration_seconds = (df_sorted.iloc[max_dd_idx]['sell_time'] -
                                  df_sorted.iloc[peak_idx]['sell_time']).total_seconds()
                max_dd_duration = duration_seconds / 86400  # Convert to days

        # Calculate Maximum Draw-up (opposite of drawdown)
        # Maximum increase from a trough (running minimum) to a subsequent peak
        running_min = np.minimum.accumulate(cumulative)
        drawup = cumulative - running_min

        max_drawup = np.max(drawup)

        # Calculate max draw-up duration
        max_du_duration = 0.0
        if max_drawup > 0:
            # Find the index of max draw-up
            max_du_idx = np.argmax(drawup)

            # Find the trough before this draw-up
            trough_idx = np.argmin(cumulative[:max_du_idx + 1])

            if trough_idx < max_du_idx:
                duration_seconds = (df_sorted.iloc[max_du_idx]['sell_time'] -
                                  df_sorted.iloc[trough_idx]['sell_time']).total_seconds()
                max_du_duration = duration_seconds / 86400  # Convert to days

        return {
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'max_drawdown_duration': max_dd_duration,
            'max_drawup': max_drawup,
            'max_drawup_duration': max_du_duration
        }
