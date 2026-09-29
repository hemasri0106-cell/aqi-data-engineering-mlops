from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager
import pandas as pd
import logging
from .schemas import PredictionRequest, RegressionResponse, ClassificationResponse
from .model_loader import load_models, get_regression_model, get_classification_model, decode_category

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting up FastAPI service... Loading MLflow models.")
    load_models()
    yield
    # Shutdown
    logger.info("Shutting down FastAPI service.")

app = FastAPI(title="AQI Prediction API", lifespan=lifespan)

@app.get("/health")
def health_check():
    reg_loaded = get_regression_model() is not None
    clf_loaded = get_classification_model() is not None
    return {
        "status": "healthy" if (reg_loaded and clf_loaded) else "degraded",
        "regression_model_loaded": reg_loaded,
        "classification_model_loaded": clf_loaded
    }

def convert_request_to_dataframe(req: PredictionRequest) -> pd.DataFrame:
    # Convert Pydantic model to dict, then to DataFrame (single row)
    return pd.DataFrame([req.model_dump()])

@app.post("/predict/regression", response_model=RegressionResponse)
def predict_regression(req: PredictionRequest):
    model = get_regression_model()
    if not model:
        raise HTTPException(status_code=503, detail="Regression model is not loaded")
    
    try:
        df = convert_request_to_dataframe(req)
        # MLflow loaded sklearn pipeline handles preprocessing natively
        pred = model.predict(df)[0]
        
        return RegressionResponse(
            predicted_aqi=float(pred),
            model_version="1"
        )
    except Exception as e:
        logger.error(f"Regression prediction failed: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid prediction input: {str(e)}")

@app.post("/predict/classification", response_model=ClassificationResponse)
def predict_classification(req: PredictionRequest):
    model = get_classification_model()
    if not model:
        raise HTTPException(status_code=503, detail="Classification model is not loaded")
    
    try:
        df = convert_request_to_dataframe(req)
        pred_code = int(model.predict(df)[0])
        category = decode_category(pred_code)
        
        return ClassificationResponse(
            predicted_category=category,
            model_version="1"
        )
    except Exception as e:
        logger.error(f"Classification prediction failed: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid prediction input: {str(e)}")
