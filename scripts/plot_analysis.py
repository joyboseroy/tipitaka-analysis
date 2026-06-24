"""
plot_analysis.py
================
Generates all figures for the Tipiṭaka statistical analysis paper.

Figures produced:
  Fig 1: Zipf log-log rank-frequency plot (4 pitakas + KJV reference line)
  Fig 2: Vocabulary overlap heatmap (Jaccard, 5 traditions)
  Fig 3: Numeral density bar chart (enumeration signal per corpus)
  Fig 4: Type-token ratio comparison (with segment-length context)
  Fig 5: Top-20 word frequency comparison (Sutta vs Vinaya vs Abhidhamma)
  Fig 6: Brahmali vs Horner distinctive vocabulary (translation shift)
  Fig 7: Segment length distributions (box plots, all pitakas)

All figures saved to results/figures/ as PNG (300dpi) + PDF (vector).

Usage:
  python3 plot_analysis.py
  python3 plot_analysis.py --results results/zipf_results.json
  python3 plot_analysis.py --fig 1 3 6   # specific figures only
"""

import json
import os
import argparse
import math
from pathlib import Path

# ── Matplotlib setup ────────────────────────────────────────────────────────
import matplotlib
matplotlib.use("Agg")   # non-interactive backend for WSL
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

FIGURES_DIR = "results/figures"
RESULTS_PATH = "results/zipf_results.json"

# ── Colour palette (consistent across all figures) ──────────────────────────
COLOURS = {
    "pitaka_sutta":              "#2E86AB",   # blue
    "pitaka_vinaya_theravada":   "#A23B72",   # purple
    "pitaka_abhidhamma":         "#F18F01",   # amber
    "vinaya_dharmaguptaka":      "#C73E1D",   # red
    "vinaya_mulasarvastivada":   "#3B1F2B",   # dark plum
    "vinaya_brahmali":           "#A23B72",   # same as vinaya theravada
    "vinaya_horner":             "#C9A7D4",   # light purple
    "tipitaka_theravada":        "#404040",   # dark grey
}

LABELS = {
    "pitaka_sutta":              "Sutta Piṭaka (Sujato)",
    "pitaka_vinaya_theravada":   "Vinaya — Theravāda (Brahmali+Horner)",
    "pitaka_abhidhamma":         "Abhidhamma (Bodhi+Narada)",
    "vinaya_dharmaguptaka":      "Vinaya — Dharmaguptaka",
    "vinaya_mulasarvastivada":   "Vinaya — Mūlasarvāstivāda",
    "vinaya_brahmali":           "Vinaya — Brahmali 2026",
    "vinaya_horner":             "Vinaya — Horner 1938",
    "tipitaka_theravada":        "Full Theravāda Tipiṭaka",
}

# ── Helpers ──────────────────────────────────────────────────────────────────

def load_results(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)

def load_tsv(path: str) -> list[dict]:
    rows = []
    with open(path, encoding="utf-8") as f:
        headers = f.readline().strip().split("\t")
        for line in f:
            vals = line.strip().split("\t")
            rows.append(dict(zip(headers, vals)))
    return rows

def savefig(fig, name: str):
    os.makedirs(FIGURES_DIR, exist_ok=True)
    png_path = f"{FIGURES_DIR}/{name}.png"
    pdf_path = f"{FIGURES_DIR}/{name}.pdf"
    fig.savefig(png_path, dpi=300, bbox_inches="tight")
    fig.savefig(pdf_path, bbox_inches="tight")
    print(f"  Saved: {png_path}")
    plt.close(fig)

# ── Figure 1: Zipf log-log plot ───────────────────────────────────────────────

def fig1_zipf(results: dict):
    """
    Log-log rank vs frequency for Sutta, Vinaya (Theravada), Abhidhamma.
    Includes a reference Zipf power-law line (slope = -1).
    Comparable to Zigmond (2020) Figure 2.
    """
    print("  Plotting Fig 1: Zipf log-log...")
    fig, ax = plt.subplots(figsize=(8, 6))

    groups = ["pitaka_sutta", "pitaka_vinaya_theravada", "pitaka_abhidhamma"]
    zipf_data = results.get("zipf", {})

    for name in groups:
        data = zipf_data.get(name, [])
        if not data:
            continue
        log_ranks = [d["log_rank"] for d in data if d.get("log_freq") is not None]
        log_freqs = [d["log_freq"] for d in data if d.get("log_freq") is not None]
        ax.plot(log_ranks, log_freqs,
                color=COLOURS[name],
                label=LABELS[name],
                linewidth=1.8, alpha=0.9)

    # Reference Zipf line (slope = -1, anchored at rank-1 of Sutta)
    sutta_data = zipf_data.get("pitaka_sutta", [])
    if sutta_data:
        anchor_freq = sutta_data[0]["log_freq"]
        x_ref = np.linspace(0, 2.3, 50)
        y_ref = anchor_freq - x_ref   # slope -1
        ax.plot(x_ref, y_ref, "k--", linewidth=1, alpha=0.4,
                label="Ideal Zipf (slope = −1)")

    ax.set_xlabel("log₁₀(rank)", fontsize=12)
    ax.set_ylabel("log₁₀(frequency)", fontsize=12)
    ax.set_title("Zipf Rank-Frequency Distribution\nacross Tipiṭaka Divisions",
                 fontsize=13)
    ax.legend(fontsize=9, loc="upper right")
    ax.grid(True, alpha=0.25)
    # Annotation bottom-left to avoid legend overlap
    ax.annotate("'consciousness' enters\ntop-10 in Abhidhamma\n(rank 8, freq=0.012)",
                xy=(0.954, -1.923), xytext=(0.25, -2.6),
                arrowprops=dict(arrowstyle="->", color=COLOURS["pitaka_abhidhamma"],
                                lw=1.2),
                fontsize=8, color=COLOURS["pitaka_abhidhamma"],
                bbox=dict(boxstyle="round,pad=0.2", facecolor="white",
                          edgecolor=COLOURS["pitaka_abhidhamma"], alpha=0.85))
    fig.tight_layout()
    savefig(fig, "fig1_zipf")

# ── Figure 2: Vocabulary overlap heatmap ─────────────────────────────────────

def fig2_heatmap(results: dict):
    """
    Jaccard similarity heatmap across all 5 corpus groups.
    """
    print("  Plotting Fig 2: Vocabulary overlap heatmap...")

    groups = [
        "pitaka_sutta",
        "pitaka_vinaya_theravada",
        "pitaka_abhidhamma",
        "vinaya_dharmaguptaka",
        "vinaya_mulasarvastivada",
    ]
    short_labels = [
        "Sutta\n(Sujato)",
        "Vinaya\nTheravāda",
        "Abhidhamma",
        "Vinaya\nDharmaguptaka",
        "Vinaya\nMūlasarvāstivāda",
    ]

    overlap = results.get("vocabulary_overlap", {})

    n = len(groups)
    matrix = np.zeros((n, n))
    np.fill_diagonal(matrix, 1.0)

    for i, a in enumerate(groups):
        for j, b in enumerate(groups):
            if i == j:
                continue
            # Try both key orderings
            key1 = f"{a}__vs__{b}"
            key2 = f"{b}__vs__{a}"
            entry = overlap.get(key1, overlap.get(key2, None))
            if entry:
                val = entry.get("jaccard", 0)
            else:
                # Pair not computed — mark as N/A with -1 sentinel
                val = -1
            matrix[i, j] = val

    # For display, replace -1 with 0 but mark differently
    display_matrix = np.where(matrix == -1, 0, matrix)

    fig, ax = plt.subplots(figsize=(7, 6))
    im = ax.imshow(display_matrix, cmap="Blues", vmin=0, vmax=0.35)
    plt.colorbar(im, ax=ax, label="Jaccard similarity")

    ax.set_xticks(range(n))
    ax.set_yticks(range(n))
    ax.set_xticklabels(short_labels, fontsize=8)
    ax.set_yticklabels(short_labels, fontsize=8)

    # Annotate cells
    for i in range(n):
        for j in range(n):
            raw = matrix[i, j]
            if raw == -1:
                # Not computed — show N/C
                ax.text(j, i, "N/C", ha="center", va="center",
                        fontsize=7, color="#999999", style="italic")
            else:
                color = "white" if raw > 0.2 else "black"
                ax.text(j, i, f"{raw:.3f}", ha="center", va="center",
                        fontsize=8, color=color, fontweight="bold")

    ax.set_title("Vocabulary Overlap (Jaccard Similarity)\nacross Tipiṭaka Traditions",
                 fontsize=12)
    fig.tight_layout()
    savefig(fig, "fig2_vocab_overlap")

# ── Figure 3: Numeral density bar chart ───────────────────────────────────────

def fig3_numerals(results: dict):
    """
    Percentage of tokens that are numeral words, per corpus.
    Shows Buddhist enumeration habit across pitakas and traditions.
    """
    print("  Plotting Fig 3: Numeral density...")

    numerals = results.get("numerals", {})
    groups = [
        ("pitaka_sutta",              "Sutta\n(Sujato)"),
        ("pitaka_vinaya_theravada",   "Vinaya\nTheravāda"),
        ("pitaka_abhidhamma",         "Abhidhamma"),
        ("vinaya_dharmaguptaka",      "Vinaya\nDharmaguptaka"),
        ("vinaya_mulasarvastivada",   "Vinaya\nMūlasarvāstivāda"),
        ("tipitaka_theravada",        "Full\nTheravāda\nTipiṭaka"),
    ]

    labels = [g[1] for g in groups]
    values = [numerals.get(g[0], {}).get("numeral_pct", 0) for g in groups]
    colors = [COLOURS.get(g[0], "#888888") for g in groups]

    fig, ax = plt.subplots(figsize=(9, 5))
    bars = ax.bar(labels, values, color=colors, edgecolor="white",
                  linewidth=0.5, alpha=0.85)

    # Value labels on bars
    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.03,
                f"{val:.2f}%", ha="center", va="bottom", fontsize=9)

    ax.set_ylabel("Numeral words (% of all tokens)", fontsize=11)
    ax.set_title("Enumeration Density across Tipiṭaka Divisions\n"
                 "(numeral words as % of total tokens, stopwords included)",
                 fontsize=12)
    ax.set_ylim(0, max(values) * 1.2)
    ax.grid(axis="y", alpha=0.25)
    ax.axhline(y=values[0], color=COLOURS["pitaka_sutta"],
               linestyle="--", alpha=0.4, linewidth=1)
    ax.annotate("Sutta baseline", xy=(0, values[0]),
                xytext=(0.3, values[0] + 0.1),
                fontsize=8, color=COLOURS["pitaka_sutta"], alpha=0.7)
    fig.tight_layout()
    savefig(fig, "fig3_numerals")

# ── Figure 4: Type-token ratio comparison ─────────────────────────────────────

def fig4_ttr(results: dict):
    """
    TTR per corpus with segment count as bubble size.
    Includes annotation about length-sensitivity caveat.
    """
    print("  Plotting Fig 4: TTR comparison...")

    ttr_data = results.get("ttr", {})
    length_data = results.get("length_stats", {})

    groups = [
        ("pitaka_sutta",              "Sutta (Sujato)",            "sutta"),
        ("pitaka_vinaya_theravada",   "Vinaya Theravāda",          "vinaya"),
        ("pitaka_abhidhamma",         "Abhidhamma",                "abhidhamma"),
        ("vinaya_dharmaguptaka",      "Vinaya Dharmaguptaka",      "vinaya"),
        ("vinaya_mulasarvastivada",   "Vinaya Mūlasarvāstivāda",  "vinaya"),
        ("vinaya_horner",             "Vinaya Horner 1938",        "vinaya"),
    ]

    # Per-point label offsets to avoid collisions
    OFFSETS = {
        "pitaka_sutta":            (6, 8),
        "pitaka_vinaya_theravada": (6, 3),
        "pitaka_abhidhamma":       (6, -10),
        "vinaya_dharmaguptaka":    (-120, 5),
        "vinaya_mulasarvastivada": (6, 3),
        "vinaya_horner":           (6, -10),
    }

    fig, ax = plt.subplots(figsize=(9, 5))

    for key, label, _ in groups:
        t = ttr_data.get(key, {})
        l = length_data.get(key, {})
        if not t:
            continue
        ttr       = t.get("ttr", 0)
        tokens    = t.get("tokens", 1)
        med_words = l.get("words", {}).get("median", 0) if l else 0

        color = COLOURS.get(key, "#888888")
        size  = math.log10(tokens) * 80
        ax.scatter(med_words, ttr, s=size, color=color, alpha=0.75,
                   edgecolors="white", linewidth=0.5)
        ox, oy = OFFSETS.get(key, (6, 3))
        ax.annotate(label, (med_words, ttr),
                    textcoords="offset points", xytext=(ox, oy),
                    fontsize=7.5)

    ax.set_xlabel("Median segment length (words)", fontsize=11)
    ax.set_ylabel("Type-token ratio (TTR)", fontsize=11)
    ax.set_title("Vocabulary Diversity vs Segment Length\n"
                 "(bubble size ∝ log total tokens)",
                 fontsize=12)
    ax.grid(True, alpha=0.2)
    ax.annotate("Longer segments → lower TTR\n(length-sensitivity caveat)",
                xy=(0.02, 0.05), xycoords="axes fraction",
                fontsize=8, color="grey",
                bbox=dict(boxstyle="round,pad=0.3", facecolor="lightyellow",
                          edgecolor="grey", alpha=0.7))
    fig.tight_layout()
    savefig(fig, "fig4_ttr")

# ── Figure 5: Top-20 word frequency side-by-side ─────────────────────────────

def fig5_word_freq(results: dict):
    """
    Horizontal bar charts: top-15 words for Sutta, Vinaya, Abhidhamma side by side.
    """
    print("  Plotting Fig 5: Word frequency comparison...")

    freq_data = results.get("word_frequency", {})
    groups = [
        ("pitaka_sutta",            "Sutta Piṭaka"),
        ("pitaka_vinaya_theravada", "Vinaya Piṭaka\n(Theravāda)"),
        ("pitaka_abhidhamma",       "Abhidhamma Piṭaka"),
    ]

    fig, axes = plt.subplots(1, 3, figsize=(15, 6))

    for ax, (key, title) in zip(axes, groups):
        data = freq_data.get(key, [])[:15]
        if not data:
            continue
        words  = [d["word"] for d in data]
        counts = [d["count"] for d in data]

        color = COLOURS.get(key, "#888888")
        bars = ax.barh(range(len(words)), counts,
                       color=color, alpha=0.8, edgecolor="white")
        ax.set_yticks(range(len(words)))
        ax.set_yticklabels(words, fontsize=9)
        ax.invert_yaxis()
        ax.set_xlabel("Count", fontsize=9)
        ax.set_title(title, fontsize=11, fontweight="bold")
        ax.grid(axis="x", alpha=0.2)

        # Value labels
        for bar, count in zip(bars, counts):
            ax.text(bar.get_width() + max(counts)*0.01, bar.get_y() + bar.get_height()/2,
                    f"{count:,}", va="center", fontsize=7)

    fig.suptitle("Top-15 Content Words per Tipiṭaka Division\n(stopwords removed)",
                 fontsize=13, y=1.01)
    fig.tight_layout()
    savefig(fig, "fig5_word_freq")

# ── Figure 6: Brahmali vs Horner distinctive vocabulary ──────────────────────

def fig6_translation(results: dict):
    """
    Back-to-back bar chart of words distinctive to each translation.
    Brahmali 2026 vs Horner 1938 — same Vinaya text, 88 years apart.
    """
    print("  Plotting Fig 6: Translation shift (Brahmali vs Horner)...")

    # PDF section-reference artefacts to exclude from distinctive word lists
    PDF_ARTEFACTS = {"sp", "kd", "pj", "ss", "np", "pc", "sk", "pd",
                     "vb", "pvr", "bi", "bu", "va", "cf", "vs"}

    tc = results.get("translation_comparison", {})
    if not tc:
        print("  No translation comparison data — skipping Fig 6")
        return

    def clean_dist(dist, exclude):
        cleaned = []
        for d in dist:
            w = d[0] if isinstance(d, list) else d.get("word", "")
            c = d[1] if isinstance(d, list) else d.get("count", 0)
            if w.lower() not in exclude and len(w) > 2:
                cleaned.append((w, c))
        return cleaned[:12]

    b_dist = clean_dist(tc.get("brahmali_distinctive", []), PDF_ARTEFACTS)
    h_dist = clean_dist(tc.get("horner_distinctive",   []), PDF_ARTEFACTS)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 6))

    # Brahmali distinctive
    b_words  = [d[0] for d in b_dist]
    b_counts = [d[1] for d in b_dist]
    ax1.barh(range(len(b_words)), b_counts,
             color=COLOURS["vinaya_brahmali"], alpha=0.85, edgecolor="white")
    ax1.set_yticks(range(len(b_words)))
    ax1.set_yticklabels(b_words, fontsize=9)
    ax1.invert_yaxis()
    ax1.set_xlabel("Count", fontsize=9)
    ax1.set_title("Words exclusive to\nBrahmali 2026", fontsize=11,
                  fontweight="bold", color=COLOURS["vinaya_brahmali"])
    ax1.grid(axis="x", alpha=0.2)

    # Horner distinctive
    h_words  = [d[0] for d in h_dist]
    h_counts = [d[1] for d in h_dist]
    ax2.barh(range(len(h_words)), h_counts,
             color=COLOURS["vinaya_horner"], alpha=0.85, edgecolor="white")
    ax2.set_yticks(range(len(h_words)))
    ax2.set_yticklabels(h_words, fontsize=9)
    ax2.invert_yaxis()
    ax2.set_xlabel("Count", fontsize=9)
    ax2.set_title("Words exclusive to\nHorner 1938", fontsize=11,
                  fontweight="bold", color="#7B4F8E")
    ax2.grid(axis="x", alpha=0.2)

    # Shared stats annotation
    ov = tc.get("overlap", {})
    jaccard = ov.get("jaccard", 0)
    shared  = ov.get("shared", 0)
    fig.suptitle(
        f"Translation Shift: Brahmali 2026 vs Horner 1938 (Vinaya Piṭaka Vol 1)\n"
        f"Vocabulary overlap: Jaccard = {jaccard:.3f}  |  "
        f"Shared vocabulary: {shared:,} words  |  "
        f"TTR Brahmali: {tc.get('brahmali_ttr', 0):.4f}  "
        f"TTR Horner: {tc.get('horner_ttr', 0):.4f}",
        fontsize=10, y=1.01
    )
    fig.tight_layout()
    savefig(fig, "fig6_translation")

# ── Figure 7: Segment length box plots ───────────────────────────────────────

def fig7_segment_lengths(results: dict):
    """
    Box plots showing segment length distributions across pitakas.
    Highlights the fundamental segmentation difference between bilara-data
    (Sutta, short) and PDF-extracted text (Vinaya/Abhidhamma, long).
    """
    print("  Plotting Fig 7: Segment length distributions...")

    length_data = results.get("length_stats", {})

    groups = [
        ("pitaka_sutta",              "Sutta\n(Sujato)"),
        ("pitaka_vinaya_theravada",   "Vinaya\nTheravāda"),
        ("pitaka_abhidhamma",         "Abhidhamma"),
        ("vinaya_mulasarvastivada",   "Vinaya\nMūlasarv."),
        ("vinaya_horner",             "Vinaya\nHorner"),
    ]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

    for ax, metric, ylabel in [
        (ax1, "words", "Segment length (words)"),
        (ax2, "chars", "Segment length (characters)"),
    ]:
        positions = []
        box_data  = []

        for i, (key, label) in enumerate(groups):
            ld = length_data.get(key, {}).get(metric, {})
            if not ld:
                continue
            # Reconstruct approximate percentile box from stored stats
            box_data.append({
                "med":  ld.get("median", 0),
                "q1":   ld.get("p25", 0),
                "q3":   ld.get("p75", 0),
                "p10":  ld.get("p10", 0),
                "p90":  ld.get("p90", 0),
                "label": label,
                "color": COLOURS.get(key, "#888888"),
            })
            positions.append(i + 1)

        # Draw manual box plots from percentile stats
        for i, bd in enumerate(box_data):
            pos = i + 1
            color = bd["color"]
            # Box (Q1 to Q3)
            ax.bar(pos, bd["q3"] - bd["q1"], bottom=bd["q1"],
                   width=0.5, color=color, alpha=0.6, edgecolor=color)
            # Median line
            ax.hlines(bd["med"], pos - 0.25, pos + 0.25,
                      color=color, linewidth=2.5)
            # Whiskers (P10 to P90)
            ax.vlines(pos, bd["p10"], bd["q1"], color=color,
                      linewidth=1, linestyle="--", alpha=0.6)
            ax.vlines(pos, bd["q3"], bd["p90"], color=color,
                      linewidth=1, linestyle="--", alpha=0.6)
            # P10 and P90 caps
            ax.hlines(bd["p10"], pos - 0.15, pos + 0.15,
                      color=color, linewidth=1.2)
            ax.hlines(bd["p90"], pos - 0.15, pos + 0.15,
                      color=color, linewidth=1.2)
            # Median value label
            ax.text(pos, bd["med"] + bd["q3"] * 0.03,
                    f"{bd['med']}", ha="center", fontsize=7.5,
                    fontweight="bold")

        ax.set_xticks(range(1, len(box_data) + 1))
        ax.set_xticklabels([bd["label"] for bd in box_data], fontsize=8.5)
        ax.set_ylabel(ylabel, fontsize=10)
        ax.grid(axis="y", alpha=0.2)
        ax.set_title(f"Segment lengths ({metric})\nBox = Q1–Q3, whiskers = P10–P90",
                     fontsize=10)

    fig.suptitle("Segment Length Distributions across Tipiṭaka Divisions\n"
                 "(Sutta Piṭaka from bilara-data; Vinaya/Abhidhamma from PDF extraction)",
                 fontsize=12, y=1.01)
    fig.tight_layout()
    savefig(fig, "fig7_segment_lengths")

# ── Main ───────────────────────────────────────────────────────────────────────

FIG_MAP = {
    1: fig1_zipf,
    2: fig2_heatmap,
    3: fig3_numerals,
    4: fig4_ttr,
    5: fig5_word_freq,
    6: fig6_translation,
    7: fig7_segment_lengths,
}

def main():
    parser = argparse.ArgumentParser(description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--results", default=RESULTS_PATH)
    parser.add_argument("--fig", nargs="+", type=int,
                        help="Which figures to generate (1-7). Default: all.")
    args = parser.parse_args()

    if not os.path.exists(args.results):
        print(f"ERROR: results file not found: {args.results}")
        print("Run python3 zipf_analysis.py first.")
        return

    print(f"Loading results from {args.results}...")
    results = load_results(args.results)

    figures = args.fig if args.fig else list(FIG_MAP.keys())
    os.makedirs(FIGURES_DIR, exist_ok=True)

    print(f"\nGenerating {len(figures)} figure(s)...")
    for n in figures:
        if n not in FIG_MAP:
            print(f"  Unknown figure {n}, skipping")
            continue
        FIG_MAP[n](results)

    print(f"\nAll figures saved to {FIGURES_DIR}/")
    print("Files:")
    for f in sorted(Path(FIGURES_DIR).glob("*.png")):
        size_kb = f.stat().st_size // 1024
        print(f"  {f.name} ({size_kb} KB)")

if __name__ == "__main__":
    main()
