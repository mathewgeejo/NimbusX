"""
Flask Backend for Will It Rain On My Parade?
NASA Space Apps Challenge Hackathon Project
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import logging
import os
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables from .env file
# Get the directory where this script is located
BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / '.env'
load_dotenv(dotenv_path=ENV_PATH)

from nasa_api import fetch_nasa_weather_data
from data_processor import process_weather_data
from gemini_agent import generate_weather_summary
from gemini_analyzer import analyze_weather_with_ai
from ensemble_predictor import ensemble_predictor

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for React frontend

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "message": "Will It Rain On My Parade API is running"}), 200


@app.route('/api/weather', methods=['POST'])
def get_weather_probabilities():
    """
    Main endpoint to get weather probabilities and AI summary
    
    Expected JSON body:
    {
        "lat": 40.7128,
        "lon": -74.006,
        "location": "New York City",
        "date": "06-21"
    }
    """
    try:
        # Parse request data
        data = request.get_json()
        lat = float(data.get('lat'))
        lon = float(data.get('lon'))
        location = data.get('location', 'Selected Location')
        date = data.get('date')  # Format: MM-DD
        year = data.get('year', datetime.now().year + 1)  # Default to next year
        
        # Validate input
        if not all([lat, lon, date]):
            return jsonify({"error": "Missing required fields: lat, lon, date"}), 400
        
        # Validate year
        current_year = datetime.now().year
        if year < current_year - 5 or year > current_year + 10:
            return jsonify({"error": f"Year must be between {current_year - 5} and {current_year + 10}"}), 400
        
        if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
            return jsonify({"error": "Invalid coordinates"}), 400
        
        logger.info(f"Fetching weather data for {location} ({lat}, {lon}) on {date}/{year}")
        
        # Step 1: Fetch NASA POWER API data with year context
        nasa_data = fetch_nasa_weather_data(lat, lon, date)
        
        if not nasa_data:
            return jsonify({"error": "Failed to fetch NASA data"}), 500
        
        # Add year information to NASA data
        nasa_data['target_year'] = year
        nasa_data['prediction_type'] = 'historical' if year <= current_year else 'forecast'
        
        # Step 2: Use Advanced Ensemble Prediction System
        logger.info(f"🚀 Starting Year-Aware Advanced Ensemble Analysis ({year})...")
        
        # Prepare location data for physics model with year context
        location_data = {"lat": lat, "lon": lon, "name": location, "target_year": year}
        
        # Run ensemble prediction with year context
        ensemble_result = ensemble_predictor.predict_ensemble_weather_risks(
            nasa_data, date, location_data, year
        )
        
        # Step 3: Add coordinate and metadata information with year context
        ensemble_result['coordinates'] = {"lat": lat, "lon": lon}
        ensemble_result['location'] = location
        ensemble_result['date'] = date
        ensemble_result['year'] = year
        ensemble_result['full_date'] = f"{date}/{year}"
        ensemble_result['data_source'] = "NASA POWER API (30-year climatology) + Multi-Temporal Analysis"
        ensemble_result['analysis_type'] = f"Year-Aware Advanced Ensemble ({year})"
        ensemble_result['prediction_category'] = 'Historical Analysis' if year <= current_year else ('Next Year Forecast' if year == current_year + 1 else 'Long-term Projection')
        
        logger.info(f"✅ Ensemble analysis complete for {location} - Overall Confidence: {ensemble_result.get('accuracy_metrics', {}).get('overall_confidence', 'N/A'):.1f}%")
        return jsonify(ensemble_result), 200
        
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        return jsonify({"error": f"Invalid input: {str(e)}"}), 400
    except Exception as e:
        logger.error(f"Server error: {str(e)}")
        return jsonify({"error": "Internal server error", "details": str(e)}), 500


@app.route('/api/analyze', methods=['POST'])
def analyze_natural_language():
    """
    Optional endpoint for natural language query processing
    
    Expected JSON body:
    {
        "query": "What's the weather like in Paris in July?"
    }
    """
    try:
        data = request.get_json()
        query = data.get('query')
        
        if not query:
            return jsonify({"error": "Query is required"}), 400
        
        # This could be extended with NLP to extract location and date
        # For now, return a helpful message
        return jsonify({
            "message": "Natural language processing feature coming soon!",
            "suggestion": "Please use the map selector or coordinate input for now."
        }), 200
        
    except Exception as e:
        logger.error(f"Error in NL analysis: {str(e)}")
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
