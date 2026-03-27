"""
dependency.py – Dependency parse visualisation and label distribution.
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


def run_dependency(corpus: list, config: dict, nlp) -> dict:
    """
    Generate displacy SVG parse trees and collect dependency label stats.

    Returns
    -------
    results : dict with per_document and per_discipline sub-dicts.
    """
    try:
        from spacy import displacy
    except ImportError:
        logger.error("spaCy displacy not available.")
        displacy = None

    output_dir = Path(config["output_dir"])
    images_dir = output_dir / "images" / "per_document"
    images_dir.mkdir(parents=True, exist_ok=True)

    save_examples = config.get("save_text_examples", True)
    max_ex = config.get("text_example_max_per_task", 5)
    max_sents = config.get("dep_parse_max_sentences", 3)

    per_doc: Dict[str, dict] = {}
    disc_agg: Dict[str, dict] = defaultdict(Counter)

    text_examples: list = []

    for doc in corpus:
        doc_id = doc["id"]
        discipline = doc["discipline"]
        path = doc["path"]
        text = doc["clean_text"]

        try:
            spacy_doc = nlp(text)
        except Exception as exc:
            logger.error("spaCy error in dependency for '%s': %s", doc_id, exc)
            continue

        dep_counts: Counter = Counter()
        for token in spacy_doc:
            if token.dep_ and not token.is_space:
                dep_counts[token.dep_] += 1

        # Generate SVG for first N sentences
        svg_paths = []
        sentences = list(spacy_doc.sents)
        for i, sent in enumerate(sentences[:max_sents]):
            if displacy is not None:
                try:
                    svg = displacy.render(
                        sent.as_doc(),
                        style="dep",
                        jupyter=False,
                        options={"compact": True},
                    )
                    svg_path = images_dir / f"{doc_id}_dep_{i}.svg"
                    svg_path.write_text(svg, encoding="utf-8")
                    svg_paths.append(str(svg_path))
                except Exception as exc:
                    logger.warning("displacy render failed for '%s' sent %d: %s", doc_id, i, exc)

            if save_examples and len(text_examples) < max_ex:
                text_examples.append(
                    f"[SOURCE] {path} (sentence {i+1})\n"
                    f"[LABEL]  Analisi delle dipendenze\n"
                    f"[TEXT]   {sent.text.strip()}"
                )

        per_doc[doc_id] = {
            "discipline": discipline,
            "path": path,
            "dep_label_counts": dict(dep_counts),
            "svg_paths": svg_paths,
        }

        disc_agg[discipline].update(dep_counts)

    # Per-discipline
    per_discipline: Dict[str, dict] = {}
    for disc, counts in disc_agg.items():
        per_discipline[disc] = {
            "dep_label_counts": dict(counts),
            "top_labels": counts.most_common(20),
        }

    if save_examples:
        ex_dir = output_dir / "text_examples" / "per_document"
        _save_text_examples(text_examples, ex_dir / "dependency_examples.txt")

    logger.info("Dependency analysis complete: %d documents.", len(per_doc))
    return {"per_document": per_doc, "per_discipline": per_discipline}
