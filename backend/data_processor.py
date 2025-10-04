"""
Data Processing and Probability Calculation Module
Computes extreme weather probabilities from NASA data
"""

import numpy as np
from utils.probability import calculate_percentile_probability
import logging

logger = logging.getLogger(__name__)


def process_weather_data(nasa_data, target_date):
    """
    Process NASA weather data and calculate extreme weather probabilities
    
    Args:
        nasa_data (dict): Weather data from NASA API
        target_date (str): Target date in MM-DD format
    
    Returns:
        dict: Probabilities for each extreme condition
    """
    try:
        # Extract current month values
        temp = nasa_data.get('temp_max')
        temp_min = nasa_data.get('temp_min')
        precip = nasa_data.get('precipitation')
        wind = nasa_data.get('wind_speed')
        humidity = nasa_data.get('humidity')
        dew_point = nasa_data.get('dew_point')
        
        # Extract annual data for percentile calculations
        annual_temp_max = nasa_data.get('annual_data', {}).get('temp_max', [])
        annual_temp_min = nasa_data.get('annual_data', {}).get('temp_min', [])
        annual_precip = nasa_data.get('annual_data', {}).get('precipitation', [])
        annual_wind = nasa_data.get('annual_data', {}).get('wind_speed', [])
        
        # Remove any None values from annual data
        annual_temp_max = [x for x in annual_temp_max if x is not None]
        annual_temp_min = [x for x in annual_temp_min if x is not None]
        annual_precip = [x for x in annual_precip if x is not None]
        annual_wind = [x for x in annual_wind if x is not None]
        
        # Calculate probabilities for extreme conditions
        probabilities = {}
        
        # VERY HOT: Temperature > 90th percentile
        if temp is not None and annual_temp_max:
            p90_temp = np.percentile(annual_temp_max, 90)
            probabilities['very_hot'] = calculate_percentile_probability(
                temp, annual_temp_max, 90, direction='above'
            )
            logger.info(f"Very Hot: {temp}°C vs 90th percentile {p90_temp:.1f}°C = {probabilities['very_hot']:.1f}%")
        else:
            probabilities['very_hot'] = 0.0
        
        # VERY COLD: Temperature < 10th percentile
        if temp_min is not None and annual_temp_min:
            p10_temp = np.percentile(annual_temp_min, 10)
            probabilities['very_cold'] = calculate_percentile_probability(
                temp_min, annual_temp_min, 10, direction='below'
            )
            logger.info(f"Very Cold: {temp_min}°C vs 10th percentile {p10_temp:.1f}°C = {probabilities['very_cold']:.1f}%")
        else:
            probabilities['very_cold'] = 0.0
        
        # VERY WET: Precipitation > 80th percentile
        if precip is not None and annual_precip:
            p80_precip = np.percentile(annual_precip, 80)
            probabilities['very_wet'] = calculate_percentile_probability(
                precip, annual_precip, 80, direction='above'
            )
            logger.info(f"Very Wet: {precip:.1f}mm vs 80th percentile {p80_precip:.1f}mm = {probabilities['very_wet']:.1f}%")
        else:
            probabilities['very_wet'] = 0.0
        
        # VERY WINDY: Wind speed > 85th percentile
        if wind is not None and annual_wind:
            p85_wind = np.percentile(annual_wind, 85)
            probabilities['very_windy'] = calculate_percentile_probability(
                wind, annual_wind, 85, direction='above'
            )
            logger.info(f"Very Windy: {wind:.1f}m/s vs 85th percentile {p85_wind:.1f}m/s = {probabilities['very_windy']:.1f}%")
        else:
            probabilities['very_windy'] = 0.0
        
        # VERY UNCOMFORTABLE: High heat index (temperature + humidity + dew point)
        # Use a combined metric: high temp + high humidity
        if temp is not None and humidity is not None:
            # Simplified heat index calculation
            heat_index = temp + (humidity / 100) * 10  # Simple approximation
            # Compare to threshold
            if heat_index > 35:  # Uncomfortable threshold
                probabilities['very_uncomfortable'] = min(100, (heat_index - 25) * 5)
            else:
                probabilities['very_uncomfortable'] = 0.0
            logger.info(f"Very Uncomfortable: Heat index {heat_index:.1f} = {probabilities['very_uncomfortable']:.1f}%")
        else:
            probabilities['very_uncomfortable'] = 0.0
        
        # Ensure all values are between 0 and 100
        for key in probabilities:
            probabilities[key] = max(0.0, min(100.0, probabilities[key]))
        
        logger.info(f"Calculated probabilities: {probabilities}")
        return probabilities
        
    except Exception as e:
        logger.error(f"Error processing weather data: {str(e)}")
        # Return default probabilities on error
        return {
            'very_hot': 0.0,
            'very_cold': 0.0,
            'very_wet': 0.0,
            'very_windy': 0.0,
            'very_uncomfortable': 0.0
        }


def calculate_trend(annual_data, target_month):
    """
    Calculate if there's an increasing or decreasing trend
    This is a bonus feature for more detailed analysis
    
    Args:
        annual_data (list): List of monthly values
        target_month (int): Target month (1-12)
    
    Returns:
        str: 'increasing', 'decreasing', or 'stable'
    """
    try:
        if len(annual_data) < 3:
            return 'stable'
        
        # Simple linear regression slope
        x = np.arange(len(annual_data))
        slope = np.polyfit(x, annual_data, 1)[0]
        
        if slope > 0.1:
            return 'increasing'
        elif slope < -0.1:
            return 'decreasing'
        else:
            return 'stable'
    except:
        return 'stable'
