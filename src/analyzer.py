import requests
import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import json
from web3 import Web3
from trading_plotter import TradingPlotter
from trading_reporter import TradingReporter
from utils import get_solscan_url, print_trade_match


class SolanaCopyTradingAnalyzer:
    """Analyze copy-trading bot wallet performance on Solana"""

    #Outlier filter constants for report generation
    #Trades with P/L % above MAX_PNL_PCT or below MIN_PNL_PCT will be excluded
    MAX_PNL_PCT = 50000.0   #Exclude trades with profit > 50000%
    MIN_PNL_PCT = -80.0   #Exclude trades with loss < -80%

    def __init__(self, main_wallet: str, target_wallet: str = None,
                 rpc_url: str = "https://api.mainnet-beta.solana.com",
                 helius_api_key: str = None,
                 shyft_api_key: str = None,
                 filter_outliers: bool = False,
                 filter_to_matched_only: bool = True,
                 use_cache: bool = False):
        """
        Initialize the Solana analyzer

        Args:
            main_wallet: The copy-trading bot wallet address
            target_wallet: The wallet being copied (optional)
            rpc_url: Solana RPC endpoint
            helius_api_key: Helius API key for enhanced data (optional)
            shyft_api_key: Shyft API key for transaction parsing (optional)
            filter_outliers: If True, filter extreme P/L outliers from analysis
            filter_to_matched_only: If True and target_wallet provided, only analyze trades that matched between main and target
        """
        self.main_wallet = main_wallet
        self.target_wallet = target_wallet
        self.rpc_url = rpc_url
        self.helius_api_key = helius_api_key
        self.shyft_api_key = shyft_api_key
        self.filter_outliers = filter_outliers
        self.filter_to_matched_only = filter_to_matched_only
        self.use_cache = use_cache

        if not self.target_wallet:
            self.filter_to_matched_only = False

        print(f"Helius API KEY IS {helius_api_key}")
        print(f"=====================================")
        
        #Helius API endpoint
        self.helius_url = f"https://api.helius.xyz/v0"
        
        #Shyft API endpoint
        self.shyft_url = "https://api.shyft.to/sol/v1"
        
        #Common Solana DEX program IDs
        self.dex_programs = {
            'JUP4Fb2cqiRUcaTHdrPC8h2gNsA2ETXiPDD33WcGuJB': 'Jupiter V4',
            'JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4': 'Jupiter V6',
            'whirLbMiicVdio4qvUfM5KAg6Ct8VwpYzGff3uctyCc': 'Orca Whirlpool',
            '9W959DqEETiGZocYWCQPaJ6sBmUzgfxXfqGeTEdp3aQP': 'Orca V2',
            '675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8': 'Raydium V4',
            'CAMMCzo5YL8w4VFF8KVHrK22GGUsp5VTaW7grrKgrWqK': 'Raydium CLMM',
            'srmqPvymJeFKQ4zGQed1GFppgkRHL9kaELCbyksJtPX': 'Serum V3',
            '6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P': 'Pump.fun',
        }
        
        #Store transaction data
        self.bot_txs = []
        self.target_txs = []
        self.trades = []
      
    
    def analyze_wallet(self, limit: int = 1000):
        """
        Main analysis function - orchestrates fetching, matching, and analyzing trades

        Args:
            limit: API request limit per call

        Returns:
            DataFrame containing matched trades with P/L calculations
        """
        
        print(f"🚀 Analyzing Solana Copy-Trading Bot")
        print(f"   Bot Wallet: {self.main_wallet}")
        print("=" * 80)
        
        #Fetch bot trades
        self.bot_txs = self._fetch_trades(self.main_wallet, limit=limit)
        
        #Match trades for P/L
        print(f"\n💰 Matching trades for P/L calculation out of {len(self.bot_txs)} txs...")
        self.trades = self._match_trades_for_pnl(self.bot_txs)
        print(f"   Matched {len(self.trades)} trade pairs")
        
        #Convert to DataFrame
        if self.trades:
            self.trades_df = pd.DataFrame(self.trades)
        else:
            self.trades_df = pd.DataFrame()
        
        #Calculate latency if target wallet provided
        if self.target_wallet:
            print(f"\n⚡ Fetching target wallet trades...")
            target_txs = self._fetch_trades(self.target_wallet, limit)

            print("📊 Calculating copy latency...")
            latency_data = self._calculate_latency(self.bot_txs, target_txs)

            if latency_data:
                self.latency_df = pd.DataFrame(latency_data)
                print(f"   Calculated latency for {len(latency_data)} trades")
            else:
                self.latency_df = pd.DataFrame()
        else:
            self.latency_df = pd.DataFrame()

        #Filter to matched trades only if requested
        if self.filter_to_matched_only and self.target_wallet and not self.latency_df.empty and not self.trades_df.empty:
            original_count = len(self.trades_df)

            #Get set of matched token symbols from latency data
            matched_tokens = set(self.latency_df['token'].unique())

            #Debug: Show what we're filtering
            print(f"\n🔍 DEBUG: Matched tokens from latency: {matched_tokens}")
            print(f"🔍 DEBUG: Unique tokens in trades_df: {set(self.trades_df['token'].unique())}")

            #Filter trades_df to only include tokens that were matched
            self.trades_df = self.trades_df[self.trades_df['token'].isin(matched_tokens)].copy()

            filtered_count = len(self.trades_df)

            if filtered_count == 0:
                print(f"\n⚠️ WARNING: filter_to_matched_only removed all trades!")
                print(f"   This might indicate a token symbol mismatch between latency matching and trade matching.")
                print(f"   Keeping all {original_count} trades for analysis.")
                # Reload the original trades_df
                #self.trades_df = pd.DataFrame(self.trades)
            else:
                print(f"\n🔍 Filtered to Matched Trades Only:")
                print(f"   Kept {filtered_count} of {original_count} trades that matched with target wallet")
                print(f"   Excluded {original_count - filtered_count} unmatched trades")

        #filter outliers
        if (self.filter_outliers):
            self._filter_outliers_from_trades()

        return self.trades_df
    
    def generate_report(self):
        """
        Generate comprehensive analysis report with statistics and metrics

        Delegates to TradingReporter class for report generation
        """
        reporter = TradingReporter(self.main_wallet, self.target_wallet)
        reporter.generate_report(self.trades_df, self.latency_df, len(self.bot_txs))
    
    def plot_results(self, figsize=(20, 14), save_plots=False):
        """
        Create visualizations with tabbed interface for Jupyter notebooks

        Args:
            figsize: Tuple of (width, height) for figure size in inches
            save_plots: If True, save plots as PNG files to ./plots/ directory
        """
        plotter = TradingPlotter(self.main_wallet, self.target_wallet)
        plotter.plot_results(self.trades_df, self.latency_df, figsize, save_plots)


    #=============================================================================================================
     
    def _get_cached_trade_results(self, wallet: str) -> bool:
        """
        Load previously cached trade data from JSON file

        Args:
            wallet: Wallet address used as cache file name

        Returns:
            True if cache loaded successfully, False otherwise
        """ 
        cache_file = self._get_cache_file_name(wallet)

        print(f"Checking for  {cache_file}")
        if os.path.exists(cache_file):
            print(f"📂 Loading cached trades from {cache_file}")
            try:
                with open(cache_file, 'r') as f:
                    self.bot_txs = json.load(f)
                print(f"   Loaded {len(self.bot_txs)} cached trades")
                return True
            except Exception as e:
                print(f"   Error loading cache: {e}, fetching fresh data...")

        return False

    def _write_to_trades_cache(self, wallet: str):
        """
        Save trade data to JSON cache file

        Args:
            wallet: Wallet address used as cache file name
        """ 
        cache_file = self._get_cache_file_name(wallet)

        try:
            with open(cache_file, 'w') as f:
                json.dump(self.bot_txs, f, indent=2)
            print(f"💾 Cached {len(self.bot_txs)} trades to {cache_file}")
        except Exception as e:
            print(f"   Warning: Could not write cache file: {e}")
    
    def _get_cache_file_name(self, wallet: str) -> str: 
        return f"./cached_results/{wallet}.json"

    def _fetch_trades(self, wallet: str, limit: int = 100) -> List[Dict]:
        """
        Fetch trades for a wallet, using cache if available or fetching fresh data

        Args:
            wallet: Wallet address to fetch trades for
            limit: API request limit per call
        """
        # Check for cached data
        if (self.use_cache):
            print('LOOKING FOR CACHE');
            if not self._get_cached_trade_results(wallet):
                # Fetch fresh data
                self._fetch_trades_raw(self.main_wallet, limit)

                # Write to cache file
                print('WRITING TO CACHE');
                self._write_to_trades_cache(wallet)
        else: 
            # Fetch fresh data
            self._fetch_trades_raw(self.main_wallet, limit)

        return self.bot_txs

    def _fetch_trades_raw(self, wallet: str, limit: int = 1000): 
        # Fetch fresh data
        self.bot_txs = self._fetch_trades_helius(self.main_wallet, limit)

    def _fetch_trades_helius(self, wallet: str, limit: int = 1000, include_transfers: bool = False) -> List[Dict]:
        """
        Fetch and parse trades using Helius API (more reliable than basic RPC)

        Args:
            wallet: Wallet address to fetch trades for
            limit: API request limit per call
            include_transfers: If True, also fetch token transfers to track complete position history

        Returns:
            List of dictionaries containing parsed trade data
        """

        print(f"🔍 Fetching trades via Helius for {wallet[:8]}...{wallet[-6:]}")
        if include_transfers:
            print(f"   Including token transfers for complete position tracking")

        url = f"{self.helius_url}/addresses/{wallet}/transactions"
        trades = []
        count = 0

        #before = '2Bx48yAZTTR4RUUshm9EpYbYXhfouh3aVNy3p57EVe8GUTypiXPcxnmZXFuso2w34UUuNLfLzseURhFzLzWkddND'
        #before = '26zhCktvwtkTVj77V6svRDvPnzvEPiQWoP2U27TaibYejDdyDyk5eU2emgsSaHAGBQR9D49nWtAcvUKKUAWFq65r'
        before = ''

        while (count < limit):
            params = {
                'api-key': self.helius_api_key,
                #'limit': limit,
                'before': before,
            }

            # Only filter for SWAP if we're not including transfers
            if not include_transfers:
                params['type'] = 'SWAP'  # Filter for swaps only
            print(before)
            
            #try:
            if (True):
                response = requests.get(url, params=params)
                #print(url)
                #print(params)
                #print(response)
                data = response.json()
                if (len(data) == 0):
                    break
                
                for tx in data:
                    count = count + 1

                    if type(tx) is str:
                        print(f"TX IS A STR: {tx}")
                        continue

                    tx_type = tx.get('type')

                    # Process both SWAP and TRANSFER transactions
                    if not type(tx) is str and tx_type in ['SWAP', 'TRANSFER']:
                        #Get token transfers
                        token_transfers = tx.get('tokenTransfers', [])

                        #Debug: print first transaction structure to see available fields
                        if count == 1:
                            print("\n=== DEBUG: First transaction structure ===")
                            print(json.dumps(tx, indent=2))
                            print("=== Token transfers ===")
                            for i, transfer in enumerate(token_transfers):
                                print(f"Transfer {i}: {json.dumps(transfer, indent=2)}")
                            print("==========================================\n")

                        #Debug: Print detailed token amount info for first 5 trades
                        if count <= 5:
                            print(f"\n--- DEBUG Trade #{count} (Sig: {tx.get('signature', 'N/A')[:16]}) ---")
                            print(f"Transaction type: {tx.get('type')}")
                            print(f"Number of token transfers: {len(token_transfers)}")
                            for i, transfer in enumerate(token_transfers):
                                print(f"\nTransfer #{i}:")
                                print(f"  Mint: {transfer.get('mint', 'N/A')[:16]}...")
                                print(f"  From: {transfer.get('fromUserAccount', 'N/A')[:16]}...")
                                print(f"  To: {transfer.get('toUserAccount', 'N/A')[:16]}...")
                                print(f"  tokenAmount (UI): {transfer.get('tokenAmount', 'N/A')}")
                                print(f"  decimals: {transfer.get('decimals', 'N/A')}")
                                #Check for raw amount if available
                                if 'rawTokenAmount' in transfer:
                                    print(f"  rawTokenAmount: {transfer.get('rawTokenAmount')}")
                                    raw = transfer.get('rawTokenAmount')
                                    decimals = transfer.get('decimals', 9)
                                    calculated_ui = raw / (10 ** decimals)
                                    print(f"  Calculated UI amount: {calculated_ui}")
                                print(f"  Direction: {'OUT from wallet' if transfer.get('fromUserAccount') == wallet else 'IN to wallet'}")
                            print(f"--- End Trade #{count} Debug ---\n")

                        #Helius provides token info - need to identify which token is going out (spent) vs coming in (received)
                        #Look at 'fromUserAccount' to determine direction relative to the wallet
                        #IMPORTANT: Sum all transfers of the same token going out (e.g., SOL to pool + fees)
                        token_in_by_mint = {}  # {mint: total_amount}
                        token_out_by_mint = {}  # {mint: {amount, symbol}}

                        for transfer in token_transfers:
                            mint = transfer.get('mint')
                            amount = transfer.get('tokenAmount', 0)
                            symbol = transfer.get('tokenSymbol', mint[:8] if mint else 'Unknown')

                            # If fromUserAccount matches our wallet, this token is going OUT (token_in)
                            if transfer.get('fromUserAccount') == wallet:
                                if mint not in token_in_by_mint:
                                    token_in_by_mint[mint] = {'amount': 0, 'symbol': symbol}
                                token_in_by_mint[mint]['amount'] += amount

                            # If toUserAccount matches our wallet, this token is coming IN (token_out)
                            elif transfer.get('toUserAccount') == wallet:
                                if mint not in token_out_by_mint:
                                    token_out_by_mint[mint] = {'amount': 0, 'symbol': symbol}
                                token_out_by_mint[mint]['amount'] += amount

                        # Handle TRANSFER vs SWAP differently
                        if tx_type == 'TRANSFER':
                            # For transfers, we only care about tokens coming IN
                            if not token_out_by_mint:
                                continue

                            # Get the transferred token
                            token_out_mint = max(token_out_by_mint.items(), key=lambda x: x[1]['amount'])[0]
                            token_out_data = {
                                'mint': token_out_mint,
                                'tokenAmount': token_out_by_mint[token_out_mint]['amount'],
                                'tokenSymbol': token_out_by_mint[token_out_mint]['symbol']
                            }

                            # For transfers, we mark token_in as 'TRANSFER' to indicate we need to look up the price
                            trade = {
                                'signature': tx.get('signature'),
                                'timestamp': tx.get('timestamp'),
                                'slot': tx.get('slot'),
                                'token_in': 'TRANSFER',  # Special marker
                                'token_in_symbol': 'TRANSFER',
                                'token_in_amount': 0,  # Will be calculated from market price
                                'token_out': token_out_data.get('mint', ''),
                                'token_out_symbol': token_out_data.get('tokenSymbol', token_out_data.get('mint', 'Unknown')[:8] if token_out_data.get('mint') else 'Unknown'),
                                'token_out_amount': token_out_data.get('tokenAmount', 0),
                                'fee': tx.get('fee', 0) / 1e9,  # Convert to SOL
                                'success': tx.get('transactionError') is None,
                                'is_transfer': True,
                                'from_account': token_transfers[0].get('fromUserAccount', 'Unknown') if token_transfers else 'Unknown'
                            }
                        else:
                            # SWAP logic (original code)
                            # Skip if we couldn't identify both sides of the swap
                            if not token_in_by_mint or not token_out_by_mint:
                                continue

                            # Identify the main swap pair (largest amounts)
                            # Token IN: what we spent (should be only one type, e.g., SOL)
                            # Token OUT: what we received (the token we're buying)
                            token_in_mint = max(token_in_by_mint.items(), key=lambda x: x[1]['amount'])[0]
                            token_out_mint = max(token_out_by_mint.items(), key=lambda x: x[1]['amount'])[0]

                            token_in_data = {
                                'mint': token_in_mint,
                                'tokenAmount': token_in_by_mint[token_in_mint]['amount'],
                                'tokenSymbol': token_in_by_mint[token_in_mint]['symbol']
                            }
                            token_out_data = {
                                'mint': token_out_mint,
                                'tokenAmount': token_out_by_mint[token_out_mint]['amount'],
                                'tokenSymbol': token_out_by_mint[token_out_mint]['symbol']
                            }

                            #Extract symbols from token transfers - Helius may provide this as 'tokenSymbol' or in tokenStandard
                            #If not available, we'll need to fetch it separately
                            trade = {
                                'signature': tx.get('signature'),
                                'timestamp': tx.get('timestamp'),
                                'slot': tx.get('slot'),
                                'token_in': token_in_data.get('mint', ''),
                                'token_in_symbol': token_in_data.get('tokenSymbol', token_in_data.get('mint', 'Unknown')[:8] if token_in_data.get('mint') else 'Unknown'),
                                'token_in_amount': abs(token_in_data.get('tokenAmount', 0)),
                                'token_out': token_out_data.get('mint', ''),
                                'token_out_symbol': token_out_data.get('tokenSymbol', token_out_data.get('mint', 'Unknown')[:8] if token_out_data.get('mint') else 'Unknown'),
                                'token_out_amount': token_out_data.get('tokenAmount', 0),
                                'fee': tx.get('fee', 0) / 1e9,  #Convert to SOL
                                'success': tx.get('transactionError') is None,
                                'is_transfer': False
                            }

                        # Sanity check: token_in and token_out should be different
                        if trade['token_in'] == trade['token_out']:
                            print(f"⚠️ Skipping invalid swap with same token: {trade['token_in_symbol']}")
                            print(f"   Signature: {tx.get('signature')}")
                            continue

                        #Debug: Show parsed trade for first 5 trades
                        if count <= 5:
                            print(f"\n=== PARSED TRADE #{count} ===")
                            print(f"Signature: {trade['signature'][:16]}...")
                            print(f"Token IN:  {trade['token_in_amount']:.8f} {trade['token_in_symbol']}")
                            print(f"Token OUT: {trade['token_out_amount']:.8f} {trade['token_out_symbol']}")
                            print(f"Fee: {trade['fee']:.6f} SOL")

                            #Calculate implied exchange rate
                            if trade['token_in_amount'] > 0 and trade['token_out_amount'] > 0:
                                rate = trade['token_out_amount'] / trade['token_in_amount']
                                print(f"Exchange rate: 1 {trade['token_in_symbol']} = {rate:.8f} {trade['token_out_symbol']}")
                            print(f"=========================\n")

                        trades.append(trade)
                        before = tx.get('signature')
                
                print(f"   Found {len(trades)} trades out of {count})")
            
        return trades
    
    def _match_trades_for_pnl(self, trades: List[Dict]) -> List[Dict]:
        """
        Match buy and sell trades using FIFO to calculate profit/loss
        NOW USES SIMPLE TOKEN FLOW APPROACH (from POC)

        Args:
            trades: List of raw trade dictionaries from transaction parsing

        Returns:
            List of matched trade pairs with P/L calculations
        """
        print('Match buy and sell trades to calculate P/L (using POC method)')

        matched = []
        token_positions = {}
        token_sell_stats = {}  # Track sell behavior per token
        
        #Sort trades by timestamp
        trades_sorted = sorted(trades, key=lambda x: x.get('timestamp', 0))
        print(f'sorted trades: {len(trades_sorted)}')
        
        for trade in trades_sorted:
            #Skip trades where token_in and token_out are the same (invalid/malformed)
            if trade['token_in'] == trade['token_out']:
                print(f"⚠️ Skipping invalid trade: same token in/out ({trade['token_in_symbol']})")
                continue

            # Skip transfers - only process actual swaps for P&L
            is_transfer = trade.get('is_transfer', False)
            if is_transfer:
                print(f"   ⏭️  SKIPPING TRANSFER for P&L: {trade['token_out_amount']:.2f} {trade['token_out_symbol']} from {trade.get('from_account', 'Unknown')[:16]}...")
                continue

            #Determine if this is a buy or sell
            #Simplified: if SOL/USDC is going out, it's a buy of the other token
            print(f'token in: {trade['token_in_symbol']}')
            print(f'token out: {trade['token_out_symbol']}')

            if True:  # Original SWAP logic only
                # SWAP logic (original)
                is_stablecoin_out = trade['token_in_symbol'] in ['USDC', 'USDT', 'SOL', 'So111111']

                if is_stablecoin_out:
                    #Buying token_out
                    token = trade['token_out']
                    token_symbol = trade['token_out_symbol']

                    if token not in token_positions:
                        token_positions[token] = {
                            'symbol': token_symbol,
                            'buys': [],
                            'sells': []
                        }

                    token_positions[token]['buys'].append({
                        'signature': trade['signature'],
                        'timestamp': trade['timestamp'],
                        'slot': trade['slot'],
                        'amount': trade['token_out_amount'],
                        'cost': trade['token_in_amount'],
                        'cost_token': trade['token_in_symbol'],
                        'is_transfer': False
                    })
                else:
                    #Selling token_in
                    token = trade['token_in']
                    token_symbol = trade['token_in_symbol']
                    print(token_symbol)

                    if token not in token_positions:
                        token_positions[token] = {
                            'symbol': token_symbol,
                            'buys': [],
                            'sells': []
                        }

                    token_positions[token]['sells'].append({
                        'signature': trade['signature'],
                        'timestamp': trade['timestamp'],
                        'slot': trade['slot'],
                        'amount': trade['token_in_amount'],
                        'proceeds': trade['token_out_amount'],
                        'proceeds_token': trade['token_out_symbol']
                    })

                    print(len(token_positions))
        
        # Debug: Show summary of buys and sells before matching
        print(f"\n📊 Trade Position Summary:")
        print(f"   Unique tokens: {len(token_positions)}")
        total_buys = sum(len(data['buys']) for data in token_positions.values())
        total_sells = sum(len(data['sells']) for data in token_positions.values())
        print(f"   Total buys:  {total_buys}")
        print(f"   Total sells: {total_sells}")

        for token, data in token_positions.items():
            print(f"\n   Token: {data['symbol']}")
            print(f"     Buys:  {len(data['buys'])}")
            print(f"     Sells: {len(data['sells'])}")

        #Calculate buy and sell statistics per token before matching
        for token, data in token_positions.items():
            buys = data['buys']
            sells = data['sells']

            # Buy statistics
            if buys:
                buy_amounts = [b['amount'] for b in buys]
                total_bought = sum(buy_amounts)
                largest_buy = max(buy_amounts) if buy_amounts else 0

                token_sell_stats[token] = {
                    'num_buys': len(buys),
                    'largest_buy_pct': (largest_buy / total_bought * 100) if total_bought > 0 else 0
                }
            else:
                token_sell_stats[token] = {
                    'num_buys': 0,
                    'largest_buy_pct': 0
                }

            # Sell statistics
            if sells:
                sell_amounts = [s['amount'] for s in sells]
                total_sold = sum(sell_amounts)
                largest_sell = max(sell_amounts) if sell_amounts else 0

                token_sell_stats[token]['num_sells'] = len(sells)
                token_sell_stats[token]['largest_sell_pct'] = (largest_sell / total_sold * 100) if total_sold > 0 else 0
            else:
                token_sell_stats[token]['num_sells'] = 0
                token_sell_stats[token]['largest_sell_pct'] = 0

        # Define acceptable base currencies that can be compared against each other
        ACCEPTABLE_BASE_CURRENCIES = {'SOL', 'USDC', 'USDT', 'So111111', 'WSOL'}

        #Match buys and sells (FIFO)
        for token, data in token_positions.items():
            buys = data['buys']
            sells = data['sells']

            for sell in sells:
                if buys:
                    buy = buys[0]  #FIFO

                    buy_currency = buy.get('cost_token')
                    sell_currency = sell.get('proceeds_token')

                    # Allow matching if:
                    # 1. Same currency (original behavior)
                    # 2. Both are acceptable base currencies (SOL/stablecoins)
                    currencies_match = buy_currency == sell_currency
                    both_acceptable = (buy_currency in ACCEPTABLE_BASE_CURRENCIES and
                                      sell_currency in ACCEPTABLE_BASE_CURRENCIES)

                    if not (currencies_match or both_acceptable):
                        print(f"⚠️ Skipping match for {data['symbol']}: incompatible currencies (bought with {buy_currency}, sold for {sell_currency})")
                        buys.pop(0)  #Remove unmatched buy
                        continue

                    #Simple P/L calculation
                    hold_time = sell['timestamp'] - buy['timestamp']
                    slot_diff = sell['slot'] - buy['slot']

                    #Calculate P/L (now works for cross-currency if both are base currencies)
                    pnl_pct = 0
                    profit = 0
                    actual_amount_traded = min(buy['amount'], sell['amount'])

                    if buy['amount'] > 0:
                        #Calculate cost per token and proceeds per token
                        cost_per_token = buy['cost'] / buy['amount']
                        proceeds_per_token = sell['proceeds'] / sell['amount']

                        #Calculate profit based on the actual amount traded
                        profit = (proceeds_per_token - cost_per_token) * actual_amount_traded

                        #Calculate percentage
                        if cost_per_token > 0:
                            pnl_pct = ((proceeds_per_token / cost_per_token) - 1) * 100

                    # Add buy and sell statistics for this token
                    stats = token_sell_stats.get(token, {
                        'num_buys': 0, 'largest_buy_pct': 0,
                        'num_sells': 0, 'largest_sell_pct': 0
                    })

                    trade_match = {
                        'token': data['symbol'],
                        'token_address': token, #[:8] + '...' + token[-6:],
                        'buy_sig': buy['signature'], #[:8] + '...',
                        'sell_sig': sell['signature'], #[:8] + '...',
                        'buy_time': datetime.fromtimestamp(buy['timestamp']),
                        'sell_time': datetime.fromtimestamp(sell['timestamp']),
                        'buy_slot': buy['slot'],
                        'sell_slot': sell['slot'],
                        'slot_diff': slot_diff,
                        'hold_seconds': hold_time,
                        'hold_days': hold_time / 86400,
                        'buy_amount': buy['amount'],
                        'sell_amount': sell['amount'],
                        'amount_traded': actual_amount_traded,
                        'cost': buy['cost'],
                        'proceeds': sell['proceeds'],
                        'cost_per_token': buy['cost'] / buy['amount'] if buy['amount'] > 0 else 0,
                        'proceeds_per_token': sell['proceeds'] / sell['amount'] if sell['amount'] > 0 else 0,
                        'profit': profit,
                        'cost_token': buy.get('cost_token', 'Unknown'),
                        'proceeds_token': sell.get('proceeds_token', 'Unknown'),
                        'pnl_pct': pnl_pct,
                        'num_buys': stats['num_buys'],
                        'largest_buy_pct': stats['largest_buy_pct'],
                        'num_sells': stats['num_sells'],
                        'largest_sell_pct': stats['largest_sell_pct']
                    }

                    #Debug: Flag trades with suspiciously high PnL
                    if len(matched) < 5 or abs(pnl_pct) > 1000:
                        print(f"\n🔍 DEBUG: PnL Calculation for {data['symbol']}")
                        print(f"  Buy:  {buy['amount']:.8f} tokens for {buy['cost']:.8f} {buy.get('cost_token')}")
                        print(f"  Sell: {sell['amount']:.8f} tokens for {sell['proceeds']:.8f} {sell.get('proceeds_token')}")
                        print(f"  Cost per token: {cost_per_token:.15f} {buy.get('cost_token')}")
                        print(f"  Proceeds per token: {proceeds_per_token:.15f} {sell.get('proceeds_token')}")
                        print(f"  Profit: {profit:.8f} {sell.get('proceeds_token')}")
                        print(f"  P/L %: {pnl_pct:.2f}%")
                        print(f"  Buy Sig: {buy['signature']}")
                        print(f"  Sell Sig: {sell['signature']}")
                        print(f"  🔗 Verify Buy:  {get_solscan_url(buy['signature'])}")
                        print(f"  🔗 Verify Sell: {get_solscan_url(sell['signature'])}")
                        if abs(pnl_pct) > 1000:
                            print(f"  ⚠️ WARNING: PnL exceeds 1000%! Verify amounts on Solscan.")
                        print()

                    matched.append(trade_match)

                    #Print formatted trade details
                    print_trade_match(trade_match, len(matched))
                    
                    buys.pop(0)  #Remove matched buy
        
        return matched
    
    def _calculate_latency(self, bot_trades: List[Dict], target_trades: List[Dict]) -> List[Dict]:
        """
        Calculate latency between bot and target wallet copy-trades

        Args:
            bot_trades: List of bot wallet trades
            target_trades: List of target wallet trades being copied

        Returns:
            List of dictionaries with latency metrics (slot and time differences)
        """

        latency_data = []

        # Maximum time window for matching trades (5 minutes = 300 seconds)
        MAX_TIME_WINDOW = 300

        #Create lookup by token with trade direction
        target_by_token_direction = {}
        for trade in target_trades:
            # Determine trade direction: buying token_out, selling token_in
            token_bought = trade.get('token_out', '')
            token_sold = trade.get('token_in', '')

            # Key format: "token_address:BUY" or "token_address:SELL"
            buy_key = f"{token_bought}:BUY"
            sell_key = f"{token_sold}:SELL"

            if buy_key not in target_by_token_direction:
                target_by_token_direction[buy_key] = []
            if sell_key not in target_by_token_direction:
                target_by_token_direction[sell_key] = []

            target_by_token_direction[buy_key].append(trade)
            target_by_token_direction[sell_key].append(trade)

        #Match bot trades to target trades
        for bot_trade in bot_trades:
            token_bought = bot_trade.get('token_out', '')
            token_sold = bot_trade.get('token_in', '')

            # Try to match as a buy first
            buy_key = f"{token_bought}:BUY"
            sell_key = f"{token_sold}:SELL"

            matched = False

            # Try matching as a BUY (bot buying token_out)
            if buy_key in target_by_token_direction:
                #Find closest preceding target trade within time window
                # IMPORTANT: Filter by slot, not timestamp, to ensure target came first
                target_candidates = [
                    t for t in target_by_token_direction[buy_key]
                    if t['slot'] < bot_trade['slot']  # Target must be in earlier slot
                    and (bot_trade['timestamp'] - t['timestamp']) <= MAX_TIME_WINDOW
                ]

                if target_candidates:
                    # Find the closest match (by slot, which is most accurate)
                    target_trade = max(target_candidates, key=lambda x: x['slot'])

                    slot_latency = bot_trade['slot'] - target_trade['slot']
                    time_latency = bot_trade['timestamp'] - target_trade['timestamp']

                    print(f"BUY MATCH - SLOT LATENCY for {bot_trade.get('token_out_symbol', 'Unknown')}: {slot_latency} slots ({time_latency}s)")

                    latency_data.append({
                        'token': bot_trade.get('token_out_symbol', 'Unknown'),
                        'direction': 'BUY',
                        'bot_sig': bot_trade['signature'][:8] + '...',
                        'target_sig': target_trade['signature'][:8] + '...',
                        'bot_slot': bot_trade['slot'],
                        'target_slot': target_trade['slot'],
                        'slot_latency': slot_latency,
                        'time_latency': time_latency,
                        'time_latency_ms': time_latency * 1000
                    })
                    matched = True

            # Try matching as a SELL (bot selling token_in)
            if not matched and sell_key in target_by_token_direction:
                # IMPORTANT: Filter by slot, not timestamp, to ensure target came first
                target_candidates = [
                    t for t in target_by_token_direction[sell_key]
                    if t['slot'] < bot_trade['slot']  # Target must be in earlier slot
                    and (bot_trade['timestamp'] - t['timestamp']) <= MAX_TIME_WINDOW
                ]

                if target_candidates:
                    # Find the closest match (by slot, which is most accurate)
                    target_trade = max(target_candidates, key=lambda x: x['slot'])

                    slot_latency = bot_trade['slot'] - target_trade['slot']
                    time_latency = bot_trade['timestamp'] - target_trade['timestamp']

                    print(f"SELL MATCH - SLOT LATENCY for {bot_trade.get('token_in_symbol', 'Unknown')}: {slot_latency} slots ({time_latency}s)")

                    latency_data.append({
                        'token': bot_trade.get('token_in_symbol', 'Unknown'),
                        'direction': 'SELL',
                        'bot_sig': bot_trade['signature'][:8] + '...',
                        'target_sig': target_trade['signature'][:8] + '...',
                        'bot_slot': bot_trade['slot'],
                        'target_slot': target_trade['slot'],
                        'slot_latency': slot_latency,
                        'time_latency': time_latency,
                        'time_latency_ms': time_latency * 1000
                    })
                    matched = True

            if not matched:
                print(f'NO MATCH FOUND for {bot_trade.get("token_out_symbol", "?")} / {bot_trade.get("token_in_symbol", "?")}')

        return latency_data
    
    def _filter_outliers_from_trades(self):
        """
        Filter extreme outliers from trades based on P/L percentage thresholds

        Removes trades outside the range defined by MIN_PNL_PCT and MAX_PNL_PCT
        to prevent skewed statistics from data errors or extreme edge cases
        """

        #Filter outliers based on P/L percentage
        original_count = len(self.trades_df)
        filtered_df = self.trades_df[
            (self.trades_df['pnl_pct'] >= self.MIN_PNL_PCT) &
            (self.trades_df['pnl_pct'] <= self.MAX_PNL_PCT)
        ].copy()

        outliers_removed = original_count - len(filtered_df)

        if outliers_removed > 0:
            print(f"\n🔍 Outlier Filtering:")
            print(f"   Excluded {outliers_removed} trades outside range [{self.MIN_PNL_PCT}%, {self.MAX_PNL_PCT}%]")
            print(f"   Analyzing {len(filtered_df)} of {original_count} total trades")

            #Show excluded outliers summary
            outliers = self.trades_df[
                (self.trades_df['pnl_pct'] < self.MIN_PNL_PCT) |
                (self.trades_df['pnl_pct'] > self.MAX_PNL_PCT)
            ]
            if len(outliers) > 0:
                print(f"   Excluded outliers range: {outliers['pnl_pct'].min():.1f}% to {outliers['pnl_pct'].max():.1f}%")

        #Use filtered data for statistics
        stats_df = filtered_df if len(filtered_df) > 0 else self.trades_df
        self.trades_df = stats_df


def analyze_transaction(signature: str,
                       helius_api_key: str = None,
                       rpc_url: str = "https://api.mainnet-beta.solana.com") -> Dict:
    """
    Analyze a single transaction signature to identify token trades

    Args:
        signature: Transaction signature hash to analyze
        helius_api_key: Optional Helius API key for enhanced data
        rpc_url: Solana RPC endpoint

    Returns:
        Dictionary containing detailed trade information:
        - success: Whether the transaction was successful
        - timestamp: Transaction timestamp
        - slot: Transaction slot number
        - participants: List of involved addresses
        - swaps: List of token swaps with detailed information
        - raw_tx: Full transaction data for further analysis
    """

    print(f"\n{'='*80}")
    print(f"🔍 TRANSACTION ANALYSIS")
    print(f"{'='*80}")
    print(f"Signature: {signature}")
    print(f"{'='*80}\n")

    # Determine which method to use
    result = _analyze_transaction_helius(signature, helius_api_key)

    # Print formatted results
    _print_transaction_analysis(result)

    return result


def _get_slot_leader(slot: int, rpc_url: str = "https://api.mainnet-beta.solana.com") -> str:
    """
    Get the slot leader (validator) for a specific slot

    NOTE: This only works for recent slots in the current or recent epochs.
    Historical slot leader information is not available via RPC as Solana
    only maintains leader schedules for current/recent epochs.

    Args:
        slot: Slot number to query
        rpc_url: Solana RPC endpoint

    Returns:
        Validator address (public key) that was the slot leader, or None if unavailable
    """
    try:
        # First, get the current epoch info to determine if this slot is queryable
        epoch_payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getEpochInfo"
        }

        response = requests.post(rpc_url, json=epoch_payload, timeout=10)
        epoch_data = response.json()

        if 'result' not in epoch_data:
            return None

        current_slot = epoch_data['result']['absoluteSlot']
        slots_in_epoch = epoch_data['result']['slotsInEpoch']
        current_epoch = epoch_data['result']['epoch']

        # Calculate which epoch the target slot belongs to
        # Approximate epoch calculation (epochs are roughly 432,000 slots)
        target_epoch = current_epoch - ((current_slot - slot) // slots_in_epoch)

        # Only try to get leader schedule if within reasonable range (current epoch)
        # Leader schedules are typically only available for current epoch
        if abs(current_epoch - target_epoch) > 1:
            # Slot is too old or too far in future, leader schedule not available
            return None

        # Get leader schedule for the target epoch
        schedule_payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getLeaderSchedule",
            "params": [
                slot,  # Use the slot to get the epoch's schedule
                {"commitment": "finalized"}
            ]
        }

        response = requests.post(rpc_url, json=schedule_payload, timeout=10)
        schedule_data = response.json()

        if 'result' not in schedule_data or not schedule_data['result']:
            return None

        # Calculate the epoch start slot
        slot_index_in_epoch = epoch_data['result']['slotIndex']
        epoch_start_slot = current_slot - slot_index_in_epoch

        # If querying a different epoch, adjust the epoch start
        if target_epoch != current_epoch:
            epoch_start_slot += (current_epoch - target_epoch) * slots_in_epoch

        # Calculate slot index within its epoch
        target_slot_index = slot - epoch_start_slot

        # Find the validator that was assigned this slot
        for validator, assigned_slots in schedule_data['result'].items():
            if target_slot_index in assigned_slots:
                return validator

        return None

    except Exception as e:
        # Silently fail for slot leader lookups as they often fail for historical data
        return None


def _analyze_transaction_helius(signature: str, helius_api_key: str) -> Dict:
    """
    Analyze transaction using Helius API (preferred method)

    Args:
        signature: Transaction signature hash
        helius_api_key: Helius API key

    Returns:
        Dictionary with transaction analysis
    """

    print("📡 Fetching transaction via Helius API...")

    url = f"https://api.helius.xyz/v0/transactions?api-key={helius_api_key}"
    params = {
        'transactions': [signature]
    }

    try:
        response = requests.post(url, json=params)
        data = response.json()

        if not data or len(data) == 0:
            return {
                'success': False,
                'error': 'Transaction not found',
                'signature': signature
            }

        tx = data[0]

        # Extract basic info
        slot = tx.get('slot')
        result = {
            'success': tx.get('transactionError') is None,
            'signature': signature,
            'timestamp': tx.get('timestamp'),
            'datetime': datetime.fromtimestamp(tx.get('timestamp', 0)),
            'slot': slot,
            'fee': tx.get('fee', 0) / 1e9,
            'type': tx.get('type'),
            'participants': [],
            'swaps': [],
            'raw_tx': tx
        }

        # Fetch slot leader if slot is available
        if slot is not None:
            try:
                slot_leader = _get_slot_leader(slot)
                if slot_leader:
                    result['slot_leader'] = slot_leader
            except Exception as e:
                print(f"⚠️ Could not fetch slot leader: {str(e)}")
                result['slot_leader'] = None

        # Extract token transfers
        token_transfers = tx.get('tokenTransfers', [])

        if not token_transfers:
            result['error'] = 'No token transfers found in transaction'
            return result

        # Build participant list
        participants = set()
        for transfer in token_transfers:
            if transfer.get('fromUserAccount'):
                participants.add(transfer['fromUserAccount'])
            if transfer.get('toUserAccount'):
                participants.add(transfer['toUserAccount'])
        result['participants'] = list(participants)

        # Analyze swaps by grouping transfers
        # Group by participant to identify their trades
        for participant in participants:
            tokens_out = []  # Tokens sent by participant
            tokens_in = []   # Tokens received by participant

            for transfer in token_transfers:
                mint = transfer.get('mint')
                amount = transfer.get('tokenAmount', 0)
                symbol = transfer.get('tokenSymbol', mint[:8] if mint else 'Unknown')

                if transfer.get('fromUserAccount') == participant:
                    tokens_out.append({
                        'mint': mint,
                        'symbol': symbol,
                        'amount': amount
                    })
                elif transfer.get('toUserAccount') == participant:
                    tokens_in.append({
                        'mint': mint,
                        'symbol': symbol,
                        'amount': amount
                    })

            # If participant both sent and received tokens, it's a swap
            if tokens_out and tokens_in:
                # Combine multiple transfers of the same token
                tokens_out_combined = {}
                for t in tokens_out:
                    if t['mint'] not in tokens_out_combined:
                        tokens_out_combined[t['mint']] = {'symbol': t['symbol'], 'amount': 0}
                    tokens_out_combined[t['mint']]['amount'] += t['amount']

                tokens_in_combined = {}
                for t in tokens_in:
                    if t['mint'] not in tokens_in_combined:
                        tokens_in_combined[t['mint']] = {'symbol': t['symbol'], 'amount': 0}
                    tokens_in_combined[t['mint']]['amount'] += t['amount']

                swap = {
                    'trader': participant,
                    'trader_short': f"{participant[:8]}...{participant[-6:]}",
                    'tokens_sold': [
                        {
                            'mint': mint,
                            'mint_short': f"{mint[:8]}...{mint[-6:]}" if mint else 'Unknown',
                            'symbol': token_data['symbol'],
                            'amount': token_data['amount']
                        }
                        for mint, token_data in tokens_out_combined.items()
                    ],
                    'tokens_bought': [
                        {
                            'mint': mint,
                            'mint_short': f"{mint[:8]}...{mint[-6:]}" if mint else 'Unknown',
                            'symbol': token_data['symbol'],
                            'amount': token_data['amount']
                        }
                        for mint, token_data in tokens_in_combined.items()
                    ]
                }

                # Calculate exchange rates - always show in terms of SOL
                if len(swap['tokens_sold']) == 1 and len(swap['tokens_bought']) == 1:
                    sold = swap['tokens_sold'][0]
                    bought = swap['tokens_bought'][0]

                    if sold['amount'] > 0 and bought['amount'] > 0:
                        # Identify SOL (can be 'SOL', 'WSOL', or the wrapped SOL mint)
                        sol_identifiers = ['SOL', 'WSOL', 'So11111111111111111111111111111111111111112']
                        sold_is_sol = sold['symbol'] in sol_identifiers or sold['mint'] in sol_identifiers
                        bought_is_sol = bought['symbol'] in sol_identifiers or bought['mint'] in sol_identifiers

                        # Always express in terms of SOL if SOL is involved
                        if bought_is_sol:
                            # Bought SOL, sold token - show how much SOL per 1 token
                            rate = bought['amount'] / sold['amount']
                            swap['exchange_rate'] = {
                                'rate': rate,
                                'description': f"1 {sold['symbol']} = {rate:.8f} SOL"
                            }
                        elif sold_is_sol:
                            # Sold SOL, bought token - show how much SOL per 1 token
                            rate = sold['amount'] / bought['amount']
                            swap['exchange_rate'] = {
                                'rate': rate,
                                'description': f"1 {bought['symbol']} = {rate:.8f} SOL"
                            }
                        else:
                            # Neither is SOL, show default
                            swap['exchange_rate'] = {
                                'rate': bought['amount'] / sold['amount'],
                                'description': f"1 {sold['symbol']} = {bought['amount'] / sold['amount']:.8f} {bought['symbol']}"
                            }

                result['swaps'].append(swap)

        return result

    except Exception as e:
        return {
            'success': False,
            'error': f'Error fetching transaction: {str(e)}',
            'signature': signature
        }


def _print_transaction_analysis(result: Dict):
    """
    Print formatted transaction analysis results

    Args:
        result: Transaction analysis dictionary
    """

    if not result.get('success'):
        print(f"❌ Transaction Error: {result.get('error', 'Unknown error')}")
        return

    print(f"✅ Transaction Status: SUCCESS")
    print(f"📅 Timestamp: {result['datetime']}")

    slot = result.get('slot')
    if slot is not None:
        print(f"🎰 Slot: {slot}")

    slot_leader = result.get('slot_leader')
    if slot_leader:
        print(f"👑 Slot Leader: {slot_leader[:8]}...{slot_leader[-6:]}")
        print(f"   Full Address: {slot_leader}")

    print(f"💸 Fee: {result['fee']:.6f} SOL")
    if result.get('type'):
        print(f"🔖 Type: {result['type']}")

    print(f"\n{'='*80}")
    print(f"👥 PARTICIPANTS ({len(result['participants'])})")
    print(f"{'='*80}")
    for i, participant in enumerate(result['participants'], 1):
        print(f"{i}. {participant}")

    if not result['swaps']:
        print(f"\n⚠️ No swaps detected in this transaction")
        return

    print(f"\n{'='*80}")
    print(f"🔄 SWAPS DETECTED ({len(result['swaps'])})")
    print(f"{'='*80}")

    for i, swap in enumerate(result['swaps'], 1):
        print(f"\n--- Swap #{i} ---")
        print(f"Trader: {swap['trader_short']}")
        print(f"Full Address: {swap['trader']}")

        print(f"\n  📤 SOLD (What was traded away):")
        for token in swap['tokens_sold']:
            print(f"    • {token['amount']:.8f} {token['symbol']}")
            print(f"      Mint: {token['mint']}")

        print(f"\n  📥 BOUGHT (What was received):")
        for token in swap['tokens_bought']:
            print(f"    • {token['amount']:.8f} {token['symbol']}")
            print(f"      Mint: {token['mint']}")

        if 'exchange_rate' in swap:
            print(f"\n  💱 Exchange Rate:")
            print(f"    {swap['exchange_rate']['description']}")

    print(f"\n{'='*80}")
    print(f"🔗 View on Solscan: https://solscan.io/tx/{result['signature']}")
    print(f"{'='*80}\n")