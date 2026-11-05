# Synthetic recordings

These JSON files are handwritten synthetic fixtures, **not real model outputs**.
No model was called. Configuration versions describe fixture variants; they do not
demonstrate measured effects of an actual prompt change.

- `baseline.synthetic.v1.json`: fixed reference answers for dataset 1.0.0.
- `candidate.synthetic.v2.json`: intentionally changes `refund-window` to 60 days
  and omits proof of purchase. The support-hours answer stays identical.

The candidate is structurally valid. A later scorer should catch its critical
quality regression; the loader must accept it. Never overwrite the baseline
automatically with candidate results.

Each file records dataset identity/version, configuration identity/version,
model/prompt/retrieval versions, and responses keyed by case ID. Retrieved source
IDs are ranked lists. Empty answers and unknown citations are valid observations.
