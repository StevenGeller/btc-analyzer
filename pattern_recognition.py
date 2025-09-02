from typing import List, Dict, Optional, Tuple
import math
import time
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class AdvancedPatternDetector:
    """
    Detects complex market patterns that actually matter for trading decisions.
    Focuses on institutional behavior, not just technical analysis.
    """
    
    def __init__(self, database):
        self.db = database
        self.patterns = {}
        
    async def detect_wyckoff_phase(self, lookback_hours: int = 24) -> Dict:
        """
        Identify Wyckoff accumulation/distribution phases.
        These patterns show institutional accumulation/distribution.
        """
        try:
            # Get price and volume data
            price_data = self.db.get_latest_price_data(hours=lookback_hours)
            
            if len(price_data) < 50:
                return {'phase': 'insufficient_data', 'confidence': 0}
            
            # Extract price and volume arrays
            prices = [float(p['price']) for p in price_data]
            volumes = [float(p['volume_24h'] if p['volume_24h'] else 0) for p in price_data if p['volume_24h']]
            
            if len(volumes) < len(prices) // 2:  # Not enough volume data
                return {'phase': 'insufficient_volume_data', 'confidence': 0}
            
            # Pad volumes to match prices length
            while len(volumes) < len(prices):
                volumes.append(volumes[-1] if volumes else 0)
            
            # Calculate moving averages
            price_sma_20 = self._moving_average(prices, 20)
            volume_sma_20 = self._moving_average(volumes, 20)
            
            # Detect trading range
            recent_high = max(prices[-100:]) if len(prices) >= 100 else max(prices)
            recent_low = min(prices[-100:]) if len(prices) >= 100 else min(prices)
            price_range = recent_high - recent_low
            
            # Calculate historical range for comparison
            historical_ranges = []
            for i in range(0, len(prices) - 50, 10):
                hist_high = max(prices[i:i+50])
                hist_low = min(prices[i:i+50])
                historical_ranges.append(hist_high - hist_low)
            
            avg_historical_range = sum(historical_ranges) / len(historical_ranges) if historical_ranges else price_range
            
            # Is market ranging? (current range < 70% of historical average)
            is_ranging = price_range < avg_historical_range * 0.7
            
            if not is_ranging:
                current_price = prices[-1]
                price_change_pct = ((current_price - prices[0]) / prices[0]) * 100
                
                if current_price > (recent_high + recent_low) / 2:
                    return {
                        'phase': 'uptrend',
                        'confidence': 0.8,
                        'action': 'BUY',
                        'message': f'📈 UPTREND CONFIRMED - Price up {price_change_pct:+.1f}% - Consider buying',
                        'simple_signal': 'BUY'
                    }
                else:
                    return {
                        'phase': 'downtrend', 
                        'confidence': 0.8,
                        'action': 'SELL',
                        'message': f'📉 DOWNTREND CONFIRMED - Price down {abs(price_change_pct):.1f}% - Consider selling',
                        'simple_signal': 'SELL'
                    }
            
            # Analyze volume patterns in range
            recent_volume = sum(volumes[-20:]) / len(volumes[-20:]) if len(volumes) >= 20 else sum(volumes) / len(volumes) if volumes else 0
            historical_volume = sum(volumes[:-20]) / len(volumes[:-20]) if len(volumes) > 40 else recent_volume
            
            # Spring detection (false breakdown with volume spike)
            spring_detected = self._detect_spring(prices, volumes, recent_low)
            if spring_detected['detected']:
                return {
                    'phase': 'fake_dump',
                    'confidence': spring_detected['confidence'],
                    'action': 'STRONG BUY',
                    'message': f'🚀 FAKE DUMP DETECTED - Whales buying at ${spring_detected["level"]:,.0f}. Expect strong bounce!',
                    'price_level': spring_detected['level'],
                    'simple_signal': 'STRONG BUY'
                }
            
            # UTAD detection (false breakout with volume decline)
            utad_detected = self._detect_utad(prices, volumes, recent_high)
            if utad_detected['detected']:
                return {
                    'phase': 'false_breakout',
                    'confidence': utad_detected['confidence'],
                    'action': 'STRONG SELL',
                    'message': f'FAKE PUMP detected - Big players selling at ${utad_detected["level"]:,.0f}. Price likely to dump hard.',
                    'price_level': utad_detected['level'],
                    'pattern_type': 'fake_pump'
                }
            
            # Test phase detection (low volume after range)
            if recent_volume < historical_volume * 0.6:
                # Check if price is holding above/below range
                current_price = prices[-1]
                range_middle = (recent_high + recent_low) / 2
                
                if current_price > range_middle:
                    return {
                        'phase': 'accumulation_test',
                        'confidence': 0.7,
                        'action': 'prepare_for_markup',
                        'message': f'🚀 BREAKOUT COMING - Price testing resistance. Get ready to buy!',
                        'price_level': recent_high,
                        'pattern_type': 'wyckoff_test'
                    }
                else:
                    return {
                        'phase': 'distribution_test',
                        'confidence': 0.7,
                        'action': 'prepare_for_markdown',
                        'message': f'📉 BREAKDOWN COMING - Price testing support. Get ready to sell!',
                        'price_level': recent_low,
                        'pattern_type': 'wyckoff_test'
                    }
            
            # Default ranging state
            return {
                'phase': 'ranging',
                'confidence': 0.5,
                'action': 'wait_for_breakout',
                'message': f'💤 SIDEWAYS MARKET - Bitcoin stuck between ${recent_low:.0f} - ${recent_high:.0f}. Wait for breakout!',
                'support_level': recent_low,
                'resistance_level': recent_high
            }
            
        except Exception as e:
            logger.error(f"Wyckoff analysis error: {e}")
            return {'phase': 'error', 'error': str(e), 'confidence': 0}
    
    def _detect_spring(self, prices: List[float], volumes: List[float], 
                      support_level: float) -> Dict:
        """Detect Wyckoff spring pattern (false breakdown)"""
        try:
            if len(prices) < 50:
                return {'detected': False}
            
            recent_prices = prices[-30:]  # Last 30 periods
            recent_volumes = volumes[-30:] if len(volumes) >= 30 else volumes
            
            # Find the lowest point in recent data
            lowest_idx = recent_prices.index(min(recent_prices))
            lowest_price = recent_prices[lowest_idx]
            
            # Must break below support level
            if lowest_price >= support_level * 0.995:  # 0.5% below support
                return {'detected': False}
            
            # Must recover above the breakdown point
            current_price = prices[-1]
            if current_price <= lowest_price * 1.01:  # Must be 1% above low
                return {'detected': False}
            
            # Volume analysis - spring should have above average volume
            if len(recent_volumes) > lowest_idx:
                spring_volume = recent_volumes[lowest_idx]
                avg_volume = sum(recent_volumes) / len(recent_volumes) if recent_volumes else 1
                
                if spring_volume < avg_volume * 1.2:  # 20% above average
                    return {'detected': False}
            
            # Calculate confidence based on:
            # 1. How quickly it recovered
            # 2. Volume spike magnitude
            # 3. Distance below support
            
            recovery_speed = (lowest_idx + 1) / len(recent_prices)  # Faster = higher confidence
            volume_spike = spring_volume / avg_volume if len(recent_volumes) > lowest_idx else 1
            breakdown_depth = (support_level - lowest_price) / support_level
            
            confidence = min(0.95, (
                (1 - recovery_speed) * 0.4 +  # Quick recovery is good
                min(1, (volume_spike - 1) * 2) * 0.4 +  # Volume spike is good
                min(1, breakdown_depth * 20) * 0.2  # Small breakdown is good
            ))
            
            return {
                'detected': True,
                'confidence': max(0.3, confidence),
                'level': lowest_price,
                'recovery_price': current_price,
                'volume_spike': volume_spike
            }
            
        except Exception as e:
            logger.error(f"Spring detection error: {e}")
            return {'detected': False}
    
    def _detect_utad(self, prices: List[float], volumes: List[float],
                    resistance_level: float) -> Dict:
        """Detect UTAD pattern (false breakout)"""
        try:
            if len(prices) < 50:
                return {'detected': False}
            
            recent_prices = prices[-30:]
            recent_volumes = volumes[-30:] if len(volumes) >= 30 else volumes
            
            # Find the highest point
            highest_idx = recent_prices.index(max(recent_prices))
            highest_price = recent_prices[highest_idx]
            
            # Must break above resistance
            if highest_price <= resistance_level * 1.005:  # 0.5% above resistance
                return {'detected': False}
            
            # Must have declined from the high
            current_price = prices[-1]
            if current_price >= highest_price * 0.99:  # Must be 1% below high
                return {'detected': False}
            
            # Volume analysis - UTAD should have declining volume
            if len(recent_volumes) > highest_idx:
                utad_volume = recent_volumes[highest_idx]
                prev_volume = sum(recent_volumes[:highest_idx]) / len(recent_volumes[:highest_idx]) if highest_idx > 5 and recent_volumes[:highest_idx] else utad_volume
                
                if utad_volume >= prev_volume * 0.8:  # Should be less than 80% of previous
                    return {'detected': False}
            
            # Calculate confidence
            decline_speed = (len(recent_prices) - highest_idx) / len(recent_prices)
            volume_decline = prev_volume / utad_volume if utad_volume > 0 else 1
            breakout_extent = (highest_price - resistance_level) / resistance_level
            
            confidence = min(0.95, (
                decline_speed * 0.4 +  # Quick decline after breakout
                min(1, (volume_decline - 1) * 2) * 0.4 +  # Volume should decline
                min(1, breakout_extent * 50) * 0.2  # Small breakout is more reliable
            ))
            
            return {
                'detected': True,
                'confidence': max(0.3, confidence),
                'level': highest_price,
                'current_price': current_price,
                'volume_decline': volume_decline
            }
            
        except Exception as e:
            logger.error(f"UTAD detection error: {e}")
            return {'detected': False}
    
    async def detect_stop_hunts(self, lookback_hours: int = 12) -> Dict:
        """
        Detect stop-loss hunting behavior - when price briefly moves to trigger stops
        then reverses. This shows institutional manipulation.
        """
        try:
            price_data = self.db.get_latest_price_data(hours=lookback_hours)
            
            if len(price_data) < 30:
                return {'stop_hunt': False, 'message': 'Insufficient data'}
            
            # Extract price arrays
            prices = [float(p['price']) for p in price_data]
            highs = [float(p['high_24h'] if p['high_24h'] else p['price']) for p in price_data]
            lows = [float(p['low_24h'] if p['low_24h'] else p['price']) for p in price_data]
            volumes = [float(p['volume_24h'] if p['volume_24h'] else 0) for p in price_data]
            
            # Find swing points (local extremes) - simplified version
            swing_highs = self._find_local_maxima(highs, window=3)
            swing_lows = self._find_local_minima(lows, window=3)
            
            if len(swing_highs) == 0 and len(swing_lows) == 0:
                return {'stop_hunt': False, 'message': 'No clear swing points found'}
            
            current_price = prices[-1]
            current_time_idx = len(prices) - 1
            
            # Check for stop hunt above recent highs
            for high_idx in swing_highs:
                if high_idx < len(highs) - 20:  # Must be recent
                    continue
                    
                swing_high = highs[high_idx]
                
                # Look for penetration above swing high followed by reversal
                penetration_detected = False
                reversal_detected = False
                
                for i in range(high_idx, min(len(highs), high_idx + 10)):
                    if highs[i] > swing_high * 1.002:  # 0.2% above swing high
                        penetration_detected = True
                        
                        # Check for quick reversal within next few periods
                        for j in range(i, min(len(prices), i + 5)):
                            if prices[j] < swing_high * 0.998:  # Back below swing high
                                reversal_detected = True
                                break
                        break
                
                if penetration_detected and reversal_detected:
                    # Verify with volume (stop hunts often have volume spikes)
                    hunt_volume = volumes[high_idx:min(len(volumes), high_idx + 5)]
                    avg_volume = sum(volumes) / len(volumes) if volumes else 1
                    volume_spike = max(hunt_volume) / avg_volume if avg_volume > 0 else 1
                    
                    confidence = min(0.9, 0.4 + min(0.5, (volume_spike - 1) * 0.5))
                    
                    return {
                        'stop_hunt': True,
                        'type': 'bull_trap',
                        'level': swing_high,
                        'confidence': confidence,
                        'action': 'expect_decline',
                        'message': f'Stop hunt above ${swing_high:,.0f} - bull trap detected',
                        'volume_spike': volume_spike,
                        'pattern_type': 'stop_hunt'
                    }
            
            # Check for stop hunt below recent lows
            for low_idx in swing_lows:
                if low_idx < len(lows) - 20:
                    continue
                    
                swing_low = lows[low_idx]
                
                penetration_detected = False
                reversal_detected = False
                
                for i in range(low_idx, min(len(lows), low_idx + 10)):
                    if lows[i] < swing_low * 0.998:  # 0.2% below swing low
                        penetration_detected = True
                        
                        for j in range(i, min(len(prices), i + 5)):
                            if prices[j] > swing_low * 1.002:  # Back above swing low
                                reversal_detected = True
                                break
                        break
                
                if penetration_detected and reversal_detected:
                    hunt_volume = volumes[low_idx:min(len(volumes), low_idx + 5)]
                    avg_volume = sum(volumes) / len(volumes) if volumes else 1
                    volume_spike = max(hunt_volume) / avg_volume if avg_volume > 0 else 1
                    
                    confidence = min(0.9, 0.4 + min(0.5, (volume_spike - 1) * 0.5))
                    
                    return {
                        'stop_hunt': True,
                        'type': 'bear_trap',
                        'level': swing_low,
                        'confidence': confidence,
                        'action': 'expect_rally',
                        'message': f'Stop hunt below ${swing_low:,.0f} - bear trap detected',
                        'volume_spike': volume_spike,
                        'pattern_type': 'stop_hunt'
                    }
            
            return {'stop_hunt': False, 'message': 'No stop hunt patterns detected'}
            
        except Exception as e:
            logger.error(f"Stop hunt detection error: {e}")
            return {'stop_hunt': False, 'error': str(e)}
    
    async def detect_momentum_divergence(self, lookback_hours: int = 48) -> Dict:
        """
        Detect price/momentum divergences using RSI and price action.
        These show weakening momentum before reversals.
        """
        try:
            # Get price data with indicators
            with self.db.get_connection() as conn:
                cursor = conn.execute("""
                    SELECT p.timestamp, p.price, p.high_24h, p.low_24h,
                           i.rsi_14
                    FROM price_data p
                    LEFT JOIN indicators i ON p.timestamp = i.timestamp
                    WHERE p.timestamp > ?
                    ORDER BY p.timestamp ASC
                """, (int((datetime.now() - timedelta(hours=lookback_hours)).timestamp()),))
                
                data = cursor.fetchall()
            
            if len(data) < 50:
                return {'divergence': None, 'message': 'Insufficient data with RSI'}
            
            # Extract arrays
            prices = [float(d['price']) for d in data]
            rsi_values = [float(d['rsi_14']) for d in data if d['rsi_14'] is not None]
            
            # If not enough RSI data, calculate simple momentum proxy
            if len(rsi_values) < len(prices) // 2:
                rsi_values = self._calculate_simple_rsi(prices)
            
            # Ensure equal length
            min_len = min(len(prices), len(rsi_values))
            prices = prices[:min_len]
            rsi_values = rsi_values[:min_len]
            
            # Find peaks and troughs - simplified version
            price_peaks = self._find_local_maxima(prices, window=5)
            price_troughs = self._find_local_minima(prices, window=5)
            rsi_peaks = self._find_local_maxima(rsi_values, window=5)
            rsi_troughs = self._find_local_minima(rsi_values, window=5)
            
            # Bearish divergence: higher price peaks, lower RSI peaks
            if len(price_peaks) >= 2 and len(rsi_peaks) >= 2:
                # Find recent peaks
                recent_price_peaks = price_peaks[-2:]
                recent_rsi_peaks = rsi_peaks[-2:]
                
                if len(recent_price_peaks) == 2 and len(recent_rsi_peaks) == 2:
                    price_high_1 = prices[recent_price_peaks[0]]
                    price_high_2 = prices[recent_price_peaks[1]]
                    rsi_high_1 = rsi_values[recent_rsi_peaks[0]]
                    rsi_high_2 = rsi_values[recent_rsi_peaks[1]]
                    
                    # Check for divergence
                    if price_high_2 > price_high_1 * 1.005 and rsi_high_2 < rsi_high_1 - 2:
                        # Calculate confidence based on divergence strength
                        price_diff = (price_high_2 - price_high_1) / price_high_1
                        rsi_diff = abs(rsi_high_2 - rsi_high_1) / 100
                        
                        confidence = min(0.9, 0.3 + price_diff * 20 + rsi_diff * 10)
                        
                        return {
                            'divergence': 'bearish',
                            'confidence': confidence,
                            'price_high_1': price_high_1,
                            'price_high_2': price_high_2,
                            'rsi_high_1': rsi_high_1,
                            'rsi_high_2': rsi_high_2,
                            'action': 'prepare_short',
                            'message': f'📉 MOMENTUM WEAKENING - Price at ${price_high_2:,.0f} but momentum declining. Consider selling!',
                            'pattern_type': 'momentum_divergence'
                        }
            
            # Bullish divergence: lower price troughs, higher RSI troughs  
            if len(price_troughs) >= 2 and len(rsi_troughs) >= 2:
                recent_price_troughs = price_troughs[-2:]
                recent_rsi_troughs = rsi_troughs[-2:]
                
                if len(recent_price_troughs) == 2 and len(recent_rsi_troughs) == 2:
                    price_low_1 = prices[recent_price_troughs[0]]
                    price_low_2 = prices[recent_price_troughs[1]]
                    rsi_low_1 = rsi_values[recent_rsi_troughs[0]]
                    rsi_low_2 = rsi_values[recent_rsi_troughs[1]]
                    
                    if price_low_2 < price_low_1 * 0.995 and rsi_low_2 > rsi_low_1 + 2:
                        price_diff = (price_low_1 - price_low_2) / price_low_1
                        rsi_diff = abs(rsi_low_2 - rsi_low_1) / 100
                        
                        confidence = min(0.9, 0.3 + price_diff * 20 + rsi_diff * 10)
                        
                        return {
                            'divergence': 'bullish',
                            'confidence': confidence,
                            'price_low_1': price_low_1,
                            'price_low_2': price_low_2,
                            'rsi_low_1': rsi_low_1,
                            'rsi_low_2': rsi_low_2,
                            'action': 'prepare_long',
                            'message': f'📈 MOMENTUM BUILDING - Price at ${price_low_2:,.0f} but strength increasing. Consider buying!',
                            'pattern_type': 'momentum_divergence'
                        }
            
            return {'divergence': None, 'message': '✅ MOMENTUM NORMAL - No reversal signals detected'}
            
        except Exception as e:
            logger.error(f"Divergence detection error: {e}")
            return {'divergence': None, 'error': str(e)}
    
    def _calculate_simple_rsi(self, prices: List[float], period: int = 14) -> List[float]:
        """Calculate simple RSI when not available in database"""
        if len(prices) < period + 1:
            return [50.0] * len(prices)  # Default neutral RSI
        
        deltas = [prices[i+1] - prices[i] for i in range(len(prices)-1)]
        gains = [d if d > 0 else 0 for d in deltas]
        losses = [-d if d < 0 else 0 for d in deltas]
        
        # Simple moving average for first calculation
        avg_gain = sum(gains[:period]) / period if period <= len(gains) else 0
        avg_loss = sum(losses[:period]) / period if period <= len(losses) else 0
        
        rsi_values = [50.0] * period  # Fill initial values
        
        for i in range(period, len(deltas)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period
            
            if avg_loss == 0:
                rsi = 100
            else:
                rs = avg_gain / avg_loss
                rsi = 100 - (100 / (1 + rs))
            
            rsi_values.append(rsi)
        
        return rsi_values
    
    def _find_local_maxima(self, data: List[float], window: int = 3) -> List[int]:
        """Find local maxima indices in data"""
        if len(data) < window * 2 + 1:
            return []
        
        maxima = []
        for i in range(window, len(data) - window):
            is_maximum = True
            current_val = data[i]
            
            # Check if current point is higher than all points in window
            for j in range(i - window, i + window + 1):
                if j != i and data[j] >= current_val:
                    is_maximum = False
                    break
            
            if is_maximum:
                maxima.append(i)
        
        return maxima
    
    def _find_local_minima(self, data: List[float], window: int = 3) -> List[int]:
        """Find local minima indices in data"""
        if len(data) < window * 2 + 1:
            return []
        
        minima = []
        for i in range(window, len(data) - window):
            is_minimum = True
            current_val = data[i]
            
            # Check if current point is lower than all points in window
            for j in range(i - window, i + window + 1):
                if j != i and data[j] <= current_val:
                    is_minimum = False
                    break
            
            if is_minimum:
                minima.append(i)
        
        return minima
    
    def _moving_average(self, data: List[float], window: int) -> List[float]:
        """Calculate simple moving average"""
        if len(data) < window:
            return data[:]
        
        result = []
        for i in range(len(data)):
            if i < window - 1:
                result.append(data[i])
            else:
                avg = sum(data[i - window + 1:i + 1]) / window
                result.append(avg)
        
        return result
    
    async def get_all_patterns(self) -> Dict:
        """
        Get comprehensive pattern analysis
        """
        try:
            # Run all pattern detections
            wyckoff = await self.detect_wyckoff_phase()
            stop_hunt = await self.detect_stop_hunts()
            divergence = await self.detect_momentum_divergence()
            
            # Collect active patterns
            active_patterns = []
            
            if wyckoff.get('confidence', 0) > 0.5:
                active_patterns.append({
                    'type': 'wyckoff',
                    'pattern': wyckoff,
                    'priority': 'high' if wyckoff.get('confidence', 0) > 0.7 else 'medium'
                })
            
            if stop_hunt.get('stop_hunt'):
                active_patterns.append({
                    'type': 'stop_hunt', 
                    'pattern': stop_hunt,
                    'priority': 'high' if stop_hunt.get('confidence', 0) > 0.7 else 'medium'
                })
            
            if divergence.get('divergence'):
                active_patterns.append({
                    'type': 'divergence',
                    'pattern': divergence,
                    'priority': 'medium'
                })
            
            # Store significant patterns in database
            for pattern_info in active_patterns:
                if pattern_info['priority'] == 'high':
                    pattern_data = {
                        'pattern_type': pattern_info['type'],
                        'confidence': pattern_info['pattern'].get('confidence', 0),
                        'price_level': pattern_info['pattern'].get('level') or pattern_info['pattern'].get('price_level'),
                        'direction': pattern_info['pattern'].get('type') or pattern_info['pattern'].get('divergence'),
                        'message': pattern_info['pattern'].get('message', ''),
                        'action': pattern_info['pattern'].get('action', '')
                    }
                    self.db.store_pattern_detection(pattern_data)
            
            return {
                'wyckoff': wyckoff,
                'stop_hunt': stop_hunt,
                'divergence': divergence,
                'active_patterns': active_patterns,
                'pattern_count': len(active_patterns),
                'timestamp': int(time.time())
            }
            
        except Exception as e:
            logger.error(f"Pattern analysis error: {e}")
            return {'error': str(e), 'active_patterns': [], 'pattern_count': 0}

# Alias for compatibility
PatternRecognizer = AdvancedPatternDetector