"""
EmbeddingProvider — Provider-agnostic text embedding for Aigis semantic search.

Supports three provider families, selected by a "provider/model-name" string:

  "openai/text-embedding-3-small"   → OpenAI Embeddings API (requires langchain-openai)
  "openai/text-embedding-3-large"   → OpenAI Embeddings API
  "openai/text-embedding-ada-002"   → OpenAI Embeddings API (legacy)
  "voyage/voyage-3"                 → Voyage AI API (requires voyageai)
  "voyage/voyage-3-lite"            → Voyage AI API
  "local/all-MiniLM-L6-v2"         → sentence-transformers (no API key needed)
  "local/all-mpnet-base-v2"         → sentence-transformers

All providers require the relevant package installed; a clear ImportError is raised
at construction time if the package is missing, not at embed time.

Usage:
    provider = EmbeddingProvider.from_config("openai/text-embedding-3-small")
    vectors = provider.embed(["first chunk", "second chunk"])
    vector  = provider.embed_one("query text")
"""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

# ── Known model dimensions ──────────────────────────────────────────────────────

_MODEL_DIMS: dict[str, int] = {
    # OpenAI
    "text-embedding-3-small":  1536,
    "text-embedding-3-large":  3072,
    "text-embedding-ada-002":  1536,
    # Voyage
    "voyage-3":                1024,
    "voyage-3-lite":            512,
    "voyage-2":                1024,
    # sentence-transformers
    "all-MiniLM-L6-v2":        384,
    "all-mpnet-base-v2":       768,
    "paraphrase-MiniLM-L6-v2": 384,
}


def get_embedding_dim(model_name: str) -> int | None:
    """Return the output dimension for a known *model_name*, or None if unknown."""
    return _MODEL_DIMS.get(model_name)


# ── EmbeddingProvider ───────────────────────────────────────────────────────────

class EmbeddingProvider:
    """Provider-agnostic text embedding.

    Constructed via EmbeddingProvider.from_config("provider/model-name").
    The underlying library is imported lazily at construction time so that
    users only need to install the library they actually use.
    """

    def __init__(
        self,
        provider:   str,
        model_name: str,
        api_keys:   dict[str, str] | None = None,
    ) -> None:
        self._provider   = provider.lower()
        self._model_name = model_name
        self._api_keys   = api_keys or {}
        self._backend: Any = self._init_backend()

    # ── Public API ──────────────────────────────────────────────────────────────

    @property
    def dim(self) -> int | None:
        """Return the output vector dimension, or None if unknown."""
        return get_embedding_dim(self._model_name)

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of *texts* and return a list of float vectors."""
        if not texts:
            return []
        return self._backend(texts)

    def embed_one(self, text: str) -> list[float]:
        """Convenience wrapper — embed a single *text* string."""
        return self.embed([text])[0]

    @staticmethod
    def from_config(
        embedding_model: str,
        api_keys: dict[str, str] | None = None,
    ) -> "EmbeddingProvider":
        """Construct an EmbeddingProvider from a "provider/model-name" string.

        The *api_keys* dict may contain keys like OPENAI_API_KEY, VOYAGE_API_KEY.
        Missing keys are automatically pulled from environment variables.

        Examples:
            EmbeddingProvider.from_config("openai/text-embedding-3-small")
            EmbeddingProvider.from_config("voyage/voyage-3", {"VOYAGE_API_KEY": "va-..."})
            EmbeddingProvider.from_config("local/all-MiniLM-L6-v2")
        """
        parts = embedding_model.split("/", 1)
        if len(parts) != 2:
            raise ValueError(
                f"embedding_model must be 'provider/model-name', got: {embedding_model!r}"
            )
        provider, model_name = parts[0], parts[1]
        return EmbeddingProvider(provider, model_name, api_keys)

    # ── Backend initialisation ──────────────────────────────────────────────────

    def _init_backend(self):
        """Return a callable (texts: list[str]) -> list[list[float]]."""
        if self._provider == "openai":
            return self._make_openai_backend()
        if self._provider == "voyage":
            return self._make_voyage_backend()
        if self._provider == "local":
            return self._make_local_backend()
        raise ValueError(
            f"Unknown embedding provider: {self._provider!r}. "
            f"Use 'openai', 'voyage', or 'local'."
        )

    def _make_openai_backend(self):
        try:
            from langchain_openai import OpenAIEmbeddings
        except ImportError as e:
            raise ImportError(
                "OpenAI embeddings require langchain-openai: pip install langchain-openai"
            ) from e
        api_key = (
            self._api_keys.get("OPENAI_API_KEY")
            or os.getenv("OPENAI_API_KEY")
        )
        embedder = OpenAIEmbeddings(model=self._model_name, api_key=api_key)

        def _embed(texts: list[str]) -> list[list[float]]:
            return embedder.embed_documents(texts)

        return _embed

    def _make_voyage_backend(self):
        try:
            import voyageai
        except ImportError as e:
            raise ImportError(
                "Voyage embeddings require voyageai: pip install voyageai"
            ) from e
        api_key = (
            self._api_keys.get("VOYAGE_API_KEY")
            or os.getenv("VOYAGE_API_KEY")
        )
        client = voyageai.Client(api_key=api_key)
        model = self._model_name

        def _embed(texts: list[str]) -> list[list[float]]:
            result = client.embed(texts, model=model)
            return result.embeddings

        return _embed

    def _make_local_backend(self):
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as e:
            raise ImportError(
                "Local embeddings require sentence-transformers: "
                "pip install sentence-transformers"
            ) from e
        model = SentenceTransformer(self._model_name)
        logger.info("Loaded local embedding model: %s", self._model_name)

        def _embed(texts: list[str]) -> list[list[float]]:
            return model.encode(texts, convert_to_tensor=False).tolist()

        return _embed
