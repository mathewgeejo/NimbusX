import React, { useState } from 'react';

const DetailedAnalysis = ({ analysis }) => {
  const [expandedCategory, setExpandedCategory] = useState(null);

  if (!analysis || Object.keys(analysis).length === 0) return null;

  const categories = {
    extreme_heat: { icon: '🌡️', title: 'Extreme Heat Analysis', color: 'red' },
    extreme_cold: { icon: '❄️', title: 'Extreme Cold Analysis', color: 'blue' },
    heavy_precipitation: { icon: '🌧️', title: 'Heavy Precipitation Analysis', color: 'cyan' },
    strong_winds: { icon: '💨', title: 'Strong Winds Analysis', color: 'gray' },
    heat_discomfort: { icon: '😓', title: 'Heat Discomfort Analysis', color: 'orange' }
  };

  const getColorClasses = (color) => {
    const colors = {
      red: 'bg-red-50 border-red-200 text-red-800',
      blue: 'bg-blue-50 border-blue-200 text-blue-800',
      cyan: 'bg-cyan-50 border-cyan-200 text-cyan-800',
      gray: 'bg-gray-50 border-gray-200 text-gray-800',
      orange: 'bg-orange-50 border-orange-200 text-orange-800'
    };
    return colors[color] || colors.gray;
  };

  const toggleCategory = (key) => {
    setExpandedCategory(expandedCategory === key ? null : key);
  };

  return (
    <div className="bg-white rounded-xl p-6 mb-8 shadow-2xl">
      <h3 className="text-2xl font-bold text-gray-800 mb-4 flex items-center">
        <span className="text-3xl mr-2">🔬</span>
        Detailed Statistical Analysis
      </h3>
      
      <div className="space-y-3">
        {Object.entries(categories).map(([key, config]) => {
          const data = analysis[key];
          if (!data) return null;

          const isExpanded = expandedCategory === key;

          return (
            <div key={key} className={`border-2 rounded-lg overflow-hidden ${getColorClasses(config.color)}`}>
              {/* Header - Always Visible */}
              <button
                onClick={() => toggleCategory(key)}
                className="w-full p-4 flex items-center justify-between hover:bg-opacity-75 transition-all"
              >
                <div className="flex items-center">
                  <span className="text-2xl mr-3">{config.icon}</span>
                  <div className="text-left">
                    <h4 className="font-bold text-lg">{config.title}</h4>
                    {data.current_value !== undefined && (
                      <p className="text-sm opacity-75">
                        Current: {data.current_value?.toFixed(2)} | 
                        Threshold: {data.threshold_value?.toFixed(2)} |
                        Percentile: {data.percentile_rank?.toFixed(1)}%
                      </p>
                    )}
                  </div>
                </div>
                <span className="text-2xl">{isExpanded ? '▼' : '▶'}</span>
              </button>

              {/* Expanded Details */}
              {isExpanded && (
                <div className="p-4 bg-white border-t-2 space-y-3">
                  {/* Statistical Metrics */}
                  <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                    {data.current_value !== undefined && (
                      <div className="bg-gray-50 rounded p-3">
                        <p className="text-xs text-gray-600">Current Value</p>
                        <p className="text-xl font-bold">{data.current_value?.toFixed(2)}</p>
                      </div>
                    )}
                    {data.threshold_value !== undefined && (
                      <div className="bg-gray-50 rounded p-3">
                        <p className="text-xs text-gray-600">Threshold</p>
                        <p className="text-xl font-bold">{data.threshold_value?.toFixed(2)}</p>
                      </div>
                    )}
                    {data.std_deviations !== undefined && (
                      <div className="bg-gray-50 rounded p-3">
                        <p className="text-xs text-gray-600">Std Deviations</p>
                        <p className="text-xl font-bold">{data.std_deviations?.toFixed(2)}σ</p>
                      </div>
                    )}
                    {data.percentile_rank !== undefined && (
                      <div className="bg-gray-50 rounded p-3">
                        <p className="text-xs text-gray-600">Percentile Rank</p>
                        <p className="text-xl font-bold">{data.percentile_rank?.toFixed(1)}%</p>
                      </div>
                    )}
                    {data.uncertainty_range && (
                      <div className="bg-gray-50 rounded p-3 col-span-2">
                        <p className="text-xs text-gray-600">Uncertainty Range</p>
                        <p className="text-xl font-bold">
                          {data.uncertainty_range.min?.toFixed(1)}% - {data.uncertainty_range.max?.toFixed(1)}%
                        </p>
                      </div>
                    )}
                  </div>

                  {/* Contributing Factors */}
                  {data.contributing_factors && data.contributing_factors.length > 0 && (
                    <div className="bg-blue-50 rounded p-3">
                      <p className="text-sm font-semibold text-blue-900 mb-2">Contributing Factors:</p>
                      <ul className="list-disc list-inside space-y-1">
                        {data.contributing_factors.map((factor, idx) => (
                          <li key={idx} className="text-sm text-blue-800">{factor}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Reasoning */}
                  {data.reasoning && (
                    <div className="bg-green-50 rounded p-3">
                      <p className="text-sm font-semibold text-green-900 mb-1">AI Reasoning:</p>
                      <p className="text-sm text-green-800 italic">{data.reasoning}</p>
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default DetailedAnalysis;
