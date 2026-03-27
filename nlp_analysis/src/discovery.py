"""
discovery.py – Scans docs_dir for *.docx files, builds document registry,
validates against expected counts, saves registry JSON.

Discipline code is extracted from the filename using the pattern:
    <DISCIPLINE_CODE>_AS<number>_...
e.g. SCSA_Bon_AS1_P54.docx → SCSA_Bon
     ELClass_Zot_AS2_P158.docx → ELClass_Zot

An optional `filename_code_mapping` in config can normalise inconsistent
prefixes (e.g. ALSPS_Zot → ELSPS_Zot).
"""

import json
import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

# Regex: capture everything before the first _AS<digit> segment
_DISC_RE = re.compile(r'^(.+?)_AS\d', re.IGNORECASE)


def _extract_discipline(stem: str, mapping: dict) -> str:
    """
    Extract discipline code from a filename stem.

    Parameters
    ----------
    stem    : filename without extension, e.g. "SCSA_Bon_AS1_P54"
    mapping : {raw_code: canonical_code} from config

    Returns
    -------
    Canonical discipline code, or "_ungrouped" if pattern not matched.
    """
    m = _DISC_RE.match(stem)
    if not m:
        return "_ungrouped"
    code = m.group(1).strip()  # strip accidental whitespace (e.g. "CLA_Pol _AS1")
    return mapping.get(code, code)


def discover_documents(config: dict) -> dict:
    """
    Recursively scan docs_dir for *.docx files.

    The discipline key is extracted from each filename rather than from
    the folder structure, because the actual corpus uses nested
    instructor/session subdirectories that do not map 1-to-1 to disciplines.

    Returns
    -------
    registry : dict
        { discipline_code: [absolute_path_str, ...] }
    """
    docs_dir = Path(config["docs_dir"]).resolve()
    output_dir = Path(config["output_dir"]).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    ext = config.get("file_extension", "docx").lstrip(".")
    mapping: dict = config.get("filename_code_mapping", {})

    if not docs_dir.exists():
        logger.warning("docs_dir '%s' does not exist – returning empty registry.", docs_dir)
        registry: dict = {}
        _save_registry(registry, output_dir)
        return registry

    all_files = sorted(docs_dir.rglob(f"*.{ext}"))
    logger.info("Found %d *.%s files under '%s'.", len(all_files), ext, docs_dir)

    registry: dict = {}
    for path in all_files:
        code = _extract_discipline(path.stem, mapping)
        registry.setdefault(code, [])
        registry[code].append(str(path))

    # Log per-discipline counts
    for key, paths in sorted(registry.items()):
        logger.info("  %-20s → %d file(s)", key, len(paths))

    # Validate against expected_count from config
    disciplines_meta = config.get("disciplines", {})
    for key, paths in registry.items():
        if key in disciplines_meta:
            expected = disciplines_meta[key].get("expected_count")
            actual = len(paths)
            if expected is not None and actual != expected:
                logger.warning(
                    "Discipline '%s': expected %d files, found %d.",
                    key, expected, actual,
                )
        elif key != "_ungrouped":
            logger.warning(
                "Discipline key '%s' found in files but not in config.disciplines.", key
            )

    for key in disciplines_meta:
        if key not in registry:
            expected = disciplines_meta[key].get("expected_count", 0)
            if expected > 0:
                logger.warning(
                    "Discipline '%s' expected %d file(s) but no files found.", key, expected
                )

    total = sum(len(v) for v in registry.values())
    logger.info(
        "Registry summary: %d total files across %d discipline(s).",
        total, len(registry),
    )

    _save_registry(registry, output_dir)
    return registry


def _save_registry(registry: dict, output_dir: Path) -> None:
    """Persist the registry to output_dir/document_registry.json."""
    out_path = output_dir / "document_registry.json"
    try:
        with open(out_path, "w", encoding="utf-8") as fh:
            json.dump(registry, fh, indent=2, ensure_ascii=False)
        logger.info("Document registry saved to '%s'.", out_path)
    except OSError as exc:
        logger.error("Could not save document registry: %s", exc)
