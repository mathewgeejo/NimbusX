# 🌦️ Will It Rain On My Parade?

**NASA Space Apps Challenge 2024 Hackathon Project**

A full-stack web application that predicts extreme weather probabilities using NASA climate data and provides AI-powered insights through Google's Gemini API.

![NASA Logo](https://www.nasa.gov/wp-content/themes/nasa/assets/images/nasa-logo.svg)

## 🎯 Project Overview

This application helps users plan outdoor activities by analyzing historical climate data from NASA's POWER API to calculate probabilities of extreme weather conditions:

- 🌡️ **Very Hot** - Temperature above 90th percentile
- ❄️ **Very Cold** - Temperature below 10th percentile
- 🌧️ **Very Wet** - Heavy precipitation (80th percentile)
- 💨 **Very Windy** - Strong winds (85th percentile)
- 😓 **Very Uncomfortable** - High heat index conditions

## 🏗️ Architecture

### Tech Stack

**Backend:**
- Flask (Python 3.8+)
- NASA POWER API for climate data
- Google Gemini API for AI summaries
- NumPy/Pandas for statistical analysis

**Frontend:**
- React.js 18
- TailwindCSS for styling
- Chart.js for data visualization
- Leaflet.js for interactive maps
- Axios for API requests

### Project Structure

```
NimbusX/
├── backend/
│   ├── app.py                 # Main Flask application
│   ├── nasa_api.py            # NASA POWER API integration
│   ├── data_processor.py      # Weather data processing & probability calculation
│   ├── gemini_agent.py        # Gemini AI integration
│   ├── utils/
│   │   └── probability.py     # Statistical utility functions
│   ├── requirements.txt       # Python dependencies
│   └── .env.example           # Environment variables template
│
└── frontend/
    ├── public/
    │   └── index.html
    ├── src/
    │   ├── components/
    │   │   ├── WeatherCard.jsx
    │   │   ├── ProbabilityChart.jsx
    │   │   ├── MapSelector.jsx
    │   │   ├── LocationInput.jsx
    │   │   ├── DatePicker.jsx
    │   │   └── LoadingSpinner.jsx
    │   ├── App.js             # Main React component
    │   ├── App.css
    │   ├── index.js
    │   └── index.css
    ├── package.json
    ├── tailwind.config.js
    └── .env.example
```

## 🚀 Quick Start

### Prerequisites

- Python 3.8 or higher
- Node.js 16 or higher
- npm or yarn
- Google Gemini API key ([Get one here](https://makersuite.google.com/app/apikey))

### Backend Setup

1. **Navigate to backend directory:**
   ```bash
   cd backend
   ```

2. **Create virtual environment:**
   ```bash
   python -m venv venv
   
   # Windows
   venv\Scripts\activate
   
   # macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables:**
   ```bash
   # Copy the example file
   copy .env.example .env
   
   # Edit .env and add your Gemini API key
   # GEMINI_API_KEY=your_actual_api_key_here
   ```

5. **Run the Flask server:**
   ```bash
   python app.py
   ```
   
   Backend will be running at `http://localhost:5000`

### Frontend Setup

1. **Navigate to frontend directory:**
   ```bash
   cd frontend
   ```

2. **Install dependencies:**
   ```bash
   npm install
   ```

3. **Set up environment variables:**
   ```bash
   # Copy the example file
   copy .env.example .env
   
   # The default API URL (http://localhost:5000) should work for local development
   ```

4. **Run the development server:**
   ```bash
   npm start
   ```
   
   Frontend will open at `http://localhost:3000`

## 📖 Usage Guide

### Using the Application

1. **Select a Location:**
   - Type a city name in the search box (popular cities available)
   - Or click on the interactive map
   - Or manually enter latitude/longitude

2. **Choose a Date:**
   - Enter date in MM-DD format (e.g., 06-21)
   - Use quick select buttons for common dates
   - Use month buttons for mid-month dates

3. **Get Weather Insights:**
   - Click "Check Weather Probabilities"
   - View AI-generated summary
   - Analyze probability cards with risk levels
   - Review detailed probability breakdown chart

### API Endpoints

#### `POST /api/weather`

Get weather probabilities for a specific location and date.

**Request Body:**
```json
{
  "lat": 40.7128,
  "lon": -74.006,
  "location": "New York City",
  "date": "06-21"
}
```

**Response:**
```json
{
  "probabilities": {
    "very_hot": 68.4,
    "very_cold": 5.2,
    "very_wet": 45.1,
    "very_windy": 31.7,
    "very_uncomfortable": 52.3
  },
  "summary": "In late June, New York City has a 68% chance of heat above normal and moderate rain likelihood.",
  "location": "New York City",
  "coordinates": {"lat": 40.7128, "lon": -74.006},
  "date": "06-21"
}
```

## 🔬 How It Works

### 1. Data Retrieval
- Fetches 30-year climatology data from NASA POWER API
- Retrieves monthly averages for temperature, precipitation, wind, humidity

### 2. Probability Calculation
- Compares target month values against historical distribution
- Calculates percentile-based probabilities
- Uses statistical analysis (z-scores, standard deviations)

### 3. AI Summary Generation
- Sends probabilities to Google Gemini API
- Generates natural, user-friendly weather insights
- Provides practical planning advice

### 4. Visualization
- Color-coded probability cards (red/yellow/green)
- Interactive bar chart
- Risk level classifications

## 🌍 Data Sources

- **NASA POWER API**: Provides global climatology data
- **Google Gemini API**: AI-powered natural language generation

## 🎨 Features

✅ Interactive map-based location selection  
✅ Popular city quick-select  
✅ Visual probability indicators  
✅ AI-generated weather summaries  
✅ Responsive design for mobile/desktop  
✅ Real-time data processing  
✅ Color-coded risk levels  
✅ Detailed probability breakdown charts  

## 🚀 Deployment

### Backend (Render/Heroku)

Add `gunicorn` to requirements.txt and deploy with:
- Build: `pip install -r requirements.txt`
- Start: `gunicorn app:app`

### Frontend (Vercel/Netlify)

Build command: `npm run build`  
Publish directory: `build`

## 📝 License

MIT License

## 🙏 Acknowledgments

- NASA POWER API for providing open climate data
- Google Gemini for AI capabilities
- OpenStreetMap for map tiles

---

**Made with ❤️ for NASA Space Apps Challenge 2024**