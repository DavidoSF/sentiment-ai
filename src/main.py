# from fastapi import FastAPI
# from src . schemas import PredictionRequest, PredictionResponse
# from src . model import SentimentModel

# app = FastAPI(title=" SentimentAI ", version=" 0.1.0 ")
# # Le modèle est chargé une seule fois au démarrage du serveur
# # Modification TP2 pour vérifier le déclenchement automatique Jenkins
# model = SentimentModel()


# @app.get("/health")
# def health():
#     """ Endpoint de healthcheck utilisé par Docker et les load balancers ."""
#     return {"status": "ok"}


# @app.post("/predict", response_model=PredictionResponse)
# def predict(request: PredictionRequest):
#     """ Analyse le sentiment du texte fourni et retourne un label + score ."""
#     return model.predict(request.text)

from fastapi import FastAPI
from prometheus_client import Counter, Gauge, Histogram
from prometheus_fastapi_instrumentator import Instrumentator

from src.model import SentimentModel
from src.schemas import PredictionRequest, PredictionResponse

import time


app = FastAPI(title="SentimentAI", version="0.1.0")
model = SentimentModel()


# Métriques métier SentimentAI
predictions_total = Counter(
    "sentiment_predictions_total",
    "Nombre total de prédictions",
    ["label", "status"],  # ex: label=POSITIVE, status=ok
)

confidence_gauge = Gauge(
    "sentiment_confidence_score",
    "Score de confiance de la dernière prédiction",
    ["label"],
)

prediction_duration = Histogram(
    "sentiment_prediction_duration_seconds",
    "Durée des prédictions en secondes",
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5],
)


# Instrumentation automatique HTTP, expose GET /metrics
Instrumentator().instrument(app).expose(app)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/predict", response_model=PredictionResponse)
def predict(request: PredictionRequest):
    start = time.time()

    try:
        result = model.predict(request.text)
        duration = time.time() - start

        predictions_total.labels(
            label=result["label"],
            status="ok",
        ).inc()

        confidence_gauge.labels(
            label=result["label"],
        ).set(result["score"])

        prediction_duration.observe(duration)

        return result

    except Exception:
        predictions_total.labels(
            label="UNKNOWN",
            status="error",
        ).inc()
        raise