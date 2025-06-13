import joblib
import numpy as np
from pathlib import Path
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class EWastePricePredictor:
    def __init__(self):
        try:
            model_path = Path(__file__).parent / 'ml_models' / 'ewaste_price_model.pkl'
            scaler_path = Path(__file__).parent / 'ml_models' / 'ewaste_price_scaler.pkl'
            
            logger.debug(f"Loading model from: {model_path}")
            logger.debug(f"Loading scaler from: {scaler_path}")
            
            if not model_path.exists():
                raise FileNotFoundError(f"Model file not found at {model_path}")
            if not scaler_path.exists():
                raise FileNotFoundError(f"Scaler file not found at {scaler_path}")
            
            self.model = joblib.load(model_path)
            self.scaler = joblib.load(scaler_path)
            
            logger.debug("Model and scaler loaded successfully")
            
        except Exception as e:
            logger.error(f"Error initializing predictor: {str(e)}")
            raise
        
        # Define mappings for categorical variables
        self.device_type_map = {
            'phone': 0,
            'laptop': 1,
            'tablet': 2,
            'desktop': 3,
            'tv': 4,
            'console': 5
        }
        
        self.condition_map = {
            'working': 2,
            'partially_working': 1,
            'not_working': 0
        }
        
        self.status_map = {
            'good': 2,
            'average': 1,
            'poor': 0,
            'na': 1
        }
    
    def preprocess_input(self, device_type, condition, age, battery_status='na', screen_condition='na', motherboard_status='na'):
        """
        Preprocess the input data before making predictions
        """
        try:
            logger.debug("\nPreprocessing input:")
            logger.debug(f"Device Type: {device_type}")
            logger.debug(f"Condition: {condition}")
            logger.debug(f"Age: {age}")
            logger.debug(f"Battery Status: {battery_status}")
            logger.debug(f"Screen Condition: {screen_condition}")
            logger.debug(f"Motherboard Status: {motherboard_status}")
            
            # Convert device type to numerical (default to -1 if not found)
            device_type_num = self.device_type_map.get(device_type.lower(), 0)  # Default to mobile/phone
            
            # Convert condition/functional status
            condition_num = self.condition_map.get(condition.lower(), 1)  # Default to partially working
            
            # Convert age to float
            age_num = float(age)
            
            # Convert component statuses
            battery_num = self.status_map.get(battery_status.lower(), 1)
            screen_num = self.status_map.get(screen_condition.lower(), 1)
            mb_num = self.status_map.get(motherboard_status.lower(), 1)
            
            # Create feature array in the exact order expected by the model
            features = [
                device_type_num,
                age_num,
                condition_num,
                battery_num,
                screen_num,
                mb_num
            ]
            
            logger.debug(f"Preprocessed features: {features}")
            
            # Scale features
            features_scaled = self.scaler.transform(np.array(features).reshape(1, -1))
            logger.debug(f"Scaled features: {features_scaled}")
            
            return features_scaled
            
        except Exception as e:
            logger.error(f"Error in preprocessing: {str(e)}")
            return None
    
    def predict_price(self, device_type, condition, age, **features):
        """
        Predict the price of e-waste based on its characteristics
        Args:
            device_type: Type of the device
            condition: Overall condition (functional status)
            age: Age of the device in years
            features: Additional features including battery_status, screen_condition, motherboard_status
        Returns:
            float: Predicted price
        """
        try:
            logger.debug("\nMaking price prediction:")
            logger.debug(f"Input - Device Type: {device_type}, Condition: {condition}, Age: {age}")
            logger.debug(f"Additional features: {features}")
            
            processed_input = self.preprocess_input(
                device_type, 
                condition, 
                age,
                features.get('batteryStatus', 'na'),
                features.get('screenCondition', 'na'),
                features.get('motherboardStatus', 'na')
            )
            
            if processed_input is None:
                logger.error("Failed to preprocess input")
                return None
                
            prediction = self.model.predict(processed_input)
            logger.debug(f"Raw prediction: {prediction}")
            
            # Ensure prediction is non-negative and round to 2 decimal places
            final_price = max(round(float(prediction[0]), 2), 100)
            logger.debug(f"Final price: {final_price}")
            
            return final_price
            
        except Exception as e:
            logger.error(f"Error in price prediction: {str(e)}")
            return None
