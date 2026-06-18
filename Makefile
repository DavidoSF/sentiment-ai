IMAGE_NAME = sentiment-ai
PORT = 8080

# .PHONY indique que ces cibles ne correspondent pas à des fichiers réels
.PHONY: build run test stop clean tag

build:
	docker build -t $(IMAGE_NAME):latest .

run:
	docker compose up -d

# Lance les tests DANS le conteneur Docker pour tester exactement
# ce qui sera en production (pas dans l'environnement local)
test:
	docker run --rm \
		-v $(PWD):/app \
		-w /app \
		$(IMAGE_NAME):latest \
		pytest tests/ -v --cov=src --cov-report=term-missing

stop:
	docker compose down

clean:
	docker compose down
	docker rmi $(IMAGE_NAME):latest || true

# Crée un tag Git annoté et le pousse vers GitHub
tag:
	git tag -a v0.1.0 -m "Initial SentimentAI release"
	git push origin v0.1.0
