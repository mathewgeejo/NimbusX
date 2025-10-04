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

# Load environment variables from .env file
# Get the directory where this script is located
BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / '.env'
load_dotenv(dotenv_path=ENV_PATH)

from nasa_api import fetch_nasa_weather_data
from data_processor import process_weather_data
from gemini_agent import generate_weather_summary

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
        
        # Validate input
        if not all([lat, lon, date]):
            return jsonify({"error": "Missing required fields: lat, lon, date"}), 400
        
        if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
            return jsonify({"error": "Invalid coordinates"}), 400
        
        logger.info(f"Fetching weather data for {location} ({lat}, {lon}) on {date}")
        
        # Step 1: Fetch NASA POWER API data
        nasa_data = fetch_nasa_weather_data(lat, lon, date)
        
        if not nasa_data:
            return jsonify({"error": "Failed to fetch NASA data"}), 500
        
        # Step 2: Process data and calculate probabilities
        probabilities = process_weather_data(nasa_data, date)
        
        # Step 3: Generate AI summary using Gemini
        summary = generate_weather_summary(probabilities, location, date)
        
        # Step 4: Return response with probabilities and actual metric values
        response = {
            "probabilities": probabilities,
            "summary": summary,
            "location": location,
            "coordinates": {"lat": lat, "lon": lon},
            "date": date,
            "metrics": {
                "temp_max": round(nasa_data.get('temp_max', 0), 1) if nasa_data.get('temp_max') else None,
                "temp_min": round(nasa_data.get('temp_min', 0), 1) if nasa_data.get('temp_min') else None,
                "precipitation": round(nasa_data.get('precipitation', 0), 1) if nasa_data.get('precipitation') else None,
                "wind_speed": round(nasa_data.get('wind_speed', 0), 1) if nasa_data.get('wind_speed') else None,
                "heat_index": round(nasa_data.get('humidity', 0), 1) if nasa_data.get('humidity') else None
            }
        }
        
        logger.info(f"Successfully processed request for {location}")
        return jsonify(response), 200
        
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
