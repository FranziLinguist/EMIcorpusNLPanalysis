"""
frequency.py – Word, bigram, and trigram frequency analysis.
"""

import logging
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)


def _save_text_examples(examples: list, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        for ex in examples:
            fh.write(ex + "\n\n")


def _make_ngrams(tokens: List[str], n: int) -> List[Tuple[str, ...]]:
    return [tuple(tokens[i:i+n]) for i in range(len(tokens) - n + 1)]


def run_frequency(corpus: list, config: dict, nlp) -> dict:
    """
    Compute word, bigram and trigram frequencies per document,
    per discipline and corpus-wide.

    Returns
    -------
    results : dict with per_document, per_discipline and corpus sub-dicts.
    """
    output_dir = Path(config["output_dir"])
    save_examples = config.get("save_text_examples", True)
    max_ex = config.get("text_example_max_per_task", 5)
    top_n = config.get("top_n_frequencies", 30)

    per_doc: Dict[str, dict] = {}
    disc_agg: Dict[str, dict] = defaultdict(lambda: {
        "word_counts": Counter(),
        "bigram_counts": Counter(),
        "trigram_counts": Counter(),
    })
    corpus_word: Counter = Counter()
    corpus_bi: Counter = Counter()
    corpus_tri: Counter = Counter()

    text_examples: list = []

    for doc in corpus:
        doc_id = doc["id"]
        discipline = doc["discipline"]
        path = doc["path"]
        text = doc["clean_text"]

        try:
            spacy_doc = nlp(text)
        except Exception as exc:
            logger.error("spaCy error in frequency for '%s': %s", doc_id, exc)
            continue

        # Filtered tokens: alpha, non-stop, lowercase
        tokens = [
            t.text.lower()
            for t in spacy_doc
            if t.is_alpha and not t.is_stop and not t.is_punct and not t.is_space
        ]

        word_counts = Counter(tokens)
        bigram_counts = Counter(_make_ngrams(tokens, 2))
        trigram_counts = Counter(_make_ngrams(tokens, 3))

        per_doc[doc_id] = {
            "discipline": discipline,
            "path": path,
            "top_words": word_counts.most_common(top_n),
            "top_bigrams": [(" ".join(bg), c) for bg, c in bigram_counts.most_common(top_n)],
            "top_trigrams": [(" ".join(tg), c) for tg, c in trigram_counts.most_common(top_n)],
            "total_tokens": len(tokens),
        }

        # Aggregate
        disc_agg[discipline]["word_counts"].update(word_counts)
        disc_agg[discipline]["bigram_counts"].update(bigram_counts)
        disc_agg[discipline]["trigram_counts"].update(trigram_counts)
        corpus_word.update(word_counts)
        corpus_bi.update(bigram_counts)
        corpus_tri.update(trigram_counts)

        if save_examples and len(text_examples) < max_ex:
            top_word = word_counts.most_common(1)
            if top_word:
                word, count = top_word[0]
                # Find a sentence containing this word
                for sent in spacy_doc.sents:
                    if word in sent.text.lower():
                        text_examples.append(
                            f"[SOURCE] {path}\n"
                            f"[LABEL]  Parola più frequente: '{word}' (×{count})\n"
                            f"[TEXT]   {sent.text.strip()}"
                        )
                        break

    # Per-discipline
    per_discipline: Dict[str, dict] = {}
    for disc, agg in disc_agg.items():
        per_discipline[disc] = {
            "top_words": agg["word_counts"].most_common(top_n),
            "top_bigrams": [(" ".join(bg), c) for bg, c in agg["bigram_counts"].most_common(top_n)],
            "top_trigrams": [(" ".join(tg), c) for tg, c in agg["trigram_counts"].most_common(top_n)],
        }

    # Corpus-wide
    corpus_results = {
        "top_words": corpus_word.most_common(top_n),
        "top_bigrams": [(" ".join(bg), c) for bg, c in corpus_bi.most_common(top_n)],
        "top_trigrams": [(" ".join(tg), c) for tg, c in corpus_tri.most_common(top_n)],
    }

    if save_examples:
        ex_dir = output_dir / "text_examples" / "per_document"
        _save_text_examples(text_examples, ex_dir / "frequency_examples.txt")

    logger.info("Frequency analysis complete: %d documents.", len(per_doc))
    return {
        "per_document": per_doc,
        "per_discipline": per_discipline,
        "corpus": corpus_results,
    }
