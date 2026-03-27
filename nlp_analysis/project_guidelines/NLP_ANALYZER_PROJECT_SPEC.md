# NLP Analyzer — Project Specification

## 1. Overview

Build a modular Python NLP pipeline that:

1. **Discovers** all `.txt` documents from a configurable project directory (recursively scanning all subdirectories).
2. **Runs** a comprehensive NLP analysis pipeline on each document and on the corpus as a whole.
3. **Produces** a final report **in Italian** (`report.md` + `images/` folder) containing numerical results, statistics, tables, graphs, word clouds, and commentary — all written in Italian.

The tool targets **a standard laptop** (no GPU required, no large transformer models). All heavy lifting relies on **spaCy** (with `en_core_web_sm` or `en_core_web_md`) and **NLTK**.

---

## 2. Domain Context

### 2.1 — Project Background

This pipeline is part of the **"Future of English" project** at the **University of Turin (UNITO)**. The corpus consists of transcriptions of written exam answers produced by university students in **English-Medium Instruction (EMI)** courses — i.e., non-native English speakers writing academic English.

**Important — typo preservation**: since the authors are non-native speakers, the texts may contain spelling errors, grammatical mistakes, and other non-standard forms. The pipeline must **never correct or normalize typos**. All text must be analyzed as-is. No spell-checking or error-correction step is included in the pipeline.

### 2.2 — Corpus Composition (as of 05/08/2024)

| Code | Course | Instructor | Transcribed | Mode | Type |
| --- | --- | --- | --- | --- | --- |
| `CPH_Mor` | Colonial and Postcolonial History | Morelli – Bobbio | 31 | handwritten | individual |
| `GLD_Gog` | Global and Local Development | Goglio | 4 | computer | group essays |
| `AS_Gus` | African Studies | Gusman | 14 | computer | 9 individual + 5 group |
| `EOK_Geu` | Economics of Knowledge | Geuna | 13 | computer | 11 individual + 2 group |
| `DEIC_San` | Development Economics and Int'l Cooperation | Sanfilippo | 1 | handwritten | group essay |
| `NAL_Car` | North-American Literature | Carosso | 8 | computer | individual |
| `NAL_DiL` | North-American Literature | Di Loreto | 6 | computer | individual |
| `SCSA_Bon` | Synthetic Chemistry for Smart Application | Bonomo | 52 | handwritten | individual |
| `CILE_Pol` | Corporate and Insolvency Law for Economics | Pollastro | 35 | handwritten | individual |
| `CLA_Pol` | Corporate Law Advanced | Pollastro | 19 | handwritten | individual |
| `ELSPS_Zot` | English Linguistics (SPS) | Zottola | 10 | handwritten | individual |
| `ELClass_Zot` | English Linguistics (Class) | Zottola | 7 | handwritten | individual |
| `DISS` | Corpus tesi di laurea | — | 6 | — | dissertations |

**Totals**: 180 participants, 206 transcribed exams, 13 disciplines.

### 2.3 — Directory Layout

The `docs/` directory uses the course **code** (from the table above) as the subdirectory name:

```
docs/
├── CPH_Mor/
│   ├── CPH_Mor_01.txt
│   ├── CPH_Mor_02.txt
│   └── ...
├── GLD_Gog/
│   └── ...
├── AS_Gus/
│   └── ...
├── EOK_Geu/
│   └── ...
├── DEIC_San/
│   └── ...
├── NAL_Car/
│   └── ...
├── NAL_DiL/
│   └── ...
├── SCSA_Bon/
│   └── ...
├── CILE_Pol/
│   └── ...
├── CLA_Pol/
│   └── ...
├── ELSPS_Zot/
│   └── ...
├── ELClass_Zot/
│   └── ...
└── DISS/
    └── ...
```

The pipeline must:

- Auto-discover the directory tree at runtime and persist the discovered structure (paths, groupings) for later comparative analysis.
- Treat each top-level subdirectory as a **discipline** (logical group), using the course code as the discipline identifier.
- Files directly in the root `docs/` folder (if any) are treated as an "ungrouped" category.
- The discovery module should detect and log when the actual file count per discipline differs from the expected counts in the table above.

### 2.4 — Metadata to Preserve

Each discipline has associated metadata that should be stored in the registry and used in the report:

- **Course code** (subdirectory name)
- **Full course name**
- **Instructor name(s)**
- **Exam mode**: `handwritten` (transcribed from handwriting) or `computer` (typed by student)
- **Assignment type**: `individual`, `group`, or `mixed`
- **Expected document count** (from the table above — for validation)

This metadata can be stored in a `metadata.yaml` file alongside the corpus or embedded in `config.yaml` under a `disciplines` key.

---

## 3. Tech Stack & Constraints

| Component          | Choice                                                        |
| ------------------ | ------------------------------------------------------------- |
| Language           | Python 3.10+                                                  |
| Core NLP           | **spaCy** (`en_core_web_md`) + **NLTK**                      |
| TF-IDF / Vectors   | `scikit-learn` (`TfidfVectorizer`, cosine similarity)         |
| Topic Modeling     | `gensim` (LDA)                                                |
| Visualization      | `matplotlib`, `seaborn`, `wordcloud`                          |
| Report generation  | Python string/template rendering to Markdown                  |
| Config             | `config.yaml` at project root                                 |
| Dependency mgmt    | `requirements.txt`                                            |

### Performance guardrails

- Use spaCy **small or medium** English model only (no `_lg` or `_trf`).
- No Hugging Face transformer models.
- Topic modeling (LDA): cap at `n_topics=10`, `passes=10`.
- Dependency parse tree visualizations: generate only for the **first 3 sentences** of each document (to avoid huge SVGs).
- All matplotlib figures saved at 150 DPI max.

---

## 4. Project Structure

```
nlp-analyzer/
├── config.yaml                  # User-editable configuration
├── requirements.txt
├── run_pipeline.py              # Single entry point — runs the full pipeline
├── docs/                        # Input documents directory (configurable)
│   ├── CPH_Mor/                 # Colonial and Postcolonial History
│   │   └── *.txt
│   ├── SCSA_Bon/                # Synthetic Chemistry
│   │   └── *.txt
│   ├── CILE_Pol/                # Corporate and Insolvency Law
│   │   └── *.txt
│   └── ...                      # (13 discipline folders total)
├── src/
│   ├── __init__.py
│   ├── discovery.py             # Directory scanning & path registry
│   ├── preprocessing.py         # Text cleaning, normalization
│   ├── tokenization.py          # Tokenization & sentence splitting
│   ├── morphology.py            # POS tagging, lemmatization
│   ├── verb_analysis.py         # Verb-specific deep analysis (modals, passive, reporting verbs)
│   ├── agency.py                # Agency analysis — who is the subject of main verbs
│   ├── nominalization.py        # Nominalization detection (-tion, -ment, -ness, etc.)
│   ├── cohesion.py              # Cohesive devices & discourse markers
│   ├── academic_formulas.py     # Formulaic academic n-gram detection
│   ├── frequency.py             # Word frequency, n-grams
│   ├── keywords.py              # TF-IDF keyword extraction
│   ├── topic_modeling.py        # LDA topic modeling
│   ├── dependency.py            # Dependency parsing & syntax trees
│   ├── similarity.py            # Discipline-wise text similarity
│   ├── visualization.py         # All chart/graph/wordcloud generation
│   └── report.py                # Markdown report assembler (Italian)
├── output/
│   ├── report.md                # Final report in Italian
│   ├── text_examples/           # Saved text excerpts illustrating results
│   │   ├── per_document/
│   │   ├── per_discipline/
│   │   └── corpus/
│   └── images/                  # All generated figures
│       ├── per_document/
│       ├── per_discipline/
│       └── corpus/
└── tests/                       # Optional unit tests
```

---

## 5. Configuration (`config.yaml`)

```yaml
# Paths
docs_dir: "./docs"
output_dir: "./output"

# spaCy model
spacy_model: "en_core_web_md"

# Analysis parameters
ngram_range: [1, 3]            # Unigrams through trigrams
top_n_keywords: 20             # Top TF-IDF keywords per document
top_n_frequencies: 30          # Top N words in frequency charts
lda_num_topics: 8              # Number of LDA topics
lda_passes: 10
wordcloud_max_words: 150
dep_parse_max_sentences: 3     # Max sentences for dependency tree SVGs
figure_dpi: 150

# Reporting verbs list (extendable)
reporting_verbs:
  - argues
  - claims
  - suggests
  - shows
  - demonstrates
  - states
  - explains
  - proposes
  - believes
  - observes
  - finds
  - indicates
  - reveals
  - notes
  - maintains
  - asserts
  - contends

# Nominalization suffixes
nominalization_suffixes:
  - -tion
  - -sion
  - -ment
  - -ness
  - -ity
  - -ance
  - -ence

# Cohesive devices / discourse markers (extendable)
discourse_markers:
  additive: ["moreover", "furthermore", "in addition", "additionally", "also", "besides"]
  adversative: ["however", "nevertheless", "on the other hand", "in contrast", "yet", "although"]
  causal: ["therefore", "consequently", "thus", "hence", "as a result", "because"]
  sequential: ["first", "secondly", "thirdly", "finally", "next", "then", "subsequently"]
  conclusive: ["in conclusion", "to summarize", "in summary", "overall", "to conclude"]

# Academic formula n-grams (extendable list of expected phrases)
academic_formulas:
  - "the aim of this essay"
  - "the purpose of this paper"
  - "this paper discusses"
  - "this essay argues"
  - "the author argues that"
  - "according to the author"
  - "in conclusion"
  - "it can be argued that"
  - "it is important to note"
  - "on the one hand"
  - "on the other hand"
  - "in other words"
  - "for example"
  - "for instance"
  - "as a result"
  - "in order to"
  - "with regard to"
  - "in terms of"
  - "as mentioned above"
  - "the findings suggest"

# Similarity parameters
ngram_overlap_char_n: 3        # Character-level n-gram size for Jaccard
ngram_overlap_word_n: [2, 3]   # Word-level n-gram sizes for Jaccard
use_sentence_embeddings: true  # Enable spaCy doc.vector similarity (needs en_core_web_md)

# Text examples
save_text_examples: true       # Save illustrative text excerpts for each analysis
text_example_max_per_task: 5   # Max examples saved per analysis task per document

# Report language
report_language: "it"          # Italian

# Discipline metadata (used in report generation and validation)
disciplines:
  CPH_Mor:
    name: "Colonial and Postcolonial History"
    instructor: "Morelli – Bobbio"
    mode: "handwritten"
    type: "individual"
    expected_count: 31
  GLD_Gog:
    name: "Global and Local Development"
    instructor: "Goglio"
    mode: "computer"
    type: "group"
    expected_count: 4
  AS_Gus:
    name: "African Studies"
    instructor: "Gusman"
    mode: "computer"
    type: "mixed"
    expected_count: 14
  EOK_Geu:
    name: "Economics of Knowledge"
    instructor: "Geuna"
    mode: "computer"
    type: "mixed"
    expected_count: 13
  DEIC_San:
    name: "Development Economics and International Cooperation"
    instructor: "Sanfilippo"
    mode: "handwritten"
    type: "group"
    expected_count: 1
  NAL_Car:
    name: "North-American Literature"
    instructor: "Carosso"
    mode: "computer"
    type: "individual"
    expected_count: 8
  NAL_DiL:
    name: "North-American Literature"
    instructor: "Di Loreto"
    mode: "computer"
    type: "individual"
    expected_count: 6
  SCSA_Bon:
    name: "Synthetic Chemistry for Smart Application"
    instructor: "Bonomo"
    mode: "handwritten"
    type: "individual"
    expected_count: 52
  CILE_Pol:
    name: "Corporate and Insolvency Law for Economics"
    instructor: "Pollastro"
    mode: "handwritten"
    type: "individual"
    expected_count: 35
  CLA_Pol:
    name: "Corporate Law Advanced"
    instructor: "Pollastro"
    mode: "handwritten"
    type: "individual"
    expected_count: 19
  ELSPS_Zot:
    name: "English Linguistics (SPS)"
    instructor: "Zottola"
    mode: "handwritten"
    type: "individual"
    expected_count: 10
  ELClass_Zot:
    name: "English Linguistics (Class)"
    instructor: "Zottola"
    mode: "handwritten"
    type: "individual"
    expected_count: 7
  DISS:
    name: "Corpus tesi di laurea"
    instructor: null
    mode: null
    type: "dissertation"
    expected_count: 6
```

---

## 6. Pipeline Stages (in execution order)

### 6.1 — Document Discovery (`discovery.py`)

- Recursively scan `docs_dir` for all `*.txt` files.
- Build a registry structured as:
  ```json
  {
    "discipline_name": ["path/to/doc1.txt", "path/to/doc2.txt", ...]
  }
  ```
  where `discipline_name` = top-level subdirectory name.
- Files directly in `docs/` root (if any) → `"_ungrouped"` discipline.
- Log and print a summary: total files, disciplines found, files per discipline.
- Persist the registry as `output/document_registry.json`.

### 6.2 — Preprocessing (`preprocessing.py`)

- Load each `.txt` file (UTF-8).
- Normalize whitespace (collapse multiple spaces/newlines).
- Strip non-printable characters.
- Optionally lowercase (configurable; default: preserve case for NER, provide lowercased copy for frequency analysis).
- Return a dict per document: `{ "id", "discipline", "path", "raw_text", "clean_text" }`.

### 6.3 — Tokenization & Sentence Splitting (`tokenization.py`)

- Use spaCy for sentence segmentation.
- Use spaCy tokenizer for word tokens (excluding punctuation and whitespace tokens).
- Compute per document:
  - Total sentence count
  - Total token count
  - Average sentence length (in tokens)
  - Sentence length distribution (list of lengths)
- NLTK `word_tokenize` as fallback/comparison if needed.
- **Save text examples**: save the longest and shortest sentences per document to `output/text_examples/`.

### 6.4 — POS Tagging & Lemmatization (`morphology.py`)

- Run spaCy pipeline; extract for each token: `(text, lemma, pos, tag, is_stop)`.
- Compute per document:
  - POS distribution (counts and percentages for each POS tag)
  - Lemma frequency list (excluding stopwords)
  - Unique lemma count vs total token count (lexical diversity)
- **Save text examples**: sentences with highest lexical diversity and sentences containing rare lemmas to `output/text_examples/`.

### 6.5 — Verb Analysis (`verb_analysis.py`)

This is a **core focus area** of the project. Analyze verb usage deeply.

#### 6.5.1 — Modal Verb Analysis

- Detect modal verbs: `can, could, may, might, shall, should, will, would, must, ought to, need to`.
- Count occurrences per document, per discipline, and corpus-wide.
- Compute modal verb frequency as percentage of all verbs.
- Classify modals by function:
  - **Ability**: can, could
  - **Permission**: may, can, could
  - **Obligation/Necessity**: must, should, ought to, need to, shall
  - **Possibility**: may, might, could
  - **Volition/Prediction**: will, would, shall
- Additionally classify modals by **epistemic stance** (key for EMI research):
  - **Hedging** (tentative claims): may, might, could → academic caution
  - **Strong claims**: must → certainty, assertiveness
  - **Recommendation**: should → evaluative stance
  - **Ability**: can → capability framing
- Produce a heatmap: modal verb × discipline.
- Produce a **hedging index** per discipline: ratio of hedging modals to total modals. Compare across disciplines (humanities expected higher hedging; law/policy expected higher obligation).
- **Save text examples**: for each modal category, save up to N example sentences to `output/text_examples/`.

#### 6.5.2 — Active vs Passive Voice

- Detect passive constructions using dependency parsing:
  - Look for `nsubjpass` / `auxpass` dependency labels (spaCy).
  - Alternatively: pattern = auxiliary "be" (any form) + past participle (VBN).
- Compute active/passive ratio per document, per discipline, corpus-wide.
- Stacked bar chart per discipline.
- **Save text examples**: save representative passive and active sentences to `output/text_examples/`.

#### 6.5.3 — Reporting Verbs Extraction (`verb_analysis.py`)

- Search for reporting verbs from the configurable list: `argues, claims, suggests, shows, demonstrates, states, explains, proposes, believes, observes, finds, indicates, reveals, notes, maintains, asserts, contends` (extendable in `config.yaml`).
- Count occurrences per document, per discipline, corpus-wide.
- Classify each reporting verb by **epistemic type**:
  - **Evidence** (empirical): shows, demonstrates, reveals, finds, indicates
  - **Caution** (hedging): suggests, implies, indicates
  - **Position** (argumentative): argues, contends, maintains, asserts, proposes
  - **Critical distance**: claims (implies skepticism toward the source)
  - **Certainty**: demonstrates, proves, establishes
  - **Subjective**: believes, thinks, feels
  - **Neutral/descriptive**: states, explains, notes, observes, describes
- Compute per discipline:
  - Total reporting verb count and % of all verbs.
  - Distribution across epistemic types (bar chart per discipline).
  - **Key diagnostic**: do students distinguish between "argues" and "shows"? Or do they default to generic verbs like "says" / "states"? Compute a **reporting verb diversity index** (unique reporting verbs / total reporting verb occurrences).
- **Save text examples**: for each epistemic category, save example sentences showing the reporting verb in context to `output/text_examples/`.

#### 6.5.4 — Verb Type Summary Table

- For each document and discipline produce a summary table:

| Metric                         | Value  | % of all verbs |
| ------------------------------ | ------ | -------------- |
| Total verbs                    | ...    | 100%           |
| Modal verbs                    | ...    | ...            |
| — of which hedging             | ...    | ...            |
| — of which obligation          | ...    | ...            |
| Passive constructions          | ...    | ...            |
| Reporting verbs                | ...    | ...            |
| — evidence type                | ...    | ...            |
| — position type                | ...    | ...            |
| — caution type                 | ...    | ...            |
| Reporting verb diversity index | ...    | n/a            |

### 6.6 — Word Frequency & N-grams (`frequency.py`)

- Compute word frequency (excluding stopwords, punctuation) per document and corpus.
- Compute bigram and trigram frequency (using NLTK `collocations` or custom counter).
- Top N most frequent for each level.
- Output: bar charts, frequency tables.
- **Save text examples**: for top frequent words and n-grams, save sentences where they occur in context to `output/text_examples/`.

### 6.7 — TF-IDF Keyword Extraction (`keywords.py`)

- Use `scikit-learn`'s `TfidfVectorizer` across the full corpus.
- Extract top N keywords per document.
- Extract top N keywords per discipline (concatenate discipline texts).
- Extract corpus-wide top keywords.
- Output: ranked keyword tables with TF-IDF scores.
- **Save text examples**: for each top keyword, save example sentences where it appears to `output/text_examples/`.

### 6.8 — Topic Modeling (`topic_modeling.py`)

- Preprocess: lemmatize, remove stopwords, build dictionary and bag-of-words corpus (gensim).
- Train LDA model (`lda_num_topics` topics, `lda_passes` passes).
- Extract top 10 words per topic.
- Assign dominant topic per document.
- Output:
  - Topic × top-words table.
  - Document × topic distribution heatmap.
  - Per-discipline dominant topic summary.
- **Save text examples**: for each topic, save the most representative sentences (highest topic probability) to `output/text_examples/`.

### 6.9 — Dependency Parsing & Syntax Trees (`dependency.py`)

- For each document, parse the first `dep_parse_max_sentences` sentences.
- Generate spaCy `displacy` SVG renders of dependency trees.
- Save SVGs to `output/images/per_document/`.
- Compute **per-discipline** dependency label distribution (nsubj, dobj, amod, etc.).
- Bar chart of top 15 dependency relations **per discipline**.
- **Save text examples**: for each top dependency relation per discipline, save example sentences to `output/text_examples/`.

### 6.10 — Text Similarity (`similarity.py`)

Three complementary similarity methods applied at **discipline level**. No document × document matrices — all analysis is aggregated by discipline.

#### 6.10.1 — TF-IDF Cosine Similarity

- Build TF-IDF matrix for all documents.
- Compute similarity **discipline-wise**:
  - Average cosine similarity among documents within each discipline (intra-discipline cohesion).
  - Average cosine similarity between disciplines (inter-discipline distance).
- Output: discipline × discipline heatmap.
- **Save text examples**: for the highest and lowest similarity pairs, save the most overlapping passages to `output/text_examples/`.

#### 6.10.2 — N-gram Overlap

- Compute **Jaccard similarity** on character-level n-grams (n=3) and word-level n-grams (bigrams and trigrams).
- Jaccard formula: `|A ∩ B| / |A ∪ B|`.
- Aggregate **discipline-wise**:
  - Average Jaccard among documents within each discipline.
  - Average Jaccard between disciplines.
- Output: discipline-level heatmap.
- **Save text examples**: for each discipline, save the top N shared n-grams with their source sentences to `output/text_examples/`.

#### 6.10.3 — Sentence Embedding Similarity

- Use **spaCy's built-in document vectors** (`doc.vector` from `en_core_web_md`) as lightweight document embeddings.
- Compute similarity **discipline-wise**:
  - Average embedding similarity among documents within each discipline.
  - Average embedding similarity between disciplines.
- Output: discipline-level embedding heatmap.
- **Note**: `en_core_web_md` provides 300-dimensional GloVe-based vectors. Lightweight, no GPU needed. Configurable via `use_sentence_embeddings` flag.

#### 6.10.4 — Combined Similarity Summary

- For each discipline, produce a summary table showing all three similarity scores: within discipline and between disciplines.
- Correlation analysis: how much do the three methods agree? (Pearson/Spearman correlation across disciplines).
- Scatter plot of method agreement.
- **Save text examples**: for the discipline with highest and lowest intra-discipline similarity, save representative excerpts.

### 6.11 — Agency Analysis (`agency.py`)

Analyze **who or what** serves as the grammatical subject of main verbs — a key indicator of academic identity and epistemological stance in EMI writing.

- Use spaCy dependency parsing to extract subject–verb pairs: for each main verb, identify its `nsubj` or `nsubjpass`.
- Classify subjects into **agency categories**:
  - **Author identity**: "I", "we", "the author" → strong authorial presence
  - **Source attribution**: "the article", "the author", "Smith (2020)" → discourse positioning
  - **Data/evidence**: "the data", "the results", "the experiment", "the findings" → empirical epistemology
  - **Concept/abstraction**: "the theory", "the argument", "globalization" → conceptual framing
  - **Impersonal**: "it" (as dummy subject: "it is argued", "it can be seen") → impersonality
  - **Other/unclassified**
- Compute per document, per discipline:
  - Distribution of agency categories (counts and %).
  - Bar chart per discipline.
- **Save text examples**: for each agency category, save representative subject–verb sentences to `output/text_examples/`.

### 6.12 — Nominalization Detection (`nominalization.py`)

Detect nominalizations as a marker of **academic density** — a hallmark of disciplinary writing in EMI contexts.

- Scan all tokens for words ending in configurable suffixes: `-tion, -sion, -ment, -ness, -ity, -ance, -ence`.
- Filter out common non-academic words (e.g., "question", "attention", "moment") using a stop-list or frequency threshold.
- Compute per document, per discipline:
  - Total nominalization count.
  - Nominalization density: nominalizations per 100 tokens.
  - Top N most frequent nominalizations.
  - Distribution by suffix type.
- Expected disciplinary patterns (for interpretive commentary):
  - **High nominalization**: economics, law, science (dense academic prose).
  - **Medium**: history, anthropology.
  - **Lower**: literature (more narrative style).
- **Save text examples**: sentences with highest nominalization density, and sentences where the student could have nominalized but used a verb instead (if detectable via lemma overlap).

### 6.13 — Cohesive Devices & Discourse Markers (`cohesion.py`)

Detect and classify discourse markers to assess **text structure and cohesion quality** in student writing.

- Search for discourse markers from the configurable categorized list in `config.yaml`:
  - **Additive**: moreover, furthermore, in addition, additionally, also, besides
  - **Adversative**: however, nevertheless, on the other hand, in contrast, yet, although
  - **Causal**: therefore, consequently, thus, hence, as a result, because
  - **Sequential**: first, secondly, thirdly, finally, next, then, subsequently
  - **Conclusive**: in conclusion, to summarize, in summary, overall, to conclude
- Compute per document, per discipline:
  - Total discourse marker count.
  - Discourse marker density: markers per 100 sentences.
  - Distribution across categories (bar chart).
  - **Diversity index**: unique markers / total marker occurrences. Low diversity = formulaic, repetitive cohesion. High diversity = more advanced academic writing.
  - Top N most used markers.
- **Diagnostic patterns** (for interpretive commentary):
  - Very few markers → poorly structured writing.
  - Always the same markers (e.g., only "however" and "in conclusion") → formulaic EMI writing.
  - Diverse markers across categories → more advanced writing proficiency.
- **Save text examples**: sentences containing each marker category; examples of long passages with no markers at all.

### 6.14 — Academic Formula Detection (`academic_formulas.py`)

Detect **formulaic academic phrases** to measure the degree of template-based writing in student exams — a key indicator of EMI writing development.

- Match against the configurable list of academic formulas in `config.yaml` (e.g., "the aim of this essay", "this paper discusses", "according to the author", "it can be argued that", etc.).
- Use case-insensitive substring matching (or regex for flexible word boundaries).
- Compute per document, per discipline:
  - Total formula count.
  - Formula density: formulas per 1000 tokens.
  - Frequency of each formula.
  - Top N most used formulas.
  - **Unique formula ratio**: unique formulas used / total available in list → how much of the "academic template repertoire" does the student deploy?
- **Compare across disciplines**: which disciplines see the most template-driven writing?
- **Save text examples**: sentences containing each detected formula, with surrounding context, to `output/text_examples/`.

### 6.15 — Sentence Complexity Enhancement (in `tokenization.py`)

In addition to basic sentence length (already in 6.3), compute:

- **Subordinate clause count** per sentence: count `advcl`, `acl`, `relcl`, `ccomp`, `xcomp` dependency labels (spaCy) which indicate subordination.
- **Parse tree depth** per sentence: maximum depth of the dependency tree for each sentence.
- Compute per document, per discipline:
  - Average subordinate clauses per sentence.
  - Average parse tree depth.
  - Distribution histograms.
- Expected disciplinary patterns:
  - Long sentences + many subordinates → humanities.
  - Medium sentences + nominalizations → economics/law.
  - Short sentences + passive → science.
- **Save text examples**: most syntactically complex sentences (deepest parse tree); simplest sentences.

### 6.16 — Visualization (`visualization.py`)

Central module called by other modules or invoked at report-assembly time. Must generate and save:

| Chart                                    | Level                    | Format |
| ---------------------------------------- | ------------------------ | ------ |
| Sentence length distribution histogram   | per-doc, corpus          | PNG    |
| Subordinate clause count histogram       | per-discipline           | PNG    |
| Parse tree depth histogram               | per-discipline           | PNG    |
| POS distribution bar chart               | per-doc, corpus          | PNG    |
| Modal verb heatmap                       | per-discipline           | PNG    |
| Hedging index bar chart                  | per-discipline           | PNG    |
| Active vs passive stacked bar            | per-discipline           | PNG    |
| Reporting verbs distribution bar chart   | per-discipline           | PNG    |
| Reporting verbs: epistemic type breakdown| per-discipline           | PNG    |
| Reporting verb diversity index           | per-discipline           | PNG    |
| Agency category distribution bar chart   | per-discipline           | PNG    |
| Nominalization density bar chart         | per-discipline           | PNG    |
| Discourse markers distribution           | per-discipline           | PNG    |
| Discourse markers diversity index        | per-discipline           | PNG    |
| Academic formulas frequency bar chart    | per-discipline           | PNG    |
| Word frequency bar chart (top N)         | per-doc, corpus          | PNG    |
| Bigram/trigram frequency bar chart       | corpus                   | PNG    |
| TF-IDF keyword bar chart                 | per-doc, corpus          | PNG    |
| Word cloud                               | per-discipline, corpus   | PNG    |
| LDA topic-words chart                    | corpus                   | PNG    |
| Document-topic heatmap                   | corpus                   | PNG    |
| Dependency label distribution bar chart  | per-discipline           | PNG    |
| Dependency tree renders                  | per-doc (first N sent.)  | SVG    |
| Cosine similarity heatmap (TF-IDF)       | discipline × discipline  | PNG    |
| N-gram overlap heatmap (Jaccard)         | discipline × discipline  | PNG    |
| Sentence embedding similarity heatmap    | discipline × discipline  | PNG    |
| Similarity methods correlation scatter   | corpus                   | PNG    |

All figures must have:
- Clear Italian titles and axis labels.
- Consistent color palette (use a seaborn palette, e.g. `"Set2"` or `"muted"`).
- Legend where appropriate.
- Saved to the appropriate `output/images/` subdirectory.

### 6.17 — Text Examples Export (cross-cutting)

**Every analysis module** must save concrete text examples that illustrate the obtained results. This is a **global requirement** across all pipeline stages:

- **What to save**: actual sentences or passages from the source documents that exemplify the detected pattern (e.g., a sentence containing a modal verb classified as "obligation", a passive voice sentence, a passage with high n-gram overlap across documents, etc.).
- **Where to save**: `output/text_examples/{task_name}/{discipline}/` as `.txt` files.
- **How many**: up to `text_example_max_per_task` examples per analysis task per document (configurable, default 5).
- **Format**: each example file contains the example text, the source document path, the sentence/token index, and the analysis label. Example:
  ```
  [SOURCE] docs/ELSPS_Zot/student_01.txt (sentence 14)
  [LABEL]  Modal verb — Obligation (must)
  [TEXT]   Students must demonstrate a clear understanding of morphological rules.
  ```
- **Usage in report**: the report generator (`report.py`) reads from `output/text_examples/` and embeds selected examples in each report section as illustrative quotations, formatted as Markdown blockquotes.

Modules and their required text examples:

| Module                 | Examples to save                                                              |
| ---------------------- | ----------------------------------------------------------------------------- |
| `tokenization.py`      | Longest and shortest sentences; most/least syntactically complex sentences    |
| `morphology.py`        | Sentences with highest lexical diversity; rare lemma usage                    |
| `verb_analysis.py`     | Modal verbs per epistemic category; passive/active sentences; reporting verbs per epistemic type |
| `agency.py`            | Subject–verb pairs for each agency category (author, data, impersonal, etc.) |
| `nominalization.py`    | Sentences with highest nominalization density; low-density counterexamples    |
| `cohesion.py`          | Sentences with each discourse marker category; long passages with no markers  |
| `academic_formulas.py` | Sentences containing each detected academic formula with context              |
| `frequency.py`         | Sentences containing top frequent words; top n-gram occurrences in context    |
| `keywords.py`          | Sentences containing top TF-IDF keywords                                     |
| `topic_modeling.py`    | Representative sentences for each LDA topic                                  |
| `dependency.py`        | Sentences exemplifying top dependency patterns per discipline                 |
| `similarity.py`        | Highest-overlap passages between documents; most divergent passages across disciplines |

---

## 7. Report Generation (`report.py`)

Generate `output/report.md` entirely **in Italian**. The report must be structured, readable, and self-contained (all images referenced with relative paths).

### Report Structure

```
# Analisi NLP del Corpus — Report Finale
# Progetto "Future of English" — UNITO

## 1. Introduzione
   - Descrizione del progetto "Future of English" e obiettivi dell'analisi NLP
   - Panoramica del corpus: 206 compiti trascritti, 13 insegnamenti, 180 partecipanti
   - Nota metodologica: testi di parlanti non nativi, nessuna correzione ortografica applicata

## 2. Struttura del Corpus
   - Tabella delle discipline con codice insegnamento, docente, n° compiti trascritti
   - Statistiche di base per disciplina (n. parole, n. frasi, lunghezza media)
   - Distinzione tra compiti individuali e di gruppo (dove applicabile)

## 3. Analisi Lessicale
   ### 3.1 Tokenizzazione e Frasi
   - Statistiche di lunghezza frasi (media, mediana, deviazione std)
   - Istogramma distribuzione lunghezza frasi
   - Esempi testuali: frasi più lunghe e più corte
   - Commento interpretativo

   ### 3.2 POS Tagging e Lemmatizzazione
   - Distribuzione POS per disciplina
   - Diversità lessicale (type-token ratio)
   - Esempi testuali: frasi con alta diversità lessicale, lemmi rari
   - Grafici e commento

   ### 3.3 Frequenze e N-grammi
   - Top parole per frequenza (tabella e grafico)
   - Top bigrammi e trigrammi
   - Esempi testuali: frasi contenenti le parole e n-grammi più frequenti
   - Commento sulle espressioni ricorrenti

## 4. Analisi dei Verbi (Sezione Principale)
   ### 4.1 Panoramica dei Verbi
   - Tabella riassuntiva per disciplina
   
   ### 4.2 Verbi Modali
   - Distribuzione e heatmap
   - Classificazione per funzione comunicativa
   - Indice di hedging per disciplina
   - Confronto tra discipline
   - Esempi testuali per ciascuna categoria modale ed epistemica
   - Commento interpretativo

   ### 4.3 Voce Attiva vs Passiva
   - Rapporto attivo/passivo per disciplina
   - Grafico stacked bar
   - Esempi testuali di frasi passive e attive
   - Commento

   ### 4.4 Reporting Verbs (Verbi di Citazione)
   - Distribuzione per disciplina
   - Classificazione per tipo epistemico (evidenza, cautela, posizione, distanza critica, certezza, neutro)
   - Indice di diversità dei reporting verbs per disciplina
   - Esempi testuali per ciascun tipo epistemico
   - Commento interpretativo

## 5. Agency (Chi è il Soggetto?)
   - Distribuzione delle categorie di agency per disciplina
   - Grafici per categoria (autore, dati, impersonale, etc.)
   - Esempi testuali di coppie soggetto–verbo
   - Commento sull'identità accademica e posizionamento epistemologico

## 6. Nominalizzazioni
   - Densità di nominalizzazione per disciplina
   - Top nominalizzazioni più frequenti
   - Esempi testuali: frasi ad alta e bassa densità nominale
   - Commento sul registro accademico

## 7. Coesione e Connettivi Discorsivi
   - Distribuzione dei marcatori per categoria (additivi, avversativi, causali, sequenziali, conclusivi)
   - Indice di diversità dei connettivi per disciplina
   - Esempi testuali: uso dei connettivi e passaggi senza connettivi
   - Commento sulla struttura e maturità del writing

## 8. Formule Accademiche
   - Frequenza e densità delle formule per disciplina
   - Top formule più usate
   - Rapporto formule uniche usate / formule disponibili
   - Esempi testuali delle formule nel contesto
   - Commento sulla scrittura template-driven

## 9. Complessità Sintattica
   - Clausole subordinate per frase (media per disciplina)
   - Profondità dell'albero sintattico (media per disciplina)
   - Istogrammi di distribuzione
   - Esempi testuali: frasi più e meno complesse
   - Commento sui pattern disciplinari

## 10. Parole Chiave (TF-IDF)
   - Top keywords per documento e per disciplina
   - Grafici
   - Esempi testuali: frasi contenenti le top keywords
   - Commento

## 11. Topic Modeling (LDA)
   - Tabella topic → parole chiave
   - Heatmap documenti × topic
   - Topic dominanti per disciplina
   - Frasi rappresentative per ciascun topic
   - Commento sugli argomenti emersi

## 12. Analisi Sintattica (Dipendenze)
   - Distribuzione delle relazioni di dipendenza per disciplina
   - Alberi sintattici di esempio (SVG)
   - Esempi testuali delle principali relazioni di dipendenza
   - Commento

## 13. Similarità tra Documenti
   ### 13.1 Similarità TF-IDF (Coseno)
   - Heatmap di similarità tra discipline
   - Coesione intra-disciplina
   - Commento

   ### 13.2 Sovrapposizione N-grammi (Jaccard)
   - Heatmap Jaccard tra discipline
   - Tabella dei top n-grammi condivisi con frasi di contesto
   - Commento sulle ripetizioni lessicali

   ### 13.3 Similarità tramite Embedding di Frase
   - Heatmap basata sui vettori spaCy (GloVe) tra discipline
   - Confronto con i risultati TF-IDF
   - Commento sulla similarità semantica vs lessicale

   ### 13.4 Confronto tra Metodi di Similarità
   - Tabella riassuntiva per disciplina (media per ciascun metodo)
   - Scatter plot di correlazione tra i tre metodi
   - Commento su convergenze e divergenze tra le metriche

## 14. Word Cloud
   - Word cloud per disciplina e corpus
   - Commento visivo

## 15. Conclusioni
   - Sintesi dei risultati principali
   - Pattern emersi nei diversi tipi di esame e discipline
   - Osservazioni sulla lingua usata nelle trascrizioni (parlanti non nativi in contesto EMI)
   - Indicatori di maturità della scrittura accademica EMI (hedging, reporting verbs, nominalizzazioni, coesione, formule)
```

### Commentary rules

Every section must include a **"Commento"** paragraph (in Italian) that:

- Interprets the numbers and graphs in plain language.
- Highlights notable patterns, anomalies, or differences between disciplines.
- Uses the domain context (university exam transcriptions by non-native English speakers in EMI) to give meaningful interpretation.
- Includes **embedded text examples** (as Markdown blockquotes) drawn from `output/text_examples/` to illustrate key findings with real passages from the documents.
- Is auto-generated via template strings populated with computed statistics (not AI-generated at runtime).

---

## 8. Entry Point (`run_pipeline.py`)

```python
# Pseudocode structure
def main():
    config = load_config("config.yaml")
    
    # Stage 1: Discover
    registry = discover_documents(config)
    
    # Stage 2: Preprocess
    corpus = preprocess_all(registry, config)
    
    # Stage 3-15: Analysis modules (each returns results dict)
    tokenization_results = run_tokenization(corpus, config)      # includes sentence complexity
    morphology_results = run_morphology(corpus, config)
    verb_results = run_verb_analysis(corpus, config)             # modals, passive, reporting verbs
    agency_results = run_agency_analysis(corpus, config)
    nominalization_results = run_nominalization(corpus, config)
    cohesion_results = run_cohesion(corpus, config)
    formula_results = run_academic_formulas(corpus, config)
    frequency_results = run_frequency(corpus, config)
    keyword_results = run_keywords(corpus, config)
    topic_results = run_topic_modeling(corpus, config)
    dependency_results = run_dependency(corpus, config)
    similarity_results = run_similarity(corpus, config)
    
    # Stage 11: Visualizations
    generate_all_visualizations(...)
    
    # Stage 12: Assemble report
    generate_report(all_results, config)
    
    print("Pipeline completata. Report: output/report.md")
```

The script must:

- Be runnable with `python run_pipeline.py`.
- Accept an optional `--config` argument to specify a custom config file path.
- Print progress to stdout (e.g., `[1/8] Scoperta documenti...`, `[2/8] Preprocessing...`).
- Handle errors gracefully: if a single document fails, log the error and continue.
- Print total execution time at the end.

---

## 9. Requirements (`requirements.txt`)

```
spacy>=3.5,<4.0
nltk>=3.8
scikit-learn>=1.2
gensim>=4.3
matplotlib>=3.7
seaborn>=0.12
wordcloud>=1.9
pyyaml>=6.0
```

Post-install steps (document in README):

```bash
python -m spacy download en_core_web_md
python -c "import nltk; nltk.download('punkt'); nltk.download('stopwords'); nltk.download('averaged_perceptron_tagger')"
```

---

## 10. Non-Functional Requirements

- **Performance**: Full pipeline should complete in under 15 minutes for the full corpus (~206 documents across 13 disciplines) on a standard laptop (8GB RAM, no GPU).
- **Memory**: Never load the entire corpus into memory at once if it exceeds 500MB. Process documents in streaming/batched fashion.
- **Logging**: Use Python `logging` module. Log to both console and `output/pipeline.log`.
- **Reproducibility**: Set random seeds for LDA and any stochastic process.
- **Encoding**: All file I/O in UTF-8.
- **Error tolerance**: A failing document must not crash the pipeline. Log and skip.

---

## 11. Deliverables Checklist

- [ ] `config.yaml` — Working default configuration
- [ ] `requirements.txt` — All dependencies
- [ ] `run_pipeline.py` — Entry point that runs the full pipeline
- [ ] `src/discovery.py` — Document discovery module
- [ ] `src/preprocessing.py` — Text preprocessing module
- [ ] `src/tokenization.py` — Tokenization & sentence splitting
- [ ] `src/morphology.py` — POS tagging & lemmatization
- [ ] `src/verb_analysis.py` — Verb analysis (modals, active/passive voice, reporting verbs)
- [ ] `src/agency.py` — Agency analysis (subject–verb semantic roles)
- [ ] `src/nominalization.py` — Nominalization detection and density
- [ ] `src/cohesion.py` — Cohesive devices & discourse marker analysis
- [ ] `src/academic_formulas.py` — Formulaic academic n-gram detection
- [ ] `src/frequency.py` — Word frequency & n-grams
- [ ] `src/keywords.py` — TF-IDF keyword extraction
- [ ] `src/topic_modeling.py` — LDA topic modeling
- [ ] `src/dependency.py` — Dependency parsing & tree visualization (per-discipline)
- [ ] `src/similarity.py` — Discipline-wise text similarity (TF-IDF, Jaccard, embeddings)
- [ ] `src/visualization.py` — All chart/graph generation
- [ ] `src/report.py` — Italian markdown report generator
- [ ] `output/report.md` — Final generated report (in Italian)
- [ ] `output/images/` — All generated figures (PNG + SVG)
- [ ] `output/text_examples/` — Saved text excerpts illustrating all analysis results
- [ ] `output/document_registry.json` — Discovered document structure
- [ ] `output/pipeline.log` — Execution log
- [ ] `README.md` — Setup and usage instructions
