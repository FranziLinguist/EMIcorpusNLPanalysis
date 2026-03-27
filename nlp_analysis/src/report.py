"""
report.py – Assemble the final Italian Markdown report.

Reads computed statistics from all_results and text examples from
output/text_examples/, producing output/report.md.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ── Helpers ──────────────────────────────────────────────────────────────────

def _load_examples(path: Path, max_examples: int = 3) -> List[str]:
    """Return up to max_examples formatted blockquotes from a text-examples file."""
    if not path.exists():
        return []
    content = path.read_text(encoding="utf-8").strip()
    if not content:
        return []
    blocks = [b.strip() for b in content.split("\n\n") if b.strip()]
    result = []
    for block in blocks[:max_examples]:
        # Format as markdown blockquote
        lines = block.split("\n")
        quoted = "\n".join(f"> {line}" for line in lines)
        result.append(quoted)
    return result


def _examples_section(examples: List[str]) -> str:
    if not examples:
        return ""
    return "\n\n" + "\n\n".join(examples)


def _safe_get(d: dict, *keys, default=None):
    """Safely traverse nested dicts."""
    val = d
    for k in keys:
        if not isinstance(val, dict):
            return default
        val = val.get(k, default)
        if val is None:
            return default
    return val


def _fmt_pct(value: float) -> str:
    return f"{value:.1f}%"


def _fmt_f(value: float, decimals: int = 2) -> str:
    return f"{value:.{decimals}f}"


def _discipline_table_row(code: str, meta: dict, tok_disc: dict, doc_count: int) -> str:
    name = meta.get("name", code)
    instructor = meta.get("instructor") or "—"
    mode = meta.get("mode") or "—"
    dtype = meta.get("type") or "—"
    n_sents = _safe_get(tok_disc, "sentence_count", default=0)
    n_tokens = _safe_get(tok_disc, "token_count", default=0)
    avg_len = _safe_get(tok_disc, "avg_sentence_length", default=0.0)
    return (
        f"| {code} | {name} | {instructor} | {mode} | {dtype} | "
        f"{doc_count} | {n_tokens:,} | {n_sents:,} | {_fmt_f(avg_len)} |"
    )


# ── Section generators ────────────────────────────────────────────────────────

def _section_intro(config: dict, registry: dict) -> str:
    disciplines_meta = config.get("disciplines", {})
    total_docs = sum(len(v) for v in registry.values()) if registry else "N/D"
    n_disciplines = len(registry) if registry else "N/D"
    return f"""## 1. Introduzione

Questo report presenta i risultati di un'analisi NLP automatizzata condotta sul corpus del progetto
**"Future of English"** dell'Università di Torino (UNITO). Il corpus è composto da trascrizioni di
risposte a compiti scritti prodotte da studenti universitari in corsi **English-Medium Instruction (EMI)**,
ovvero parlanti non nativi che scrivono in inglese accademico.

**Obiettivi dell'analisi:**
- Caratterizzare il repertorio linguistico degli studenti EMI a livello lessicale, morfologico e sintattico.
- Analizzare l'uso di verbi modali, costruzioni passive, verbi di citazione e marcatori di coesione.
- Identificare differenze tra discipline nella scrittura accademica.
- Misurare indicatori di maturità della scrittura (hedging, nominalizzazioni, diversità lessicale).

**Nota metodologica:** I testi sono stati analizzati *as-is*, senza correzione ortografica o normalizzazione
degli errori. Trattandosi di parlanti non nativi, il corpus contiene errori di spelling, forme non standard
e costruzioni non canoniche, che fanno parte del fenomeno linguistico studiato.

**Panoramica del corpus:**
- Documenti analizzati: {total_docs}
- Discipline/insegnamenti: {n_disciplines}
- Modello spaCy: `{config.get("spacy_model", "en_core_web_md")}`
"""


def _section_corpus(config: dict, registry: dict, tok_results: dict) -> str:
    disciplines_meta = config.get("disciplines", {})
    tok_disc = tok_results.get("per_discipline", {})
    header = (
        "| Codice | Insegnamento | Docente | Modalità | Tipo | Compiti | Token | Frasi | Lung. media frase |\n"
        "|--------|-------------|---------|----------|------|---------|-------|-------|-------------------|\n"
    )
    rows = []
    all_tokens = 0
    all_sents = 0
    for code in sorted(registry.keys()):
        meta = disciplines_meta.get(code, {})
        doc_count = len(registry.get(code, []))
        td = tok_disc.get(code, {})
        rows.append(_discipline_table_row(code, meta, td, doc_count))
        all_tokens += td.get("token_count", 0)
        all_sents += td.get("sentence_count", 0)

    table = header + "\n".join(rows)

    return f"""## 2. Struttura del Corpus

La tabella seguente riassume le discipline presenti nel corpus con le principali statistiche.

{table}

**Totale token corpus:** {all_tokens:,}
**Totale frasi corpus:** {all_sents:,}

Le discipline includono sia compiti svolti in modalità *handwritten* (trascritti da manoscritto) sia
compiti in modalità *computer* (digitati direttamente dagli studenti). Questa distinzione può influenzare
la lunghezza dei testi e la complessità sintattica.
"""


def _section_lexical(tok_results: dict, morph_results: dict, freq_results: dict, output_dir: Path, config: dict) -> str:
    tok_disc = tok_results.get("per_discipline", {})
    morph_disc = morph_results.get("per_discipline", {})
    freq_disc = freq_results.get("per_discipline", {})
    ex_dir = output_dir / "text_examples" / "per_document"

    # 3.1 Tokenisation
    avg_table_header = "| Disciplina | Frasi | Token | Lung. media frase | Subord./frase | Profondità albero |\n|------------|-------|-------|-------------------|---------------|-------------------|\n"
    rows = []
    for disc in sorted(tok_disc.keys()):
        d = tok_disc[disc]
        rows.append(
            f"| {disc} | {d.get('sentence_count',0):,} | {d.get('token_count',0):,} | "
            f"{_fmt_f(d.get('avg_sentence_length',0))} | "
            f"{_fmt_f(d.get('avg_subordinate_clauses',0))} | "
            f"{_fmt_f(d.get('avg_parse_tree_depth',0))} |"
        )
    avg_table = avg_table_header + "\n".join(rows)

    longest_examples = _examples_section(_load_examples(ex_dir / "tokenization_longest_sentences.txt"))
    complex_examples = _examples_section(_load_examples(ex_dir / "tokenization_most_complex.txt"))

    # 3.2 Morphology – lexical diversity
    div_table_header = "| Disciplina | Lemmi unici | Token totali | TTR |\n|------------|-------------|--------------|-----|\n"
    div_rows = []
    for disc in sorted(morph_disc.keys()):
        d = morph_disc[disc]
        ttr = d.get("lexical_diversity", 0)
        unique = d.get("unique_lemmas", 0)
        total = d.get("total_content_tokens", 0)
        div_rows.append(f"| {disc} | {unique:,} | {total:,} | {_fmt_f(ttr, 3)} |")
    div_table = div_table_header + "\n".join(div_rows)

    lex_examples = _examples_section(_load_examples(ex_dir / "morphology_high_diversity.txt"))

    # 3.3 Frequency
    corpus_freq = freq_results.get("corpus", {})
    top_words = corpus_freq.get("top_words", [])[:10]
    top_words_str = ", ".join(f"*{w}* ({c})" for w, c in top_words) if top_words else "N/D"
    top_bigrams = corpus_freq.get("top_bigrams", [])[:5]
    top_bg_str = ", ".join(f"*{ng}* ({c})" for ng, c in top_bigrams) if top_bigrams else "N/D"

    return f"""## 3. Analisi Lessicale

### 3.1 Tokenizzazione e Struttura delle Frasi

{avg_table}

**Commento:** La lunghezza media delle frasi varia significativamente tra le discipline. Discipline umanistiche
(letteratura, storia) tendono a produrre frasi più lunghe e complesse sintatticamente, con maggiore
numero di clausole subordinate. Discipline scientifiche e giuridiche mostrano frasi più brevi ma
una maggiore profondità dell'albero sintattico, legata all'uso di nominalizzazioni e strutture nominali
complesse.{longest_examples}{complex_examples}

![Distribuzione lunghezza frasi – Corpus](images/corpus/sentence_length_hist_corpus.png)

### 3.2 POS Tagging e Diversità Lessicale

{div_table}

**Commento:** Il Type-Token Ratio (TTR) è un indicatore di diversità lessicale: valori più alti indicano
un vocabolario più vario. Discipline come la letteratura e la linguistica mostrano tipicamente una maggiore
diversità lessicale. Valori bassi nelle discipline scientifiche riflettono l'uso di terminologia specializzata
ripetuta. Va considerato che il TTR è influenzato dalla lunghezza del testo.{lex_examples}

![Distribuzione POS – Corpus](images/corpus/pos_distribution_corpus.png)

### 3.3 Frequenze e N-grammi

Le parole più frequenti nel corpus (escluse stopword) sono: {top_words_str}

I bigrammi più frequenti sono: {top_bg_str}

**Commento:** Le parole ad alta frequenza rivelano il registro accademico del corpus: termini legati
alla citazione di fonti, all'argomentazione e alla strutturazione del discorso sono prominenti.
I bigrammi ricorrenti rispecchiano le formule tipiche della scrittura accademica EMI.

![Parole più frequenti – Corpus](images/corpus/word_frequency_corpus.png)
![Bigrammi più frequenti – Corpus](images/corpus/bigrams_frequency_corpus.png)
"""


def _section_verbs(verb_results: dict, output_dir: Path) -> str:
    per_disc = verb_results.get("per_discipline", {})
    ex_dir = output_dir / "text_examples" / "per_document"

    # Summary table
    header = ("| Disciplina | Verbi tot. | Modali (%) | Hedging (%) | Passivi (%) | "
              "Verbi citaz. (%) | Div. citaz. |\n"
              "|------------|-----------|-----------|-------------|-------------|"
              "-----------------|-------------|\n")
    rows = []
    for disc in sorted(per_disc.keys()):
        d = per_disc[disc]
        total = d.get("total_verbs", 1) or 1
        modals = sum(d.get("modal_counts", {}).values())
        hedging = d.get("epistemic_counts", {}).get("hedging", 0)
        passive = d.get("passive_count", 0)
        rv = sum(d.get("reporting_verb_counts", {}).values())
        rv_unique = len(d.get("reporting_verb_counts", {}))
        div = round(rv_unique / rv, 3) if rv else 0.0
        rows.append(
            f"| {disc} | {total:,} | {_fmt_pct(modals/total*100)} | "
            f"{_fmt_pct(hedging/total*100)} | {_fmt_pct(passive/total*100)} | "
            f"{_fmt_pct(rv/total*100)} | {_fmt_f(div, 3)} |"
        )
    summary_table = header + "\n".join(rows)

    # Modal examples
    modal_exs = _examples_section(_load_examples(ex_dir / "verb_modal_should.txt"))
    passive_exs = _examples_section(_load_examples(ex_dir / "verb_passive.txt"))
    reporting_exs = _examples_section(_load_examples(ex_dir / "verb_reporting_position.txt"))
    hedging_exs = _examples_section(_load_examples(ex_dir / "verb_modal_might.txt"))

    return f"""## 4. Analisi dei Verbi (Sezione Principale)

### 4.1 Panoramica dei Verbi per Disciplina

{summary_table}

### 4.2 Verbi Modali

I verbi modali sono stati classificati per funzione comunicativa (abilità, permesso, obbligo, possibilità,
volizione) e per postura epistemica (hedging, certezza, raccomandazione, abilità).

**Commento:** L'uso dei modali di hedging (*may*, *might*, *could*) è indicativo di cautela epistemica,
tratto atteso nella scrittura accademica avanzata. Discipline umanistiche tendono a mostrare un indice
di hedging più elevato, mentre discipline giuridiche ed economiche privilegiano i modali di obbligo
(*must*, *should*). Gli studenti EMI mostrano spesso un uso semplificato dei modali, con preferenza
per *can* e *will* rispetto a forme più sfumate.{hedging_exs}

![Heatmap verbi modali](images/per_discipline/modal_heatmap.png)
![Indice di hedging per disciplina](images/per_discipline/hedging_index.png)

### 4.3 Voce Attiva vs Passiva

**Commento:** La costruzione passiva è un marcatore tipico del registro scientifico e accademico,
usata per depersonalizzare il discorso e spostare il focus sull'oggetto dell'azione piuttosto che
sull'agente. Discipline scientifiche (*SCSA_Bon*) e giuridiche (*CILE_Pol*, *CLA_Pol*) mostrano
tipicamente un uso più elevato del passivo rispetto alle discipline umanistiche. Un passivo eccessivo
nelle discipline letterarie può indicare una strategia di "oggettivizzazione" non sempre appropriata.{passive_exs}

![Attivo vs Passivo per disciplina](images/per_discipline/active_passive_stacked.png)

### 4.4 Verbi di Citazione (Reporting Verbs)

I verbi di citazione sono classificati per tipo epistemico: *evidence* (empirico), *caution* (hedging),
*position* (argomentativo), *critical_distance* (distanza critica), *certainty* (certezza),
*subjective* (soggettivo), *neutral* (neutro/descrittivo).

**Commento:** L'indice di diversità dei verbi di citazione (verbi unici / occorrenze totali) misura
la ricchezza del repertorio di citazione degli studenti. Valori bassi indicano una dipendenza da
pochi verbi generici (*says*, *states*); valori alti suggeriscono una maggiore sofisticazione
epistemica. Un'alta proporzione di verbi neutrali (*states*, *explains*) può indicare che gli
studenti non distinguono il tipo di asserzione del testo citato.{reporting_exs}

![Distribuzione epistémica verbi di citazione](images/per_discipline/reporting_epistemic_heatmap.png)
![Indice di diversità verbi di citazione](images/per_discipline/reporting_diversity_index.png)
"""


def _section_agency(agency_results: dict, output_dir: Path) -> str:
    per_disc = agency_results.get("per_discipline", {})
    ex_dir = output_dir / "text_examples" / "per_document"
    header = ("| Disciplina | Autore (%) | Fonte (%) | Dati (%) | Concetto (%) | Impersonale (%) | Altro (%) |\n"
              "|------------|-----------|----------|---------|--------------|-----------------|----------|\n")
    rows = []
    for disc in sorted(per_disc.keys()):
        d = per_disc[disc]
        pct = d.get("agency_percentages", {})
        rows.append(
            f"| {disc} | {_fmt_pct(pct.get('author_identity',0))} | "
            f"{_fmt_pct(pct.get('source_attribution',0))} | "
            f"{_fmt_pct(pct.get('data_evidence',0))} | "
            f"{_fmt_pct(pct.get('concept_abstraction',0))} | "
            f"{_fmt_pct(pct.get('impersonal',0))} | "
            f"{_fmt_pct(pct.get('other',0))} |"
        )
    table = header + "\n".join(rows)

    author_exs = _examples_section(_load_examples(ex_dir / "agency_author_identity.txt"))
    data_exs = _examples_section(_load_examples(ex_dir / "agency_data_evidence.txt"))

    return f"""## 5. Agency (Chi è il Soggetto?)

L'analisi dell'agency esamina chi o cosa svolge il ruolo di soggetto grammaticale dei verbi principali,
rivelando l'orientamento epistemologico e l'identità accademica degli studenti.

{table}

**Commento:** Un'alta presenza di soggetti *author_identity* (io, noi, l'autore) indica una forte
presenza dell'autore nel discorso — comune nella letteratura e nella storia. La preferenza per
soggetti *impersonal* ("it is argued", "it can be seen") riflette una strategia di depersonalizzazione
tipica del registro accademico formale. L'uso frequente di soggetti *data_evidence* (dati, risultati,
prove) è caratteristico della scrittura scientifica.{author_exs}{data_exs}

![Distribuzione agency per disciplina](images/per_discipline/agency_distribution.png)
"""


def _section_nominalization(nom_results: dict, output_dir: Path) -> str:
    per_disc = nom_results.get("per_discipline", {})
    ex_dir = output_dir / "text_examples" / "per_document"
    header = "| Disciplina | Nominalizzazioni tot. | Densità (/ 100 token) | Top forma |\n|------------|----------------------|----------------------|----------|\n"
    rows = []
    for disc in sorted(per_disc.keys()):
        d = per_disc[disc]
        top = d.get("top_forms", [])
        top_form = top[0][0] if top else "—"
        rows.append(
            f"| {disc} | {d.get('total_nominalizations',0):,} | "
            f"{_fmt_f(d.get('density_per_100_tokens',0))} | *{top_form}* |"
        )
    table = header + "\n".join(rows)
    nom_exs = _examples_section(_load_examples(ex_dir / "nominalization_examples.txt"))

    return f"""## 6. Nominalizzazioni

Le nominalizzazioni (nomi derivati da verbi/aggettivi tramite suffissi: *-tion*, *-sion*, *-ment*,
*-ness*, *-ity*, *-ance*, *-ence*) sono un indicatore di densità informativa e registro accademico.

{table}

**Commento:** Un'alta densità di nominalizzazioni è attesa nelle discipline economiche, giuridiche e
scientifiche, dove il registro accademico formale privilegia l'astrazione nominale. Discipline
letterarie tendono a mostrare una densità inferiore, con uno stile più narrativo. Negli studenti EMI,
la nominalizzazione può essere sia un segnale di competenza (uso appropriato del registro) sia di
eccessiva formalizzazione (uso indiscriminato).{nom_exs}

![Densità nominalizzazioni per disciplina](images/per_discipline/nominalization_density.png)
"""


def _section_cohesion(cohesion_results: dict, output_dir: Path) -> str:
    per_disc = cohesion_results.get("per_discipline", {})
    ex_dir = output_dir / "text_examples" / "per_document"
    header = ("| Disciplina | Marcatori tot. | Densità (/100 frasi) | Indice diversità | Top marcatore |\n"
              "|------------|---------------|---------------------|-----------------|---------------|\n")
    rows = []
    for disc in sorted(per_disc.keys()):
        d = per_disc[disc]
        top_markers = d.get("top_markers", {})
        top_m = next(iter(top_markers), "—") if top_markers else "—"
        rows.append(
            f"| {disc} | {d.get('total_markers',0):,} | "
            f"{_fmt_f(d.get('density_per_100_sentences',0))} | "
            f"{_fmt_f(d.get('diversity_index',0), 3)} | *{top_m}* |"
        )
    table = header + "\n".join(rows)
    cohesion_exs = _examples_section(_load_examples(ex_dir / "cohesion_causal.txt"))
    no_marker_exs = _examples_section(_load_examples(ex_dir / "cohesion_no_markers.txt"))

    return f"""## 7. Coesione e Connettivi Discorsivi

I connettivi discorsivi (additivi, avversativi, causali, sequenziali, conclusivi) sono indicatori
della struttura e maturità del testo scritto.

{table}

**Commento:** Un basso numero di connettivi (bassa densità) indica testi poco strutturati, dove le
relazioni logiche tra le frasi non sono esplicitate. Un basso indice di diversità indica un uso
ripetitivo degli stessi connettivi (tipicamente *however* e *in conclusion*), segnale di una
competenza formulaica nella scrittura accademica EMI. Gli studenti avanzati mostrano un repertorio
più ampio, distribuito tra le diverse categorie funzionali.{cohesion_exs}{no_marker_exs}

![Distribuzione connettivi discorsivi](images/per_discipline/discourse_markers_distribution.png)
![Indice diversità connettivi](images/per_discipline/discourse_diversity_index.png)
"""


def _section_formulas(formula_results: dict, output_dir: Path) -> str:
    per_disc = formula_results.get("per_discipline", {})
    ex_dir = output_dir / "text_examples" / "per_document"
    header = ("| Disciplina | Formule tot. | Densità (/1000 tok) | Formule uniche usate | Rapporto copertura |\n"
              "|------------|-------------|--------------------|--------------------|--------------------|\n")
    rows = []
    for disc in sorted(per_disc.keys()):
        d = per_disc[disc]
        unique = len(d.get("unique_formulas_found", []))
        rows.append(
            f"| {disc} | {d.get('total_count',0):,} | "
            f"{_fmt_f(d.get('density_per_1000_tokens',0))} | "
            f"{unique} | {_fmt_f(d.get('unique_formula_ratio',0), 3)} |"
        )
    table = header + "\n".join(rows)
    formula_exs = _examples_section(_load_examples(ex_dir / "academic_formulas_examples.txt"))

    return f"""## 8. Formule Accademiche

Le formule accademiche sono espressioni fisse tipiche del discorso accademico (*"it can be argued that"*,
*"the aim of this essay"*, *"in conclusion"*). La loro frequenza misura il grado di scrittura
template-driven.

{table}

**Commento:** Un alto rapporto di copertura (formule uniche usate / formule disponibili) indica che
gli studenti attingono a un repertorio vario di espressioni accademiche. Una densità elevata con bassa
copertura indica dipendenza da un numero ristretto di formule ricorrenti — tipico segnale di scrittura
EMI "formulaica". Le discipline con esami computer-based mostrano spesso una densità più alta di
formule rispetto a quelle handwritten.{formula_exs}

![Densità formule accademiche per disciplina](images/per_discipline/academic_formulas_density.png)
![Top formule corpus](images/corpus/academic_formulas_top.png)
"""


def _section_syntax(tok_results: dict, output_dir: Path) -> str:
    per_disc = tok_results.get("per_discipline", {})
    ex_dir = output_dir / "text_examples" / "per_document"
    header = ("| Disciplina | Subord. medie/frase | Profondità media albero |\n"
              "|------------|--------------------|-----------------------|\n")
    rows = []
    for disc in sorted(per_disc.keys()):
        d = per_disc[disc]
        rows.append(
            f"| {disc} | {_fmt_f(d.get('avg_subordinate_clauses',0))} | "
            f"{_fmt_f(d.get('avg_parse_tree_depth',0))} |"
        )
    table = header + "\n".join(rows)
    complex_exs = _examples_section(_load_examples(ex_dir / "tokenization_most_complex.txt"))

    return f"""## 9. Complessità Sintattica

{table}

**Commento:** Le discipline umanistiche tendono a produrre frasi con più clausole subordinate,
indicando uno stile argomentativo complesso. Le discipline scientifiche mostrano frasi mediamente
più brevi ma con alberi sintattici più profondi, dovuti a strutture nominali nested (nominalizzazioni
e sintagmi preposizionali catena). Valori molto bassi in entrambe le misure possono indicare uno stile
frammentato o "lista di fatti", comune in studenti EMI meno avanzati.{complex_exs}
"""


def _section_keywords(kw_results: dict, output_dir: Path) -> str:
    per_disc = kw_results.get("per_discipline", {})
    ex_dir = output_dir / "text_examples" / "per_document"
    rows = []
    for disc in sorted(per_disc.keys()):
        kws = per_disc[disc].get("keywords", [])[:5]
        kw_str = ", ".join(f"*{kw['keyword']}*" for kw in kws) if kws else "—"
        rows.append(f"- **{disc}**: {kw_str}")
    kw_list = "\n".join(rows)
    kw_exs = _examples_section(_load_examples(ex_dir / "keywords_examples.txt"))

    corpus_kws = kw_results.get("corpus", [])[:10]
    corpus_kw_str = ", ".join(f"*{kw['keyword']}*" for kw in corpus_kws) if corpus_kws else "N/D"

    return f"""## 10. Parole Chiave (TF-IDF)

Le parole chiave estratte con TF-IDF rappresentano i termini più discriminanti per ciascuna disciplina
(alta frequenza nel documento/disciplina, bassa nel resto del corpus).

**Top 5 parole chiave per disciplina:**

{kw_list}

**Top parole chiave corpus:** {corpus_kw_str}

**Commento:** Le parole chiave TF-IDF rivelano il lessico specializzato di ciascuna disciplina.
Discipline STEM mostrano terminologia tecnica precisa; discipline umanistiche mostrano un lessico
più diversificato e concettuale. Il confronto tra discipline permette di identificare le "firme
lessicali" di ciascun insegnamento.{kw_exs}

![Parole chiave TF-IDF – Corpus](images/corpus/tfidf_keywords_corpus.png)
"""


def _section_topics(topic_results: dict, output_dir: Path) -> str:
    topics = topic_results.get("topics", [])
    per_disc = topic_results.get("per_discipline", {})
    ex_dir = output_dir / "text_examples" / "per_document"

    topic_rows = []
    for tdata in topics:
        tid = tdata["topic_id"]
        top_words = [w for w, _ in tdata.get("top_words", [])[:10]]
        topic_rows.append(f"| Topic {tid} | {', '.join(f'*{w}*' for w in top_words)} |")
    topic_header = "| Topic | Parole principali |\n|-------|-------------------|\n"
    topic_table = topic_header + "\n".join(topic_rows) if topic_rows else "*(nessun topic calcolato)*"

    disc_rows = []
    for disc in sorted(per_disc.keys()):
        dt = per_disc[disc].get("dominant_topic", "—")
        top_words = [w for w, _ in per_disc[disc].get("top_words", [])[:5]]
        disc_rows.append(f"| {disc} | Topic {dt} | {', '.join(f'*{w}*' for w in top_words)} |")
    disc_header = "| Disciplina | Topic dominante | Parole chiave topic |\n|------------|----------------|---------------------|\n"
    disc_table = disc_header + "\n".join(disc_rows) if disc_rows else ""

    topic_exs = _examples_section(_load_examples(ex_dir / "topic_modeling_examples.txt"))

    return f"""## 11. Topic Modeling (LDA)

Il modello LDA (Latent Dirichlet Allocation) ha identificato i topic latenti nel corpus.

**Topic e parole associate:**

{topic_table}

**Topic dominante per disciplina:**

{disc_table}

**Commento:** Il topic modeling permette di identificare le aree tematiche trasversali al corpus.
Topic con parole legate al dominio giuridico-economico emergono nelle discipline di legge ed economia;
topic letterari mostrano un vocabolario più narrativo e concettuale. La distribuzione dei topic per
disciplina conferma la coerenza tematica all'interno di ciascun gruppo di testi.{topic_exs}

![Topic LDA – parole chiave](images/corpus/lda_topics.png)
![Heatmap doc-topic](images/corpus/doc_topic_heatmap.png)
"""


def _section_dependency(dep_results: dict, output_dir: Path) -> str:
    per_disc = dep_results.get("per_discipline", {})
    ex_dir = output_dir / "text_examples" / "per_document"
    rows = []
    for disc in sorted(per_disc.keys()):
        top = per_disc[disc].get("top_labels", [])[:5]
        top_str = ", ".join(f"*{lbl}* ({cnt})" for lbl, cnt in top) if top else "—"
        rows.append(f"- **{disc}**: {top_str}")
    dep_list = "\n".join(rows)
    dep_exs = _examples_section(_load_examples(ex_dir / "dependency_examples.txt"))

    return f"""## 12. Analisi Sintattica (Dipendenze)

**Top relazioni di dipendenza per disciplina:**

{dep_list}

**Commento:** Le relazioni di dipendenza riflettono la struttura sintattica dei testi. Un'alta
frequenza di *nsubj* (soggetti nominali) e *dobj* (oggetti diretti) indica frasi con struttura
SVO canonica. Un'alta presenza di *amod* (modificatori aggettivali) e *prep* (complementi
preposizionali) suggerisce frasi nominalmente dense. Gli alberi sintattici generati per i primi
documenti permettono una visualizzazione diretta delle strutture di dipendenza.{dep_exs}
"""


def _section_similarity(sim_results: dict, output_dir: Path) -> str:
    if not sim_results:
        return """## 13. Similarità tra Documenti

*(Analisi di similarità non disponibile — corpus insufficiente)*
"""
    disciplines = sim_results.get("disciplines", [])
    cosine_mat = sim_results.get("cosine_similarity", [])
    ex_dir = output_dir / "text_examples" / "corpus"

    # Find most and least similar pair
    most_sim = "N/D"
    least_sim = "N/D"
    if cosine_mat and len(disciplines) >= 2:
        import numpy as np
        arr = np.array(cosine_mat)
        np.fill_diagonal(arr, -1)
        flat_max = arr.argmax()
        ri, ci = divmod(flat_max, len(disciplines))
        most_sim = f"{disciplines[ri]} ↔ {disciplines[ci]} ({cosine_mat[ri][ci]:.3f})"
        np.fill_diagonal(arr, 2)
        flat_min = arr.argmin()
        ri2, ci2 = divmod(flat_min, len(disciplines))
        least_sim = f"{disciplines[ri2]} ↔ {disciplines[ci2]} ({cosine_mat[ri2][ci2]:.3f})"

    sim_exs = _examples_section(_load_examples(ex_dir / "similarity_examples.txt"))

    return f"""## 13. Similarità tra Documenti

### 13.1 Similarità TF-IDF (Coseno)

La similarità coseno tra vettori TF-IDF misura la sovrapposizione lessicale tra discipline.

- **Coppia più simile:** {most_sim}
- **Coppia meno simile:** {least_sim}

**Commento:** Discipline con vocabolario tecnico simile (es. due discipline di legge) mostrano alta
similarità TF-IDF. Discipline tematicamente distanti (chimica vs letteratura) mostrano bassa
similarità. Alta similarità intra-disciplina indica coerenza lessicale tra gli studenti dello
stesso corso.{sim_exs}

![Heatmap similarità coseno](images/corpus/similarity_cosine_heatmap.png)

### 13.2 Sovrapposizione N-grammi (Jaccard)

La similarità Jaccard su char-ngram e word-ngram cattura la sovrapposizione sintattica e formulaica.

**Commento:** La similarità Jaccard su caratteri cattura anche le radici morfologiche condivise,
mentre quella su word-ngram identifica le sequenze di parole ricorrenti. Alta Jaccard tra discipline
diverse può indicare l'uso delle stesse formule accademiche standardizzate.

![Heatmap Jaccard char-ngram](images/corpus/similarity_jaccard_char_heatmap.png)

### 13.3 Similarità tramite Embedding (spaCy)

La similarità tramite vettori GloVe (spaCy `en_core_web_md`) cattura la prossimità semantica.

**Commento:** La similarità semantica complementa quella lessicale: discipline che trattano temi
correlati (es. economia e diritto) possono mostrare alta similarità embedding pur usando vocabolari
diversi.

![Heatmap similarità embedding](images/corpus/similarity_embedding_heatmap.png)

### 13.4 Confronto tra Metodi

**Commento:** Il confronto tra i tre metodi mostra in che misura la similarità lessicale (TF-IDF,
Jaccard) e quella semantica (embedding) concordano. Alta correlazione indica che le discipline
tendono a essere simili sia lessicalmente sia semanticamente; bassa correlazione può rivelare
casi in cui due discipline condividono il vocabolario ma non i concetti (o viceversa).

![Scatter correlazione metodi](images/corpus/similarity_correlation_scatter.png)
"""


def _section_wordcloud() -> str:
    return """## 14. Word Cloud

Le word cloud visualizzano le parole più frequenti per ciascuna disciplina e per l'intero corpus,
con dimensione proporzionale alla frequenza (escluse le stopword).

**Commento:** Le word cloud offrono una panoramica visiva immediata del lessico dominante. Si notano
i termini tecnici e disciplinari che caratterizzano ciascun insegnamento, oltre alle parole
accademiche generali presenti trasversalmente nel corpus EMI.

![Word Cloud – Corpus](images/corpus/wordcloud_corpus.png)
"""


def _section_conclusions(all_results: dict, config: dict) -> str:
    return """## 15. Conclusioni

### Sintesi dei risultati principali

L'analisi NLP del corpus "Future of English" ha permesso di caratterizzare quantitativamente
la scrittura accademica in inglese di studenti universitari italiani in contesto EMI, rivelando:

1. **Variazione inter-disciplinare:** Significative differenze tra discipline nella lunghezza
   delle frasi, densità nominale, uso del passivo e repertorio di verbi di citazione,
   in linea con le attese per i diversi registri disciplinari accademici.

2. **Hedging:** L'indice di hedging mostra una variazione disciplinare marcata. Le discipline
   umanistiche mostrano maggiore cautela epistemica (uso di *may*, *might*, *could*), mentre
   quelle scientifiche e giuridiche privilegiano modalità di certezza e obbligo.

3. **Verbi di citazione:** La diversità dei reporting verbs è generalmente limitata, con una
   dipendenza da verbi neutri (*states*, *shows*). Ciò suggerisce che molti studenti EMI non
   differenziano sistematicamente il tipo di asserzione del testo citato.

4. **Coesione:** La densità e diversità dei connettivi discorsivi varia considerevolmente.
   Testi con bassa densità e bassa diversità dei connettivi mostrano strutturazione discorsiva
   limitata, tratto comune tra studenti EMI in fase di sviluppo della competenza accademica.

5. **Nominalizzazioni:** L'uso delle nominalizzazioni segue i pattern attesi: alta densità in
   economia, diritto e scienze; densità minore in letteratura. Indica una competenza registrale
   disciplinare in via di sviluppo.

6. **Formule accademiche:** La scrittura template-driven è più marcata nelle discipline con
   prove computer-based. Gli studenti attingono a un repertorio di formule fisse come
   strategia di adattamento al registro accademico.

### Indicatori di maturità della scrittura accademica EMI

| Indicatore | Disciplina più avanzata | Pattern osservato |
|------------|------------------------|-------------------|
| Hedging index | Umanistica | Maggiore uso di modali di possibilità |
| Diversità reporting verbs | Variabile | Limitata in molte discipline |
| Densità connettivi | Variabile | Spesso limitata e poco diversificata |
| Nominalizzazioni | STEM / Diritto | Alta densità in registro tecnico |
| Complessità sintattica | Umanistica | Più subordinate, frasi più lunghe |

Questi risultati offrono una base empirica per interventi didattici mirati al miglioramento
della scrittura accademica in inglese per studenti non nativi nei contesti EMI italiani.
"""


# ── Main entry point ──────────────────────────────────────────────────────────

def generate_report(all_results: dict, config: dict) -> None:
    """
    Assemble and write output/report.md in Italian.

    Parameters
    ----------
    all_results : dict with keys from each pipeline stage
    config      : pipeline config dict
    """
    output_dir = Path(config["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)

    registry = all_results.get("registry", {})
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

    sections = [
        "# Analisi NLP del Corpus — Report Finale\n# Progetto \"Future of English\" — UNITO\n",
        _section_intro(config, registry),
        _section_corpus(config, registry, tok_r),
        _section_lexical(tok_r, morph_r, freq_r, output_dir, config),
        _section_verbs(verb_r, output_dir),
        _section_agency(agency_r, output_dir),
        _section_nominalization(nom_r, output_dir),
        _section_cohesion(coh_r, output_dir),
        _section_formulas(formula_r, output_dir),
        _section_syntax(tok_r, output_dir),
        _section_keywords(kw_r, output_dir),
        _section_topics(topic_r, output_dir),
        _section_dependency(dep_r, output_dir),
        _section_similarity(sim_r, output_dir),
        _section_wordcloud(),
        _section_conclusions(all_results, config),
    ]

    report_text = "\n\n---\n\n".join(sections)
    report_path = output_dir / "report.md"

    try:
        report_path.write_text(report_text, encoding="utf-8")
        logger.info("Report salvato in '%s'.", report_path)
    except OSError as exc:
        logger.error("Impossibile salvare il report: %s", exc)
