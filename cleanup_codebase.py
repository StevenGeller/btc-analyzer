#!/usr/bin/env python3
"""
Codebase Cleanup and Organization Script
"""
import os
import shutil
from pathlib import Path

# Files currently in use (DO NOT DELETE)
ACTIVE_FILES = {
    'working_app.py',           # Main application
    'database.py',               # Database management
    'multi_asset_analyzer.py',   # Multi-asset correlation
    'real_whale_tracker.py',     # Real whale tracking
    'strategy_fetcher.py',       # Strategy.com data fetcher
    'microstructure_integration.py',  # Microstructure analysis
    'pattern_recognition.py',    # Pattern detection
    'unified_dashboard.html',    # Main dashboard
    'CLAUDE.md',                 # Project documentation
    'requirements.txt'           # Dependencies
}

# Files to archive (might be useful but not actively used)
ARCHIVE_FILES = {
    'app.py',                    # Old version
    'simple_app.py',             # Simple version
    'professional_app.py',       # Professional version
    'analyzer.py',               # Old analyzer
    'enhanced_analyzer.py',      # Enhanced version
    'data_fetcher.py',           # Old fetcher
    'optimized_data_fetcher.py', # Optimized version
    'test_robust_system.py',     # Test file
    'test_fetcher.py',           # Test file
    'populate_data.py',          # Data population script
    'backtester.py',             # Backtesting module
    'liquidation_tracker.py',    # Liquidation tracking
    'funding_tracker.py',        # Funding tracking
    'market_microstructure.py',  # Market microstructure
    'websocket_streamer.py',     # WebSocket streamer
    'whale_tracker.py',          # Old whale tracker (simulated)
    'fetch_mstr_actual.py',      # MSTR fetcher
    'fetch_mstr_real.py',        # MSTR fetcher
    'scrape_strategy.py'         # Strategy scraper
}

def cleanup():
    """Clean up and organize the codebase"""
    
    # Create archive directory
    archive_dir = Path('archive')
    archive_dir.mkdir(exist_ok=True)
    
    # Create organized structure
    dirs = ['core', 'api', 'utils', 'tests', 'static']
    for d in dirs:
        Path(d).mkdir(exist_ok=True)
    
    stats = {
        'archived': 0,
        'kept': 0,
        'errors': 0
    }
    
    # Archive old files
    for file in ARCHIVE_FILES:
        if os.path.exists(file):
            try:
                shutil.move(file, archive_dir / file)
                print(f"✓ Archived: {file}")
                stats['archived'] += 1
            except Exception as e:
                print(f"✗ Error archiving {file}: {e}")
                stats['errors'] += 1
    
    # List active files
    print("\n📦 Active Files:")
    for file in ACTIVE_FILES:
        if os.path.exists(file):
            size = os.path.getsize(file) / 1024
            print(f"  • {file} ({size:.1f} KB)")
            stats['kept'] += 1
    
    # Clean up __pycache__
    for root, dirs, files in os.walk('.'):
        if '__pycache__' in dirs:
            shutil.rmtree(os.path.join(root, '__pycache__'))
            print(f"✓ Removed __pycache__ from {root}")
    
    # Summary
    print(f"\n📊 Cleanup Summary:")
    print(f"  Archived: {stats['archived']} files")
    print(f"  Kept: {stats['kept']} files")
    print(f"  Errors: {stats['errors']}")
    
    return stats

if __name__ == "__main__":
    cleanup()