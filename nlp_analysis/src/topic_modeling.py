"""
topic_modeling.py – LDA topic modelling with Gensim.
"""

import logging
import random
from collections import defaultdict
from pathlib import Path
from typing import Dict, List

import numpy as np

logger = logging.getLogger(__name__)


def _save_text_examples(examples: list, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        for ex in examples:
            fh.write(ex + "\n\n")


def _tokenize_for_lda(text: str, nlp) -> List[str]:
    """Lemmatize, remove stopwords / punct, return lowercase token list."""
    doc = nlp(text)
    return [
        t.lemma_.lower()
        for t in doc
        if t.is_alpha and not t.is_stop and len(t.lemma_) > 2
    ]


def run_topic_modeling(corpus: list, config: dict, nlp) -> dict:
    """
    Train LDA model and return per-doc and per-discipline topic assignments.

    Returns
    -------
    results : dict with topics, per_document and per_discipline sub-dicts.
    """
    try:
        from gensim import corpora
        from gensim.models import LdaModel
    except ImportError:
        logger.error("Gensim not installed – skipping topic modelling.")
        return {}

    output_dir = Path(config["output_dir"])
    save_examples = config.get("save_text_examples", True)
    max_ex = config.get("text_example_max_per_task", 5)
    num_topics = config.get("lda_num_topics", 8)
    passes = config.get("lda_passes", 10)

    random.seed(42)
    np.random.seed(42)

    if not corpus:
        logger.warning("Empty corpus in run_topic_modeling.")
        return {}

    logger.info("Tokenising documents for LDA…")
    tokenised: List[List[str]] = []
    doc_ids: List[str] = []
    doc_disciplines: List[str] = []
    doc_paths: List[str] = []

    for doc in corpus:
        try:
            tokens = _tokenize_for_lda(doc["clean_text"], nlp)
        except Exception as exc:
            logger.error("LDA tokenisation error for '%s': %s", doc["id"], exc)
            tokens = []
        tokenised.append(tokens)
        doc_ids.append(doc["id"])
        doc_disciplines.append(doc["discipline"])
        doc_paths.append(doc["path"])

    # Build dictionary and corpus
    dictionary = corpora.Dictionary(tokenised)
    dictionary.filter_extremes(no_below=1, no_above=0.95)
    bow_corpus = [dictionary.doc2bow(toks) for toks in tokenised]

    logger.info("Training LDA: %d topics, %d passes…", num_topics, passes)
    try:
        lda_model = LdaModel(
            corpus=bow_corpus,
            id2word=dictionary,
            num_topics=num_topics,
            passes=passes,
            random_state=42,
            alpha="auto",
            eta="auto",
        )
    except Exception as exc:
        logger.error("LDA training failed: %s", exc)
        return {}

    # Extract top words per topic
    topics: List[dict] = []
    for topic_id in range(num_topics):
        top_words = lda_model.show_topic(topic_id, topn=10)
        topics.append({
            "topic_id": topic_id,
            "top_words": [(word, round(weight, 4)) for word, weight in top_words],
        })

    per_doc: Dict[str, dict] = {}
    disc_topic_agg: Dict[str, list] = defaultdict(list)

    text_examples: list = []

    for i, doc_id in enumerate(doc_ids):
        topic_dist = lda_model.get_document_topics(bow_corpus[i], minimum_probability=0.0)
        topic_dist_sorted = sorted(topic_dist, key=lambda x: x[1], reverse=True)
        dominant_topic = topic_dist_sorted[0][0] if topic_dist_sorted else 0
        dominant_prob = topic_dist_sorted[0][1] if topic_dist_sorted else 0.0

        per_doc[doc_id] = {
            "discipline": doc_disciplines[i],
            "path": doc_paths[i],
            "dominant_topic": dominant_topic,
            "dominant_topic_prob": round(float(dominant_prob), 4),
            "topic_distribution": [
                {"topic_id": tid, "probability": round(float(prob), 4)}
                for tid, prob in topic_dist
            ],
        }

        disc_topic_agg[doc_disciplines[i]].append(dominant_topic)

        if save_examples and len(text_examples) < max_ex:
            top_words_str = ", ".join(w for w, _ in topics[dominant_topic]["top_words"][:5])
            text_examples.append(
                f"[SOURCE] {doc_paths[i]}\n"
                f"[LABEL]  Topic dominante: {dominant_topic} ({top_words_str})\n"
                f"[TEXT]   (probabilità: {dominant_prob:.3f})"
            )

    # Per-discipline: majority dominant topic
    per_discipline: Dict[str, dict] = {}
    from collections import Counter
    for disc, topic_list in disc_topic_agg.items():
        topic_counter = Counter(topic_list)
        majority_topic = topic_counter.most_common(1)[0][0]
        per_discipline[disc] = {
            "dominant_topic": majority_topic,
            "topic_distribution": dict(topic_counter),
            "top_words": topics[majority_topic]["top_words"],
        }

    if save_examples:
        ex_dir = output_dir / "text_examples" / "per_document"
        _save_text_examples(text_examples, ex_dir / "topic_modeling_examples.txt")

    logger.info("Topic modelling complete: %d topics, %d documents.", num_topics, len(per_doc))
    return {
        "topics": topics,
        "per_document": per_doc,
        "per_discipline": per_discipline,
        "num_topics": num_topics,
    }
