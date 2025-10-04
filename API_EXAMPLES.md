# API Testing Examples

## Sample Requests and Responses

### Test 1: New York City - Summer (June 21)

**Request:**
```bash
curl -X POST http://localhost:5000/api/weather \
  -H "Content-Type: application/json" \
  -d '{
    "lat": 40.7128,
    "lon": -74.0060,
    "location": "New York City",
    "date": "06-21"
  }'
```

**Expected Response:**
```json
{
  "probabilities": {
    "very_hot": 68.4,
    "very_cold": 5.2,
    "very_wet": 45.1,
    "very_windy": 31.7,
    "very_uncomfortable": 52.3
  },
  "summary": "In late June, New York City has a 68% chance of heat above normal and moderate rain likelihood. Plan for warm, potentially humid conditions with a possibility of afternoon showers.",
  "location": "New York City",
  "coordinates": {
    "lat": 40.7128,
    "lon": -74.006
  },
  "date": "06-21"
}
```

---

### Test 2: London - Winter (December 25)

**Request:**
```bash
curl -X POST http://localhost:5000/api/weather \
  -H "Content-Type: application/json" \
  -d '{
    "lat": 51.5074,
    "lon": -0.1278,
    "location": "London",
    "date": "12-25"
  }'
```

**Expected Response:**
```json
{
  "probabilities": {
    "very_hot": 2.1,
    "very_cold": 72.8,
    "very_wet": 68.3,
    "very_windy": 54.2,
    "very_uncomfortable": 8.5
  },
  "summary": "Christmas in London brings a high chance of cold temperatures (73%) and wet conditions (68%). Bundle up and bring an umbrella for your holiday celebrations!",
  "location": "London",
  "coordinates": {
    "lat": 51.5074,
    "lon": -0.1278
  },
  "date": "12-25"
}
```

---

### Test 3: Mumbai - Monsoon Season (July 15)

**Request:**
```bash
curl -X POST http://localhost:5000/api/weather \
  -H "Content-Type: application/json" \
  -d '{
    "lat": 19.0760,
    "lon": 72.8777,
    "location": "Mumbai",
    "date": "07-15"
  }'
```

**Expected Response:**
```json
{
  "probabilities": {
    "very_hot": 45.2,
    "very_cold": 0.0,
    "very_wet": 91.7,
    "very_windy": 62.3,
    "very_uncomfortable": 87.4
  },
  "summary": "Mid-July in Mumbai falls during monsoon season, with an extremely high chance of heavy rainfall (92%) and very uncomfortable humid conditions (87%). Expect strong winds and prepare for wet weather.",
  "location": "Mumbai",
  "coordinates": {
    "lat": 19.076,
    "lon": 72.8777
  },
  "date": "07-15"
}
```

---

### Test 4: Sydney - Summer (January 15)

**Request:**
```bash
curl -X POST http://localhost:5000/api/weather \
  -H "Content-Type: application/json" \
  -d '{
    "lat": -33.8688,
    "lon": 151.2093,
    "location": "Sydney",
    "date": "01-15"
  }'
```

**Expected Response:**
```json
{
  "probabilities": {
    "very_hot": 78.9,
    "very_cold": 1.2,
    "very_wet": 32.4,
    "very_windy": 41.6,
    "very_uncomfortable": 65.8
  },
  "summary": "Mid-January is peak summer in Sydney with a 79% chance of very hot temperatures and 66% chance of uncomfortable conditions. Stay hydrated, use sun protection, and consider indoor activities during peak heat.",
  "location": "Sydney",
  "coordinates": {
    "lat": -33.8688,
    "lon": 151.2093
  },
  "date": "01-15"
}
```

---

### Test 5: Dubai - Peak Summer (August 1)

**Request:**
```bash
curl -X POST http://localhost:5000/api/weather \
  -H "Content-Type: application/json" \
  -d '{
    "lat": 25.2048,
    "lon": 55.2708,
    "location": "Dubai",
    "date": "08-01"
  }'
```

**Expected Response:**
```json
{
  "probabilities": {
    "very_hot": 95.6,
    "very_cold": 0.0,
    "very_wet": 5.3,
    "very_windy": 28.4,
    "very_uncomfortable": 98.2
  },
  "summary": "Early August in Dubai brings extreme heat (96% probability) and extremely uncomfortable conditions (98%). Outdoor activities are strongly discouraged during daytime. Stick to air-conditioned indoor spaces.",
  "location": "Dubai",
  "coordinates": {
    "lat": 25.2048,
    "lon": 55.2708
  },
  "date": "08-01"
}
```

---

### Test 6: Reykjavik - Mild Summer (June 15)

**Request:**
```bash
curl -X POST http://localhost:5000/api/weather \
  -H "Content-Type: application/json" \
  -d '{
    "lat": 64.1466,
    "lon": -21.9426,
    "location": "Reykjavik",
    "date": "06-15"
  }'
```

**Expected Response:**
```json
{
  "probabilities": {
    "very_hot": 8.3,
    "very_cold": 15.7,
    "very_wet": 48.2,
    "very_windy": 68.9,
    "very_uncomfortable": 5.1
  },
  "summary": "Mid-June in Reykjavik offers mild temperatures but expect windy conditions (69% probability) and moderate rain chances (48%). Layer your clothing and be prepared for variable weather typical of Iceland.",
  "location": "Reykjavik",
  "coordinates": {
    "lat": 64.1466,
    "lon": -21.9426
  },
  "date": "06-15"
}
```

---

## Testing with PowerShell (Windows)

### Basic Test
```powershell
$body = @{
    lat = 40.7128
    lon = -74.0060
    location = "New York City"
    date = "06-21"
} | ConvertTo-Json

Invoke-RestMethod -Method Post -Uri "http://localhost:5000/api/weather" -ContentType "application/json" -Body $body
```

### Health Check
```powershell
Invoke-RestMethod -Uri "http://localhost:5000/api/health"
```

---

## Testing with Python

```python
import requests
import json

# Test endpoint
url = "http://localhost:5000/api/weather"

# Test data
data = {
    "lat": 40.7128,
    "lon": -74.0060,
    "location": "New York City",
    "date": "06-21"
}

# Make request
response = requests.post(url, json=data)

# Print results
print(f"Status: {response.status_code}")
print(f"Response: {json.dumps(response.json(), indent=2)}")
```

---

## Testing with JavaScript/Node

```javascript
const axios = require('axios');

async function testWeatherAPI() {
  try {
    const response = await axios.post('http://localhost:5000/api/weather', {
      lat: 40.7128,
      lon: -74.0060,
      location: 'New York City',
      date: '06-21'
    });
    
    console.log('Status:', response.status);
    console.log('Data:', JSON.stringify(response.data, null, 2));
  } catch (error) {
    console.error('Error:', error.message);
  }
}

testWeatherAPI();
```

---

## Error Cases to Test

### Invalid Coordinates
```json
{
  "lat": 100,
  "lon": -74.0060,
  "location": "Invalid",
  "date": "06-21"
}
```

**Expected:** HTTP 400 - "Invalid coordinates"

### Missing Fields
```json
{
  "lat": 40.7128,
  "location": "Missing Lon",
  "date": "06-21"
}
```

**Expected:** HTTP 400 - "Missing required fields"

### Invalid Date Format
```json
{
  "lat": 40.7128,
  "lon": -74.0060,
  "location": "New York",
  "date": "June 21"
}
```

**Expected:** HTTP 500 or 400 - Invalid date format error

---

## Performance Testing

### Multiple Rapid Requests
```bash
for i in {1..10}; do
  curl -X POST http://localhost:5000/api/weather \
    -H "Content-Type: application/json" \
    -d '{"lat":40.7128,"lon":-74.006,"location":"NYC","date":"06-21"}' &
done
wait
```

---

## Expected Response Times

- Health check: < 50ms
- Weather API (with NASA data fetch): 2-5 seconds
- Weather API (with Gemini summary): 3-8 seconds

---

**Note:** Actual probabilities will vary based on NASA POWER API data. The examples above are illustrative.
