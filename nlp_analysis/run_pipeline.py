"""
run_pipeline.py – Single entry point for the NLP analysis pipeline.

Usage:
    python run_pipeline.py
    python run_pipeline.py --config path/to/config.yaml
"""

import argparse
import logging
import sys
import time
from pathlib import Path


# ── Config loader ─────────────────────────────────────────────────────────────

def load_config(path: str) -> dict:
    try:
        import yaml
    except ImportError:
        print("ERROR: PyYAML not installed. Run: pip install pyyaml")
        sys.exit(1)
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


# ── Logging setup ─────────────────────────────────────────────────────────────

def setup_logging(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    log_path = output_dir / "pipeline.log"
    fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    handlers = [
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(log_path, encoding="utf-8"),
    ]
    logging.basicConfig(level=logging.INFO, format=fmt, handlers=handlers)


# ── Output directory setup ────────────────────────────────────────────────────

def ensure_output_dirs(output_dir: Path) -> None:
    for subdir in [
        "images/per_document",
        "images/per_discipline",
        "images/corpus",
        "text_examples/per_document",
        "text_examples/per_discipline",
        "text_examples/corpus",
    ]:
        (output_dir / subdir).mkdir(parents=True, exist_ok=True)


# ── NLTK data download ────────────────────────────────────────────────────────

def ensure_nltk_data() -> None:
    import nltk
    for resource in ["punkt", "stopwords", "averaged_perceptron_tagger", "punkt_tab"]:
        try:
            nltk.data.find(f"tokenizers/{resource}" if resource.startswith("punkt") else f"corpora/{resource}")
        except LookupError:
            try:
                nltk.download(resource, quiet=True)
            except Exception:
                pass


# ── spaCy model loader ────────────────────────────────────────────────────────

def load_spacy_model(model_name: str):
    try:
        import spacy
        nlp = spacy.load(model_name)
        # Increase max length for large documents
        nlp.max_length = 2_000_000
        return nlp
    except OSError:
        logging.getLogger(__name__).error(
            "spaCy model '%s' not found. Run: python -m spacy download %s",
            model_name, model_name,
        )
        sys.exit(1)


# ── Progress printer ──────────────────────────────────────────────────────────

def step(n: int, total: int, label: str) -> None:
    print(f"\n[{n}/{total}] {label}...", flush=True)


# ── Results saver ─────────────────────────────────────────────────────────────

def _save_all_results(all_results: dict, config: dict) -> None:
    from src.results_writer import save_all_results
    save_all_results(all_results, config)


# ── Main pipeline ─────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="NLP Analysis Pipeline — Future of English")
    parser.add_argument("--config", default="config.yaml", help="Path to config.yaml")
    args = parser.parse_args()

    start_time = time.time()

    # ── Load config ────────────────────────────────────────────────────────────
    config = load_config(args.config)
    output_dir = Path(config["output_dir"]).resolve()
    setup_logging(output_dir)
    ensure_output_dirs(output_dir)
    logger = logging.getLogger("pipeline")
    logger.info("Config caricato da '%s'.", args.config)

    TOTAL_STEPS = 14

    # ── NLTK ───────────────────────────────────────────────────────────────────
    step(0, TOTAL_STEPS, "Inizializzazione NLTK")
    ensure_nltk_data()

    # ── spaCy ──────────────────────────────────────────────────────────────────
    step(0, TOTAL_STEPS, "Caricamento modello spaCy")
    nlp = load_spacy_model(config.get("spacy_model", "en_core_web_md"))
    logger.info("Modello spaCy caricato: %s", config.get("spacy_model"))

    # ── Stage 1: Discovery ────────────────────────────────────────────────────
    step(1, TOTAL_STEPS, "Scoperta documenti")
    from src.discovery import discover_documents
    registry = discover_documents(config)
    logger.info("Registry: %d documenti in %d discipline.", sum(len(v) for v in registry.values()), len(registry))

    # ── Stage 2: Preprocessing ─────────────────────────────────────────────────
    step(2, TOTAL_STEPS, "Preprocessing")
    from src.preprocessing import preprocess_all
    corpus = preprocess_all(registry, config)
    logger.info("Corpus preprocessato: %d documenti.", len(corpus))

    if not corpus:
        logger.warning("Nessun documento disponibile. Il report sarà vuoto.")

    # ── Stage 3: Tokenisation ──────────────────────────────────────────────────
    step(3, TOTAL_STEPS, "Tokenizzazione e analisi frasi")
    from src.tokenization import run_tokenization
    try:
        tokenization_results = run_tokenization(corpus, config, nlp)
    except Exception as exc:
        logger.error("Tokenizzazione fallita: %s", exc)
        tokenization_results = {}

    # ── Stage 4: Morphology ────────────────────────────────────────────────────
    step(4, TOTAL_STEPS, "POS tagging e lemmatizzazione")
    from src.morphology import run_morphology
    try:
        morphology_results = run_morphology(corpus, config, nlp)
    except Exception as exc:
        logger.error("Morfologia fallita: %s", exc)
        morphology_results = {}

    # ── Stage 5: Verb analysis ─────────────────────────────────────────────────
    step(5, TOTAL_STEPS, "Analisi verbi (modali, passivo, citazione)")
    from src.verb_analysis import run_verb_analysis
    try:
        verb_results = run_verb_analysis(corpus, config, nlp)
    except Exception as exc:
        logger.error("Analisi verbi fallita: %s", exc)
        verb_results = {}

    # ── Stage 6: Agency ────────────────────────────────────────────────────────
    step(6, TOTAL_STEPS, "Analisi agency (soggetti grammaticali)")
    from src.agency import run_agency_analysis
    try:
        agency_results = run_agency_analysis(corpus, config, nlp)
    except Exception as exc:
        logger.error("Analisi agency fallita: %s", exc)
        agency_results = {}

    # ── Stage 7: Nominalization ────────────────────────────────────────────────
    step(7, TOTAL_STEPS, "Rilevamento nominalizzazioni")
    from src.nominalization import run_nominalization
    try:
        nominalization_results = run_nominalization(corpus, config, nlp)
    except Exception as exc:
        logger.error("Nominalizzazioni fallite: %s", exc)
        nominalization_results = {}

    # ── Stage 8: Cohesion ──────────────────────────────────────────────────────
    step(8, TOTAL_STEPS, "Analisi connettivi discorsivi")
    from src.cohesion import run_cohesion
    try:
        cohesion_results = run_cohesion(corpus, config)
    except Exception as exc:
        logger.error("Coesione fallita: %s", exc)
        cohesion_results = {}

    # ── Stage 9: Academic formulas ─────────────────────────────────────────────
    step(9, TOTAL_STEPS, "Rilevamento formule accademiche")
    from src.academic_formulas import run_academic_formulas
    try:
        formula_results = run_academic_formulas(corpus, config)
    except Exception as exc:
        logger.error("Formule accademiche fallite: %s", exc)
        formula_results = {}

    # ── Stage 10: Frequency ────────────────────────────────────────────────────
    step(10, TOTAL_STEPS, "Analisi frequenze e n-grammi")
    from src.frequency import run_frequency
    try:
        frequency_results = run_frequency(corpus, config, nlp)
    except Exception as exc:
        logger.error("Frequenze fallite: %s", exc)
        frequency_results = {}

    # ── Stage 11: Keywords ─────────────────────────────────────────────────────
    step(11, TOTAL_STEPS, "Estrazione parole chiave TF-IDF")
    from src.keywords import run_keywords
    try:
        keyword_results = run_keywords(corpus, config)
    except Exception as exc:
        logger.error("Keywords fallite: %s", exc)
        keyword_results = {}

    # ── Stage 12: Topic modeling ───────────────────────────────────────────────
    step(12, TOTAL_STEPS, "Topic modeling LDA")
    from src.topic_modeling import run_topic_modeling
    try:
        topic_results = run_topic_modeling(corpus, config, nlp)
    except Exception as exc:
        logger.error("Topic modeling fallito: %s", exc)
        topic_results = {}

    # ── Stage 13: Dependency ───────────────────────────────────────────────────
    step(13, TOTAL_STEPS, "Analisi delle dipendenze sintattiche")
    from src.dependency import run_dependency
    try:
        dependency_results = run_dependency(corpus, config, nlp)
    except Exception as exc:
        logger.error("Dependency parsing fallito: %s", exc)
        dependency_results = {}

    # ── Stage 14a: Similarity ──────────────────────────────────────────────────
    step(14, TOTAL_STEPS, "Analisi similarità tra discipline")
    from src.similarity import run_similarity
    try:
        similarity_results = run_similarity(corpus, config, nlp)
    except Exception as exc:
        logger.error("Similarità fallita: %s", exc)
        similarity_results = {}

    # ── Stage 14b: Visualizations ─────────────────────────────────────────────
    print(f"\n[VIS] Generazione visualizzazioni...", flush=True)
    from src.visualization import generate_all_visualizations
    all_results = {
        "registry": registry,
        "tokenization": tokenization_results,
        "morphology": morphology_results,
        "verb_analysis": verb_results,
        "agency": agency_results,
        "nominalization": nominalization_results,
        "cohesion": cohesion_results,
        "academic_formulas": formula_results,
        "frequency": frequency_results,
        "keywords": keyword_results,
        "topic_modeling": topic_results,
        "dependency": dependency_results,
        "similarity": similarity_results,
    }
    try:
        generate_all_visualizations(all_results, config)
    except Exception as exc:
        logger.error("Visualizzazioni fallite: %s", exc)

    # ── Save results ──────────────────────────────────────────────────────────
    print(f"\n[SAVE] Salvataggio risultati...", flush=True)
    _save_all_results(all_results, config)

    # ── Done ───────────────────────────────────────────────────────────────────
    elapsed = time.time() - start_time
    minutes, seconds = divmod(int(elapsed), 60)
    results_dir = Path(config.get("results_dir", "./results")).resolve()
    print(f"\n{'='*60}")
    print(f"Pipeline completata in {minutes}m {seconds}s.")
    print(f"Risultati: {results_dir}")
    print(f"Log:       {output_dir / 'pipeline.log'}")
    print(f"{'='*60}\n")
    logger.info("Pipeline completata in %.1f secondi.", elapsed)


if __name__ == "__main__":
    main()
