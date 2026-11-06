# Real SQuAD 1.1 development slice

This directory contains **real public dataset text and human annotations**, not
invented fixtures or model outputs. It replaces the proposed PubMedQA data source
for our first real-data integration.

- 25 original questions across five articles.
- 50 source paragraphs, including distractor contexts beyond each question's source.
- Human answer spans and offsets preserved in `references.json`.
- First annotated answer used as one required phrase in `dataset.json`.
- All cases are standard; no reviewed domain-critical labels are claimed.
- No model has been run and no baseline/candidate recordings exist for this subset.

## Attribution and license

Data adapted from **SQuAD**, Pranav Rajpurkar, Jian Zhang, Konstantin Lopyrev,
and Percy Liang (2016), *SQuAD: 100,000+ Questions for Machine Comprehension of Text*.
[Paper](https://aclanthology.org/D16-1264/),
[official project and dataset license notice](https://rajpurkar.github.io/SQuAD-explorer/).

SQuAD is distributed under [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/).
The adapted dataset JSON files here are distributed under that same license;
this notice does not license the repository's Python code.
Changes: selected questions/paragraphs, assigned stable case/content-hash source
IDs, mapped the first annotated answer to a required-phrase assertion, and added
evaluation metadata. The upstream reference answers and context text are preserved.

Contexts originate from Wikipedia articles and their contributors:
[Super Bowl 50](https://en.wikipedia.org/wiki/Super_Bowl_50),
[Warsaw](https://en.wikipedia.org/wiki/Warsaw),
[Normans](https://en.wikipedia.org/wiki/Normans),
[Nikola Tesla](https://en.wikipedia.org/wiki/Nikola_Tesla), and
[Computational complexity theory](https://en.wikipedia.org/wiki/Computational_complexity_theory).
These links identify article provenance, not current text snapshots; the pinned
SQuAD source file determines the exact text used. Detailed IDs, source location,
selection positions, and checksums are recorded in `manifest.json`.

## Reproduce

Download the pinned public source, then run the offline importer from the repo root:

```sh
curl --fail --location \
  https://raw.githubusercontent.com/rajpurkar/SQuAD-explorer/240e165ab706d95bd4323653bb92421f446208cf/dataset/dev-v1.1.json \
  --output /tmp/squad-dev-v1.1.json
uv run --python 3.12 scripts/prepare_squad.py \
  --input /tmp/squad-dev-v1.1.json \
  --output-dir /tmp/squad-reproduced-v1
```

The input checksum must match the pinned original. The output directory must not
exist. A disk error may leave partial output; inspect it and choose a new directory
to retry. The full downloaded file stays outside the repository. No inference or
provider key is needed. Tests read the committed subset without network access.

## Limits and integration boundary

Selection is fixed: first five articles, first ten paragraphs per article as the
corpus, first question from each of paragraphs 0–4 as evaluation cases. This small
nonrandom slice is an integration dataset, not a representative benchmark.

Source labels identify the original associated paragraph, not all potentially
relevant paragraphs in the corpus. Retrieval must search all 50 contexts and never
receive answer annotations. Actual citations must come from pipeline output.

The current scorer checks only the first answer phrase. Other human answers are
often equally valid but are not accepted as alternatives by that scorer yet. Its
coverage score is not official SQuAD exact-match/F1 or semantic correctness.
Do not copy references into a baseline and claim a model result. The next step is
to produce genuine local retrieval/pipeline recordings against this corpus.
