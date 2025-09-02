#!/usr/bin/env python3
"""
Test script to verify all on-chain data endpoints are working
"""

import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8000"

def test_endpoint(name, endpoint):
    """Test a single endpoint"""
    print(f"\n{'='*60}")
    print(f"Testing: {name}")
    print(f"Endpoint: {endpoint}")
    print(f"{'='*60}")
    
    try:
        response = requests.get(f"{BASE_URL}{endpoint}", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Success! Status: {response.status_code}")
            print(f"Response data:")
            print(json.dumps(data, indent=2, default=str))
            
            # Validate key fields for on-chain data
            if endpoint == "/api/onchain":
                if 'mvrv' in data:
                    print(f"\n📊 MVRV Data:")
                    print(f"  - MVRV Ratio: {data['mvrv'].get('mvrv', 'N/A')}")
                    print(f"  - Z-Score: {data['mvrv'].get('z_score', 'N/A')}")
                    print(f"  - Condition: {data['mvrv'].get('condition', 'N/A')}")
                    
                if 'exchange_flows' in data:
                    print(f"\n💰 Exchange Flows:")
                    print(f"  - Net Flow 24h: {data['exchange_flows'].get('net_flow_24h', 'N/A')} BTC")
                    print(f"  - Direction: {data['exchange_flows'].get('flow_direction', 'N/A')}")
                    print(f"  - Signal: {data['exchange_flows'].get('signal', 'N/A')}")
                    
                if 'lth_supply' in data:
                    print(f"\n💎 Long-Term Holders:")
                    print(f"  - LTH %: {data['lth_supply'].get('lth_percentage', 'N/A')}%")
                    print(f"  - HODL Strength: {data['lth_supply'].get('hodl_strength', 'N/A')}")
                    print(f"  - Change 30d: {data['lth_supply'].get('change_30d_pct', 'N/A')}%")
                    
                if 'network_health' in data:
                    print(f"\n⚡ Network Health:")
                    print(f"  - Score: {data['network_health'].get('health_score', 'N/A')}/100")
                    print(f"  - Status: {data['network_health'].get('status', 'N/A')}")
                    print(f"  - Hash Rate: {data['network_health'].get('hash_rate', 'N/A')}")
                    
                # Check if data sources are real
                if 'is_real_data' in data:
                    print(f"\n🔍 Data Verification:")
                    print(f"  - Is Real Data: {data.get('is_real_data', False)}")
                    print(f"  - Data Sources: {data.get('data_sources', [])}")
                    
        else:
            print(f"❌ Failed! Status: {response.status_code}")
            print(f"Response: {response.text}")
            
    except requests.exceptions.Timeout:
        print(f"⏱️ Timeout! Endpoint took too long to respond")
    except requests.exceptions.ConnectionError:
        print(f"🔌 Connection Error! Is the server running?")
    except Exception as e:
        print(f"💥 Error: {e}")

def main():
    print("="*60)
    print("ON-CHAIN DATA ENDPOINT TESTER")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("="*60)
    
    # Test all critical endpoints
    endpoints = [
        ("On-Chain Analytics", "/api/onchain"),
        ("Power Law Status", "/api/power-law"),
        ("Current Price", "/api/price/current"),
        ("Correlation Data", "/api/correlation"),
        ("Market Analysis", "/api/analysis")
    ]
    
    for name, endpoint in endpoints:
        test_endpoint(name, endpoint)
    
    print("\n" + "="*60)
    print("TESTING COMPLETE")
    print("="*60)

if __name__ == "__main__":
    main()