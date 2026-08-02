"""
Simple Test Gemini Analyzer - Minimal version to test AI functionality
"""

import os
import logging
import json
import google.generativeai as genai
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

logger = logging.getLogger(__name__)

# Configure Gemini API
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    logger.info("✅ Simple Gemini API configured successfully")
else:
    logger.warning("⚠️ GEMINI_API_KEY not found")

def simple_ai_analysis(nasa_data, location, date):
    """
    Simplified AI analysis for testing
    """
    if not GEMINI_API_KEY:
        return None
    
    try:
        # Extract basic data
        parameters = nasa_data.get('properties', {}).get('parameter', {})
        
        # Simple prompt
        prompt = f"""Analyze weather for {location} on {date}.

Data: {json.dumps(parameters, indent=1)}

Respond ONLY with valid JSON:
{{
  "probabilities": {{
    "extreme_heat": 25.0,
    "extreme_cold": 5.0,
    "heavy_precipitation": 75.0,
    "strong_winds": 35.0,
    "heat_discomfort": 60.0
  }},
  "accuracy_metrics": {{
    "data_quality_score": 88.0,
    "statistical_confidence": 85.0,
    "model_reliability": 82.0,
    "overall_confidence": 85.0,
    "uncertainty_level": "low",
    "data_completeness": 100.0
  }},
  "summary": "AI weather analysis for {location}.",
  "key_takeaway": "Key weather insight."
}}"""

        # Call Gemini
        model = genai.GenerativeModel('gemini-2.5-pro')
        response = model.generate_content(prompt)
        
        # Parse response
        response_text = response.text.strip()
        if '```json' in response_text:
            response_text = response_text.split('```json')[1].split('```')[0]
        elif '```' in response_text:
            response_text = response_text.split('```')[1].split('```')[0]
            
        result = json.loads(response_text)
        logger.info("✅ Simple AI analysis successful")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Simple AI analysis failed: {str(e)}")
        return None