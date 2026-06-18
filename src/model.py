class SentimentModel:
    def __init__(self):
        # Ce message sera visible dans " docker logs sentiment "
        print("[ SentimentModel ] Modèle chargé")
    
    def predict(self, text: str) -> dict:
        text_lower = text.lower()
        positive_words = ["bien", "super", "excellent", "parfait", "bon", "aime", "adore"]
        negative_words = ["mal", "nul", "horrible", "mauvais", "déteste", "pire"]
        # Compter les occurrences de mots positifs et négatifs
        pos = sum(1 for w in positive_words if w in text_lower)
        neg = sum(1 for w in negative_words if w in text_lower)
        if pos > neg:
            return {"label": "POSITIVE", "score": round(0.6 + 0.1 * pos, 2), "text": text}
        elif neg > pos:
            return {"label": "NEGATIVE", "score": round(0.6 + 0.1 * neg, 2), "text": text}
        return {"label": "NEUTRAL", "score": 0.5, "text": text}
