"""
ingest_pdfs.py
==============
Ingests the five Theravāda Vinaya + Abhidhamma PDFs into JSONL
compatible with the darshana-graph / buddhism.json schema.

Outputs one JSONL file per source, plus a combined tipitaka_extended.jsonl.

Schema per record (matches darshana-graph buddhism.json):
  id            unique string
  pitaka        vinaya | abhidhamma
  source        source identifier (e.g. "brahmali_vinaya", "bodhi_sangaha")
  book          human book name
  segment_id    source:position
  position      int, paragraph index within source
  text          English text (or pali for Pali-only sources)
  language      en | pali
  translator    brahmali | bodhi | narada | nandamalabhivamsa
  license       CC0 | free_distribution | bps_copyright
  tradition     theravada
  pitaka_note   brief annotation on scope

Usage:
  python ingest_pdfs.py --vinaya /path/to/brahmali_vinaya.pdf
  python ingest_pdfs.py --all --pdf-dir /path/to/pdfs/
  python ingest_pdfs.py --all  # uses default paths from config below
"""

import json
import os
import re
import argparse
import subprocess
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

# ── Default PDF paths ── edit these to match your local paths ──────────────
DEFAULT_PATHS = {
    "brahmali_vinaya":    "Theravāda-Collection-on-Monastic-Law-brahmali-2026-04-30-1.pdf",
    "bodhi_sangaha":      "bp304s_Bfodhi_Comprehensive_Manual_of_Abhidhamma.pdf",
    "narada_sangaha":     "abhidhamma.pdf",
    "nandamalabhivamsa":  "fundamentalabhidhamma.pdf",
}

OUTPUT_DIR = "output"

# ── Source metadata ────────────────────────────────────────────────────────
@dataclass
class SourceMeta:
    key: str
    pitaka: str
    book: str
    translator: str
    language: str
    license: str
    tradition: str
    pitaka_note: str
    # Pages to skip at start (front matter) and end (back matter/index)
    skip_start_pages: int = 0
    skip_end_pages: int = 0
    # Min paragraph word count to keep (filters headers, page numbers)
    min_words: int = 8

SOURCE_META = {
    "brahmali_vinaya": SourceMeta(
        key="brahmali_vinaya",
        pitaka="vinaya",
        book="Theravāda Collection on Monastic Law",
        translator="brahmali",
        language="en",
        license="CC0",
        tradition="theravada",
        pitaka_note="Complete Vinaya Piṭaka: Bhikkhu + Bhikkhunī Vibhaṅga, Khandhakas, Parivāra. "
                    "Brahmali 2026 translation. Newest available English rendering.",
        skip_start_pages=10,   # title, TOC, preface
        skip_end_pages=10,
        min_words=8,
    ),
    "bodhi_sangaha": SourceMeta(
        key="bodhi_sangaha",
        pitaka="abhidhamma",
        book="A Comprehensive Manual of Abhidhamma (Abhidhammattha Saṅgaha)",
        translator="bodhi",
        language="en",
        license="bps_copyright",   # BPS © 1993/2007, free distribution
        tradition="theravada",
        pitaka_note="Translation and commentary of Anuruddha's Abhidhammattha Saṅgaha (11th c.). "
                    "Covers all 9 chapters: citta, cetasika, miscellaneous, thought process, "
                    "matter, cosmology, categories, dependent origination, mental culture. "
                    "Secondary/summary source, not root Abhidhamma Piṭaka.",
        skip_start_pages=8,
        skip_end_pages=5,
        min_words=8,
    ),
    "narada_sangaha": SourceMeta(
        key="narada_sangaha",
        pitaka="abhidhamma",
        book="A Manual of Abhidhamma (Abhidhammattha Saṅgaha) — Narada",
        translator="narada",
        language="en",
        license="free_distribution",   # Buddhist Missionary Society
        tradition="theravada",
        pitaka_note="Earlier translation of same Saṅgaha by Narada Maha Thera (1956/1975). "
                    "Bilingual: Pali verses + English translation + notes. "
                    "Use alongside Bodhi for translation comparison.",
        skip_start_pages=15,
        skip_end_pages=5,
        min_words=8,
    ),
    "nandamalabhivamsa": SourceMeta(
        key="nandamalabhivamsa",
        pitaka="abhidhamma",
        book="Fundamental Abhidhamma Part I — Nandamālābhivaṃsa",
        translator="nandamalabhivamsa",
        language="en",
        license="free_distribution",
        tradition="theravada",
        pitaka_note="Burmese scholastic teaching manual (Sagaing Hills). "
                    "Covers citta, cetasika, rūpa only (first three ultimate realities). "
                    "Highly structured with enumeration tables.",
        skip_start_pages=5,
        skip_end_pages=3,
        min_words=6,   # shorter because of table-style content
    ),
}

# ── Text extraction ────────────────────────────────────────────────────────

def extract_text_pdftotext(pdf_path: str, first_page: int, last_page: int) -> str:
    """Use pdftotext (poppler) for extraction. Best for prose PDFs."""
    cmd = ["pdftotext", "-f", str(first_page), "-l", str(last_page),
           "-enc", "UTF-8", pdf_path, "-"]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    return result.stdout

def get_page_count(pdf_path: str) -> int:
    result = subprocess.run(["pdfinfo", pdf_path], capture_output=True, text=True)
    for line in result.stdout.splitlines():
        if line.startswith("Pages:"):
            return int(line.split(":")[1].strip())
    return 0

# ── Paragraph splitting and cleaning ──────────────────────────────────────

# Patterns to drop regardless
JUNK_PATTERNS = [
    re.compile(r'^\s*\d+\s*$'),                          # bare page numbers
    re.compile(r'^\s*[ivxlcdmIVXLCDM]+\s*$'),            # roman numeral pages
    re.compile(r'^\s*\f\s*$'),                            # form-feed only
    re.compile(r'^(table of contents|contents|index|bibliography|references)\s*$',
               re.IGNORECASE),
    re.compile(r'^\s*\.{4,}\s*\d*\s*$'),                 # TOC dotted lines
]

def is_junk(para: str) -> bool:
    stripped = para.strip()
    for pat in JUNK_PATTERNS:
        if pat.match(stripped):
            return True
    return False

def clean_paragraph(para: str) -> str:
    """Normalise whitespace, remove form feeds."""
    text = para.replace('\f', ' ').replace('\r', ' ')
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

def split_paragraphs(raw_text: str, min_words: int = 8) -> list[str]:
    """
    Split on blank lines. Each paragraph is cleaned and filtered.
    Returns list of paragraph strings.
    """
    raw_paras = re.split(r'\n\s*\n', raw_text)
    result = []
    for p in raw_paras:
        p = clean_paragraph(p)
        if not p:
            continue
        if is_junk(p):
            continue
        word_count = len(p.split())
        if word_count < min_words:
            continue
        result.append(p)
    return result

# ── Section detection ──────────────────────────────────────────────────────

# Heuristic: short all-caps or title-case lines that start a section
SECTION_HEADER_RE = re.compile(
    r'^(chapter|part|book|section|§|\d+\.|[IVXLCDM]+\.)\b',
    re.IGNORECASE
)

def detect_section(para: str) -> Optional[str]:
    """Return section header string if this paragraph looks like a heading."""
    lines = [l.strip() for l in para.strip().splitlines() if l.strip()]
    if not lines:
        return None
    first = lines[0]
    if len(first.split()) <= 8 and SECTION_HEADER_RE.match(first):
        return first
    return None

# ── Main ingestion ─────────────────────────────────────────────────────────

def ingest_pdf(pdf_path: str, meta: SourceMeta) -> list[dict]:
    """Extract and segment a PDF. Returns list of record dicts."""
    if not os.path.exists(pdf_path):
        print(f"  ERROR: file not found: {pdf_path}")
        return []

    total_pages = get_page_count(pdf_path)
    if total_pages == 0:
        print(f"  ERROR: could not read page count for {pdf_path}")
        return []

    first_page = meta.skip_start_pages + 1
    last_page  = total_pages - meta.skip_end_pages
    print(f"  Pages: {total_pages} total, extracting {first_page}–{last_page}")

    raw = extract_text_pdftotext(pdf_path, first_page, last_page)
    paragraphs = split_paragraphs(raw, min_words=meta.min_words)
    print(f"  → {len(paragraphs)} paragraphs extracted")

    records = []
    current_section = ""
    for pos, para in enumerate(paragraphs, 1):
        section = detect_section(para)
        if section:
            current_section = section

        record = {
            "id":           f"{meta.key}:{pos}",
            "pitaka":       meta.pitaka,
            "source":       meta.key,
            "book":         meta.book,
            "section":      current_section,
            "segment_id":   f"{meta.key}:{pos}",
            "position":     pos,
            "text":         para,
            "language":     meta.language,
            "translator":   meta.translator,
            "license":      meta.license,
            "tradition":    meta.tradition,
            "pitaka_note":  meta.pitaka_note,
            "commentaries": [],   # matches darshana-graph schema
        }
        records.append(record)

    return records

# ── Stats ──────────────────────────────────────────────────────────────────

def print_stats(records: list[dict], source_key: str):
    if not records:
        return
    lengths = [len(r["text"]) for r in records]
    words   = [len(r["text"].split()) for r in records]
    print(f"  {source_key}: {len(records)} segments | "
          f"chars: min={min(lengths)} med={sorted(lengths)[len(lengths)//2]} max={max(lengths)} | "
          f"words: min={min(words)} med={sorted(words)[len(words)//2]} max={max(words)}")

# ── Entry point ────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--pdf-dir", default=".",
                        help="Directory containing the PDFs")
    parser.add_argument("--output-dir", default=OUTPUT_DIR)
    parser.add_argument("--vinaya",         action="store_true")
    parser.add_argument("--bodhi",          action="store_true")
    parser.add_argument("--narada",         action="store_true")
    parser.add_argument("--nandamalabhivamsa", action="store_true")
    parser.add_argument("--all",            action="store_true",
                        help="Process all four sources")
    # Override individual PDF paths
    parser.add_argument("--brahmali-vinaya-pdf",    default=None)
    parser.add_argument("--bodhi-pdf",              default=None)
    parser.add_argument("--narada-pdf",             default=None)
    parser.add_argument("--nandamalabhivamsa-pdf",  default=None)

    args = parser.parse_args()
    os.makedirs(args.output_dir, exist_ok=True)

    # Resolve which sources to process
    to_process = []
    if args.all or args.vinaya:         to_process.append("brahmali_vinaya")
    if args.all or args.bodhi:          to_process.append("bodhi_sangaha")
    if args.all or args.narada:         to_process.append("narada_sangaha")
    if args.all or args.nandamalabhivamsa: to_process.append("nandamalabhivamsa")

    if not to_process:
        parser.print_help()
        return

    # Path resolution priority: explicit arg > pdf_dir/default > cwd/default
    path_overrides = {
        "brahmali_vinaya":   args.brahmali_vinaya_pdf,
        "bodhi_sangaha":     args.bodhi_pdf,
        "narada_sangaha":    args.narada_pdf,
        "nandamalabhivamsa": args.nandamalabhivamsa_pdf,
    }

    all_records = []
    for key in to_process:
        meta = SOURCE_META[key]
        override = path_overrides.get(key)
        if override:
            pdf_path = override
        else:
            pdf_path = os.path.join(args.pdf_dir, DEFAULT_PATHS[key])
            if not os.path.exists(pdf_path):
                # Try current directory
                pdf_path = DEFAULT_PATHS[key]

        print(f"\n[{key}] {pdf_path}")
        records = ingest_pdf(pdf_path, meta)
        if not records:
            continue

        print_stats(records, key)

        # Write per-source JSONL
        out_path = os.path.join(args.output_dir, f"{key}.jsonl")
        with open(out_path, "w", encoding="utf-8") as f:
            for r in records:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"  Written: {out_path}")

        all_records.extend(records)

    # Write combined
    if len(to_process) > 1 and all_records:
        combined_path = os.path.join(args.output_dir, "tipitaka_extended.jsonl")
        with open(combined_path, "w", encoding="utf-8") as f:
            for r in all_records:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"\nCombined: {combined_path} ({len(all_records)} total segments)")

        # Summary table
        print("\n=== Summary ===")
        from collections import Counter
        by_source = Counter(r["source"] for r in all_records)
        by_pitaka = Counter(r["pitaka"] for r in all_records)
        for src, count in sorted(by_source.items()):
            print(f"  {src:35s} {count:6d} segments")
        print(f"  {'---':35s} {'------'}")
        for pit, count in sorted(by_pitaka.items()):
            print(f"  {'  pitaka='+pit:35s} {count:6d}")
        print(f"  {'  TOTAL':35s} {len(all_records):6d}")

if __name__ == "__main__":
    main()
