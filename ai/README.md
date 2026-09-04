# HealthWatch AI / Machine Learning Engine

The AI module powers intelligent disease surveillance, spatial-temporal hotspot discovery, and epidemiological risk forecasting.

## Core Capabilities (Roadmap)
1. **DBSCAN Spatial Hotspot Clustering**: Identifies high-density geographic clusters of infectious disease incidents using haversine metric.
2. **Spatial-Temporal Exposure Matching**: Computes intersection probabilities between patient trajectories and public contacts.
3. **Outbreak Risk Forecaster**: Utilizes time-series regressors and ensemble models (RandomForest / GradientBoosting) to forecast case volume per administrative zone.

## Structure
```
ai/
├── models/         # Serialized model artifacts (.joblib / .pkl)
├── pipelines/      # ML training and inference pipelines
├── notebooks/      # Exploratory data analysis (EDA)
├── requirements.txt
└── README.md
```
