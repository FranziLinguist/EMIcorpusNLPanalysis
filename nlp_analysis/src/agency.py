"""
agency.py – Subject agency classification for main clause verbs.
"""

import logging
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict

logger = logging.getLogger(__name__)

# Words that suggest source attribution
SOURCE_WORDS = {
    "article", "paper", "book", "author", "study", "text",
    "report", "chapter", "document", "essay", "work", "thesis",
    "dissertation", "journal", "publication", "source", "reference",
}

# Words that suggest data / evidence subjects
DATA_WORDS = {
    "data", "results", "result", "experiment", "findings", "finding",
    "analysis", "evidence", "survey", "test", "observation",
    "measurement", "figure", "table", "graph", "statistics",
    "statistic", "sample", "dataset",
}

# Author-identity pronouns / phrases
AUTHOR_PRONOUNS = {"i", "we"}


def _classify_subject(token, doc) -> str:
    """Classify the agency type of a subject token."""
    text_lower = token.text.lower()
    lemma_lower = token.lemma_.lower()

    # Impersonal "it"
    if text_lower == "it":
        return "impersonal"

    # Author identity
    if lemma_lower in AUTHOR_PRONOUNS:
        return "author_identity"

    # Named entities (PERSON) → source_attribution
    if token.ent_type_ in ("PERSON", "ORG"):
        return "source_attribution"

    # Source attribution by lemma
    if lemma_lower in SOURCE_WORDS:
        return "source_attribution"

    # Data / evidence
    if lemma_lower in DATA_WORDS:
        return "data_evidence"

    # NOUN / PROPN that is neither of the above → concept_abstraction
    if token.pos_ in ("NOUN", "PROPN"):
        return "concept_abstraction"

    return "other"


def _save_text_examples(examples: list, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        for ex in examples:
            fh.write(ex + "\n\n")


def run_agency_analysis(corpus: list, config: dict, nlp) -> dict:
    """
    Classify subjects of main verbs into agency categories.

    Returns
    -------
    results : dict with per_document and per_discipline sub-dicts.
    """
    output_dir = Path(config["output_dir"])
    save_examples = config.get("save_text_examples", True)
    max_ex = config.get("text_example_max_per_task", 5)

    per_doc: Dict[str, dict] = {}
    disc_agg: Dict[str, dict] = defaultdict(Counter)

    category_examples: dict = defaultdict(list)

    CATEGORIES = [
        "author_identity", "source_attribution", "data_evidence",
        "concept_abstraction", "impersonal", "other",
    ]

    for doc in corpus:
        doc_id = doc["id"]
        discipline = doc["discipline"]
        path = doc["path"]
        text = doc["clean_text"]

        try:
            spacy_doc = nlp(text)
        except Exception as exc:
            logger.error("spaCy error in agency for '%s': %s", doc_id, exc)
            continue

        agency_counts: Counter = Counter()

        for token in spacy_doc:
            # Only look at ROOT verbs and main verbs
            if token.dep_ not in ("ROOT",) and token.pos_ not in ("VERB",):
                continue
            if token.pos_ not in ("VERB", "AUX"):
                continue

            # Find nsubj or nsubjpass
            subj = None
            for child in token.children:
                if child.dep_ in ("nsubj", "nsubjpass"):
                    subj = child
                    break

            if subj is None:
                continue

            category = _classify_subject(subj, spacy_doc)
            agency_counts[category] += 1

            if save_examples and len(category_examples[category]) < max_ex:
                category_examples[category].append(
                    f"[SOURCE] {path}\n"
                    f"[LABEL]  Agentività: {category} (soggetto: '{subj.text}')\n"
                    f"[TEXT]   {token.sent.text.strip()}"
                )

        total = sum(agency_counts.values())
        pct = {
            cat: round(agency_counts.get(cat, 0) / total * 100, 2) if total else 0.0
            for cat in CATEGORIES
        }

        per_doc[doc_id] = {
            "discipline": discipline,
            "path": path,
            "agency_counts": {cat: agency_counts.get(cat, 0) for cat in CATEGORIES},
            "agency_percentages": pct,
            "total_classified": total,
        }

        disc_agg[discipline].update(agency_counts)

    # Per-discipline
    per_discipline: Dict[str, dict] = {}
    for disc, counts in disc_agg.items():
        total = sum(counts.values())
        per_discipline[disc] = {
            "agency_counts": {cat: counts.get(cat, 0) for cat in CATEGORIES},
            "agency_percentages": {
                cat: round(counts.get(cat, 0) / total * 100, 2) if total else 0.0
                for cat in CATEGORIES
            },
            "total_classified": total,
        }

    # Save text examples
    if save_examples:
        ex_dir = output_dir / "text_examples" / "per_document"
        for cat, exs in category_examples.items():
            _save_text_examples(exs, ex_dir / f"agency_{cat}.txt")

    logger.info("Agency analysis complete: %d documents.", len(per_doc))
    return {"per_document": per_doc, "per_discipline": per_discipline}
