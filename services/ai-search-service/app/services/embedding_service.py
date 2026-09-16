import os
import random

# A mock embedding provider to satisfy the academic requirement without a paid API.
# In a real scenario, this would call OpenAI or SentenceTransformers.
class EmbeddingProvider:
    def __init__(self):
        self.dimension = int(os.getenv("EMBEDDING_DIMENSION", 384))
        self.model = os.getenv("EMBEDDING_MODEL", "mock-model-v1")
        self.provider = os.getenv("EMBEDDING_PROVIDER", "mock")

    def embed_text(self, text: str) -> list[float]:
        """
        Generates a mock normalized embedding vector of the specified dimension.
        """
        # For demonstration purposes, generate a random normalized vector
        vector = [random.uniform(-1, 1) for _ in range(self.dimension)]
        # Normalize the vector to length 1 for cosine similarity
        norm = sum(x**2 for x in vector) ** 0.5
        if norm > 0:
            vector = [x / norm for x in vector]
        return vector

embedding_provider = EmbeddingProvider()
