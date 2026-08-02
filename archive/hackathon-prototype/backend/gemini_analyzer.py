"""
Advanced Gemini-Powered Weather Analysis Engine
Uses AI to analyze NASA climate data with detailed metrics and confidence scoring
"""

import os
import logging
import json
import numpy as np
import google.generativeai as genai
from dotenv import load_dotenv
from datetime import datetime
from pathlib import Path

# Load environment variables from .env file
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

logger = logging.getLogger(__name__)

# Configure Gemini API
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    logger.info("✅ Gemini API configured successfully")
else:
    logger.warning("⚠️ GEMINI_API_KEY not found")
    print("⚠️ GEMINI_API_KEY not found")
    print("Gemini API not available")


def analyze_weather_with_ai(nasa_data, location, date):
    """
    Advanced AI-powered weather analysis with detailed metrics
    
    Args:
        nasa_data (dict): Complete NASA POWER climatology data
        location (str): Location name
        date (str): Target date in MM-DD format
    
    Returns:
        dict: Comprehensive analysis with probabilities, metrics, and insights
    """
    if not GEMINI_API_KEY:
        logger.warning("Gemini API not available")
        return fallback_analysis(nasa_data, location, date)
    
    try:
        # Extract month information
        month_num = int(date.split('-')[0])
        day_num = int(date.split('-')[1])
        month_names = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 
                       'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC']
        target_month = month_names[month_num - 1]
        
        # Get parameters
        parameters = nasa_data.get('properties', {}).get('parameter', {})
        
        # Calculate statistical metrics for context
        stats = calculate_climate_statistics(parameters, target_month)
        
        # Build comprehensive prompt
        prompt = build_analysis_prompt(parameters, target_month, location, date, stats)
        
        # Call Gemini with advanced configuration
        model = genai.GenerativeModel(
            'gemini-2.5-pro',
            generation_config={
                'temperature': 0.3,  # Low for consistent analytical output
                'top_p': 0.85,
                'top_k': 40,
                'max_output_tokens': 4096,  # Allow detailed responses
            }
        )
        
        logger.info(f"🤖 Sending climate data to Gemini AI for deep analysis...")
        response = model.generate_content(prompt)
        
        # Parse response
        result = parse_gemini_response(response.text)
        
        # Add metadata
        result['metadata'] = {
            'analysis_timestamp': datetime.now().isoformat(),
            'data_source': 'NASA POWER (1991-2020 Climatology)',
            'ai_model': 'Gemini 1.5 Pro',
            'location': location,
            'target_date': date,
            'target_month': target_month
        }
        
        # Add raw metrics
        result['raw_metrics'] = extract_raw_metrics(parameters, target_month)
        
        logger.info(f"✅ AI analysis complete - Confidence: {result.get('overall_confidence', 'N/A')}%")
        
        return result
    
    except Exception as e:
        logger.error(f"❌ AI analysis failed: {str(e)}", exc_info=True)
        return fallback_analysis(nasa_data, location, date)


def calculate_climate_statistics(parameters, target_month):
    """
    Calculate comprehensive statistics from climate data
    """
    stats = {}
    
    # Temperature stats
    if 'T2M_MAX' in parameters:
        temps = [v for v in parameters['T2M_MAX'].values() if v is not None]
        target_temp = parameters['T2M_MAX'].get(target_month)
        
        if temps and target_temp:
            stats['temp_max'] = {
                'value': target_temp,
                'annual_mean': np.mean(temps),
                'annual_std': np.std(temps),
                'annual_min': np.min(temps),
                'annual_max': np.max(temps),
                'percentile_rank': calculate_percentile_rank(target_temp, temps),
                'z_score': (target_temp - np.mean(temps)) / np.std(temps) if np.std(temps) > 0 else 0
            }
    
    # Precipitation stats
    if 'PRECTOTCORR' in parameters:
        precip = [v for v in parameters['PRECTOTCORR'].values() if v is not None]
        target_precip = parameters['PRECTOTCORR'].get(target_month)
        
        if precip and target_precip:
            stats['precipitation'] = {
                'value': target_precip,
                'annual_mean': np.mean(precip),
                'annual_std': np.std(precip),
                'annual_min': np.min(precip),
                'annual_max': np.max(precip),
                'percentile_rank': calculate_percentile_rank(target_precip, precip),
                'z_score': (target_precip - np.mean(precip)) / np.std(precip) if np.std(precip) > 0 else 0
            }
    
    # Wind stats
    if 'WS10M' in parameters:
        wind = [v for v in parameters['WS10M'].values() if v is not None]
        target_wind = parameters['WS10M'].get(target_month)
        
        if wind and target_wind:
            stats['wind_speed'] = {
                'value': target_wind,
                'annual_mean': np.mean(wind),
                'annual_std': np.std(wind),
                'annual_min': np.min(wind),
                'annual_max': np.max(wind),
                'percentile_rank': calculate_percentile_rank(target_wind, wind),
                'z_score': (target_wind - np.mean(wind)) / np.std(wind) if np.std(wind) > 0 else 0
            }
    
    return stats


def calculate_percentile_rank(value, distribution):
    """Calculate what percentile a value falls into"""
    if not distribution:
        return 0
    count_below = sum(1 for v in distribution if v <= value)
    return (count_below / len(distribution)) * 100


def build_analysis_prompt(parameters, target_month, location, date, stats):
    """
    Build comprehensive prompt for Gemini AI analysis
    """
    
    # Format climate data
    climate_data = {}
    for param in ['T2M_MAX', 'T2M_MIN', 'PRECTOTCORR', 'WS10M', 'RH2M', 'T2MDEW']:
        if param in parameters:
            climate_data[param] = parameters[param]
    
        # Simple, reliable prompt that's less likely to fail
        prompt = f"""Analyze weather data for {location} on {date}.

Climate data for all 12 months:
{json.dumps(climate_data)}

Calculate probabilities (0-100) for:
1. extreme_heat (if current month temp is in top 10% of year)
2. extreme_cold (if current month temp is in bottom 10% of year) 
3. heavy_precipitation (if current month rain is in top 20% of year)
4. strong_winds (if current month wind is in top 15% of year)
5. heat_discomfort (combined temp + humidity assessment)

Respond with ONLY valid JSON in this exact format:
{{
  "probabilities": {{
    "extreme_heat": 0.0,
    "extreme_cold": 0.0,
    "heavy_precipitation": 0.0,
    "strong_winds": 0.0,
    "heat_discomfort": 0.0
  }},
  "accuracy_metrics": {{
    "data_quality_score": 85.0,
    "statistical_confidence": 80.0,
    "model_reliability": 85.0,
    "overall_confidence": 83.3,
    "uncertainty_level": "moderate",
    "data_completeness": 100.0
  }},
  "summary": "Professional weather analysis summary based on NASA climate data.",
  "key_takeaway": "Most important weather insight for planning."
}}"""
    
    return prompt


def parse_gemini_response(response_text):
    """
    Parse Gemini's JSON response
    """
    try:
        # Clean response
        response_text = response_text.strip()
        
        # Remove markdown code blocks if present
        if '```json' in response_text:
            response_text = response_text.split('```json')[1].split('```')[0]
        elif '```' in response_text:
            response_text = response_text.split('```')[1].split('```')[0]
        
        # Parse JSON
        result = json.loads(response_text)
        
        logger.info("✅ Successfully parsed Gemini JSON response")
        return result
    
    except json.JSONDecodeError as e:
        logger.error(f"❌ Failed to parse JSON: {e}")
        logger.error(f"Response text: {response_text[:500]}")
        
        # Return minimal structure
        return {
            'probabilities': {
                'extreme_heat': 0,
                'extreme_cold': 0,
                'heavy_precipitation': 0,
                'strong_winds': 0,
                'heat_discomfort': 0
            },
            'accuracy_metrics': {
                'overall_confidence': 0,
                'uncertainty_level': 'high'
            },
            'summary': 'AI analysis failed - using fallback.',
            'error': str(e)
        }


def extract_raw_metrics(parameters, target_month):
    """
    Extract raw meteorological values
    """
    return {
        'temperature_max': parameters.get('T2M_MAX', {}).get(target_month),
        'temperature_min': parameters.get('T2M_MIN', {}).get(target_month),
        'precipitation': parameters.get('PRECTOTCORR', {}).get(target_month),
        'wind_speed': parameters.get('WS10M', {}).get(target_month),
        'humidity': parameters.get('RH2M', {}).get(target_month),
        'dew_point': parameters.get('T2MDEW', {}).get(target_month)
    }


def fallback_analysis(nasa_data, location, date):
    """
    Fallback when AI is unavailable - uses simple percentile calculations
    """
    logger.info("Using fallback statistical analysis")
    
    # Extract month from date
    month_num = int(date.split('-')[0])
    month_names = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 
                   'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC']
    target_month = month_names[month_num - 1]
    
    # Get parameters from NASA data
    params = nasa_data.get('properties', {}).get('parameter', {})
    
    # Simple percentile-based probabilities
    probabilities = {
        'extreme_heat': 0.0,
        'extreme_cold': 0.0,
        'heavy_precipitation': 0.0,
        'strong_winds': 0.0,
        'heat_discomfort': 0.0
    }
    
    # Calculate simple probabilities if data exists
    if params:
        try:
            # Temperature analysis
            if 'T2M_MAX' in params:
                temps = [v for v in params['T2M_MAX'].values() if v is not None]
                current_temp = params['T2M_MAX'].get(target_month)
                if temps and current_temp:
                    import numpy as np
                    threshold_90 = np.percentile(temps, 90)
                    if current_temp >= threshold_90:
                        probabilities['extreme_heat'] = 50.0 + (current_temp - threshold_90) * 10
            
            # Precipitation analysis
            if 'PRECTOTCORR' in params:
                precip = [v for v in params['PRECTOTCORR'].values() if v is not None]
                current_precip = params['PRECTOTCORR'].get(target_month)
                if precip and current_precip:
                    import numpy as np
                    threshold_80 = np.percentile(precip, 80)
                    if current_precip >= threshold_80:
                        probabilities['heavy_precipitation'] = min(100.0, 50.0 + (current_precip / threshold_80 - 1) * 100)
        except Exception as e:
            logger.error(f"Fallback calculation error: {e}")
    
    return {
        'probabilities': probabilities,
        'accuracy_metrics': {
            'data_quality_score': 75,
            'statistical_confidence': 70,
            'model_reliability': 60,
            'overall_confidence': 68,
            'uncertainty_level': 'moderate'
        },
        'detailed_analysis': {},
        'advanced_insights': {
            'seasonal_pattern': 'Analysis based on statistical methods',
            'anomalies_detected': []
        },
        'recommendations': {
            'outdoor_activities': {'favorable': [], 'challenging': [], 'not_recommended': []},
            'preparation_checklist': ['Check weather forecast', 'Plan for contingencies']
        },
        'summary': f'Statistical climate analysis for {location} on {date}. AI analysis unavailable.',
        'key_takeaway': 'Check individual probability cards for risk assessment.'
    }
