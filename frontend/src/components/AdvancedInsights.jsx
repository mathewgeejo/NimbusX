import React from 'react';

const AdvancedInsights = ({ insights, recommendations }) => {
  if (!insights && !recommendations) return null;

  return (
    <div className="grid md:grid-cols-2 gap-6 mb-8">
      {/* Advanced Insights */}
      {insights && (
        <div className="bg-gradient-to-br from-purple-50 to-pink-50 rounded-xl p-6 shadow-lg border-2 border-purple-200">
          <h3 className="text-2xl font-bold text-gray-800 mb-4 flex items-center">
            <span className="text-3xl mr-2">🔍</span>
            Climate Insights
          </h3>

          <div className="space-y-4">
            {insights.seasonal_pattern && (
              <div className="bg-white rounded-lg p-4 shadow">
                <p className="text-sm font-semibold text-purple-900 mb-1">📊 Seasonal Pattern</p>
                <p className="text-sm text-gray-700">{insights.seasonal_pattern}</p>
              </div>
            )}

            {insights.climate_classification && (
              <div className="bg-white rounded-lg p-4 shadow">
                <p className="text-sm font-semibold text-purple-900 mb-1">🌍 Climate Classification</p>
                <p className="text-sm text-gray-700">{insights.climate_classification}</p>
              </div>
            )}

            {insights.anomalies_detected && insights.anomalies_detected.length > 0 && (
              <div className="bg-white rounded-lg p-4 shadow">
                <p className="text-sm font-semibold text-purple-900 mb-2">⚠️ Anomalies Detected</p>
                <ul className="list-disc list-inside space-y-1">
                  {insights.anomalies_detected.map((anomaly, idx) => (
                    <li key={idx} className="text-sm text-gray-700">{anomaly}</li>
                  ))}
                </ul>
              </div>
            )}

            {insights.historical_context && (
              <div className="bg-white rounded-lg p-4 shadow">
                <p className="text-sm font-semibold text-purple-900 mb-1">📜 Historical Context</p>
                <p className="text-sm text-gray-700">{insights.historical_context}</p>
              </div>
            )}

            {insights.trend_indicators && (
              <div className="bg-white rounded-lg p-4 shadow">
                <p className="text-sm font-semibold text-purple-900 mb-1">📈 Trend Indicators</p>
                <p className="text-sm text-gray-700">{insights.trend_indicators}</p>
              </div>
            )}

            {insights.comparison_to_global && (
              <div className="bg-white rounded-lg p-4 shadow">
                <p className="text-sm font-semibold text-purple-900 mb-1">🌐 Global Comparison</p>
                <p className="text-sm text-gray-700">{insights.comparison_to_global}</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Recommendations */}
      {recommendations && (
        <div className="bg-gradient-to-br from-green-50 to-emerald-50 rounded-xl p-6 shadow-lg border-2 border-green-200">
          <h3 className="text-2xl font-bold text-gray-800 mb-4 flex items-center">
            <span className="text-3xl mr-2">💡</span>
            Recommendations
          </h3>

          <div className="space-y-4">
            {/* Outdoor Activities */}
            {recommendations.outdoor_activities && (
              <div className="bg-white rounded-lg p-4 shadow">
                <p className="text-sm font-semibold text-green-900 mb-2">🏃 Activity Planning</p>
                
                {recommendations.outdoor_activities.favorable && recommendations.outdoor_activities.favorable.length > 0 && (
                  <div className="mb-2">
                    <p className="text-xs text-green-700 font-semibold">✅ Favorable:</p>
                    <p className="text-sm text-gray-700">{recommendations.outdoor_activities.favorable.join(', ')}</p>
                  </div>
                )}
                
                {recommendations.outdoor_activities.challenging && recommendations.outdoor_activities.challenging.length > 0 && (
                  <div className="mb-2">
                    <p className="text-xs text-yellow-700 font-semibold">⚠️ Challenging:</p>
                    <p className="text-sm text-gray-700">{recommendations.outdoor_activities.challenging.join(', ')}</p>
                  </div>
                )}
                
                {recommendations.outdoor_activities.not_recommended && recommendations.outdoor_activities.not_recommended.length > 0 && (
                  <div>
                    <p className="text-xs text-red-700 font-semibold">❌ Not Recommended:</p>
                    <p className="text-sm text-gray-700">{recommendations.outdoor_activities.not_recommended.join(', ')}</p>
                  </div>
                )}
              </div>
            )}

            {/* Preparation Checklist */}
            {recommendations.preparation_checklist && recommendations.preparation_checklist.length > 0 && (
              <div className="bg-white rounded-lg p-4 shadow">
                <p className="text-sm font-semibold text-green-900 mb-2">📋 Preparation Checklist</p>
                <ul className="space-y-1">
                  {recommendations.preparation_checklist.map((item, idx) => (
                    <li key={idx} className="text-sm text-gray-700 flex items-start">
                      <span className="mr-2">☑️</span>
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Risk Mitigation */}
            {recommendations.risk_mitigation && recommendations.risk_mitigation.length > 0 && (
              <div className="bg-white rounded-lg p-4 shadow">
                <p className="text-sm font-semibold text-green-900 mb-2">🛡️ Risk Mitigation</p>
                <ul className="list-disc list-inside space-y-1">
                  {recommendations.risk_mitigation.map((strategy, idx) => (
                    <li key={idx} className="text-sm text-gray-700">{strategy}</li>
                  ))}
                </ul>
              </div>
            )}

            {/* Scenarios */}
            {(recommendations.best_case_scenario || recommendations.worst_case_scenario) && (
              <div className="bg-white rounded-lg p-4 shadow space-y-2">
                {recommendations.best_case_scenario && (
                  <div>
                    <p className="text-xs font-semibold text-green-700">😊 Best Case:</p>
                    <p className="text-sm text-gray-700">{recommendations.best_case_scenario}</p>
                  </div>
                )}
                {recommendations.worst_case_scenario && (
                  <div>
                    <p className="text-xs font-semibold text-red-700">😟 Worst Case:</p>
                    <p className="text-sm text-gray-700">{recommendations.worst_case_scenario}</p>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default AdvancedInsights;
