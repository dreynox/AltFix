# AltFix - MLH Hackathon Submission

## 💡 Inspiration
Over 80% of open-source documentation contains diagrams, charts, and terminal screenshots with completely empty or useless alt text (like `"image"` or `"screenshot"`). Screen-reader users navigating GitHub READMEs and docs pages are left completely in the dark.

Existing automated solutions usually rely on cloud AI APIs (sending private company documentation and screenshots to third parties) or complex multi-agent frameworks that hallucinate verbose paragraphs and break Markdown syntax.

We asked: *Can we fix documentation accessibility locally, privately, and with mathematical diff purity?* That's why we built **AltFix**.

---

## 🚀 What It Does
**AltFix finds images in your documentation that have no alt text, describes them with a local open-weight vision model (Qwen3.5-9B), and patches only the alt attributes with 100% diff purity.**

- **Multi-Format Scanner**: Recursively scans `.md`, `.markdown`, `.mdx`, `.html`, and `.rst` files, skipping code blocks, `<pre>`, and literal fences while extracting rich context (headings, captions, adjacent paragraphs, and links).
- **Zero-Network Privacy**: All multimodal inference runs locally on your machine via LM Studio or any OpenAI-compatible local server. Zero bytes leave your machine.
- **Deterministic Quality Rules**: No second LLM as a judge. It strips quotes, `<think>` blocks, and filler words like "Image of", enforces a hard 125-character WCAG budget, and rejects filename echoes.
- **Span-Accurate Diff Purity**: Edits exact character spans. Running AltFix twice changes nothing the second time (100% idempotent).
- **Interactive Review & PR Automation**: Interactive CLI review (`altfix review`), automated Git branch & PR generation (`altfix pr`), and GitHub Action CI/CD integration (`action.yml`).

---

## 🛠️ How We Built It
- **Language & CLI**: Built in Python 3.11+ using `typer` and `rich` for an accessible terminal UI.
- **Core Vision Pipeline**: Communicates with local open-weight models (`Qwen3.5-9B`) using `httpx` and `Pillow` for smart client-side downscaling.
- **Smart 4-Part Cache**: Custom content-addressed disk cache keyed by `sha256(model | prompt_version | image_hash | context_hash)` ensuring instantaneous deterministic re-runs.
- **Evaluation Harness**: Programmatic synthetic fixture generator (`eval/make_fixtures.py`) covering charts, dashboards, diagrams, and screenshots, with a ground-truth benchmark suite (`eval/run.py` and `eval/rate.py`).

---

## 📊 Benchmark Results
We evaluated AltFix against our synthetic benchmark suite of 28 documentation images:
- **Detection Recall**: **100.0%** (13/13 problematic images detected)
- **Detection Precision**: **100.0%** (0 false positives)
- **Classification Accuracy**: **100.0%** (28/28 correctly sorted)
- **Quality Check Pass Rate**: **100.0%** (all ≤125 chars, 0 filler phrases)
- **Diff Purity**: **100.0%** (0 bytes touched outside alt text attributes)
- **Human Rating**: **1.92 / 2.0 (4.8 / 5.0)**

---

## 🧗 Challenges We Ran Into
1. **Preserving Document Layout & Byte Integrity**: Replacing text in raw Markdown or RST without disturbing formatting, indentation, or surrounding links required computing exact byte spans and custom escaping for Markdown brackets (`\[...\]`), HTML quotes (`&quot;`), and RST directive indentation.
2. **Preventing AI Hallucinations**: Vision models frequently start with filler phrases ("This image displays a...") or echo image filenames. We built a strict two-stage retry mechanism with deterministic regex checks that marks failing outputs as `[needs review]` instead of polluting documents.

---

## 🏆 Accomplishments We're Proud Of
- **100% Diff Purity**: Our patcher modifies only the exact alt text attribute—surrounding prose, links, and code blocks remain 100% untouched.
- **Comprehensive Test Suite**: 143 unit and integration tests passing in under 2 seconds with >80% code coverage.
- **Instant Reproducible Demo**: A bundled demo mode (`altfix demo`) that works instantly out-of-the-box without requiring a running model or GPU.

---

## 🔮 What's Next For AltFix
- **Live OCR Integration**: Adding local OCR (like Tesseract or PaddleOCR) to enhance reading of small text in screenshots.
- **Multi-lingual Alt Text**: Supporting multi-language document translation for internationalized open-source projects.
- **Pre-commit Hook**: Publishing an official `pre-commit` hook to automatically catch missing alt text before commits are pushed.

