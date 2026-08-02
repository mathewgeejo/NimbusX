"""
Physics-Based Weather Risk Assessment
Uses atmospheric science principles and thermodynamics
"""

import numpy as np
import math
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class PhysicsWeatherModel:
    """
    Advanced physics-based weather risk calculation
    Uses atmospheric science and thermodynamics principles
    """
    
    def __init__(self):
        # Physical constants
        self.STEFAN_BOLTZMANN = 5.67e-8  # W/m²K⁴
        self.SPECIFIC_HEAT_AIR = 1005  # J/kg·K
        self.LATENT_HEAT_VAPORIZATION = 2.26e6  # J/kg
        self.GAS_CONSTANT_DRY_AIR = 287  # J/kg·K
    
    def calculate_heat_stress_index(self, temp, humidity, wind_speed, solar_radiation=800):
        """
        Advanced heat stress calculation using WBGT (Wet Bulb Globe Temperature)
        """
        # Wet bulb temperature approximation
        wet_bulb = temp * math.atan(0.151977 * math.sqrt(humidity + 8.313659)) + \
                   math.atan(temp + humidity) - math.atan(humidity - 1.676331) + \
                   0.00391838 * humidity**(3/2) * math.atan(0.023101 * humidity) - 4.686035
        
        # Globe temperature (considers solar radiation)
        globe_temp = temp + (solar_radiation / 1000) * 2  # Simplified solar heating
        
        # WBGT calculation
        if wind_speed < 3:  # Calm conditions
            wbgt = 0.7 * wet_bulb + 0.2 * globe_temp + 0.1 * temp
        else:  # Windy conditions
            wbgt = 0.7 * wet_bulb + 0.3 * temp
        
        # Convert to risk percentage
        if wbgt < 27:
            heat_risk = 0
        elif wbgt < 32:
            heat_risk = (wbgt - 27) * 20  # 0-100% over 5°C range
        else:
            heat_risk = 100
        
        return min(100, max(0, heat_risk))
    
    def calculate_precipitation_potential(self, temp, humidity, pressure, wind_speed):
        """
        Calculate precipitation probability using atmospheric moisture and instability
        """
        # Saturation vapor pressure (Clausius-Clapeyron)
        e_sat = 6.112 * math.exp((17.67 * temp) / (temp + 243.5))  # hPa
        
        # Actual vapor pressure
        e_actual = e_sat * (humidity / 100)
        
        # Precipitable water (column moisture)
        precipitable_water = (e_actual / pressure) * 1000 * 10  # mm equivalent
        
        # Lifting condensation level
        lcl_height = 125 * (temp - (temp - 2.5 * (temp - 273.15) / 1000))
        
        # Atmospheric instability factor
        instability = max(0, (temp - 15) * (humidity - 70) / 100)
        
        # Wind convergence factor
        convergence = min(wind_speed / 10, 1.0)  # 0-1 scaling
        
        # Combined precipitation potential
        precip_potential = (
            precipitable_water * 0.4 +  # Available moisture
            instability * 0.3 +         # Atmospheric instability  
            convergence * 0.2 +         # Wind convergence
            (1000 - pressure) * 0.1     # Low pressure boost
        )
        
        return min(100, max(0, precip_potential))
    
    def calculate_wind_risk(self, pressure_gradient, temp_gradient, latitude):
        """
        Calculate wind risk using pressure gradients and Coriolis effect
        """
        # Geostrophic wind approximation
        coriolis_parameter = 2 * 7.292e-5 * math.sin(math.radians(latitude))
        
        if abs(coriolis_parameter) < 1e-10:  # Near equator
            coriolis_parameter = 1e-10
        
        # Pressure gradient force
        geostrophic_wind = pressure_gradient / (1.225 * abs(coriolis_parameter))  # m/s
        
        # Temperature gradient enhancement (thermal wind)
        thermal_wind = temp_gradient * 2  # Simplified thermal wind
        
        # Total wind speed estimate
        total_wind = math.sqrt(geostrophic_wind**2 + thermal_wind**2)
        
        # Convert to risk percentage (>15 m/s is high risk)
        wind_risk = min(100, (total_wind / 15) * 100)
        
        return max(0, wind_risk)
    
    def calculate_cold_risk(self, temp, wind_speed, humidity):
        """
        Calculate cold risk using wind chill and physiological factors
        """
        if temp > 10:
            return 0  # No cold risk above 10°C
        
        # Wind chill calculation (Environment Canada formula)
        if wind_speed < 4.8:
            wind_chill = temp
        else:
            wind_chill = 13.12 + 0.6215*temp - 11.37*(wind_speed**0.16) + \
                        0.3965*temp*(wind_speed**0.16)
        
        # Humidity effect (dry cold feels different)
        humidity_factor = 1.0 + (50 - humidity) / 200  # Dry air feels colder
        effective_chill = wind_chill * humidity_factor
        
        # Risk scale (dangerous below -15°C wind chill)
        if effective_chill > 0:
            cold_risk = 0
        elif effective_chill > -15:
            cold_risk = (0 - effective_chill) * 3.33  # 0-50% risk
        else:
            cold_risk = 50 + ((-15) - effective_chill) * 2  # 50-100% risk
        
        return min(100, max(0, cold_risk))
    
    def predict_weather_risks_physics(self, nasa_data, target_date, location_data=None):
        """
        Main physics-based prediction function
        """
        try:
            # Extract basic meteorological data
            temp = nasa_data.get('temp_max', 20)
            temp_min = nasa_data.get('temp_min', 10)
            humidity = nasa_data.get('humidity', 60)
            wind_speed = nasa_data.get('wind_speed', 5)
            pressure = nasa_data.get('pressure', 1013.25)  # Standard atmospheric pressure
            
            # Location data for advanced calculations
            latitude = location_data.get('lat', 0) if location_data else 0
            
            # Calculate pressure and temperature gradients (simplified)
            pressure_gradient = max(1, abs(1013.25 - pressure))  # Deviation from standard
            temp_gradient = abs(temp - temp_min) / 1000  # Per km (simplified)
            
            # Physics-based risk calculations
            risks = {}
            
            # Heat Stress (WBGT-based)
            risks['extreme_heat'] = self.calculate_heat_stress_index(
                temp, humidity, wind_speed
            )
            
            # Cold Risk (Wind Chill + Physiological)
            risks['extreme_cold'] = self.calculate_cold_risk(
                temp_min, wind_speed, humidity
            )
            
            # Precipitation Potential (Atmospheric Physics)
            risks['heavy_precipitation'] = self.calculate_precipitation_potential(
                temp, humidity, pressure, wind_speed
            )
            
            # Wind Risk (Geostrophic + Thermal)
            risks['strong_winds'] = self.calculate_wind_risk(
                pressure_gradient, temp_gradient, latitude
            )
            
            # Heat Discomfort (Comprehensive Index)
            risks['heat_discomfort'] = self.calculate_heat_stress_index(
                temp, humidity, wind_speed * 0.7  # Reduced wind effect for comfort
            )
            
            # Physics-based confidence assessment
            confidence = self.calculate_physics_confidence(nasa_data, risks)
            
            return {
                'predictions': risks,
                'physics_confidence': confidence,
                'physical_parameters': {
                    'wet_bulb_temp': temp * 0.8 + humidity * 0.2,  # Approximation
                    'heat_index': temp + (humidity - 40) * 0.1,
                    'wind_chill': temp - wind_speed * 0.8 if temp < 10 else temp,
                    'atmospheric_pressure': pressure
                }
            }
            
        except Exception as e:
            logger.error(f"Physics model error: {str(e)}")
            return self.get_physics_fallback()
    
    def calculate_physics_confidence(self, data, predictions):
        """
        Calculate confidence based on physical parameter validity
        """
        # Data quality checks
        temp_realistic = -50 <= data.get('temp_max', 0) <= 60
        humidity_valid = 0 <= data.get('humidity', 0) <= 100
        wind_realistic = 0 <= data.get('wind_speed', 0) <= 100
        
        data_quality = sum([temp_realistic, humidity_valid, wind_realistic]) / 3 * 100
        
        # Physical consistency checks
        temp_range_ok = data.get('temp_max', 20) >= data.get('temp_min', 10)
        prediction_consistency = all(0 <= p <= 100 for p in predictions.values())
        
        physics_validity = sum([temp_range_ok, prediction_consistency]) / 2 * 100
        
        # Overall confidence
        overall = (data_quality * 0.6 + physics_validity * 0.4)
        
        return {
            'overall_confidence': overall,
            'data_quality_score': data_quality,
            'physics_validity': physics_validity,
            'uncertainty_level': 'LOW' if overall > 80 else 'MODERATE'
        }
    
    def get_physics_fallback(self):
        """
        Fallback for physics model errors
        """
        return {
            'predictions': {
                'extreme_heat': 30.0,
                'extreme_cold': 20.0,
                'heavy_precipitation': 35.0,
                'strong_winds': 25.0,
                'heat_discomfort': 40.0
            },
            'physics_confidence': {
                'overall_confidence': 60.0,
                'uncertainty_level': 'HIGH'
            }
        }


# Initialize physics model
physics_weather_model = PhysicsWeatherModel()