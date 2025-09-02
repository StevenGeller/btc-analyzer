import requests
import json

print("="*70)
print("TESTING ENHANCED NETWORK HEALTH INSIGHTS")
print("="*70)

# Fetch on-chain data
response = requests.get("http://localhost:8000/api/onchain")
if response.status_code == 200:
    data = response.json()
    
    if 'network_health' in data:
        nh = data['network_health']
        
        print(f"\n⚡ NETWORK HEALTH SCORE: {nh.get('health_score', 0):.1f}/100")
        print(f"   Status: {nh.get('status', 'N/A')} ({nh.get('color', '#888')})")
        print(f"\n📊 MAIN INSIGHT:")
        print(f"   {nh.get('main_insight', 'No insight available')}")
        
        print(f"\n📈 DETAILED METRICS:")
        print(f"   Hash Rate: {nh.get('hash_rate_th', 0):.1f} TH/s")
        print(f"   Daily Transactions: {nh.get('daily_transactions', 0):,}")
        print(f"   Mempool Size: {nh.get('mempool_size', 0):,} txs")
        print(f"   Block Time: {nh.get('minutes_between_blocks', 10):.1f} minutes")
        
        if 'components' in nh:
            comp = nh['components']
            print(f"\n🎯 SCORE BREAKDOWN (100 points total):")
            print(f"   Hash Rate:    {comp.get('hash_score', 0):5.1f}/40 pts")
            print(f"   Transactions: {comp.get('tx_score', 0):5.1f}/30 pts")
            print(f"   Mempool:      {comp.get('mempool_score', 0):5.1f}/15 pts")
            print(f"   Block Time:   {comp.get('block_score', 0):5.1f}/15 pts")
            print(f"   {'─'*30}")
            print(f"   TOTAL:        {nh.get('health_score', 0):5.1f}/100 pts")
        
        if 'breakdown' in nh:
            print(f"\n💡 COMPONENT INSIGHTS:")
            for key, value in nh['breakdown'].items():
                print(f"   • {key.replace('_', ' ').title()}: {value}")
        
        if 'insights' in nh and len(nh['insights']) > 0:
            print(f"\n⚠️ KEY INSIGHTS:")
            for insight in nh['insights']:
                print(f"   {insight}")
        
        print(f"\n📝 EXPLANATION:")
        print(f"   The score of {nh.get('health_score', 0):.0f}/100 indicates the network is")
        print(f"   {nh.get('status', 'UNKNOWN').lower()} because:")
        
        # Explain the score
        score = nh.get('health_score', 0)
        if score < 40:
            print("   - Multiple components are underperforming")
            print("   - Network may be experiencing stress or low activity")
        elif score < 60:
            print("   - Some components are below optimal levels")
            print("   - Network is stable but not at peak performance")
        elif score < 80:
            print("   - Most components are performing well")
            print("   - Network is healthy with room for improvement")
        else:
            print("   - All components are at or near optimal levels")
            print("   - Network security and activity are excellent")
            
    else:
        print("❌ No network health data available")
        
else:
    print(f"❌ Failed to fetch data: {response.status_code}")

print("\n" + "="*70)
print("Network health insights provide transparency into the score calculation")
print("="*70)
