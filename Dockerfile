FROM python:3.11-slim
# Définir le répertoire de travail dans le conteneur
WORKDIR /app
# Étape 1 : copier UNIQUEMENT le fichier de dépendances
# Cette couche sera mise en cache tant que requirements.txt ne change pas
COPY requirements.txt .
# Étape 2 : installer les dépendances (couche mise en cache)
RUN pip install --no-cache-dir -r requirements.txt
# Étape 3 : copier le code source (invalidé à chaque modification du code)
COPY src/ ./src/
COPY tests/ ./tests/
# Documenter le port utilisé par l’application
EXPOSE 8000
# Commande de démarrage du serveur Uvicorn
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]