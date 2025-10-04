import React, { useState } from 'react';

// Common cities for quick selection
const POPULAR_LOCATIONS = [
  { name: 'New York, USA', lat: 40.7128, lon: -74.0060 },
  { name: 'London, UK', lat: 51.5074, lon: -0.1278 },
  { name: 'Tokyo, Japan', lat: 35.6762, lon: 139.6503 },
  { name: 'Paris, France', lat: 48.8566, lon: 2.3522 },
  { name: 'Sydney, Australia', lat: -33.8688, lon: 151.2093 },
  { name: 'Mumbai, India', lat: 19.0760, lon: 72.8777 },
  { name: 'São Paulo, Brazil', lat: -23.5505, lon: -46.6333 },
  { name: 'Dubai, UAE', lat: 25.2048, lon: 55.2708 },
  { name: 'Los Angeles, USA', lat: 34.0522, lon: -118.2437 },
  { name: 'Singapore', lat: 1.3521, lon: 103.8198 },
];

const LocationInput = ({ onLocationSelect, setLocation }) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [showSuggestions, setShowSuggestions] = useState(false);

  const filteredLocations = POPULAR_LOCATIONS.filter(loc =>
    loc.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const handleLocationClick = (loc) => {
    setSearchQuery(loc.name);
    setLocation(loc.name);
    onLocationSelect({ lat: loc.lat, lon: loc.lon }, loc.name);
    setShowSuggestions(false);
  };

  return (
    <div className="relative">
      <label className="block text-sm font-medium text-gray-700 mb-2">
        Search Location (or use popular cities)
      </label>
      
      <input
        type="text"
        placeholder="Search for a city..."
        value={searchQuery}
        onChange={(e) => {
          setSearchQuery(e.target.value);
          setShowSuggestions(true);
        }}
        onFocus={() => setShowSuggestions(true)}
        className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
      />

      {showSuggestions && searchQuery && (
        <div className="absolute z-10 w-full mt-1 bg-white border border-gray-200 rounded-lg shadow-lg max-h-60 overflow-y-auto">
          {filteredLocations.length > 0 ? (
            filteredLocations.map((loc, index) => (
              <button
                key={index}
                onClick={() => handleLocationClick(loc)}
                className="w-full text-left px-4 py-3 hover:bg-blue-50 transition-colors border-b border-gray-100 last:border-b-0"
              >
                <div className="font-medium text-gray-800">{loc.name}</div>
                <div className="text-xs text-gray-500">
                  {loc.lat.toFixed(2)}°, {loc.lon.toFixed(2)}°
                </div>
              </button>
            ))
          ) : (
            <div className="px-4 py-3 text-gray-500 text-sm">
              No matching cities found. Use coordinates instead.
            </div>
          )}
        </div>
      )}

      {/* Quick select buttons for popular cities */}
      <div className="mt-3">
        <p className="text-xs text-gray-500 mb-2">Popular cities:</p>
        <div className="flex flex-wrap gap-2">
          {POPULAR_LOCATIONS.slice(0, 5).map((loc, index) => (
            <button
              key={index}
              onClick={() => handleLocationClick(loc)}
              className="px-3 py-1 text-xs bg-blue-100 text-blue-700 rounded-full hover:bg-blue-200 transition-colors"
            >
              {loc.name.split(',')[0]}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
};

export default LocationInput;
