"""
cohesion.py – Discourse markers / cohesive device detection.
"""

import logging
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List

logger = logging.getLogger(__name__)


def _save_text_examples(examples: list, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        for ex in examples:
            fh.write(ex + "\n\n")


def _split_sentences(text: str) -> List[str]:
    """Simple sentence splitter on '.', '!', '?' boundaries."""
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    return [s.strip() for s in sentences if s.strip()]


def run_cohesion(corpus: list, config: dict) -> dict:
    """
    Detect discourse markers (cohesive devices) across category buckets.

    Returns
    -------
    results : dict with per_document and per_discipline sub-dicts.
    """
    output_dir = Path(config["output_dir"])
    save_examples = config.get("save_text_examples", True)
    max_ex = config.get("text_example_max_per_task", 5)

    raw_markers: dict = config.get("discourse_markers", {})
    # Flatten all markers for quick search
    all_markers: dict = {}
    for category, markers in raw_markers.items():
        for marker in markers:
            all_markers[marker.lower()] = category

    per_doc: Dict[str, dict] = {}
    disc_agg: Dict[str, dict] = defaultdict(lambda: {
        "category_counts": Counter(),
        "marker_counts": Counter(),
        "sentence_count": 0,
        "total_markers": 0,
        "unique_markers": set(),
    })

    category_examples: dict = defaultdict(list)
    no_marker_examples: list = []

    for doc in corpus:
        doc_id = doc["id"]
        discipline = doc["discipline"]
        path = doc["path"]
        text = doc["clean_text"]

        sentences = _split_sentences(text)
        n_sents = len(sentences)

        category_counts: Counter = Counter()
        marker_counts: Counter = Counter()
        unique_found: set = set()
        total_markers = 0

        # Track consecutive sentences without any marker
        no_marker_streak = 0
        long_no_marker_passages: list = []
        streak_start = 0

        for i, sent in enumerate(sentences):
            sent_lower = sent.lower()
            found_in_sent = False

            for marker, category in all_markers.items():
                # Use word-boundary-aware matching for single words,
                # substring matching for multi-word phrases
                if " " in marker:
                    hit = marker in sent_lower
                else:
                    hit = bool(re.search(r'\b' + re.escape(marker) + r'\b', sent_lower))

                if hit:
                    category_counts[category] += 1
                    marker_counts[marker] += 1
                    unique_found.add(marker)
                    total_markers += 1
                    found_in_sent = True

                    if save_examples and len(category_examples[category]) < max_ex:
                        category_examples[category].append(
                            f"[SOURCE] {path} (sentence {i+1})\n"
                            f"[LABEL]  Connettivo {category}: '{marker}'\n"
                            f"[TEXT]   {sent.strip()}"
                        )

            if not found_in_sent:
                if no_marker_streak == 0:
                    streak_start = i
                no_marker_streak += 1
                if no_marker_streak >= 5 and save_examples and len(no_marker_examples) < max_ex:
                    passage = " ".join(sentences[streak_start:i+1])
                    no_marker_examples.append(
                        f"[SOURCE] {path} (sentences {streak_start+1}–{i+1})\n"
                        f"[LABEL]  Passaggio senza connettivi ({no_marker_streak} frasi)\n"
                        f"[TEXT]   {passage[:400]}…"
                    )
            else:
                no_marker_streak = 0

        density = round(total_markers / n_sents * 100, 2) if n_sents else 0.0
        diversity = round(len(unique_found) / total_markers, 4) if total_markers else 0.0

        per_doc[doc_id] = {
            "discipline": discipline,
            "path": path,
            "sentence_count": n_sents,
            "total_markers": total_markers,
            "density_per_100_sentences": density,
            "diversity_index": diversity,
            "category_counts": dict(category_counts),
            "marker_counts": dict(marker_counts.most_common(20)),
            "unique_markers_found": sorted(unique_found),
        }

        agg = disc_agg[discipline]
        agg["category_counts"].update(category_counts)
        agg["marker_counts"].update(marker_counts)
        agg["sentence_count"] += n_sents
        agg["total_markers"] += total_markers
        agg["unique_markers"].update(unique_found)

    # Per-discipline
    per_discipline: Dict[str, dict] = {}
    for disc, agg in disc_agg.items():
        n_s = agg["sentence_count"]
        tm = agg["total_markers"]
        per_discipline[disc] = {
            "sentence_count": n_s,
            "total_markers": tm,
            "density_per_100_sentences": round(tm / n_s * 100, 2) if n_s else 0.0,
            "diversity_index": round(len(agg["unique_markers"]) / tm, 4) if tm else 0.0,
            "category_counts": dict(agg["category_counts"]),
            "top_markers": dict(agg["marker_counts"].most_common(20)),
            "unique_markers_found": sorted(agg["unique_markers"]),
        }

    if save_examples:
        ex_dir = output_dir / "text_examples" / "per_document"
        for cat, exs in category_examples.items():
            _save_text_examples(exs, ex_dir / f"cohesion_{cat}.txt")
        _save_text_examples(no_marker_examples, ex_dir / "cohesion_no_markers.txt")

    logger.info("Cohesion analysis complete: %d documents.", len(per_doc))
    return {"per_document": per_doc, "per_discipline": per_discipline}
