# Research and evaluation guide

## Research objective
Evaluate whether a hybrid rule-based and machine-learning detector improves prompt-injection/jailbreak detection over regex-only and ML-only baselines, including multilingual and document-derived inputs.

## Suggested research questions
1. Does hybrid detection improve the precision/recall trade-off over regex-only and ML-only baselines?
2. How does performance differ across English, obfuscated English, Telugu script, Romanized Telugu, and Telugu-English mixed prompts?
3. What is the operational cost of REVIEW decisions for benign inputs?
4. Does document pre-screening identify structural indicators such as HTML comments or hidden elements?

## Experimental protocol
- Freeze a versioned dataset and record its source, date, labels, and licensing.
- Deduplicate exact and near-duplicate texts across train, validation, and test splits.
- Ensure the held-out test set is not used for threshold selection or training.
- Use grouped splits when paraphrases or templates are related.
- Have a fluent Telugu speaker validate Telugu-script and Romanized Telugu labels.
- Compare:
  - Regex-only: any configured regex match is positive.
  - ML-only: classifier score at a threshold selected on validation data.
  - Combined: report both binary BLOCK outcomes and the full BLOCK/REVIEW/ALLOW policy.
- Report confusion matrix, accuracy, precision, recall, F1, false-positive rate, false-negative rate, per-language metrics, review rate, and repeated-run latency.
- Use multiple latency runs; report median and p95 as well as mean where possible.
- Keep thresholds fixed before the final test.

## Important caveats
- A score derived as `max(risk, 1-risk)` is not calibrated confidence.
- A small manually authored set is a smoke test, not a validated benchmark.
- Exact-text test overrides must be disabled or explicitly excluded from generalization claims.
- A successful classification test does not prove that a protected LLM or RAG application is secure.
- Avoid claims such as “100% secure” or “guaranteed prompt injection prevention.”

## Results table template
| Method | Accuracy | Precision | Recall | F1 | FPR | FNR | Review rate | Median latency |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Regex-only | — | — | — | — | — | — | N/A | — |
| ML-only | — | — | — | — | — | — | N/A | — |
| Combined | — | — | — | — | — | — | — | — |

Populate this table only with results from the finalized held-out test set.
