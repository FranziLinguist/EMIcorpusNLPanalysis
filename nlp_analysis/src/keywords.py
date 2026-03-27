"""
keywords.py – TF-IDF keyword extraction per document, discipline and corpus.
"""

import logging
from collections import defaultdict
from pathlib import Path
from typing import Dict, List

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

logger = logging.getLogger(__name__)


def _save_text_examples(examples: list, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        for ex in examples:
            fh.write(ex + "\n\n")


def run_keywords(corpus: list, config: dict) -> dict:
    """
    Extract TF-IDF keywords per document, per discipline and corpus-wide.

    Returns
    -------
    results : dict with per_document, per_discipline and corpus sub-dicts.
    """
    output_dir = Path(config["output_dir"])
    save_examples = config.get("save_text_examples", True)
    max_ex = config.get("text_example_max_per_task", 5)
    top_n = config.get("top_n_keywords", 20)

    if not corpus:
        logger.warning("Empty corpus in run_keywords.")
        return {"per_document": {}, "per_discipline": {}, "corpus": []}

    # Build document texts
    doc_ids = [d["id"] for d in corpus]
    doc_texts = [d["clean_text"] for d in corpus]
    doc_disciplines = [d["discipline"] for d in corpus]
    doc_paths = [d["path"] for d in corpus]

    # Fit TF-IDF on full corpus
    vectorizer = TfidfVectorizer(
        max_features=10000,
        ngram_range=(1, 2),
        stop_words="english",
        min_df=1,
        sublinear_tf=True,
    )
    try:
        tfidf_matrix = vectorizer.fit_transform(doc_texts)
    except Exception as exc:
        logger.error("TF-IDF fitting failed: %s", exc)
        return {"per_document": {}, "per_discipline": {}, "corpus": []}

    feature_names: List[str] = vectorizer.get_feature_names_out().tolist()

    per_doc: Dict[str, dict] = {}
    text_examples: list = []

    for i, (doc_id, path, discipline) in enumerate(zip(doc_ids, doc_paths, doc_disciplines)):
        row = tfidf_matrix[i].toarray()[0]
        top_indices = row.argsort()[::-1][:top_n]
        keywords = [
            {"keyword": feature_names[j], "score": round(float(row[j]), 6)}
            for j in top_indices if row[j] > 0
        ]

        per_doc[doc_id] = {
            "discipline": discipline,
            "path": path,
            "keywords": keywords,
        }

        if save_examples and len(text_examples) < max_ex and keywords:
            top_kw = keywords[0]["keyword"]
            text_examples.append(
                f"[SOURCE] {path}\n"
                f"[LABEL]  Keyword TF-IDF #1: '{top_kw}' (score={keywords[0]['score']})\n"
                f"[TEXT]   Top 5 keywords: {', '.join(k['keyword'] for k in keywords[:5])}"
            )

    # Per-discipline: concatenate discipline texts and re-fit
    disc_texts: Dict[str, str] = defaultdict(str)
    for doc in corpus:
        disc_texts[doc["discipline"]] += " " + doc["clean_text"]

    per_discipline: Dict[str, dict] = {}
    if len(disc_texts) > 1:
        disc_names = list(disc_texts.keys())
        disc_docs = [disc_texts[d] for d in disc_names]
        try:
            disc_vectorizer = TfidfVectorizer(
                max_features=5000,
                ngram_range=(1, 2),
                stop_words="english",
                sublinear_tf=True,
            )
            disc_matrix = disc_vectorizer.fit_transform(disc_docs)
            disc_features = disc_vectorizer.get_feature_names_out().tolist()
            for i, disc in enumerate(disc_names):
                row = disc_matrix[i].toarray()[0]
                top_idx = row.argsort()[::-1][:top_n]
                per_discipline[disc] = {
                    "keywords": [
                        {"keyword": disc_features[j], "score": round(float(row[j]), 6)}
                        for j in top_idx if row[j] > 0
                    ]
                }
        except Exception as exc:
            logger.error("Discipline TF-IDF failed: %s", exc)

    # Corpus-wide: average TF-IDF scores across all documents
    mean_scores = np.asarray(tfidf_matrix.mean(axis=0)).flatten()
    top_corpus_idx = mean_scores.argsort()[::-1][:top_n]
    corpus_keywords = [
        {"keyword": feature_names[j], "score": round(float(mean_scores[j]), 6)}
        for j in top_corpus_idx
    ]

    if save_examples:
        ex_dir = output_dir / "text_examples" / "per_document"
        _save_text_examples(text_examples, ex_dir / "keywords_examples.txt")

    logger.info("Keywords extraction complete: %d documents.", len(per_doc))
    return {
        "per_document": per_doc,
        "per_discipline": per_discipline,
        "corpus": corpus_keywords,
    }
