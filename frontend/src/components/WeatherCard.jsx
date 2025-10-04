import React from 'react';

const WeatherCard = ({ label, value, icon }) => {
  // Determine color based on probability value
  const getColorClasses = () => {
    if (value >= 70) {
      return 'bg-gradient-to-br from-red-500 to-red-600 border-red-400';
    } else if (value >= 40) {
      return 'bg-gradient-to-br from-yellow-400 to-yellow-500 border-yellow-300';
    } else {
      return 'bg-gradient-to-br from-green-400 to-green-500 border-green-300';
    }
  };

  const getRiskLevel = () => {
    if (value >= 70) return 'High Risk';
    if (value >= 40) return 'Moderate Risk';
    if (value >= 15) return 'Low Risk';
    return 'Minimal Risk';
  };

  return (
    <div className={`rounded-xl p-6 text-white shadow-lg border-2 transform hover:scale-105 transition-transform duration-200 ${getColorClasses()}`}>
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-lg font-bold">{label}</h3>
        {icon && <span className="text-3xl">{icon}</span>}
      </div>
      <p className="text-4xl font-bold mb-1">{value.toFixed(1)}%</p>
      <p className="text-sm opacity-90">{getRiskLevel()}</p>
      
      {/* Progress bar */}
      <div className="mt-3 bg-white bg-opacity-30 rounded-full h-2 overflow-hidden">
        <div 
          className="bg-white h-full rounded-full transition-all duration-500"
          style={{ width: `${Math.min(value, 100)}%` }}
        />
      </div>
    </div>
  );
};

export default WeatherCard;
