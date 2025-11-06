import os
from datetime import datetime
from analyzer import SolanaCopyTradingAnalyzer

#TODO: that bug where it thinks a str is a tx: Error with Helius API: 'str' object has no attribute 'get'
#TODO: outliers filtered out but not for the plotting
#TODO: bug: not calculating latency


def quick_solana_analysis(bot_wallet: str, 
                         target_wallet: str = None,
                         use_helius: bool = True,
                         helius_api_key: str = None,
                         limit: int = 1000):
    """
    Quick analysis function for Solana copy-trading bots
    
    Args:
        bot_wallet: Bot wallet address
        target_wallet: Target wallet to compare (optional)
        use_helius: Whether to use Helius API for better data
        helius_api_key: Your Helius API key
    """
    
    print("🚀 Solana Copy-Trading Bot Quick Analysis")
    print("=" * 60)
    
    # Create analyzer
    analyzer = SolanaCopyTradingAnalyzer(
        bot_wallet=bot_wallet,
        target_wallet=target_wallet,
        helius_api_key=helius_api_key if use_helius else None
    )

    print(f"{helius_api_key}, {use_helius}")
    
    # Run analysis
    trades_df = analyzer.analyze_wallet(limit=limit)  # Limit for quick analysis
    
    # Generate report
    analyzer.generate_report()
    
    # Plot if data available
    if not trades_df.empty or not analyzer.latency_df.empty:
        analyzer.plot_results()
    
    # Export results
    if not trades_df.empty:
        filename = f"solana_trades_{bot_wallet[:8]}_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
        trades_df.to_csv(filename, index=False)
        print(f"\n✅ Results exported to {filename}")
    
    return analyzer, trades_df


quick_solana_analysis(
    "9EibckQ6Jdfnhb4uAG352KaepYXspRrcNwFjC7xkvRXx", 
    None, 
    True, 
    os.getenv('HELIUS_API_KEY'), 
    1000
    )

#9EibckQ6Jdfnhb4uAG352KaepYXspRrcNwFjC7xkvRXx

#8deJ9xeUvXSJwicYptA9mHsU2rN2pDx37KWzkDkEXhU6
#ADENywZuaxmt9Ar8Hju9z4zMYktjTLTVecDrDENrTsKF