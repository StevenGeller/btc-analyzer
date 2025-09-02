import asyncio
import aiohttp
import json

async def test_dashboard():
    async with aiohttp.ClientSession() as session:
        # Get whale data
        async with session.get('http://localhost:8000/api/whale') as resp:
            whale_data = await resp.json()
            
        print("WHALE METRICS TEST")
        print("-" * 50)
        
        metrics = whale_data.get('whale_metrics', {})
        if 'metrics' in metrics:
            m = metrics['metrics']['24h']
            print(f"24h Whale TXs: {m['tx_count']} ({m['total_btc']:.0f} BTC)")
            
            # Show comparisons
            comp = metrics.get('comparisons', {})
            if comp.get('dod'):
                dod = comp['dod']['tx_change']
                print(f"  DoD: {'↑' if dod > 0 else '↓' if dod < 0 else '→'}{abs(dod):.0f}%")
            if comp.get('wow'):
                wow = comp['wow']['tx_change']
                print(f"  WoW: {'+' if wow > 0 else ''}{wow:.0f}%")
            if comp.get('mom'):
                mom = comp['mom']['tx_change']
                print(f"  MoM: {'+' if mom > 0 else ''}{mom:.0f}%")
            if comp.get('yoy'):
                yoy = comp['yoy']['tx_change']
                print(f"  YoY: {'+' if yoy > 0 else ''}{yoy:.0f}%")
            if comp.get('4y_cycle'):
                print(f"  🔄 {comp['4y_cycle']['cycle_position']}")
                
        # Check for duplicate recommendations
        async with session.get('http://localhost:8000/api/bitcoin-data') as resp:
            btc_data = await resp.json()
            
        print("\nRECOMMENDATIONS CHECK")
        print("-" * 50)
        
        if 'recommendations' in btc_data:
            for rec in btc_data['recommendations']:
                msg = rec.get('message', '')
                if 'Real-time Bitcoin' in msg or 'Fear & Greed' in msg:
                    print(f"DUPLICATE FOUND: {msg}")
                    
        print("\nDashboard should now display:")
        print("- Whale TXs with DoD/WoW/MoM/YoY comparisons")
        print("- 4-year cycle position")
        print("- No duplicate INFO messages")
        print("- Phase detection logic with all conditions")

asyncio.run(test_dashboard())
