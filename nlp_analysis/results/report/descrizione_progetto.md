# Descrizione del Progetto di Analisi NLP

Questo progetto analizza un corpus di testi accademici in lingua inglese suddivisi per disciplina, con l'obiettivo di caratterizzare le convenzioni linguistiche, retoriche e stilistiche tipiche di ciascun ambito disciplinare. La pipeline è composta da 14 stage sequenziali, orchestrati da `run_pipeline.py`.

---

## Stage 0 — Inizializzazione

### Obiettivo
Preparare l'ambiente di esecuzione prima di qualsiasi analisi, assicurando che le dipendenze esterne siano disponibili e che la struttura di output sia pronta.

### Implementazione
- **NLTK**: scarica i dataset necessari (`punkt`, `stopwords`, `averaged_perceptron_tagger`, `punkt_tab`) se non già presenti nel sistema.
- **spaCy**: carica il modello linguistico configurato (default: `en_core_web_md`) con un limite di lunghezza esteso a 2.000.000 caratteri per gestire documenti molto lunghi. Se il modello non è installato, la pipeline si interrompe con un messaggio esplicativo.
- **Directory di output**: crea la struttura di cartelle `output/images/` e `output/text_examples/`, ciascuna con tre sottodirectory: `per_document/`, `per_discipline/`, `corpus/`.

### Output atteso
- Nessun file di dati, solo struttura di directory e log di avvio.
- **Motivazione**: garantire che tutti gli stage successivi trovino le cartelle già create, evitando errori di accesso al filesystem durante l'esecuzione parallela delle visualizzazioni.

---

## Stage 1 — Discovery dei documenti (`src/discovery.py`)

### Obiettivo
Costruire il registro dei documenti del corpus, associando ogni file `.docx` alla propria disciplina, senza dipendere dalla struttura delle cartelle (che contiene sottodirectory di sessione non allineate alle discipline).

### Implementazione
- Scansione ricorsiva della directory `docs_dir` per tutti i file `.docx`.
- Estrazione del codice disciplina dal nome del file tramite regex: tutto ciò che precede il primo segmento `_AS<numero>` (es. `SCSA_Bon_AS1_P54.docx` → `SCSA_Bon`).
- Applicazione di un mapping opzionale `filename_code_mapping` per normalizzare codici inconsistenti.
- Validazione: confronto tra il numero di file trovati per disciplina e il valore `expected_count` configurato; warning per discipline mancanti o in eccesso.
- Il registro viene salvato in `output/document_registry.json`.

### Output atteso
- **`output/document_registry.json`**: dizionario `{codice_disciplina: [percorso_assoluto, ...]}`.
- **Motivazione**: centralizzare il catalogo dei documenti permette a tutti gli stage successivi di lavorare su una lista consistente e tracciabile. Il JSON su disco serve come audit trail.

---

## Stage 2 — Preprocessing (`src/preprocessing.py`)

### Obiettivo
Trasformare i file `.docx` grezzi in testo pulito e normalizzato, pronto per l'analisi NLP. Nessuna correzione ortografica viene applicata: i refusi originali vengono preservati.

### Implementazione
- Estrazione del testo da ogni `.docx` tramite `python-docx`, limitandosi ai paragrafi (intestazioni, piè di pagina e tabelle sono esclusi per evitare rumore di layout).
- Pipeline di pulizia applicata in sequenza:
  1. Rimozione dei tag XML/HTML residui.
  2. Rimozione dei caratteri non stampabili (mantenendo newline e tab).
  3. Normalizzazione degli spazi bianchi (collasso multipli spazi, riduzione delle righe vuote consecutive a massimo due).
- Ogni documento viene rappresentato come dizionario con chiavi: `id`, `discipline`, `path`, `raw_text`, `clean_text`.

### Output atteso
- **Corpus in memoria**: lista di dizionari documento, passata in cascata a tutti gli stage successivi.
- **Nessun file su disco** in questo stage.
- **Motivazione**: separare il preprocessing dall'analisi permette di modificare la pulizia del testo senza rieseguire le analisi NLP costose.

---

## Stage 3 — Tokenizzazione e analisi delle frasi (`src/tokenization.py`)

### Obiettivo
Misurare la complessità sintattica dei testi tramite statistiche a livello di frase: lunghezza, subordinazione e profondità dell'albero di parsing. Queste metriche riflettono il grado di elaborazione sintattica tipico della prosa accademica.

### Implementazione

**Per ogni documento:**
- Il testo viene processato con spaCy per ottenere la segmentazione in frasi e token.
- Per ogni frase: conteggio token (escludendo punteggiatura e spazi), conteggio delle subordinate clauses (label di dipendenza: `advcl`, `acl`, `relcl`, `ccomp`, `xcomp`), calcolo della profondità massima dell'albero di parsing a partire dal ROOT.
- Metriche aggregate per documento: numero di frasi, numero di token, lunghezza media della frase, media delle subordinate per frase, profondità media dell'albero.

**Per disciplina:**
- Tutte le distribuzioni dei documenti vengono aggregate per calcolare le stesse metriche a livello disciplinare.

**Esempi testuali** (se `save_text_examples: true`):
- Frase più lunga, frase più corta, frase più complessa, frase meno complessa per ogni documento.

### Output atteso
- **Dati in memoria**: `tokenization_results` con sotto-dizionari `per_document` e `per_discipline`.
- **File di testo** in `output/text_examples/per_document/`: `tokenization_longest_sentences.txt`, `tokenization_shortest_sentences.txt`, `tokenization_most_complex.txt`, `tokenization_least_complex.txt`.
- **Motivazione**: la lunghezza media delle frasi e il tasso di subordinazione sono indicatori consolidati della complessità della prosa accademica; confrontarli tra discipline rivela differenze di stile argomentativo.

---

## Stage 4 — POS tagging e lemmatizzazione (`src/morphology.py`)

### Obiettivo
Caratterizzare la struttura morfologica dei testi tramite la distribuzione delle parti del discorso (POS) e misurare la ricchezza lessicale tramite il Type-Token Ratio (TTR). Un alto numero di sostantivi suggerisce nominalizzazione; un alto TTR indica varietà lessicale.

### Implementazione

**Per ogni documento:**
- Conteggio e percentuale di ogni categoria POS (NOUN, VERB, ADJ, ADV, AUX, ecc.).
- Conteggio dei lemmi (escludendo stopword, punteggiatura e token non alfabetici).
- Calcolo del TTR: `lemmi unici / totale token`.
- Top-50 lemmi per frequenza.

**Per disciplina:**
- Somma dei conteggi POS e dei lemmi di tutti i documenti della disciplina.
- TTR disciplinare calcolato come `lemmi unici della disciplina / totale token della disciplina`.

**Esempi testuali** (se `save_text_examples: true`):
- Frase con massimo TTR per documento.
- Lista degli hapax (lemmi con frequenza 1) per documento.

### Output atteso
- **Dati in memoria**: `morphology_results` con `per_document` e `per_discipline`.
- **File di testo** in `output/text_examples/per_document/`: `morphology_high_diversity.txt`, `morphology_rare_lemmas.txt`.
- **Motivazione**: la distribuzione POS è uno degli indicatori più robusti dello stile disciplinare; discipline con alta nominalizzazione (molti NOUN) sono tipicamente più formali e astratte.

---

## Stage 5 — Analisi verbale (`src/verb_analysis.py`)

### Obiettivo
Quantificare tre dimensioni fondamentali della retorica accademica: (1) uso dei verbi modali e il loro valore epistémico, (2) proporzione di costruzioni passive vs. attive, (3) presenza e tipo dei verbi di riporto usati nelle citazioni.

### Implementazione

**Verbi modali:**
- Lista fissa: `can, could, may, might, shall, should, will, would, must, ought, need`.
- Ogni modale viene classificato in categorie funzionali: `ability`, `permission`, `obligation`, `possibility`, `volition`.
- Classificazione epistemica: `hedging` (may/might/could), `strong_claim` (must), `recommendation` (should), `ability` (can).

**Voce passiva:**
- Metodo 1: presenza di `nsubjpass` o `auxpass` tra i figli del verbo (label spaCy).
- Metodo 2: verbo con tag `VBN` che ha come ausiliare "be" con dep `aux` o `auxpass`.
- Calcolo del passive ratio: `passivi / (passivi + attivi)`.

**Verbi di riporto:**
- Lista configurabile in `config.yaml` (`reporting_verbs`).
- Classificazione in tipi: `evidence`, `caution`, `position`, `critical_distance`, `certainty`, `subjective`, `neutral`.

**Per disciplina:** aggregazione di tutti i conteggi dei documenti.

**Esempi testuali** (se `save_text_examples: true`):
- Frasi con ciascun modale, frasi passive, frasi con verbi di riporto per tipo.

### Output atteso
- **Dati in memoria**: `verb_results` con `per_document` e `per_discipline`.
- **File di testo** in `output/text_examples/per_document/`: `verb_modal_{modale}.txt`, `verb_passive.txt`, `verb_reporting_{tipo}.txt`.
- **Motivazione**: i modali di hedging (may/might) e il passive ratio sono marcatori del grado di certezza e dell'attribuzione di responsabilità tipici del registro scientifico; differiscono sistematicamente tra scienze dure e discipline umanistiche.

---

## Stage 6 — Analisi dell'agency (`src/agency.py`)

### Obiettivo
Identificare chi o cosa riveste il ruolo di soggetto grammaticale delle clausole principali, per misurare le scelte retoriche di attribuzione dell'azione: l'autore si espone in prima persona, cita fonti, lascia agire i dati, o usa costruzioni impersonali?

### Implementazione

**Categorie di agency:**
- `author_identity`: soggetto è "I" o "we" → presenza esplicita dell'autore.
- `source_attribution`: soggetto è un'entità PERSON/ORG (NER) o lemma in una lista di parole-fonte (article, paper, study, ecc.) → citazione.
- `data_evidence`: soggetto è un lemma appartenente al dominio dei dati (data, results, findings, ecc.) → i dati parlano.
- `concept_abstraction`: soggetto è NOUN o PROPN non classificato altrove → concetti astratti come agenti.
- `impersonal`: soggetto è "it" → costruzione impersonale.
- `other`: tutto il resto.

**Per ogni token verbale** (ROOT o VERB) con un soggetto `nsubj` o `nsubjpass` identificabile, viene classificata la categoria del soggetto.

**Per disciplina:** aggregazione dei conteggi e calcolo delle percentuali.

### Output atteso
- **Dati in memoria**: `agency_results` con `per_document` e `per_discipline`.
- **File di testo** in `output/text_examples/per_document/`: `agency_{categoria}.txt`.
- **Motivazione**: la distribuzione dell'agency rivela le convenzioni retoriche disciplinari; le scienze naturali tendono a nascondere l'autore (impersonal/data_evidence), le scienze sociali a citare fonti (source_attribution), le humanities a usare la prima persona.

---

## Stage 7 — Nominalizzazioni (`src/nominalization.py`)

### Obiettivo
Misurare la densità di nominalizzazioni, cioè sostantivi derivati da verbi o aggettivi tramite suffissi tipici (-tion, -ment, -ity, -ness, ecc.). La nominalizzazione è un marcatore della prosa accademica formale che comprime eventi in entità.

### Implementazione

**Criteri di rilevamento:**
- Solo token con POS `NOUN`, non stopword, non punteggiatura, alfabetici, lunghezza > 4 caratteri.
- Esclusione di una lista di parole comuni non accademiche (`NON_ACADEMIC_STOPLIST`: question, attention, moment, ecc.).
- Match del suffisso più lungo dalla lista `nominalization_suffixes` configurata in `config.yaml`.

**Metriche per documento:**
- Conteggio totale delle nominalizzazioni rilevate.
- Densità: `nominalizzazioni / totale token × 100`.
- Distribuzione per suffisso e top-20 forme più frequenti.

**Per disciplina:** aggregazione di tutti i conteggi e ricalcolo della densità.

### Output atteso
- **Dati in memoria**: `nominalization_results` con `per_document` e `per_discipline`.
- **File di testo** in `output/text_examples/per_document/`: `nominalization_examples.txt`.
- **Motivazione**: un'alta densità di nominalizzazioni caratterizza la prosa tecnico-scientifica; confrontare le densità tra discipline permette di quantificare il grado di formalizzazione del linguaggio.

---

## Stage 8 — Connettivi discorsivi (`src/cohesion.py`)

### Obiettivo
Rilevare e classificare i connettivi discorsivi (discourse markers) che segnalano le relazioni logiche tra le parti del testo (causa, concessione, contrasto, sequenza, ecc.). La densità e la varietà dei connettivi riflettono la coesione retorica del testo.

### Implementazione

**Rilevamento:**
- I connettivi sono configurati in `config.yaml` (`discourse_markers`), raggruppati per categoria (es. `causali`, `avversativi`, `sequenziali`).
- Per ogni frase (segmentazione semplice su `.!?`) viene cercato ogni connettivo: word-boundary matching per parole singole, substring matching per locuzioni multi-parola.
- Un connettivo può essere trovato più volte nella stessa frase.

**Metriche per documento:**
- Conteggio totale dei connettivi e distribuzione per categoria.
- Densità: `totale connettivi / numero frasi × 100`.
- Diversity index: `connettivi unici trovati / totale occorrenze`.
- Rilevamento di sequenze di ≥ 5 frasi consecutive senza connettivi.

**Per disciplina:** aggregazione dei conteggi, ricalcolo di densità e diversity.

### Output atteso
- **Dati in memoria**: `cohesion_results` con `per_document` e `per_discipline`.
- **File di testo** in `output/text_examples/per_document/`: `cohesion_{categoria}.txt`, `cohesion_no_markers.txt`.
- **Motivazione**: una bassa densità di connettivi può indicare uno stile più assertivo e frammentato (tipico di testi tecnici o scientifici), mentre un'alta varietà di connettivi segnala una struttura argomentativa elaborata.

---

## Stage 9 — Formule accademiche (`src/academic_formulas.py`)

### Obiettivo
Quantificare la presenza di formule lessicalizzate tipiche del discorso accademico (es. "it is worth noting", "in contrast to", "the results suggest"). Queste espressioni fisse codificano funzioni retoriche convenzionali e la loro frequenza misura quanto un testo aderisca alle norme del genere accademico.

### Implementazione

**Rilevamento:**
- Lista di formule configurata in `config.yaml` (`academic_formulas`).
- Ricerca case-insensitive tramite `text.count(formula_lower)` per ogni formula.
- Per ciascuna formula trovata viene estratta la frase contenente (tramite ricerca di confini `.`).

**Metriche per documento:**
- Conteggio totale delle occorrenze di formule.
- Densità: `occorrenze / totale token × 1000` (per mille token).
- Unique formula ratio: `formule distinte trovate / totale formule in lista`.

**Per disciplina:** aggregazione di tutti i conteggi e ricalcolo della densità.

### Output atteso
- **Dati in memoria**: `formula_results` con `per_document` e `per_discipline`.
- **File di testo** in `output/text_examples/per_document/`: `academic_formulas_examples.txt`.
- **Motivazione**: le formule accademiche sono segnali di appartenenza al genere testuale; un'alta unique formula ratio indica un testo che usa un repertorio formulaico ampio e consolidato.

---

## Stage 10 — Frequenze e n-grammi (`src/frequency.py`)

### Obiettivo
Costruire i profili di frequenza lessicale a tre livelli (parole, bigrammi, trigrammi) per identificare le parole e le collocazioni più caratteristiche di ogni documento e disciplina, come base per le visualizzazioni (word cloud, bar chart).

### Implementazione

**Token filtrati:** alfabetici, non stopword, lowercase.

**Per ogni documento:**
- Top-N parole singole, bigrammi e trigrammi per frequenza (N configurabile, default 30).

**Per disciplina:**
- Aggregazione dei Counter di tutti i documenti della disciplina; stessa estrazione top-N.

**Livello corpus:**
- Aggregazione di tutti i documenti; estrazione del top-N globale.

**Esempi testuali** (se `save_text_examples: true`):
- Per ogni documento, la frase contenente la parola più frequente.

### Output atteso
- **Dati in memoria**: `frequency_results` con `per_document`, `per_discipline` e `corpus`.
- **File di testo** in `output/text_examples/per_document/`: `frequency_examples.txt`.
- **Motivazione**: le frequenze assolute rivelano il campo semantico dominante; i bigrammi e trigrammi catturano collocazioni e terminologia tecnica che le parole singole non mostrano.

---

## Stage 11 — Parole chiave TF-IDF (`src/keywords.py`)

### Obiettivo
Estrarre le parole chiave che meglio distinguono ogni documento e ogni disciplina rispetto agli altri, usando TF-IDF. A differenza della frequenza assoluta, TF-IDF penalizza i termini ubiqui nel corpus e valorizza quelli specifici.

### Implementazione

**Per documento:**
- Fitting di un `TfidfVectorizer` (scikit-learn) sull'intero corpus (unigrammi e bigrammi, max 10.000 feature, stopword inglesi, TF sublineare).
- Estrazione dei top-N termini per score TF-IDF per ogni documento (N configurabile, default 20).

**Per disciplina:**
- Concatenazione dei testi di tutti i documenti della disciplina in un unico testo.
- Fitting di un secondo `TfidfVectorizer` sui testi disciplinari aggregati.
- Estrazione dei top-N termini per score.

**Livello corpus:**
- Media delle righe della matrice TF-IDF → top-N termini più importanti nel corpus complessivo.

### Output atteso
- **Dati in memoria**: `keyword_results` con `per_document`, `per_discipline` e `corpus`.
- **File di testo** in `output/text_examples/per_document/`: `keywords_examples.txt`.
- **Motivazione**: le keyword TF-IDF di ogni disciplina costituiscono il suo "vocabolario caratteristico" e sono usate per generare i grafici `tfidf_keywords_{disciplina}.png` che rendono visivamente confrontabili i profili terminologici.

---

## Stage 12 — Topic modeling LDA (`src/topic_modeling.py`)

### Obiettivo
Scoprire automaticamente i macro-temi latenti presenti nel corpus tramite Latent Dirichlet Allocation (LDA), e associare ogni documento e disciplina al tema dominante. Serve a verificare se le discipline si distinguono anche a livello tematico, oltre che stilistico.

### Implementazione

**Tokenizzazione per LDA:**
- Lemmatizzazione con spaCy, rimozione di stopword, punteggiatura e lemmi di lunghezza ≤ 2 caratteri.

**Training LDA (Gensim):**
- Costruzione del dizionario e del corpus Bag-of-Words.
- Filtro sulle estremità: esclusione dei termini troppo rari o troppo frequenti (`no_above=0.95`).
- Parametri configurabili: `lda_num_topics` (default 8), `lda_passes` (default 10), seed fisso 42 per riproducibilità.

**Per documento:**
- Distribuzione di probabilità su tutti i topic; topic dominante con relativa probabilità.

**Per disciplina:**
- Topic dominante come moda dei topic dominanti dei singoli documenti.

**Esempi testuali** (se `save_text_examples: true`):
- Top-5 parole del topic dominante per ogni documento campione.

### Output atteso
- **Dati in memoria**: `topic_results` con `topics`, `per_document`, `per_discipline`, `num_topics`.
- **File di testo** in `output/text_examples/per_document/`: `topic_modeling_examples.txt`.
- **Motivazione**: confrontare il topic dominante tra discipline verifica se i cluster tematici LDA coincidono con i confini disciplinari, oppure se esistono temi trasversali che accomunano discipline diverse.

---

## Stage 13 — Analisi delle dipendenze sintattiche (`src/dependency.py`)

### Obiettivo
Analizzare la struttura sintattica dei testi tramite il dependency parsing di spaCy, raccogliendo la distribuzione delle label di dipendenza (soggetti, oggetti, modificatori, ecc.) e generando visualizzazioni degli alberi di parsing per ispezione qualitativa.

### Implementazione

**Per ogni documento:**
- Parsing del testo con spaCy.
- Conteggio di ogni label di dipendenza (`nsubj`, `dobj`, `amod`, `advmod`, `prep`, ecc.) escludendo spazi.
- Generazione di SVG degli alberi di dipendenza per le prime N frasi (default 3), tramite `displacy.render()` con stile `dep` e layout compatto.
- Gli SVG vengono salvati in `output/images/per_document/{doc_id}_dep_{i}.svg`.

**Per disciplina:**
- Aggregazione dei Counter di label di dipendenza di tutti i documenti; top-20 label più frequenti.

**Esempi testuali** (se `save_text_examples: true`):
- Frase con coordinate (sorgente, numero di frase) per le prime N frasi dei documenti campione.

### Output atteso
- **Dati in memoria**: `dependency_results` con `per_document` e `per_discipline`.
- **SVG** in `output/images/per_document/`: un file per ogni frase campionata (`{doc_id}_dep_{i}.svg`).
- **File di testo** in `output/text_examples/per_document/`: `dependency_examples.txt`.
- **Motivazione**: la distribuzione delle label di dipendenza rivela preferenze sintattiche disciplinari (es. alta frequenza di `amod` suggerisce prosa molto modificata; alta frequenza di `nsubjpass` conferma l'uso del passivo). Gli SVG servono per ispezione manuale qualitativa.

---

## Stage 14a — Similarità tra discipline (`src/similarity.py`)

### Obiettivo
Misurare quanto i testi delle diverse discipline si assomigliano tra loro, usando tre metriche complementari, per identificare cluster di discipline linguisticamente affini e coppie agli antipodi.

### Implementazione

**Testi aggregati:** ogni disciplina viene rappresentata dalla concatenazione dei suoi documenti.

**Metrica 1 — Cosine similarity TF-IDF:**
- Vettorizzazione TF-IDF (max 10.000 feature, stopword inglesi, TF sublineare).
- Matrice coseno N×N tra tutte le discipline.

**Metrica 2 — Jaccard:**
- Jaccard su character n-grammi (default n=3): misura la sovrapposizione a livello di sequenze di caratteri (stile superficiale).
- Jaccard su word n-grammi (default: bigrammi e trigrammi): misura la sovrapposizione di collocazioni.

**Metrica 3 — Embedding similarity (opzionale):**
- Se `use_sentence_embeddings: true`, vettore medio spaCy (primi 50.000 caratteri per disciplina).
- Cosine similarity tra vettori disciplinari.

**Summary:** identificazione della coppia di discipline più simile (valore massimo fuori dalla diagonale della matrice coseno).

### Output atteso
- **Dati in memoria**: `similarity_results` con `disciplines`, `cosine_similarity`, `jaccard_char`, `jaccard_word`, `embedding_similarity`.
- **File di testo** in `output/text_examples/corpus/`: `similarity_examples.txt`.
- **Motivazione**: le matrici di similarità alimentano le heatmap nei report e permettono di rispondere a domande come "quali discipline condividono più vocabolario?" o "quali sono le più distanti stilisticamente?".

---

## Stage 14b — Visualizzazioni (`src/visualization.py`)

### Obiettivo
Trasformare tutti i risultati numerici in grafici, rendendoli leggibili e confrontabili senza dover interpretare i dati grezzi.

### Implementazione

Tutti i grafici usano la palette seaborn `muted`, titoli in italiano, risoluzione 150 DPI e layout automatico. Le visualizzazioni prodotte includono:

**Per disciplina** (`output/images/per_discipline/`):
- `sentence_length_hist_{disc}.png` — istogramma della distribuzione della lunghezza delle frasi.
- `subordinate_hist_{disc}.png` — istogramma delle clausole subordinate per frase.
- `pos_distribution_{disc}.png` — bar chart della distribuzione POS.
- `word_frequency_{disc}.png` — bar chart delle top parole per frequenza.
- `wordcloud_{disc}.png` — word cloud basato sulle frequenze.
- `tfidf_keywords_{disc}.png` — bar chart delle top keyword TF-IDF.
- `dep_labels_{disc}.png` — bar chart delle top label di dipendenza.
- `modal_verbs_{disc}.png` — distribuzione dei verbi modali.
- `passive_ratio_{disc}.png` — confronto passivo/attivo.
- `agency_{disc}.png` — distribuzione delle categorie di agency.
- `nominalization_density_{disc}.png` — densità di nominalizzazioni.
- `cohesion_markers_{disc}.png` — distribuzione dei connettivi per categoria.

**Corpus** (`output/images/corpus/`):
- Heatmap della similarità coseno tra discipline.
- Confronti trasversali tra discipline (box plot, scatter, bar comparativi).
- Word cloud e frequenze a livello corpus.

**Per documento** (`output/images/per_document/`):
- SVG degli alberi di dipendenza (generati dallo Stage 13).

### Output atteso
- **File `.png`** nelle directory `per_discipline/` e `corpus/` per ogni metrica visualizzata.
- **File `.svg`** in `per_document/` per i dependency tree.
- **Motivazione**: le immagini sono la forma di output primaria per i report; rendono immediatamente visibili differenze che nei dati grezzi richiederebbero lunghe tabelle comparative.

---

## Salvataggio dei risultati (`src/results_writer.py`)

Al termine di tutti gli stage, tutti i risultati vengono serializzati in JSON nella directory `results/`, organizzati per task e per livello (per_document, per_discipline, corpus), garantendo la riproducibilità e la possibilità di analisi post-hoc senza rieseguire la pipeline.
