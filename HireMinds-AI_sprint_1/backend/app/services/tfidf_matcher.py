"""
TF-IDF + Cosine Similarity matching service.

How it works (student explanation):
-------------------------------------
TF-IDF stands for Term Frequency–Inverse Document Frequency.

  • TF  = how often a word appears in a document
  • IDF = how rare that word is across ALL documents

Words that appear a lot in one document but rarely in others get HIGH scores.
Words that appear everywhere ("the", "and") get LOW scores.

We convert both the resume and the job description into TF-IDF vectors –
think of them as lists of numbers, one number per unique word.

Cosine Similarity then measures the ANGLE between these two vectors.
  • 1.0 → perfectly aligned (identical wording)
  • 0.0 → completely unrelated

Strengths:
  ✔ Fast – no GPU, no internet
  ✔ Good at keyword matching (exact technology names)
  ✔ Explainable – we can see which terms drove the score

Limitations:
  ✗ Misses synonyms ("ML" vs "machine learning")
  ✗ Treats every word independently – no understanding of meaning
"""
from typing import Optional

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def compute_tfidf_similarity(text_a: str, text_b: str) -> float:
    """
    Return the cosine similarity (0.0 – 1.0) between two plain-text documents
    using TF-IDF vectorisation.

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
        Returns 0.0 if either input is empty/whitespace.
    """
    # Guard: empty inputs produce no meaningful vector
    if not text_a or not text_a.strip():
        return 0.0
    if not text_b or not text_b.strip():
        return 0.0

    # Build a fresh vectoriser for this pair.
    # sublinear_tf=True applies log-scaling to term frequencies which reduces
    # the impact of very common words inside a single document.
    vectorizer = TfidfVectorizer(
        sublinear_tf=True,
        strip_accents="unicode",
        analyzer="word",
        token_pattern=r"(?u)\b\w+\b",   # keeps single-letter tokens (e.g. C)
        ngram_range=(1, 2),             # unigrams + bigrams ("machine learning")
        min_df=1,
    )

    try:
        # fit_transform expects an iterable; we pass both texts at once so the
        # vocabulary is built from their union – fair comparison.
        tfidf_matrix = vectorizer.fit_transform([text_a, text_b])
    except ValueError:
        # fit_transform raises ValueError on empty vocabulary
        return 0.0

    # tfidf_matrix is a (2, vocab_size) sparse matrix.
    # Row 0 → text_a vector, Row 1 → text_b vector.
    score: float = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]

    return round(float(score), 4)
