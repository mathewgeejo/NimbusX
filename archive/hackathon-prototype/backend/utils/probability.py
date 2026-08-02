"""
Probability Calculation Utilities
Statistical functions for computing extreme weather probabilities
"""

import numpy as np


def calculate_percentile_probability(value, historical_data, percentile, direction='above'):
    """
    Calculate probability of a value being extreme based on historical percentiles
    
    Args:
        value (float): Current value to assess
        historical_data (list): List of historical values
        percentile (int): Percentile threshold (e.g., 90 for 90th percentile)
        direction (str): 'above' or 'below' the percentile
    
    Returns:
        float: Probability percentage (0-100)
    """
    try:
        if not historical_data or value is None:
            return 0.0
        
        # Convert to numpy array for easier handling
        historical_data = np.array(historical_data)
        
        # Calculate the percentile threshold
        threshold = np.percentile(historical_data, percentile)
        
        # Calculate where the value falls in the distribution
        if direction == 'above':
            # For "above percentile" checks (hot, wet, windy)
            # Calculate what percentile the current value represents
            current_percentile = (np.sum(historical_data <= value) / len(historical_data)) * 100
            
            # If we're checking for values above the Xth percentile:
            # - If current is at 95th percentile and threshold is 90th → high probability
            # - If current is at 50th percentile and threshold is 90th → low probability
            if current_percentile >= percentile:
                # Value is above threshold - scale from 50% to 100%
                prob = 50 + ((current_percentile - percentile) / (100 - percentile)) * 50
            else:
                # Value is below threshold - scale from 0% to 50%
                prob = (current_percentile / percentile) * 50
                
        else:  # 'below'
            # For "below percentile" checks (cold)
            current_percentile = (np.sum(historical_data <= value) / len(historical_data)) * 100
            
            # If we're checking for values below the Xth percentile:
            # - If current is at 5th percentile and threshold is 10th → high probability
            # - If current is at 50th percentile and threshold is 10th → low probability
            if current_percentile <= percentile:
                # Value is below threshold - scale from 50% to 100%
                prob = 50 + ((percentile - current_percentile) / percentile) * 50
            else:
                # Value is above threshold - scale from 0% to 50%
                prob = max(0, 50 - ((current_percentile - percentile) / (100 - percentile)) * 50)
        
        return float(min(100, max(0, prob)))
        
    except Exception as e:
        print(f"Error calculating probability: {str(e)}")
        import traceback
        traceback.print_exc()
        return 0.0



def calculate_combined_probability(prob1, prob2, method='max'):
    """
    Combine two probabilities using different methods
    
    Args:
        prob1 (float): First probability (0-100)
        prob2 (float): Second probability (0-100)
        method (str): 'max', 'min', 'avg', or 'multiply'
    
    Returns:
        float: Combined probability
    """
    if method == 'max':
        return max(prob1, prob2)
    elif method == 'min':
        return min(prob1, prob2)
    elif method == 'avg':
        return (prob1 + prob2) / 2
    elif method == 'multiply':
        # Independent events
        return (prob1 / 100) * (prob2 / 100) * 100
    else:
        return prob1


def heat_index(temperature, humidity):
    """
    Calculate heat index (feels like temperature)
    Simplified Rothfusz regression formula
    
    Args:
        temperature (float): Temperature in Celsius
        humidity (float): Relative humidity (0-100)
    
    Returns:
        float: Heat index in Celsius
    """
    try:
        # Convert to Fahrenheit for calculation
        T = temperature * 9/5 + 32
        RH = humidity
        
        # Simplified heat index formula
        if T < 80:
            HI = T
        else:
            HI = -42.379 + 2.04901523*T + 10.14333127*RH - 0.22475541*T*RH
            HI += -0.00683783*T*T - 0.05481717*RH*RH + 0.00122874*T*T*RH
            HI += 0.00085282*T*RH*RH - 0.00000199*T*T*RH*RH
        
        # Convert back to Celsius
        heat_index_c = (HI - 32) * 5/9
        
        return heat_index_c
        
    except:
        return temperature


def wind_chill(temperature, wind_speed):
    """
    Calculate wind chill temperature
    
    Args:
        temperature (float): Temperature in Celsius
        wind_speed (float): Wind speed in m/s
    
    Returns:
        float: Wind chill in Celsius
    """
    try:
        # Convert wind speed from m/s to km/h
        wind_kmh = wind_speed * 3.6
        
        # Wind chill formula (only valid for T ≤ 10°C and wind ≥ 4.8 km/h)
        if temperature > 10 or wind_kmh < 4.8:
            return temperature
        
        wc = 13.12 + 0.6215*temperature - 11.37*(wind_kmh**0.16) + 0.3965*temperature*(wind_kmh**0.16)
        
        return wc
        
    except:
        return temperature


def classify_probability(probability):
    """
    Classify probability into risk levels
    
    Args:
        probability (float): Probability value (0-100)
    
    Returns:
        str: Risk level classification
    """
    if probability >= 70:
        return 'high'
    elif probability >= 40:
        return 'moderate'
    elif probability >= 15:
        return 'low'
    else:
        return 'minimal'


def get_color_for_probability(probability):
    """
    Get color code for probability visualization
    
    Args:
        probability (float): Probability value (0-100)
    
    Returns:
        str: Color name or hex code
    """
    if probability >= 70:
        return '#ef4444'  # red-500
    elif probability >= 40:
        return '#fbbf24'  # yellow-400
    else:
        return '#10b981'  # green-500
