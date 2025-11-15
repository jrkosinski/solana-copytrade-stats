import os
from datetime import datetime
from analyzer import SolanaCopyTradingAnalyzer, analyze_transaction
from tokenchart import TokenChart

#TODO: that bug where it thinks a str is a tx: Error with Helius API: 'str' object has no attribute 'get'
#TODO: outliers filtered out but not for the plotting
#TODO: bug: not calculating latency


def quick_solana_analysis(main_wallet: str, 
                         target_wallet: str = None,
                         limit: int = 1000):
    """
    Quick analysis function for Solana copy-trading bots
    
    Args:
        main_wallet: Bot wallet address
        target_wallet: Target wallet to compare (optional)
    """
    
    print("🚀 Solana Copy-Trading Bot Quick Analysis")
    print("=" * 60)
    
    helius_api_key = os.getenv('HELIUS_API_KEY')

    # Create analyzer
    analyzer = SolanaCopyTradingAnalyzer(
        main_wallet=main_wallet,
        target_wallet=target_wallet,
        helius_api_key=helius_api_key
    )
    
    # Run analysis
    trades_df = analyzer.analyze_wallet(limit=limit)  # Limit for quick analysis
    
    # Generate report
    analyzer.generate_report()

    return analyzer, trades_df

def full_solana_analysis(main_wallet: str,
                         target_wallet: str = None,
                         limit: int = 1000,
                         save_plots: bool = False):
    """
    Full analysis function for Solana copy-trading bots

    Args:
        main_wallet: Bot wallet address
        target_wallet: Target wallet to compare (optional)
        limit: API request limit per call
        save_plots: If True, save plots as PNG files to ./plots/ directory
    """

    analyzer, trades_df = quick_solana_analysis(main_wallet, target_wallet, limit)

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
        quick_solana_analysis(wallet, None, 1000)


def full_analyses(main_wallets):
    for wallet in main_wallets:
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
    helius_api_key = os.getenv('HELIUS_API_KEY')

    return analyze_transaction(signature, helius_api_key)

def analyze_txs(signatures): 
    for sig in signatures:
        analyze_tx(sig)

full_analyze = True

if (full_analyze): 

    #full_solana_analysis("8deJ9xeUvXSJwicYptA9mHsU2rN2pDx37KWzkDkEXhU6", 
    #    None, 1000)


    #chart = TokenChart( "F2rgvoWN6AM5U82BxV6AxXTLq3CJmTbF7bu7Yssxpump", os.getenv('HELIUS_API_KEY'),
    #    372916770, 372916870)
    #chart.build_chart()


#########################
    #full_solana_analysis("9EibckQ6Jdfnhb4uAG352KaepYXspRrcNwFjC7xkvRXx", 
    #    "CFS2db3cag9A3G8P5NHT3sbFTcvDeXW4WXgWn6tQcs74", 1000)

    full_analyses([
        "2fg5QD1eD7rzNNCsvnhmXFm5hqNgwTTG8p7kQ6f3rx6f",
        #"JDuqZT2f8nzNWMSLYo8LWfYDV34Zgj7zYGqp1y9SPXai",
        #"CFS2db3cag9A3G8P5NHT3sbFTcvDeXW4WXgWn6tQcs74",
        #"7CXbEAX4GTBur2te85FyZkWitk97NX5adJN9cevWJfg2",
          #"5a1zqmGWmdAC4qYtoD3RQwFtJR7EwPXxpkYZQRRfeMVY",
          #"AEfUGoV2qh1A1k3KxuEpZS9o8wSLKXpHpCUkv5mov6Zk",
          #"4MLv9wmF5RFhp2rpNJ5ZzrNZwE4VNKrMYv7FoEij5vL4",
          #"6LEUnbZtcSoekRUTiLXbhtLgLcjQEUSu4Y29n8tbCBqi",
          #"EZk34zBM6cCCzzWARz5uG7P592bpjB2cEfXLvSNYvNNu",
          #"3wNnJCa1Z37uD2tMYkHPMi3MHmcQdYJ4wpvyk4xb6Qck",
          #"CZD26AV4yxX2x7Z9jDsSEQiCLcTpkZejAbjEmCD6ntEk"
    ])

    


else:
    analyze_txs([
        "5pycPpVsMhTTd6wGrYNYPQQhvECCGzDquBuWNvR3L1VPLXT2hDHobe61MTY2wF63MzJkFuFeCA2XiqYvpNtq9FKQ",
        "ovfU7wzcuLinbpa5oYYUvj8yQnSVScXeuZNnxyXctGMtuUhD5MUXdceGvkajPUL8vxvyWKMBrUMxSBBAwz3JzCa",
    ])


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