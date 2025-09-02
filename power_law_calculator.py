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
    
    # Power Law parameters (fitted to historical data)
    # These are commonly cited parameters for the Bitcoin power law
    A = 10**(-17.01)  # Scaling factor
    N = 5.82  # Power exponent
    
    # Support and resistance band multipliers
    RESISTANCE_MULTIPLIER = 3.2  # Upper band (overvalued)
    SUPPORT_MULTIPLIER = 0.35  # Lower band (undervalued)
    
    def __init__(self):
        self.last_calculation = None
        self.cached_result = None
        
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
            
            # Determine status
            if current_price > resistance:
                status = "EXTREMELY_OVERVALUED"
                color = "#ff0000"  # Red
                signal = "🔴"
            elif current_price > fair_value * 1.5:
                status = "OVERVALUED"
                color = "#ff6600"  # Orange
                signal = "🟠"
            elif current_price > fair_value:
                status = "ABOVE_FAIR_VALUE"
                color = "#ffcc00"  # Yellow
                signal = "🟡"
            elif current_price > support:
                status = "BELOW_FAIR_VALUE"
                color = "#00cc66"  # Light green
                signal = "🟢"
            else:
                status = "UNDERVALUED"
                color = "#00ff00"  # Bright green
                signal = "🟢"
            
            # Calculate position within band (0 to 1)
            band_range = resistance - support
            position_in_band = (current_price - support) / band_range
            position_in_band = max(0, min(1, position_in_band))  # Clamp to 0-1
            
            return {
                'status': status,
                'deviation_percent': round(deviation_pct, 2),
                'fair_value': round(fair_value, 2),
                'resistance': round(resistance, 2),
                'support': round(support, 2),
                'current_price': round(current_price, 2),
                'position_in_band': round(position_in_band, 3),
                'color': color,
                'signal': signal,
                'days_since_genesis': power_law['days_since_genesis'],
                'calculation_time': now.isoformat()
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