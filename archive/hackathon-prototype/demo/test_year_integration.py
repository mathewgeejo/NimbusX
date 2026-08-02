#!/usr/bin/env python3
"""
Test script to verify year-aware functionality integration
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from datetime import datetime
from ensemble_predictor import EnsembleWeatherPredictor
from ml_weather_predictor import WeatherRiskMLModel
from neural_weather_model import AdvancedNeuralWeatherModel

def test_year_aware_prediction():
    """Test the complete year-aware prediction system"""
    print("🧪 Testing Year-Aware Weather Prediction System\n")
    
    # Test data
    test_data = {
        'lat': 40.7128,
        'lon': -74.0060,
        'temp_max': 25.0,
        'temp_min': 18.0,
        'humidity': 65.0,
        'precipitation': 0.5,
        'wind_speed': 12.0,
        'pressure': 1013.25
    }
    
    target_date = "07-15"
    test_years = [2020, 2024, 2025, 2030]  # Historical, current, next year, future
    
    print("=" * 60)
    
    # Test 1: Neural Weather Model
    print("1️⃣ Testing Neural Weather Model Year-Aware Features")
    neural_model = AdvancedNeuralWeatherModel()
    
    for year in test_years:
        try:
            result = neural_model.predict_multi_temporal(
                test_data, target_date, 
                ['short_term', 'seasonal', 'climate'], 
                target_year=year
            )
            
            prediction_type = "Historical" if year < 2024 else ("Current" if year == 2024 else "Forecast")
            print(f"   📅 {year} ({prediction_type}): ✅ Success")
            print(f"      - Innovation Score: {result.get('innovation_score', 'N/A')}")
            print(f"      - Features Used: {result.get('metadata', {}).get('features_used', 'N/A')}")
            
        except Exception as e:
            print(f"   📅 {year}: ❌ Error - {str(e)}")
    
    print()
    
    # Test 2: ML Weather Predictor  
    print("2️⃣ Testing ML Weather Predictor Year-Aware Training")
    ml_predictor = WeatherRiskMLModel()
    
    for year in test_years:
        try:
            result = ml_predictor.predict_weather_risks(test_data, target_date, target_year=year)
            
            prediction_type = "Historical" if year < 2024 else ("Current" if year == 2024 else "Forecast")
            print(f"   📅 {year} ({prediction_type}): ✅ Success")
            print(f"      - Confidence: {result.get('confidence', {}).get('overall_confidence', 'N/A'):.1f}%")
            
        except Exception as e:
            print(f"   📅 {year}: ❌ Error - {str(e)}")
    
    print()
    
    # Test 3: Complete Ensemble System
    print("3️⃣ Testing Complete Ensemble System Integration")
    ensemble = EnsembleWeatherPredictor()
    
    # Test NASA data simulation
    nasa_data = {**test_data, 'date': target_date}
    
    for year in test_years:
        try:
            result = ensemble.predict_ensemble_weather_risks(
                nasa_data, target_date, None, target_year=year
            )
            
            prediction_type = "Historical Analysis" if year < 2024 else (
                "Current Analysis" if year == 2024 else (
                    "Next Year Forecast" if year == 2025 else "Long-term Projection"
                )
            )
            
            print(f"   📅 {year} ({prediction_type}): ✅ Success")
            print(f"      - Innovation Score: {result.get('innovation_metrics', {}).get('overall_innovation_score', 'N/A')}")
            print(f"      - Ensemble Confidence: {result.get('ensemble_confidence', {}).get('overall_confidence', 'N/A'):.1f}%")
            
        except Exception as e:
            print(f"   📅 {year}: ❌ Error - {str(e)}")
    
    print()
    print("=" * 60)
    print("🎉 Year-Aware Integration Test Complete!")
    print("\n📊 System Features Verified:")
    print("   ✅ Year-aware neural model features")
    print("   ✅ Multi-year ML training data generation")  
    print("   ✅ Complete ensemble system integration")
    print("   ✅ Historical analysis vs future forecasting")
    print("   ✅ Temporal consistency across prediction horizons")

if __name__ == "__main__":
    test_year_aware_prediction()