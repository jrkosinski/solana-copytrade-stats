"""
Utility Functions - Shared helper functions for Solana trading analysis

This module provides utility functions used across multiple modules,
including URL generation, formatting helpers, and common calculations.
"""

from typing import Dict


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
    print(f"\n{'='*70}")
    print(f"Trade #{trade_num} - {trade['token']}{amount_warning}")
    print(f"{'='*70}")
    print(f"Token:         {trade['token']} ({trade['token_address']})")
    print(f"Hold Duration: {duration_str} ({trade['hold_days']:.2f} days)")
    print(f"Buy Time:      {trade['buy_time'].strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Sell Time:     {trade['sell_time'].strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"---")
    print(f"Buy Amount:    {trade['buy_amount']:.4f} {trade['token']}")
    print(f"Sell Amount:   {trade['sell_amount']:.4f} {trade['token']}")
    if amount_mismatch:
        print(f"Amount Traded: {trade['amount_traded']:.4f} {trade['token']} (min of buy/sell)")
    print(f"---")
    print(f"Cost:          {trade['cost']:.4f} {trade['cost_token']} ({trade['cost_per_token']:.8f} per token)")
    print(f"Proceeds:      {trade['proceeds']:.4f} {trade['proceeds_token']} ({trade['proceeds_per_token']:.8f} per token)")
    print(f"---")
    print(f"PROFIT:        {profit_indicator}{profit_raw:.4f} {trade['proceeds_token']} ({pnl_indicator}{pnl_pct:.2f}%)")
    print(f"{'='*70}")
