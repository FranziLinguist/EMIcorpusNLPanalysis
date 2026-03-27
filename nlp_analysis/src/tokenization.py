"""
tokenization.py – Sentence / token statistics, subordination, parse-tree depth.
"""

import logging
from collections import defaultdict
from pathlib import Path
from typing import Dict, List

logger = logging.getLogger(__name__)

# spaCy dependency labels that indicate subordinate clauses
SUBORD_DEPS = {"advcl", "acl", "relcl", "ccomp", "xcomp"}


def get_tree_depth(token) -> int:
    """Return the depth of the subtree rooted at *token* (root = 1)."""
    children = list(token.children)
    if not children:
        return 1
    return 1 + max(get_tree_depth(child) for child in children)


def _save_text_examples(examples: list, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        for ex in examples:
            fh.write(ex + "\n\n")


def run_tokenization(corpus: list, config: dict, nlp) -> dict:
    """
    Compute per-document and per-discipline tokenisation statistics.

    Returns
    -------
    results : dict
        {
          "per_document": { doc_id: {...} },
          "per_discipline": { discipline: {...} },
        }
    """
    output_dir = Path(config["output_dir"])
    save_examples = config.get("save_text_examples", True)
    max_ex = config.get("text_example_max_per_task", 5)

    per_doc: Dict[str, dict] = {}
    # Aggregate data per discipline
    disc_agg: Dict[str, dict] = defaultdict(lambda: {
        "sentence_lengths": [],
        "subordinate_counts": [],
        "tree_depths": [],
        "sentence_count": 0,
        "token_count": 0,
    })

    # Text examples
    longest_sentences: list = []
    shortest_sentences: list = []
    most_complex: list = []
    least_complex: list = []

    for doc in corpus:
        doc_id = doc["id"]
        discipline = doc["discipline"]
        path = doc["path"]
        text = doc["clean_text"]

        try:
            spacy_doc = nlp(text)
        except Exception as exc:
            logger.error("spaCy parse error for '%s': %s – skipping.", doc_id, exc)
            continue

        sentences = list(spacy_doc.sents)
        sentence_lengths = []
        subord_per_sent = []
        depth_per_sent = []

        for sent in sentences:
            tokens = [t for t in sent if not t.is_punct and not t.is_space]
            length = len(tokens)
            sentence_lengths.append(length)

            # Subordinate clause count
            sub_count = sum(1 for t in sent if t.dep_ in SUBORD_DEPS)
            subord_per_sent.append(sub_count)

            # Parse tree depth from ROOT
            root_tokens = [t for t in sent if t.dep_ == "ROOT"]
            if root_tokens:
                depth = get_tree_depth(root_tokens[0])
            else:
                depth = max((get_tree_depth(t) for t in sent), default=1)
            depth_per_sent.append(depth)

        n_sents = len(sentences)
        n_tokens = sum(
            1 for t in spacy_doc if not t.is_punct and not t.is_space
        )
        avg_sent_len = (sum(sentence_lengths) / n_sents) if n_sents else 0.0
        avg_sub = (sum(subord_per_sent) / n_sents) if n_sents else 0.0
        avg_depth = (sum(depth_per_sent) / n_sents) if n_sents else 0.0

        per_doc[doc_id] = {
            "discipline": discipline,
            "path": path,
            "sentence_count": n_sents,
            "token_count": n_tokens,
            "avg_sentence_length": round(avg_sent_len, 2),
            "sentence_length_distribution": sentence_lengths,
            "avg_subordinate_clauses": round(avg_sub, 2),
            "avg_parse_tree_depth": round(avg_depth, 2),
            "subordinate_clause_counts": subord_per_sent,
            "parse_tree_depths": depth_per_sent,
        }

        # Aggregate for discipline
        agg = disc_agg[discipline]
        agg["sentence_lengths"].extend(sentence_lengths)
        agg["subordinate_counts"].extend(subord_per_sent)
        agg["tree_depths"].extend(depth_per_sent)
        agg["sentence_count"] += n_sents
        agg["token_count"] += n_tokens

        # Collect text examples
        if save_examples and sentences:
            sent_by_length = sorted(
                sentences, key=lambda s: len([t for t in s if not t.is_punct and not t.is_space])
            )
            sent_by_complexity = sorted(
                zip(sentences, subord_per_sent, depth_per_sent),
                key=lambda x: x[1] + x[2]
            )

            def _fmt(sent_obj, label):
                return (
                    f"[SOURCE] {path}\n"
                    f"[LABEL]  {label}\n"
                    f"[TEXT]   {sent_obj.text.strip()}"
                )

            if sent_by_length:
                longest_sentences.append(_fmt(sent_by_length[-1], "Frase più lunga"))
                shortest_sentences.append(_fmt(sent_by_length[0], "Frase più corta"))
            if sent_by_complexity:
                most_complex.append(_fmt(sent_by_complexity[-1][0], "Frase più complessa"))
                least_complex.append(_fmt(sent_by_complexity[0][0], "Frase meno complessa"))

    # Per-discipline aggregates
    per_discipline: Dict[str, dict] = {}
    for disc, agg in disc_agg.items():
        sl = agg["sentence_lengths"]
        sc = agg["subordinate_counts"]
        td = agg["tree_depths"]
        n_s = agg["sentence_count"]
        per_discipline[disc] = {
            "sentence_count": n_s,
            "token_count": agg["token_count"],
            "avg_sentence_length": round(sum(sl) / len(sl), 2) if sl else 0.0,
            "avg_subordinate_clauses": round(sum(sc) / len(sc), 2) if sc else 0.0,
            "avg_parse_tree_depth": round(sum(td) / len(td), 2) if td else 0.0,
            "sentence_length_distribution": sl,
        }

    # Save text examples
    if save_examples:
        ex_dir = output_dir / "text_examples" / "per_document"
        _save_text_examples(longest_sentences[:max_ex],  ex_dir / "tokenization_longest_sentences.txt")
        _save_text_examples(shortest_sentences[:max_ex], ex_dir / "tokenization_shortest_sentences.txt")
        _save_text_examples(most_complex[:max_ex],       ex_dir / "tokenization_most_complex.txt")
        _save_text_examples(least_complex[:max_ex],      ex_dir / "tokenization_least_complex.txt")

    logger.info("Tokenisation complete: %d documents processed.", len(per_doc))
    return {"per_document": per_doc, "per_discipline": dict(per_discipline)}
