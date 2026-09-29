# Part 2 Summary: Machine Learning & MLOps

## 1. ML Problem Definition
The objective of this project was to leverage historical pollution and weather data to forecast the Air Quality Index (AQI) of Indian cities 24 hours in advance.
- **Regression:** Predict the exact numerical value of the AQI.
- **Classification:** Predict the AQI severity category (e.g., 'Satisfactory', 'Poor').

## 2. Feature Engineering
The model relied on a 29-feature matrix generated entirely from chronological SQL-backed historical data:
- Core metrics: `pm25`, `no2`, `aqi`, weather metrics (`temperature_c`, `humidity_pct`, etc.)
- Time dimensions: `day_of_week`, `month`
- Temporal dynamics: Lags of 1, 2, and 3 days. Rolling means over 3 and 7 days. Standard deviations over 7 days.

## 3. Training & Evaluation
We utilized an explicit chronological train (70%) / validation (15%) / test (15%) split to prevent data leakage.
### Regression
- Evaluated: Linear Regression, Random Forest, XGBoost
- Selected: **Linear Regression** (Best balance of stability and RMSE).
### Classification
- Evaluated: Logistic Regression, Random Forest, XGBoost
- Selected: **Logistic Regression** (Highest generalizable F1 Macro).

## 4. MLflow Experiment Tracking & Registry
- **Experiments:** All runs, hyperparameters, models, and evaluation metrics were rigorously logged to a local PostgreSQL MLflow tracking backend.
- **Registry:** Selected models were transitioned into the MLflow Model Registry, isolating inference requirements from training.

## 5. Deployment
- **FastAPI:** Created asynchronous inference endpoints utilizing `pydantic` schemas for rigorous input validation.
- **Docker:** The API and MLflow PyFunc loading mechanisms were containerized to guarantee identical operating environments between training and inference (e.g., matching `numpy`, `pandas`, `scikit-learn` versions).

## 6. Streamlit Integration
A dedicated interface was appended to the core dashboard allowing users to:
- Pick any active station.
- Dynamically formulate the 29-feature real historical payload.
- Directly query the Dockerized FastAPI model container and receive a next-day prediction utilizing NO fabricated or future information.

## 7. Monitoring & Model Lifecycle
- Implemented `src/monitoring` scripts to enforce statistical feature drift (Kolmogorov-Smirnov test), track data quality degradation, and evaluate chronological model accuracy against real targets. 
- Fully defined retraining thresholds prevent automated model thrashing, reserving deployment pushes exclusively for verified performance improvements.
