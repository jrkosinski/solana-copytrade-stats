import requests
import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, List, Optional, Tuple
import json
from web3 import Web3
from IPython.display import display, HTML
import ipywidgets as widgets
from IPython.display import clear_output

#Set style for better looking plots
plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("husl")


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
                 use_cache: bool = True):
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
      
    
    def analyze_wallet(self, limit: int = 1000, max_trades: int =100):
        """
        Main analysis function - orchestrates fetching, matching, and analyzing trades

        Args:
            limit: API request limit per call
            max_trades: Maximum number of trades to fetch

        Returns:
            DataFrame containing matched trades with P/L calculations
        """
        
        print(f"🚀 Analyzing Solana Copy-Trading Bot")
        print(f"   Bot Wallet: {self.main_wallet}")
        print("=" * 80)
        
        #Fetch bot trades
        self.bot_txs = self._fetch_trades(self.main_wallet, limit, max_trades)
        
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

        if not self.trades_df.empty:

            if not self.trades_df.empty:
                print("\n📈 Overall Statistics:")
                print(f"   Total Matched Trades: {len(self.trades_df)}")
                print(f"   Trades in Analysis: {len(self.trades_df)}")
                print(f"   Unique Tokens Traded: {self.trades_df['token'].nunique()}")
                print(f"   Date Range: {self.trades_df['buy_time'].min()} to {self.trades_df['sell_time'].max()}")

                print("\n💰 Profit/Loss Statistics (Filtered):")
                print(f"   Average P/L per trade: {self.trades_df['pnl_pct'].mean():.2f}%")
                print(f"   Median P/L per trade: {self.trades_df['pnl_pct'].median():.2f}%")
                print(f"   Best Trade: {self.trades_df['pnl_pct'].max():.2f}%")
                print(f"   Worst Trade: {self.trades_df['pnl_pct'].min():.2f}%")
                print(f"   Win Rate: {(self.trades_df['pnl_pct'] > 0).mean() * 100:.1f}%")

                # Calculate and display risk metrics
                risk_metrics = self._calculate_risk_metrics()
                print("\n📊 Risk Metrics:")
                print(f"   Sharpe Ratio: {risk_metrics['sharpe_ratio']:.2f}")
                print(f"   Max Drawdown: {risk_metrics['max_drawdown']:.2f}%")
                print(f"   Max Drawdown Duration: {risk_metrics['max_drawdown_duration']:.2f} days")
                print(f"   Max Draw-up: {risk_metrics['max_drawup']:.2f}%")
                print(f"   Max Draw-up Duration: {risk_metrics['max_drawup_duration']:.2f} days")

                print("\n⏰ Hold Time Statistics:")
                print(f"   Average Hold Time: {self.trades_df['hold_days'].mean():.2f} days")
                print(f"   Median Hold Time: {self.trades_df['hold_days'].median():.2f} days")
                print(f"   Shortest Hold: {self.trades_df['hold_seconds'].min() / 60:.1f} minutes")
                print(f"   Longest Hold: {self.trades_df['hold_days'].max():.1f} days")

                print("\n📥 Entry Behavior:")
                print(f"   Average Largest Buy: {self.trades_df['largest_buy_pct'].mean():.1f}% of position")
                print(f"   Median Largest Buy: {self.trades_df['largest_buy_pct'].median():.1f}% of position")
                print(f"   Average Buys per Token: {self.trades_df['num_buys'].mean():.1f}")

                # Categorize entry behavior
                instant_buys = (self.trades_df['largest_buy_pct'] == 100).sum()
                partial_entries = ((self.trades_df['largest_buy_pct'] >= 50) & (self.trades_df['largest_buy_pct'] < 100)).sum()
                gradual_entries = (self.trades_df['largest_buy_pct'] < 50).sum()
                print(f"   Instant Buy-ins (100%): {instant_buys} ({instant_buys/len(self.trades_df)*100:.1f}%)")
                print(f"   Partial Entries (50-99%): {partial_entries} ({partial_entries/len(self.trades_df)*100:.1f}%)")
                print(f"   Gradual Entries (<50%): {gradual_entries} ({gradual_entries/len(self.trades_df)*100:.1f}%)")

                print("\n🔄 Exit Behavior:")
                print(f"   Average Largest Sell: {self.trades_df['largest_sell_pct'].mean():.1f}% of position")
                print(f"   Median Largest Sell: {self.trades_df['largest_sell_pct'].median():.1f}% of position")
                print(f"   Average Sells per Token: {self.trades_df['num_sells'].mean():.1f}")

                # Categorize exit behavior
                instant_dumps = (self.trades_df['largest_sell_pct'] == 100).sum()
                partial_exits = ((self.trades_df['largest_sell_pct'] >= 50) & (self.trades_df['largest_sell_pct'] < 100)).sum()
                gradual_exits = (self.trades_df['largest_sell_pct'] < 50).sum()
                print(f"   Instant Dumps (100%): {instant_dumps} ({instant_dumps/len(self.trades_df)*100:.1f}%)")
                print(f"   Partial Exits (50-99%): {partial_exits} ({partial_exits/len(self.trades_df)*100:.1f}%)")
                print(f"   Gradual Exits (<50%): {gradual_exits} ({gradual_exits/len(self.trades_df)*100:.1f}%)")
        else:
            print("\n⚠️ No matched trades found")
            print("   Raw transaction count:", len(self.bot_txs))
        
        if not self.latency_df.empty:
            print("\n⚡ Copy Latency Statistics:")
            print(f"   Total Matched Swaps: {len(self.latency_df)}")

            # Count by direction
            buys = len(self.latency_df[self.latency_df['direction'] == 'BUY'])
            sells = len(self.latency_df[self.latency_df['direction'] == 'SELL'])
            print(f"   Matched Buys: {buys}")
            print(f"   Matched Sells: {sells}")

            print(f"\n   Average Slot Latency: {self.latency_df['slot_latency'].mean():.1f} slots")
            print(f"   Median Slot Latency: {self.latency_df['slot_latency'].median():.0f} slots")
            print(f"   Average Time Latency: {self.latency_df['time_latency'].mean():.1f} seconds")
            print(f"   Fastest Copy: {self.latency_df['slot_latency'].min()} slots")
            print(f"   Slowest Copy: {self.latency_df['slot_latency'].max()} slots")

            #Estimate latency in milliseconds (Solana slot time ~400ms)
            avg_ms = self.latency_df['slot_latency'].mean() * 400
            print(f"   Estimated Avg Latency: ~{avg_ms:.0f}ms")

            # Detailed breakdown of matched trades
            print("\n📋 Matched Trade Details:")
            for idx, row in self.latency_df.iterrows():
                direction_emoji = "🟢" if row['direction'] == 'BUY' else "🔴"
                print(f"\n   {direction_emoji} {row['direction']} {row['token']}")
                print(f"      Bot Signature:    {row['bot_sig']}")
                print(f"      Target Signature: {row['target_sig']}")
                print(f"      Slot Latency:     {row['slot_latency']} slots ({row['time_latency']:.1f}s)")
                print(f"      Bot Slot:         {row['bot_slot']}")
                print(f"      Target Slot:      {row['target_slot']}")
    
    def plot_results(self, figsize=(20, 14), save_plots=False):
        """
        Create visualizations with tabbed interface for Jupyter notebooks

        Args:
            figsize: Tuple of (width, height) for figure size in inches
            save_plots: If True, save plots as PNG files to ./plots/ directory
        """

        if self.trades_df.empty and self.latency_df.empty:
            print("❌ No data to plot")
            return

        #Determine what data we have
        has_trades = not self.trades_df.empty
        has_latency = not self.latency_df.empty

        #Create output widgets for each tab
        graphs_output = widgets.Output()
        table_output = widgets.Output()
        behavior_output = widgets.Output()

        #Create the graphs tab
        with graphs_output:
            self._plot_graphs(has_trades, has_latency, figsize, save_plots)

        #Create the table tab
        with table_output:
            if has_trades:
                self._plot_table(save_plots)
            else:
                print("No trade data available for table")

        #Create the behavior tab
        with behavior_output:
            if has_trades:
                self._plot_entry_exit_behavior(figsize, save_plots)
            else:
                print("No trade data available for behavior analysis")

        #Create tab widget
        tab = widgets.Tab(children=[graphs_output, table_output, behavior_output])
        tab.set_title(0, 'Performance Graphs')
        tab.set_title(1, 'Trade Details')
        tab.set_title(2, 'Entry/Exit Behavior')

        #Display the tabbed interface
        display(tab)


    #=============================================================================================================
     
    def _fetch_signatures(self, wallet: str, limit: int = 1000) -> List[str]:
        """
        Fetch transaction signatures for a wallet using Solana RPC

        Args:
            wallet: Solana wallet address to fetch signatures for
            limit: Maximum number of signatures to retrieve (default: 1000)

        Returns:
            List of transaction signature strings
        """
        
        print(f"📥 Fetching signatures for {wallet[:8]}...{wallet[-6:]}")
        
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getSignaturesForAddress",
            "params": [
                wallet,
                {"limit": limit}
            ]
        }
        
        try:
            response = requests.post(self.rpc_url, json=payload)
            data = response.json()
            
            if 'result' in data:
                signatures = [sig['signature'] for sig in data['result']]
                print(f"   Found {len(signatures)} signatures")
                print(signatures[0]);
                return signatures
            else:
                print(f"   Error: {data.get('error', 'Unknown error')}")
                return []
        except Exception as e:
            print(f"   Error fetching signatures: {e}")
            return []
    
    def _fetch_transaction(self, signature: str) -> Dict:
        """
        Fetch detailed transaction data for a given signature

        Args:
            signature: Transaction signature hash

        Returns:
            Dictionary containing transaction details or empty dict on error
        """
        
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getTransaction",
            "params": [
                signature,
                {
                    "encoding": "json",
                    "maxSupportedTransactionVersion": 0
                }
            ]
        }
        
        try:
            response = requests.post(self.rpc_url, json=payload)
            data = response.json()
            return data.get('result', {})
        except:
            return {}
    
    def _parse_jupiter_swap(self, tx_data: Dict) -> Optional[Dict]:
        """
        Parse Jupiter swap details from transaction data

        Args:
            tx_data: Dictionary containing raw transaction data

        Returns:
            Dictionary with swap details (token_in, token_out, amounts, symbols) or None if not a Jupiter swap
        """
        #print("PARSE_JUPYTER_SWAP")
        
        if not tx_data or 'meta' not in tx_data:
            return None
        
        meta = tx_data['meta']
        
        #Check for Jupiter in account keys
        account_keys = tx_data.get('transaction', {}).get('message', {}).get('accountKeys', [])
        
        #Look for Jupiter program
        is_jupiter = any(
            key in ['JUP4Fb2cqiRUcaTHdrPC8h2gNsA2ETXiPDD33WcGuJB',
                   'JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4']
            for key in account_keys
        )
        
        if not is_jupiter:
            return None
        
        #Parse token balances
        pre_balances = meta.get('preTokenBalances', [])
        post_balances = meta.get('postTokenBalances', [])
        
        if not pre_balances or not post_balances:
            return None
        
        #Find token changes
        token_changes = {}
        
        for post in post_balances:
            mint = post.get('mint')
            owner = post.get('owner')
            post_amount = float(post.get('uiTokenAmount', {}).get('uiAmount', 0))
            
            #Find corresponding pre balance
            pre_amount = 0
            for pre in pre_balances:
                if pre.get('mint') == mint and pre.get('owner') == owner:
                    pre_amount = float(pre.get('uiTokenAmount', {}).get('uiAmount', 0))
                    break
            
            change = post_amount - pre_amount
            if abs(change) > 0.000001:  #Ignore dust
                token_changes[mint] = {
                    'change': change,
                    'symbol': post.get('uiTokenAmount', {}).get('symbol', 'Unknown'),
                    'decimals': post.get('uiTokenAmount', {}).get('decimals', 9)
                }
        
        #Identify swap direction
        tokens_in = {k: v for k, v in token_changes.items() if v['change'] < 0}
        tokens_out = {k: v for k, v in token_changes.items() if v['change'] > 0}
        
        if tokens_in and tokens_out:
            #Take first token pair (simplified)
            token_in = list(tokens_in.keys())[0]
            token_out = list(tokens_out.keys())[0]
            
            return {
                'token_in': token_in,
                'token_in_symbol': tokens_in[token_in]['symbol'],
                'token_in_amount': abs(tokens_in[token_in]['change']),
                'token_out': token_out,
                'token_out_symbol': tokens_out[token_out]['symbol'],
                'token_out_amount': tokens_out[token_out]['change'],
                'program': 'Jupiter'
            }
        
        return None
    
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

    def _fetch_trades(self, wallet: str, limit: int = 100, max_trades: int = 100) -> List[Dict]:
        print("FETCH TRADES")
        """
        Fetch trades for a wallet, using cache if available or fetching fresh data

        Args:
            wallet: Wallet address to fetch trades for
            limit: API request limit per call
            max_trades: Maximum number of trades to fetch
        """
        # Check for cached data
        if (self.use_cache):
            if not self._get_cached_trade_results(wallet):
                # Fetch fresh data
                self._fetch_trades_raw(self.main_wallet, limit, max_trades=max_trades)

                # Write to cache file
                self._write_to_trades_cache(wallet)
        else: 
            # Fetch fresh data
            self._fetch_trades(self.main_wallet, limit, max_trades=max_trades)

        return self.bot_txs

    def _fetch_trades_raw(self, wallet: str, limit: int = 1000, max_trades: int = 1000): 
        # Fetch fresh data
        if self.helius_api_key:
            self.bot_txs = self._fetch_trades_helius(self.main_wallet, limit, max_trades=max_trades)
        else:
            self.bot_txs = self._fetch_trades_basic(self.main_wallet, limit)

    def _fetch_trades_helius(self, wallet: str, limit: int = 1000, max_trades: int = 1000) -> List[Dict]:
        """
        Fetch and parse trades using Helius API (more reliable than basic RPC)

        Args:
            wallet: Wallet address to fetch trades for
            limit: API request limit per call
            max_trades: Maximum number of trades to fetch (0 for unlimited)

        Returns:
            List of dictionaries containing parsed trade data
        """

        print(f" FETCH TRADES HELIUS")
        
        if not self.helius_api_key:
            print("⚠️ Helius API key not provided, using basic RPC parsing")
            return self._fetch_trades_basic(wallet, limit)
        
        print(f"🔍 Fetching trades via Helius for {wallet[:8]}...{wallet[-6:]}")
        
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
                'type': 'SWAP'  #Filter for swaps only
            }
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

                    if not type(tx) is str and tx.get('type') == 'SWAP'  :
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
                            'success': tx.get('transactionError') is None
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

                if (max_trades > 0 and len(trades) >= max_trades): 
                    return trades
            
            #except Exception as e:
            #    print(f"   Error with Helius API: {e}")
            #    return self._fetch_trades_basic(wallet, limit)

        return trades
    
    def _fetch_trades_basic(self, wallet: str, limit: int = 1000) -> List[Dict]:
        """
        Basic trade fetching using standard Solana RPC endpoints

        Args:
            wallet: Wallet address to fetch trades for
            limit: Maximum number of signatures to fetch

        Returns:
            List of dictionaries containing parsed trade data
        """
        print(f" FETCH TRADES BASIC")
        
        signatures = self._fetch_signatures(wallet, limit)
        trades = []
        
        print(f"🔄 Parsing {len(signatures)} transactions...")
        
        for i, sig in enumerate(signatures[:100]):  #Limit to 100 for performance
            if i % 20 == 0:
                print(f"   Progress: {i}/{min(100, len(signatures))}")
            
            tx = self._fetch_transaction(sig)
            
            if tx:
                #Parse swap
                swap = self._parse_jupiter_swap(tx)
                
                if swap:
                    trade = {
                        'signature': sig,
                        'slot': tx.get('slot', 0),
                        'timestamp': tx.get('blockTime', 0),
                        'token_in': swap['token_in'],
                        'token_in_symbol': swap['token_in_symbol'],
                        'token_in_amount': swap['token_in_amount'],
                        'token_out': swap['token_out'],
                        'token_out_symbol': swap['token_out_symbol'],
                        'token_out_amount': swap['token_out_amount'],
                        'fee': tx.get('meta', {}).get('fee', 0) / 1e9,
                        'success': tx.get('meta', {}).get('err') is None,
                        'program': swap['program']
                    }
                    trades.append(trade)
        
        print(f"   Identified {len(trades)} trades")
        return trades
    
    def _get_solscan_url(self, signature: str) -> str:
        """
        Generate Solscan URL for transaction verification

        Args:
            signature: Transaction signature hash

        Returns:
            Full Solscan.io URL for the transaction
        """
        return f"https://solscan.io/tx/{signature}"

    def _print_trade_match(self, trade: Dict, trade_num: int):
        """
        Print formatted trade match details to console

        Args:
            trade: Dictionary containing matched trade details (buy/sell pair with P/L)
            trade_num: Sequential trade number for display
        """

        #Calculate hold duration in a readable format
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

        #Format profit/loss with color indicators
        profit_raw = trade['profit']
        pnl_pct = trade['pnl_pct']
        profit_indicator = "+" if profit_raw >= 0 else ""
        pnl_indicator = "+" if pnl_pct >= 0 else ""

        #Check if amounts match
        amount_mismatch = trade['buy_amount'] != trade['sell_amount']
        amount_warning = " ⚠️ PARTIAL" if amount_mismatch else ""

        #Print formatted output
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

    def _match_trades_for_pnl(self, trades: List[Dict]) -> List[Dict]:
        """
        Match buy and sell trades using FIFO to calculate profit/loss

        Args:
            trades: List of raw trade dictionaries from transaction parsing

        Returns:
            List of matched trade pairs with P/L calculations
        """
        print('Match buy and sell trades to calculate P/L')

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

            #Determine if this is a buy or sell
            #Simplified: if SOL/USDC is going out, it's a buy of the other token
            print(f'token in: {trade['token_in_symbol']}')
            print(f'token out: {trade['token_out_symbol']}')
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
                    'cost_token': trade['token_in_symbol']
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

        #Match buys and sells (FIFO)
        for token, data in token_positions.items():
            buys = data['buys']
            sells = data['sells']

            for sell in sells:
                if buys:
                    buy = buys[0]  #FIFO

                    #Validate that we can compare these trades (same base currency)
                    if buy.get('cost_token') != sell.get('proceeds_token'):
                        print(f"⚠️ Skipping match for {data['symbol']}: different currencies (bought with {buy.get('cost_token')}, sold for {sell.get('proceeds_token')})")
                        buys.pop(0)  #Remove unmatched buy
                        continue

                    #Simple P/L calculation
                    hold_time = sell['timestamp'] - buy['timestamp']
                    slot_diff = sell['slot'] - buy['slot']

                    #Calculate P/L if same base currency
                    pnl_pct = 0
                    profit = 0
                    actual_amount_traded = min(buy['amount'], sell['amount'])

                    if buy.get('cost_token') == sell.get('proceeds_token'):
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
                        print(f"  🔗 Verify Buy:  {self._get_solscan_url(buy['signature'])}")
                        print(f"  🔗 Verify Sell: {self._get_solscan_url(sell['signature'])}")
                        if abs(pnl_pct) > 1000:
                            print(f"  ⚠️ WARNING: PnL exceeds 1000%! Verify amounts on Solscan.")
                        print()

                    matched.append(trade_match)

                    #Print formatted trade details
                    self._print_trade_match(trade_match, len(matched))
                    
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
    
    def _add_trade_table(self, ax):
        """
        Add a detailed trade table to a matplotlib axis

        Args:
            ax: Matplotlib axis to draw the table on
        """

        ax.axis('off')

        #Prepare data for table - show all trades
        df_display = self.trades_df.copy()

        #Sort by sell time (most recent first) - show all trades
        df_display = df_display.sort_values('sell_time', ascending=False)

        #Format the data for display
        table_data = []
        for idx, row in df_display.iterrows():
            #Format hold time
            hold_seconds = row['hold_seconds']
            if hold_seconds < 60:
                hold_str = f"{hold_seconds:.0f}s"
            elif hold_seconds < 3600:
                hold_str = f"{hold_seconds / 60:.0f}m"
            elif hold_seconds < 86400:
                hold_str = f"{hold_seconds / 3600:.1f}h"
            else:
                hold_str = f"{hold_seconds / 86400:.1f}d"

            #Format profit
            profit_sign = "+" if row['profit'] >= 0 else ""
            pnl_sign = "+" if row['pnl_pct'] >= 0 else ""

            table_data.append([
                row['token'][:12],  #Token symbol (truncated)
                row['buy_time'].strftime('%m/%d %H:%M'),  #Buy Time
                row['sell_time'].strftime('%m/%d %H:%M'),  #Sell Time
                hold_str,
                f"{row['cost']:.3f} {row['cost_token']}",
                f"{row['proceeds']:.3f} {row['proceeds_token']}",
                f"{profit_sign}{row['profit']:.3f}",
                f"{pnl_sign}{row['pnl_pct']:.1f}%",
                f"{row['largest_buy_pct']:.0f}%",
                f"{row['largest_sell_pct']:.0f}%",
                row['buy_sig'],  #Buy Tx Sig
                row['sell_sig']  #Sell Tx Sig
            ])

        #Create column headers
        col_labels = ['Token', 'Buy Time', 'Sell Time', 'Hold', 'Cost', 'Proceeds', 'Profit', 'P/L %', 'Buy %', 'Dump %', 'Buy Tx Sig', 'Sell Tx Sig']

        #Create the table
        table = ax.table(cellText=table_data,
                        colLabels=col_labels,
                        cellLoc='left',
                        loc='center',
                        colWidths=[0.08, 0.07, 0.07, 0.04, 0.10, 0.10, 0.06, 0.05, 0.04, 0.04, 0.12, 0.12])

        #Style the table
        table.auto_set_font_size(False)
        table.set_fontsize(7)
        table.scale(1, 1.5)

        #Color code the header
        for i, key in enumerate(col_labels):
            cell = table[(0, i)]
            cell.set_facecolor('#4472C4')
            cell.set_text_props(weight='bold', color='white')

        #Color code profit/loss rows
        for i, row_data in enumerate(table_data):
            profit_val = float(row_data[7].replace('%', '').replace('+', ''))
            color = '#E8F5E9' if profit_val >= 0 else '#FFEBEE'

            for j in range(len(col_labels)):
                cell = table[(i + 1, j)]
                cell.set_facecolor(color)

        ax.set_title(f'Matched Trades (All {len(df_display)} trades)', fontsize=12, fontweight='bold', pad=10)

    def _plot_graphs(self, has_trades, has_latency, figsize, save_plots=False):
        """
        Create the performance graphs including P/L distribution, win/loss ratio, etc.

        Args:
            has_trades: Boolean indicating if trade data is available
            has_latency: Boolean indicating if latency data is available
            figsize: Tuple of (width, height) for figure size in inches
            save_plots: If True, save the plot as a PNG file
        """

        #Create figure with GridSpec for flexible layout
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
            #1. P/L Distribution
            ax = axes[plot_idx]
            self.trades_df['pnl_pct'].hist(bins=30, ax=ax, color='skyblue', edgecolor='black')
            ax.axvline(0, color='red', linestyle='--', alpha=0.5)
            ax.set_title('P/L Distribution')
            ax.set_xlabel('P/L (%)')
            ax.set_ylabel('Number of Trades')
            plot_idx += 1

            #2. Win/Loss Pie
            ax = axes[plot_idx]
            wins = (self.trades_df['pnl_pct'] > 0).sum()
            losses = (self.trades_df['pnl_pct'] <= 0).sum()
            ax.pie([wins, losses], labels=[f'Wins ({wins})', f'Losses ({losses})'],
                   autopct='%1.1f%%', colors=['#2ecc71', '#e74c3c'], startangle=90)
            ax.set_title('Win/Loss Ratio')
            plot_idx += 1

            #3. Cumulative P/L
            ax = axes[plot_idx]
            df_sorted = self.trades_df.sort_values('sell_time')
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

            #4. Hold Time vs P/L
            ax = axes[plot_idx]
            scatter = ax.scatter(self.trades_df['hold_days'], self.trades_df['pnl_pct'],
                               c=self.trades_df['pnl_pct'], cmap='RdYlGn',
                               alpha=0.6, edgecolors='black', linewidth=0.5)
            ax.axhline(0, color='black', linestyle='-', alpha=0.3)
            ax.set_title('Hold Time vs P/L')
            ax.set_xlabel('Hold Time (days)')
            ax.set_ylabel('P/L (%)')
            plt.colorbar(scatter, ax=ax)
            plot_idx += 1

            #5. Top Tokens
            ax = axes[plot_idx]
            token_perf = self.trades_df.groupby('token')['pnl_pct'].mean().sort_values().tail(10)
            colors = ['red' if x < 0 else 'green' for x in token_perf]
            token_perf.plot(kind='barh', ax=ax, color=colors)
            ax.set_title('Top 10 Tokens by Avg P/L')
            ax.set_xlabel('Average P/L (%)')
            plot_idx += 1

        if has_latency:
            #6. Latency Distribution
            ax = axes[plot_idx]
            self.latency_df['slot_latency'].hist(bins=30, ax=ax,
                                                 color='purple', edgecolor='black', alpha=0.7)
            mean_latency = self.latency_df['slot_latency'].mean()
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
            # Create plots directory if it doesn't exist
            os.makedirs('./plots', exist_ok=True)

            # Generate filename with timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            dirname = f"./plots/{self.main_wallet}"
            if not os.path.exists(dirname):
                os.mkdir(dirname)
            filename = f"{dirname}/analysis_graphs_{self.main_wallet[:8]}_{timestamp}.png"

            plt.savefig(filename, dpi=300, bbox_inches='tight')
            print(f"📊 Performance graphs saved to {filename}")

        plt.show()

    def _plot_table(self, save_plots=False):
        """
        Create a separate figure for the detailed trade table showing recent trades

        Args:
            save_plots: If True, save the table as a PNG file
        """

        fig, ax = plt.subplots(figsize=(20, 10))
        self._add_trade_table(ax)

        # Create title with target wallet if specified
        title = f'Trade Details - {self.main_wallet[:8]}...{self.main_wallet[-6:]}'
        if self.target_wallet:
            title += f'\nvs. {self.target_wallet[:8]}...{self.target_wallet[-6:]}'

        plt.suptitle(title, fontsize=14, fontweight='bold', y=0.995)
        plt.tight_layout()

        # Save plot if requested
        if save_plots:
            # Create plots directory if it doesn't exist
            os.makedirs('./plots', exist_ok=True)

            # Generate filename with timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            dirname = f"./plots/{self.main_wallet}"
            if not os.path.exists(dirname):
                os.mkdir(dirname)
            filename = f"{dirname}/trade_table_{self.main_wallet[:8]}_{timestamp}.png"

            plt.savefig(filename, dpi=300, bbox_inches='tight')
            print(f"📋 Trade table saved to {filename}")

        plt.show()

    def _plot_entry_exit_behavior(self, figsize=(20, 14), save_plots=False):
        """
        Create detailed visualizations of entry and exit behavior

        Args:
            figsize: Tuple of (width, height) for figure size in inches
            save_plots: If True, save the plot as a PNG file
        """

        # Create figure with 3x2 grid for 6 subplots
        fig = plt.figure(figsize=(figsize[0], figsize[1] * 0.75))
        gs = fig.add_gridspec(3, 2, hspace=0.4, wspace=0.3)

        # Calculate statistics
        avg_buy_pct = self.trades_df['largest_buy_pct'].mean()
        median_buy_pct = self.trades_df['largest_buy_pct'].median()
        min_buy_pct = self.trades_df['largest_buy_pct'].min()
        max_buy_pct = self.trades_df['largest_buy_pct'].max()

        avg_sell_pct = self.trades_df['largest_sell_pct'].mean()
        median_sell_pct = self.trades_df['largest_sell_pct'].median()
        min_sell_pct = self.trades_df['largest_sell_pct'].min()
        max_sell_pct = self.trades_df['largest_sell_pct'].max()

        avg_num_buys = self.trades_df['num_buys'].mean()
        avg_num_sells = self.trades_df['num_sells'].mean()

        # 1. Largest Buy Percentage Distribution
        ax1 = fig.add_subplot(gs[0, 0])
        self.trades_df['largest_buy_pct'].hist(bins=30, ax=ax1, color='skyblue', edgecolor='black')
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
        self.trades_df['largest_sell_pct'].hist(bins=30, ax=ax2, color='coral', edgecolor='black')
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
        self.trades_df['num_buys'].hist(bins=range(1, int(self.trades_df['num_buys'].max()) + 2),
                                        ax=ax3, color='lightgreen', edgecolor='black')
        ax3.axvline(avg_num_buys, color='red', linestyle='--', linewidth=2, label=f'Mean: {avg_num_buys:.1f}')
        ax3.set_title('Entry Fragmentation\n(Number of Buy Transactions per Token)', fontsize=10, fontweight='bold')
        ax3.set_xlabel('Number of Buys')
        ax3.set_ylabel('Number of Trades')
        ax3.legend()

        # 4. Number of Sells per Trade
        ax4 = fig.add_subplot(gs[1, 1])
        self.trades_df['num_sells'].hist(bins=range(1, int(self.trades_df['num_sells'].max()) + 2),
                                         ax=ax4, color='lightsalmon', edgecolor='black')
        ax4.axvline(avg_num_sells, color='red', linestyle='--', linewidth=2, label=f'Mean: {avg_num_sells:.1f}')
        ax4.set_title('Exit Fragmentation\n(Number of Sell Transactions per Token)', fontsize=10, fontweight='bold')
        ax4.set_xlabel('Number of Sells')
        ax4.set_ylabel('Number of Trades')
        ax4.legend()

        # 5. Buy Aggressiveness vs P/L
        ax5 = fig.add_subplot(gs[2, 0])
        scatter = ax5.scatter(self.trades_df['largest_buy_pct'], self.trades_df['pnl_pct'],
                             c=self.trades_df['pnl_pct'], cmap='RdYlGn',
                             alpha=0.6, edgecolors='black', linewidth=0.5)
        ax5.axhline(0, color='black', linestyle='-', alpha=0.3)
        ax5.set_title('Entry Aggressiveness vs P/L', fontsize=10, fontweight='bold')
        ax5.set_xlabel('Largest Buy (%)')
        ax5.set_ylabel('P/L (%)')
        plt.colorbar(scatter, ax=ax5, label='P/L %')

        # 6. Sell Aggressiveness vs P/L
        ax6 = fig.add_subplot(gs[2, 1])
        scatter = ax6.scatter(self.trades_df['largest_sell_pct'], self.trades_df['pnl_pct'],
                             c=self.trades_df['pnl_pct'], cmap='RdYlGn',
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
            # Create plots directory if it doesn't exist
            os.makedirs('./plots', exist_ok=True)

            # Generate filename with timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            dirname = f"./plots/{self.main_wallet}"
            if not os.path.exists(dirname):
                os.mkdir(dirname)
            filename = f"{dirname}/behavior_analysis_{self.main_wallet[:8]}_{timestamp}.png"

            plt.savefig(filename, dpi=300, bbox_inches='tight')
            print(f"📈 Behavior analysis saved to {filename}")

        plt.show()

    def _calculate_risk_metrics(self) -> Dict[str, float]:
        """
        Calculate Sharpe ratio, max drawdown, and max draw-up from trades

        Returns:
            Dict containing:
                - sharpe_ratio: Annualized Sharpe ratio (assuming 0% risk-free rate)
                - max_drawdown: Maximum drawdown percentage
                - max_drawdown_duration: Duration of max drawdown in days
                - max_drawup: Maximum draw-up percentage (most account was up)
                - max_drawup_duration: Duration of max draw-up in days
        """
        if self.trades_df.empty:
            return {
                'sharpe_ratio': 0.0,
                'max_drawdown': 0.0,
                'max_drawdown_duration': 0.0,
                'max_drawup': 0.0,
                'max_drawup_duration': 0.0
            }

        # Sort trades by sell time
        df_sorted = self.trades_df.sort_values('sell_time').copy()

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
    if helius_api_key:
        result = _analyze_transaction_helius(signature, helius_api_key)
    else:
        return None

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