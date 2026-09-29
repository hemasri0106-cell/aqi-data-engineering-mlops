# MLflow Tracking and Model Registry

## 1. What MLflow is used for in this project
In Phase 3 of the AQI Prediction project, MLflow is used as the centralized tracking layer and model registry. It replaces manual inspection of CSVs and joblib files by systematically tracking parameters, metrics, metrics artifacts (plots), and models for every training run.

## 2. Experiment Names
We have two primary MLflow experiments corresponding to our two distinct machine learning tasks:
- `AQI_Next_Day_Regression` (Tracking runs for predicting the raw AQI value)
- `AQI_Next_Day_Classification` (Tracking runs for predicting the categorical AQI bucket)

## 3. What is logged
For each model training attempt (Run), the following is logged:
- **Parameters:** Model name, number of training rows, feature count, and random seed.
- **Metrics:** Validation MAE, RMSE, and R² for Regression. Validation Accuracy, Precision, Recall, Macro F1, and Weighted F1 for Classification.
- **Test Metrics:** (Logged specifically on the selected/best model run after test evaluation).
- **Artifacts:** Actual-vs-Predicted plots (Regression) and Confusion Matrices (Classification).
- **Models:** Full scikit-learn preprocessing and modeling pipelines, complete with inferred input/output signatures and dataset examples.

## 4. Selected Models
- **Regression:** `Linear Regression` (Selected automatically via lowest Validation MAE)
- **Classification:** `Logistic Regression` (Selected automatically via highest Validation Macro F1)

## 5. Registered Model Names
Once a model is selected via validation, its artifacts are promoted to the MLflow Model Registry under the following names:
- `AQI_Next_Day_AQI_Regression`
- `AQI_Next_Day_Category_Classification`

## 6. Versioning approach
The pipeline automatically provisions a new version integer whenever `mlflow.register_model` is called. For example, running the pipeline the first time generated `Version 1`. Subsequent successful runs of the pipeline that trigger registration will automatically increment to `Version 2`, `Version 3`, preventing accidental overrides of historical models.

## 7. MLflow UI Address
The MLflow User Interface can be accessed locally at:
`http://localhost:5000`

*(Ensure this does not conflict with Airflow at 8080 or Streamlit at 8501).*

## 8. How to start the MLflow server
To start the tracking server and UI, activate your virtual environment and run:
```bash
mlflow server --backend-store-uri postgresql://postgres:<PASSWORD>@localhost:5432/mlflow_db --default-artifact-root file:///C:/Users/hemas/OneDrive/Desktop/mlops project/AQI-Prediction-Project/mlflow_artifacts --host 0.0.0.0 --port 5000
```

## 9. How to load a registered model
To load a registered model for inference (e.g., during FastAPI deployment):
```python
import mlflow

mlflow.set_tracking_uri("postgresql://postgres:<PASSWORD>@localhost:5432/mlflow_db")

# Load Regression
reg_model = mlflow.pyfunc.load_model("models:/AQI_Next_Day_AQI_Regression/1")

# Load Classification
clf_model = mlflow.pyfunc.load_model("models:/AQI_Next_Day_Category_Classification/1")
```

## 10. Relationship between MLflow and PostgreSQL
MLflow is configured to use a completely isolated database (`mlflow_db`) running on the local PostgreSQL instance. This ensures that the MLflow model registry metadata is persistent and relational, while keeping it strictly separated from the live `aqi_db` containing the ETL and project data. 
