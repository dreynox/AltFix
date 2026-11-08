# AltFix Accessibility Guidelines & Rationale

This document outlines the core accessibility standards, design principles, and technical rationale underlying AltFix.

---

## 1. Regulatory & Standards Alignment

AltFix adheres to the **W3C Web Content Accessibility Guidelines (WCAG) 2.2** at Level AA, specifically:

- **WCAG Guideline 1.1 Text Alternatives**: Provide text alternatives for any non-text content so that it can be changed into other forms people need, such as large print, braille, speech, symbols or simpler language.
- **Success Criterion 1.1.1 Non-text Content (Level A)**: All non-text content that is presented to the user has a text alternative that serves the equivalent purpose.

---

## 2. Core Heuristics & Rules

### A. The 125-Character Budget
- **Screen Reader Navigation**: Popular screen readers (JAWS, NVDA, VoiceOver) treat alt text as single continuous speech units. Lengthy descriptions interrupt reading flow, cannot easily be skimmed, and force users to listen through entire paragraphs before reaching relevant document content.
- **Conciseness Target**: Alt text should summarize the content in one sentence (≤ 125 characters). If an image contains complex data (e.g. detailed architectural topologies or 50 data points in a chart), the documentation body should include an accompanying data table or descriptive paragraph, while the alt text acts as a concise anchor (e.g., *"Quarterly revenue bar chart comparing Q1 to Q4 2024"*).

### B. Why AltFix Strips Filler Phrases
- Phrases such as `"Image of"`, `"Picture showing"`, or `"Screenshot of"` are redundant. Screen readers automatically announce the HTML `<img>` role or element type (e.g. *"Graphic, Acme Analytics dashboard"*). Repeating "Image of" wastes listening time.
- AltFix deterministically strips these prefixes so the screen reader immediately begins with the image subject.

### C. The `[needs review]` Safety Gate
- **A wrong description is worse than no description**: A hallucinated alt text actively misinforms visually impaired developers.
- When an image description fails quality checks (e.g. generic responses like `"diagram"`, filename echoes like `"arch-v2"`, or server inference timeouts), AltFix retries once with stricter prompting. If it fails a second time, the image is marked `[needs review]` and **never written to disk**.

### D. Decorative vs. Informative Images
- **Informative Images**: Diagrams, screenshots, charts, conceptual illustrations that communicate meaning. These require descriptive alt text.
- **Decorative Images**: Badges (build passing, npm version, shields.io), horizontal spacers, or tracking pixels convey status handled elsewhere in text or serve purely visual layout purposes.
- In Markdown and HTML, decorative images should have empty alt text (`alt=""`) or be left untouched so assistive technology skips them without noise.

---

## 3. Formatting-Specific Rules

| Format | Syntax | Escaping Rules |
| --- | --- | --- |
| **Markdown** | `![alt](src)` | Escapes nested brackets `\[` and `\]` and backslashes |
| **HTML** | `<img src="src" alt="alt">` | Escapes `&quot;`, `&amp;`, `&lt;`, `&gt;` |
| **RST** | `.. image:: src`<br>`   :alt: alt` | Normalizes whitespace; matches existing directive indentation |

---

## 4. Ground Truth Verification & Human In The Loop

AltFix provides interactive review:
```bash
altfix review .
```
Users can step through each proposal:
- `[a]ccept`: Accept proposed alt text and stage patch.
- `[e]dit`: Refine the proposed text interactively.
- `[s]kip`: Leave the image unmodified.
- `[q]uit`: Stop and review staged patches.
