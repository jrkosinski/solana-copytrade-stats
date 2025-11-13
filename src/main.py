import os
from datetime import datetime
from analyzer import SolanaCopyTradingAnalyzer, analyze_transaction

#TODO: that bug where it thinks a str is a tx: Error with Helius API: 'str' object has no attribute 'get'
#TODO: outliers filtered out but not for the plotting
#TODO: bug: not calculating latency


def quick_solana_analysis(main_wallet: str, 
                         target_wallet: str = None,
                         helius_api_key: str = None,
                         limit: int = 1000, 
                         max_trades:int = 100):
    """
    Quick analysis function for Solana copy-trading bots
    
    Args:
        main_wallet: Bot wallet address
        target_wallet: Target wallet to compare (optional)
        helius_api_key: Your Helius API key
    """
    
    print("🚀 Solana Copy-Trading Bot Quick Analysis")
    print("=" * 60)
    
    # Create analyzer
    analyzer = SolanaCopyTradingAnalyzer(
        main_wallet=main_wallet,
        target_wallet=target_wallet,
        helius_api_key=helius_api_key
    )
    
    # Run analysis
    trades_df = analyzer.analyze_wallet(limit=limit, max_trades=max_trades)  # Limit for quick analysis
    
    # Generate report
    analyzer.generate_report()

    return analyzer, trades_df

def full_solana_analysis(main_wallet: str,
                         target_wallet: str = None,
                         helius_api_key: str = None,
                         limit: int = 1000,
                         max_trades:int = 100,
                         save_plots: bool = False):
    """
    Full analysis function for Solana copy-trading bots

    Args:
        main_wallet: Bot wallet address
        target_wallet: Target wallet to compare (optional)
        helius_api_key: Your Helius API key
        limit: API request limit per call
        max_trades: Maximum number of trades to fetch
        save_plots: If True, save plots as PNG files to ./plots/ directory
    """

    analyzer, trades_df = quick_solana_analysis(main_wallet, target_wallet, helius_api_key, limit, max_trades)

    # Plot if data available
    if not trades_df.empty or not analyzer.latency_df.empty:
        analyzer.plot_results(save_plots=save_plots)

    # Export results
    if not trades_df.empty:
        filename = f"./csv/solana_trades_{main_wallet[:8]}_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
        trades_df.to_csv(filename, index=False)
        print(f"\n✅ Results exported to {filename}")

    return analyzer, trades_df

def quick_analyses(main_wallets): 
    for wallet in main_wallets: 
        quick_solana_analysis(wallet, None, os.getenv('HELIUS_API_KEY'), 1000, max_trades=150)


def full_analyses(main_wallets):
    for wallet in main_wallets:
        full_solana_analysis(wallet, None, os.getenv('HELIUS_API_KEY'), 1000, max_trades=150)

def analyze_tx(signature: str, helius_api_key: str = None):
    """
    Analyze a single transaction signature

    Args:
        signature: Transaction signature to analyze
        helius_api_key: Optional Helius API key (uses env var if not provided)

    Returns:
        Dictionary containing transaction analysis

    Example:
        analyze_tx("5Jb3...")
        analyze_tx("5Jb3...", os.getenv('HELIUS_API_KEY'))
    """
    if helius_api_key is None:
        helius_api_key = os.getenv('HELIUS_API_KEY')

    return analyze_transaction(signature, helius_api_key)


full_analyze = False

if (full_analyze): 
    full_solana_analysis("8deJ9xeUvXSJwicYptA9mHsU2rN2pDx37KWzkDkEXhU6", 
        None, 
        os.getenv('HELIUS_API_KEY'), 1000, max_trades=150)

    full_solana_analysis("9EibckQ6Jdfnhb4uAG352KaepYXspRrcNwFjC7xkvRXx", 
        "8deJ9xeUvXSJwicYptA9mHsU2rN2pDx37KWzkDkEXhU6", 
        os.getenv('HELIUS_API_KEY'), 1000, max_trades=150)

    full_solana_analysis("9EibckQ6Jdfnhb4uAG352KaepYXspRrcNwFjC7xkvRXx", 
        None, 
        os.getenv('HELIUS_API_KEY'), 1000, max_trades=150)
else:
    analyze_tx("gn79MPugB7fAGoQ7i2GGdE8wLKRhF2rUobBeUqUYbL1bbZg7GBDdBztf5fN6zPUrkZPMuSe8y8HHP637ax6s5Mp", os.getenv('HELIUS_API_KEY'))


#full_analyses([
#    "2fg5QD1eD7rzNNCsvnhmXFm5hqNgwTTG8p7kQ6f3rx6f",
#    "8deJ9xeUvXSJwicYptA9mHsU2rN2pDx37KWzkDkEXhU6",
#    "FPAeapSTb5H33Jmm2cZXEJhBP2MdHYgoecxTmChHrocV",
#    "CU3ErWQvUQhxiLE8Kvo6NsYujTudYLUAJ1qogVkMJQ1r",
#    "GpTXmkdvrTajqkzX1fBmC4BUjSboF9dHgfnqPqj8WAc4",
#    "2ezv4U5HmPpkt2xLsKnw1FyyGmjFBeW7c166p99Hw2xB",
#    "7BNaxx6KdUYrjACNQZ9He26NBFoFxujQMAfNLnArLGH5",
#    "5TaPtQ9DE1YMUfiyLv7CCNx1CEh88nWx3sPmNRz9zL75",
#    "Aqje5DsN4u2PHmQxGF9PKfpsDGwQRCBhWeLKHCFhSMXk",
#    "9sCcAxe56AuDQfJgU7kB1LpnQEYXDcGpAtXnN49H6SB3",
#    "HdKJM6Lvfp9aV9tvEMC8AD4GnsbFgMUkHLoK923Sn1ET",
#    "YCmJLPnathD2TWQEvUUD4pWUSQ1UP8KtUZFzH8ARdkr",
#    "ADENywZuaxmt9Ar8Hju9z4zMYktjTLTVecDrDENrTsKF",
#])

#TO DO: 
#==================================
#8deJ9xeUvXSJwicYptA9mHsU2rN2pDx37KWzkDkEXhU6
#ADENywZuaxmt9Ar8Hju9z4zMYktjTLTVecDrDENrTsKF
#FPAeapSTb5H33Jmm2cZXEJhBP2MdHYgoecxTmChHrocV
#CU3ErWQvUQhxiLE8Kvo6NsYujTudYLUAJ1qogVkMJQ1r
#TTdzckfwm7Y46gUULe6zmwC9z5pV1o5qaKkvAbAvXvY  ?
#GpTXmkdvrTajqkzX1fBmC4BUjSboF9dHgfnqPqj8WAc4
#2ezv4U5HmPpkt2xLsKnw1FyyGmjFBeW7c166p99Hw2xB
#7BNaxx6KdUYrjACNQZ9He26NBFoFxujQMAfNLnArLGH5
#5TaPtQ9DE1YMUfiyLv7CCNx1CEh88nWx3sPmNRz9zL75
#Aqje5DsN4u2PHmQxGF9PKfpsDGwQRCBhWeLKHCFhSMXk
#9sCcAxe56AuDQfJgU7kB1LpnQEYXDcGpAtXnN49H6SB3
#HdKJM6Lvfp9aV9tvEMC8AD4GnsbFgMUkHLoK923Sn1ET
#YCmJLPnathD2TWQEvUUD4pWUSQ1UP8KtUZFzH8ARdkr

#DONE: 
#==================================
#CFS2db3cag9A3G8P5NHT3sbFTcvDeXW4WXgWn6tQcs74: ERROR 
#2fg5QD1eD7rzNNCsvnhmXFm5hqNgwTTG8p7kQ6f3rx6f


#HOMEBOT - 9EibckQ6Jdfnhb4uAG352KaepYXspRrcNwFjC7xkvRXx

#8deJ9xeUvXSJwicYptA9mHsU2rN2pDx37KWzkDkEXhU6 - no matched trades found
#ADENywZuaxmt9Ar8Hju9z4zMYktjTLTVecDrDENrTsKF - Fastest Copy: 4 slots
#FPAeapSTb5H33Jmm2cZXEJhBP2MdHYgoecxTmChHrocV
#CU3ErWQvUQhxiLE8Kvo6NsYujTudYLUAJ1qogVkMJQ1r
#TTdzckfwm7Y46gUULe6zmwC9z5pV1o5qaKkvAbAvXvY  ?