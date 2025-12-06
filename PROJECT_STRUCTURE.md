# Project Structure: Solana Copy-Trading Analysis Tools

## Overview

This project provides utilities for analyzing the profitability and behavior of token-trading Solana wallets, with a focus on copy-trading bot performance analysis.

## Core Analysis Pipeline (Production-Ready)

### 1. WalletTradeAnalyzer
**File:** [src/analyzer.py](src/analyzer.py:14)
**Lines:** 1335
**Status:** Primary/Core Module

The main analyzer that powers the entire analysis pipeline. This is the heart of the project.

**Capabilities:**
- Analyzes profitability of trading wallets
- Fetches wallet transactions via Helius API
- Matches buy/sell pairs for P&L calculation
- Handles both SWAP and TRANSFER transactions
- Tracks position sizes, hold times, win rates
- Calculates latency between wallet and target wallets (when target wallet is provided)
- Supports caching for improved performance
- Filters outliers and provides clean data

**Key Methods:**
- `analyze()` - Main orchestration method
- `generate_report()` - Creates comprehensive text reports
- `generate_plots()` - Generates visualizations

**Usage:**
```python
analyzer = WalletTradeAnalyzer(
    wallet_address="<wallet_address>",
    target_wallet="<optional_target>",
    use_cache=True
)
trades_df = analyzer.analyze(limit=1000)
analyzer.generate_report()
analyzer.generate_plots(save_plots=True)
```

### 2. TradingReporter
**File:** [src/trading_reporter.py](src/trading_reporter.py:14)
**Lines:** 313
**Status:** Production - Report Generation

Generates comprehensive text-based analysis reports from trading data.

**Capabilities:**
- Trading statistics (win rate, average P/L, total profit)
- Risk metrics (Sharpe ratio, max drawdown, profit factor)
- Behavioral analysis (position sizing patterns, hold time analysis)
- Formatted console output with clear sections

**Key Methods:**
- `generate_report()` - Main report generation
- `_calculate_statistics()` - Compute trading metrics
- `_analyze_behavior()` - Pattern analysis

### 3. TradingPlotter
**File:** [src/trading_plotter.py](src/trading_plotter.py:23)
**Lines:** 523
**Status:** Production - Visualization

Creates comprehensive visualizations for trading performance analysis.

**Capabilities:**
- P/L distribution histograms
- Hold time analysis charts
- Entry/exit behavior patterns
- Interactive trade detail views
- Latency analysis plots (when comparing with target wallet)
- Saves plots to `/plots/` directory

**Key Methods:**
- `plot_analysis()` - Creates full analysis visualization suite
- `plot_trade_details()` - Interactive per-trade exploration
- `plot_latency_analysis()` - Copy speed visualization

## Utility & Discovery Functions

### 4. Copy Target Discovery
**Files:**
- [src/find_copy_target.py](src/find_copy_target.py) (115 lines)
- `find_copy_trading_targets()` in [src/utils.py](src/utils.py)

**Status:** Production - Utility

Reverse-engineers which wallet(s) a bot might be copying.

**How it works:**
1. Analyzes a bot's trade history
2. For each bot trade, looks backwards N blocks
3. Finds wallets that traded the same token before the bot
4. Scores candidates based on correlation frequency

**Exposed via:**
```python
from main import find_copy_target

result = find_copy_target(
    main_wallet="<bot_wallet>",
    lookback_blocks=10,
    min_correlation_score=2,
    num_trades_to_analyze=5
)
```

### 5. TokenInflowTracker
**File:** [src/token_inflow_tracker.py](src/token_inflow_tracker.py:18)
**Lines:** 215
**Status:** Standalone - Not Integrated

Tracks how tokens entered a wallet (transfers vs. swaps).

**Capabilities:**
- Identifies token acquisition sources
- Distinguishes between swaps and transfers
- Tracks timing of token inflows
- Maps token distribution patterns

**Current Status:** Built as a standalone utility but not integrated into the main analysis pipeline.

**Potential Use:** Could be integrated to provide deeper insight into token acquisition patterns.

### 6. Single Transaction Analyzer
**File:** [src/main.py](src/main.py:81)
**Function:** `analyze_tx()` / `analyze_txs()`
**Status:** Utility

Analyzes individual transaction signatures for debugging or detailed inspection.

```python
from main import analyze_tx
analyze_tx("5Jb3...")
```

## Entry Points & Main Interface

### Main Entry File
**File:** [src/main.py](src/main.py)
**Lines:** 291

Provides convenience functions and example usage:

**Key Functions:**
- `quick_solana_analysis()` - Fast analysis without plots
- `full_solana_analysis()` - Complete analysis with plots and CSV export
- `quick_analyses()` / `full_analyses()` - Batch wallet analysis
- `analyze_tx()` / `analyze_txs()` - Single transaction analysis
- `find_copy_target()` - Discover copy trading targets

## Support Modules

### Utils
**File:** [src/utils.py](src/utils.py)
**Lines:** 723

Shared utility functions used across modules:
- `is_base_currency()` - Identify base currencies (SOL, USDC, USDT)
- `is_sol()` - SOL-specific checks
- `get_solscan_url()` - Generate blockchain explorer URLs
- `find_copy_trading_targets()` - Target discovery logic
- `get_wallets_that_bought_token_in_block_range()` - Block-range token buyer search
- Various formatting and printing utilities

## Test & Development Scripts

**Location:** `/tests/` directory

### Active Tests (Keep)
1. **[test_transfer_pnl.py](tests/test_transfer_pnl.py)** - Tests transfer cost estimation in analyzer
2. **[test_cross_currency_matching.py](tests/test_cross_currency_matching.py)** - Tests buy/sell matching across currencies
3. **[test_token_buyers.py](tests/test_token_buyers.py)** - Tests block-range buyer search utility
4. **[test_position_size.py](tests/test_position_size.py)** - Tests position size tracking

### Development/Investigation Scripts
1. **[investigate_transfers.py](tests/investigate_transfers.py)** (212 lines) - Transfer chain investigation
2. **[poc_transfer_pnl.py](tests/poc_transfer_pnl.py)** (319 lines) - POC for transfer-based P&L
3. **[test_transfers.py](tests/test_transfers.py)** (143 lines) - Transfer fetching tests

**Status:** These are development artifacts. Determine which to keep vs. delete during cleanup.

## Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    User Entry Point                          │
│                  (main.py functions)                         │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              WalletTradeAnalyzer                             │
│  - Fetch transactions (Helius API)                          │
│  - Parse swaps & transfers                                  │
│  - Match buy/sell pairs                                     │
│  - Calculate P&L, metrics                                   │
└────────────┬──────────────────────┬─────────────────────────┘
             │                      │
             ▼                      ▼
┌────────────────────┐    ┌────────────────────┐
│  TradingReporter   │    │  TradingPlotter    │
│  - Text reports    │    │  - Visualizations  │
│  - Statistics      │    │  - Charts          │
│  - Risk metrics    │    │  - Plots           │
└────────────────────┘    └────────────────────┘
```

## Configuration & Requirements

### API Dependencies
- **Helius API** (required): Enhanced Solana transaction data
- **Shyft API** (optional): Alternative transaction parsing

### Environment Variables
```bash
HELIUS_API_KEY=<your_key>
SHYFT_API_KEY=<optional>
```

### Key Dependencies
- `pandas` - Data manipulation
- `numpy` - Numerical operations
- `matplotlib` / `seaborn` - Plotting
- `requests` - API calls
- `web3` - Blockchain utilities

## Output Locations

- **CSV Exports:** `./csv/`
- **Visualizations:** `./plots/<wallet_address>/`
- **Cached Data:** `./cached_results/`

## Future Considerations

### Potential Integrations
1. **TokenInflowTracker** - Could be integrated into main analyzer for richer acquisition analysis
2. **Enhanced API Support** - Additional data sources beyond Helius

### Recent Changes
- **2025-12-06**: Renamed `SolanaCopyTradingAnalyzer` to `WalletTradeAnalyzer`
  - Changed `main_wallet` parameter to `wallet_address` for clarity
  - Changed `filter_to_matched_only` to `matched_tokens_only` for clarity
  - Renamed `analyze_wallet()` to `analyze()`
  - Renamed `plot_results()` to `generate_plots()`
  - Removed `helius_api_key` and `shyft_api_key` from constructor - now read from environment variables
  - Name now better reflects that the analyzer works for any trading wallet, not just copy-trading bots

## Architecture Notes

### Design Patterns
- **Separation of Concerns:** Analysis (Analyzer) → Reporting (Reporter) → Visualization (Plotter)
- **Caching:** Results cached to reduce API calls during development
- **Filtering:** Outlier filtering to prevent extreme trades from skewing statistics

### Key Trade-offs
- **Transfer Handling:** Complex logic to estimate cost basis for transferred tokens (using market price approximations)
- **Cross-Currency Matching:** Handles trades in different currencies (SOL, USDC) with conversion logic
- **API Rate Limiting:** Helius API used exclusively due to rich transaction metadata

## Removed Components

### TokenChart
**Removed:** 2025-12-06
**Reason:** Standalone token price charting not needed for core wallet analysis use case
**Previous Location:** `src/tokenchart.py` (210 lines)
