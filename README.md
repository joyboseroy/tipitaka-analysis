# tipitaka-analysis

**Three Piṭakas, Three Vocabularies: A Computational Analysis of the English Buddhist Canon**

Computational stylometric analysis of the English Tipiṭaka across all three Piṭakas — Sutta, Vinaya, and Abhidhamma — plus cross-tradition Vinaya comparison (Theravāda, Dharmaguptaka, Mūlasarvāstivāda) and an 88-year translation-shift analysis (Brahmali 2026 versus Horner 1938).

**Paper:** 
**Extends:** [Darshana Graph](https://github.com/joyboseroy/darshana-graph) (arXiv:2606.18222)  
**Data:** [joyboseroy/darshana-graph on HuggingFace](https://huggingface.co/datasets/joyboseroy/darshana-graph)  

---

## What this repo contains

This repo extends the Darshana Graph project from Sutta-only analysis to the full Tipiṭaka. The Darshana Graph corpus and knowledge graph remain in their own repo; this repo adds the Vinaya and Abhidhamma-adjacent corpora and runs a unified analysis across all three Piṭaka-level divisions.

```
tipitaka-analysis/
├── scripts/
│   ├── ingest_pdfs_v2.py        # PDF ingestion for Vinaya + Abhidhamma sources
│   ├── zipf_analysis.py         # Zipf, TTR, MATTR, numeral density, Jaccard
│   ├── plot_analysis.py         # All 7 figures
│   └── reviewer_analyses.py     # MATTR, bootstrap Jaccard, Zipf OLS, size-controlled TTR
├── results/
│   ├── zipf_results.json        # All analysis outputs
│   ├── reviewer_analyses.json   # MATTR, Zipf slopes, size-controlled TTR
│   ├── mattr_comparison.tsv
│   ├── jaccard_bootstrap.tsv
│   └── zipf_exponents.tsv
├── figures/
│   ├── fig1_segment_lengths.png
│   ├── fig2_ttr_scatter.png
│   ├── fig3_zipf.png
│   ├── fig4_numerals.png
│   ├── fig5_vocab_overlap.png
│   ├── fig6_translation_shift.png
│   └── fig7_word_freq.png       # (word frequency top-15 per division)
├── paper/
│   └── tipitaka_paper_v4_final.docx
├── data/
│   └── sources.md               # Where to obtain each PDF and JSONL
└── README.md
```

---

## Key findings

| Finding | Result |
|---------|--------|
| Sutta vs Vinaya MATTR-500 | 0.399 vs 0.400 — nearly identical; raw TTR difference is a segmentation artefact |
| Sangaha corpus MATTR-500 | 0.560 — genuinely more diverse, confirmed by size-controlled subsampling |
| Sangaha numeral density | 3.26% — highest of all divisions |
| Sangaha Zipf slope | −0.876 (Δ = +0.124 from ideal) — 'consciousness' at rank 8 displaces grammatical particles |
| Vinaya Theravāda Zipf slope | −0.949 — closest to ideal Zipf |
| Theravāda vs Mūlasarvāstivāda Vinaya | Jaccard 0.200, overlap coeff. 0.491 — substantial shared legal heritage |
| Brahmali vs Horner translation shift | Jaccard 0.242 — only 24.2% shared vocabulary across 88 years |
| Most diagnostic translation shifts | musing → absorption (jhāna); defeat → expulsion (pārājika) |

---

## Corpus sources

The analysis uses the following corpora. See `data/sources.md` for download instructions.

| Source | Segments | License | Format |
|--------|----------|---------|--------|
| Sutta Piṭaka (Sujato/bilara-data) | 114,591 | CC0 | JSONL from HuggingFace |
| Vinaya — Brahmali 2026 (6 vols) | 7,923 | CC0 | PDF → extracted |
| Vinaya — Horner 1938 Vol. 1 | 2,826 | Public domain | PDF → extracted |
| Vinaya — Dharmaguptaka (partial) | 185 | Free distribution | PDF → extracted |
| Vinaya — Mūlasarvāstivāda (84000) | 7,229 | CC BY-NC-SA 4.0 | PDF → extracted |
| Sangaha corpus (Bodhi + Narada + Nandamālā) | 2,077 | Free distribution | PDF → extracted |

The Sutta corpus is downloaded from HuggingFace:

```bash
wget "https://huggingface.co/datasets/joyboseroy/darshana-graph/resolve/main/darshana_corpus.jsonl" \
     -O darshana_corpus.jsonl
```

---

## Quickstart

```bash
git clone https://github.com/joyboseroy/tipitaka-analysis
cd tipitaka-analysis
pip install matplotlib numpy tqdm requests

# Download Sutta corpus from HuggingFace (see above)
# Place your PDF files in the working directory (see data/sources.md)

# Step 1: Ingest Vinaya PDFs (Brahmali vols 1-6)
for i in 1 2 3 4 5 6; do
  python3 scripts/ingest_pdfs_v2.py \
    --vinaya \
    --brahmali-vinaya-pdf "Theravada-Collection-on-Monastic-Law-brahmali-2026-04-30-${i}.pdf" \
    --output-dir output/brahmali_v${i}
done
cat output/brahmali_v{1,2,3,4,5,6}/brahmali_vinaya.jsonl > output/brahmali_vinaya_complete.jsonl

# Step 2: Ingest cross-tradition Vinaya and Abhidhamma
python3 scripts/ingest_pdfs_v2.py --vinaya-cross --abhidhamma-all \
  --pdf-dir . --output-dir output/all

# Step 3: Concatenate master corpus
cat output/all/brahmali_v{1,2,3,4,5,6}.jsonl \
    output/all/{horner_v1,dharmaguptaka,mulasarvastivada}.jsonl \
    output/all/{bodhi_sangaha,narada_sangaha,nandamalabhivamsa}.jsonl \
    > output/tipitaka_master.jsonl

# Step 4: Run main analysis
python3 scripts/zipf_analysis.py \
  --sutta darshana_corpus.jsonl \
  --master output/tipitaka_master.jsonl

# Step 5: Generate figures
pip install matplotlib numpy
python3 scripts/plot_analysis.py

# Step 6: Run reviewer analyses (MATTR, Zipf OLS, size-controlled TTR)
python3 scripts/reviewer_analyses.py \
  --sutta darshana_corpus.jsonl \
  --master output/tipitaka_master.jsonl
```

All results are written to `results/` and figures to `results/figures/`.

---

## Reproducing specific numbers from the paper

Every number in the paper can be reproduced from the scripts above. Key mappings:

| Paper section | Script | Output file |
|---------------|--------|-------------|
| Table 1 (MATTR, TTR, Num%) | `zipf_analysis.py` | `results/zipf_results.json` → `ttr`, `mattr`, `numerals` |
| Table 2 (segment lengths) | `zipf_analysis.py` | `results/zipf_results.json` → `length_stats` |
| Table 3 (Jaccard, overlap coeff.) | `zipf_analysis.py` | `results/zipf_results.json` → `vocabulary_overlap` |
| Table 4 (Zipf slopes) | `reviewer_analyses.py` | `results/zipf_exponents.tsv` |
| MATTR-500 values | `reviewer_analyses.py` | `results/mattr_comparison.tsv` |
| Size-controlled TTR | `reviewer_analyses.py` | `results/reviewer_analyses.json` → `size_controlled_ttr` |
| Translation shift (Brahmali vs Horner) | `zipf_analysis.py` | `results/zipf_results.json` → `translation_comparison` |

---

## Relation to Darshana Graph

This repo extends [joyboseroy/darshana-graph](https://github.com/joyboseroy/darshana-graph) in two ways:

1. **Corpus extension:** The Darshana Graph corpus (`darshana_corpus.jsonl`) covers the Sutta Piṭaka and Hindu/Jain texts. This repo adds the Vinaya Piṭaka and Abhidhamma-adjacent sources, producing a corpus spanning all three Piṭaka-level divisions.

2. **Analysis extension:** The Darshana Graph paper (arXiv:2606.18222) analysed the Sutta Piṭaka only. This paper runs a unified analysis across all three divisions and adds cross-tradition Vinaya comparison.

The Darshana Graph knowledge graph (`darshana_graph.jsonl`, 28,322 edges) is not modified by this repo. Future work will extend the IS_PRECURSOR_OF and NEGATES edges to cover the Vinaya and cross-tradition Mahayana corpora ingested here, which is the intended direction for concept-level doctrinal evolution analysis.

---

## Citation

Please cite the Darshana Graph paper for the Sutta corpus:

```bibtex
@article{bose2026darshana,
  title   = {Darshana Graph: A Parallel Commentary Corpus for Comparative Indian Philosophy,
             with Stylometric and Exploratory Graph Analyses},
  author  = {Bose, Joy},
  journal = {arXiv preprint arXiv:2606.18222},
  year    = {2026},
  url     = {https://arxiv.org/abs/2606.18222}
}
```

---

## License

All original code in this repository is released under the MIT License.

Corpus data licenses vary by source — see `data/sources.md` for details. The Sutta corpus (Sujato/bilara-data) and Brahmali Vinaya are CC0. The 84000 Mūlasarvāstivāda Vinaya is CC BY-NC-SA 4.0.

