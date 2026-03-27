"""
results_writer.py – Save pipeline results as JSON + human-readable TXT.

Directory layout:
    results/
        per_corpus/       ← corpus-level aggregates
        per_discipline/   ← per-discipline summaries
        per_document/     ← per-document details
"""

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# ── JSON encoder (handles numpy) ──────────────────────────────────────────────

class _Enc(json.JSONEncoder):
    def default(self, obj):
        try:
            import numpy as np
            if isinstance(obj, np.integer):
                return int(obj)
            if isinstance(obj, np.floating):
                return float(obj)
            if isinstance(obj, np.ndarray):
                return obj.tolist()
        except ImportError:
            pass
        return super().default(obj)


def _jdump(data: Any, path: Path) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False, cls=_Enc)


def _write(path: Path, text: str) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


# ── Generic per-document text ─────────────────────────────────────────────────

def _fmt_per_document_generic(stage: str, per_doc: dict) -> str:
    lines = [f"{'='*70}", f"  {stage.upper()}  –  PER DOCUMENT", f"{'='*70}", ""]
    for doc_id, data in sorted(per_doc.items()):
        lines.append(f"Document: {doc_id}  (discipline: {data.get('discipline','-')})")
        for k, v in data.items():
            if k in ("discipline", "path"):
                continue
            if isinstance(v, list) and len(v) > 10:
                lines.append(f"  {k}: [{v[0]}, {v[1]}, … {v[-1]}]  (n={len(v)})")
            elif isinstance(v, dict) and len(v) > 12:
                top = list(v.items())[:8]
                lines.append(f"  {k}: {{ {', '.join(f'{kk}: {vv}' for kk,vv in top)} … }}")
            else:
                lines.append(f"  {k}: {v}")
        lines.append("")
    return "\n".join(lines)


# ── Stage-specific formatters ─────────────────────────────────────────────────

def _text_registry(data: dict) -> tuple[str, str, str]:
    """Returns (corpus_txt, discipline_txt, document_txt)."""
    lines = [f"{'='*70}", "  REGISTRY  –  CORPUS OVERVIEW", f"{'='*70}", ""]
    total = sum(len(v) for v in data.values())
    lines.append(f"Totale discipline: {len(data)}")
    lines.append(f"Totale documenti: {total}")
    lines.append("")
    lines.append(f"{'Disciplina':<20} {'N documenti':>12}")
    lines.append("-" * 35)
    for disc, paths in sorted(data.items()):
        lines.append(f"{disc:<20} {len(paths):>12}")
    return "\n".join(lines), "", ""


def _text_tokenization(per_disc: dict, per_doc: dict) -> tuple[str, str, str]:
    disc_lines = [f"{'='*70}", "  TOKENIZZAZIONE  –  PER DISCIPLINA", f"{'='*70}", ""]
    disc_lines.append(f"{'Disciplina':<20} {'Frasi':>7} {'Token':>8} {'Avg frase':>10} {'Avg subord':>11} {'Avg depth':>10}")
    disc_lines.append("-" * 70)
    for disc, d in sorted(per_disc.items()):
        disc_lines.append(
            f"{disc:<20} {d.get('sentence_count',0):>7} {d.get('token_count',0):>8} "
            f"{d.get('avg_sentence_length',0):>10.2f} {d.get('avg_subordinate_clauses',0):>11.2f} "
            f"{d.get('avg_parse_tree_depth',0):>10.2f}"
        )

    doc_lines = [f"{'='*70}", "  TOKENIZZAZIONE  –  PER DOCUMENTO", f"{'='*70}", ""]
    doc_lines.append(f"{'Documento':<45} {'Frasi':>6} {'Token':>7} {'Avg sl':>7} {'Avg dep':>8}")
    doc_lines.append("-" * 75)
    for doc_id, d in sorted(per_doc.items()):
        doc_lines.append(
            f"{doc_id:<45} {d.get('sentence_count',0):>6} {d.get('token_count',0):>7} "
            f"{d.get('avg_sentence_length',0):>7.2f} {d.get('avg_parse_tree_depth',0):>8.2f}"
        )

    return "", "\n".join(disc_lines), "\n".join(doc_lines)


def _text_morphology(per_disc: dict, per_doc: dict) -> tuple[str, str, str]:
    disc_lines = [f"{'='*70}", "  MORFOLOGIA  –  PER DISCIPLINA", f"{'='*70}", ""]
    disc_lines.append(f"{'Disciplina':<20} {'TTR':>6} {'Lemmi uniq':>11} {'NOUN%':>7} {'VERB%':>7} {'ADJ%':>6} {'ADV%':>6}")
    disc_lines.append("-" * 67)
    for disc, d in sorted(per_disc.items()):
        pos = d.get("pos_percentages", {})
        disc_lines.append(
            f"{disc:<20} {d.get('lexical_diversity_ttr',0):>6.3f} {d.get('unique_lemma_count',0):>11} "
            f"{pos.get('NOUN',0):>7.1f} {pos.get('VERB',0):>7.1f} {pos.get('ADJ',0):>6.1f} {pos.get('ADV',0):>6.1f}"
        )
    disc_lines.append("")
    disc_lines.append("Top 10 lemmi per disciplina:")
    for disc, d in sorted(per_disc.items()):
        lemmas = d.get("top_lemmas", [])[:10]
        disc_lines.append(f"  {disc}: {', '.join(f'{l[0]}({l[1]})' for l in lemmas)}")

    doc_lines = [f"{'='*70}", "  MORFOLOGIA  –  PER DOCUMENTO", f"{'='*70}", ""]
    doc_lines.append(f"{'Documento':<45} {'TTR':>6} {'Lemmi uniq':>11} {'NOUN%':>7} {'VERB%':>7}")
    doc_lines.append("-" * 78)
    for doc_id, d in sorted(per_doc.items()):
        pos = d.get("pos_percentages", {})
        doc_lines.append(
            f"{doc_id:<45} {d.get('lexical_diversity_ttr',0):>6.3f} {d.get('unique_lemma_count',0):>11} "
            f"{pos.get('NOUN',0):>7.1f} {pos.get('VERB',0):>7.1f}"
        )

    return "", "\n".join(disc_lines), "\n".join(doc_lines)


def _text_verb_analysis(per_disc: dict, per_doc: dict) -> tuple[str, str, str]:
    disc_lines = [f"{'='*70}", "  ANALISI VERBI  –  PER DISCIPLINA", f"{'='*70}", ""]
    disc_lines.append(f"{'Disciplina':<20} {'Tot verbi':>10} {'Passivo%':>9} {'Ability':>8} {'Perm':>7} {'Possib':>8} {'Oblig':>7} {'Epistem':>8}")
    disc_lines.append("-" * 83)
    for disc, d in sorted(per_disc.items()):
        mc = d.get("modal_category_counts", {})
        ep = d.get("epistemic_counts", {})
        ep_tot = sum(ep.values()) if ep else 0
        passive_pct = d.get("passive_ratio", 0) * 100
        disc_lines.append(
            f"{disc:<20} {d.get('total_verbs',0):>10} {passive_pct:>9.1f} "
            f"{mc.get('ability',0):>8} {mc.get('permission',0):>7} {mc.get('possibility',0):>8} "
            f"{mc.get('obligation',0):>7} {ep_tot:>8}"
        )
    disc_lines.append("")
    disc_lines.append("Verbi di citazione per disciplina (top 5):")
    for disc, d in sorted(per_disc.items()):
        rv = d.get("reporting_verb_counts", {})
        top = sorted(rv.items(), key=lambda x: x[1], reverse=True)[:5]
        if top:
            disc_lines.append(f"  {disc}: {', '.join(f'{v}({n})' for v,n in top)}")
        else:
            disc_lines.append(f"  {disc}: (nessuno)")

    doc_lines = [f"{'='*70}", "  ANALISI VERBI  –  PER DOCUMENTO", f"{'='*70}", ""]
    doc_lines.append(f"{'Documento':<45} {'Tot verbi':>10} {'Passivo%':>9} {'Mod tot':>8}")
    doc_lines.append("-" * 75)
    for doc_id, d in sorted(per_doc.items()):
        mc = d.get("modal_category_counts", {})
        mod_tot = sum(mc.values()) if mc else 0
        passive_pct = d.get("passive_ratio", 0) * 100
        doc_lines.append(
            f"{doc_id:<45} {d.get('total_verbs',0):>10} {passive_pct:>9.1f} {mod_tot:>8}"
        )

    return "", "\n".join(disc_lines), "\n".join(doc_lines)


def _text_agency(per_disc: dict, per_doc: dict) -> tuple[str, str, str]:
    disc_lines = [f"{'='*70}", "  AGENCY  –  PER DISCIPLINA", f"{'='*70}", ""]
    disc_lines.append(f"{'Disciplina':<20} {'Concept%':>9} {'AuthorID%':>10} {'SrcAttr%':>9} {'Imperso%':>9} {'Data%':>7} {'Other%':>7}")
    disc_lines.append("-" * 74)
    for disc, d in sorted(per_disc.items()):
        pct = d.get("agency_percentages", {})
        disc_lines.append(
            f"{disc:<20} {pct.get('concept_abstraction',0):>9.1f} {pct.get('author_identity',0):>10.1f} "
            f"{pct.get('source_attribution',0):>9.1f} {pct.get('impersonal',0):>9.1f} "
            f"{pct.get('data_evidence',0):>7.1f} {pct.get('other',0):>7.1f}"
        )

    doc_lines = [f"{'='*70}", "  AGENCY  –  PER DOCUMENTO", f"{'='*70}", ""]
    doc_lines.append(f"{'Documento':<45} {'Concept%':>9} {'AuthID%':>8} {'SrcAttr%':>9} {'Impers%':>8}")
    doc_lines.append("-" * 82)
    for doc_id, d in sorted(per_doc.items()):
        pct = d.get("agency_percentages", {})
        doc_lines.append(
            f"{doc_id:<45} {pct.get('concept_abstraction',0):>9.1f} {pct.get('author_identity',0):>8.1f} "
            f"{pct.get('source_attribution',0):>9.1f} {pct.get('impersonal',0):>8.1f}"
        )

    return "", "\n".join(disc_lines), "\n".join(doc_lines)


def _text_nominalization(per_disc: dict, per_doc: dict) -> tuple[str, str, str]:
    disc_lines = [f"{'='*70}", "  NOMINALIZZAZIONI  –  PER DISCIPLINA", f"{'='*70}", ""]
    disc_lines.append(f"{'Disciplina':<20} {'Totale':>8} {'Density/100':>12}  Top forme")
    disc_lines.append("-" * 70)
    for disc, d in sorted(per_disc.items()):
        top = [f"{f[0]}({f[1]})" for f in d.get("top_forms", [])[:6]]
        disc_lines.append(
            f"{disc:<20} {d.get('total_nominalizations',0):>8} {d.get('density_per_100_tokens',0):>12.2f}  {', '.join(top)}"
        )
    disc_lines.append("")
    disc_lines.append("Distribuzione suffissi per disciplina:")
    for disc, d in sorted(per_disc.items()):
        sd = d.get("suffix_distribution", {})
        top_suf = sorted(sd.items(), key=lambda x: x[1], reverse=True)[:5]
        disc_lines.append(f"  {disc}: {', '.join(f'{s}({n})' for s,n in top_suf)}")

    doc_lines = [f"{'='*70}", "  NOMINALIZZAZIONI  –  PER DOCUMENTO", f"{'='*70}", ""]
    doc_lines.append(f"{'Documento':<45} {'Totale':>8} {'Density/100':>12}")
    doc_lines.append("-" * 68)
    for doc_id, d in sorted(per_doc.items()):
        doc_lines.append(
            f"{doc_id:<45} {d.get('total_nominalizations',0):>8} {d.get('density_per_100_tokens',0):>12.2f}"
        )

    return "", "\n".join(disc_lines), "\n".join(doc_lines)


def _text_cohesion(per_disc: dict, per_doc: dict) -> tuple[str, str, str]:
    disc_lines = [f"{'='*70}", "  COESIONE  –  PER DISCIPLINA", f"{'='*70}", ""]
    disc_lines.append(f"{'Disciplina':<20} {'Tot mark':>9} {'Den/100s':>9} {'Div idx':>8}  Categorie")
    disc_lines.append("-" * 75)
    for disc, d in sorted(per_disc.items()):
        cats = d.get("category_counts", {})
        cat_str = " | ".join(f"{k}:{v}" for k,v in sorted(cats.items()))
        disc_lines.append(
            f"{disc:<20} {d.get('total_markers',0):>9} {d.get('density_per_100_sentences',0):>9.2f} "
            f"{d.get('diversity_index',0):>8.3f}  {cat_str}"
        )
    disc_lines.append("")
    disc_lines.append("Top 5 marcatori per disciplina:")
    for disc, d in sorted(per_disc.items()):
        top = d.get("top_markers", {})
        if isinstance(top, dict):
            top5 = sorted(top.items(), key=lambda x: x[1], reverse=True)[:5]
        else:
            top5 = top[:5]
        disc_lines.append(f"  {disc}: {', '.join(f'{m}({n})' for m,n in top5)}")

    doc_lines = [f"{'='*70}", "  COESIONE  –  PER DOCUMENTO", f"{'='*70}", ""]
    doc_lines.append(f"{'Documento':<45} {'Tot mark':>9} {'Den/100s':>9} {'Div idx':>8}")
    doc_lines.append("-" * 75)
    for doc_id, d in sorted(per_doc.items()):
        doc_lines.append(
            f"{doc_id:<45} {d.get('total_markers',0):>9} {d.get('density_per_100_sentences',0):>9.2f} "
            f"{d.get('diversity_index',0):>8.3f}"
        )

    return "", "\n".join(disc_lines), "\n".join(doc_lines)


def _text_academic_formulas(per_disc: dict, per_doc: dict) -> tuple[str, str, str]:
    disc_lines = [f"{'='*70}", "  FORMULE ACCADEMICHE  –  PER DISCIPLINA", f"{'='*70}", ""]
    disc_lines.append(f"{'Disciplina':<20} {'Totale':>8} {'Den/1000t':>10} {'Uniq ratio':>11}  Top formule")
    disc_lines.append("-" * 80)
    for disc, d in sorted(per_disc.items()):
        fc = d.get("formula_counts", {})
        top = sorted(fc.items(), key=lambda x: x[1], reverse=True)[:4]
        top_str = ", ".join(f"'{f}'({n})" for f,n in top)
        disc_lines.append(
            f"{disc:<20} {d.get('total_count',0):>8} {d.get('density_per_1000_tokens',0):>10.2f} "
            f"{d.get('unique_formula_ratio',0):>11.3f}  {top_str}"
        )

    doc_lines = [f"{'='*70}", "  FORMULE ACCADEMICHE  –  PER DOCUMENTO", f"{'='*70}", ""]
    doc_lines.append(f"{'Documento':<45} {'Totale':>8} {'Den/1000t':>10}")
    doc_lines.append("-" * 66)
    for doc_id, d in sorted(per_doc.items()):
        doc_lines.append(
            f"{doc_id:<45} {d.get('total_count',0):>8} {d.get('density_per_1000_tokens',0):>10.2f}"
        )

    return "", "\n".join(disc_lines), "\n".join(doc_lines)


def _text_frequency(per_disc: dict, per_doc: dict, corpus: dict) -> tuple[str, str, str]:
    corp_lines = [f"{'='*70}", "  FREQUENZE  –  CORPUS", f"{'='*70}", ""]
    corp_lines.append("Top 20 parole:")
    for w, n in (corpus.get("top_words") or [])[:20]:
        corp_lines.append(f"  {w:<25} {n:>6}")
    corp_lines.append("")
    corp_lines.append("Top 15 bigrammi:")
    for bg, n in (corpus.get("top_bigrams") or [])[:15]:
        corp_lines.append(f"  {' '.join(bg) if isinstance(bg, list) else bg:<35} {n:>6}")
    corp_lines.append("")
    corp_lines.append("Top 15 trigrammi:")
    for tg, n in (corpus.get("top_trigrams") or [])[:15]:
        corp_lines.append(f"  {' '.join(tg) if isinstance(tg, list) else tg:<45} {n:>6}")

    disc_lines = [f"{'='*70}", "  FREQUENZE  –  PER DISCIPLINA", f"{'='*70}", ""]
    for disc, d in sorted(per_disc.items()):
        disc_lines.append(f"--- {disc} ---")
        disc_lines.append("Top 10 parole: " + ", ".join(f"{w}({n})" for w,n in (d.get("top_words") or [])[:10]))
        disc_lines.append("Top 5 bigrammi: " + ", ".join(
            f"{'_'.join(bg) if isinstance(bg, list) else bg}({n})" for bg,n in (d.get("top_bigrams") or [])[:5]
        ))
        disc_lines.append("")

    doc_lines = [f"{'='*70}", "  FREQUENZE  –  PER DOCUMENTO", f"{'='*70}", ""]
    for doc_id, d in sorted(per_doc.items()):
        top5 = ", ".join(f"{w}({n})" for w,n in (d.get("top_words") or [])[:5])
        doc_lines.append(f"{doc_id}: {top5}")

    return "\n".join(corp_lines), "\n".join(disc_lines), "\n".join(doc_lines)


def _text_keywords(per_disc: dict, per_doc: dict, corpus: list) -> tuple[str, str, str]:
    corp_lines = [f"{'='*70}", "  KEYWORDS TF-IDF  –  CORPUS", f"{'='*70}", ""]
    corp_lines.append(f"{'Keyword':<35} {'Score':>10}")
    corp_lines.append("-" * 47)
    for item in (corpus or [])[:20]:
        if isinstance(item, dict):
            corp_lines.append(f"{item.get('keyword',''):<35} {item.get('score',0):>10.6f}")
        else:
            corp_lines.append(str(item))

    disc_lines = [f"{'='*70}", "  KEYWORDS TF-IDF  –  PER DISCIPLINA", f"{'='*70}", ""]
    for disc, d in sorted(per_disc.items()):
        kws = d.get("keywords", [])[:12]
        disc_lines.append(f"--- {disc} ---")
        for item in kws:
            if isinstance(item, dict):
                disc_lines.append(f"  {item.get('keyword',''):<35} {item.get('score',0):.6f}")
        disc_lines.append("")

    doc_lines = [f"{'='*70}", "  KEYWORDS TF-IDF  –  PER DOCUMENTO", f"{'='*70}", ""]
    for doc_id, d in sorted(per_doc.items()):
        kws = d.get("keywords", [])[:5]
        top = ", ".join(item.get("keyword","") if isinstance(item, dict) else str(item) for item in kws)
        doc_lines.append(f"{doc_id}: {top}")

    return "\n".join(corp_lines), "\n".join(disc_lines), "\n".join(doc_lines)


def _text_topic_modeling(topics: list, per_disc: dict, per_doc: dict) -> tuple[str, str, str]:
    corp_lines = [f"{'='*70}", "  TOPIC MODELING LDA  –  CORPUS", f"{'='*70}", ""]
    for t in topics:
        words = [w for w, _ in t.get("top_words", [])[:10]]
        corp_lines.append(f"Topic {t['topic_id']:>2}: {', '.join(words)}")

    disc_lines = [f"{'='*70}", "  TOPIC MODELING LDA  –  PER DISCIPLINA", f"{'='*70}", ""]
    disc_lines.append(f"{'Disciplina':<20} {'Topic dom':>10}  Distribuzione topic")
    disc_lines.append("-" * 60)
    for disc, d in sorted(per_disc.items()):
        dom = d.get("dominant_topic", "-")
        dist = d.get("topic_distribution", {})
        if isinstance(dist, dict):
            dist_str = " ".join(f"T{k}:{v}" for k, v in sorted(dist.items(), key=lambda x: int(x[0])))
        elif isinstance(dist, list):
            dist_str = " ".join(f"T{i}:{v:.2f}" for i, v in enumerate(dist) if isinstance(v, (int, float)))
        else:
            dist_str = "-"
        disc_lines.append(f"{disc:<20} {str(dom):>10}  {dist_str}")

    doc_lines = [f"{'='*70}", "  TOPIC MODELING LDA  –  PER DOCUMENTO", f"{'='*70}", ""]
    doc_lines.append(f"{'Documento':<45} {'Topic dom':>10}")
    doc_lines.append("-" * 58)
    for doc_id, d in sorted(per_doc.items()):
        doc_lines.append(f"{doc_id:<45} {str(d.get('dominant_topic','-')):>10}")

    return "\n".join(corp_lines), "\n".join(disc_lines), "\n".join(doc_lines)


def _text_dependency(per_disc: dict, per_doc: dict) -> tuple[str, str, str]:
    disc_lines = [f"{'='*70}", "  DEPENDENCY PARSING  –  PER DISCIPLINA", f"{'='*70}", ""]
    for disc, d in sorted(per_disc.items()):
        top = d.get("top_labels", [])[:8]
        if isinstance(top, list) and top and isinstance(top[0], list):
            top_str = ", ".join(f"{label}({n})" for label, n in top)
        else:
            top_str = str(top)
        disc_lines.append(f"{disc}: {top_str}")

    doc_lines = [f"{'='*70}", "  DEPENDENCY PARSING  –  PER DOCUMENTO", f"{'='*70}", ""]
    doc_lines.append(f"{'Documento':<45}  Top-5 label")
    doc_lines.append("-" * 70)
    for doc_id, d in sorted(per_doc.items()):
        top = d.get("top_labels", [])[:5]
        if isinstance(top, list) and top and isinstance(top[0], list):
            top_str = ", ".join(f"{label}({n})" for label, n in top)
        else:
            top_str = str(top)
        doc_lines.append(f"{doc_id:<45}  {top_str}")

    return "", "\n".join(disc_lines), "\n".join(doc_lines)


def _text_similarity(data: dict) -> tuple[str, str, str]:
    disciplines = data.get("disciplines", [])
    cosine = data.get("cosine_similarity", [])
    emb = data.get("embedding_similarity", [])

    lines = [f"{'='*70}", "  SIMILARITÀ TRA DISCIPLINE  –  CORPUS", f"{'='*70}", ""]
    lines.append("Metrica: cosine similarity (TF-IDF bag-of-words)")
    lines.append("")
    # Header
    header = f"{'':>15}" + "".join(f"{d[:8]:>10}" for d in disciplines)
    lines.append(header)
    lines.append("-" * (15 + 10 * len(disciplines)))
    for i, disc in enumerate(disciplines):
        if i < len(cosine):
            row = f"{disc:<15}" + "".join(f"{cosine[i][j]:>10.3f}" for j in range(len(disciplines)))
            lines.append(row)

    lines.append("")
    lines.append("Metrica: embedding similarity (spaCy vectors)")
    lines.append("")
    lines.append(header)
    lines.append("-" * (15 + 10 * len(disciplines)))
    for i, disc in enumerate(disciplines):
        if i < len(emb):
            row = f"{disc:<15}" + "".join(f"{emb[i][j]:>10.3f}" for j in range(len(disciplines)))
            lines.append(row)

    lines.append("")
    lines.append("Coppie più simili (cosine):")
    pairs = []
    for i in range(len(disciplines)):
        for j in range(i + 1, len(disciplines)):
            if i < len(cosine) and j < len(cosine[i]):
                pairs.append((cosine[i][j], disciplines[i], disciplines[j]))
    pairs.sort(reverse=True)
    for score, d1, d2 in pairs[:10]:
        lines.append(f"  {d1:<20} ↔  {d2:<20}  cosine={score:.3f}")

    return "\n".join(lines), "", ""


# ── Main entry point ──────────────────────────────────────────────────────────

def save_all_results(all_results: dict, config: dict) -> None:
    """
    For each pipeline stage, save:
      results/per_corpus/{stage}.json  +  .txt
      results/per_discipline/{stage}.json  +  .txt
      results/per_document/{stage}.json  +  .txt
    """
    results_root = Path(config.get("results_dir", "./results")).resolve()
    dirs = {
        "corpus":      results_root / "per_corpus",
        "discipline":  results_root / "per_discipline",
        "document":    results_root / "per_document",
    }
    for d in dirs.values():
        d.mkdir(parents=True, exist_ok=True)

    def _save(level: str, stage: str, json_data: Any, txt: str) -> None:
        if not json_data and not txt:
            return
        base = dirs[level] / stage
        if json_data is not None:
            _jdump(json_data, base.with_suffix(".json"))
        if txt:
            _write(base.with_suffix(".txt"), txt + "\n")
        logger.info("Salvato: %s", base)

    # ── registry ──────────────────────────────────────────────────────────────
    reg = all_results.get("registry", {})
    corp_txt, _, _ = _text_registry(reg)
    _save("corpus", "registry", reg, corp_txt)

    # ── tokenization ─────────────────────────────────────────────────────────
    tok = all_results.get("tokenization", {})
    per_disc = tok.get("per_discipline", {})
    per_doc  = tok.get("per_document", {})
    _, disc_txt, doc_txt = _text_tokenization(per_disc, per_doc)
    _save("discipline", "tokenization", per_disc, disc_txt)
    _save("document",   "tokenization", per_doc,  doc_txt)

    # ── morphology ───────────────────────────────────────────────────────────
    mor = all_results.get("morphology", {})
    per_disc = mor.get("per_discipline", {})
    per_doc  = mor.get("per_document", {})
    _, disc_txt, doc_txt = _text_morphology(per_disc, per_doc)
    _save("discipline", "morphology", per_disc, disc_txt)
    _save("document",   "morphology", per_doc,  doc_txt)

    # ── verb_analysis ────────────────────────────────────────────────────────
    verb = all_results.get("verb_analysis", {})
    per_disc = verb.get("per_discipline", {})
    per_doc  = verb.get("per_document", {})
    _, disc_txt, doc_txt = _text_verb_analysis(per_disc, per_doc)
    _save("discipline", "verb_analysis", per_disc, disc_txt)
    _save("document",   "verb_analysis", per_doc,  doc_txt)

    # ── agency ───────────────────────────────────────────────────────────────
    ag = all_results.get("agency", {})
    per_disc = ag.get("per_discipline", {})
    per_doc  = ag.get("per_document", {})
    _, disc_txt, doc_txt = _text_agency(per_disc, per_doc)
    _save("discipline", "agency", per_disc, disc_txt)
    _save("document",   "agency", per_doc,  doc_txt)

    # ── nominalization ───────────────────────────────────────────────────────
    nom = all_results.get("nominalization", {})
    per_disc = nom.get("per_discipline", {})
    per_doc  = nom.get("per_document", {})
    _, disc_txt, doc_txt = _text_nominalization(per_disc, per_doc)
    _save("discipline", "nominalization", per_disc, disc_txt)
    _save("document",   "nominalization", per_doc,  doc_txt)

    # ── cohesion ─────────────────────────────────────────────────────────────
    coh = all_results.get("cohesion", {})
    per_disc = coh.get("per_discipline", {})
    per_doc  = coh.get("per_document", {})
    _, disc_txt, doc_txt = _text_cohesion(per_disc, per_doc)
    _save("discipline", "cohesion", per_disc, disc_txt)
    _save("document",   "cohesion", per_doc,  doc_txt)

    # ── academic_formulas ────────────────────────────────────────────────────
    af = all_results.get("academic_formulas", {})
    per_disc = af.get("per_discipline", {})
    per_doc  = af.get("per_document", {})
    _, disc_txt, doc_txt = _text_academic_formulas(per_disc, per_doc)
    _save("discipline", "academic_formulas", per_disc, disc_txt)
    _save("document",   "academic_formulas", per_doc,  doc_txt)

    # ── frequency ────────────────────────────────────────────────────────────
    freq = all_results.get("frequency", {})
    per_disc = freq.get("per_discipline", {})
    per_doc  = freq.get("per_document", {})
    corpus   = freq.get("corpus", {})
    corp_txt, disc_txt, doc_txt = _text_frequency(per_disc, per_doc, corpus)
    _save("corpus",     "frequency", corpus,   corp_txt)
    _save("discipline", "frequency", per_disc, disc_txt)
    _save("document",   "frequency", per_doc,  doc_txt)

    # ── keywords ─────────────────────────────────────────────────────────────
    kw = all_results.get("keywords", {})
    per_disc = kw.get("per_discipline", {})
    per_doc  = kw.get("per_document", {})
    corpus   = kw.get("corpus", [])
    corp_txt, disc_txt, doc_txt = _text_keywords(per_disc, per_doc, corpus)
    _save("corpus",     "keywords", corpus,   corp_txt)
    _save("discipline", "keywords", per_disc, disc_txt)
    _save("document",   "keywords", per_doc,  doc_txt)

    # ── topic_modeling ───────────────────────────────────────────────────────
    top = all_results.get("topic_modeling", {})
    topics   = top.get("topics", [])
    per_disc = top.get("per_discipline", {})
    per_doc  = top.get("per_document", {})
    corp_txt, disc_txt, doc_txt = _text_topic_modeling(topics, per_disc, per_doc)
    _save("corpus",     "topic_modeling", {"topics": topics, "num_topics": top.get("num_topics")}, corp_txt)
    _save("discipline", "topic_modeling", per_disc, disc_txt)
    _save("document",   "topic_modeling", per_doc,  doc_txt)

    # ── dependency ───────────────────────────────────────────────────────────
    dep = all_results.get("dependency", {})
    per_disc = dep.get("per_discipline", {})
    per_doc  = dep.get("per_document", {})
    _, disc_txt, doc_txt = _text_dependency(per_disc, per_doc)
    _save("discipline", "dependency", per_disc, disc_txt)
    _save("document",   "dependency", per_doc,  doc_txt)

    # ── similarity ───────────────────────────────────────────────────────────
    sim = all_results.get("similarity", {})
    corp_txt, _, _ = _text_similarity(sim)
    _save("corpus", "similarity", sim, corp_txt)

    logger.info("Tutti i risultati salvati in '%s'.", results_root)
    print(f"\n[SAVE] Risultati salvati in: {results_root}")
    print(f"  per_corpus/    → {len(list(dirs['corpus'].iterdir()))} file")
    print(f"  per_discipline/ → {len(list(dirs['discipline'].iterdir()))} file")
    print(f"  per_document/  → {len(list(dirs['document'].iterdir()))} file")
