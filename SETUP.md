# Quick Setup Guide

## 🚀 Getting Started in 5 Minutes

### Step 1: Get Your Gemini API Key
1. Go to https://makersuite.google.com/app/apikey
2. Click "Create API Key"
3. Copy your key

### Step 2: Backend Setup
```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
copy .env.example .env
# Edit .env and paste your Gemini API key
python app.py
```

Backend runs at: http://localhost:5000

### Step 3: Frontend Setup
Open a NEW terminal:
```bash
cd frontend
npm install
copy .env.example .env
npm start
```

Frontend opens at: http://localhost:3000

### Step 4: Test It Out!
1. Select "New York" from popular cities
2. Click "Today" button for date
3. Click "Check Weather Probabilities"
4. See your results!

## 🔧 Troubleshooting

### Backend Issues

**Problem**: `ModuleNotFoundError: No module named 'flask'`
**Solution**: Make sure virtual environment is activated and run `pip install -r requirements.txt`

**Problem**: `GEMINI_API_KEY not found`
**Solution**: 
1. Copy `.env.example` to `.env`
2. Add your actual API key to `.env`
3. Make sure there are no spaces around the `=` sign

**Problem**: NASA API request fails
**Solution**: 
- Check internet connection
- NASA POWER API is free and doesn't require authentication
- Try a different location

### Frontend Issues

**Problem**: `npm install` fails
**Solution**: 
- Make sure Node.js 16+ is installed
- Try `npm cache clean --force` then `npm install` again

**Problem**: Map doesn't load
**Solution**: 
- Leaflet CSS might not be loading
- Check console for errors
- Clear browser cache

**Problem**: Backend connection refused
**Solution**: 
- Make sure backend is running on port 5000
- Check `.env` file has correct `REACT_APP_API_URL`
- Try `http://localhost:5000` instead of `http://127.0.0.1:5000`

## 📋 Quick Test Commands

### Test Backend
```bash
# Health check
curl http://localhost:5000/api/health

# Test weather endpoint (PowerShell)
curl -Method POST -Uri http://localhost:5000/api/weather -ContentType "application/json" -Body '{"lat":40.7128,"lon":-74.006,"location":"New York","date":"06-21"}'
```

### Test Frontend
- Navigate to http://localhost:3000
- Open browser console (F12)
- Check for any errors

## 🎯 Sample Test Data

Use these for testing:

**Locations:**
- New York: 40.7128, -74.0060
- London: 51.5074, -0.1278
- Tokyo: 35.6762, 139.6503
- Sydney: -33.8688, 151.2093

**Dates:**
- Summer: 06-21, 07-15, 08-01
- Winter: 12-21, 01-15, 02-01
- Spring: 03-21, 04-15, 05-01
- Fall: 09-21, 10-15, 11-01

## 📦 What's Installed?

### Backend
- Flask - Web framework
- Flask-CORS - Allow frontend to connect
- requests - HTTP library for NASA API
- numpy - Math calculations
- pandas - Data processing
- google-generativeai - Gemini AI
- python-dotenv - Environment variables

### Frontend
- React - UI framework
- axios - HTTP requests
- chart.js - Charts
- react-chartjs-2 - React wrapper for Chart.js
- leaflet - Maps
- react-leaflet - React wrapper for Leaflet
- tailwindcss - Styling

## 🌟 Pro Tips

1. **Use Popular Cities**: Faster than typing coordinates
2. **Try Different Dates**: Summer vs winter shows dramatic differences
3. **Check Multiple Locations**: Compare tropical vs temperate climates
4. **Watch the AI Summary**: It adapts to each location/date
5. **Color Coding**: Red = high risk, Yellow = moderate, Green = low

## 🔒 Security Note

**Never commit your `.env` file to Git!**

The `.gitignore` files are already configured to exclude `.env` files.

## 📞 Need Help?

1. Check console for error messages (F12 in browser)
2. Make sure both backend and frontend are running
3. Verify your Gemini API key is valid
4. Check that ports 5000 and 3000 are not in use

---

Happy Hacking! 🚀
