#!/usr/bin/env python3
"""Test the MSTR holdings fetcher"""

import asyncio
from mstr_holdings_fetcher import get_fetcher

async def test():
    fetcher = get_fetcher()
    try:
        print("Testing MSTR Holdings Fetcher...")
        data = await fetcher.update_holdings()
        print('\nFetched MSTR Holdings:')
        print(f'  BTC Holdings: {data.get("btc_holdings", "N/A")} BTC')
        print(f'  Avg Cost: ${data.get("avg_cost_basis", "N/A")}')
        print(f'  Stock Price: ${data.get("stock_price", "N/A")}')
        print(f'  Market Cap: ${data.get("market_cap", "N/A")}')
        print(f'  Source: {data.get("source", "N/A")}')
        print(f'  Timestamp: {data.get("timestamp", "N/A")}')
        
        # Test database retrieval
        print("\nFrom Database:")
        db_data = fetcher.get_latest_holdings()
        print(f'  BTC Holdings: {db_data.get("btc_holdings", "N/A")} BTC')
        print(f'  Source: {db_data.get("source", "N/A")}')
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await fetcher.cleanup()

if __name__ == "__main__":
    asyncio.run(test())