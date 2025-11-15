# Solana Copy-Trading Bot Performance Analyzer

A comprehensive performance analysis tool for Solana copy-trading bots. Analyze multiple bot wallets, track trading performance, calculate risk metrics, and visualize profitability with advanced statistical analysis.

## Features

### Core Functionality

-   **Transaction Parsing**: Fetch and parse swap transactions using Helius API
-   **Trade Matching**: FIFO-based buy/sell matching for accurate P/L calculation
-   **Multi-Wallet Analysis**: Batch analyze multiple bot wallets in one run
-   **Caching System**: Local caching of transaction data for faster re-analysis

### Performance Metrics

-   **Profit/Loss Analysis**: Calculate per-trade and cumulative P/L with percentage returns
-   **Win Rate**: Track winning vs. losing trade ratios
-   **Hold Time Statistics**: Average, median, min/max hold durations
-   **Risk Metrics**:
    -   Annualized Sharpe Ratio
    -   Maximum Drawdown (largest loss from peak)
    -   Maximum Draw-up (largest gain from trough)
    -   Drawdown/Draw-up duration tracking

### Data Quality

-   **Outlier Filtering**: Configurable P/L percentage thresholds to exclude anomalous trades
-   **Partial Trade Detection**: Identifies and flags mismatched buy/sell amounts
-   **Currency Validation**: Ensures buy and sell use compatible base currencies

### Visualization (Jupyter Support)

-   **Interactive Plots**: Tabbed interface with performance graphs and trade tables
-   P/L distribution histograms
-   Win/loss ratio pie charts
-   Cumulative P/L over time
-   Hold time vs. P/L scatter plots
-   Top tokens by average P/L
-   Detailed trade history tables

### Export Capabilities

-   **CSV Export**: Full trade details with timestamps, amounts, and P/L metrics
-   **Cached Results**: JSON caching for faster subsequent analyses

## Prerequisites

-   Python 3.12+
-   [Helius API Key](https://www.helius.dev/) (required for transaction data)
-   Virtual environment (recommended)

## Installation

### 1. Clone and set up environment

```bash
# Navigate to project directory
cd solana-copytrade-stats

# Create virtual environment (if not already created)
python3 -m venv .

# Activate virtual environment
source bin/activate  # Linux/Mac
# or
.\Scripts\activate  # Windows
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

Key dependencies:

-   `requests` - API communication
-   `pandas` - Data manipulation
-   `numpy` - Statistical calculations
-   `matplotlib`, `seaborn` - Visualization
-   `web3` - Solana blockchain interaction
-   `ipywidgets` - Jupyter notebook interactivity

### 3. Configure API key

Create a `.env` file or export as environment variable:

```bash
export HELIUS_API_KEY=your_api_key_here
```

Or add to `.env` file:

```
HELIUS_API_KEY=your_api_key_here
```

## Quick Start

### Run the analyzer

```bash
./run.sh
```

Or directly:

```bash
python src/main.py
```

## Usage

### Analyzing Bot Wallets

Edit [src/main.py](src/main.py) to specify wallet addresses:

```python
# Quick analysis (console output only)
quick_analyses([
    "2fg5QD1eD7rzNNCsvnhmXFm5hqNgwTTG8p7kQ6f3rx6f",
    "8deJ9xeUvXSJwicYptA9mHsU2rN2pDx37KWzkDkEXhU6",
    # ... add more wallets
])

# Full analysis (console + CSV export + plots)
full_analyses([
    "YourWalletAddressHere",
])
```

### Configuration Options

In [src/analyzer.py](src/analyzer.py):

```python
# Outlier filter constants (lines 23-26)
MAX_PNL_PCT = 50000.0   # Exclude trades with profit > 50000%
MIN_PNL_PCT = -80.0     # Exclude trades with loss < -80%

# Analysis limits
limit = 1000      # API request limit per call
```

### Understanding the Output

#### Console Report

```
📊 SOLANA COPY-TRADING BOT PERFORMANCE REPORT
================================================================================

📈 Overall Statistics:
   Total Matched Trades: 45
   Unique Tokens Traded: 23
   Date Range: 2024-11-01 to 2024-11-09

💰 Profit/Loss Statistics:
   Average P/L per trade: 12.34%
   Median P/L per trade: 8.56%
   Win Rate: 62.2%

📊 Risk Metrics:
   Sharpe Ratio: 1.45
   Max Drawdown: -15.67%
   Max Drawdown Duration: 2.34 days
   Max Draw-up: 45.23%
   Max Draw-up Duration: 3.12 days

⏰ Hold Time Statistics:
   Average Hold Time: 1.23 days
   Median Hold Time: 0.87 days
```

#### CSV Export

Format: `solana_trades_{wallet_first8}_{timestamp}.csv`

Columns include:

-   `token`, `token_address`
-   `buy_time`, `sell_time`, `hold_days`
-   `buy_amount`, `sell_amount`, `cost`, `proceeds`
-   `profit`, `pnl_pct`
-   Transaction signatures and slot numbers

#### Cached Data

Location: `cached_results/{wallet_address}.json`

Caches fetched transaction data to avoid repeated API calls.

## Project Structure

```
solana-copytrade-stats/
├── src/
│   ├── analyzer.py      # Main SolanaCopyTradingAnalyzer class
│   └── main.py          # Entry point with wallet configurations
├── cached_results/      # Cached transaction data (JSON)
├── csv/                 # Exported CSV trade reports
├── jupyter/             # Jupyter notebook files (if used)
├── requirements.txt     # Python dependencies
├── run.sh              # Quick run script
├── .env                # Environment variables (API keys)
└── README.md           # This file
```

## Advanced Usage

### Using in Jupyter Notebooks

```python
from src.analyzer import SolanaCopyTradingAnalyzer
import os

analyzer = SolanaCopyTradingAnalyzer(
    main_wallet="YourWalletAddress",
    helius_api_key=os.getenv('HELIUS_API_KEY'),
    filter_outliers=True
)

# Run analysis
trades_df = analyzer.analyze_wallet(limit=1000)

# Generate report
analyzer.generate_report()

# Show interactive plots
analyzer.plot_results()
```

### Copy-Trading Analysis with Target Wallet

When analyzing a copy-trading bot, you can compare it against the wallet being copied:

```python
analyzer = SolanaCopyTradingAnalyzer(
    main_wallet="YourBotWalletAddress",
    target_wallet="WalletBeingCopied",
    helius_api_key=os.getenv('HELIUS_API_KEY'),
    filter_outliers=True,
    filter_to_matched_only=True  # Only analyze trades that matched between bot and target
)

# Run analysis
trades_df = analyzer.analyze_wallet(limit=1000)

# View latency statistics
if not analyzer.latency_df.empty:
    print(f"Average copy latency: {analyzer.latency_df['slot_latency'].mean():.1f} slots")
```

**Parameters:**

-   `target_wallet`: The wallet address being copied (optional)
-   `filter_to_matched_only`: When `True`, only analyze trades on tokens that were copied from the target wallet. Useful for focused copy-trading performance analysis. Default: `False`

### Custom Analysis

```python
# Access the trades DataFrame directly
trades_df = analyzer.trades_df

# Filter for specific tokens
specific_token = trades_df[trades_df['token'] == 'BONK']

# Calculate custom metrics
avg_hold_winners = trades_df[trades_df['pnl_pct'] > 0]['hold_days'].mean()
```

## Supported DEXs

The analyzer currently supports swaps on:

-   Jupiter (v4, v6)
-   Orca (Whirlpool, v2)
-   Raydium (v4, CLMM)
-   Pump.fun
-   Serum v3

## Known Limitations

-   Only analyzes completed trade pairs (matched buys and sells)
-   Requires both buy and sell in the same base currency (SOL/USDC/USDT)
-   Does not track partial position management
-   Copy latency tracking requires target wallet configuration (optional)

## Troubleshooting

### No matched trades found

-   Check that the wallet has completed buy/sell pairs
-   Verify transactions are SWAP type on supported DEXs
-   Ensure sufficient transaction history (increase `limit` parameter)

### Outlier warnings

-   Adjust `MAX_PNL_PCT` and `MIN_PNL_PCT` in analyzer.py
-   Review flagged trades on [Solscan](https://solscan.io/) for validation

### API rate limits

-   Helius free tier has rate limits
-   Use caching to minimize repeated API calls
-   Consider upgrading Helius plan for high-frequency analysis

## Contributing

This is a personal analysis tool. Feel free to fork and customize for your needs.

## License

Private project - all rights reserved.
