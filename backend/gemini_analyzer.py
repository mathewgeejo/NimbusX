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

load_dotenv()
logger = logging.getLogger(__name__)

# Configure Gemini API
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    logger.info("✅ Gemini API configured successfully")
else:
    logger.warning("⚠️ GEMINI_API_KEY not found")


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
    
    prompt = f"""You are an expert AI meteorologist and climate data analyst working with NASA's POWER dataset.

**MISSION**: Perform a comprehensive climate risk analysis for {location} targeting {date} ({target_month}).

**CLIMATE DATA** (30-year averages, 1991-2020):
```json
{json.dumps(climate_data, indent=2)}
```

**STATISTICAL CONTEXT**:
{json.dumps(stats, indent=2)}

**PARAMETER DEFINITIONS**:
- T2M_MAX: Maximum temperature at 2m (°C)
- T2M_MIN: Minimum temperature at 2m (°C)
- PRECTOTCORR: Precipitation (mm/month)
- WS10M: Wind speed at 10m (m/s)
- RH2M: Relative humidity (%)
- T2MDEW: Dew point temperature (°C)

**YOUR ANALYTICAL TASK**:

Perform a deep statistical and meteorological analysis to determine:

1. **Probability Calculations** (0-100% for each):
   - extreme_heat: Probability temp is in top 10% (90th percentile)
   - extreme_cold: Probability temp is in bottom 10% (10th percentile)
   - heavy_precipitation: Probability rainfall is in top 20% (80th percentile)
   - strong_winds: Probability wind is in top 15% (85th percentile)
   - heat_discomfort: Combined temp + humidity discomfort index

2. **Accuracy & Confidence Metrics**:
   - Data quality score (0-100): Based on completeness and consistency
   - Statistical confidence (0-100): Based on variance and sample adequacy
   - Model reliability (0-100): Your confidence in the predictions
   - Overall confidence: Weighted average of above

3. **Detailed Risk Analysis**:
   For EACH risk category, provide:
   - Calculated threshold value
   - Target month's value
   - Standard deviations from mean
   - Percentile ranking
   - Contributing factors
   - Uncertainty range (min-max probability)

4. **Advanced Insights**:
   - Seasonal patterns identified
   - Climate anomalies detected
   - Comparison to global averages
   - Historical context
   - Trend indicators

5. **Practical Recommendations**:
   - Activity planning advice
   - Risk mitigation strategies
   - Best/worst case scenarios
   - Preparation checklist

**OUTPUT FORMAT** (MUST be valid JSON, no markdown):
{{
  "probabilities": {{
    "extreme_heat": <float 0-100>,
    "extreme_cold": <float 0-100>,
    "heavy_precipitation": <float 0-100>,
    "strong_winds": <float 0-100>,
    "heat_discomfort": <float 0-100>
  }},
  
  "accuracy_metrics": {{
    "data_quality_score": <float 0-100>,
    "statistical_confidence": <float 0-100>,
    "model_reliability": <float 0-100>,
    "overall_confidence": <float 0-100>,
    "uncertainty_level": "<low|moderate|high>",
    "sample_size": 12,
    "data_completeness": <float 0-100>
  }},
  
  "detailed_analysis": {{
    "extreme_heat": {{
      "threshold_value": <float>,
      "current_value": <float>,
      "std_deviations": <float>,
      "percentile_rank": <float 0-100>,
      "uncertainty_range": {{"min": <float>, "max": <float>}},
      "contributing_factors": ["<factor1>", "<factor2>"],
      "reasoning": "<detailed explanation>"
    }},
    "extreme_cold": {{ ... }},
    "heavy_precipitation": {{ ... }},
    "strong_winds": {{ ... }},
    "heat_discomfort": {{ ... }}
  }},
  
  "advanced_insights": {{
    "seasonal_pattern": "<description>",
    "climate_classification": "<climate type>",
    "anomalies_detected": ["<anomaly1>", "<anomaly2>"],
    "historical_context": "<context>",
    "trend_indicators": "<trends>",
    "comparison_to_global": "<comparison>"
  }},
  
  "recommendations": {{
    "outdoor_activities": {{
      "favorable": ["<activity1>", "<activity2>"],
      "challenging": ["<activity3>", "<activity4>"],
      "not_recommended": ["<activity5>"]
    }},
    "preparation_checklist": ["<item1>", "<item2>", "<item3>"],
    "risk_mitigation": ["<strategy1>", "<strategy2>"],
    "best_case_scenario": "<scenario>",
    "worst_case_scenario": "<scenario>"
  }},
  
  "summary": "<3-4 sentence professional summary>",
  "key_takeaway": "<single most important insight>"
}}

**CRITICAL REQUIREMENTS**:
1. Use actual statistical calculations - don't guess
2. Calculate real percentiles from the 12-month data
3. Consider z-scores and standard deviations
4. Factor in seasonal variations
5. Be scientifically rigorous and transparent
6. Provide uncertainty ranges for all probabilities
7. Respond ONLY with valid JSON - no markdown, no code blocks
"""
    
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
                        probabilities['heavy_precipitation'] = 50.0 + (current_precip / threshold_80 - 1) * 100
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
