import React, { useState } from 'react';
import axios from 'axios';
import WeatherCard from './components/WeatherCard';
import ProbabilityChart from './components/ProbabilityChart';
import MapSelector from './components/MapSelector';
import LocationInput from './components/LocationInput';
import DatePicker from './components/DatePicker';
import LoadingSpinner from './components/LoadingSpinner';
import AccuracyMetrics from './components/AccuracyMetrics';
import DetailedAnalysis from './components/DetailedAnalysis';
import AdvancedInsights from './components/AdvancedInsights';
import './App.css';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000';

function App() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [lat, setLat] = useState('');
  const [lon, setLon] = useState('');
  const [location, setLocation] = useState('');
  const [date, setDate] = useState('');
  const [year, setYear] = useState(new Date().getFullYear() + 1); // Default to next year
  const [showMap, setShowMap] = useState(false);

  const fetchWeather = async () => {
    // Validate inputs
    if (!lat || !lon || !date || !year) {
      setError('Please fill in all fields: latitude, longitude, date, and year');
      return;
    }

    const latNum = parseFloat(lat);
    const lonNum = parseFloat(lon);

    if (isNaN(latNum) || isNaN(lonNum)) {
      setError('Invalid coordinates. Please enter valid numbers.');
      return;
    }

    if (latNum < -90 || latNum > 90 || lonNum < -180 || lonNum > 180) {
      setError('Coordinates out of range. Lat: -90 to 90, Lon: -180 to 180');
      return;
    }

    // Validate year
    const currentYear = new Date().getFullYear();
    if (year < currentYear - 5 || year > currentYear + 10) {
      setError(`Year must be between ${currentYear - 5} and ${currentYear + 10}`);
      return;
    }

    setLoading(true);
    setError(null);
    setData(null);

    try {
      const response = await axios.post(`${API_BASE_URL}/api/weather`, {
        lat: latNum,
        lon: lonNum,
        location: location || 'Selected Location',
        date: date,
        year: year
      });

      setData(response.data);
      setLoading(false);
    } catch (err) {
      console.error('Error fetching weather data:', err);
      setError(err.response?.data?.error || 'Failed to fetch weather data. Please try again.');
      setLoading(false);
    }
  };

  const handleMapClick = (coords) => {
    console.log('Map clicked at:', coords);
    setLat(coords.lat.toFixed(4));
    setLon(coords.lng.toFixed(4));
    setLocation(`Location: ${coords.lat.toFixed(2)}°, ${coords.lng.toFixed(2)}°`);
  };

  const handleLocationSelect = (coords, name) => {
    console.log('Location selected:', name, coords);
    setLat(coords.lat.toFixed(4));
    setLon(coords.lon.toFixed(4));
    setLocation(name);
  };

  return (
    <div className="min-h-screen py-8 px-4">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <header className="text-center mb-8 fade-in">
          <div className="flex items-center justify-center mb-4">
            <img 
              src="https://www.nasa.gov/wp-content/themes/nasa/assets/images/nasa-logo.svg" 
              alt="NASA Logo" 
              className="h-16 mr-4"
            />
            <h1 className="text-4xl md:text-5xl font-bold text-white">
              Will It Rain On My Parade?
            </h1>
          </div>
          <p className="text-lg text-white opacity-90">
            Predict extreme weather probabilities using NASA climate data and AI
          </p>
        </header>

        {/* Input Section */}
        <div className="bg-white rounded-2xl shadow-2xl p-6 md:p-8 mb-8 fade-in">
          <h2 className="text-2xl font-semibold mb-6 text-gray-800">
            Select Location & Date
          </h2>

          <div className="grid md:grid-cols-2 gap-6 mb-6">
            {/* Location Input */}
            <div>
              <LocationInput 
                onLocationSelect={handleLocationSelect}
                setLocation={setLocation}
              />
              
              <div className="mt-4">
                <button
                  onClick={() => setShowMap(!showMap)}
                  className="text-sm text-blue-600 hover:text-blue-800 font-medium"
                >
                  {showMap ? '▲ Hide Map' : '▼ Show Map Selector'}
                </button>
              </div>

              {showMap && (
                <div className="mt-4">
                  <MapSelector onLocationSelect={handleMapClick} />
                </div>
              )}
            </div>

            {/* Date Input */}
            <div>
              <DatePicker date={date} setDate={setDate} year={year} setYear={setYear} />
            </div>
          </div>

          {/* Coordinate Inputs */}
          <div className="grid md:grid-cols-3 gap-4 mb-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Latitude
              </label>
              <input
                type="text"
                placeholder="e.g., 40.7128"
                value={lat}
                onChange={e => setLat(e.target.value)}
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Longitude
              </label>
              <input
                type="text"
                placeholder="e.g., -74.006"
                value={lon}
                onChange={e => setLon(e.target.value)}
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Location Name (Optional)
              </label>
              <input
                type="text"
                placeholder="e.g., New York City"
                value={location}
                onChange={e => setLocation(e.target.value)}
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
          </div>

          {/* Submit Button */}
          <button
            onClick={fetchWeather}
            disabled={loading}
            className="w-full bg-gradient-to-r from-blue-600 to-blue-800 text-white font-semibold py-4 px-6 rounded-lg hover:from-blue-700 hover:to-blue-900 transition-all shadow-lg disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? 'Analyzing Weather Data...' : 'Check Weather Probabilities'}
          </button>

          {/* Error Message */}
          {error && (
            <div className="mt-4 p-4 bg-red-100 border border-red-400 text-red-700 rounded-lg">
              <p className="font-medium">⚠️ {error}</p>
            </div>
          )}
        </div>

        {/* Loading State */}
        {loading && (
          <div className="text-center py-12">
            <LoadingSpinner />
            <p className="mt-4 text-white text-lg">
              Fetching NASA climate data and generating AI insights...
            </p>
          </div>
        )}

        {/* Results Dashboard */}
        {data && !loading && (
          <div className="fade-in">
            {/* AI Summary */}
            <div className="bg-white rounded-2xl shadow-2xl p-6 md:p-8 mb-8">
              <h2 className="text-2xl font-semibold mb-4 text-gray-800 flex items-center">
                <span className="text-3xl mr-2">🤖</span>
                AI Weather Intelligence Report
              </h2>
              <p className="text-lg text-gray-700 leading-relaxed mb-4">
                {data.summary}
              </p>
              
              {data.key_takeaway && (
                <div className="bg-blue-50 border-l-4 border-blue-500 p-4 mt-4">
                  <p className="text-sm font-semibold text-blue-900">🎯 Key Takeaway:</p>
                  <p className="text-blue-800">{data.key_takeaway}</p>
                </div>
              )}
              
              <div className="mt-4 text-sm text-gray-500 grid md:grid-cols-3 gap-2">
                <p>📍 <span className="font-semibold">Location:</span> {data.location || 'Selected Location'}</p>
                <p>📅 <span className="font-semibold">Target Date:</span> {data.date}</p>
                <p>🗺️ <span className="font-semibold">Coordinates:</span> {data.coordinates?.lat}°, {data.coordinates?.lon}°</p>
              </div>
              
              {data.metadata && (
                <div className="mt-3 text-xs text-gray-400 border-t pt-2">
                  <p>🤖 <span className="font-semibold">AI Model:</span> {data.metadata.ai_model} | 
                     📊 <span className="font-semibold">Data Source:</span> {data.metadata.data_source} | 
                     🕐 <span className="font-semibold">Analyzed:</span> {new Date(data.metadata.analysis_timestamp).toLocaleString()}
                  </p>
                </div>
              )}
            </div>

            {/* Accuracy Metrics */}
            <AccuracyMetrics metrics={data.accuracy_metrics} />

            {/* Probability Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
              {Object.entries(data.probabilities).map(([key, value]) => {
                const metricInfo = getMetricInfo(key, data);
                return (
                  <WeatherCard
                    key={key}
                    label={formatLabel(key)}
                    value={value}
                    icon={getIconForCondition(key)}
                    metricValue={metricInfo.value}
                    metricUnit={metricInfo.unit}
                    threshold={metricInfo.threshold}
                    description={metricInfo.description}
                  />
                );
              })}
            </div>

            {/* Detailed Analysis */}
            <DetailedAnalysis analysis={data.detailed_analysis} />

            {/* Advanced Insights & Recommendations */}
            <AdvancedInsights 
              insights={data.advanced_insights} 
              recommendations={data.recommendations} 
            />

            {/* Probability Chart */}
            <div className="bg-white rounded-2xl shadow-2xl p-6 md:p-8">
              <h2 className="text-2xl font-semibold mb-6 text-gray-800">
                📊 Probability Breakdown
              </h2>
              <ProbabilityChart probabilities={data.probabilities} />
            </div>

            {/* Data Source Attribution */}
            <div className="mt-8 text-center text-white text-sm opacity-75">
              <p>Data Source: NASA POWER API | AI: Google Gemini</p>
              <p>NASA Space Apps Challenge 2024</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// Helper function to format labels with professional terminology
function formatLabel(key) {
  const labels = {
    'very_hot': 'Extreme Heat',
    'very_cold': 'Extreme Cold',
    'very_wet': 'Heavy Precipitation',
    'very_windy': 'Strong Winds',
    'very_uncomfortable': 'Heat Discomfort Index'
  };
  return labels[key] || key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
}

// Helper function to get icons
function getIconForCondition(key) {
  const icons = {
    'very_hot': '🌡️',
    'very_cold': '❄️',
    'very_wet': '🌧️',
    'very_windy': '💨',
    'very_uncomfortable': '😓'
  };
  return icons[key] || '📊';
}

// Helper function to get metric information for each risk category
function getMetricInfo(key, data) {
  if (!data?.metrics) return {};
  
  const metricMap = {
    very_hot: {
      value: data.metrics.temp_max,
      unit: '°C',
      threshold: 'Based on 90th percentile threshold',
      description: 'Maximum daily temperature'
    },
    very_cold: {
      value: data.metrics.temp_min,
      unit: '°C',
      threshold: 'Based on 10th percentile threshold',
      description: 'Minimum daily temperature'
    },
    very_wet: {
      value: data.metrics.precipitation,
      unit: 'mm/day',
      threshold: 'Based on 80th percentile threshold',
      description: 'Daily precipitation amount'
    },
    very_windy: {
      value: data.metrics.wind_speed,
      unit: 'm/s',
      threshold: 'Based on 85th percentile threshold',
      description: 'Wind speed at 2m height'
    },
    very_uncomfortable: {
      value: data.metrics.heat_index,
      unit: '',
      threshold: 'Calculated from temp & humidity',
      description: 'Feels-like temperature index'
    }
  };
  return metricMap[key] || {};
}

export default App;
