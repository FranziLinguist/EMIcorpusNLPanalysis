"""
similarity.py – Discipline-level text similarity (TF-IDF cosine, Jaccard, embeddings).
"""

import logging
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np

logger = logging.getLogger(__name__)


def _char_ngrams(text: str, n: int) -> set:
    text_lower = text.lower().replace(" ", "")
    return set(text_lower[i:i+n] for i in range(len(text_lower) - n + 1))


def _word_ngrams(tokens: List[str], n: int) -> set:
    return set(tuple(tokens[i:i+n]) for i in range(len(tokens) - n + 1))


def _jaccard(set_a: set, set_b: set) -> float:
    if not set_a and not set_b:
        return 1.0
    union = set_a | set_b
    if not union:
        return 0.0
    return round(len(set_a & set_b) / len(union), 4)


def _save_text_examples(examples: list, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        for ex in examples:
            fh.write(ex + "\n\n")


def run_similarity(corpus: list, config: dict, nlp) -> dict:
    """
    Compute three similarity matrices at the discipline level:
    1. TF-IDF cosine similarity
    2. Jaccard on char n-grams and word n-grams
    3. spaCy embedding similarity (if use_sentence_embeddings)

    Returns
    -------
    results : dict with discipline names, matrices and summary.
    """
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity

    output_dir = Path(config["output_dir"])
    save_examples = config.get("save_text_examples", True)
    max_ex = config.get("text_example_max_per_task", 5)
    char_n = config.get("ngram_overlap_char_n", 3)
    word_ns: List[int] = config.get("ngram_overlap_word_n", [2, 3])
    use_embeddings: bool = config.get("use_sentence_embeddings", True)

    # Aggregate texts per discipline
    disc_texts: Dict[str, str] = defaultdict(str)
    for doc in corpus:
        disc_texts[doc["discipline"]] += " " + doc["clean_text"]

    disciplines = sorted(disc_texts.keys())
    n = len(disciplines)

    if n < 2:
        logger.warning("Need at least 2 disciplines for similarity – skipping.")
        return {}

    # ── 1. TF-IDF Cosine ────────────────────────────────────────────────────
    try:
        tfidf_vec = TfidfVectorizer(
            stop_words="english",
            sublinear_tf=True,
            max_features=10000,
        )
        tfidf_mat = tfidf_vec.fit_transform([disc_texts[d] for d in disciplines])
        cosine_mat = cosine_similarity(tfidf_mat).tolist()
    except Exception as exc:
        logger.error("TF-IDF cosine similarity failed: %s", exc)
        cosine_mat = [[0.0] * n for _ in range(n)]

    # ── 2. Jaccard on char + word n-grams ───────────────────────────────────
    char_ngram_sets = {d: _char_ngrams(disc_texts[d], char_n) for d in disciplines}

    word_ngram_sets: Dict[str, Dict[int, set]] = {}
    for d in disciplines:
        try:
            spacy_doc = nlp(disc_texts[d][:100000])  # cap length for speed
        except Exception:
            spacy_doc = None
        tokens = (
            [t.text.lower() for t in spacy_doc if t.is_alpha and not t.is_stop]
            if spacy_doc else []
        )
        word_ngram_sets[d] = {wn: _word_ngrams(tokens, wn) for wn in word_ns}

    jaccard_char_mat = np.zeros((n, n))
    jaccard_word_mats: Dict[int, np.ndarray] = {wn: np.zeros((n, n)) for wn in word_ns}

    for i, di in enumerate(disciplines):
        for j, dj in enumerate(disciplines):
            jaccard_char_mat[i][j] = _jaccard(char_ngram_sets[di], char_ngram_sets[dj])
            for wn in word_ns:
                jaccard_word_mats[wn][i][j] = _jaccard(
                    word_ngram_sets[di][wn], word_ngram_sets[dj][wn]
                )

    # ── 3. spaCy embedding similarity ───────────────────────────────────────
    embedding_mat = np.zeros((n, n))
    if use_embeddings:
        for i, di in enumerate(disciplines):
            try:
                vec_i = nlp(disc_texts[di][:50000]).vector
            except Exception:
                vec_i = np.zeros(300)
            for j, dj in enumerate(disciplines):
                try:
                    vec_j = nlp(disc_texts[dj][:50000]).vector
                except Exception:
                    vec_j = np.zeros(300)
                # Cosine similarity
                norm = np.linalg.norm(vec_i) * np.linalg.norm(vec_j)
                if norm > 0:
                    embedding_mat[i][j] = round(float(np.dot(vec_i, vec_j) / norm), 4)
                else:
                    embedding_mat[i][j] = 0.0

    # ── Summary / correlation ────────────────────────────────────────────────
    text_examples: list = []
    # Find most-similar pair (excluding diagonal)
    cosine_arr = np.array(cosine_mat)
    np.fill_diagonal(cosine_arr, -1)
    if cosine_arr.size > 0:
        flat_idx = cosine_arr.argmax()
        ri, ci = divmod(flat_idx, n)
        text_examples.append(
            f"[SOURCE] Corpus\n"
            f"[LABEL]  Coppia più simile (TF-IDF coseno)\n"
            f"[TEXT]   {disciplines[ri]} ↔ {disciplines[ci]}: "
            f"cosine={cosine_mat[ri][ci]:.4f}"
        )

    if save_examples:
        ex_dir = output_dir / "text_examples" / "corpus"
        _save_text_examples(text_examples, ex_dir / "similarity_examples.txt")

    logger.info("Similarity analysis complete: %d disciplines.", n)
    return {
        "disciplines": disciplines,
        "cosine_similarity": cosine_mat,
        "jaccard_char": {
            "n": char_n,
            "matrix": jaccard_char_mat.tolist(),
        },
        "jaccard_word": {
            wn: jaccard_word_mats[wn].tolist() for wn in word_ns
        },
        "embedding_similarity": embedding_mat.tolist() if use_embeddings else None,
    }
