"""
FastAPI application for Solana wallet analysis
"""
from fastapi import FastAPI, Query, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, Dict, List
from src.analyzer import WalletTradeAnalyzer
import uuid
import asyncio
import os
import glob

app = FastAPI(
    title="Solana Wallet Analysis API",
    description="API for analyzing Solana wallet trading patterns and transactions",
    version="1.0.0"
)

# Mount static files directory for serving plots and reports
os.makedirs("./output", exist_ok=True)
app.mount("/files", StaticFiles(directory="./output"), name="files")

# Global dictionary to store running analyzer instances
# Key: analysis_id (UUID string), Value: WalletTradeAnalyzer instance
active_analyses: Dict[str, WalletTradeAnalyzer] = {}


# Request/Response Models
class WalletAnalysisOptions(BaseModel):
    """Options for wallet analysis endpoints"""
    save_plots: bool = True
    read_cache: bool = True
    write_cache: bool = True
    matched_tokens_only: bool = True
    lookback: int = 3000


class WalletAnalysisResponse(BaseModel):
    """Response model for wallet analysis"""
    analysis_id: str
    status: str
    message: str
    wallet_address: Optional[str] = None
    error_message: Optional[str] = None
    results: Optional[Dict] = None  # Vital statistics when completed
    plot_urls: Optional[list] = None  # URLs to generated plots
    report_url: Optional[str] = None  # URL to the report file


class TransactionResponse(BaseModel):
    """Response model for transaction endpoints"""
    status: str = "pending"
    message: str = "Transaction endpoint not yet implemented"


# API Routes
@app.get("/api/v1/")
async def root():
    """Health check endpoint"""
    return "HI"


def get_analysis_file_urls(analysis_id: str) -> tuple[List[str], str]:
    """
    Collect URLs for plots and report files for a completed analysis

    Args:
        analysis_id: Unique identifier for the analysis

    Returns:
        Tuple of (plot_urls, report_url)
    """
    output_dir = f"./output/{analysis_id}"
    plot_urls = []
    report_url = None

    # Collect plot URLs
    plots_dir = os.path.join(output_dir, "plots")
    if os.path.exists(plots_dir):
        plot_files = glob.glob(os.path.join(plots_dir, "*.png"))
        plot_urls = [f"/files/{analysis_id}/plots/{os.path.basename(f)}" for f in plot_files]

    # Collect report URL
    reports_dir = os.path.join(output_dir, "reports")
    report_file = os.path.join(reports_dir, "stats.txt")
    if os.path.exists(report_file):
        report_url = f"/files/{analysis_id}/reports/stats.txt"

    return plot_urls, report_url


def run_analysis(analysis_id: str, analyzer: WalletTradeAnalyzer, lookback: int):
    """
    Background task to run wallet analysis

    Args:
        analysis_id: Unique identifier for this analysis
        analyzer: WalletTradeAnalyzer instance
        lookback: Number of transactions to look back
    """
    try:
        # Run the analysis
        analyzer.analyze(lookback=lookback)

        # Generate plots and reports if analysis succeeded
        if analyzer.status == "completed":
            analyzer.generate_plots(save_plots=True)
            analyzer.generate_report(save_to_file=True)

    except Exception as e:
        # Error is already captured in analyzer.status and analyzer.error_message
        print(f"Analysis {analysis_id} failed: {e}")


@app.post("/api/v1/wallet/{wallet_address}", response_model=WalletAnalysisResponse)
async def analyze_wallet(
    wallet_address: str,
    background_tasks: BackgroundTasks,
    save_plots: bool = Query(default=True),
    read_cache: bool = Query(default=True),
    write_cache: bool = Query(default=True),
    filter_outliers: bool = Query(default=True),
    lookback: int = Query(default=3000)
):
    """
    Start analysis of a single wallet's trading patterns (async)

    Args:
        wallet_address: The Solana wallet address to analyze
        background_tasks: FastAPI background tasks
        save_plots: Whether to save generated plots
        read_cache: Whether to read from cache
        write_cache: Whether to write to cache
        filter_outliers: Whether to filter outlier trades
        lookback: Number of transactions to look back

    Returns:
        Analysis ID and initial status
    """
    # Generate a unique ID for this analysis
    analysis_id = str(uuid.uuid4())

    # Create the analyzer instance with analysis_id
    analyzer = WalletTradeAnalyzer(
        wallet_address,
        None,
        filter_outliers=filter_outliers,
        matched_tokens_only=False,  # No target wallet, so can't filter
        read_cache=read_cache,
        write_cache=write_cache,
        analysis_id=analysis_id
    )

    # Store the analyzer in the global dictionary
    active_analyses[analysis_id] = analyzer

    # Start the analysis in the background
    background_tasks.add_task(run_analysis, analysis_id, analyzer, lookback)

    return WalletAnalysisResponse(
        analysis_id=analysis_id,
        status="initialized",
        message=f"Analysis started for wallet {wallet_address}",
        wallet_address=wallet_address
    )


@app.get("/api/v1/analysis/{analysis_id}", response_model=WalletAnalysisResponse)
async def get_analysis_status(analysis_id: str):
    """
    Get the status of a running or completed analysis

    Args:
        analysis_id: The unique ID returned when starting the analysis

    Returns:
        Current status of the analysis, including results and file URLs if completed
    """
    if analysis_id not in active_analyses:
        return WalletAnalysisResponse(
            analysis_id=analysis_id,
            status="not_found",
            message=f"Analysis with ID {analysis_id} not found"
        )

    analyzer = active_analyses[analysis_id]

    # Prepare response
    response = WalletAnalysisResponse(
        analysis_id=analysis_id,
        status=analyzer.status,
        message=f"Analysis status: {analyzer.status}",
        wallet_address=analyzer.wallet_address,
        error_message=analyzer.error_message
    )

    # If completed, include results and file URLs
    if analyzer.status == "completed":
        response.results = analyzer.get_vital_statistics()
        plot_urls, report_url = get_analysis_file_urls(analysis_id)
        response.plot_urls = plot_urls
        response.report_url = report_url

    return response


@app.get("/api/v1/analysis/{analysis_id}/results")
async def get_analysis_results(analysis_id: str):
    """
    Get detailed results from a completed analysis

    Args:
        analysis_id: The unique ID of the analysis

    Returns:
        JSON containing vital statistics, plot URLs, and report URL
    """
    if analysis_id not in active_analyses:
        return {
            "error": "not_found",
            "message": f"Analysis with ID {analysis_id} not found"
        }

    analyzer = active_analyses[analysis_id]

    if analyzer.status != "completed":
        return {
            "error": "not_completed",
            "status": analyzer.status,
            "message": f"Analysis is {analyzer.status}, results not available yet"
        }

    # Get vital statistics
    results = analyzer.get_vital_statistics()

    # Get file URLs
    plot_urls, report_url = get_analysis_file_urls(analysis_id)

    return {
        "analysis_id": analysis_id,
        "wallet_address": analyzer.wallet_address,
        "statistics": results,
        "plot_urls": plot_urls,
        "report_url": report_url
    }


@app.post("/api/v1/wallet/{wallet_address}/{target_wallet_address}", response_model=WalletAnalysisResponse)
async def analyze_wallet_with_target(
    wallet_address: str,
    target_wallet_address: str,
    save_plots: bool = Query(default=True),
    read_cache: bool = Query(default=True),
    write_cache: bool = Query(default=True),
    lookback: int = Query(default=3000)
):
    """
    Analyze a wallet's trading patterns compared to a target wallet

    Args:
        wallet_address: The Solana wallet address to analyze
        target_wallet_address: The target wallet to compare against
        save_plots: Whether to save generated plots
        read_cache: Whether to read from cache
        write_cache: Whether to write to cache
        lookback: Number of transactions to look back

    Returns:
        Comparative analysis results (not yet implemented)
    """
    return WalletAnalysisResponse(
        status="pending",
        message=f"Comparative analysis for {wallet_address} vs {target_wallet_address} not yet implemented"
    )


@app.post("/api/v1/transaction/{tx_id}", response_model=TransactionResponse)
async def analyze_transaction(tx_id: str):
    """
    Analyze a specific transaction

    Args:
        tx_id: The transaction ID/signature to analyze

    Returns:
        Transaction analysis results (not yet implemented)
    """
    return TransactionResponse(
        status="pending",
        message=f"Transaction analysis for {tx_id} not yet implemented"
    )


@app.get("/api/v1/transaction/{tx_id}", response_model=TransactionResponse)
async def get_transaction(tx_id: str):
    """
    Get transaction details

    Args:
        tx_id: The transaction ID/signature to retrieve

    Returns:
        Transaction details (not yet implemented)
    """
    return TransactionResponse(
        status="pending",
        message=f"Transaction retrieval for {tx_id} not yet implemented"
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
