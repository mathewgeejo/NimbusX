"""
Gemini AI Integration Module
Generates natural language weather summaries using Google's Gemini API
"""

import google.generativeai as genai
import os
import logging

logger = logging.getLogger(__name__)

# Configure Gemini API
# API key should be set in environment variable GEMINI_API_KEY
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    logger.info("Gemini API configured successfully")
else:
    logger.warning("GEMINI_API_KEY not found in environment variables")


def generate_weather_summary(probabilities, location, date):
    """
    Generate a natural language summary of weather probabilities using Gemini AI
    
    Args:
        probabilities (dict): Dictionary of extreme weather probabilities
        location (str): Location name
        date (str): Target date in MM-DD format
    
    Returns:
        str: Natural language summary
    """
    try:
        if not GEMINI_API_KEY:
            logger.warning("Gemini API key not configured, returning default summary")
            return generate_fallback_summary(probabilities, location, date)
        
        # Parse date for better readability
        month, day = date.split('-')
        month_names = [
            'January', 'February', 'March', 'April', 'May', 'June',
            'July', 'August', 'September', 'October', 'November', 'December'
        ]
        month_name = month_names[int(month) - 1]
        date_readable = f"{month_name} {int(day)}"
        
        # Create a detailed prompt for Gemini
        prompt = f"""
You are a friendly and knowledgeable NASA weather assistant helping users plan outdoor activities.

Based on NASA POWER climatology data for {location} on {date_readable}, here are the probabilities of extreme weather conditions:
- Very Hot (above 90th percentile): {probabilities.get('very_hot', 0):.1f}%
- Very Cold (below 10th percentile): {probabilities.get('very_cold', 0):.1f}%
- Very Wet (heavy precipitation): {probabilities.get('very_wet', 0):.1f}%
- Very Windy (strong winds): {probabilities.get('very_windy', 0):.1f}%
- Very Uncomfortable (high heat index): {probabilities.get('very_uncomfortable', 0):.1f}%

Write a concise, friendly, and informative 2-3 sentence summary for a dashboard display. 
- Focus on the most significant probabilities (above 40%)
- Give practical advice for outdoor planning
- Use a warm, conversational tone
- Don't mention percentiles or technical terms
- If all probabilities are low, reassure the user that conditions look favorable

Summary:"""
        
        # Generate content using Gemini
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        
        summary = response.text.strip()
        logger.info(f"Generated Gemini summary: {summary}")
        
        return summary
        
    except Exception as e:
        logger.error(f"Error generating Gemini summary: {str(e)}")
        return generate_fallback_summary(probabilities, location, date)


def generate_fallback_summary(probabilities, location, date):
    """
    Generate a simple rule-based summary if Gemini API is not available
    
    Args:
        probabilities (dict): Dictionary of extreme weather probabilities
        location (str): Location name
        date (str): Target date in MM-DD format
    
    Returns:
        str: Simple summary
    """
    try:
        # Parse date
        month, day = date.split('-')
        month_names = [
            'January', 'February', 'March', 'April', 'May', 'June',
            'July', 'August', 'September', 'October', 'November', 'December'
        ]
        month_name = month_names[int(month) - 1]
        
        # Find the highest probability
        max_prob = max(probabilities.values())
        
        if max_prob < 30:
            return f"Weather conditions in {location} during {month_name} are typically mild and favorable for outdoor activities. No extreme weather is expected."
        
        concerns = []
        if probabilities.get('very_hot', 0) > 40:
            concerns.append(f"high temperatures ({probabilities['very_hot']:.0f}% probability)")
        if probabilities.get('very_cold', 0) > 40:
            concerns.append(f"cold conditions ({probabilities['very_cold']:.0f}% probability)")
        if probabilities.get('very_wet', 0) > 40:
            concerns.append(f"rain ({probabilities['very_wet']:.0f}% probability)")
        if probabilities.get('very_windy', 0) > 40:
            concerns.append(f"strong winds ({probabilities['very_windy']:.0f}% probability)")
        if probabilities.get('very_uncomfortable', 0) > 40:
            concerns.append(f"uncomfortable heat ({probabilities['very_uncomfortable']:.0f}% probability)")
        
        if concerns:
            concern_str = ', '.join(concerns[:-1]) + (' and ' + concerns[-1] if len(concerns) > 1 else concerns[0])
            return f"In {location} during {month_name}, you may encounter {concern_str}. Plan accordingly for your outdoor activities."
        else:
            return f"Weather conditions in {location} during {month_name} should be relatively comfortable, though minor variations may occur."
    
    except Exception as e:
        logger.error(f"Error in fallback summary: {str(e)}")
        return "Weather data has been processed. Please check the probability cards for details."


def analyze_natural_language_query(query):
    """
    Optional: Use Gemini to parse natural language weather queries
    Example: "What's the weather like in Paris in July?"
    
    Args:
        query (str): User's natural language query
    
    Returns:
        dict: Extracted location and date information
    """
    try:
        if not GEMINI_API_KEY:
            return None
        
        prompt = f"""
Extract the location and date from this weather query:
"{query}"

Return ONLY a JSON object with these fields:
- location: the place name (or null if not found)
- month: the month number 1-12 (or null if not found)
- day: the day number (or null if not found)

Example: {{"location": "Paris", "month": 7, "day": null}}

JSON:"""
        
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        
        # Parse JSON response
        import json
        result = json.loads(response.text.strip())
        
        return result
        
    except Exception as e:
        logger.error(f"Error in NL query analysis: {str(e)}")
        return None
