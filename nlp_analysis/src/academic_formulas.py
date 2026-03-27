"""
academic_formulas.py – Detection of fixed academic formula n-grams.
"""

import logging
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List

logger = logging.getLogger(__name__)


def _save_text_examples(examples: list, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        for ex in examples:
            fh.write(ex + "\n\n")


def _find_sentence_for_formula(text: str, formula: str) -> str:
    """Return the sentence (approx) containing the formula."""
    import re
    lower_text = text.lower()
    idx = lower_text.find(formula.lower())
    if idx == -1:
        return ""
    # Find sentence boundaries around idx
    start = text.rfind(".", 0, idx)
    start = (start + 1) if start != -1 else 0
    end = text.find(".", idx)
    end = (end + 1) if end != -1 else len(text)
    return text[start:end].strip()


def run_academic_formulas(corpus: list, config: dict) -> dict:
    """
    Count occurrences of fixed academic formula phrases.

    Returns
    -------
    results : dict with per_document and per_discipline sub-dicts.
    """
    output_dir = Path(config["output_dir"])
    save_examples = config.get("save_text_examples", True)
    max_ex = config.get("text_example_max_per_task", 5)

    formulas: List[str] = config.get("academic_formulas", [])
    total_formulas = len(formulas)

    per_doc: Dict[str, dict] = {}
    disc_agg: Dict[str, dict] = defaultdict(lambda: {
        "formula_counts": Counter(),
        "total_count": 0,
        "token_count": 0,
        "unique_formulas": set(),
    })

    text_examples: list = []

    for doc in corpus:
        doc_id = doc["id"]
        discipline = doc["discipline"]
        path = doc["path"]
        text = doc["clean_text"]
        text_lower = text.lower()

        # Rough token count (split on whitespace)
        token_count = len(text.split())

        formula_counts: Counter = Counter()
        unique_found: set = set()

        for formula in formulas:
            formula_lower = formula.lower()
            count = text_lower.count(formula_lower)
            if count > 0:
                formula_counts[formula] = count
                unique_found.add(formula)

                if save_examples and len(text_examples) < max_ex:
                    sent = _find_sentence_for_formula(text, formula)
                    if sent:
                        text_examples.append(
                            f"[SOURCE] {path}\n"
                            f"[LABEL]  Formula accademica: '{formula}' (×{count})\n"
                            f"[TEXT]   {sent}"
                        )

        total_count = sum(formula_counts.values())
        density = round(total_count / token_count * 1000, 2) if token_count else 0.0
        unique_ratio = round(len(unique_found) / total_formulas, 4) if total_formulas else 0.0

        per_doc[doc_id] = {
            "discipline": discipline,
            "path": path,
            "total_count": total_count,
            "density_per_1000_tokens": density,
            "unique_formula_ratio": unique_ratio,
            "formula_counts": dict(formula_counts),
            "unique_formulas_found": sorted(unique_found),
        }

        agg = disc_agg[discipline]
        agg["formula_counts"].update(formula_counts)
        agg["total_count"] += total_count
        agg["token_count"] += token_count
        agg["unique_formulas"].update(unique_found)

    # Per-discipline
    per_discipline: Dict[str, dict] = {}
    for disc, agg in disc_agg.items():
        tok = agg["token_count"]
        per_discipline[disc] = {
            "total_count": agg["total_count"],
            "density_per_1000_tokens": round(agg["total_count"] / tok * 1000, 2) if tok else 0.0,
            "unique_formula_ratio": round(len(agg["unique_formulas"]) / total_formulas, 4)
                                    if total_formulas else 0.0,
            "formula_counts": dict(agg["formula_counts"].most_common()),
            "unique_formulas_found": sorted(agg["unique_formulas"]),
        }

    if save_examples:
        ex_dir = output_dir / "text_examples" / "per_document"
        _save_text_examples(text_examples, ex_dir / "academic_formulas_examples.txt")

    logger.info("Academic formulas analysis complete: %d documents.", len(per_doc))
    return {"per_document": per_doc, "per_discipline": per_discipline}
