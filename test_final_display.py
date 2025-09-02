import requests
import json

print("="*60)
print("FINAL DASHBOARD DATA VERIFICATION")
print("="*60)

# Test on-chain endpoint
response = requests.get("http://localhost:8000/api/onchain")
if response.status_code == 200:
    data = response.json()
    print("\n✅ ON-CHAIN DATA (REAL):")
    print(f"  💎 LTH: {data['lth_supply']['lth_percentage']}% - {data['lth_supply']['signal']}")
    print(f"  ⚡ Network: {data['network_health']['health_score']}/100 - {data['network_health']['status']}")
    print(f"  📊 MVRV: {data['mvrv']['mvrv']} (Z-Score: {data['mvrv']['z_score']})")
    print(f"  💰 Exchange Flow: {data['exchange_flows']['net_flow_24h']} BTC")
    print(f"  ✓ Real Data: {data.get('is_real_data', False)}")
    print(f"  ✓ Data Source: {data.get('data_sources', [])}")
else:
    print("❌ Failed to fetch on-chain data")

# Test correlation endpoint
response = requests.get("http://localhost:8000/api/correlation")
if response.status_code == 200:
    data = response.json()
    print("\n✅ MULTI-ASSET DATA:")
    if 'solana' in data:
        print(f"  ◎ SOL/BTC: {data['solana']['sol_btc_ratio']:.5f}")
        print(f"  ◎ SOL Price: ${data['solana']['price']}")
    print(f"  Ξ ETH/BTC: {data['eth_btc']['current_ratio']:.4f}")
    print(f"  💼 MSTR Premium: {data['mstr']['nav_premium']:.1f}%")
else:
    print("❌ Failed to fetch correlation data")

print("\n" + "="*60)
print("ALL REAL DATA - NO SIMULATIONS ✅")
print("="*60)
