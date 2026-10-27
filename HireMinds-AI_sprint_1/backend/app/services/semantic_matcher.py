"""
Sentence Transformer semantic matching service.

How it works (student explanation):
-------------------------------------
Sentence Transformers are pre-trained neural networks that read a sentence
(or paragraph) and output a VECTOR of numbers called an *embedding*.

The key insight is that semantically similar sentences have embeddings that
POINT IN SIMILAR DIRECTIONS in high-dimensional space – even if they use
completely different words.

Example:
  "Python developer with ML experience"  →  embedding A
  "Software engineer skilled in machine learning"  →  embedding B

Even though almost no words overlap, A and B will be very close in embedding
space because the model learned the meaning of the phrases from billions of
text samples during pre-training.

We then compute Cosine Similarity between the two embeddings, exactly like we
do with TF-IDF vectors.

Strengths:
  ✔ Understands synonyms and paraphrases
  ✔ Language-level understanding, not just keyword matching

Limitations:
  ✗ Slower than TF-IDF – model must run inference (though cached)
  ✗ Requires downloading model weights on first run (~90 MB)
  ✗ Less precise for exact technical terms (TF-IDF does that better)

Model choice:
  'all-MiniLM-L6-v2' – a 6-layer distilled MiniLM model.
  Why: Best balance of speed, size, and accuracy for semantic textual
  similarity tasks. 384-dimensional embeddings.
"""
from __future__ import annotations

import logging
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------ #
#  Lazy singleton pattern                                              #
#  The model is ~90 MB. We load it ONCE and reuse it for the entire  #
#  process lifetime. Using a module-level variable is the simplest   #
#  way to share state across requests in a single FastAPI process.   #
# ------------------------------------------------------------------ #
_model = None
_MODEL_NAME = "all-MiniLM-L6-v2"


def _get_model():
    """
    Lazily initialise and return the Sentence Transformer model.
    Thread-safe enough for single-process uvicorn; use a proper lock
    if you run with multiple workers.
    """
    global _model
    if _model is None:
        try:
            from sentence_transformers import SentenceTransformer  # noqa: WPS433
            logger.info("Loading Sentence Transformer model: %s", _MODEL_NAME)
            _model = SentenceTransformer(_MODEL_NAME)
            logger.info("Sentence Transformer model loaded successfully.")
        except ImportError:
            logger.error(
                "sentence-transformers package not installed. "
                "Run: pip install sentence-transformers"
            )
            raise
    return _model


def compute_semantic_similarity(text_a: str, text_b: str) -> float:
    """
    Return the cosine similarity (0.0 – 1.0) between two texts using
    a pre-trained Sentence Transformer.

    Parameters
    ----------
    text_a : str
        First document (e.g. resume raw text).
    text_b : str
        Second document (e.g. job description).

    Returns
    -------
    float
        Cosine similarity rounded to 4 decimal places.
        Returns 0.0 if either input is empty/whitespace or model fails.
    """
    # Guard: empty inputs
    if not text_a or not text_a.strip():
        return 0.0
    if not text_b or not text_b.strip():
        return 0.0

    try:
        model = _get_model()

        # Encode both texts. convert_to_numpy=True returns numpy arrays.
        # show_progress_bar=False keeps logs clean in API context.
        embeddings = model.encode(
            [text_a, text_b],
            convert_to_numpy=True,
            show_progress_bar=False,
            normalize_embeddings=True,   # L2-normalise → dot product == cosine sim
        )

        # After L2 normalisation, cosine similarity = dot product
        score: float = float(np.dot(embeddings[0], embeddings[1]))

        # Clamp to [0, 1] – very dissimilar texts can yield small negatives
        score = max(0.0, min(1.0, score))

        return round(score, 4)

    except Exception as exc:
        logger.error("Semantic similarity computation failed: %s", exc)
        return 0.0


def is_model_available() -> bool:
    """
    Check whether the Sentence Transformer model can be initialised.
    Used by the health-check endpoint.
    """
    try:
        _get_model()
        return True
    except Exception:
        return False
