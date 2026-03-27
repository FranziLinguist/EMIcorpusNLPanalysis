"""
morphology.py – POS distribution, lemma frequency, lexical diversity.
"""

import logging
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict

logger = logging.getLogger(__name__)


def _save_text_examples(examples: list, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        for ex in examples:
            fh.write(ex + "\n\n")


def run_morphology(corpus: list, config: dict, nlp) -> dict:
    """
    Compute POS distribution, lemma frequencies and lexical diversity.

    Returns
    -------
    results : dict with per_document and per_discipline sub-dicts.
    """
    output_dir = Path(config["output_dir"])
    save_examples = config.get("save_text_examples", True)
    max_ex = config.get("text_example_max_per_task", 5)

    per_doc: Dict[str, dict] = {}
    disc_agg: Dict[str, dict] = defaultdict(lambda: {
        "pos_counts": Counter(),
        "lemma_counts": Counter(),
        "token_count": 0,
        "unique_lemmas": set(),
    })

    high_diversity_examples: list = []
    rare_lemma_examples: list = []

    for doc in corpus:
        doc_id = doc["id"]
        discipline = doc["discipline"]
        path = doc["path"]
        text = doc["clean_text"]

        try:
            spacy_doc = nlp(text)
        except Exception as exc:
            logger.error("spaCy error in morphology for '%s': %s", doc_id, exc)
            continue

        pos_counts: Counter = Counter()
        lemma_counts: Counter = Counter()
        all_tokens = []

        for token in spacy_doc:
            if token.is_space:
                continue
            pos_counts[token.pos_] += 1
            all_tokens.append(token)
            if not token.is_stop and not token.is_punct and token.is_alpha:
                lemma_counts[token.lemma_.lower()] += 1

        total_tokens = len(all_tokens)
        unique_lemmas = set(lemma_counts.keys())
        ttr = round(len(unique_lemmas) / total_tokens, 4) if total_tokens else 0.0

        # POS percentages
        pos_pct = {
            pos: round(cnt / total_tokens * 100, 2) if total_tokens else 0.0
            for pos, cnt in pos_counts.items()
        }

        per_doc[doc_id] = {
            "discipline": discipline,
            "path": path,
            "total_tokens": total_tokens,
            "pos_counts": dict(pos_counts),
            "pos_percentages": pos_pct,
            "lemma_frequency": lemma_counts.most_common(50),
            "unique_lemma_count": len(unique_lemmas),
            "lexical_diversity_ttr": ttr,
        }

        # Aggregate
        agg = disc_agg[discipline]
        agg["pos_counts"].update(pos_counts)
        agg["lemma_counts"].update(lemma_counts)
        agg["token_count"] += total_tokens
        agg["unique_lemmas"].update(unique_lemmas)

        # Text examples
        if save_examples:
            # High-diversity sentence: sentence whose tokens have most unique lemmas
            sentences = list(spacy_doc.sents)
            if sentences:
                def sent_ttr(s):
                    toks = [t for t in s if not t.is_punct and not t.is_space and t.is_alpha]
                    if not toks:
                        return 0.0
                    return len({t.lemma_.lower() for t in toks}) / len(toks)

                best_sent = max(sentences, key=sent_ttr)
                high_diversity_examples.append(
                    f"[SOURCE] {path}\n"
                    f"[LABEL]  Alta diversità lessicale (TTR doc={ttr})\n"
                    f"[TEXT]   {best_sent.text.strip()}"
                )

            # Rare lemmas in doc (frequency == 1)
            rare = [l for l, c in lemma_counts.items() if c == 1]
            if rare:
                rare_lemma_examples.append(
                    f"[SOURCE] {path}\n"
                    f"[LABEL]  Lemmi rari (hapax): {', '.join(rare[:10])}\n"
                    f"[TEXT]   (lista parziale)"
                )

    # Per-discipline aggregates
    per_discipline: Dict[str, dict] = {}
    for disc, agg in disc_agg.items():
        total = agg["token_count"]
        pos_pct = {
            pos: round(cnt / total * 100, 2) if total else 0.0
            for pos, cnt in agg["pos_counts"].items()
        }
        unique_count = len(agg["unique_lemmas"])
        per_discipline[disc] = {
            "total_tokens": total,
            "pos_counts": dict(agg["pos_counts"]),
            "pos_percentages": pos_pct,
            "top_lemmas": agg["lemma_counts"].most_common(50),
            "unique_lemma_count": unique_count,
            "lexical_diversity_ttr": round(unique_count / total, 4) if total else 0.0,
        }

    if save_examples:
        ex_dir = output_dir / "text_examples" / "per_document"
        _save_text_examples(high_diversity_examples[:max_ex], ex_dir / "morphology_high_diversity.txt")
        _save_text_examples(rare_lemma_examples[:max_ex],     ex_dir / "morphology_rare_lemmas.txt")

    logger.info("Morphology analysis complete: %d documents.", len(per_doc))
    return {"per_document": per_doc, "per_discipline": per_discipline}
