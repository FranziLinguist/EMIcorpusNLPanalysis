"""
verb_analysis.py – Modal verbs, passive voice, reporting verbs.
"""

import logging
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List

logger = logging.getLogger(__name__)

MODAL_VERBS = {"can", "could", "may", "might", "shall", "should",
               "will", "would", "must", "ought", "need"}

MODAL_CATEGORIES = {
    "ability":     {"can", "could"},
    "permission":  {"may", "can", "could"},
    "obligation":  {"must", "should", "ought", "need", "shall"},
    "possibility": {"may", "might", "could"},
    "volition":    {"will", "would", "shall"},
}

EPISTEMIC_STANCE = {
    "hedging":       {"may", "might", "could"},
    "strong_claim":  {"must"},
    "recommendation": {"should"},
    "ability":       {"can"},
}

REPORTING_VERB_TYPES = {
    "evidence":          {"shows", "demonstrates", "reveals", "finds", "indicates"},
    "caution":           {"suggests", "implies", "indicates"},
    "position":          {"argues", "contends", "maintains", "asserts", "proposes"},
    "critical_distance": {"claims"},
    "certainty":         {"demonstrates", "proves", "establishes"},
    "subjective":        {"believes", "thinks", "feels"},
    "neutral":           {"states", "explains", "notes", "observes", "describes"},
}


def _classify_reporting_verb(lemma: str) -> List[str]:
    lemma_lower = lemma.lower()
    types = []
    for rtype, verbs in REPORTING_VERB_TYPES.items():
        if lemma_lower in verbs:
            types.append(rtype)
    return types if types else ["other"]


def _is_passive(token) -> bool:
    """Return True if *token* is the main verb of a passive construction."""
    # Method 1: spaCy's nsubjpass / auxpass dependency labels
    for child in token.children:
        if child.dep_ in ("nsubjpass", "auxpass"):
            return True
    # Method 2: auxiliary "be" + past participle tag
    if token.tag_ == "VBN":
        for child in token.children:
            if child.lemma_.lower() == "be" and child.dep_ in ("aux", "auxpass"):
                return True
    return False


def _save_text_examples(examples: list, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        for ex in examples:
            fh.write(ex + "\n\n")


def run_verb_analysis(corpus: list, config: dict, nlp) -> dict:
    """
    Analyse modal verbs, passive constructions and reporting verbs.

    Returns
    -------
    results : dict with per_document and per_discipline sub-dicts.
    """
    output_dir = Path(config["output_dir"])
    save_examples = config.get("save_text_examples", True)
    max_ex = config.get("text_example_max_per_task", 5)
    reporting_verbs_cfg = {v.lower() for v in config.get("reporting_verbs", [])}

    per_doc: Dict[str, dict] = {}
    disc_agg: Dict[str, dict] = defaultdict(lambda: {
        "modal_counts": Counter(),
        "modal_category_counts": Counter(),
        "epistemic_counts": Counter(),
        "passive_count": 0,
        "active_count": 0,
        "reporting_verb_counts": Counter(),
        "reporting_type_counts": Counter(),
        "total_verbs": 0,
    })

    modal_examples: dict = defaultdict(list)
    passive_examples: list = []
    reporting_examples: dict = defaultdict(list)

    for doc in corpus:
        doc_id = doc["id"]
        discipline = doc["discipline"]
        path = doc["path"]
        text = doc["clean_text"]

        try:
            spacy_doc = nlp(text)
        except Exception as exc:
            logger.error("spaCy error in verb_analysis for '%s': %s", doc_id, exc)
            continue

        modal_counts: Counter = Counter()
        modal_category_counts: Counter = Counter()
        epistemic_counts: Counter = Counter()
        passive_count = 0
        active_count = 0
        reporting_verb_counts: Counter = Counter()
        reporting_type_counts: Counter = Counter()
        total_verbs = 0

        for token in spacy_doc:
            if token.pos_ not in ("VERB", "AUX"):
                continue
            total_verbs += 1

            lemma_lower = token.lemma_.lower()

            # Modal verbs
            if lemma_lower in MODAL_VERBS and token.pos_ == "AUX":
                modal_counts[lemma_lower] += 1
                for cat, members in MODAL_CATEGORIES.items():
                    if lemma_lower in members:
                        modal_category_counts[cat] += 1
                for stance, members in EPISTEMIC_STANCE.items():
                    if lemma_lower in members:
                        epistemic_counts[stance] += 1

                if save_examples and len(modal_examples[lemma_lower]) < max_ex:
                    sent = token.sent
                    modal_examples[lemma_lower].append(
                        f"[SOURCE] {path}\n"
                        f"[LABEL]  Modale: {lemma_lower}\n"
                        f"[TEXT]   {sent.text.strip()}"
                    )

            # Passive / active
            if token.pos_ == "VERB":
                if _is_passive(token):
                    passive_count += 1
                    if save_examples and len(passive_examples) < max_ex:
                        passive_examples.append(
                            f"[SOURCE] {path}\n"
                            f"[LABEL]  Passivo\n"
                            f"[TEXT]   {token.sent.text.strip()}"
                        )
                else:
                    active_count += 1

                # Reporting verbs
                if lemma_lower in reporting_verbs_cfg:
                    reporting_verb_counts[lemma_lower] += 1
                    rtypes = _classify_reporting_verb(lemma_lower)
                    for rt in rtypes:
                        reporting_type_counts[rt] += 1
                    if save_examples:
                        for rt in rtypes:
                            if len(reporting_examples[rt]) < max_ex:
                                reporting_examples[rt].append(
                                    f"[SOURCE] {path}\n"
                                    f"[LABEL]  Verbo di riporto ({rt}): {lemma_lower}\n"
                                    f"[TEXT]   {token.sent.text.strip()}"
                                )

        per_doc[doc_id] = {
            "discipline": discipline,
            "path": path,
            "total_verbs": total_verbs,
            "modal_counts": dict(modal_counts),
            "modal_category_counts": dict(modal_category_counts),
            "epistemic_counts": dict(epistemic_counts),
            "passive_count": passive_count,
            "active_count": active_count,
            "passive_ratio": round(passive_count / (passive_count + active_count), 4)
                             if (passive_count + active_count) else 0.0,
            "reporting_verb_counts": dict(reporting_verb_counts),
            "reporting_type_counts": dict(reporting_type_counts),
        }

        # Aggregate
        agg = disc_agg[discipline]
        agg["modal_counts"].update(modal_counts)
        agg["modal_category_counts"].update(modal_category_counts)
        agg["epistemic_counts"].update(epistemic_counts)
        agg["passive_count"] += passive_count
        agg["active_count"] += active_count
        agg["reporting_verb_counts"].update(reporting_verb_counts)
        agg["reporting_type_counts"].update(reporting_type_counts)
        agg["total_verbs"] += total_verbs

    # Per-discipline
    per_discipline: Dict[str, dict] = {}
    for disc, agg in disc_agg.items():
        p = agg["passive_count"]
        a = agg["active_count"]
        per_discipline[disc] = {
            "total_verbs": agg["total_verbs"],
            "modal_counts": dict(agg["modal_counts"]),
            "modal_category_counts": dict(agg["modal_category_counts"]),
            "epistemic_counts": dict(agg["epistemic_counts"]),
            "passive_count": p,
            "active_count": a,
            "passive_ratio": round(p / (p + a), 4) if (p + a) else 0.0,
            "reporting_verb_counts": dict(agg["reporting_verb_counts"]),
            "reporting_type_counts": dict(agg["reporting_type_counts"]),
        }

    # Save text examples
    if save_examples:
        ex_dir = output_dir / "text_examples" / "per_document"
        for modal, exs in modal_examples.items():
            _save_text_examples(exs, ex_dir / f"verb_modal_{modal}.txt")
        _save_text_examples(passive_examples, ex_dir / "verb_passive.txt")
        for rtype, exs in reporting_examples.items():
            _save_text_examples(exs, ex_dir / f"verb_reporting_{rtype}.txt")

    logger.info("Verb analysis complete: %d documents.", len(per_doc))
    return {"per_document": per_doc, "per_discipline": per_discipline}
