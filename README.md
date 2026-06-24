# SentimentAI
## API

| Endpoint | Méthode | Description |
|---|---|---|
| `/health` | GET | Healthcheck |
| `/predict` | POST | Prédiction de sentiment |
| `/metrics` | GET | Métriques Prometheus |

**Exemple :**
```bash
curl -X POST http://localhost:8080/predict \
  -H "Content-Type: application/json" \
  -d '{"text": "Ce produit est excellent !"}'
# {"label": "POSITIVE", "score": 0.7, "text": "Ce produit est excellent !"}
```

## Lancer en local

```bash
make build   # construire l'image Docker
make run     # démarrer avec docker compose (port 8080)
make test    # lancer pytest + coverage dans le conteneur
make stop    # arrêter les conteneurs
make clean   # arrêter + supprimer l'image
```

## Stack technique

- **API** — FastAPI + Uvicorn (Python 3.11)
- **Métriques** — Prometheus + Grafana (via `monitoring/`)
- **CI/CD** — Pipeline Jenkins : lint → test → SonarQube → Trivy → push vers GHCR → déploiement Terraform
- **IaC** — Terraform (déploie le conteneur de staging)

## Étapes du pipeline

1. **Checkout** — récupération du code source
2. **Lint** — flake8 (longueur de ligne max : 100)
3. **IaC Validate** — `terraform validate`
4. **Build & Test** — build Docker + pytest (couverture ≥ 70% requise)
5. **SonarQube Analysis** — analyse statique + quality gate
6. **Security Scan** — scan Trivy pour les CVE HIGH/CRITICAL
7. **Push** — tag et push vers `ghcr.io/davidosf/sentiment-ai`
8. **IaC Apply** — `terraform apply` (branche main uniquement)
9. **Deploy Staging** — healthcheck sur le conteneur de staging
10. **Smoke Test** — vérifie `/health`, `/metrics`, Prometheus et Grafana