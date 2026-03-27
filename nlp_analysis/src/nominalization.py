"""
nominalization.py – Count and categorise nominalised forms.
"""

import logging
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List

logger = logging.getLogger(__name__)

NON_ACADEMIC_STOPLIST = {
    "question", "attention", "moment", "action", "section", "mention",
    "position", "addition", "station", "nation", "pension", "tension",
    "session", "mission", "fashion", "passion", "version", "person",
    "reason", "season", "lesson", "prison", "weapon", "button",
    "cotton", "common", "open",
}


def _get_suffix(word: str, suffixes: List[str]) -> str:
    """Return the matching suffix (longest match) or empty string."""
    word_lower = word.lower()
    # Sort by length descending to find longest match first
    for suffix in sorted(suffixes, key=len, reverse=True):
        clean_suffix = suffix.lstrip("-")
        if word_lower.endswith(clean_suffix) and len(word_lower) > len(clean_suffix) + 1:
            return suffix
    return ""


def _save_text_examples(examples: list, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        for ex in examples:
            fh.write(ex + "\n\n")


def run_nominalization(corpus: list, config: dict, nlp) -> dict:
    """
    Detect nominalisations using suffix matching.

    Returns
    -------
    results : dict with per_document and per_discipline sub-dicts.
    """
    output_dir = Path(config["output_dir"])
    save_examples = config.get("save_text_examples", True)
    max_ex = config.get("text_example_max_per_task", 5)

    raw_suffixes: List[str] = config.get("nominalization_suffixes", [])

    per_doc: Dict[str, dict] = {}
    disc_agg: Dict[str, dict] = defaultdict(lambda: {
        "total_nominalizations": 0,
        "suffix_counts": Counter(),
        "token_count": 0,
        "top_forms": Counter(),
    })

    text_examples: list = []

    for doc in corpus:
        doc_id = doc["id"]
        discipline = doc["discipline"]
        path = doc["path"]
        text = doc["clean_text"]

        try:
            spacy_doc = nlp(text)
        except Exception as exc:
            logger.error("spaCy error in nominalization for '%s': %s", doc_id, exc)
            continue

        total_tokens = 0
        nom_count = 0
        suffix_counts: Counter = Counter()
        form_counts: Counter = Counter()

        for token in spacy_doc:
            if token.is_space or token.is_punct:
                continue
            total_tokens += 1

            if not token.is_alpha:
                continue

            word = token.text
            word_lower = word.lower()

            # Skip stopwords and short words
            if token.is_stop or len(word_lower) <= 4:
                continue

            # Skip non-academic common words
            if word_lower in NON_ACADEMIC_STOPLIST:
                continue

            # Only NOUN POS
            if token.pos_ != "NOUN":
                continue

            matched_suffix = _get_suffix(word, raw_suffixes)
            if matched_suffix:
                nom_count += 1
                suffix_counts[matched_suffix] += 1
                form_counts[word_lower] += 1

                if save_examples and len(text_examples) < max_ex:
                    text_examples.append(
                        f"[SOURCE] {path}\n"
                        f"[LABEL]  Nominalizzazione (suffisso: {matched_suffix}): '{word}'\n"
                        f"[TEXT]   {token.sent.text.strip()}"
                    )

        density = round(nom_count / total_tokens * 100, 2) if total_tokens else 0.0

        per_doc[doc_id] = {
            "discipline": discipline,
            "path": path,
            "total_nominalizations": nom_count,
            "density_per_100_tokens": density,
            "total_tokens": total_tokens,
            "suffix_distribution": dict(suffix_counts),
            "top_forms": form_counts.most_common(20),
        }

        agg = disc_agg[discipline]
        agg["total_nominalizations"] += nom_count
        agg["suffix_counts"].update(suffix_counts)
        agg["token_count"] += total_tokens
        agg["top_forms"].update(form_counts)

    # Per-discipline
    per_discipline: Dict[str, dict] = {}
    for disc, agg in disc_agg.items():
        total_tok = agg["token_count"]
        per_discipline[disc] = {
            "total_nominalizations": agg["total_nominalizations"],
            "density_per_100_tokens": round(
                agg["total_nominalizations"] / total_tok * 100, 2
            ) if total_tok else 0.0,
            "total_tokens": total_tok,
            "suffix_distribution": dict(agg["suffix_counts"]),
            "top_forms": agg["top_forms"].most_common(20),
        }

    if save_examples:
        ex_dir = output_dir / "text_examples" / "per_document"
        _save_text_examples(text_examples, ex_dir / "nominalization_examples.txt")

    logger.info("Nominalization analysis complete: %d documents.", len(per_doc))
    return {"per_document": per_doc, "per_discipline": per_discipline}
