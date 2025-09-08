#!/usr/bin/env python3
"""
Test the improved Power Law calculator with corrected boundaries
"""

import asyncio
import json
from power_law_calculator import get_power_law_calculator
from datetime import datetime

def print_zone_visualization(price, zones, fair_value):
    """Print a visual representation of price zones"""
    print("\n📊 POWER LAW ZONES:")
    print("=" * 60)
    
    # Create price scale
    min_price = zones['deep_undervalued']
    max_price = zones['extreme_bubble']
    price_range = max_price - min_price
    
    # Print zones from top to bottom
    zone_levels = [
        ('extreme_bubble', '🔴🔴 Extreme Bubble (>3.2x)', '#ff0000'),
        ('bubble', '🔴 Bubble Territory (2.0-3.2x)', '#ff6600'),
        ('overheated', '🟠 Overheated (1.5-2.0x)', '#ff9900'),
        ('fair_value_high', '🟠 Above Fair (1.15-1.5x)', '#ffcc00'),
        ('fair_value', '🟡 Fair Value Zone (1.0x)', '#cccc00'),
        ('fair_value_low', '🟡 Near Fair (0.85-1.0x)', '#99cc00'),
        ('undervalued', '🟢 Undervalued (0.7-0.85x)', '#66cc66'),
        ('deep_undervalued', '🟢🟢 Deep Undervalued (<0.42x)', '#00ff00')
    ]
    
    print(f"Current Price: ${price:,.0f}")
    print("-" * 60)
    
    for zone_key, label, color in zone_levels:
        zone_price = zones.get(zone_key, 0)
        if zone_price:
            marker = "→ YOU ARE HERE" if abs(price - zone_price) < price_range * 0.05 else ""
            print(f"${zone_price:>8,.0f} | {label:<35} {marker}")
    
    print("-" * 60)
    print(f"Fair Value: ${fair_value:,.0f}")

async def test_power_law():
    """Test the improved power law calculator"""
    calc = get_power_law_calculator()
    
    # Test with different price scenarios
    test_prices = [
        45000,   # Below fair value  
        103000,  # Near fair value
        111940,  # Current price (slightly above)
        150000,  # Overheated
        200000,  # Bubble territory
        300000,  # Extreme bubble
        35000,   # Deep undervalued
    ]
    
    print("🚀 BITCOIN POWER LAW CALCULATOR - IMPROVED VERSION")
    print("=" * 80)
    
    for test_price in test_prices:
        result = calc.get_power_law_status(test_price)
        
        print(f"\n💰 Test Price: ${test_price:,.0f}")
        print("-" * 60)
        
        # Core metrics
        print(f"📈 Zone: {result['zone']}")
        print(f"📊 Status: {result['status']} {result['signal']}")
        print(f"💡 Action: {result['action_hint']}")
        print(f"📍 Deviation from Fair Value: {result['deviation_percent']:+.1f}%")
        
        # Boundaries
        print(f"\n📏 Key Levels:")
        print(f"  • Support (0.42x): ${result['support']:,.0f} ({result['deviation_from_support']:+.1f}% from here)")
        print(f"  • Fair Value (1.0x): ${result['fair_value']:,.0f}")
        print(f"  • Resistance (3.2x): ${result['resistance']:,.0f} ({result['deviation_from_resistance']:+.1f}% from here)")
        
        # Halving context
        if 'cycle_context' in result and result['cycle_context']:
            ctx = result['cycle_context']
            print(f"\n⏰ Halving Cycle Context:")
            if 'days_since_halving' in ctx:
                print(f"  • Days since last halving: {ctx['days_since_halving']} ({ctx['last_halving']})")
            if 'days_to_halving' in ctx:
                print(f"  • Days to next halving: {ctx['days_to_halving']} ({ctx['next_halving']})")
            if 'cycle_position' in ctx:
                print(f"  • Cycle progress: {ctx['cycle_position']}%")
                print(f"  • Cycle phase: {ctx['cycle_phase']}")
        
        # Model confidence
        print(f"\n📊 Model Confidence: {result['model_confidence']*100:.0f}% (R² value)")
        
        # Visual representation for current price scenario
        if test_price == 111940:
            print_zone_visualization(test_price, result['zones'], result['fair_value'])
    
    # Historical context
    print("\n" + "=" * 80)
    print("📚 HISTORICAL CONTEXT (Based on Research):")
    print("-" * 60)
    print("• 2021 Peak: ~$69,000 (reached ~2.5x fair value)")
    print("• 2022 Bottom: ~$15,500 (reached ~0.4x fair value, -60% from trend)")
    print("• FTX collapse caused deeper than normal bottom")
    print("• Model R² improved from 0.92 to 0.95 since 2018")
    print("• Bottoms consistently occur at ~0.42x fair value (-58%)")
    print("• Tops can reach 3.2x in extreme bubbles")
    
    print("\n✅ Power Law Calculator Test Complete!")

if __name__ == "__main__":
    asyncio.run(test_power_law())