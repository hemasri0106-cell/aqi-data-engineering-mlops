# AQI Prediction - Model Lifecycle & Monitoring

This document details the end-to-end lifecycle of models used in the AQI Prediction project.

## 1. Development & Experimentation (Phase 2 & 3)
Models are developed locally using historical data processed by the ELT pipeline. 
- Features are engineered, incorporating lags and 7-day rolling statistics.
- Multiple algorithms (e.g., Linear Regression, Random Forest, XGBoost) are trained and evaluated chronologically.
- MLflow automatically tracks hyperparameters, artifacts, and test metrics.

## 2. Model Registry & Deployment (Phase 3 & 4)
- Best performing models (based on MAE and Macro F1) are registered into the MLflow Model Registry.
- A FastAPI application docker container runs a startup script to fetch these production models.
- Fast and scalable REST endpoints serve predictions in real-time.

## 3. Monitoring (Phase 5)
System health is guaranteed through continuous monitoring stored in `reports/monitoring/`:
- **Data Quality:** Validates nulls, invalid categories, duplicates, and physical limits of incoming AQI metrics.
- **Feature Drift:** Implements the Kolmogorov-Smirnov (KS) test to evaluate if incoming feature distributions have statistically deviated from the training baseline (`data/ml/train/train.csv`).
- **Model Performance:** Compares `(Prediction, Actual)` pairs as truth labels emerge chronologically. 
- **Service Health:** Tracks standard metrics like latency, error rates, and load failures on the FastAPI inference endpoints.

## 4. Retraining Criteria
Models will NOT be continuously retrained blindly. Retraining is triggered when:
1. **Model Error degrades:** If MAE > 50 or R² < 0 for a sustained window.
2. **Significant Feature Drift:** If KS test p-values fall below `0.05` across high-importance features.
3. **Data Quality is restored:** If DQ failed, retraining is paused until ingestion pipelines are fixed.

## 5. Model Rollback & Versioning
- **Versioning:** Handled natively by MLflow (`Version: X`).
- **Validation Check:** New models are evaluated against the current baseline. A newly trained model will only transition to `Production` status if its chronologically validated MAE is strictly better than the currently deployed artifact.
- **Rollback:** In the event of a catastrophic performance drop or container crash during load, we revert `MODEL_VERSION` environment variables in Docker to load the previous integer version from MLflow.
