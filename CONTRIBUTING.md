# Contributing to AltFix

Thanks for helping make documentation more accessible. AltFix is small on purpose, so most contributions are focused and bounded.

## Getting set up

```bash
git clone https://github.com/dreynox/AltFix.git
cd AltFix
pip install -e ".[dev]"
pytest -q
```

The test suite uses synthetic inputs and never calls a model, so it finishes in a couple of seconds. You do **not** need LM Studio or a GPU to contribute.

To run AltFix against a real model, install [LM Studio](https://lmstudio.ai), load a multimodal model and start the local server:

```bash
export ALTFIX_BASE_URL=http://localhost:1234/v1
export ALTFIX_MODEL=qwen3.5-9b
altfix scan .
```

## Ground rules

- **Never fabricate a result.** Every number in the README comes from a saved run in `results/`. Every alt text AltFix writes comes from a real model call. If a call fails, the image is marked *needs review*.
- **No special cases for the fixtures.** Rules and prompts must be generic. If a change only helps one image in `eval/fixtures/`, it is the wrong change.
- **Keep the diffs surgical.** The patcher must only ever change alt text. There is a test for this and it must stay green.
- **No heavy dependencies.** `httpx`, `typer`, `rich` and `pillow` are the current set. No web UI, no cloud APIs, no LangChain.

## Running the evaluation

```bash
python eval/run.py                 # writes results/results.json and results/RESULTS.md
python eval/run.py --no-cache      # force a fresh model call for every image
python eval/rate.py export         # write the rating sheet
python eval/rate.py score          # score the sheet you filled in
```

If you change a prompt, bump `ALTFIX_PROMPT_VERSION` (or `DEFAULT_PROMPT_VERSION` in `src/altfix/config.py`). It is part of the cache key, so old cached answers will not be reused.

## Good first issues

These are all small, self-contained and do not need a model server:

- **Support for `<figure>` / `<figcaption>` in HTML.** The scanner reads `<img>` but ignores `<figcaption>`, which is often the best context available for a description.
- **Add `.htm` and `.markdown` to the scanned extensions.** The extension map lives in `src/altfix/scan.py`.
- **Write the results table into the README automatically.** `eval/run.py` already writes `results/RESULTS.md`; a small script could splice that into the `<!-- RESULTS_TABLE -->` marker in `README.md` so the numbers can never go stale.
- **Per-language cache keys.** The cache key covers the model, prompt, image and context, but not the language of the surrounding document.
- **A `--report` flag for `altfix scan`.** Emit a summary of how many images are missing, low quality, ok and decorative per directory.
- **Handle `.rst` `:target:` options.** The RST scanner reads `:alt:` but ignores `:target:` and `:scale:`, which are occasionally useful context.
- **Improve the RST insertion indent.** The inserted `:alt:` option always uses three spaces of indentation; it should match the indent of the surrounding option block.
- **Detect duplicate descriptions.** If two different images get the same alt text, flag it - it usually means the model is not really looking at the image.
- **A `--jobs` option for `altfix fix`.** Describing images is embarrassingly parallel, and the local server can usually handle a few requests at once.
- **Document the accessibility guidelines AltFix follows.** A short `docs/guidelines.md` explaining why 125 characters, why "needs review" exists and when an image should be decorative.

## Pull requests

1. Branch from `main`.
2. Add or update tests for the behaviour you changed.
3. Make sure `pytest -q` passes.
4. If you changed a prompt or a quality rule, run `python eval/run.py` and commit the updated `results/` files, so the numbers in the README stay honest.
5. Open a pull request describing what changed and why.

## Code of conduct

Be kind and constructive. Reviews are about the code, not the person who wrote it.
