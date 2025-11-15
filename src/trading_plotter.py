"""
Trading Plotter - Visualization utilities for trading analysis

This module provides plotting functionality for analyzing trading performance,
including P/L distributions, entry/exit behavior, and trade details.
"""

import os
import pandas as pd
import numpy as np
from datetime import datetime
import matplotlib.pyplot as plt
import seaborn as sns
from IPython.display import display
import ipywidgets as widgets

# Set style for better looking plots
plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("husl")


class TradingPlotter:
    """
    Creates visualizations for trading performance analysis

    Expected DataFrame formats:

    trades_df (pandas.DataFrame):
        Required columns:
        - token (str): Token symbol
        - buy_time (datetime): When position was opened
        - sell_time (datetime): When position was closed
        - hold_seconds (float): Duration of position in seconds
        - hold_days (float): Duration of position in days
        - cost (float): Cost of entering position
        - cost_token (str): Currency used for cost (e.g., 'SOL', 'USDC')
        - proceeds (float): Proceeds from closing position
        - proceeds_token (str): Currency received (e.g., 'SOL', 'USDC')
        - profit (float): Net profit/loss
        - pnl_pct (float): Profit/loss as percentage
        - buy_sig (str): Buy transaction signature
        - sell_sig (str): Sell transaction signature
        - largest_buy_pct (float): Largest single buy as % of total position
        - largest_sell_pct (float): Largest single sell as % of total position
        - num_buys (int): Number of buy transactions for this token
        - num_sells (int): Number of sell transactions for this token

    latency_df (pandas.DataFrame):
        Required columns:
        - slot_latency (float): Copy latency in slots
        - token (str): Token symbol
    """

    def __init__(self, main_wallet: str, target_wallet: str = None):
        """
        Initialize the plotter

        Args:
            main_wallet: Main wallet address being analyzed
            target_wallet: Optional target wallet for comparison
        """
        self.main_wallet = main_wallet
        self.target_wallet = target_wallet

    def plot_results(self, trades_df: pd.DataFrame, latency_df: pd.DataFrame = None,
                    figsize=(20, 14), save_plots=False):
        """
        Create visualizations with tabbed interface for Jupyter notebooks

        Args:
            trades_df: DataFrame containing trade data (see class docstring for format)
            latency_df: Optional DataFrame containing latency data
            figsize: Tuple of (width, height) for figure size in inches
            save_plots: If True, save plots as PNG files to ./plots/ directory
        """
        if trades_df.empty and (latency_df is None or latency_df.empty):
            print("❌ No data to plot")
            return

        # Determine what data we have
        has_trades = not trades_df.empty
        has_latency = latency_df is not None and not latency_df.empty

        # Create output widgets for each tab
        graphs_output = widgets.Output()
        table_output = widgets.Output()
        behavior_output = widgets.Output()

        # Create the graphs tab
        with graphs_output:
            self._plot_graphs(trades_df, latency_df, has_trades, has_latency, figsize, save_plots)

        # Create the table tab
        with table_output:
            if has_trades:
                self._plot_table(trades_df, save_plots)
            else:
                print("No trade data available for table")

        # Create the behavior tab
        with behavior_output:
            if has_trades:
                self._plot_entry_exit_behavior(trades_df, figsize, save_plots)
            else:
                print("No trade data available for behavior analysis")

        # Create tab widget
        tab = widgets.Tab(children=[graphs_output, table_output, behavior_output])
        tab.set_title(0, 'Performance Graphs')
        tab.set_title(1, 'Trade Details')
        tab.set_title(2, 'Entry/Exit Behavior')

        # Display the tabbed interface
        display(tab)

    def _plot_graphs(self, trades_df, latency_df, has_trades, has_latency, figsize, save_plots=False):
        """
        Create the performance graphs including P/L distribution, win/loss ratio, etc.

        Args:
            trades_df: DataFrame containing trade data
            latency_df: DataFrame containing latency data
            has_trades: Boolean indicating if trade data is available
            has_latency: Boolean indicating if latency data is available
            figsize: Tuple of (width, height) for figure size in inches
            save_plots: If True, save the plot as a PNG file
        """
        # Create figure with GridSpec for flexible layout
        if has_trades and has_latency:
            fig = plt.figure(figsize=(figsize[0], figsize[1] * 0.75))
            gs = fig.add_gridspec(2, 3, hspace=0.4, wspace=0.3)
            axes = [fig.add_subplot(gs[i, j]) for i in range(2) for j in range(3)]
        elif has_trades:
            fig = plt.figure(figsize=(figsize[0], figsize[1] * 0.6))
            gs = fig.add_gridspec(2, 3, hspace=0.4, wspace=0.3)
            axes = [fig.add_subplot(gs[i, j]) for i in range(2) for j in range(3)]
        else:
            fig, axes = plt.subplots(1, 2, figsize=(12, 5))

        plot_idx = 0

        if has_trades:
            # 1. P/L Distribution
            ax = axes[plot_idx]
            trades_df['pnl_pct'].hist(bins=30, ax=ax, color='skyblue', edgecolor='black')
            ax.axvline(0, color='red', linestyle='--', alpha=0.5)
            ax.set_title('P/L Distribution')
            ax.set_xlabel('P/L (%)')
            ax.set_ylabel('Number of Trades')
            plot_idx += 1

            # 2. Win/Loss Pie
            ax = axes[plot_idx]
            wins = (trades_df['pnl_pct'] > 0).sum()
            losses = (trades_df['pnl_pct'] <= 0).sum()
            ax.pie([wins, losses], labels=[f'Wins ({wins})', f'Losses ({losses})'],
                   autopct='%1.1f%%', colors=['#2ecc71', '#e74c3c'], startangle=90)
            ax.set_title('Win/Loss Ratio')
            plot_idx += 1

            # 3. Cumulative P/L
            ax = axes[plot_idx]
            df_sorted = trades_df.sort_values('sell_time')
            df_sorted['cumulative_pnl'] = df_sorted['pnl_pct'].cumsum()
            ax.plot(df_sorted['sell_time'], df_sorted['cumulative_pnl'],
                   linewidth=2, color='blue')
            ax.fill_between(df_sorted['sell_time'], 0, df_sorted['cumulative_pnl'],
                           where=(df_sorted['cumulative_pnl'] > 0), color='green', alpha=0.3)
            ax.fill_between(df_sorted['sell_time'], 0, df_sorted['cumulative_pnl'],
                           where=(df_sorted['cumulative_pnl'] <= 0), color='red', alpha=0.3)
            ax.set_title('Cumulative P/L Over Time')
            ax.set_xlabel('Date')
            ax.set_ylabel('Cumulative P/L (%)')
            ax.tick_params(axis='x', rotation=45)
            plot_idx += 1

            # 4. Hold Time vs P/L
            ax = axes[plot_idx]
            scatter = ax.scatter(trades_df['hold_days'], trades_df['pnl_pct'],
                               c=trades_df['pnl_pct'], cmap='RdYlGn',
                               alpha=0.6, edgecolors='black', linewidth=0.5)
            ax.axhline(0, color='black', linestyle='-', alpha=0.3)
            ax.set_title('Hold Time vs P/L')
            ax.set_xlabel('Hold Time (days)')
            ax.set_ylabel('P/L (%)')
            plt.colorbar(scatter, ax=ax)
            plot_idx += 1

            # 5. Top Tokens
            ax = axes[plot_idx]
            token_perf = trades_df.groupby('token')['pnl_pct'].mean().sort_values().tail(10)
            colors = ['red' if x < 0 else 'green' for x in token_perf]
            token_perf.plot(kind='barh', ax=ax, color=colors)
            ax.set_title('Top 10 Tokens by Avg P/L')
            ax.set_xlabel('Average P/L (%)')
            plot_idx += 1

        if has_latency:
            # 6. Latency Distribution
            ax = axes[plot_idx]
            latency_df['slot_latency'].hist(bins=30, ax=ax,
                                                 color='purple', edgecolor='black', alpha=0.7)
            mean_latency = latency_df['slot_latency'].mean()
            ax.axvline(mean_latency, color='red', linestyle='--',
                      label=f'Mean: {mean_latency:.1f} slots')
            ax.set_title('Copy Latency Distribution (Slots)')
            ax.set_xlabel('Slot Latency')
            ax.set_ylabel('Frequency')
            ax.legend()

        # Create title with target wallet if specified
        title = f'Solana Copy-Trading Bot Analysis\n{self.main_wallet[:8]}...{self.main_wallet[-6:]}'
        if self.target_wallet:
            title += f'\nvs. {self.target_wallet[:8]}...{self.target_wallet[-6:]}'

        plt.suptitle(title, fontsize=14, fontweight='bold', y=0.995)
        plt.tight_layout()

        # Save plot if requested
        if save_plots:
            self._save_plot('analysis_graphs', plt)

        plt.show()

    def _plot_table(self, trades_df, save_plots=False):
        """
        Create a separate figure for the detailed trade table showing recent trades

        Args:
            trades_df: DataFrame containing trade data
            save_plots: If True, save the table as a PNG file
        """
        fig, ax = plt.subplots(figsize=(20, 10))
        self._add_trade_table(ax, trades_df)

        # Create title with target wallet if specified
        title = f'Trade Details - {self.main_wallet[:8]}...{self.main_wallet[-6:]}'
        if self.target_wallet:
            title += f'\nvs. {self.target_wallet[:8]}...{self.target_wallet[-6:]}'

        plt.suptitle(title, fontsize=14, fontweight='bold', y=0.995)
        plt.tight_layout()

        # Save plot if requested
        if save_plots:
            self._save_plot('trade_table', plt)

        plt.show()

    def _plot_entry_exit_behavior(self, trades_df, figsize=(20, 14), save_plots=False):
        """
        Create detailed visualizations of entry and exit behavior

        Args:
            trades_df: DataFrame containing trade data
            figsize: Tuple of (width, height) for figure size in inches
            save_plots: If True, save the plot as a PNG file
        """
        # Create figure with 3x2 grid for 6 subplots
        fig = plt.figure(figsize=(figsize[0], figsize[1] * 0.75))
        gs = fig.add_gridspec(3, 2, hspace=0.4, wspace=0.3)

        # Calculate statistics
        avg_buy_pct = trades_df['largest_buy_pct'].mean()
        median_buy_pct = trades_df['largest_buy_pct'].median()
        min_buy_pct = trades_df['largest_buy_pct'].min()
        max_buy_pct = trades_df['largest_buy_pct'].max()

        avg_sell_pct = trades_df['largest_sell_pct'].mean()
        median_sell_pct = trades_df['largest_sell_pct'].median()
        min_sell_pct = trades_df['largest_sell_pct'].min()
        max_sell_pct = trades_df['largest_sell_pct'].max()

        avg_num_buys = trades_df['num_buys'].mean()
        avg_num_sells = trades_df['num_sells'].mean()

        # 1. Largest Buy Percentage Distribution
        ax1 = fig.add_subplot(gs[0, 0])
        trades_df['largest_buy_pct'].hist(bins=30, ax=ax1, color='skyblue', edgecolor='black')
        ax1.axvline(avg_buy_pct, color='red', linestyle='--', linewidth=2, label=f'Mean: {avg_buy_pct:.1f}%')
        ax1.axvline(median_buy_pct, color='orange', linestyle='--', linewidth=2, label=f'Median: {median_buy_pct:.1f}%')
        ax1.set_title('Entry Aggressiveness Distribution\n(Largest Single Buy as % of Position)', fontsize=10, fontweight='bold')
        ax1.set_xlabel('Largest Buy (%)')
        ax1.set_ylabel('Number of Trades')
        ax1.legend()
        ax1.text(0.02, 0.98, f'Min: {min_buy_pct:.1f}%\nMax: {max_buy_pct:.1f}%',
                transform=ax1.transAxes, verticalalignment='top',
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

        # 2. Largest Sell Percentage Distribution
        ax2 = fig.add_subplot(gs[0, 1])
        trades_df['largest_sell_pct'].hist(bins=30, ax=ax2, color='coral', edgecolor='black')
        ax2.axvline(avg_sell_pct, color='red', linestyle='--', linewidth=2, label=f'Mean: {avg_sell_pct:.1f}%')
        ax2.axvline(median_sell_pct, color='orange', linestyle='--', linewidth=2, label=f'Median: {median_sell_pct:.1f}%')
        ax2.set_title('Exit Aggressiveness Distribution\n(Largest Single Sell as % of Position)', fontsize=10, fontweight='bold')
        ax2.set_xlabel('Largest Sell (%)')
        ax2.set_ylabel('Number of Trades')
        ax2.legend()
        ax2.text(0.02, 0.98, f'Min: {min_sell_pct:.1f}%\nMax: {max_sell_pct:.1f}%',
                transform=ax2.transAxes, verticalalignment='top',
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

        # 3. Number of Buys per Trade
        ax3 = fig.add_subplot(gs[1, 0])
        trades_df['num_buys'].hist(bins=range(1, int(trades_df['num_buys'].max()) + 2),
                                        ax=ax3, color='lightgreen', edgecolor='black')
        ax3.axvline(avg_num_buys, color='red', linestyle='--', linewidth=2, label=f'Mean: {avg_num_buys:.1f}')
        ax3.set_title('Entry Fragmentation\n(Number of Buy Transactions per Token)', fontsize=10, fontweight='bold')
        ax3.set_xlabel('Number of Buys')
        ax3.set_ylabel('Number of Trades')
        ax3.legend()

        # 4. Number of Sells per Trade
        ax4 = fig.add_subplot(gs[1, 1])
        trades_df['num_sells'].hist(bins=range(1, int(trades_df['num_sells'].max()) + 2),
                                         ax=ax4, color='lightsalmon', edgecolor='black')
        ax4.axvline(avg_num_sells, color='red', linestyle='--', linewidth=2, label=f'Mean: {avg_num_sells:.1f}')
        ax4.set_title('Exit Fragmentation\n(Number of Sell Transactions per Token)', fontsize=10, fontweight='bold')
        ax4.set_xlabel('Number of Sells')
        ax4.set_ylabel('Number of Trades')
        ax4.legend()

        # 5. Buy Aggressiveness vs P/L
        ax5 = fig.add_subplot(gs[2, 0])
        scatter = ax5.scatter(trades_df['largest_buy_pct'], trades_df['pnl_pct'],
                             c=trades_df['pnl_pct'], cmap='RdYlGn',
                             alpha=0.6, edgecolors='black', linewidth=0.5)
        ax5.axhline(0, color='black', linestyle='-', alpha=0.3)
        ax5.set_title('Entry Aggressiveness vs P/L', fontsize=10, fontweight='bold')
        ax5.set_xlabel('Largest Buy (%)')
        ax5.set_ylabel('P/L (%)')
        plt.colorbar(scatter, ax=ax5, label='P/L %')

        # 6. Sell Aggressiveness vs P/L
        ax6 = fig.add_subplot(gs[2, 1])
        scatter = ax6.scatter(trades_df['largest_sell_pct'], trades_df['pnl_pct'],
                             c=trades_df['pnl_pct'], cmap='RdYlGn',
                             alpha=0.6, edgecolors='black', linewidth=0.5)
        ax6.axhline(0, color='black', linestyle='-', alpha=0.3)
        ax6.set_title('Exit Aggressiveness vs P/L', fontsize=10, fontweight='bold')
        ax6.set_xlabel('Largest Sell (%)')
        ax6.set_ylabel('P/L (%)')
        plt.colorbar(scatter, ax=ax6, label='P/L %')

        # Create title with target wallet if specified
        title = f'Entry/Exit Behavior Analysis\n{self.main_wallet[:8]}...{self.main_wallet[-6:]}'
        if self.target_wallet:
            title += f'\nvs. {self.target_wallet[:8]}...{self.target_wallet[-6:]}'

        plt.suptitle(title, fontsize=14, fontweight='bold', y=0.995)
        plt.tight_layout()

        # Save plot if requested
        if save_plots:
            self._save_plot('behavior_analysis', plt)

        plt.show()

    def _add_trade_table(self, ax, trades_df):
        """
        Add a detailed trade table to a matplotlib axis

        Args:
            ax: Matplotlib axis to draw the table on
            trades_df: DataFrame containing trade data
        """
        ax.axis('off')

        # Prepare data for table - show all trades
        df_display = trades_df.copy()

        # Sort by sell time (most recent first) - show all trades
        df_display = df_display.sort_values('sell_time', ascending=False)

        # Format the data for display
        table_data = []
        for idx, row in df_display.iterrows():
            # Format hold time
            hold_seconds = row['hold_seconds']
            if hold_seconds < 60:
                hold_str = f"{hold_seconds:.0f}s"
            elif hold_seconds < 3600:
                hold_str = f"{hold_seconds / 60:.0f}m"
            elif hold_seconds < 86400:
                hold_str = f"{hold_seconds / 3600:.1f}h"
            else:
                hold_str = f"{hold_seconds / 86400:.1f}d"

            # Format profit
            profit_sign = "+" if row['profit'] >= 0 else ""
            pnl_sign = "+" if row['pnl_pct'] >= 0 else ""

            table_data.append([
                row['token'][:12],  # Token symbol (truncated)
                row['buy_time'].strftime('%m/%d %H:%M'),  # Buy Time
                row['sell_time'].strftime('%m/%d %H:%M'),  # Sell Time
                hold_str,
                f"{row['cost']:.3f} {row['cost_token']}",
                f"{row['proceeds']:.3f} {row['proceeds_token']}",
                f"{profit_sign}{row['profit']:.3f}",
                f"{pnl_sign}{row['pnl_pct']:.1f}%",
                f"{row['largest_buy_pct']:.0f}%",
                f"{row['largest_sell_pct']:.0f}%",
                row['buy_sig'],  # Buy Tx Sig
                row['sell_sig']  # Sell Tx Sig
            ])

        # Create column headers
        col_labels = ['Token', 'Buy Time', 'Sell Time', 'Hold', 'Cost', 'Proceeds', 'Profit', 'P/L %', 'Buy %', 'Dump %', 'Buy Tx Sig', 'Sell Tx Sig']

        # Create the table
        table = ax.table(cellText=table_data,
                        colLabels=col_labels,
                        cellLoc='left',
                        loc='center',
                        colWidths=[0.08, 0.07, 0.07, 0.04, 0.10, 0.10, 0.06, 0.05, 0.04, 0.04, 0.12, 0.12])

        # Style the table
        table.auto_set_font_size(False)
        table.set_fontsize(7)
        table.scale(1, 1.5)

        # Color code the header
        for i, key in enumerate(col_labels):
            cell = table[(0, i)]
            cell.set_facecolor('#4472C4')
            cell.set_text_props(weight='bold', color='white')

        # Color code profit/loss rows
        for i, row_data in enumerate(table_data):
            profit_val = float(row_data[7].replace('%', '').replace('+', ''))
            color = '#E8F5E9' if profit_val >= 0 else '#FFEBEE'

            for j in range(len(col_labels)):
                cell = table[(i + 1, j)]
                cell.set_facecolor(color)

        ax.set_title(f'Matched Trades (All {len(df_display)} trades)', fontsize=12, fontweight='bold', pad=10)

    def _save_plot(self, plot_type: str, plt_instance):
        """
        Save a plot to the plots directory

        Args:
            plot_type: Type of plot (e.g., 'analysis_graphs', 'trade_table')
            plt_instance: Matplotlib pyplot instance
        """
        # Create plots directory if it doesn't exist
        os.makedirs('./plots', exist_ok=True)

        # Generate filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        dirname = f"./plots/{self.main_wallet}"
        if not os.path.exists(dirname):
            os.mkdir(dirname)
        filename = f"{dirname}/{plot_type}_{self.main_wallet[:8]}_{timestamp}.png"

        plt_instance.savefig(filename, dpi=300, bbox_inches='tight')

        # Print appropriate message based on plot type
        emoji_map = {
            'analysis_graphs': '📊',
            'trade_table': '📋',
            'behavior_analysis': '📈'
        }
        emoji = emoji_map.get(plot_type, '💾')
        print(f"{emoji} {plot_type.replace('_', ' ').title()} saved to {filename}")
