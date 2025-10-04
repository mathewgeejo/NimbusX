import React from 'react';

const AccuracyMetrics = ({ metrics }) => {
  if (!metrics) return null;

  const getConfidenceColor = (score) => {
    if (score >= 80) return 'text-green-600';
    if (score >= 60) return 'text-yellow-600';
    return 'text-red-600';
  };

  const getUncertaintyBadge = (level) => {
    const badges = {
      low: 'bg-green-100 text-green-800',
      moderate: 'bg-yellow-100 text-yellow-800',
      high: 'bg-red-100 text-red-800'
    };
    return badges[level] || badges.moderate;
  };

  return (
    <div className="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-xl p-6 mb-8 border-2 border-blue-200">
      <h3 className="text-2xl font-bold text-gray-800 mb-4 flex items-center">
        <span className="text-3xl mr-2">🎯</span>
        Analysis Accuracy & Confidence Metrics
      </h3>
      
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
        <div className="bg-white rounded-lg p-4 shadow">
          <p className="text-sm text-gray-600 mb-1">Data Quality</p>
          <p className={`text-3xl font-bold ${getConfidenceColor(metrics.data_quality_score)}`}>
            {metrics.data_quality_score?.toFixed(1) || 'N/A'}%
          </p>
        </div>
        
        <div className="bg-white rounded-lg p-4 shadow">
          <p className="text-sm text-gray-600 mb-1">Statistical Confidence</p>
          <p className={`text-3xl font-bold ${getConfidenceColor(metrics.statistical_confidence)}`}>
            {metrics.statistical_confidence?.toFixed(1) || 'N/A'}%
          </p>
        </div>
        
        <div className="bg-white rounded-lg p-4 shadow">
          <p className="text-sm text-gray-600 mb-1">Model Reliability</p>
          <p className={`text-3xl font-bold ${getConfidenceColor(metrics.model_reliability)}`}>
            {metrics.model_reliability?.toFixed(1) || 'N/A'}%
          </p>
        </div>
        
        <div className="bg-white rounded-lg p-4 shadow">
          <p className="text-sm text-gray-600 mb-1">Overall Confidence</p>
          <p className={`text-3xl font-bold ${getConfidenceColor(metrics.overall_confidence)}`}>
            {metrics.overall_confidence?.toFixed(1) || 'N/A'}%
          </p>
        </div>
      </div>

      <div className="flex items-center justify-between bg-white rounded-lg p-4 shadow">
        <div>
          <p className="text-sm text-gray-600">Uncertainty Level</p>
          <span className={`inline-block px-3 py-1 rounded-full text-sm font-semibold mt-1 ${getUncertaintyBadge(metrics.uncertainty_level)}`}>
            {(metrics.uncertainty_level || 'moderate').toUpperCase()}
          </span>
        </div>
        <div className="text-right">
          <p className="text-sm text-gray-600">Data Completeness</p>
          <p className="text-2xl font-bold text-blue-600">
            {metrics.data_completeness?.toFixed(0) || '100'}%
          </p>
        </div>
      </div>

      <p className="text-xs text-gray-500 mt-3 italic">
        💡 Confidence scores reflect data quality, statistical validity, and model certainty.
        Higher scores indicate more reliable predictions.
      </p>
    </div>
  );
};

export default AccuracyMetrics;
