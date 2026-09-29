import os
import logging
import mlflow
import joblib

logger = logging.getLogger(__name__)

from dotenv import load_dotenv
load_dotenv()
# Config from environment variables
MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI")
REG_MODEL_NAME = "AQI_Next_Day_AQI_Regression"
CLF_MODEL_NAME = "AQI_Next_Day_Category_Classification"
MODEL_VERSION = os.getenv("MODEL_VERSION", "1")

# Configure MLflow
mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)

# Models
reg_model = None
clf_model = None
class_map = None
inverse_class_map = None

def load_models():
    global reg_model, clf_model, class_map, inverse_class_map
    try:
        logger.info(f"Connecting to MLflow at {MLFLOW_TRACKING_URI}...")
        
        reg_uri = f"models:/{REG_MODEL_NAME}/{MODEL_VERSION}"
        logger.info(f"Loading regression model from {reg_uri}")
        reg_model = mlflow.pyfunc.load_model(reg_uri)
        
        clf_uri = f"models:/{CLF_MODEL_NAME}/{MODEL_VERSION}"
        logger.info(f"Loading classification model from {clf_uri}")
        clf_model = mlflow.pyfunc.load_model(clf_uri)
        
        # AQI Categories Mapping (0: Good, 1: Satisfactory, etc)
        # Assuming the standard mapping used during training:
        AQI_CATEGORIES = ['Good', 'Satisfactory', 'Moderate', 'Poor', 'Very Poor', 'Severe']
        inverse_class_map = {i: cat for i, cat in enumerate(AQI_CATEGORIES)}
        
        logger.info("Models loaded successfully.")
    except Exception as e:
        logger.error(f"Failed to load models: {e}")
        raise e

def get_regression_model():
    return reg_model

def get_classification_model():
    return clf_model

def decode_category(code: int) -> str:
    if inverse_class_map and code in inverse_class_map:
        return inverse_class_map[code]
    return str(code)
