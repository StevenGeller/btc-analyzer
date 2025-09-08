"""
Bitcoin Power Law Calculator
Implements the Bitcoin Power Law model for fair value estimation
"""

import math
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class BitcoinPowerLaw:
    """
    Bitcoin Power Law Model
    Based on Giovanni Santostasi's power law: Price = A * (days from genesis)^n
    """
    
    # Bitcoin genesis block: January 3, 2009
    GENESIS_DATE = datetime(2009, 1, 3)
    
    # Bitcoin halving dates (historical and projected)
    HALVING_DATES = [
        datetime(2012, 11, 28),  # First halving
        datetime(2016, 7, 9),    # Second halving
        datetime(2020, 5, 11),   # Third halving
        datetime(2024, 4, 19),   # Fourth halving (actual)
        datetime(2028, 4, 1),    # Fifth halving (projected)
    ]
    
    # Power Law parameters (fitted to historical data)
    # These are commonly cited parameters for the Bitcoin power law
    A = 10**(-17.01)  # Scaling factor
    N = 5.82  # Power exponent
    
    # Support and resistance band multipliers (based on historical data)
    # Research shows bottoms consistently occur at ~0.42x (58% below fair value)
    # Tops can reach 3.2x in extreme bubbles, but intermediate levels matter
    RESISTANCE_MULTIPLIER = 3.2  # Extreme bubble top
    SUPPORT_MULTIPLIER = 0.42  # Historical bottom (~58% below fair value)
    
    # Intermediate zone multipliers for better granularity
    ZONE_MULTIPLIERS = {
        'deep_undervalued': 0.42,   # Historical bottom
        'undervalued': 0.7,          # Strong buy zone
        'fair_value_low': 0.85,      # Below fair value
        'fair_value': 1.0,           # Power law trend line
        'fair_value_high': 1.15,     # Slightly above fair
        'overheated': 1.5,           # Getting expensive
        'bubble_territory': 2.0,     # Clear bubble
        'extreme_bubble': 3.2        # Historical max deviation
    }
    
    def __init__(self):
        self.last_calculation = None
        self.cached_result = None
    
    def get_halving_context(self, date=None):
        """Calculate halving cycle context"""
        if date is None:
            date = datetime.now()
        
        # Find the last and next halving
        last_halving = None
        next_halving = None
        
        for halving_date in self.HALVING_DATES:
            if halving_date <= date:
                last_halving = halving_date
            elif next_halving is None:
                next_halving = halving_date
                break
        
        result = {}
        
        if last_halving:
            days_since_halving = (date - last_halving).days
            result['days_since_halving'] = days_since_halving
            result['last_halving'] = last_halving.strftime('%Y-%m-%d')
        
        if next_halving:
            days_to_halving = (next_halving - date).days
            result['days_to_halving'] = days_to_halving
            result['next_halving'] = next_halving.strftime('%Y-%m-%d')
            
            # Calculate position in 4-year cycle (approximately 1461 days)
            if last_halving:
                total_cycle_days = (next_halving - last_halving).days
                cycle_progress = days_since_halving / total_cycle_days
                result['cycle_position'] = round(cycle_progress * 100, 1)
                
                # Determine cycle phase
                if cycle_progress < 0.25:
                    result['cycle_phase'] = 'Post-halving accumulation'
                elif cycle_progress < 0.5:
                    result['cycle_phase'] = 'Mid-cycle rally'
                elif cycle_progress < 0.75:
                    result['cycle_phase'] = 'Late-cycle expansion'
                else:
                    result['cycle_phase'] = 'Pre-halving anticipation'
        
        return result
        
    def days_since_genesis(self, date=None):
        """Calculate days since Bitcoin genesis block"""
        if date is None:
            date = datetime.now()
        delta = date - self.GENESIS_DATE
        return max(1, delta.days)  # Ensure at least 1 day
    
    def calculate_fair_value(self, date=None):
        """Calculate Bitcoin's fair value according to power law"""
        days = self.days_since_genesis(date)
        
        # Power law formula: Price = A * days^n
        fair_value = self.A * (days ** self.N)
        
        # Calculate support and resistance bands
        resistance = fair_value * self.RESISTANCE_MULTIPLIER
        support = fair_value * self.SUPPORT_MULTIPLIER
        
        return {
            'fair_value': fair_value,
            'resistance': resistance,
            'support': support,
            'days_since_genesis': days
        }
    
    def get_power_law_status(self, current_price):
        """
        Determine if Bitcoin is over/under valued relative to power law
        Returns status and percentage deviation
        """
        try:
            # Cache calculation for 1 minute
            now = datetime.now()
            if (self.last_calculation is None or 
                (now - self.last_calculation).seconds > 60):
                
                power_law = self.calculate_fair_value()
                self.cached_result = power_law
                self.last_calculation = now
            else:
                power_law = self.cached_result
            
            fair_value = power_law['fair_value']
            resistance = power_law['resistance']
            support = power_law['support']
            
            # Calculate deviation from fair value
            deviation_pct = ((current_price - fair_value) / fair_value) * 100
            
            # Enhanced zone classification with more granularity
            price_to_fair_ratio = current_price / fair_value
            
            # Determine zone and status based on comprehensive boundaries
            if price_to_fair_ratio < self.ZONE_MULTIPLIERS['deep_undervalued']:
                zone = "DEEP_UNDERVALUED"
                status = "Extreme Undervaluation"
                color = "#00ff00"  # Bright green
                signal = "🟢🟢🟢"
                action_hint = "Historical bottom zone"
            elif price_to_fair_ratio < self.ZONE_MULTIPLIERS['undervalued']:
                zone = "UNDERVALUED"
                status = "Strong Buy Zone"
                color = "#00dd00"  # Green
                signal = "🟢🟢"
                action_hint = "Accumulation opportunity"
            elif price_to_fair_ratio < self.ZONE_MULTIPLIERS['fair_value_low']:
                zone = "BELOW_FAIR"
                status = "Below Fair Value"
                color = "#66cc66"  # Light green
                signal = "🟢"
                action_hint = "Good value zone"
            elif price_to_fair_ratio < self.ZONE_MULTIPLIERS['fair_value']:
                zone = "FAIR_VALUE_LOW"
                status = "Near Fair Value"
                color = "#99cc00"  # Yellow-green
                signal = "🟡"
                action_hint = "Approaching fair value"
            elif price_to_fair_ratio < self.ZONE_MULTIPLIERS['fair_value_high']:
                zone = "FAIR_VALUE"
                status = "Fair Value Zone"
                color = "#cccc00"  # Yellow
                signal = "🟡"
                action_hint = "Fairly valued"
            elif price_to_fair_ratio < self.ZONE_MULTIPLIERS['overheated']:
                zone = "ABOVE_FAIR"
                status = "Above Fair Value"
                color = "#ffcc00"  # Light orange
                signal = "🟠"
                action_hint = "Getting expensive"
            elif price_to_fair_ratio < self.ZONE_MULTIPLIERS['bubble_territory']:
                zone = "OVERHEATED"
                status = "Overheated Zone"
                color = "#ff9900"  # Orange
                signal = "🟠"
                action_hint = "Caution advised"
            elif price_to_fair_ratio < self.ZONE_MULTIPLIERS['extreme_bubble']:
                zone = "BUBBLE"
                status = "Bubble Territory"
                color = "#ff6600"  # Dark orange
                signal = "🔴"
                action_hint = "High risk zone"
            else:
                zone = "EXTREME_BUBBLE"
                status = "Extreme Bubble"
                color = "#ff0000"  # Red
                signal = "🔴🔴"
                action_hint = "Historical top zone"
            
            # Calculate position within band (0 to 1)
            band_range = resistance - support
            position_in_band = (current_price - support) / band_range
            position_in_band = max(0, min(1, position_in_band))  # Clamp to 0-1
            
            # Get halving cycle context
            halving_context = self.get_halving_context(now)
            
            # Calculate historical context percentages
            deviation_from_support_pct = ((current_price - support) / support) * 100
            deviation_from_resistance_pct = ((resistance - current_price) / current_price) * 100
            
            return {
                # Core metrics
                'zone': zone,
                'status': status,
                'deviation_percent': round(deviation_pct, 2),
                'fair_value': round(fair_value, 2),
                'resistance': round(resistance, 2),
                'support': round(support, 2),
                'current_price': round(current_price, 2),
                'position_in_band': round(position_in_band, 3),
                'color': color,
                'signal': signal,
                'action_hint': action_hint,
                
                # Enhanced metrics
                'price_to_fair_ratio': round(price_to_fair_ratio, 3),
                'deviation_from_support': round(deviation_from_support_pct, 1),
                'deviation_from_resistance': round(deviation_from_resistance_pct, 1),
                
                # Zone boundaries for visualization
                'zones': {
                    'deep_undervalued': round(fair_value * self.ZONE_MULTIPLIERS['deep_undervalued'], 2),
                    'undervalued': round(fair_value * self.ZONE_MULTIPLIERS['undervalued'], 2),
                    'fair_value_low': round(fair_value * self.ZONE_MULTIPLIERS['fair_value_low'], 2),
                    'fair_value': round(fair_value, 2),
                    'fair_value_high': round(fair_value * self.ZONE_MULTIPLIERS['fair_value_high'], 2),
                    'overheated': round(fair_value * self.ZONE_MULTIPLIERS['overheated'], 2),
                    'bubble': round(fair_value * self.ZONE_MULTIPLIERS['bubble_territory'], 2),
                    'extreme_bubble': round(fair_value * self.ZONE_MULTIPLIERS['extreme_bubble'], 2)
                },
                
                # Halving cycle context
                'cycle_context': halving_context,
                
                # Metadata
                'days_since_genesis': power_law['days_since_genesis'],
                'calculation_time': now.isoformat(),
                'model_confidence': 0.95  # R² value from research
            }
            
        except Exception as e:
            logger.error(f"Error calculating power law status: {e}")
            return {
                'status': 'UNKNOWN',
                'deviation_percent': 0,
                'fair_value': 0,
                'resistance': 0,
                'support': 0,
                'current_price': current_price,
                'position_in_band': 0.5,
                'color': '#888888',
                'signal': '⚪',
                'error': str(e)
            }
    
    def get_historical_power_law(self, days_back=365):
        """Get historical power law values for charting"""
        values = []
        today = datetime.now()
        
        for i in range(days_back, -1, -7):  # Weekly data points
            date = today - timedelta(days=i)
            calc = self.calculate_fair_value(date)
            values.append({
                'date': date.isoformat(),
                'fair_value': round(calc['fair_value'], 2),
                'resistance': round(calc['resistance'], 2),
                'support': round(calc['support'], 2)
            })
        
        return values

# Singleton instance
_power_law_calculator = None

def get_power_law_calculator():
    """Get or create the singleton power law calculator"""
    global _power_law_calculator
    if _power_law_calculator is None:
        _power_law_calculator = BitcoinPowerLaw()
    return _power_law_calculator