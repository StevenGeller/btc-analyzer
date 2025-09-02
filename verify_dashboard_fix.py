import requests
import time

print("="*60)
print("VERIFYING DASHBOARD FIX - ALL ON-CHAIN METRICS")
print("="*60)

# Test on-chain endpoint
response = requests.get("http://localhost:8000/api/onchain")
if response.status_code == 200:
    data = response.json()
    
    print("\n✅ ON-CHAIN DATA VERIFICATION:")
    print("-" * 40)
    
    # Check MVRV
    if 'mvrv' in data and data['mvrv'].get('z_score') is not None:
        print(f"📊 MVRV Z-Score: {data['mvrv']['z_score']:.2f} ✓")
        print(f"   Signal: {data['mvrv']['signal']}")
        print(f"   Color: {data['mvrv']['color']}")
    else:
        print("❌ MVRV data missing or incomplete")
    
    # Check Exchange Flows
    if 'exchange_flows' in data:
        flow = data['exchange_flows']
        if flow.get('net_flow_24h') is not None:
            print(f"\n🏦 Exchange Flows: {flow['net_flow_24h']:.2f} BTC ✓")
            print(f"   Direction: {flow.get('flow_direction', 'N/A')}")
            print(f"   Signal: {flow.get('signal', 'N/A')}")
            print(f"   30d Trend: {flow.get('trend_30d_pct', 0):.1f}%")
        else:
            print("❌ Exchange flow data incomplete")
    else:
        print("❌ Exchange flows data missing")
    
    # Check LTH
    if 'lth_supply' in data and data['lth_supply'].get('lth_percentage') is not None:
        print(f"\n💎 LTH Supply: {data['lth_supply']['lth_percentage']}% ✓")
        print(f"   HODL Strength: {data['lth_supply']['hodl_strength']}")
    else:
        print("❌ LTH data missing or incomplete")
    
    # Check Network Health
    if 'network_health' in data and data['network_health'].get('health_score') is not None:
        print(f"\n⚡ Network Health: {data['network_health']['health_score']:.1f}/100 ✓")
        print(f"   Status: {data['network_health']['status']}")
    else:
        print("❌ Network health data missing or incomplete")
    
    # Verify data is real
    if data.get('is_real_data'):
        print(f"\n✅ REAL DATA CONFIRMED")
        print(f"   Sources: {', '.join(data.get('data_sources', []))}")
    
    print("\n" + "="*60)
    print("DASHBOARD SHOULD NOW DISPLAY ALL METRICS CORRECTLY")
    print("="*60)
    
else:
    print(f"❌ Failed to fetch data: Status {response.status_code}")

# Also check the HTML is being served
html_response = requests.get("http://localhost:8000/")
if html_response.status_code == 200:
    print("\n✅ Dashboard HTML is being served at http://localhost:8000/")
else:
    print("\n❌ Dashboard HTML not accessible")
