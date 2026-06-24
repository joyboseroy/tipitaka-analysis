# Data Sources

This file lists where to obtain every corpus file used in the analysis.
None of the PDF files are redistributed in this repository due to file size
and licensing. The JSONL files produced by the ingestion scripts are not
redistributed either, but can be reproduced by running `scripts/ingest_pdfs_v2.py`
on the PDFs listed below.

---

## 1. Sutta Pitaka — darshana_corpus.jsonl

**What it is:** 125,040 records covering the Sutta Pitaka (114,591 Buddhist
segments) plus Hindu and Jain texts from the Darshana Graph project. The
analysis filters to `tradition == "buddhism"` (114,591 records).

**Download:**

```bash
wget "https://huggingface.co/datasets/joyboseroy/darshana-graph/resolve/main/darshana_corpus.jsonl" \
     -O data/darshana_corpus.jsonl
```

Or with curl:

```bash
curl -L "https://huggingface.co/datasets/joyboseroy/darshana-graph/resolve/main/darshana_corpus.jsonl" \
     -o data/darshana_corpus.jsonl
```

**Size:** ~83 MB  
**License:** CC0 (Sujato translations); see HuggingFace dataset card for full details  
**Citation:** Bose (2026a), arXiv:2606.18222

---

## 2. Vinaya Pitaka — Brahmali 2026 (6 volumes)

**What it is:** The first complete modern English translation of the Theravada
Vinaya Pitaka by Bhikkhu Brahmali. Six PDF volumes covering Bhikkhu Vibhanga,
Bhikkhuni Vibhanga, Khandhakas 1-22, and Parivara.

**Download:** All six volumes are available from SuttaCentral:

```
https://suttacentral.net/editions/pli-tv-vi/en/brahmali
```

Click "Download" on that page. The PDFs are named:

```
Theravada-Collection-on-Monastic-Law-brahmali-2026-04-30-1.pdf  (Bhikkhu Vibhanga)
Theravada-Collection-on-Monastic-Law-brahmali-2026-04-30-2.pdf  (Bhikkhuni Vibhanga)
Theravada-Collection-on-Monastic-Law-brahmali-2026-04-30-3.pdf  (Khandhakas 1-10)
Theravada-Collection-on-Monastic-Law-brahmali-2026-04-30-4.pdf  (Khandhakas 11-22)
Theravada-Collection-on-Monastic-Law-brahmali-2026-04-30-5.pdf  (Parivara)
Theravada-Collection-on-Monastic-Law-brahmali-2026-04-30-6.pdf  (Appendices)
```

**License:** CC0  
**Note:** The edition date in the filename (2026-04-30) may change in future
releases. Check the SuttaCentral page for the current edition.

---

## 3. Vinaya Pitaka — Horner 1938 Vol. 1

**What it is:** I.B. Horner's Pali Text Society translation of the
Suttavibhanga (monks' rules), Volume 1 of "The Book of the Discipline".
Used only for the translation-shift analysis against Brahmali Vol. 1.

**Where to find it:**

The PTS translation is still in copyright in some jurisdictions. It is widely
available through university library systems. Scanned copies can be found via:

```
https://archive.org  (search: "Horner Book of Discipline Vinaya")
```

A clean scan is available at:

```
https://archive.org/details/bookdiscipline01hornuoft
```

**License:** PTS copyright (1938); verify your local fair-use provisions before
downloading for research use.

---

## 4. Vinaya — Dharmaguptaka (partial)

**What it is:** English rendering of the Dharmaguptaka Vinaya Bhikshu Posadha
rite (fortnightly recitation ceremony). Covers the Posadha rite and associated
rules only — not the full Dharmaguptaka Vinaya. 185 segments in the analysis.

**File:** `Dharmaguptaka_Vinaya_Bhikshu_Posadha_and_Rites_PDF_v2024-03-13.pdf`

**Where to find it:** This document circulates freely in Chinese Buddhist
monastic communities. It can be found via:

- The Dharma Drum Buddhist College digital archive
- BDK America (Numata Center) publications
- Search: "Dharmaguptaka Vinaya Bhikshu Posadha English PDF"

**License:** Free distribution for Buddhist education purposes.

**Important caveat:** This is a partial corpus (Posadha rite only). Any
cross-tradition comparison involving this corpus should be treated as
preliminary. See Section 5.4 of the paper for full discussion.

---

## 5. Vinaya — Mulasarvastivada (Toh 1-6, 84000)

**What it is:** 84000 Translation Project's English translation of the
Mulasarvastivada Vinaya from the Tibetan Kangyur (Toh 1-6). This is the
Vinaya lineage used by Tibetan Buddhism including the Nyingma, Kagyu,
Sakya, and Gelug schools.

**Download:** Available from the 84000 Reading Room:

```
https://84000.co/translation/toh1   (Vinayavastu)
https://84000.co/translation/toh2   (Vinayavibhanga)
https://84000.co/translation/toh3   (Bhiksunivibhanga)
https://84000.co/translation/toh4   (Vinayaksudrakavastu)
https://84000.co/translation/toh5   (Vinayottaragrantha)
https://84000.co/translation/toh6   (supplement)
```

From each page, use the PDF download option. The combined PDF used in this
analysis is referred to as `toh1-6.pdf`.

**License:** CC BY-NC-SA 4.0  
**Citation:** 84000: Translating the Words of the Buddha (https://84000.co)

---

## 6. Abhidhamma-adjacent corpus — three Sangaha translations

These are three English translations of the same source text: the
Abhidhammattha Sangaha, an 11th-century compendium by Acariya Anuruddha.
They are not translations of the canonical Abhidhamma Pitaka books.
See Section 2.3 of the paper for full discussion.

### 6a. Bodhi — Comprehensive Manual of Abhidhamma

**File:** `bp304s_Bfodhi_Comprehensive_Manual_of_Abhidhamma.pdf`

**What it is:** Bhikkhu Bodhi's translation and commentary of the
Abhidhammattha Sangaha. Buddhist Publication Society, 1993/2007.
This is the primary Sangaha source used in the analysis.

**Where to find it:** Available from the Buddhist Publication Society:

```
https://www.bps.lk
```

Also available through major Buddhist libraries and archive.org:

```
https://archive.org  (search: "Bodhi Comprehensive Manual Abhidhamma")
```

**License:** BPS copyright; free distribution for Dhamma purposes.

### 6b. Narada — Manual of Abhidhamma

**File:** `abhidhamma.pdf`

**What it is:** Narada Maha Thera's translation of the same Abhidhammattha
Sangaha. Buddhist Missionary Society, Kuala Lumpur, 1956/1975.
Used as a translation-comparison source alongside Bodhi.

**Where to find it:**

```
https://archive.org  (search: "Narada Manual Abhidhamma")
```

**License:** Free distribution.

### 6c. Nandamalabhivamsa — Fundamental Abhidhamma Part I

**File:** `fundamentalabhidhamma.pdf`

**What it is:** Teaching manual by Nandamalabhivamsa covering citta,
cetasika, and rupa (the first three ultimate realities). Sagaing Hills,
Myanmar. Covers Part I only — not the full Sangaha.

**Where to find it:** Circulates freely through Burmese Buddhist study
communities. Search:

```
"Nandamalabhivamsa Fundamental Abhidhamma PDF"
```

**License:** Free distribution.

---

## File placement

Once downloaded, place all PDFs in your working directory (or the `data/`
folder) and update the paths in the ingestion commands. The scripts accept
`--pdf-dir` and per-source `--pdf` arguments:

```bash
python3 scripts/ingest_pdfs_v2.py --all \
  --pdf-dir /path/to/your/pdfs/ \
  --output-dir output/all
```

See the main README for the full quickstart command sequence.

---

## File sizes (approximate)

| File | Size |
|------|------|
| darshana_corpus.jsonl | 83 MB |
| Brahmali vols 1-6 (combined) | ~350 MB |
| Horner Vol. 1 | ~30 MB |
| Dharmaguptaka Posadha | ~5 MB |
| toh1-6.pdf (Mulasarvastivada) | ~120 MB |
| Bodhi Comprehensive Manual | ~25 MB |
| Narada Manual | ~20 MB |
| Nandamalabhivamsa Fundamental | ~8 MB |

Total data needed to reproduce the full analysis: approximately 640 MB.

---

## Produced JSONL files

The ingestion scripts produce the following JSONL files which feed into
the analysis scripts. These are not distributed in the repo but can be
reproduced from the PDFs above.

| File | Records | Produced by |
|------|---------|-------------|
| `output/brahmali_vinaya_complete.jsonl` | ~7,923 | `ingest_pdfs_v2.py --brahmali-all` |
| `output/all/horner_v1.jsonl` | 2,826 | `ingest_pdfs_v2.py --horner` |
| `output/all/dharmaguptaka.jsonl` | 185 | `ingest_pdfs_v2.py --dharmaguptaka` |
| `output/all/mulasarvastivada.jsonl` | 7,229 | `ingest_pdfs_v2.py --mulasarvastivada` |
| `output/all/bodhi_sangaha.jsonl` | 796 | `ingest_pdfs_v2.py --bodhi` |
| `output/all/narada_sangaha.jsonl` | 922 | `ingest_pdfs_v2.py --narada` |
| `output/all/nandamalabhivamsa.jsonl` | 389 | `ingest_pdfs_v2.py --nandamalabhivamsa` |
| `output/tipitaka_master.jsonl` | 20,240 | `cat` concatenation (see README) |
