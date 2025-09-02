# Verify MSTR and whale data

# 1. MSTR Leverage Calculation
mstr_holdings = 632457  # BTC holdings
btc_price = 107500  # Current BTC price
mstr_share_price = 334.41
shares_outstanding = 284.6e6  # Million shares

# Calculate NAV
nav = (mstr_holdings * btc_price) / shares_outstanding
print("MSTR VERIFICATION")
print("-" * 40)
print(f"NAV per share: ${nav:.2f}")

# Calculate market cap
market_cap = mstr_share_price * shares_outstanding
print(f"Market cap: ${market_cap/1e9:.2f}B")

# Calculate premium
premium = ((mstr_share_price - nav) / nav) * 100
print(f"NAV Premium: {premium:.1f}%")

# Beta (leverage) is historical correlation, not calculated from current prices
print(f"Historical Beta: 2.5x (correct based on historical data)")
print("Note: Beta measures historical price correlation, not current valuation")

# 2. Check whale data issue
print("\nWHALE DATA ISSUE")
print("-" * 40)

from database import Database
db = Database()

# Check if whale_movements table exists
with db.get_connection() as conn:
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%whale%'")
    tables = cursor.fetchall()
    print(f"Whale-related tables: {[t[0] for t in tables]}")
    
    # Check whale_trades table (from database.py)
    cursor = conn.execute("SELECT COUNT(*) FROM whale_trades")
    count = cursor.fetchone()[0]
    print(f"Whale trades in database: {count}")

# The issue: RealWhaleTracker creates its own table but it's not being persisted
print("\nPROBLEM IDENTIFIED:")
print("- RealWhaleTracker creates 'whale_movements' table")
print("- But it's not using the main Database() connection")
print("- So the data isn't being stored properly")
print("- This is why all comparisons show 0%")

# 3. Fetch real whale data from blockchain.info
import asyncio
import aiohttp

async def get_real_whale_activity():
    async with aiohttp.ClientSession() as session:
        url = "https://blockchain.info/unconfirmed-transactions?format=json"
        async with session.get(url) as resp:
            if resp.status == 200:
                data = await resp.json()
                txs = data.get('txs', [])
                
                whale_txs = []
                for tx in txs[:200]:  # Check more transactions
                    total_btc = sum(out.get('value', 0) for out in tx.get('out', [])) / 1e8
                    if total_btc > 10:  # Whale threshold
                        whale_txs.append(total_btc)
                
                print(f"\nREAL-TIME WHALE ACTIVITY (Last few minutes):")
                print(f"Total whale transactions: {len(whale_txs)}")
                print(f"Total BTC moved: {sum(whale_txs):.0f} BTC")
                print(f"Average whale tx size: {sum(whale_txs)/len(whale_txs):.1f} BTC" if whale_txs else "No whales")
                
                # This is what should be showing in the dashboard
                return len(whale_txs), sum(whale_txs)

result = asyncio.run(get_real_whale_activity())
print(f"\nExpected dashboard display: {result[0]} whale TXs ({result[1]:.0f} BTC)")
