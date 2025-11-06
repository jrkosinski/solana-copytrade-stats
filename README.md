# Solana Copy-Trading Stats

A performance analysis tool for Solana copy-trading bots. Track and analyze trading performance, latency, and profitability metrics for bot wallets copying other traders.

## Features

- **Transaction Analysis**: Fetch and parse all transactions from bot wallets
- **Performance Metrics**: Calculate P/L, win rate, average gains/losses
- **Latency Tracking**: Measure execution delays between target and bot trades
- **Data Export**: Save detailed trade data to CSV for further analysis
- **Visual Analytics**: Generate performance charts and statistics

## Prerequisites

- Python 3.12+
- [Helius API Key](https://www.helius.dev/) (required for transaction data)

## Quick Start

### 1. Set up your API key

Export your Helius API key as an environment variable:

```bash
export HELIUS_API_KEY=your_api_key_here
```

### 2. Run the analyzer

Execute the application using the provided script:

```bash
./run.sh
```

## Usage

The application will analyze the specified bot wallet's trading performance and generate:
- Detailed trade statistics
- P/L analysis with outlier filtering
- CSV export of all trades
- Performance visualizations

### Configuration

Edit [src/main.py](src/main.py) to configure:
- Bot wallet address
- Target wallet address (optional)
- Outlier filtering thresholds
- Time ranges for analysis

## Project Structure

```
solana-copytrade-stats/
├── src/
│   └── main.py          # Main analyzer class and execution
├── run.sh               # Run script
└── README.md           # This file
```

## Output

The analyzer generates:
- Console output with key statistics
- CSV files with trade details (format: `solana_trades_{wallet}_{timestamp}.csv`)
- Visual charts (if configured)

## Notes

- Outlier filtering is enabled by default (configurable in main.py:27-29)
- Transactions are fetched using Helius API for enhanced accuracy
- Large wallets may take time to process all historical trades