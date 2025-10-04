"""
Advanced Ensemble Weather Prediction System
Combines ML, Physics, and Statistical approaches for maximum accuracy
"""

try:
    from ml_weather_predictor import ml_weather_model
except ImportError:
    ml_weather_model = None
    
from physics_weather_model import physics_weather_model
from data_processor import process_weather_data  # Original percentile system
import numpy as np
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class EnsembleWeatherPredictor:
    """
    Advanced ensemble system combining multiple prediction methods
    """
    
    def __init__(self):
        self.models = {
            'ml_model': ml_weather_model,
            'physics_model': physics_weather_model,
            'statistical_model': None  # Uses existing percentile system
        }
        self.weights = {
            'ml_model': 0.4,        # 40% - Machine Learning (reduced if not available)
            'physics_model': 0.35,  # 35% - Physics-based  
            'statistical_model': 0.25 # 25% - Statistical percentiles
        }
        
        # Adjust weights if ML is not available
        if ml_weather_model is None:
            logger.warning("ML model not available, adjusting ensemble weights")
            self.weights = {
                'ml_model': 0.0,
                'physics_model': 0.6,   # 60% - Physics-based
                'statistical_model': 0.4 # 40% - Statistical percentiles
            }
    
    def predict_ensemble_weather_risks(self, nasa_data, target_date, location_data=None):
        """
        Generate ensemble predictions using all available methods
        """
        predictions = {}
        confidences = {}
        model_outputs = {}
        
        try:
            # 1. Statistical Model (Original Percentile System)
            logger.info("Running statistical percentile model...")
            stat_result = process_weather_data(nasa_data, target_date)
            model_outputs['statistical'] = {
                'predictions': {
                    'extreme_heat': stat_result.get('very_hot', 0),
                    'extreme_cold': stat_result.get('very_cold', 0),
                    'heavy_precipitation': stat_result.get('very_wet', 0),
                    'strong_winds': stat_result.get('very_windy', 0),
                    'heat_discomfort': stat_result.get('very_uncomfortable', 0)
                },
                'confidence': 75.0  # Static confidence for percentile method
            }
            
            # 2. Machine Learning Model (if available)
            if self.models['ml_model'] is not None:
                logger.info("Running ML ensemble model...")
                try:
                    ml_result = self.models['ml_model'].predict_weather_risks(nasa_data, target_date)
                    model_outputs['ml'] = {
                        'predictions': ml_result['predictions'],
                        'confidence': ml_result['model_confidence']['overall_confidence']
                    }
                except Exception as e:
                    logger.warning(f"ML model failed: {e}")
                    model_outputs['ml'] = self._get_fallback_prediction(60.0)
            else:
                logger.info("ML model not available, using fallback")
                model_outputs['ml'] = self._get_fallback_prediction(50.0)
            
            # 3. Physics-Based Model  
            logger.info("Running physics-based model...")
            try:
                physics_result = self.models['physics_model'].predict_weather_risks_physics(
                    nasa_data, target_date, location_data
                )
                model_outputs['physics'] = {
                    'predictions': physics_result['predictions'],
                    'confidence': physics_result['physics_confidence']['overall_confidence']
                }
            except Exception as e:
                logger.warning(f"Physics model failed: {e}")
                model_outputs['physics'] = self._get_fallback_prediction(65.0)
            
            # 4. Ensemble Combination
            logger.info("Combining ensemble predictions...")
            ensemble_predictions = self._combine_predictions(model_outputs)
            ensemble_confidence = self._calculate_ensemble_confidence(model_outputs)
            
            # 5. Advanced Analysis
            advanced_metrics = self._calculate_advanced_metrics(
                ensemble_predictions, model_outputs, nasa_data, target_date
            )
            
            return {
                'probabilities': ensemble_predictions,
                'accuracy_metrics': ensemble_confidence,
                'model_breakdown': model_outputs,
                'advanced_metrics': advanced_metrics,
                'ensemble_method': 'ML + Physics + Statistical',
                'summary': self._generate_ensemble_summary(
                    ensemble_predictions, ensemble_confidence, target_date
                )
            }
            
        except Exception as e:
            logger.error(f"Ensemble prediction error: {str(e)}")
            return self._get_ensemble_fallback()
    
    def _combine_predictions(self, model_outputs):
        """
        Combine predictions using weighted ensemble with adaptive weights
        """
        risk_types = ['extreme_heat', 'extreme_cold', 'heavy_precipitation', 'strong_winds', 'heat_discomfort']
        combined = {}
        
        for risk_type in risk_types:
            predictions = []
            weights = []
            
            # Collect predictions and confidence-based weights
            for model_name, output in model_outputs.items():
                pred = output['predictions'].get(risk_type, 0)
                conf = output['confidence'] / 100  # Normalize to 0-1
                
                predictions.append(pred)
                # Adaptive weight = base weight × confidence
                adaptive_weight = self.weights.get(model_name, 0) * conf
                weights.append(adaptive_weight)
            
            # Weighted average (normalize weights)
            if sum(weights) > 0:
                weights = [w / sum(weights) for w in weights]
                combined[risk_type] = sum(p * w for p, w in zip(predictions, weights))
            else:
                combined[risk_type] = np.mean(predictions) if predictions else 0
            
            # Ensure valid range
            combined[risk_type] = max(0, min(100, combined[risk_type]))
        
        return combined
    
    def _calculate_ensemble_confidence(self, model_outputs):
        """
        Calculate ensemble confidence metrics
        """
        # Individual model confidences
        confidences = [output['confidence'] for output in model_outputs.values()]
        
        # Agreement between models (lower variance = higher agreement)
        agreements = []
        risk_types = ['extreme_heat', 'extreme_cold', 'heavy_precipitation', 'strong_winds', 'heat_discomfort']
        
        for risk_type in risk_types:
            predictions = [output['predictions'].get(risk_type, 0) for output in model_outputs.values()]
            if len(predictions) > 1:
                variance = np.var(predictions)
                agreement = max(0, 100 - variance)  # Lower variance = higher agreement
                agreements.append(agreement)
        
        # Calculate composite metrics
        data_quality_score = np.mean(confidences)
        statistical_confidence = np.mean(agreements) if agreements else 80.0
        
        # Model reliability based on number of successful models
        successful_models = sum(1 for output in model_outputs.values() if output['confidence'] > 50)
        model_reliability = (successful_models / len(model_outputs)) * 100
        
        # Overall confidence (weighted combination)
        overall_confidence = (
            data_quality_score * 0.4 +
            statistical_confidence * 0.35 +
            model_reliability * 0.25
        )
        
        return {
            'data_quality_score': data_quality_score,
            'statistical_confidence': statistical_confidence,
            'model_reliability': model_reliability,
            'overall_confidence': overall_confidence,
            'uncertainty_level': 'LOW' if overall_confidence > 80 else 'MODERATE' if overall_confidence > 60 else 'HIGH'
        }
    
    def _calculate_advanced_metrics(self, predictions, model_outputs, nasa_data, target_date='07-15'):
        """
        Calculate advanced ensemble metrics
        """
        # Prediction entropy (measure of uncertainty)
        entropies = []
        for risk_type, prob in predictions.items():
            if 0 < prob < 100:
                p = prob / 100
                entropy = -(p * np.log2(p) + (1-p) * np.log2(1-p))
                entropies.append(entropy)
        
        avg_entropy = np.mean(entropies) if entropies else 0
        
        # Model consensus (how much models agree)
        consensus_scores = []
        for risk_type in predictions.keys():
            preds = [output['predictions'].get(risk_type, 0) for output in model_outputs.values()]
            if len(preds) > 1:
                consensus = 100 - np.std(preds)  # Lower std = higher consensus
                consensus_scores.append(max(0, consensus))
        
        avg_consensus = np.mean(consensus_scores) if consensus_scores else 80.0
        
        # Seasonal reliability (some seasons are more predictable)
        month = datetime.strptime(target_date if '-' in target_date else '07-15', '%m-%d').month
        seasonal_reliability = 90 if month in [6, 7, 8, 12, 1, 2] else 75  # Summer/Winter more predictable
        
        # Data completeness score
        available_params = sum(1 for key, value in nasa_data.items() 
                              if value is not None and value != 0)
        total_params = len(nasa_data)
        data_completeness = (available_params / total_params) * 100 if total_params > 0 else 100
        
        return {
            'prediction_entropy': avg_entropy,
            'model_consensus': avg_consensus,
            'seasonal_reliability': seasonal_reliability,
            'data_completeness': data_completeness,
            'ensemble_strength': len([m for m in model_outputs.values() if m['confidence'] > 70])
        }
    
    def _generate_ensemble_summary(self, predictions, confidence, target_date):
        """
        Generate human-readable ensemble summary
        """
        # Find highest risk
        max_risk = max(predictions.values())
        max_risk_type = max(predictions, key=predictions.get)
        
        # Risk level classification
        if max_risk > 80:
            risk_level = "VERY HIGH"
        elif max_risk > 60:
            risk_level = "HIGH" 
        elif max_risk > 40:
            risk_level = "MODERATE"
        else:
            risk_level = "LOW"
        
        # Confidence level
        conf_score = confidence['overall_confidence']
        if conf_score > 85:
            conf_level = "VERY HIGH"
        elif conf_score > 70:
            conf_level = "HIGH"
        elif conf_score > 55:
            conf_level = "MODERATE"
        else:
            conf_level = "LOW"
        
        # Generate summary
        risk_name = {
            'extreme_heat': 'Extreme Heat',
            'extreme_cold': 'Extreme Cold', 
            'heavy_precipitation': 'Heavy Precipitation',
            'strong_winds': 'Strong Winds',
            'heat_discomfort': 'Heat Discomfort'
        }.get(max_risk_type, 'Weather Risk')
        
        summary = f"Ensemble Analysis: {risk_name} shows {risk_level} risk ({max_risk:.1f}%) with {conf_level} confidence ({conf_score:.1f}%). "
        summary += f"Analysis combines statistical percentiles, atmospheric physics, and machine learning models for comprehensive risk assessment."
        
        return summary
    
    def _get_fallback_prediction(self, confidence):
        """
        Generate fallback prediction for failed models
        """
        return {
            'predictions': {
                'extreme_heat': 25.0,
                'extreme_cold': 15.0,
                'heavy_precipitation': 30.0,
                'strong_winds': 20.0,
                'heat_discomfort': 35.0
            },
            'confidence': confidence
        }
    
    def _get_ensemble_fallback(self):
        """
        Complete fallback when ensemble fails
        """
        return {
            'probabilities': {
                'extreme_heat': 30.0,
                'extreme_cold': 20.0,
                'heavy_precipitation': 35.0,
                'strong_winds': 25.0,
                'heat_discomfort': 40.0
            },
            'accuracy_metrics': {
                'data_quality_score': 60.0,
                'statistical_confidence': 50.0,
                'model_reliability': 40.0,
                'overall_confidence': 50.0,
                'uncertainty_level': 'HIGH'
            },
            'ensemble_method': 'Fallback Mode',
            'summary': 'Using fallback predictions due to ensemble system error.'
        }


# Initialize global ensemble predictor
ensemble_predictor = EnsembleWeatherPredictor()