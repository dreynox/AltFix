# AltFix: Hackathon Video Demo Script (2:30 Walkthrough)

This script is structured for a 2 to 3-minute video recording suitable for Devpost and MLH judge evaluation.

---

### [0:00 - 0:30] The Hook & Problem Statement
- **Visual**: Show a repository `README.md` on GitHub containing a complex architecture diagram and a metrics chart, with cursor inspecting element: `alt=""` or `alt="screenshot"`.
- **Narration**:
  > *"Over 80% of open-source documentation has images with missing or useless alt text like 'screenshot' or 'image'. For screen reader users and visually impaired developers, critical charts and diagrams are completely invisible.*
  >
  > *Most teams don't fix this because writing alt text at scale is tedious, and cloud AI APIs require uploading private company docs and proprietary screenshots to third parties. Today, we're introducing **AltFix**: an open-source, local-first CLI that fixes documentation alt text with surgical diff purity and zero network leakage."*

---

### [0:30 - 1:00] Step 1: Scanning the Repository
- **Visual**: Terminal window.
- **Action**: Run `altfix scan demo/sample_repo --report`
- **Narration**:
  > *"Let's test AltFix on a sample documentation repository. We run `altfix scan --report`. In milliseconds, our multi-format AST scanner parses Markdown, MDX, HTML, and RST documents.*
  >
  > *Notice the breakdown: it classifies every image into missing, low quality, ok, or decorative—automatically ignoring badges and tracking pixels so you never waste time on them."*

---

### [1:00 - 1:40] Step 2: Local AI Generation & Deterministic Quality Checks
- **Visual**: Terminal window.
- **Action**: Run `altfix demo`
- **Narration**:
  > *"Now, let's fix the missing alt text using `altfix demo`.*
  >
  > *AltFix sends the image and its surrounding context—such as section headings and adjacent paragraphs—to a local open-weight vision model running on our machine via LM Studio.*
  >
  > *No data leaves the laptop. The generated description goes through deterministic quality checks: stripping quotes, removing filler phrases like 'image of', enforcing a strict 125-character WCAG budget, and preventing filename echoes."*
- **Visual**: Highlight the unified diff table showing only `alt="..."` being changed.

---

### [1:40 - 2:05] Step 3: Interactive Review & Human in the Loop
- **Visual**: Terminal window.
- **Action**: Run `altfix review demo/sample_repo`
- **Narration**:
  > *"AltFix believes that a wrong description is worse than no description. With `altfix review`, developers can interactively inspect each proposed alt text, accept it, edit it in real time, or skip it before applying."*
- **Action**: Press `a` to accept first item, `q` to exit.

---

### [2:05 - 2:30] Step 4: 100% Diff Purity & CI/CD
- **Visual**: Split screen: VS Code git diff and `.github/workflows/altfix-check.yml`.
- **Narration**:
  > *"When we inspect the patch, we see 100% diff purity: character spans outside the alt attribute are byte-exact and untouched.*
  >
  > *And with our new GitHub Action wrapper (`action.yml`), teams can drop AltFix into their CI pipelines to catch inaccessible documentation on every pull request.*
  >
  > *Make your documentation accessible to everyone, everywhere, privately with AltFix. Thank you!"*

