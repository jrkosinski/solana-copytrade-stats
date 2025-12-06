import os
from datetime import datetime
from analyzer import WalletTradeAnalyzer, analyze_transaction

#TODO: that bug where it thinks a str is a tx: Error with Helius API: 'str' object has no attribute 'get'
#TODO: outliers filtered out but not for the plotting
#TODO: bug: not calculating latency


def quick_solana_analysis(wallet_address: str,
                         target_wallet: str = None,
                         limit: int = 1000,
                         use_cache=True):
    """
    Quick analysis function for Solana wallets

    Args:
        wallet_address: Wallet address to analyze
        target_wallet: Target wallet to compare (optional)
    """

    print("🚀 Solana Wallet Quick Analysis")
    print("=" * 60)

    # Create analyzer
    analyzer = WalletTradeAnalyzer(
        wallet_address=wallet_address,
        target_wallet=target_wallet,
        use_cache=use_cache
    )

    # Run analysis
    trades_df = analyzer.analyze(limit=limit)  # Limit for quick analysis

    # Generate report
    analyzer.generate_report()

    return analyzer, trades_df

def full_solana_analysis(wallet_address: str,
                         target_wallet: str = None,
                         limit: int = 1000,
                         save_plots: bool = False,
                         use_cache=True):
    """
    Full analysis function for Solana wallets

    Args:
        wallet_address: Wallet address to analyze
        target_wallet: Target wallet to compare (optional)
        limit: API request limit per call
        save_plots: If True, save plots as PNG files to ./plots/ directory
    """

    analyzer, trades_df = quick_solana_analysis(wallet_address, target_wallet, limit, use_cache=use_cache)

    # Plot if data available
    if not trades_df.empty or not analyzer.latency_df.empty:
        analyzer.generate_plots(save_plots=save_plots)

    # Export results
    if not trades_df.empty:
        filename = f"./csv/solana_trades_{wallet_address[:8]}_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
        trades_df.to_csv(filename, index=False)
        print(f"\n✅ Results exported to {filename}")

    return analyzer, trades_df

def quick_analyses(wallets):
    for wallet in wallets:
        quick_solana_analysis(wallet, None, 3000, use_cache=True)

def full_analyses(wallets):
    for wallet in wallets:
        full_solana_analysis(wallet, None, 3000, save_plots=True)

def analyze_tx(signature: str):
    """
    Analyze a single transaction signature

    Args:
        signature: Transaction signature to analyze

    Returns:
        Dictionary containing transaction analysis

    Example:
        analyze_tx("5Jb3...")
    """
    return analyze_transaction(signature, os.getenv('HELIUS_API_KEY'))

def analyze_txs(signatures):
    for sig in signatures:
        analyze_tx(sig)

def find_copy_target(wallet_address: str,
                     lookback_blocks: int = 10,
                     min_correlation_score: int = 2,
                     num_trades_to_analyze: int = 5,
                     limit: int = 100):
    """
    Find potential copy-trading targets for a wallet

    This analyzes the wallet's trade history and looks for wallets that
    consistently traded the same tokens shortly before this wallet.

    Args:
        wallet_address: Wallet address to analyze
        lookback_blocks: How many blocks to look backwards from each trade
        min_correlation_score: Minimum number of matching trade pairs required
        num_trades_to_analyze: Number of wallet's trades to analyze (smaller = faster)
        limit: How many transactions to fetch from wallet

    Returns:
        Dictionary with:
        - candidates: Ranked list of potential copy targets
        - analysis: Per-trade breakdown
        - summary: Overall statistics

    Example:
        >>> result = find_copy_target("9EibckQ6Jdfnhb4uAG352KaepYXspRrcNwFjC7xkvRXx")
        >>> for candidate in result['candidates'][:3]:
        ...     print(f"{candidate['wallet']}: {candidate['score']} matches")
    """
    from src.utils import find_copy_trading_targets

    print(f"🔍 Finding copy-trading targets for {wallet_address[:8]}...")
    print("=" * 80)

    # Step 1: Analyze wallet's trades
    analyzer = WalletTradeAnalyzer(
        wallet_address=wallet_address,
        target_wallet=None
    )

    trades_df = analyzer.analyze(limit=limit)
    matched_trades = analyzer.trades

    if not matched_trades:
        print("❌ No matched trade pairs found")
        return None

    print(f"✅ Found {len(matched_trades)} matched trade pairs")

    # Step 2: Find correlation
    num_to_analyze = min(num_trades_to_analyze, len(matched_trades))
    print(f"Analyzing {num_to_analyze} trades...")

    result = find_copy_trading_targets(
        bot_trades=matched_trades[:num_to_analyze],
        helius_api_key=os.getenv('HELIUS_API_KEY'),
        lookback_blocks=lookback_blocks,
        min_correlation_score=min_correlation_score,
        bot_wallet=wallet_address
    )

    return result

full_analyze = True

if (full_analyze): 


    full_analyses([
        "2fg5QD1eD7rzNNCsvnhmXFm5hqNgwTTG8p7kQ6f3rx6f",
        "JDuqZT2f8nzNWMSLYo8LWfYDV34Zgj7zYGqp1y9SPXai",
        "CFS2db3cag9A3G8P5NHT3sbFTcvDeXW4WXgWn6tQcs74",
        "7CXbEAX4GTBur2te85FyZkWitk97NX5adJN9cevWJfg2",
        "5a1zqmGWmdAC4qYtoD3RQwFtJR7EwPXxpkYZQRRfeMVY",
        "AEfUGoV2qh1A1k3KxuEpZS9o8wSLKXpHpCUkv5mov6Zk",
        "4MLv9wmF5RFhp2rpNJ5ZzrNZwE4VNKrMYv7FoEij5vL4",
        "6LEUnbZtcSoekRUTiLXbhtLgLcjQEUSu4Y29n8tbCBqi",
        "EZk34zBM6cCCzzWARz5uG7P592bpjB2cEfXLvSNYvNNu",
        "3wNnJCa1Z37uD2tMYkHPMi3MHmcQdYJ4wpvyk4xb6Qck",
        "CZD26AV4yxX2x7Z9jDsSEQiCLcTpkZejAbjEmCD6ntEk",

        "Gg5xSmrpDGrhFJKQ2V4psfL78AV4EPzK5vwwriYtcEzs",
        "ADENywZuaxmt9Ar8Hju9z4zMYktjTLTVecDrDENrTsKF",
        "4CoXh8R1QbbazXrftAx8HDAnUe9uqPJC1TPcZWayTpdi",
        "4TqoBiBYPKVjd2oENupLKHCLTNTZGEng1LMraoN2e3yZ",
        "2fg5QD1eD7rzNNCsvnhmXFm5hqNgwTTG8p7kQ6f3rx6f",
        "8deJ9xeUvXSJwicYptA9mHsU2rN2pDx37KWzkDkEXhU6",
        "FPAeapSTb5H33Jmm2cZXEJhBP2MdHYgoecxTmChHrocV",
        "GpTXmkdvrTajqkzX1fBmC4BUjSboF9dHgfnqPqj8WAc4",
        "2ezv4U5HmPpkt2xLsKnw1FyyGmjFBeW7c166p99Hw2xB",
        "7BNaxx6KdUYrjACNQZ9He26NBFoFxujQMAfNLnArLGH5",
        "5TaPtQ9DE1YMUfiyLv7CCNx1CEh88nWx3sPmNRz9zL75",
        "Aqje5DsN4u2PHmQxGF9PKfpsDGwQRCBhWeLKHCFhSMXk",
        "9sCcAxe56AuDQfJgU7kB1LpnQEYXDcGpAtXnN49H6SB3",
        "HdKJM6Lvfp9aV9tvEMC8AD4GnsbFgMUkHLoK923Sn1ET",
        "ADENywZuaxmt9Ar8Hju9z4zMYktjTLTVecDrDENrTsKF",
        "BhBc8kbkgzXHmv79mPHCCVfpdZwanYabPR939g8foje6",
        "9EibckQ6Jdfnhb4uAG352KaepYXspRrcNwFjC7xkvRXx",
        "8Q1yVTrV5WLt8GACJ83idpPw2RRXETwaMHjxsZVo4PvD",
        "8G5XHW2SF3fzCSFNGxvtHKFe9uZ58vScqhsQeyTwZPgQ",
        "E45YLW6LV2GdvPu4HgpBMZF4veGmUqbK6hs2W3ykx2s1"
    ])

    



else:
    analyze_txs([
        "5pycPpVsMhTTd6wGrYNYPQQhvECCGzDquBuWNvR3L1VPLXT2hDHobe61MTY2wF63MzJkFuFeCA2XiqYvpNtq9FKQ",
        "ovfU7wzcuLinbpa5oYYUvj8yQnSVScXeuZNnxyXctGMtuUhD5MUXdceGvkajPUL8vxvyWKMBrUMxSBBAwz3JzCa",
    ])




#HOMEBOT - 9EibckQ6Jdfnhb4uAG352KaepYXspRrcNwFjC7xkvRXx
