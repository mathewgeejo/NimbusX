"""
NASA POWER API Integration Module
Fetches historical weather data from NASA's POWER API
"""

import requests
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# NASA POWER API endpoint
NASA_POWER_BASE_URL = "https://power.larc.nasa.gov/api/temporal/climatology/point"


def fetch_nasa_weather_data(lat, lon, target_date):
    """
    Fetch historical climatology data from NASA POWER API
    
    Args:
        lat (float): Latitude
        lon (float): Longitude
        target_date (str): Target date in MM-DD format
    
    Returns:
        dict: Weather data from NASA API
    """
    try:
        # Parse the month and day
        month, day = map(int, target_date.split('-'))
        
        # NASA POWER parameters
        # We fetch 30-year climatology data (1991-2020)
        params = {
            'parameters': ','.join([
                'T2M',        # Temperature at 2 Meters (°C)
                'T2M_MAX',    # Maximum Temperature (°C)
                'T2M_MIN',    # Minimum Temperature (°C)
                'PRECTOTCORR', # Precipitation Corrected (mm/day)
                'WS2M',       # Wind Speed at 2 Meters (m/s)
                'RH2M',       # Relative Humidity at 2 Meters (%)
                'T2MDEW',     # Dew Point Temperature (°C)
            ]),
            'community': 'AG',  # Agroclimatology community
            'longitude': lon,
            'latitude': lat,
            'format': 'JSON'
        }
        
        logger.info(f"Requesting NASA POWER data for ({lat}, {lon})")
        
        # Make request to NASA POWER API
        response = requests.get(NASA_POWER_BASE_URL, params=params, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        # Extract the climatology data
        if 'properties' not in data or 'parameter' not in data['properties']:
            logger.error("Invalid NASA API response structure")
            return None
        
        parameters = data['properties']['parameter']
        
        # Get the specific month's data (climatology is monthly average)
        # NASA API uses text month names: JAN, FEB, MAR, etc.
        month_names = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 
                       'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC']
        month_key = month_names[month - 1]
        
        # Debug: Log what we're looking for and what's available
        logger.info(f"Looking for month key: {month_key}")
        if 'T2M_MAX' in parameters:
            logger.info(f"T2M_MAX keys available: {list(parameters['T2M_MAX'].keys())}")
        
        result = {
            'temperature': parameters.get('T2M', {}).get(month_key, None),
            'temp_max': parameters.get('T2M_MAX', {}).get(month_key, None),
            'temp_min': parameters.get('T2M_MIN', {}).get(month_key, None),
            'precipitation': parameters.get('PRECTOTCORR', {}).get(month_key, None),
            'wind_speed': parameters.get('WS2M', {}).get(month_key, None),
            'humidity': parameters.get('RH2M', {}).get(month_key, None),
            'dew_point': parameters.get('T2MDEW', {}).get(month_key, None),
            'month': month,
            'day': day
        }
        
        # Debug: Log what values we extracted
        logger.info(f"Extracted values: temp_max={result['temp_max']}, precip={result['precipitation']}, wind={result['wind_speed']}")
        
        # For more detailed analysis, fetch annual data to calculate percentiles
        result['annual_data'] = {
            'temperature': list(parameters.get('T2M', {}).values()),
            'temp_max': list(parameters.get('T2M_MAX', {}).values()),
            'temp_min': list(parameters.get('T2M_MIN', {}).values()),
            'precipitation': list(parameters.get('PRECTOTCORR', {}).values()),
            'wind_speed': list(parameters.get('WS2M', {}).values()),
            'humidity': list(parameters.get('RH2M', {}).values()),
        }
        
        logger.info(f"Successfully fetched NASA data for month {month}")
        
        # Return complete NASA response for AI analysis
        return data
        
    except requests.RequestException as e:
        logger.error(f"NASA API request failed: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Error processing NASA data: {str(e)}")
        return None


def fetch_imerg_data(lat, lon, date):
    """
    Optional: Fetch precipitation data from NASA IMERG
    This is a placeholder for future implementation
    
    Args:
        lat (float): Latitude
        lon (float): Longitude
        date (str): Date in MM-DD format
    
    Returns:
        dict: Precipitation data
    """
    # IMERG requires more complex authentication and data processing
    # This is a placeholder for hackathon extension
    logger.info("IMERG integration is a future enhancement")
    return None
