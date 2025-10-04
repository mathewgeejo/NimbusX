import React, { useState, useEffect } from 'react';

const DatePicker = ({ date, setDate, year, setYear }) => {
  const months = [
    'January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December'
  ];

  const handleDateChange = (e) => {
    setDate(e.target.value);
  };

  const handleYearChange = (e) => {
    setYear(parseInt(e.target.value));
  };

  // Generate year options (current year - 5 to current year + 10)
  const currentYear = new Date().getFullYear();
  const yearOptions = [];
  for (let i = currentYear - 5; i <= currentYear + 10; i++) {
    yearOptions.push(i);
  }

  // Get today's date for default
  const today = new Date();
  const currentMonth = String(today.getMonth() + 1).padStart(2, '0');
  const currentDay = String(today.getDate()).padStart(2, '0');
  const defaultDate = `${currentMonth}-${currentDay}`;

  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-2">
        🗓️ Target Date & Year
      </label>
      
      {/* Date and Year Input Row */}
      <div className="flex gap-3 mb-3">
        <div className="flex-2">
          <input
            type="text"
            placeholder="e.g., 06-21 for June 21"
            value={date}
            onChange={handleDateChange}
            className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
          <p className="text-xs text-gray-500 mt-1">Month-Day (MM-DD)</p>
        </div>
        
        <div className="flex-1">
          <select
            value={year}
            onChange={handleYearChange}
            className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white"
          >
            {yearOptions.map(yearOption => (
              <option key={yearOption} value={yearOption}>
                {yearOption}
              </option>
            ))}
          </select>
          <p className="text-xs text-gray-500 mt-1">Year</p>
        </div>
      </div>

      {/* Full Date Display */}
      {date && year && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 mb-3">
          <p className="text-sm font-medium text-blue-800">
            📅 Selected: {date}/{year}
          </p>
          <p className="text-xs text-blue-600">
            Prediction Type: {year <= currentYear ? 'Historical Analysis' : year === currentYear + 1 ? 'Next Year Forecast' : 'Long-term Projection'}
          </p>
        </div>
      )}

      {/* Year Preset Buttons */}
      <div className="mb-3">
        <p className="text-xs text-gray-500 mb-2">Quick select year:</p>
        <div className="grid grid-cols-3 gap-2">
          <button
            onClick={() => setYear(currentYear)}
            className="px-3 py-2 text-sm bg-green-100 text-green-700 rounded hover:bg-green-200 transition-colors"
          >
            {currentYear} (This Year)
          </button>
          <button
            onClick={() => setYear(currentYear + 1)}
            className="px-3 py-2 text-sm bg-blue-100 text-blue-700 rounded hover:bg-blue-200 transition-colors"
          >
            {currentYear + 1} (Next Year)
          </button>
          <button
            onClick={() => setYear(currentYear + 2)}
            className="px-3 py-2 text-sm bg-purple-100 text-purple-700 rounded hover:bg-purple-200 transition-colors"
          >
            {currentYear + 2} (Future)
          </button>
        </div>
      </div>

      {/* Quick select buttons for months */}
      <div className="space-y-2">
        <p className="text-xs text-gray-500">Quick select month:</p>
        <div className="grid grid-cols-4 gap-2">
          {months.map((month, index) => (
            <button
              key={index}
              onClick={() => setDate(`${String(index + 1).padStart(2, '0')}-15`)}
              className="px-2 py-1 text-xs bg-gray-100 text-gray-700 rounded hover:bg-gray-200 transition-colors"
            >
              {month.substring(0, 3)}
            </button>
          ))}
        </div>
      </div>

      {/* Common dates */}
      <div className="mt-3">
        <p className="text-xs text-gray-500 mb-2">Common dates:</p>
        <div className="flex flex-wrap gap-2">
          <button
            onClick={() => setDate(defaultDate)}
            className="px-3 py-1 text-xs bg-blue-100 text-blue-700 rounded-full hover:bg-blue-200 transition-colors"
          >
            Today ({defaultDate})
          </button>
          <button
            onClick={() => setDate('12-25')}
            className="px-3 py-1 text-xs bg-green-100 text-green-700 rounded-full hover:bg-green-200 transition-colors"
          >
            Christmas
          </button>
          <button
            onClick={() => setDate('07-04')}
            className="px-3 py-1 text-xs bg-red-100 text-red-700 rounded-full hover:bg-red-200 transition-colors"
          >
            July 4th
          </button>
          <button
            onClick={() => setDate('01-01')}
            className="px-3 py-1 text-xs bg-yellow-100 text-yellow-700 rounded-full hover:bg-yellow-200 transition-colors"
          >
            New Year
          </button>
        </div>
      </div>

      {/* Date format help */}
      {date && !date.match(/^\d{2}-\d{2}$/) && (
        <p className="mt-2 text-xs text-red-500">
          Please use MM-DD format (e.g., 06-21)
        </p>
      )}
    </div>
  );
};

export default DatePicker;
