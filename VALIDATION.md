# Validation — v0.3 (2026-11-02)

- **39 tests passed** on Python 3.12. One upstream SQLAlchemy deprecation warning from MLflow.
- New deterministic regressions cover the observed Qwen exact-to-more-than number drift, unsupported Groq authority/partnership statements, comma vs sentence boundary, decimal points, Arabic digits, equivalent approximate/minimum qualifiers, percent changes, selected negation patterns, source-supported partners, Latin source names, literal case constraints and uniqueness/count of the 24 synthetic evaluation cases.
- Existing Groq/Ollama contract, API, frozen-input comparison, preflight and MLflow persistence tests remain passing. Model calls in these tests use mock inference or mocked HTTP, not live model generation.
- Versioned v1/v2 prompts and A/B configurations use the same revised evaluator. No old smoke score is presented as directly comparable with the new evaluator.
- Configs, case JSONL, debugger JSON and Python sources are parsed. Package excludes .env secrets, runtime databases and generated results.

Not verified here: live model quality improvement, real-provider A/B or full-suite results, GPU runtime or Docker deployment of this release, cloud trace ingestion, GitHub CI or remote Git publication. Earlier user logs validate earlier deployment only. Regex heuristics can produce false positives/negatives; no semantic correctness guarantee or automatic quality winner is claimed.

See QUALITY_UPGRADE_AR.md for the exact live verification commands and review rubric.

## Earlier release validation

# Validation — v0.2 (2026-11-02)

Python 3.12; MLflow 3.17.2; LangSmith 0.14.16; Groq SDK 0.37.1; FastAPI 0.162.0. Direct tested dependencies are pinned in requirements-tested.txt; optional semantic/transitive dependencies are not fully locked.

## Executed

- **29 tests passed**. One upstream SQLAlchemy deprecation warning from MLflow.
- Includes the original 18 tests plus native Ollama HTTP request/response fixtures, token/time mapping, Qwen3 thinking flag, incomplete/empty/truncated response rejection, sanitized provider failures, model inventory/digest extraction, GPT-OSS token budget and reasoning options.
- Controlled comparison tests persist real MLflow runs and artifacts in local SQLite using mock generation. They verify identical request hashes across candidates for each case, warmup exclusion, no invented monetary costs, no automatic quality winner, and failed evaluation tags when every case fails.
- Source Python syntax and Compose YAML structure parsed; API, MLflow and benchmark point to one shared Docker image.
- Packaged source scanned for the previously exposed Groq key pattern; no .env credentials or runtime databases included.

## Not executed here

- Real Groq requests, account inventory, billed comparison or live LangSmith cloud trace rendering. User has demonstrated earlier API requests/traces in the conversation; this changed release still needs its own smoke run.
- Real Ollama inference or GPU allocation on the user's Windows RTX 3050 machine. HTTP fixtures verify integration contracts, not model quality, memory fit or throughput.
- Docker build and Compose deployment: Docker engine is unavailable in this execution environment. Layer ordering is corrected and a lighter dependency set is used, but no build duration or successful container deployment is claimed for this release.
- E5 model download/inference; default Docker image now uses TF-IDF, with INSTALL_SEMANTIC=true available for an explicit build.
- Human style/meaning/unsupported-claim evaluation, power measurement or peak RAM/VRAM measurement. Runtime snapshots are not peak measurements.

No real-provider results are bundled. No conclusion that Groq, Ollama or a particular model is best is warranted until the user runs a common dataset and reviews the outputs.
