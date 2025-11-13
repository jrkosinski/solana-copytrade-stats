import requests
import pandas as pd
import matplotlib.pyplot as plt
import re

class TokenChart:

    def __init__(self,
                 token_mint: str = None,
                 helius_api_key: str = None,
                 start_slot: int = None,
                 end_slot: int = None):

        self.helius_api_key = helius_api_key
        self.token_mint = token_mint
        self.start_slot = start_slot
        self.end_slot = end_slot
      

    def build_chart(self):
        print('buildign chart')
        sigs = self._get_sigs_for_address(self.token_mint, self.start_slot, self.end_slot)
        print('got the sigs')

        swaps = []
        for entry in sigs:
            # Filter by slot range if specified
            if self.start_slot is not None and entry["slot"] < self.start_slot:
                continue
            if self.end_slot is not None and entry["slot"] > self.end_slot:
                continue

            sig = entry["signature"]
            tx = self._get_full_tx(sig)
            if not tx:
                continue

            swap = self._extract_swap(tx)

            if swap:
                swap["slot"] = entry["slot"]  # Add slot info to swap data
                swaps.append(swap)
                print(f"Swap #{len(swaps)}: {swap['side']} {swap['token_amount']:.2f} tokens for {swap['sol_amount']:.4f} SOL")
        
        if (len(swaps) > 0):
            print(f"\nProcessed {len(swaps)} swaps total")
            ohlc = self._build_candles(swaps)
            self._plot_candles(ohlc)
        else:
            print('No swaps detected')

    def _extract_swap(self, tx):
        # Check if we have the necessary data
        if "meta" not in tx:
            return None

        meta = tx["meta"]

        # Determine if this is a buy or sell from logs
        side = None
        if "logMessages" in meta:
            for log in meta["logMessages"]:
                if "Instruction: Buy" in log:
                    side = "buy"
                    break
                elif "Instruction: Sell" in log:
                    side = "sell"
                    break

        if not side:
            return None  # Not a pump.fun swap

        # Extract amounts from token balance changes
        pre_balances = meta.get("preTokenBalances", [])
        post_balances = meta.get("postTokenBalances", [])

        # Calculate SOL change (from native SOL balances)
        sol_pre = meta.get("preBalances", [])
        sol_post = meta.get("postBalances", [])

        # Find the token mint balance change
        token_amount = None
        for i, post in enumerate(post_balances):
            if post["mint"] == self.token_mint:
                # Find matching pre balance
                pre = next((p for p in pre_balances if p.get("accountIndex") == post.get("accountIndex")), None)
                if pre:
                    pre_amount = float(pre["uiTokenAmount"]["uiAmount"] or 0)
                    post_amount = float(post["uiTokenAmount"]["uiAmount"] or 0)
                    token_amount = abs(post_amount - pre_amount)
                    break

        # Calculate SOL change (typically index 0 is the signer)
        sol_amount = None
        if len(sol_pre) > 0 and len(sol_post) > 0:
            sol_change = abs(sol_post[0] - sol_pre[0]) / 1e9  # Convert lamports to SOL
            sol_amount = sol_change

        if sol_amount is None or token_amount is None or token_amount == 0:
            return None

        return {
            "side": side,
            "sol_amount": sol_amount,
            "token_amount": token_amount,
            "price": sol_amount / token_amount,
            "timestamp": tx["blockTime"]
        }
    
    def _get_sigs_for_address(self, address, start_slot=None, end_slot=None):
        url = f"https://mainnet.helius-rpc.com/?api-key={self.helius_api_key}"

        # getSignaturesForAddress doesn't support slot-based filtering directly
        # We need to paginate and filter results by slot manually
        all_sigs = []
        before_sig = None

        while True:
            params_dict = {"limit": 1000}
            if before_sig:
                params_dict["before"] = before_sig

            payload = {
                "jsonrpc": "2.0",
                "id": "fetch-sigs",
                "method": "getSignaturesForAddress",
                "params": [address, params_dict]
            }
            res = requests.post(url, json=payload).json()

            if "result" not in res or not res["result"]:
                break

            batch = res["result"]

            # Filter by slot range
            for entry in batch:
                if start_slot is not None and entry["slot"] < start_slot:
                    # We've gone past our range, stop pagination
                    return all_sigs
                if end_slot is None or entry["slot"] <= end_slot:
                    all_sigs.append(entry)

            # If we got fewer than limit results, we're done
            if len(batch) < 1000:
                break

            # Set up for next page
            before_sig = batch[-1]["signature"]

        return all_sigs

    def _get_full_tx(self, signature):
        url = f"https://mainnet.helius-rpc.com/?api-key={self.helius_api_key}"
        payload = {
            "jsonrpc": "2.0",
            "id": "fetch-tx",
            "method": "getTransaction",
            "params": [signature, {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 0}]
        }
        res = requests.post(url, json=payload).json()
        return res["result"]

    def _build_candles(self, swaps, interval='5s'):
        print(f'building candles for {len(swaps)} swaps')
        df = pd.DataFrame(swaps)

        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
        df = df.set_index('timestamp')

        time_range = (df.index.max() - df.index.min()).total_seconds()
        print(f"Time range: {time_range:.0f} seconds")
        print(f"Price range: {df['price'].min():.2e} to {df['price'].max():.2e}")

        ohlc = df['price'].resample(interval).ohlc()
        # Drop empty candles
        ohlc = ohlc.dropna()

        print(f"Created {len(ohlc)} candles with {interval} interval")

        return ohlc

    def _plot_candles(self, ohlc):
        if len(ohlc) == 0:
            print("No candles to plot")
            return

        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8), height_ratios=[3, 1])

        # Price chart
        ax1.plot(ohlc.index, ohlc['close'], marker='o', linestyle='-', linewidth=2, markersize=4, label='Close')
        ax1.fill_between(ohlc.index, ohlc['low'], ohlc['high'], alpha=0.3, label='High-Low Range')
        ax1.set_title(f"Pump.fun Price Chart - {self.token_mint[:8]}...", fontsize=14, fontweight='bold')
        ax1.set_ylabel("Price (SOL per Token)", fontsize=11)
        ax1.grid(True, alpha=0.3)
        ax1.legend()
        ax1.ticklabel_format(style='scientific', axis='y', scilimits=(0,0))

        # Volume indicator (using high-low spread as proxy)
        spread = ohlc['high'] - ohlc['low']
        ax2.bar(ohlc.index, spread, width=0.0001, alpha=0.6, color='steelblue')
        ax2.set_ylabel("Price Volatility", fontsize=11)
        ax2.set_xlabel("Time", fontsize=11)
        ax2.grid(True, alpha=0.3)
        ax2.ticklabel_format(style='scientific', axis='y', scilimits=(0,0))

        plt.tight_layout()
        plt.show()


