"""Embedding abstraction and deterministic local provider."""

from __future__ import annotations

import math
import re
from abc import ABC, abstractmethod
from hashlib import sha256


class EmbeddingProvider(ABC):
    """Abstract interface for text embedding providers."""

    @abstractmethod
    def embed_text(self, text: str) -> list[float]:
        """Return a vector representation for a single text snippet."""

    @abstractmethod
    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Return vectors for a batch of texts in the same order."""


class DeterministicEmbeddingProvider(EmbeddingProvider):
    """A deterministic local embedding provider that avoids external API dependencies."""

    def __init__(self, dimensions: int = 32) -> None:
        self.dimensions = max(1, dimensions)

    def embed_text(self, text: str) -> list[float]:
        tokens = self._tokenize(text)
        if not tokens:
            return [0.0 for _ in range(self.dimensions)]

        vector = [0.0 for _ in range(self.dimensions)]
        for token in tokens:
            digest = sha256(token.encode("utf-8")).digest()
            for index in range(self.dimensions):
                byte = digest[(index * 3 + len(token)) % len(digest)]
                vector[index] += (byte / 255.0) * (1.0 + (len(token) % 7) / 10.0)

        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0:
            return [0.0 for _ in range(self.dimensions)]
        return [value / norm for value in vector]

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [self.embed_text(text) for text in texts]

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        return re.findall(r"[a-zA-Z0-9_]+", text.lower())


__all__ = ["DeterministicEmbeddingProvider", "EmbeddingProvider"]
