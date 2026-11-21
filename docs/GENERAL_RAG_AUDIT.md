# General RAG 0.6.1 experiment-integrity audit

**Overall verdict: PASS. Review independence: same-family. Acceptance status: provisional. External human review: false.**

No open experiment-integrity blocker was found. This verdict checks consistency of the frozen retrieval evidence and qualified publication claims. It does not promote the failed candidate; G0 TF-IDF remains the release recommendation.

Date: 2026-10-23. Auditor: fresh inherited Codex subagent; exact model identifier is unavailable. No paid API calls, retrieval reruns, model inference, evaluator edits or result edits were made by this auditor.

## Verified extent

- Bound 138 input-file hashes in the companion JSON.
- Verified 35 frozen inputs, 8 frozen artifacts, 18 archived source copies, 43 source snapshots and 12 project-provenance entries.
- Recomputed 1,920 raw/delivered question scores from 960 records and checked 17,035 returned chunk occurrences.
- Recomputed all 24 paired intervals, checked all six selected development thresholds and all 389 failure rows.
- Read all 80 questions, 40 target groups, eleven knowledge cards, the evaluator/retriever code, review history and final published claims.

## A. Ground truth provenance: PASS

The labels are source-grounded programmatic evidence spans with model-authored Chinese questions. All 80 question texts, 40 paired targets and eleven cards were read. All 100 per-question quote occurrences (38 evidence groups, 50 unique alternative definitions) match exact source offsets and complete chunks. Fact groups and evidence groups do not cross development/test.

G0 has 14 chunks. G1 has 65 and retains the original 14 unchanged. Every existing target is covered in G0; every new target requires added knowledge. Missing-information negatives are distinct from supported negative capability answers.

The initial rejection and four findings are preserved. Final questions remove redundant requirements, add complete equivalent alternatives, combine arithmetic consequences with their source facts, and correctly identify MPD as a database. Final review binds the current dataset SHA. Saved chronology: final camera revision 15:32:22 UTC, accepted review 15:37:10, freeze 15:38:23, then development selection before heldout output. No evidence of retrieval-rank-derived ground truth was found. Records and filesystem timestamps are not externally notarized proof of execution history.

Official algorithm documentation, project rules, research conclusions and prior measured visual results remain distinguished. Saved sources support Gamma, SSIM, CLAHE, model-weight and MPD statements. Frozen visual summaries support AP, working-point, calibration, diagnostic and SICE statements. Those source facts do not make this a new visual evaluation.

Evidence:

- [general_rag_questions.json:4](<private-repository/eval/general_rag_questions.json:4>) - Source-grounded authoring
- [general_rag_eval.py:75](<private-repository/optical_agent/general_rag_eval.py:75>) - Exact offsets and split checks
- [general_rag_eval.py:123](<private-repository/optical_agent/general_rag_eval.py:123>) - Preserved original corpus
- [label_review_initial.md:9](<D:/CodexData/optical_agent/rag/general_v061/label_review_initial.md:9>) - Preserved initial blockers
- [authoring_manifest.json:704](<D:/CodexData/optical_agent/rag/general_v061/authoring_manifest.json:704>) - Final revision timestamp
- [label_review.json:4](<D:/CodexData/optical_agent/rag/general_v061/label_review.json:4>) - Accepted dataset binding
- [label_review.json:10](<D:/CodexData/optical_agent/rag/general_v061/label_review.json:10>) - Review timestamp
- [freeze.json:4](<D:/CodexData/optical_agent/rag/general_v061/run_20261023/freeze.json:4>) - Freeze timestamp
- [GENERAL_V2_ENHANCEMENT.md:7](<private-repository/knowledge/GENERAL_V2_ENHANCEMENT.md:7>) - MPD database
- [cvpr2025_machine_iqa.txt:18](<D:/CodexData/optical_agent/rag/general_v061/sources/cvpr2025_machine_iqa.txt:18>) - Saved official abstract
- [skimage_exposure_020.txt:63](<D:/CodexData/optical_agent/rag/general_v061/sources/skimage_exposure_020.txt:63>) - Gamma formula
- [skimage_metrics_020.txt:778](<D:/CodexData/optical_agent/rag/general_v061/sources/skimage_metrics_020.txt:778>) - SSIM parameters
- [opencv_histogram_3414_official_source.md:43](<D:/CodexData/optical_agent/rag/general_v061/sources/opencv_histogram_3414_official_source.md:43>) - CLAHE official fallback source
- [GENERAL_EVALUATION.md:23](<D:/CodexData/optical_agent/rag/general_v061/sources/project_v060/docs/GENERAL_EVALUATION.md:23>) - Frozen visual measurements

## B. Scores and denominators: PASS

Independently recomputed 1,920 raw/delivered question scores from 960 records across 2 splits, 2 corpora, 3 methods and 2 threshold stages. Recall@1/3/5/10, first-relevant MRR@10, full evidence hits, missing evidence and negative-return flags all match. Aggregate, old/new and multi-evidence summaries match. All 17,035 returned chunk occurrences match their frozen corpus contents.

Recall divides unique retrieved required evidence groups by source-defined required groups. MRR is reciprocal rank of the first relevant chunk. Overlapping chunks never create additional evidence credit. All primary profiles use 30 answerable questions and 10 negatives; G0 new-only questions stay in its denominator. Negatives are excluded from Recall/MRR.

All 24 paired confidence intervals reproduce with fact-group resampling, seed 20261023 and 2,000 repetitions. Old-target comparisons use 10 answerable groups; all-answerable comparisons use 15. Hybrid minus TF-IDF tuned G1 R@3 is -0.20, CI [-0.35, -0.05].

No performance denominator comes from the predictions' maximum, minimum or mean. Embedding unit normalization and cosine/RRF scores are retrieval components. Raw retrieval and threshold-filtered delivery are reported separately.

Evidence:

- [rag_eval.py:49](<private-repository/optical_agent/rag_eval.py:49>) - Evidence matching
- [rag_eval.py:56](<private-repository/optical_agent/rag_eval.py:56>) - Recall and MRR
- [rag_eval.py:75](<private-repository/optical_agent/rag_eval.py:75>) - Denominators
- [rag_eval.py:87](<private-repository/optical_agent/rag_eval.py:87>) - Fact-group bootstrap
- [general_rag_eval.py:252](<private-repository/optical_agent/general_rag_eval.py:252>) - G0 primary denominator
- [test.json:126038](<D:/CodexData/optical_agent/rag/general_v061/run_20261023/test.json:126038>) - G1 TF-IDF tuned
- [test.json:171573](<D:/CodexData/optical_agent/rag/general_v061/run_20261023/test.json:171573>) - G1 embedding tuned
- [test.json:217764](<D:/CodexData/optical_agent/rag/general_v061/run_20261023/test.json:217764>) - G1 hybrid tuned
- [summary.json:176](<D:/CodexData/optical_agent/rag/general_v061/run_20261023/summary.json:176>) - Algorithm intervals
- [GENERAL_RAG_RESULTS.md:116](<private-repository/docs/GENERAL_RAG_RESULTS.md:116>) - Published interval

## C. Files, claims and selection: PASS

All 35 freeze input hashes, 8 frozen artifact hashes, 18 archived repository source copies, 43 source snapshots and 12 project-provenance entries match. Both indexes have correct hashes, finite 512-dimensional vectors and unit norms within floating-point error. Corpus fingerprints and the G0 original baseline match.

Published RESULTS.json and FAILURES.csv are byte-identical to frozen summary.json and failures.csv. The CSV contains 389 expected failure rows: 198 development and 191 test. Six publication/config artifacts match the public repository copies. Both README result statements match the frozen values.

All six threshold choices satisfy the recorded development-grid objective. Hybrid is correctly preselected: development G1 R@3 73.33%, versus TF-IDF 65% and embedding 56.67%. The selection lock binds freeze and selection; heldout uses selected profiles and does not tune them.

Heldout G1 tuned R@3 is 80% / 25% / 60%, MRR 0.850 / 0.300 / 0.616667, negative false returns 1/10 / 0/10 / 0/10 for TF-IDF / embedding / hybrid. Hybrid fails method, old-knowledge and actual-release guards. Actual release remains G0 TF-IDF at 0.10/0.75; no heldout runner-up was promoted.

The publication's stale pending-review sentence was corrected before final hash binding. Historical authoring records retain pre-review states, superseded by the exact hash-bound accepted review. Frozen evaluator inputs and results were preserved.

Evidence:

- [freeze.json:30](<D:/CodexData/optical_agent/rag/general_v061/run_20261023/freeze.json:30>) - Input identities
- [freeze.json:67](<D:/CodexData/optical_agent/rag/general_v061/run_20261023/freeze.json:67>) - Artifact identities
- [selection.lock.json:2](<D:/CodexData/optical_agent/rag/general_v061/run_20261023/selection.lock.json:2>) - Selection lock
- [selection.json:6002](<D:/CodexData/optical_agent/rag/general_v061/run_20261023/selection.json:6002>) - Candidate
- [dev.json:215865](<D:/CodexData/optical_agent/rag/general_v061/run_20261023/dev.json:215865>) - Dev hybrid result
- [general_rag_eval.py:355](<private-repository/optical_agent/general_rag_eval.py:355>) - Locked execution
- [general_rag_eval.py:434](<private-repository/optical_agent/general_rag_eval.py:434>) - Preselected candidate gate
- [decision.json:8](<D:/CodexData/optical_agent/rag/general_v061/run_20261023/decision.json:8>) - Failed promotion
- [decision.json:27](<D:/CodexData/optical_agent/rag/general_v061/run_20261023/decision.json:27>) - Retained baseline
- [general_rag_release.json:4](<private-repository/knowledge/general_rag_release.json:4>) - Actual release
- [GENERAL_RAG_RESULTS.md:29](<private-repository/docs/GENERAL_RAG_RESULTS.md:29>) - Published values
- [README.md:13](<private-repository/README.md:13>) - Private README
- [README.md:50](<public-repository/README.md:50>) - Public README
- [GENERAL_RAG_SOURCES.json:34](<private-repository/docs/GENERAL_RAG_SOURCES.json:34>) - Completed review wording
- [publish_general_rag_v061.py:107](<workspace-artifacts/publish_general_rag_v061.py:107>) - Publication-only wording correction

## D. Called metrics, outputs and timing: PASS

The CLI calls the general evaluator. Its active pipeline calls scoring, aggregate summaries, latency, release decision, confidence intervals and failure-table export. Saved results contain these outputs. Historical C0/C1 routines in rag_eval.py are separate; this experiment uses only its shared scoring/statistics helpers.

Timing occurs after tuned thresholds are installed, on CPU. Query caches are cleared for each warm timing and an immediate cached timing is recorded separately. Each split has 40 distinct texts repeated five times (200 timings), not 200 independent samples. Model load is excluded and separately reported.

The archived run REPORT.md places the same latency in both threshold tables under a generic heading. The final published report explicitly calls it tuned-configuration timing and says fixed thresholds were not separately timed. No fixed-versus-tuned speed comparison is supported. The legacy independent_questions field denotes distinct texts, not independent facts; final documentation explains that distinction and confidence intervals use fact groups.

The auditor did not rerun retrieval, model inference or heldout evaluation. Statistics were independently recomputed from saved outputs; code paths and frozen identities were inspected.

Evidence:

- [evaluate_general_rag.py:16](<private-repository/optical_agent/experiments/evaluate_general_rag.py:16>) - CLI calls evaluator
- [general_rag_eval.py:284](<private-repository/optical_agent/general_rag_eval.py:284>) - Scoring calls
- [general_rag_eval.py:390](<private-repository/optical_agent/general_rag_eval.py:390>) - Fixed/tuned calls and timing
- [general_rag_eval.py:327](<private-repository/optical_agent/general_rag_eval.py:327>) - Latency procedure
- [general_rag_eval.py:485](<private-repository/optical_agent/general_rag_eval.py:485>) - Statistics/report calls
- [test.json:240934](<D:/CodexData/optical_agent/rag/general_v061/run_20261023/test.json:240934>) - Hybrid timing
- [REPORT.md:11](<D:/CodexData/optical_agent/rag/general_v061/run_20261023/REPORT.md:11>) - Archived generic timing heading
- [GENERAL_RAG_RESULTS.md:9](<private-repository/docs/GENERAL_RAG_RESULTS.md:9>) - Correct timing qualification
- [GENERAL_RAG_RESULTS.md:125](<private-repository/docs/GENERAL_RAG_RESULTS.md:125>) - Distinct texts versus facts

## E. Scope and claim strength: PASS

Actual scope: one local model revision, two corpora, three retrieval algorithms, fixed and development-selected rejection profiles, 80 authored questions and 40 fact groups. Each split has 40 texts from 20 groups: 30 answerable texts from 15 groups and 10 negative texts from five groups. Paraphrases and timing repetitions are not additional independent facts.

Final documentation calls this a small project retrieval experiment and explicitly excludes real LLM answer quality, generated citation correctness, visual improvement and multi-agent gains. Off-target retrieval IDs are not reported as erroneous generated citations. No unsupported comprehensive or externally validated benchmark claim was found.

Same-family review remains provisional; external human review is false. Results support this frozen authored benchmark, not broad deployment rejection guarantees or general retriever superiority.

Evidence:

- [authoring_manifest.json:25](<D:/CodexData/optical_agent/rag/general_v061/authoring_manifest.json:25>) - Questions/fact groups
- [freeze.json:131](<D:/CodexData/optical_agent/rag/general_v061/run_20261023/freeze.json:131>) - No external human review
- [GENERAL_RAG.md:48](<private-repository/docs/GENERAL_RAG.md:48>) - Question scope
- [GENERAL_RAG.md:54](<private-repository/docs/GENERAL_RAG.md:54>) - Provisional small evaluation
- [GENERAL_RAG_RESULTS.md:86](<private-repository/docs/GENERAL_RAG_RESULTS.md:86>) - No generated citation metric
- [GENERAL_RAG_RESULTS.md:88](<private-repository/docs/GENERAL_RAG_RESULTS.md:88>) - Retrieval-only limits
- [GENERAL_RAG_RESULTS.md:124](<private-repository/docs/GENERAL_RAG_RESULTS.md:124>) - Fact group units
- [general_rag_release.json:38](<private-repository/knowledge/general_rag_release.json:38>) - Correct scope fields

## F. Evaluation type: PASS

Classification: source_grounded_model_authored_retrieval_benchmark; coarse skill taxonomy: synthetic_proxy.

Precise classification: source-grounded, model-authored retrieval benchmark with exact source-span relevance labels and same-family provisional semantic review. In the skill's coarse taxonomy, synthetic_proxy is the closest category because queries and relevance annotations are project-authored, not an official independent human benchmark.

This is not real_gt detector evaluation, human_eval, an official external retrieval benchmark or real LLM answer-quality evaluation. Prior COCO measurements in cards are source content for retrieval questions and were not produced by this retrieval experiment.

No fake-ground-truth pattern was found: source labels precede retrieval and do not treat the evaluated retriever's output as the reference.

Evidence:

- [general_rag_questions.json:4](<private-repository/eval/general_rag_questions.json:4>) - Authored queries
- [label_review.json:5](<D:/CodexData/optical_agent/rag/general_v061/label_review.json:5>) - Same-family review
- [GENERAL_V2_RESULTS.md:3](<private-repository/knowledge/GENERAL_V2_RESULTS.md:3>) - Prior measurements as content
- [general_rag_eval.py:296](<private-repository/optical_agent/general_rag_eval.py:296>) - No generated answers
- [GENERAL_RAG_SOURCES.json:34](<private-repository/docs/GENERAL_RAG_SOURCES.json:34>) - Authored/review limits
- [GENERAL_RAG_RESULTS.md:88](<private-repository/docs/GENERAL_RAG_RESULTS.md:88>) - Retrieval-only scope

## Claim impact

| Claim | Impact | Scope |
|---|---|---|
| G1 tuned heldout Recall@3 80% / 25% / 60% | supported | TF-IDF / embedding / hybrid; 30 answerable texts from 15 fact groups |
| Knowledge expansion improves overall fixed-TF-IDF coverage | supported_with_qualifier | Overall 60% to 80%, but old-target R@3 falls 90% to 80%; new-target R@3 80% |
| G1 Hybrid should replace the default | unsupported_and_correctly_rejected | Failed preset gates; G0 TF-IDF retained |
| Published CPU P95 timings | supported_with_qualifier | Tuned CPU warm queries; fixed thresholds not separately timed |
| 80 independent facts or 200 independent performance samples per split | unsupported_not_claimed | 80 texts / 40 groups total; 200 repeated timings per split |
| LLM answer, vision or multi-agent gains; external human acceptance | unsupported_not_claimed | Outside experiment |

## Concrete blockers

Open integrity blockers: **none**. Candidate promotion remains blocked by the measured failures:

- G1 tuned Hybrid R@3 0.60 versus G1 tuned TF-IDF 0.80 fails the +0.05 gain requirement; MRR 0.616667 versus 0.85 also decreases.
- Same-fixed-threshold Hybrid old-target R@3 decreases 0.90 to 0.80 and MRR 0.85 to 0.75.
- Actual tuned Hybrid old-target R@3/MRR are 0.55/0.55 versus current G0 TF-IDF 0.90/0.90. New-target R@3 0.70 is below 0.80.

## Limits and follow-up

- Exact reviewer model identifier is not exposed; no particular model or cross-family review is claimed.
- Source checks used saved official content and frozen project artifacts; no new external-network verification.
- Hashes and chronological records are consistent but not externally notarized execution evidence.
- Metrics were recalculated from saved rankings; retrieval/inference/heldout were not rerun.
- One model revision and small authored Chinese benchmark cannot establish broad generalization.
- Archived REPORT.md has generic CPU headings; final publication supplies the correct tuned-timing interpretation.

- Retain G0 TF-IDF; integrity PASS is not candidate promotion.
- Preserve frozen inputs, results and both review stages. Future tuning needs a new evaluation version.
- Keep authored-benchmark, fact-group, timing and provisional-review qualifiers in shortened summaries.

Final tests/test_general_rag_release.py fixture uses a case-sensitive GENERAL_ filename prefix to exclude the live lowercase release JSON on Windows. This fixture-only correction was read and its final hash is bound; it does not change frozen evaluator inputs or results.

The publication provenance wording correction is included in the final bound hashes. Historical authoring records and frozen results remain preserved. The companion JSON contains all input hashes, evidence references, verification counts, claim impacts and chronology.

## Published copy

Private workspace prefixes were replaced with repository labels; the original audit and exact local paths remain on D. `private-repository` and `public-repository` identify the corresponding source tree, not downloadable local-file links. Local experiment artifacts are not included in Git.
