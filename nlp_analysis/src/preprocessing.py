"""
preprocessing.py – Load, clean and normalise raw .docx documents.

Text is extracted from each .docx using python-docx (paragraph text only;
tables, headers and footers are skipped to avoid layout noise).
No spell-checking or error correction is applied — typos are preserved.
"""

import logging
import re
import unicodedata
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


def _read_docx(path: Path) -> str:
    """Extract plain text from a .docx file using python-docx."""
    try:
        from docx import Document  # python-docx
    except ImportError:
        raise ImportError("python-docx is required. Run: pip install python-docx")

    doc = Document(str(path))
    paragraphs = [para.text for para in doc.paragraphs if para.text.strip()]
    return "\n".join(paragraphs)


def _strip_non_printable(text: str) -> str:
    """Remove non-printable / control characters while keeping newlines and tabs."""
    result = []
    for ch in text:
        cat = unicodedata.category(ch)
        if ch in ("\n", "\t", "\r") or cat[0] != "C":
            result.append(ch)
    return "".join(result)


def _strip_tags(text: str) -> str:
    """Remove any XML/HTML-like tags of the form <...>."""
    return re.sub(r"<[^>]+>", "", text)


def _normalise_whitespace(text: str) -> str:
    """Collapse multiple spaces; normalise multiple blank lines to at most two."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    lines = [line.strip() for line in text.split("\n")]
    return "\n".join(lines).strip()


def preprocess_document(
    path: str, discipline: str, config: dict
) -> Optional[Dict]:
    """
    Load and clean a single .docx document.

    Returns a dict with keys: id, discipline, path, raw_text, clean_text
    or None on error.
    """
    p = Path(path)
    doc_id = p.stem
    try:
        raw_text = _read_docx(p)
    except Exception as exc:
        logger.error("Cannot read '%s': %s – skipping.", path, exc)
        return None

    if not raw_text.strip():
        logger.warning("Document '%s' appears to be empty – skipping.", path)
        return None

    clean_text = _strip_tags(raw_text)
    clean_text = _strip_non_printable(clean_text)
    clean_text = _normalise_whitespace(clean_text)

    return {
        "id": doc_id,
        "discipline": discipline,
        "path": str(p.resolve()),
        "raw_text": raw_text,
        "clean_text": clean_text,
    }


def preprocess_all(registry: dict, config: dict) -> List[Dict]:
    """
    Preprocess every document in the registry.

    Parameters
    ----------
    registry : {discipline_key: [path, ...]}
    config   : pipeline config dict

    Returns
    -------
    corpus : list of document dicts
    """
    corpus: List[Dict] = []
    total_docs = sum(len(v) for v in registry.values())
    logger.info("Preprocessing %d document(s)…", total_docs)

    for discipline, paths in sorted(registry.items()):
        for path in sorted(paths):
            doc = preprocess_document(path, discipline, config)
            if doc is None:
                continue
            corpus.append(doc)
            logger.debug("Preprocessed '%s' (%s).", doc["id"], discipline)

    logger.info(
        "Preprocessing complete: %d/%d documents loaded successfully.",
        len(corpus), total_docs,
    )
    return corpus
