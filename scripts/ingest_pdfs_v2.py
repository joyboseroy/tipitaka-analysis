"""
ingest_pdfs_v2.py
=================
Ingests all Vinaya + Abhidhamma PDFs into JSONL compatible with the
darshana-graph / buddhism.json schema.

SOURCES HANDLED:
  Vinaya — Theravāda:
    brahmali_v1..v6   Brahmali 2026, vols 1-6, CC0
    horner_v1         I.B. Horner PTS 1938, vol 1 (Suttavibhaṅga monks)

  Vinaya — Cross-tradition:
    dharmaguptaka     Dharmaguptaka Vinaya Bhikshu Posadha & Rites (Chinese)
    mulasarvastivada  Mūlasarvāstivāda Vinaya Toh 1-6, 84000 (Tibetan)

  Abhidhamma — Theravāda:
    bodhi_sangaha     Bodhi Comprehensive Manual (Saṅgaha), BPS 2007
    narada_sangaha    Narada Manual of Abhidhamma (Saṅgaha), 1956
    nandamalabhivamsa Fundamental Abhidhamma Pt I, Sagaing Hills

USAGE — run everything at once:
  python3 ingest_pdfs_v2.py --all --pdf-dir /path/to/pdfs --output-dir output

USAGE — run specific sources:
  python3 ingest_pdfs_v2.py --brahmali-all --pdf-dir . --output-dir output
  python3 ingest_pdfs_v2.py --horner --dharmaguptaka --mulasarvastivada --pdf-dir .
  python3 ingest_pdfs_v2.py --abhidhamma-all --pdf-dir .

USAGE — run a single volume by path:
  python3 ingest_pdfs_v2.py --source brahmali_v3 \\
      --pdf "Theravāda-Collection-on-Monastic-Law-brahmali-2026-04-30-3.pdf"

AFTER RUNNING — concatenate Brahmali vols:
  cat output/brahmali_v{1,2,3,4,5,6}.jsonl > output/brahmali_vinaya_complete.jsonl

SCHEMA per record (matches darshana-graph buddhism.json):
  id, pitaka, source, tradition, book, volume, section,
  segment_id, position, text, language, translator, license, pitaka_note,
  commentaries (empty list — placeholder for graph edges)
"""

import json
import os
import re
import argparse
import subprocess
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
from collections import Counter

# ── Source metadata ────────────────────────────────────────────────────────

@dataclass
class SourceMeta:
    key: str
    pitaka: str           # vinaya | abhidhamma
    tradition: str        # theravada | dharmaguptaka | mulasarvastivada
    book: str
    volume: str
    translator: str
    language: str
    license: str
    pitaka_note: str
    default_filename: str
    skip_start_pages: int = 0
    skip_end_pages: int = 0
    min_words: int = 8


SOURCE_META = {

    # ── Brahmali Vinaya vols 1-6 (CC0, SuttaCentral 2026) ─────────────────
    # Vol contents per SuttaCentral edition structure:
    #   v1 = Bu Vb (Bhikkhu Vibhaṅga — monks' rules analysis)
    #   v2 = Bi Vb (Bhikkhunī Vibhaṅga — nuns' rules analysis)
    #   v3 = Kd 1-10 (Khandhakas — Great Division, first half)
    #   v4 = Kd 11-22 (Khandhakas — Great Division, second half)
    #   v5 = Appendices + Parivāra (compendium)
    #   v6 = Notes + Glossary (skip most — heavily reference material)
    # Front matter per vol: title page + copyright + opening quote = ~4 pages
    # Back matter: glossary/notes vary — v1 ends with plant glossary (~10pp)

    "brahmali_v1": SourceMeta(
        key="brahmali_v1", pitaka="vinaya", tradition="theravada",
        book="Theravāda Collection on Monastic Law",
        volume="Vol 1 — Bhikkhu Vibhaṅga (monks' rules analysis)",
        translator="brahmali", language="en", license="CC0",
        pitaka_note="Monks' Expulsion, Suspension, Forfeiture, Confession, "
                    "Confession of Fault, Training, Breach of Decorum rules. "
                    "Brahmali 2026, ed5.",
        default_filename="Theravāda-Collection-on-Monastic-Law-brahmali-2026-04-30-1.pdf",
        skip_start_pages=4, skip_end_pages=10, min_words=8,
    ),
    "brahmali_v2": SourceMeta(
        key="brahmali_v2", pitaka="vinaya", tradition="theravada",
        book="Theravāda Collection on Monastic Law",
        volume="Vol 2 — Bhikkhunī Vibhaṅga (nuns' rules analysis)",
        translator="brahmali", language="en", license="CC0",
        pitaka_note="Full analysis of nuns' rules — expulsion, suspension, "
                    "forfeiture, confession, training rules. "
                    "Sections previously untranslated by Horner are included.",
        default_filename="Theravāda-Collection-on-Monastic-Law-brahmali-2026-04-30-2.pdf",
        skip_start_pages=4, skip_end_pages=10, min_words=8,
    ),
    "brahmali_v3": SourceMeta(
        key="brahmali_v3", pitaka="vinaya", tradition="theravada",
        book="Theravāda Collection on Monastic Law",
        volume="Vol 3 — Khandhakas 1-10 (Great Division, first half)",
        translator="brahmali", language="en", license="CC0",
        pitaka_note="Ordination, Pātimokkha, Rains retreat, Robes, Leather, "
                    "Medicine, Kaṭhina, Cloth, Proper conduct, Bhikkhu rules.",
        default_filename="Theravāda-Collection-on-Monastic-Law-brahmali-2026-04-30-3.pdf",
        skip_start_pages=4, skip_end_pages=8, min_words=8,
    ),
    "brahmali_v4": SourceMeta(
        key="brahmali_v4", pitaka="vinaya", tradition="theravada",
        book="Theravāda Collection on Monastic Law",
        volume="Vol 4 — Khandhakas 11-22 (Great Division, second half)",
        translator="brahmali", language="en", license="CC0",
        pitaka_note="Schism, Procedures, Monks' duties, Suppression, "
                    "Bhikkhunī rules, Five hundreds, Seven hundreds.",
        default_filename="Theravāda-Collection-on-Monastic-Law-brahmali-2026-04-30-4.pdf",
        skip_start_pages=4, skip_end_pages=8, min_words=8,
    ),
    "brahmali_v5": SourceMeta(
        key="brahmali_v5", pitaka="vinaya", tradition="theravada",
        book="Theravāda Collection on Monastic Law",
        volume="Vol 5 — Parivāra (Compendium of Monastic Law)",
        translator="brahmali", language="en", license="CC0",
        pitaka_note="Parivāra: summary, questions and answers, analysis of "
                    "offences and procedures. Mnemonic compendium of the Vinaya.",
        default_filename="Theravāda-Collection-on-Monastic-Law-brahmali-2026-04-30-5.pdf",
        skip_start_pages=4, skip_end_pages=8, min_words=8,
    ),
    "brahmali_v6": SourceMeta(
        key="brahmali_v6", pitaka="vinaya", tradition="theravada",
        book="Theravāda Collection on Monastic Law",
        volume="Vol 6 — Appendices, Notes, Glossaries",
        translator="brahmali", language="en", license="CC0",
        pitaka_note="Translator notes, Pali-English glossary, botanical "
                    "identifications, bibliography. Reference material — "
                    "lower doctrinal content density than vols 1-5.",
        default_filename="Theravāda-Collection-on-Monastic-Law-brahmali-2026-04-30-6.pdf",
        skip_start_pages=4, skip_end_pages=5, min_words=10,
        # ADJUST: vol 6 is mostly reference — raise min_words if too noisy
    ),

    # ── Horner vol 1 (PTS 1938) ────────────────────────────────────────────
    # I.B. Horner "Book of the Discipline" vol 1 = Suttavibhaṅga (monks)
    # PTS front matter: title, dedication, preface, abbreviations ~20pp
    # Back matter: index ~15pp
    # ADJUST skip values after first run — PTS PDFs vary
    "horner_v1": SourceMeta(
        key="horner_v1", pitaka="vinaya", tradition="theravada",
        book="The Book of the Discipline (Vinaya-Piṭaka) Vol 1 — Suttavibhaṅga",
        volume="Vol 1 — Suttavibhaṅga (monks' rules)",
        translator="horner", language="en", license="pts_public_domain",
        pitaka_note="I.B. Horner PTS translation (1938). Monks' rules only. "
                    "Older idiom — 'he', archaic constructions. "
                    "Direct comparison source for Brahmali v1 translation-shift analysis. "
                    "Note: Horner omitted some risqué sections; Brahmali restores them.",
        default_filename="I.B Horner - Vinaya Pitaka vol 1 - Suttavibhanga.pdf",
        skip_start_pages=20, skip_end_pages=15, min_words=8,
        # ADJUST: PTS PDFs often have long introductions; increase skip_start if needed
    ),

    # ── Dharmaguptaka Vinaya (Chinese Buddhist tradition) ──────────────────
    # Dharmaguptaka = school whose Vinaya was adopted by Chinese Buddhism
    # This PDF is a modern scholarly edition of the Bhikshu Posadha rite
    # Front matter likely minimal (modern PDF) — ADJUST after first run
    "dharmaguptaka": SourceMeta(
        key="dharmaguptaka", pitaka="vinaya", tradition="dharmaguptaka",
        book="Dharmaguptaka Vinaya — Bhikshu Posadha and Rites",
        volume="Bhikshu Posadha ceremony and associated rites",
        translator="unknown",   # ADJUST: check PDF for translator credit
        language="en", license="free_distribution",
        pitaka_note="Dharmaguptaka Vinaya as preserved in Chinese Buddhism "
                    "(四分律 Sìfēnlǜ). This PDF covers the Posadha (fortnightly "
                    "recitation) ceremony and associated rites only — not the "
                    "full Vinaya. Key comparison: Pātimokkha rules vs Theravāda "
                    "equivalent. Dharmaguptaka has 250 monks' rules vs "
                    "Theravāda's 227.",
        default_filename="Dharmaguptaka_Vinaya_Bhikshu_Posadha_and_Rites_PDF_v2024-03-13.pdf",
        skip_start_pages=3, skip_end_pages=3, min_words=8,
        # ADJUST: modern PDFs usually have minimal front matter
    ),

    # ── Mūlasarvāstivāda Vinaya Toh 1-6 (84000, Tibetan Buddhism) ─────────
    # 84000.co translation of Toh 1-6 from the Tibetan Kangyur
    # Toh 1 = Vinayavastu (monastic procedures — 18 khandhakas equivalent)
    # Toh 2 = Vinayavibhaṅga (monks' rules analysis)
    # Toh 3 = Bhikṣuṇīvibhaṅga (nuns' rules)
    # Toh 4 = Vinayakṣudrakavastu (minor matters)
    # Toh 5 = Vinayottaragrantha
    # Toh 6 = Uttaragrantha supplement
    # 84000 PDFs: cover + title + about 84000 + translator intro ~8pp front
    # Back matter: colophon + acknowledgements ~5pp
    # ADJUST: 84000 PDFs vary; check after first run
    "mulasarvastivada": SourceMeta(
        key="mulasarvastivada", pitaka="vinaya", tradition="mulasarvastivada",
        book="Mūlasarvāstivāda Vinaya — Toh 1-6 (84000)",
        volume="Toh 1-6: Vinayavastu, Vinayavibhaṅga, Bhikṣuṇīvibhaṅga, "
               "Kṣudrakavastu, Uttaragrantha",
        translator="84000",
        language="en", license="CC_BY_NC_SA_4",
        pitaka_note="Mūlasarvāstivāda Vinaya from the Tibetan Kangyur (Toh 1-6). "
                    "84000 translation project. This is the Vinaya lineage used "
                    "by Tibetan Buddhism including Nyingma/Palyul. "
                    "Substantially longer than Pali Vinaya — Vinayavastu alone "
                    "covers 18 khandhakas-equivalent with much more narrative. "
                    "CC BY-NC-SA 4.0.",
        default_filename="toh1-6.pdf",
        skip_start_pages=8, skip_end_pages=5, min_words=8,
        # ADJUST: 84000 PDFs sometimes have longer intros per volume
    ),

    # ── Abhidhamma sources (already ingested in v1 — included here for
    #    completeness so this script is the single entry point) ───────────
    "bodhi_sangaha": SourceMeta(
        key="bodhi_sangaha", pitaka="abhidhamma", tradition="theravada",
        book="A Comprehensive Manual of Abhidhamma (Abhidhammattha Saṅgaha)",
        volume="Complete — 9 chapters",
        translator="bodhi", language="en", license="bps_free_distribution",
        pitaka_note="Bhikkhu Bodhi's translation and commentary of Anuruddha's "
                    "Abhidhammattha Saṅgaha (11th c.). BPS 1993/2007. "
                    "Covers citta, cetasika, miscellaneous, thought process, "
                    "matter, cosmology, categories, dependent origination, "
                    "mental culture. Secondary/summary — not root Abhidhamma Piṭaka.",
        default_filename="bp304s_Bfodhi_Comprehensive_Manual_of_Abhidhamma.pdf",
        skip_start_pages=8, skip_end_pages=5, min_words=8,
    ),
    "narada_sangaha": SourceMeta(
        key="narada_sangaha", pitaka="abhidhamma", tradition="theravada",
        book="A Manual of Abhidhamma (Abhidhammattha Saṅgaha) — Narada",
        volume="Complete — 9 chapters",
        translator="narada", language="en", license="free_distribution",
        pitaka_note="Narada Maha Thera translation (1956/1975), Buddhist "
                    "Missionary Society. Bilingual Pali+English. "
                    "Earlier translation of same Saṅgaha as Bodhi. "
                    "Use for translation-shift comparison.",
        default_filename="abhidhamma.pdf",
        skip_start_pages=15, skip_end_pages=5, min_words=8,
    ),
    "nandamalabhivamsa": SourceMeta(
        key="nandamalabhivamsa", pitaka="abhidhamma", tradition="theravada",
        book="Fundamental Abhidhamma Part I — Nandamālābhivaṃsa",
        volume="Part I — citta, cetasika, rūpa",
        translator="nandamalabhivamsa", language="en",
        license="free_distribution",
        pitaka_note="Burmese scholastic teaching manual, Sagaing Hills. "
                    "Covers first three ultimate realities only. "
                    "Highly structured with enumeration tables.",
        default_filename="fundamentalabhidhamma.pdf",
        skip_start_pages=5, skip_end_pages=3, min_words=6,
    ),
}

# ── Convenience groupings ──────────────────────────────────────────────────

BRAHMALI_KEYS   = [f"brahmali_v{i}" for i in range(1, 7)]
ABHIDHAMMA_KEYS = ["bodhi_sangaha", "narada_sangaha", "nandamalabhivamsa"]
VINAYA_CROSS    = ["horner_v1", "dharmaguptaka", "mulasarvastivada"]
ALL_KEYS        = BRAHMALI_KEYS + VINAYA_CROSS + ABHIDHAMMA_KEYS

# ── Text extraction ────────────────────────────────────────────────────────

def get_page_count(pdf_path: str) -> int:
    r = subprocess.run(["pdfinfo", pdf_path], capture_output=True, text=True)
    for line in r.stdout.splitlines():
        if line.startswith("Pages:"):
            return int(line.split(":")[1].strip())
    return 0

def extract_text(pdf_path: str, first_page: int, last_page: int) -> str:
    cmd = ["pdftotext", "-f", str(first_page), "-l", str(last_page),
           "-enc", "UTF-8", pdf_path, "-"]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    return r.stdout

# ── Paragraph cleaning ─────────────────────────────────────────────────────

JUNK_RE = [
    re.compile(r'^\s*\d+\s*$'),
    re.compile(r'^\s*[ivxlcdmIVXLCDM]+\s*$'),
    re.compile(r'^\s*\f\s*$'),
    re.compile(r'^(table of contents|contents|index|bibliography)\s*$', re.I),
    re.compile(r'^\s*\.{4,}\s*\d*\s*$'),
    re.compile(r'^[\d\s\.\n]+$'),   # TOC number lists
]

def fix_spaced_chars(text: str) -> str:
    """Fix BPS-font artifact: 'N o n - g r e e d' → 'Non-greed'"""
    if re.search(r'([A-Za-z] ){4,}', text):
        text = re.sub(r'(?<=[A-Za-z]) (?=[A-Za-z])', '', text)
        text = re.sub(r'  +', ' ', text)
    return text

def clean(para: str) -> str:
    return para.replace('\f', ' ').replace('\r', ' ').strip()

def is_junk(para: str) -> bool:
    s = para.strip()
    return any(p.match(s) for p in JUNK_RE)

def split_paragraphs(raw: str, min_words: int) -> list[str]:
    paras = re.split(r'\n\s*\n', raw)
    result = []
    for p in paras:
        p = clean(p)
        if not p or is_junk(p):
            continue
        p = fix_spaced_chars(p)
        if len(p.split()) < min_words:
            continue
        result.append(p)
    return result

# ── Section detection ──────────────────────────────────────────────────────

SECTION_RE = re.compile(
    r'^(chapter|part|book|section|khandhaka|vibhaṅga|pārājika|'
    r'saṅghādisesa|nissaggiya|pācittiya|pāṭidesanīya|sekhiya|'
    r'adhikaraṇasamatha|§|\d+\.|[IVXLCDM]+\.)\b',
    re.IGNORECASE
)

def detect_section(para: str) -> str:
    lines = [l.strip() for l in para.strip().splitlines() if l.strip()]
    if lines and len(lines[0].split()) <= 10 and SECTION_RE.match(lines[0]):
        return lines[0]
    return ""

# ── Core ingestion ─────────────────────────────────────────────────────────

def ingest(pdf_path: str, meta: SourceMeta) -> list[dict]:
    if not os.path.exists(pdf_path):
        print(f"  ERROR: not found: {pdf_path}")
        return []

    total = get_page_count(pdf_path)
    if not total:
        print(f"  ERROR: cannot read page count: {pdf_path}")
        return []

    first = meta.skip_start_pages + 1
    last  = total - meta.skip_end_pages
    print(f"  Pages: {total} total → extracting {first}–{last}")

    raw   = extract_text(pdf_path, first, last)
    paras = split_paragraphs(raw, meta.min_words)
    print(f"  → {len(paras)} paragraphs")

    records = []
    section = ""
    for pos, para in enumerate(paras, 1):
        s = detect_section(para)
        if s:
            section = s
        records.append({
            "id":          f"{meta.key}:{pos}",
            "pitaka":      meta.pitaka,
            "source":      meta.key,
            "tradition":   meta.tradition,
            "book":        meta.book,
            "volume":      meta.volume,
            "section":     section,
            "segment_id":  f"{meta.key}:{pos}",
            "position":    pos,
            "text":        para,
            "language":    meta.language,
            "translator":  meta.translator,
            "license":     meta.license,
            "pitaka_note": meta.pitaka_note,
            "commentaries": [],
        })
    return records

def print_stats(records: list[dict], key: str):
    if not records:
        return
    chars = sorted(len(r["text"]) for r in records)
    words = sorted(len(r["text"].split()) for r in records)
    n = len(records)
    print(f"  {key}: {n} segs | "
          f"chars min={chars[0]} med={chars[n//2]} max={chars[-1]} | "
          f"words min={words[0]} med={words[n//2]} max={words[-1]}")

# ── Entry point ────────────────────────────────────────────────────────────

def resolve_path(meta: SourceMeta, pdf_dir: str,
                 override: Optional[str]) -> str:
    if override:
        return override
    candidate = os.path.join(pdf_dir, meta.default_filename)
    if os.path.exists(candidate):
        return candidate
    # fallback: cwd
    return meta.default_filename

def main():
    p = argparse.ArgumentParser(description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)

    # Source selection
    p.add_argument("--all",            action="store_true", help="All sources")
    p.add_argument("--brahmali-all",   action="store_true", help="Brahmali vols 1-6")
    p.add_argument("--abhidhamma-all", action="store_true", help="All Abhidhamma sources")
    p.add_argument("--vinaya-cross",   action="store_true",
                   help="Cross-tradition Vinaya (Horner + Dharmaguptaka + Mūlasarvāstivāda)")
    for k in ALL_KEYS:
        p.add_argument(f"--{k.replace('_','-')}", action="store_true")
    p.add_argument("--source", help="Single source key (use with --pdf)")

    # Path overrides
    p.add_argument("--pdf",     help="PDF path (used with --source for single file)")
    p.add_argument("--pdf-dir", default=".", help="Directory containing PDFs")
    p.add_argument("--output-dir", default="output")

    # Per-source path overrides
    for k in ALL_KEYS:
        p.add_argument(f"--{k.replace('_','-')}-pdf", default=None)

    args = p.parse_args()
    os.makedirs(args.output_dir, exist_ok=True)

    # Build list of keys to process
    to_process = []
    if args.all:
        to_process = ALL_KEYS
    else:
        if args.brahmali_all:   to_process += BRAHMALI_KEYS
        if args.abhidhamma_all: to_process += ABHIDHAMMA_KEYS
        if args.vinaya_cross:   to_process += VINAYA_CROSS
        if args.source:
            if args.source not in SOURCE_META:
                print(f"Unknown source key: {args.source}")
                print(f"Valid keys: {', '.join(SOURCE_META.keys())}")
                return
            to_process.append(args.source)
        # Individual flags
        for k in ALL_KEYS:
            flag = k.replace("_", "-")
            if getattr(args, k.replace("-", "_"), False):
                if k not in to_process:
                    to_process.append(k)

    if not to_process:
        p.print_help()
        return

    # Deduplicate while preserving order
    seen = set()
    to_process = [k for k in to_process if not (k in seen or seen.add(k))]

    # Resolve path overrides from args
    overrides = {}
    for k in ALL_KEYS:
        attr = f"{k.replace('-', '_')}_pdf"
        val = getattr(args, attr, None)
        if val:
            overrides[k] = val
    if args.source and args.pdf:
        overrides[args.source] = args.pdf

    all_records = []
    written = []

    for key in to_process:
        meta = SOURCE_META[key]
        pdf_path = resolve_path(meta, args.pdf_dir, overrides.get(key))
        print(f"\n[{key}] {pdf_path}")

        records = ingest(pdf_path, meta)
        if not records:
            continue

        print_stats(records, key)

        out = os.path.join(args.output_dir, f"{key}.jsonl")
        with open(out, "w", encoding="utf-8") as f:
            for r in records:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"  → {out}")
        written.append((key, out, len(records)))
        all_records.extend(records)

    # Combined output when processing multiple sources
    if len(written) > 1:
        combined = os.path.join(args.output_dir, "tipitaka_extended_v2.jsonl")
        with open(combined, "w", encoding="utf-8") as f:
            for r in all_records:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")

        print(f"\n{'='*60}")
        print(f"Combined: {combined}")
        print(f"{'='*60}")
        by_pitaka    = Counter(r["pitaka"]    for r in all_records)
        by_tradition = Counter(r["tradition"] for r in all_records)
        by_source    = Counter(r["source"]    for r in all_records)

        print(f"\n{'Source':<35} {'Segments':>8}")
        print(f"{'-'*35} {'-'*8}")
        for k, out, n in written:
            print(f"  {k:<33} {n:>8}")
        print(f"{'  TOTAL':<35} {len(all_records):>8}")

        print(f"\n{'By pitaka':<35} {'Segments':>8}")
        for k, v in sorted(by_pitaka.items()):
            print(f"  {'pitaka='+k:<33} {v:>8}")

        print(f"\n{'By tradition':<35} {'Segments':>8}")
        for k, v in sorted(by_tradition.items()):
            print(f"  {'tradition='+k:<33} {v:>8}")


if __name__ == "__main__":
    main()
