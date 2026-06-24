"""
zipf_analysis.py
================
Zipf distribution + word frequency analysis across the full Tipiṭaka:
  - Sutta Piṭaka   : darshana_corpus.jsonl  (filtered to tradition=buddhism)
  - Vinaya Piṭaka  : output/all/brahmali_v{1..6}.jsonl + horner_v1 + cross-tradition
  - Abhidhamma     : output/all/{bodhi_sangaha,narada_sangaha,nandamalabhivamsa}.jsonl
  - New corpus     : output/tipitaka_master.jsonl

Analyses produced:
  1. Word frequency top-50 per pitaka (and per tradition for Vinaya)
  2. Zipf rank-frequency distribution per pitaka
  3. Type-token ratio per pitaka and per source
  4. Vocabulary overlap across pitakas (Jaccard)
  5. Numerals analysis (Buddhist enumeration habit)
  6. All results saved to results/zipf_results.json + TSV tables

Usage:
  python3 zipf_analysis.py

  # Custom paths:
  python3 zipf_analysis.py \\
      --sutta darshana_corpus.jsonl \\
      --new   output/all/tipitaka_extended_v2.jsonl \\
      --master output/tipitaka_master.jsonl
"""

import json
import os
import re
import argparse
import math
from collections import Counter, defaultdict
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────
DEFAULT_SUTTA_PATH  = "darshana_corpus.jsonl"
DEFAULT_MASTER_PATH = "output/tipitaka_master.jsonl"
DEFAULT_ALL_PATH    = "output/all/tipitaka_extended_v2.jsonl"
RESULTS_DIR         = "results"

# ── Stopwords (English) ────────────────────────────────────────────────────
# Minimal set — we keep Buddhist terms that would normally be stopwords
# e.g. "one" is both a numeral signal AND a stopword candidate
STOPWORDS = {
    "the","a","an","and","or","but","in","on","at","to","for","of","with",
    "by","from","as","is","was","are","were","be","been","being","have",
    "has","had","do","does","did","will","would","could","should","may",
    "might","shall","must","that","this","these","those","it","its",
    "he","she","they","we","you","i","me","him","her","us","them","his",
    "their","our","your","my","its","who","which","what","when","where",
    "how","if","then","than","so","not","no","nor","yet","both","either",
    "also","just","even","very","too","more","most","some","any","all",
    "each","every","other","such","same","own","up","out","about","into",
    "through","during","before","after","above","below","between","among",
}

# ── Loading ────────────────────────────────────────────────────────────────

def load_sutta_corpus(path: str) -> list[dict]:
    """Load darshana_corpus.jsonl, filter to Buddhism only."""
    records = []
    skipped = 0
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            if r.get("tradition") != "buddhism":
                skipped += 1
                continue
            # Normalise to common schema
            records.append({
                "text":      r.get("text", ""),
                "pitaka":    "sutta",
                "source":    r.get("source", ""),
                "tradition": "theravada",
                "translator": r.get("translator", "sujato"),
            })
    print(f"  Sutta: {len(records)} Buddhist records loaded "
          f"({skipped} non-Buddhist skipped)")
    return records

def load_new_corpus(path: str) -> list[dict]:
    """Load tipitaka_master.jsonl or tipitaka_extended_v2.jsonl."""
    records = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            records.append({
                "text":      r.get("text", ""),
                "pitaka":    r.get("pitaka", ""),
                "source":    r.get("source", ""),
                "tradition": r.get("tradition", ""),
                "translator": r.get("translator", ""),
            })
    print(f"  New corpus: {len(records)} records loaded from {path}")
    return records

# ── Text processing ────────────────────────────────────────────────────────

TOKEN_RE = re.compile(r"\b[a-zA-ZāīūṭḍṇḷṃṅñśṣṛḥÀ-ÿ]+\b")
NUMERAL_WORDS = {
    "one","two","three","four","five","six","seven","eight","nine","ten",
    "eleven","twelve","thirteen","fourteen","fifteen","sixteen","seventeen",
    "eighteen","nineteen","twenty","thirty","forty","fifty","sixty",
    "seventy","eighty","ninety","hundred","thousand","million",
    # Buddhist enumeration terms
    "first","second","third","fourth","fifth","sixth","seventh","eighth",
    "ninth","tenth","twofold","threefold","fourfold","fivefold","sevenfold",
    "eightfold","tenfold","twelvefold",
}

# ── Contraction remnants to filter ────────────────────────────────────────
# Sujato uses modern English contractions (don't, they're, it's).
# pdftotext splits on apostrophes, leaving fragments like s, t, re, ve.
# These are not real tokens and must be excluded.
CONTRACTION_REMNANTS = {
    "re","ve","ll","nt","em",           # they're→re, I've→ve, I'll→ll
    "don","doesn","didn","isn","wasn",   # don't→don, doesn't→doesn
    "couldn","wouldn","shouldn",
    "haven","hadn","won","aren","ca",    # can't→ca+nt
}

def tokenise(text: str, remove_stopwords: bool = True) -> list[str]:
    tokens = TOKEN_RE.findall(text.lower())
    # Drop single-char fragments (s, t from it's, don't) and contraction remnants
    tokens = [t for t in tokens
              if len(t) > 1 and t not in CONTRACTION_REMNANTS]
    if remove_stopwords:
        tokens = [t for t in tokens if t not in STOPWORDS]
    return tokens

def tokenise_all(records: list[dict],
                 remove_stopwords: bool = True) -> list[str]:
    all_tokens = []
    for r in records:
        all_tokens.extend(tokenise(r["text"], remove_stopwords))
    return all_tokens

# ── Analysis functions ─────────────────────────────────────────────────────

def word_frequency(tokens: list[str], top_n: int = 50) -> list[tuple]:
    c = Counter(tokens)
    return c.most_common(top_n)

def type_token_ratio(tokens: list[str]) -> float:
    if not tokens:
        return 0.0
    return len(set(tokens)) / len(tokens)

def zipf_data(tokens: list[str], top_n: int = 200) -> list[dict]:
    """
    Return rank-frequency data for Zipf plot.
    Each entry: {rank, word, count, freq, log_rank, log_freq}
    """
    c = Counter(tokens)
    total = len(tokens)
    result = []
    for rank, (word, count) in enumerate(c.most_common(top_n), 1):
        freq = count / total
        result.append({
            "rank":     rank,
            "word":     word,
            "count":    count,
            "freq":     round(freq, 8),
            "log_rank": round(math.log10(rank), 4),
            "log_freq": round(math.log10(freq), 4) if freq > 0 else None,
        })
    return result

def vocabulary_overlap(vocab_a: set, vocab_b: set) -> dict:
    """Jaccard similarity + shared/unique counts."""
    intersection = vocab_a & vocab_b
    union = vocab_a | vocab_b
    return {
        "jaccard":    round(len(intersection) / len(union), 4) if union else 0,
        "shared":     len(intersection),
        "only_a":     len(vocab_a - vocab_b),
        "only_b":     len(vocab_b - vocab_a),
        "total_a":    len(vocab_a),
        "total_b":    len(vocab_b),
    }

def numeral_analysis(tokens: list[str]) -> dict:
    """What fraction of tokens are numeral words?"""
    numerals = [t for t in tokens if t in NUMERAL_WORDS]
    total = len(tokens)
    return {
        "numeral_count": len(numerals),
        "total_tokens":  total,
        "numeral_pct":   round(100 * len(numerals) / total, 3) if total else 0,
        "top_numerals":  Counter(numerals).most_common(15),
    }

def segment_length_stats(records: list[dict]) -> dict:
    """Character and word length distribution."""
    char_lens = sorted(len(r["text"]) for r in records)
    word_lens = sorted(len(r["text"].split()) for r in records)
    n = len(records)
    if n == 0:
        return {}
    return {
        "n_segments": n,
        "chars": {
            "min": char_lens[0],
            "p10": char_lens[n//10],
            "p25": char_lens[n//4],
            "median": char_lens[n//2],
            "p75": char_lens[3*n//4],
            "p90": char_lens[9*n//10],
            "max": char_lens[-1],
        },
        "words": {
            "min": word_lens[0],
            "p10": word_lens[n//10],
            "p25": word_lens[n//4],
            "median": word_lens[n//2],
            "p75": word_lens[3*n//4],
            "p90": word_lens[9*n//10],
            "max": word_lens[-1],
        },
    }

# ── Reporting ──────────────────────────────────────────────────────────────

def print_freq_table(label: str, freq: list[tuple], top: int = 30):
    print(f"\n  Top {top} words — {label}")
    print(f"  {'Rank':<5} {'Word':<25} {'Count':>8}")
    print(f"  {'-'*5} {'-'*25} {'-'*8}")
    for i, (word, count) in enumerate(freq[:top], 1):
        print(f"  {i:<5} {word:<25} {count:>8}")

def print_zipf_summary(label: str, data: list[dict]):
    print(f"\n  Zipf summary — {label}")
    print(f"  {'Rank':<6} {'Word':<20} {'Freq':>10} {'log_rank':>9} {'log_freq':>9}")
    print(f"  {'-'*6} {'-'*20} {'-'*10} {'-'*9} {'-'*9}")
    for d in data[:10]:
        print(f"  {d['rank']:<6} {d['word']:<20} {d['freq']:>10.6f} "
              f"{d['log_rank']:>9.3f} {d['log_freq']:>9.3f}")
    print(f"  ... (top 200 saved to results)")

def save_tsv(path: str, rows: list[dict], fields: list[str]):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\t".join(fields) + "\n")
        for row in rows:
            f.write("\t".join(str(row.get(k, "")) for k in fields) + "\n")

# ── Main ───────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--sutta",  default=DEFAULT_SUTTA_PATH)
    parser.add_argument("--master", default=DEFAULT_MASTER_PATH)
    parser.add_argument("--new",    default=DEFAULT_ALL_PATH,
                        help="Fallback if --master not found")
    parser.add_argument("--top-n",  type=int, default=50)
    parser.add_argument("--no-stopwords", action="store_true",
                        help="Include stopwords in frequency counts")
    args = parser.parse_args()

    os.makedirs(RESULTS_DIR, exist_ok=True)
    remove_sw = not args.no_stopwords

    # ── Load corpora ───────────────────────────────────────────────────────
    print("\n=== Loading corpora ===")
    sutta_records = load_sutta_corpus(args.sutta)

    master_path = args.master if os.path.exists(args.master) else args.new
    new_records = load_new_corpus(master_path)

    # Split new records by pitaka and tradition
    vinaya_theravada = [r for r in new_records
                        if r["pitaka"] == "vinaya"
                        and r["tradition"] == "theravada"]
    vinaya_dharmaguptaka = [r for r in new_records
                            if r["tradition"] == "dharmaguptaka"]
    vinaya_mulasarv = [r for r in new_records
                       if r["tradition"] == "mulasarvastivada"]
    abhidhamma_all  = [r for r in new_records
                       if r["pitaka"] == "abhidhamma"]

    # Brahmali only (exclude Horner from Theravada Vinaya primary)
    vinaya_brahmali = [r for r in vinaya_theravada
                       if "brahmali" in r["source"]]
    vinaya_horner   = [r for r in vinaya_theravada
                       if r["source"] == "horner_v1"]

    print(f"\n  Corpus summary:")
    print(f"  {'Sutta (Theravada)':<35} {len(sutta_records):>8}")
    print(f"  {'Vinaya Brahmali (Theravada)':<35} {len(vinaya_brahmali):>8}")
    print(f"  {'Vinaya Horner (Theravada)':<35} {len(vinaya_horner):>8}")
    print(f"  {'Vinaya Dharmaguptaka':<35} {len(vinaya_dharmaguptaka):>8}")
    print(f"  {'Vinaya Mulasarvastivada':<35} {len(vinaya_mulasarv):>8}")
    print(f"  {'Abhidhamma (all sources)':<35} {len(abhidhamma_all):>8}")
    total = (len(sutta_records) + len(new_records))
    print(f"  {'TOTAL':<35} {total:>8}")

    # ── Define analysis groups ─────────────────────────────────────────────
    groups = {
        "sutta":                  sutta_records,
        "vinaya_brahmali":        vinaya_brahmali,
        "vinaya_horner":          vinaya_horner,
        "vinaya_dharmaguptaka":   vinaya_dharmaguptaka,
        "vinaya_mulasarvastivada":vinaya_mulasarv,
        "abhidhamma":             abhidhamma_all,
        # Pitaka-level aggregates
        "pitaka_sutta":           sutta_records,
        "pitaka_vinaya_theravada": vinaya_brahmali + vinaya_horner,
        "pitaka_vinaya_all":      vinaya_brahmali + vinaya_horner +
                                  vinaya_dharmaguptaka + vinaya_mulasarv,
        "pitaka_abhidhamma":      abhidhamma_all,
        # Full Theravada Tipitaka
        "tipitaka_theravada":     sutta_records + vinaya_brahmali + abhidhamma_all,
    }

    results = {}

    # ── Analysis 1: Segment length stats ──────────────────────────────────
    print("\n=== Analysis 1: Segment length distributions ===")
    length_stats = {}
    for name, recs in groups.items():
        if not recs:
            continue
        stats = segment_length_stats(recs)
        length_stats[name] = stats
        if "pitaka" in name or name in ("sutta", "abhidhamma"):
            print(f"\n  {name} (n={stats['n_segments']:,})")
            c = stats["chars"]
            w = stats["words"]
            print(f"    chars: min={c['min']} p25={c['p25']} "
                  f"med={c['median']} p75={c['p75']} max={c['max']}")
            print(f"    words: min={w['min']} p25={w['p25']} "
                  f"med={w['median']} p75={w['p75']} max={w['max']}")
    results["length_stats"] = length_stats

    # ── Analysis 2: Word frequency per pitaka ─────────────────────────────
    print("\n=== Analysis 2: Word frequency (stopwords removed) ===")
    freq_results = {}
    for name in ["pitaka_sutta", "pitaka_vinaya_theravada",
                 "pitaka_abhidhamma", "pitaka_vinaya_all"]:
        recs = groups[name]
        if not recs:
            continue
        tokens = tokenise_all(recs, remove_stopwords=remove_sw)
        freq = word_frequency(tokens, top_n=args.top_n)
        freq_results[name] = freq
        print_freq_table(name, freq, top=20)

        # Save TSV
        tsv_rows = [{"rank": i+1, "word": w, "count": c}
                    for i, (w, c) in enumerate(freq)]
        save_tsv(f"{RESULTS_DIR}/freq_{name}.tsv",
                 tsv_rows, ["rank", "word", "count"])

    results["word_frequency"] = {
        k: [{"word": w, "count": c} for w, c in v]
        for k, v in freq_results.items()
    }

    # ── Analysis 3: Type-token ratio ───────────────────────────────────────
    print("\n=== Analysis 3: Type-token ratio (vocabulary diversity) ===")
    ttr_results = {}
    print(f"\n  {'Group':<35} {'Tokens':>10} {'Types':>10} {'TTR':>8}")
    print(f"  {'-'*35} {'-'*10} {'-'*10} {'-'*8}")
    for name, recs in groups.items():
        if not recs:
            continue
        tokens = tokenise_all(recs, remove_stopwords=True)
        ttr = type_token_ratio(tokens)
        ttr_results[name] = {
            "tokens": len(tokens),
            "types":  len(set(tokens)),
            "ttr":    round(ttr, 4),
        }
        print(f"  {name:<35} {len(tokens):>10,} {len(set(tokens)):>10,} {ttr:>8.4f}")
    results["ttr"] = ttr_results

    # ── Analysis 4: Zipf distribution ─────────────────────────────────────
    print("\n=== Analysis 4: Zipf rank-frequency distribution ===")
    zipf_results = {}
    # Include stopwords for Zipf (as Zigmond does — stopword freq matters)
    for name in ["pitaka_sutta", "pitaka_vinaya_theravada",
                 "pitaka_abhidhamma", "pitaka_vinaya_all"]:
        recs = groups[name]
        if not recs:
            continue
        tokens = tokenise_all(recs, remove_stopwords=False)
        zdata = zipf_data(tokens, top_n=200)
        zipf_results[name] = zdata
        print_zipf_summary(name, zdata)

        save_tsv(f"{RESULTS_DIR}/zipf_{name}.tsv",
                 zdata,
                 ["rank", "word", "count", "freq", "log_rank", "log_freq"])

    results["zipf"] = zipf_results

    # ── Analysis 5: Numeral analysis ──────────────────────────────────────
    print("\n=== Analysis 5: Numeral word frequency "
          "(Buddhist enumeration signal) ===")
    numeral_results = {}
    print(f"\n  {'Group':<35} {'Numeral%':>10} {'Count':>10}")
    print(f"  {'-'*35} {'-'*10} {'-'*10}")
    for name in ["pitaka_sutta", "pitaka_vinaya_theravada",
                 "pitaka_abhidhamma", "vinaya_brahmali",
                 "vinaya_horner", "vinaya_dharmaguptaka",
                 "vinaya_mulasarvastivada", "tipitaka_theravada"]:
        recs = groups.get(name, [])
        if not recs:
            continue
        tokens = tokenise_all(recs, remove_stopwords=False)
        na = numeral_analysis(tokens)
        numeral_results[name] = na
        print(f"  {name:<35} {na['numeral_pct']:>9.3f}% {na['numeral_count']:>10,}")
    print("\n  Top numeral words per pitaka:")
    for name in ["pitaka_sutta", "pitaka_vinaya_theravada", "pitaka_abhidhamma"]:
        if name not in numeral_results:
            continue
        top = numeral_results[name]["top_numerals"][:8]
        print(f"  {name}: {', '.join(f'{w}({c})' for w,c in top)}")
    results["numerals"] = numeral_results

    # ── Analysis 6: Vocabulary overlap (Jaccard) ──────────────────────────
    print("\n=== Analysis 6: Vocabulary overlap across traditions ===")
    # Build vocabulary sets
    vocabs = {}
    for name in ["pitaka_sutta", "pitaka_vinaya_theravada",
                 "pitaka_abhidhamma", "vinaya_dharmaguptaka",
                 "vinaya_mulasarvastivada"]:
        recs = groups.get(name, [])
        if recs:
            vocabs[name] = set(tokenise_all(recs, remove_stopwords=True))

    overlap_results = {}
    pairs = [
        ("pitaka_sutta",             "pitaka_vinaya_theravada"),
        ("pitaka_sutta",             "pitaka_abhidhamma"),
        ("pitaka_vinaya_theravada",  "pitaka_abhidhamma"),
        ("pitaka_vinaya_theravada",  "vinaya_dharmaguptaka"),
        ("pitaka_vinaya_theravada",  "vinaya_mulasarvastivada"),
        ("vinaya_dharmaguptaka",     "vinaya_mulasarvastivada"),
    ]
    print(f"\n  {'Pair':<60} {'Jaccard':>8} {'Shared':>8}")
    print(f"  {'-'*60} {'-'*8} {'-'*8}")
    for a, b in pairs:
        if a not in vocabs or b not in vocabs:
            continue
        ov = vocabulary_overlap(vocabs[a], vocabs[b])
        label = f"{a} vs {b}"
        overlap_results[f"{a}__vs__{b}"] = ov
        print(f"  {label:<60} {ov['jaccard']:>8.4f} {ov['shared']:>8,}")
    results["vocabulary_overlap"] = overlap_results

    # ── Analysis 7: Brahmali vs Horner translation comparison ─────────────
    print("\n=== Analysis 7: Brahmali vs Horner (same text, two translations) ===")
    if vinaya_brahmali and vinaya_horner:
        b_tokens = tokenise_all(vinaya_brahmali[:1039], remove_stopwords=True)
        h_tokens = tokenise_all(vinaya_horner,          remove_stopwords=True)
        b_vocab = set(b_tokens)
        h_vocab = set(h_tokens)
        ov = vocabulary_overlap(b_vocab, h_vocab)
        b_ttr = type_token_ratio(b_tokens)
        h_ttr = type_token_ratio(h_tokens)
        b_freq = dict(Counter(b_tokens).most_common(20))
        h_freq = dict(Counter(h_tokens).most_common(20))

        print(f"\n  Brahmali vol1 tokens: {len(b_tokens):,}  TTR: {b_ttr:.4f}")
        print(f"  Horner vol1 tokens:   {len(h_tokens):,}  TTR: {h_ttr:.4f}")
        print(f"  Vocabulary overlap (Jaccard): {ov['jaccard']:.4f}")
        print(f"  Shared vocabulary: {ov['shared']:,} words")
        print(f"  Only in Brahmali:  {ov['only_a']:,} words")
        print(f"  Only in Horner:    {ov['only_b']:,} words")

        # Words distinctive to each
        b_unique = b_vocab - h_vocab
        h_unique = h_vocab - b_vocab
        b_dist = Counter({w: c for w, c in Counter(b_tokens).items()
                          if w in b_unique}).most_common(15)
        h_dist = Counter({w: c for w, c in Counter(h_tokens).items()
                          if w in h_unique}).most_common(15)
        print(f"\n  Most frequent words ONLY in Brahmali:")
        print(f"  {', '.join(f'{w}({c})' for w,c in b_dist)}")
        print(f"\n  Most frequent words ONLY in Horner:")
        print(f"  {', '.join(f'{w}({c})' for w,c in h_dist)}")

        results["translation_comparison"] = {
            "brahmali_ttr": b_ttr,
            "horner_ttr":   h_ttr,
            "overlap":      ov,
            "brahmali_distinctive": b_dist,
            "horner_distinctive":   h_dist,
        }

    # ── Save all results ───────────────────────────────────────────────────
    out_path = f"{RESULTS_DIR}/zipf_results.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=str)
    print(f"\n\nAll results saved to {out_path}")
    print(f"TSV files saved to {RESULTS_DIR}/")

    # ── Summary table for paper ────────────────────────────────────────────
    print("\n" + "="*65)
    print("SUMMARY TABLE (for paper)")
    print("="*65)
    print(f"\n{'Source':<35} {'Segs':>7} {'Tokens':>10} {'Types':>8} "
          f"{'TTR':>7} {'Num%':>7}")
    print(f"{'-'*35} {'-'*7} {'-'*10} {'-'*8} {'-'*7} {'-'*7}")

    summary_groups = [
        ("Sutta Piṭaka (Sujato)",        "pitaka_sutta"),
        ("Vinaya — Brahmali",             "vinaya_brahmali"),
        ("Vinaya — Horner",               "vinaya_horner"),
        ("Vinaya — Dharmaguptaka",        "vinaya_dharmaguptaka"),
        ("Vinaya — Mūlasarvāstivāda",    "vinaya_mulasarvastivada"),
        ("Abhidhamma (all)",              "pitaka_abhidhamma"),
        ("Full Theravāda Tipiṭaka",      "tipitaka_theravada"),
    ]
    for label, name in summary_groups:
        recs = groups.get(name, [])
        if not recs:
            print(f"  {label:<33} {'—':>7}")
            continue
        t = ttr_results.get(name, {})
        n = numeral_results.get(name, {})
        tokens = t.get("tokens", 0)
        types  = t.get("types", 0)
        ttr    = t.get("ttr", 0)
        numpct = n.get("numeral_pct", 0) if n else 0
        print(f"  {label:<33} {len(recs):>7,} {tokens:>10,} {types:>8,} "
              f"{ttr:>7.4f} {numpct:>6.2f}%")

if __name__ == "__main__":
    main()
