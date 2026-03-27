"""
visualization.py – Generate all charts, heatmaps, word clouds and dependency SVGs.

All figures: Italian titles/labels, seaborn "muted" palette, ≤150 DPI, tight_layout.
"""

import logging
import warnings
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional

import matplotlib
matplotlib.use("Agg")  # non-interactive backend
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns

warnings.filterwarnings("ignore")
logger = logging.getLogger(__name__)

# ── Helpers ─────────────────────────────────────────────────────────────────

def _setup():
    sns.set_theme(style="whitegrid", palette="muted")
    plt.rcParams.update({
        "figure.autolayout": True,
        "axes.titlesize": 12,
        "axes.labelsize": 10,
        "xtick.labelsize": 8,
        "ytick.labelsize": 8,
    })


def _save(fig, path: Path, dpi: int = 150):
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    logger.debug("Saved figure: %s", path)


def _short(discipline: str, max_len: int = 12) -> str:
    """Shorten long discipline codes/names for axis labels."""
    return discipline if len(discipline) <= max_len else discipline[:max_len] + "…"


# ── 1. Sentence length distribution histogram ───────────────────────────────

def plot_sentence_length_histogram(tok_results: dict, output_dir: Path, dpi: int):
    """One histogram per discipline + one corpus-wide."""
    per_disc = tok_results.get("per_discipline", {})
    img_dir = output_dir / "images" / "per_discipline"

    for disc, data in per_disc.items():
        lengths = data.get("sentence_length_distribution", [])
        if not lengths:
            continue
        fig, ax = plt.subplots(figsize=(7, 4))
        ax.hist(lengths, bins=30, color=sns.color_palette("muted")[0], edgecolor="white")
        ax.set_title(f"Distribuzione lunghezza frasi – {disc}")
        ax.set_xlabel("Numero di token per frase")
        ax.set_ylabel("Frequenza")
        _save(fig, img_dir / f"sentence_length_hist_{disc}.png", dpi)

    # Corpus-wide
    all_lengths = []
    for data in per_disc.values():
        all_lengths.extend(data.get("sentence_length_distribution", []))
    if all_lengths:
        fig, ax = plt.subplots(figsize=(7, 4))
        ax.hist(all_lengths, bins=40, color=sns.color_palette("muted")[1], edgecolor="white")
        ax.set_title("Distribuzione lunghezza frasi – Corpus")
        ax.set_xlabel("Numero di token per frase")
        ax.set_ylabel("Frequenza")
        _save(fig, output_dir / "images" / "corpus" / "sentence_length_hist_corpus.png", dpi)


# ── 2. Subordinate clause count histogram ───────────────────────────────────

def plot_subordinate_histogram(tok_results: dict, output_dir: Path, dpi: int):
    per_disc = tok_results.get("per_discipline", {})
    img_dir = output_dir / "images" / "per_discipline"
    for disc, data in per_disc.items():
        # Rebuild per-sentence subordinate counts from per_document
        pass  # aggregated data only has averages; use per_document
    per_doc = tok_results.get("per_document", {})
    disc_sub: Dict[str, list] = defaultdict(list)
    disc_depth: Dict[str, list] = defaultdict(list)
    for doc_data in per_doc.values():
        disc = doc_data["discipline"]
        disc_sub[disc].extend(doc_data.get("subordinate_clause_counts", []))
        disc_depth[disc].extend(doc_data.get("parse_tree_depths", []))

    for disc, counts in disc_sub.items():
        if not counts:
            continue
        fig, ax = plt.subplots(figsize=(7, 4))
        ax.hist(counts, bins=max(10, max(counts)+1), color=sns.color_palette("muted")[2], edgecolor="white")
        ax.set_title(f"Clausole subordinate per frase – {disc}")
        ax.set_xlabel("Numero di subordinate")
        ax.set_ylabel("Frequenza")
        _save(fig, img_dir / f"subordinate_hist_{disc}.png", dpi)

    for disc, depths in disc_depth.items():
        if not depths:
            continue
        fig, ax = plt.subplots(figsize=(7, 4))
        ax.hist(depths, bins=max(10, max(depths)+1), color=sns.color_palette("muted")[3], edgecolor="white")
        ax.set_title(f"Profondità albero sintattico – {disc}")
        ax.set_xlabel("Profondità")
        ax.set_ylabel("Frequenza")
        _save(fig, img_dir / f"tree_depth_hist_{disc}.png", dpi)


# ── 3. POS distribution bar chart ───────────────────────────────────────────

def plot_pos_distribution(morph_results: dict, output_dir: Path, dpi: int):
    per_disc = morph_results.get("per_discipline", {})
    img_dir = output_dir / "images" / "per_discipline"
    for disc, data in per_disc.items():
        pos_counts = data.get("pos_counts", {})
        if not pos_counts:
            continue
        labels = list(pos_counts.keys())
        values = list(pos_counts.values())
        fig, ax = plt.subplots(figsize=(9, 4))
        colors = sns.color_palette("muted", len(labels))
        ax.bar(labels, values, color=colors)
        ax.set_title(f"Distribuzione POS – {disc}")
        ax.set_xlabel("Categoria grammaticale")
        ax.set_ylabel("Conteggio")
        plt.xticks(rotation=45, ha="right")
        _save(fig, img_dir / f"pos_distribution_{disc}.png", dpi)

    # Corpus-wide aggregate
    corpus_pos: Dict[str, int] = defaultdict(int)
    for data in per_disc.values():
        for pos, cnt in data.get("pos_counts", {}).items():
            corpus_pos[pos] += cnt
    if corpus_pos:
        labels = list(corpus_pos.keys())
        values = list(corpus_pos.values())
        fig, ax = plt.subplots(figsize=(9, 4))
        colors = sns.color_palette("muted", len(labels))
        ax.bar(labels, values, color=colors)
        ax.set_title("Distribuzione POS – Corpus")
        ax.set_xlabel("Categoria grammaticale")
        ax.set_ylabel("Conteggio")
        plt.xticks(rotation=45, ha="right")
        _save(fig, output_dir / "images" / "corpus" / "pos_distribution_corpus.png", dpi)


# ── 4. Modal verb heatmap (discipline × modal) ──────────────────────────────

def plot_modal_heatmap(verb_results: dict, output_dir: Path, dpi: int):
    per_disc = verb_results.get("per_discipline", {})
    if not per_disc:
        return
    disciplines = sorted(per_disc.keys())
    all_modals = sorted({m for d in per_disc.values() for m in d.get("modal_counts", {})})
    if not all_modals:
        return
    matrix = np.array([
        [per_disc[d]["modal_counts"].get(m, 0) for m in all_modals]
        for d in disciplines
    ], dtype=float)
    fig, ax = plt.subplots(figsize=(max(8, len(all_modals)), max(5, len(disciplines) * 0.6)))
    sns.heatmap(
        matrix, xticklabels=all_modals, yticklabels=[_short(d) for d in disciplines],
        annot=True, fmt=".0f", cmap="Blues", ax=ax, linewidths=0.5
    )
    ax.set_title("Heatmap verbi modali per disciplina")
    ax.set_xlabel("Verbo modale")
    ax.set_ylabel("Disciplina")
    _save(fig, output_dir / "images" / "per_discipline" / "modal_heatmap.png", dpi)


# ── 5. Hedging index bar chart ──────────────────────────────────────────────

def plot_hedging_index(verb_results: dict, output_dir: Path, dpi: int):
    per_disc = verb_results.get("per_discipline", {})
    if not per_disc:
        return
    disciplines = sorted(per_disc.keys())
    hedging_indices = []
    for d in disciplines:
        ep = per_disc[d].get("epistemic_counts", {})
        total_modals = sum(per_disc[d].get("modal_counts", {}).values())
        hedging = ep.get("hedging", 0)
        hedging_indices.append(hedging / total_modals if total_modals else 0.0)

    fig, ax = plt.subplots(figsize=(max(7, len(disciplines) * 0.8), 4))
    colors = sns.color_palette("muted", len(disciplines))
    ax.bar([_short(d) for d in disciplines], hedging_indices, color=colors)
    ax.set_title("Indice di hedging per disciplina")
    ax.set_xlabel("Disciplina")
    ax.set_ylabel("Proporzione modali hedging")
    plt.xticks(rotation=45, ha="right")
    _save(fig, output_dir / "images" / "per_discipline" / "hedging_index.png", dpi)


# ── 6. Active vs passive stacked bar ────────────────────────────────────────

def plot_active_passive(verb_results: dict, output_dir: Path, dpi: int):
    per_disc = verb_results.get("per_discipline", {})
    if not per_disc:
        return
    disciplines = sorted(per_disc.keys())
    actives = [per_disc[d].get("active_count", 0) for d in disciplines]
    passives = [per_disc[d].get("passive_count", 0) for d in disciplines]
    x = np.arange(len(disciplines))
    width = 0.6
    fig, ax = plt.subplots(figsize=(max(7, len(disciplines) * 0.8), 4))
    palette = sns.color_palette("muted")
    ax.bar(x, actives, width, label="Attivo", color=palette[0])
    ax.bar(x, passives, width, bottom=actives, label="Passivo", color=palette[3])
    ax.set_xticks(x)
    ax.set_xticklabels([_short(d) for d in disciplines], rotation=45, ha="right")
    ax.set_title("Voce attiva vs passiva per disciplina")
    ax.set_xlabel("Disciplina")
    ax.set_ylabel("Conteggio verbi")
    ax.legend()
    _save(fig, output_dir / "images" / "per_discipline" / "active_passive_stacked.png", dpi)


# ── 7. Reporting verbs distribution ─────────────────────────────────────────

def plot_reporting_verbs(verb_results: dict, output_dir: Path, dpi: int):
    per_disc = verb_results.get("per_discipline", {})
    if not per_disc:
        return
    img_dir = output_dir / "images" / "per_discipline"

    for disc, data in per_disc.items():
        rv_counts = data.get("reporting_verb_counts", {})
        if not rv_counts:
            continue
        verbs = sorted(rv_counts, key=rv_counts.get, reverse=True)[:15]
        counts = [rv_counts[v] for v in verbs]
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.barh(verbs[::-1], counts[::-1], color=sns.color_palette("muted")[2])
        ax.set_title(f"Verbi di citazione – {disc}")
        ax.set_xlabel("Frequenza")
        _save(fig, img_dir / f"reporting_verbs_{disc}.png", dpi)

    # Epistemic type breakdown per discipline
    disciplines = sorted(per_disc.keys())
    all_types = ["evidence", "caution", "position", "critical_distance", "certainty", "subjective", "neutral"]
    matrix = np.array([
        [per_disc[d].get("reporting_type_counts", {}).get(t, 0) for t in all_types]
        for d in disciplines
    ], dtype=float)
    if matrix.sum() > 0:
        fig, ax = plt.subplots(figsize=(10, max(4, len(disciplines) * 0.6)))
        sns.heatmap(
            matrix, xticklabels=all_types, yticklabels=[_short(d) for d in disciplines],
            annot=True, fmt=".0f", cmap="YlOrRd", ax=ax, linewidths=0.5
        )
        ax.set_title("Verbi di citazione per tipo epistemico")
        ax.set_xlabel("Tipo epistemico")
        ax.set_ylabel("Disciplina")
        plt.xticks(rotation=30, ha="right")
        _save(fig, img_dir / "reporting_epistemic_heatmap.png", dpi)

    # Diversity index
    diversity_indices = []
    for d in disciplines:
        rv = per_disc[d].get("reporting_verb_counts", {})
        total = sum(rv.values())
        unique = len(rv)
        diversity_indices.append(unique / total if total else 0.0)
    fig, ax = plt.subplots(figsize=(max(7, len(disciplines) * 0.8), 4))
    colors = sns.color_palette("muted", len(disciplines))
    ax.bar([_short(d) for d in disciplines], diversity_indices, color=colors)
    ax.set_title("Indice di diversità verbi di citazione")
    ax.set_xlabel("Disciplina")
    ax.set_ylabel("Indice di diversità")
    plt.xticks(rotation=45, ha="right")
    _save(fig, img_dir / "reporting_diversity_index.png", dpi)


# ── 8. Agency category distribution ─────────────────────────────────────────

def plot_agency(agency_results: dict, output_dir: Path, dpi: int):
    per_disc = agency_results.get("per_discipline", {})
    if not per_disc:
        return
    disciplines = sorted(per_disc.keys())
    categories = ["author_identity", "source_attribution", "data_evidence",
                  "concept_abstraction", "impersonal", "other"]
    x = np.arange(len(disciplines))
    width = 0.12
    palette = sns.color_palette("muted", len(categories))
    fig, ax = plt.subplots(figsize=(max(10, len(disciplines) * 0.9), 5))
    for i, cat in enumerate(categories):
        values = [per_disc[d].get("agency_counts", {}).get(cat, 0) for d in disciplines]
        ax.bar(x + i * width, values, width, label=cat.replace("_", " "), color=palette[i])
    ax.set_xticks(x + width * (len(categories) - 1) / 2)
    ax.set_xticklabels([_short(d) for d in disciplines], rotation=45, ha="right")
    ax.set_title("Distribuzione agency per disciplina")
    ax.set_xlabel("Disciplina")
    ax.set_ylabel("Conteggio soggetti")
    ax.legend(loc="upper right", fontsize=7)
    _save(fig, output_dir / "images" / "per_discipline" / "agency_distribution.png", dpi)


# ── 9. Nominalization density bar chart ─────────────────────────────────────

def plot_nominalization(nom_results: dict, output_dir: Path, dpi: int):
    per_disc = nom_results.get("per_discipline", {})
    if not per_disc:
        return
    disciplines = sorted(per_disc.keys())
    densities = [per_disc[d].get("density_per_100_tokens", 0) for d in disciplines]
    fig, ax = plt.subplots(figsize=(max(7, len(disciplines) * 0.8), 4))
    colors = sns.color_palette("muted", len(disciplines))
    ax.bar([_short(d) for d in disciplines], densities, color=colors)
    ax.set_title("Densità nominalizzazioni per disciplina (per 100 token)")
    ax.set_xlabel("Disciplina")
    ax.set_ylabel("Nominalizzazioni / 100 token")
    plt.xticks(rotation=45, ha="right")
    _save(fig, output_dir / "images" / "per_discipline" / "nominalization_density.png", dpi)


# ── 10. Discourse markers distribution ──────────────────────────────────────

def plot_discourse_markers(cohesion_results: dict, output_dir: Path, dpi: int):
    per_disc = cohesion_results.get("per_discipline", {})
    if not per_disc:
        return
    disciplines = sorted(per_disc.keys())
    categories = ["additive", "adversative", "causal", "sequential", "conclusive"]
    x = np.arange(len(disciplines))
    width = 0.15
    palette = sns.color_palette("muted", len(categories))
    fig, ax = plt.subplots(figsize=(max(10, len(disciplines) * 0.9), 5))
    for i, cat in enumerate(categories):
        values = [per_disc[d].get("category_counts", {}).get(cat, 0) for d in disciplines]
        ax.bar(x + i * width, values, width, label=cat, color=palette[i])
    ax.set_xticks(x + width * (len(categories) - 1) / 2)
    ax.set_xticklabels([_short(d) for d in disciplines], rotation=45, ha="right")
    ax.set_title("Distribuzione connettivi discorsivi per disciplina")
    ax.set_xlabel("Disciplina")
    ax.set_ylabel("Frequenza")
    ax.legend()
    _save(fig, output_dir / "images" / "per_discipline" / "discourse_markers_distribution.png", dpi)

    # Diversity index
    diversity = [per_disc[d].get("diversity_index", 0) for d in disciplines]
    fig, ax = plt.subplots(figsize=(max(7, len(disciplines) * 0.8), 4))
    colors = sns.color_palette("muted", len(disciplines))
    ax.bar([_short(d) for d in disciplines], diversity, color=colors)
    ax.set_title("Indice di diversità connettivi discorsivi")
    ax.set_xlabel("Disciplina")
    ax.set_ylabel("Indice di diversità")
    plt.xticks(rotation=45, ha="right")
    _save(fig, output_dir / "images" / "per_discipline" / "discourse_diversity_index.png", dpi)


# ── 11. Academic formulas frequency bar chart ───────────────────────────────

def plot_academic_formulas(formula_results: dict, output_dir: Path, dpi: int):
    per_disc = formula_results.get("per_discipline", {})
    if not per_disc:
        return
    disciplines = sorted(per_disc.keys())
    densities = [per_disc[d].get("density_per_1000_tokens", 0) for d in disciplines]
    fig, ax = plt.subplots(figsize=(max(7, len(disciplines) * 0.8), 4))
    colors = sns.color_palette("muted", len(disciplines))
    ax.bar([_short(d) for d in disciplines], densities, color=colors)
    ax.set_title("Densità formule accademiche (per 1000 token)")
    ax.set_xlabel("Disciplina")
    ax.set_ylabel("Formule / 1000 token")
    plt.xticks(rotation=45, ha="right")
    _save(fig, output_dir / "images" / "per_discipline" / "academic_formulas_density.png", dpi)

    # Top formulas corpus-wide
    corpus_counts: Dict[str, int] = defaultdict(int)
    for data in per_disc.values():
        for formula, cnt in data.get("formula_counts", {}).items():
            corpus_counts[formula] += cnt
    if corpus_counts:
        top_formulas = sorted(corpus_counts, key=corpus_counts.get, reverse=True)[:15]
        counts = [corpus_counts[f] for f in top_formulas]
        fig, ax = plt.subplots(figsize=(8, 5))
        ax.barh(top_formulas[::-1], counts[::-1], color=sns.color_palette("muted")[4])
        ax.set_title("Top formule accademiche – Corpus")
        ax.set_xlabel("Frequenza")
        _save(fig, output_dir / "images" / "corpus" / "academic_formulas_top.png", dpi)


# ── 12. Word frequency bar chart ────────────────────────────────────────────

def plot_word_frequency(freq_results: dict, output_dir: Path, dpi: int, top_n: int = 30):
    per_disc = freq_results.get("per_discipline", {})
    img_dir = output_dir / "images" / "per_discipline"
    for disc, data in per_disc.items():
        top_words = data.get("top_words", [])[:top_n]
        if not top_words:
            continue
        words, counts = zip(*top_words)
        fig, ax = plt.subplots(figsize=(8, 5))
        ax.barh(list(words)[::-1], list(counts)[::-1], color=sns.color_palette("muted")[0])
        ax.set_title(f"Parole più frequenti – {disc}")
        ax.set_xlabel("Frequenza")
        _save(fig, img_dir / f"word_frequency_{disc}.png", dpi)

    corpus = freq_results.get("corpus", {})
    top_words = corpus.get("top_words", [])[:top_n]
    if top_words:
        words, counts = zip(*top_words)
        fig, ax = plt.subplots(figsize=(8, 6))
        ax.barh(list(words)[::-1], list(counts)[::-1], color=sns.color_palette("muted")[1])
        ax.set_title("Parole più frequenti – Corpus")
        ax.set_xlabel("Frequenza")
        _save(fig, output_dir / "images" / "corpus" / "word_frequency_corpus.png", dpi)

    # Bigrams and trigrams corpus-wide
    top_bigrams = corpus.get("top_bigrams", [])[:top_n]
    if top_bigrams:
        ngrams, counts = zip(*top_bigrams)
        fig, ax = plt.subplots(figsize=(9, 6))
        ax.barh(list(ngrams)[::-1], list(counts)[::-1], color=sns.color_palette("muted")[2])
        ax.set_title("Bigrammi più frequenti – Corpus")
        ax.set_xlabel("Frequenza")
        _save(fig, output_dir / "images" / "corpus" / "bigrams_frequency_corpus.png", dpi)

    top_trigrams = corpus.get("top_trigrams", [])[:top_n]
    if top_trigrams:
        ngrams, counts = zip(*top_trigrams)
        fig, ax = plt.subplots(figsize=(9, 6))
        ax.barh(list(ngrams)[::-1], list(counts)[::-1], color=sns.color_palette("muted")[3])
        ax.set_title("Trigrammi più frequenti – Corpus")
        ax.set_xlabel("Frequenza")
        _save(fig, output_dir / "images" / "corpus" / "trigrams_frequency_corpus.png", dpi)


# ── 13. TF-IDF keyword bar chart ────────────────────────────────────────────

def plot_keywords(kw_results: dict, output_dir: Path, dpi: int, top_n: int = 20):
    per_disc = kw_results.get("per_discipline", {})
    img_dir = output_dir / "images" / "per_discipline"
    for disc, data in per_disc.items():
        kws = data.get("keywords", [])[:top_n]
        if not kws:
            continue
        words = [kw["keyword"] for kw in kws]
        scores = [kw["score"] for kw in kws]
        fig, ax = plt.subplots(figsize=(8, 5))
        ax.barh(words[::-1], scores[::-1], color=sns.color_palette("muted")[4])
        ax.set_title(f"Parole chiave TF-IDF – {disc}")
        ax.set_xlabel("Score TF-IDF")
        _save(fig, img_dir / f"tfidf_keywords_{disc}.png", dpi)

    corpus_kws = kw_results.get("corpus", [])[:top_n]
    if corpus_kws:
        words = [kw["keyword"] for kw in corpus_kws]
        scores = [kw["score"] for kw in corpus_kws]
        fig, ax = plt.subplots(figsize=(8, 6))
        ax.barh(words[::-1], scores[::-1], color=sns.color_palette("muted")[5 % 6])
        ax.set_title("Parole chiave TF-IDF – Corpus")
        ax.set_xlabel("Score TF-IDF")
        _save(fig, output_dir / "images" / "corpus" / "tfidf_keywords_corpus.png", dpi)


# ── 14. Word clouds ──────────────────────────────────────────────────────────

def plot_word_clouds(freq_results: dict, output_dir: Path, dpi: int, max_words: int = 150):
    try:
        from wordcloud import WordCloud
    except ImportError:
        logger.warning("wordcloud not installed – skipping word clouds.")
        return

    per_disc = freq_results.get("per_discipline", {})
    img_dir = output_dir / "images" / "per_discipline"
    for disc, data in per_disc.items():
        top_words = dict(data.get("top_words", []))
        if not top_words:
            continue
        wc = WordCloud(
            width=800, height=400, background_color="white",
            max_words=max_words, colormap="Set2"
        ).generate_from_frequencies(top_words)
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.imshow(wc, interpolation="bilinear")
        ax.axis("off")
        ax.set_title(f"Word Cloud – {disc}")
        _save(fig, img_dir / f"wordcloud_{disc}.png", dpi)

    # Corpus-wide
    corpus_words = dict(freq_results.get("corpus", {}).get("top_words", []))
    if corpus_words:
        wc = WordCloud(
            width=1000, height=500, background_color="white",
            max_words=max_words, colormap="tab20"
        ).generate_from_frequencies(corpus_words)
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.imshow(wc, interpolation="bilinear")
        ax.axis("off")
        ax.set_title("Word Cloud – Corpus")
        _save(fig, output_dir / "images" / "corpus" / "wordcloud_corpus.png", dpi)


# ── 15. LDA topic-words chart ────────────────────────────────────────────────

def plot_lda_topics(topic_results: dict, output_dir: Path, dpi: int):
    topics = topic_results.get("topics", [])
    if not topics:
        return
    n_topics = len(topics)
    fig, axes = plt.subplots(
        nrows=(n_topics + 1) // 2, ncols=2,
        figsize=(12, max(4, n_topics * 1.5))
    )
    axes_flat = axes.flatten() if hasattr(axes, "flatten") else [axes]
    palette = sns.color_palette("muted", 10)
    for i, tdata in enumerate(topics):
        tid = tdata["topic_id"]
        if i >= len(axes_flat):
            break
        ax = axes_flat[i]
        top_words = tdata.get("top_words", [])[:10]
        if not top_words:
            ax.axis("off")
            continue
        words = [w for w, _ in top_words]
        probs = [p for _, p in top_words]
        ax.barh(words[::-1], probs[::-1], color=palette[i % len(palette)])
        ax.set_title(f"Topic {tid}")
        ax.set_xlabel("Peso")
    for j in range(i + 1, len(axes_flat)):
        axes_flat[j].axis("off")
    fig.suptitle("Topic LDA – Parole chiave per topic", fontsize=13)
    plt.tight_layout()
    _save(fig, output_dir / "images" / "corpus" / "lda_topics.png", dpi)


# ── 16. Document-topic heatmap ───────────────────────────────────────────────

def plot_doc_topic_heatmap(topic_results: dict, output_dir: Path, dpi: int):
    per_doc = topic_results.get("per_document", {})
    if not per_doc:
        return
    topics_obj = topic_results.get("topics", {})
    n_topics = len(topics_obj)
    if n_topics == 0:
        return

    doc_ids = sorted(per_doc.keys())[:50]  # cap at 50 for readability
    matrix = np.zeros((len(doc_ids), n_topics))
    for i, doc_id in enumerate(doc_ids):
        dist = per_doc[doc_id].get("topic_distribution", [])
        for entry in dist:
            tid = entry["topic_id"]
            prob = entry["probability"]
            if 0 <= tid < n_topics:
                matrix[i][tid] = prob

    fig, ax = plt.subplots(figsize=(max(8, n_topics), max(6, len(doc_ids) * 0.3)))
    sns.heatmap(
        matrix, xticklabels=[f"T{i}" for i in range(n_topics)],
        yticklabels=doc_ids, cmap="YlGnBu", ax=ax, linewidths=0.0
    )
    ax.set_title("Distribuzione topic per documento (LDA)")
    ax.set_xlabel("Topic")
    ax.set_ylabel("Documento")
    _save(fig, output_dir / "images" / "corpus" / "doc_topic_heatmap.png", dpi)


# ── 17. Dependency label distribution ───────────────────────────────────────

def plot_dependency_labels(dep_results: dict, output_dir: Path, dpi: int):
    per_disc = dep_results.get("per_discipline", {})
    img_dir = output_dir / "images" / "per_discipline"
    for disc, data in per_disc.items():
        top_labels = data.get("top_labels", [])[:15]
        if not top_labels:
            continue
        labels = [lbl for lbl, _ in top_labels]
        counts = [cnt for _, cnt in top_labels]
        fig, ax = plt.subplots(figsize=(8, 5))
        ax.barh(labels[::-1], counts[::-1], color=sns.color_palette("muted")[1])
        ax.set_title(f"Etichette dipendenza più frequenti – {disc}")
        ax.set_xlabel("Frequenza")
        _save(fig, img_dir / f"dep_labels_{disc}.png", dpi)


# ── 18. Similarity heatmaps ──────────────────────────────────────────────────

def _plot_similarity_heatmap(matrix: list, disciplines: list, title: str, path: Path, dpi: int):
    if not matrix or not disciplines:
        return
    arr = np.array(matrix)
    short_discs = [_short(d) for d in disciplines]
    fig, ax = plt.subplots(figsize=(max(6, len(disciplines) * 0.7), max(5, len(disciplines) * 0.6)))
    sns.heatmap(
        arr, xticklabels=short_discs, yticklabels=short_discs,
        annot=True, fmt=".2f", cmap="coolwarm", ax=ax,
        vmin=0, vmax=1, linewidths=0.5
    )
    ax.set_title(title)
    plt.xticks(rotation=45, ha="right")
    plt.yticks(rotation=0)
    _save(fig, path, dpi)


def plot_similarity(sim_results: dict, output_dir: Path, dpi: int):
    if not sim_results:
        return
    disciplines = sim_results.get("disciplines", [])
    img_dir = output_dir / "images" / "corpus"

    _plot_similarity_heatmap(
        sim_results.get("cosine_similarity", []), disciplines,
        "Similarità coseno TF-IDF tra discipline",
        img_dir / "similarity_cosine_heatmap.png", dpi
    )

    jaccard_char = sim_results.get("jaccard_char", {})
    if jaccard_char.get("matrix"):
        _plot_similarity_heatmap(
            jaccard_char["matrix"], disciplines,
            f"Similarità Jaccard (char n-gram n={jaccard_char['n']}) tra discipline",
            img_dir / "similarity_jaccard_char_heatmap.png", dpi
        )

    jaccard_word = sim_results.get("jaccard_word", {})
    for wn, mat in jaccard_word.items():
        _plot_similarity_heatmap(
            mat, disciplines,
            f"Similarità Jaccard (word {wn}-gram) tra discipline",
            img_dir / f"similarity_jaccard_word{wn}_heatmap.png", dpi
        )

    emb_mat = sim_results.get("embedding_similarity")
    if emb_mat:
        _plot_similarity_heatmap(
            emb_mat, disciplines,
            "Similarità semantica (embedding spaCy) tra discipline",
            img_dir / "similarity_embedding_heatmap.png", dpi
        )

    # Correlation scatter between methods
    _plot_similarity_correlation(sim_results, disciplines, img_dir, dpi)


def _plot_similarity_correlation(sim_results: dict, disciplines: list, img_dir: Path, dpi: int):
    n = len(disciplines)
    if n < 3:
        return
    cosine_mat = np.array(sim_results.get("cosine_similarity", [[0]*n]*n))
    emb_mat_raw = sim_results.get("embedding_similarity")
    jw = sim_results.get("jaccard_word", {})
    first_wn = next(iter(jw), None)

    if emb_mat_raw is None or first_wn is None:
        return

    emb_mat = np.array(emb_mat_raw)
    jac_mat = np.array(jw[first_wn])

    # Off-diagonal pairs
    idx = np.triu_indices(n, k=1)
    cos_vals = cosine_mat[idx]
    emb_vals = emb_mat[idx]
    jac_vals = jac_mat[idx]

    fig, axes = plt.subplots(1, 3, figsize=(13, 4))
    palette = sns.color_palette("muted")
    for ax, (x_vals, y_vals, xlabel, ylabel) in zip(axes, [
        (cos_vals, emb_vals, "Coseno TF-IDF", "Embedding"),
        (cos_vals, jac_vals, "Coseno TF-IDF", "Jaccard word"),
        (emb_vals, jac_vals, "Embedding", "Jaccard word"),
    ]):
        ax.scatter(x_vals, y_vals, color=palette[0], alpha=0.7)
        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)
        # Simple trend line
        if len(x_vals) > 1:
            z = np.polyfit(x_vals, y_vals, 1)
            p = np.poly1d(z)
            ax.plot(sorted(x_vals), p(sorted(x_vals)), color=palette[3], linestyle="--")
    fig.suptitle("Correlazione tra metodi di similarità", fontsize=12)
    _save(fig, img_dir / "similarity_correlation_scatter.png", dpi)


# ── Main entry point ─────────────────────────────────────────────────────────

def generate_all_visualizations(all_results: dict, config: dict) -> None:
    """
    Generate and save all figures.

    Parameters
    ----------
    all_results : dict with keys matching pipeline stage names
    config      : pipeline config dict
    """
    _setup()
    output_dir = Path(config["output_dir"])
    dpi = int(config.get("figure_dpi", 150))
    top_n_freq = int(config.get("top_n_frequencies", 30))
    top_n_kw = int(config.get("top_n_keywords", 20))
    wc_max = int(config.get("wordcloud_max_words", 150))

    tok_r = all_results.get("tokenization", {})
    morph_r = all_results.get("morphology", {})
    verb_r = all_results.get("verb_analysis", {})
    agency_r = all_results.get("agency", {})
    nom_r = all_results.get("nominalization", {})
    coh_r = all_results.get("cohesion", {})
    formula_r = all_results.get("academic_formulas", {})
    freq_r = all_results.get("frequency", {})
    kw_r = all_results.get("keywords", {})
    topic_r = all_results.get("topic_modeling", {})
    dep_r = all_results.get("dependency", {})
    sim_r = all_results.get("similarity", {})

    steps = [
        ("Istogramma lunghezza frasi",       lambda: plot_sentence_length_histogram(tok_r, output_dir, dpi)),
        ("Istogramma subordinate/profondità", lambda: plot_subordinate_histogram(tok_r, output_dir, dpi)),
        ("Distribuzione POS",                lambda: plot_pos_distribution(morph_r, output_dir, dpi)),
        ("Heatmap verbi modali",             lambda: plot_modal_heatmap(verb_r, output_dir, dpi)),
        ("Indice hedging",                   lambda: plot_hedging_index(verb_r, output_dir, dpi)),
        ("Attivo vs passivo",                lambda: plot_active_passive(verb_r, output_dir, dpi)),
        ("Verbi di citazione",               lambda: plot_reporting_verbs(verb_r, output_dir, dpi)),
        ("Agency",                           lambda: plot_agency(agency_r, output_dir, dpi)),
        ("Nominalizzazioni",                 lambda: plot_nominalization(nom_r, output_dir, dpi)),
        ("Connettivi discorsivi",            lambda: plot_discourse_markers(coh_r, output_dir, dpi)),
        ("Formule accademiche",              lambda: plot_academic_formulas(formula_r, output_dir, dpi)),
        ("Frequenze parole",                 lambda: plot_word_frequency(freq_r, output_dir, dpi, top_n_freq)),
        ("Parole chiave TF-IDF",             lambda: plot_keywords(kw_r, output_dir, dpi, top_n_kw)),
        ("Word cloud",                       lambda: plot_word_clouds(freq_r, output_dir, dpi, wc_max)),
        ("Topic LDA",                        lambda: plot_lda_topics(topic_r, output_dir, dpi)),
        ("Heatmap doc-topic",                lambda: plot_doc_topic_heatmap(topic_r, output_dir, dpi)),
        ("Etichette dipendenza",             lambda: plot_dependency_labels(dep_r, output_dir, dpi)),
        ("Heatmap similarità",               lambda: plot_similarity(sim_r, output_dir, dpi)),
    ]

    for name, fn in steps:
        try:
            fn()
            logger.info("Visualizzazione completata: %s", name)
        except Exception as exc:
            logger.error("Errore nella visualizzazione '%s': %s", name, exc)

    logger.info("Tutte le visualizzazioni generate.")
