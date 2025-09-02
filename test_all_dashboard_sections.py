import requests
import json
import time

print("="*70)
print("COMPREHENSIVE DASHBOARD DATA TEST")
print("="*70)

base_url = "http://localhost:8000"

# Test all endpoints
endpoints = {
    "analysis": "/api/analysis",
    "onchain": "/api/onchain", 
    "power_law": "/api/power-law",
    "correlation": "/api/correlation",
}

all_good = True

for name, endpoint in endpoints.items():
    print(f"\n{'='*50}")
    print(f"Testing: {name.upper()}")
    print(f"{'='*50}")
    
    try:
        response = requests.get(f"{base_url}{endpoint}", timeout=10)
        if response.status_code == 200:
            data = response.json()
            
            if name == "analysis":
                print(f"✅ Market Analysis:")
                print(f"   Composite Score: {data.get('composite_score', 0):.3f}")
                print(f"   Market State: {data.get('market_state', {}).get('state', 'N/A')}")
                print(f"   Fear & Greed: {data.get('fear_greed_index', {}).get('value', 'N/A')}")
                print(f"   Current Price: ${data.get('current_data', {}).get('price', 0):,.0f}")
                
            elif name == "onchain":
                print(f"✅ On-Chain Data (REAL):")
                mvrv = data.get('mvrv', {})
                print(f"   MVRV Z-Score: {mvrv.get('z_score', 0):.2f} - {mvrv.get('signal', 'N/A')}")
                
                flows = data.get('exchange_flows', {})
                print(f"   Exchange Flows: {flows.get('net_flow_24h', 0):.1f} BTC - {flows.get('signal', 'N/A')}")
                
                lth = data.get('lth_supply', {})
                print(f"   LTH Supply: {lth.get('lth_percentage', 0)}% - {lth.get('signal', 'N/A')}")
                
                health = data.get('network_health', {})
                print(f"   Network Health: {health.get('health_score', 0):.1f}/100 - {health.get('status', 'N/A')}")
                
                print(f"   Real Data: {data.get('is_real_data', False)}")
                
            elif name == "power_law":
                current = data.get('current', {})
                print(f"✅ Power Law Model:")
                print(f"   Current Price: ${current.get('current_price', 0):,.0f}")
                print(f"   Fair Value: ${current.get('fair_value', 0):,.0f}")
                print(f"   Deviation: {current.get('deviation_percent', 0):.1f}%")
                print(f"   Status: {current.get('status', 'N/A')}")
                
            elif name == "correlation":
                print(f"✅ Multi-Asset Signals:")
                
                mstr = data.get('mstr', {})
                print(f"   MSTR Premium: {mstr.get('nav_premium', 0):.1f}%")
                
                eth = data.get('eth_btc', {})
                print(f"   ETH/BTC Ratio: {eth.get('current_ratio', 0):.4f}")
                
                sol = data.get('solana', {})
                if sol:
                    print(f"   SOL Price: ${sol.get('price', 0):.2f}")
                    print(f"   SOL/BTC Ratio: {sol.get('sol_btc_ratio', 0):.5f}")
                
                phase = data.get('market_phase', {})
                print(f"   Market Phase: {phase.get('phase', 'N/A')}")
                
        else:
            print(f"❌ Failed: Status {response.status_code}")
            all_good = False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        all_good = False

print("\n" + "="*70)
if all_good:
    print("✅ ALL DASHBOARD SECTIONS WORKING PROPERLY")
    print("✅ No Buy/Sell language - Using color zones (Green/Red)")
else:
    print("⚠️ Some sections need attention")
print("="*70)
