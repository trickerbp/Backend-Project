from __future__ import annotations

import hashlib
import math
import re
import unicodedata
from dataclasses import dataclass


TOKEN_RE = re.compile(r"[^\W_]+", re.UNICODE)


@dataclass(frozen=True, slots=True)
class VectorizerConfig:
    dimensions: int = 256
    include_bigrams: bool = True

    def __post_init__(self) -> None:
        if self.dimensions < 8:
            raise ValueError("dimensions must be at least 8")


class TextVectorizer:
    """Deterministic, dependency-free text vectors via signed feature hashing.

    Ported from document-processing-api/backend/vectorization.py. Produces an
    L2-normalized vector so that the dot product of two vectors is their cosine
    similarity. No ML dependencies required.
    """

    ALGORITHM = "signed_feature_hashing"
    VERSION = "1.0"

    def __init__(self, config: VectorizerConfig | None = None) -> None:
        self.config = config or VectorizerConfig()

    def vectorize(self, text: str) -> list[float]:
        tokens = self.tokenize(text)
        features = list(tokens)
        if self.config.include_bigrams:
            features.extend(
                f"{left}␟{right}" for left, right in zip(tokens, tokens[1:])
            )

        vector = [0.0] * self.config.dimensions
        for feature in features:
            digest = hashlib.blake2b(
                feature.encode("utf-8"),
                digest_size=16,
                person=b"doc-vector-v1",
            ).digest()
            index = int.from_bytes(digest[:8], "little") % self.config.dimensions
            sign = 1.0 if digest[8] & 1 else -1.0
            vector[index] += sign

        norm = math.sqrt(sum(value * value for value in vector))
        if norm:
            vector = [round(value / norm, 8) for value in vector]
        return vector

    @staticmethod
    def tokenize(text: str) -> list[str]:
        normalized = unicodedata.normalize("NFKC", text).casefold()
        return TOKEN_RE.findall(normalized)


def cosine_similarity(left: list[float], right: list[float]) -> float:
    """Dot product of two L2-normalized vectors (already a cosine in [-1, 1])."""
    if len(left) != len(right):
        raise ValueError("vectors must have the same dimensions")
    return sum(a * b for a, b in zip(left, right))


_DEFAULT_VECTORIZER = TextVectorizer()


def text_similarity(left_text: str, right_text: str) -> float:
    """Cosine similarity of two free-text strings, clamped to [0, 1].

    Returns 0.0 when either side is empty. Negative cosines (no shared
    features beyond hash collisions) are floored to 0 because a "below zero"
    match has no meaning for recommendation scoring.
    """
    if not left_text or not left_text.strip():
        return 0.0
    if not right_text or not right_text.strip():
        return 0.0
    left_vector = _DEFAULT_VECTORIZER.vectorize(left_text)
    right_vector = _DEFAULT_VECTORIZER.vectorize(right_text)
    similarity = cosine_similarity(left_vector, right_vector)
    return max(0.0, min(1.0, similarity))
