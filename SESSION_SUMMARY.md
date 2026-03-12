# Vendor Review Tool v1.0 — Session Summary

## Project Location
`/Users/ana.ni/Documents/Obsidian Vault/Claude Code projects/Vendor Review Tool v1.0`

---

## What This Tool Does

A Streamlit web app for GRC vendor risk reviews. Two-phase workflow:

1. **Initial Review** — Claude runs `/vendor-risk-review <ticket-id>` (fetches Jira, searches web, applies triage, writes `output/{vendor_slug}_review.md`). The app detects and displays this automatically.

2. **Document Analysis** — User uploads vendor documents to one of three tabs:

| Tab | Input | Pipeline | Output |
|---|---|---|---|
| Vendor Documentation Review | Vendor PDFs/Excel | DocumentParser → EvidenceExtractor → SecurityDocReviewer → RiskSummaryGenerator* | Security Doc Review + Final Vendor Risk Review* (Word) |
| Completed Questionnaire Review | Vendor-completed Excel | CompletedQuestionnaireReviewer (GPT-4o) | Annotated Excel with Finding column |
| Auto-Fill Questionnaire | Vendor docs + blank Excel | DocumentParser → EvidenceExtractor → QuestionnaireMapper → RiskAssessor | Completed questionnaire (Excel) |

*Final Vendor Risk Review only generated when an initial review (`*_review.md`) exists.

---

## Key Files

| File | Purpose |
|---|---|
| `app.py` | Streamlit UI — three tabs, three process functions, three display functions |
| `SKILL.md` | `/vendor-risk-review` skill definition |
| `.claude/commands/vendor-risk-review.md` | Copy of SKILL.md registered as CLI slash command |
| `PRESENTATION.md` | Tool summary + manager Q&A |
| `src/security_doc_reviewer.py` | Extracts structured findings from SOC 2, pen test, policy docs |
| `src/completed_questionnaire_reviewer.py` | Reviews vendor-answered questionnaires; flags findings by severity; outputs annotated Excel |
| `src/risk_summary_generator.py` | Generates Final Vendor Risk Review (GPT-4o, updates initial review) |
| `src/questionnaire_mapper.py` | RAG: embeds chunks + questions, retrieves top-8, answers with GPT-4o |
| `src/risk_assessor.py` | Scores questionnaire confidence levels into risk report |
| `src/evidence_extractor.py` | Chunks parsed docs into searchable evidence library |
| `src/document_parser.py` | Parses PDF and Excel files |
| `src/docx_utils.py` | Markdown-to-docx converter |
| `output/{vendor_slug}_review.md` | Initial review written by Claude; read by app and risk_summary_generator |

---

## How to Run

```bash
cd "/Users/ana.ni/Documents/Obsidian Vault/Claude Code projects/Vendor Review Tool v1.0"
source venv/bin/activate
streamlit run app.py
```

---

## Current Behaviour

### UI
- Default theme: dark
- "Start New Review" button resets session and deletes the current `*_review.md`
- All output files are vendor-prefixed: `{vendor_slug}_*.docx/xlsx/md`
- Initial Vendor Risk Review displayed in a collapsible expander (collapsed by default) on all three tabs
- Final Vendor Risk Review displayed in a collapsible expander (collapsed by default), followed by What Changed block

### Tab 1 — Vendor Documentation Review

Layout order:
1. Initial Vendor Risk Review (collapsible expander)
2. Final Vendor Risk Review (collapsible expander) — only when initial review exists
3. What Changed from Initial Review (table, always visible below the expander)
4. Security Documentation Review
5. Downloads

- Upload: vendor PDFs/Excel (multi-file)
- Runs: DocumentParser → EvidenceExtractor → SecurityDocReviewer → (optionally) RiskSummaryGenerator
- Final Vendor Risk Review section only appears when `output/*_review.md` exists
- Downloads: Final Vendor Risk Review (Word), Security Doc Review (Word)

### Tab 2 — Completed Questionnaire Review
- Upload: single vendor-completed Excel
- Runs: CompletedQuestionnaireReviewer (GPT-4o in batches of 10)
- Findings flagged as High / Medium / Low (Critical removed)
- Colors: High = red, Medium = orange, Low = green
- Metrics row: Total Questions | Findings | High | Medium | Low
- Findings grouped by severity in UI; each expander shows question, vendor answer, finding, recommendation
- Download: Excel with all original columns + "Finding" column (severity + title, color-coded)

### Tab 3 — Auto-Fill Questionnaire
- Upload: vendor docs (multi) + blank questionnaire (single Excel)
- Runs: DocumentParser → EvidenceExtractor → QuestionnaireMapper (RAG + GPT-4o) → RiskAssessor
- Confidence: HIGH / MEDIUM / LOW / NOT_FOUND
- Filter by confidence level; questions sorted numerically
- Download: Completed questionnaire (Excel)

---

## Output Files

| File | Tab | Contents |
|---|---|---|
| `{vendor}_vendor_risk_summary.docx` | Vendor Documentation Review | Final Vendor Risk Review (Word) |
| `{vendor}_security_doc_review.docx` | Vendor Documentation Review | SOC 2, pen test, policy findings (Word) |
| `{vendor}_final_vendor_risk_review.md` | Vendor Documentation Review | Final review (Markdown) |
| `{vendor}_questionnaire_findings.xlsx` | Completed Questionnaire Review | Original Q&A + Finding column |
| `{vendor}_completed_questionnaire.xlsx` | Auto-Fill Questionnaire | Answered questionnaire with confidence + sources |

---

## Vendor Reviews Conducted

| Vendor | File | Disposition |
|---|---|---|
| Petual AI | `output/petual_review.md` | APPROVE WITH CONDITIONS |
| Jess Ellis (JJE Consulting) | `output/jess_ellis_review.md` | APPROVE WITH CONDITIONS |
| Attention (attention.com) | `output/attention_review.md` | APPROVE WITH CONDITIONS (PoC scope only) |

---

## What Changed block (risk_summary_generator.py + app.py)

- `risk_summary_generator.py` prompt updated: GPT-4o now produces a "## What Changed from Initial Review" table at the top of the final review output, before the full review body. Table columns: Section | Before | After. Only changed sections are listed.
- `app.py` — `_split_what_changed(risk_text)`: parses the final review text to separate the What Changed section from the full review body (splits on `\n---\n` separator).
- `app.py` — `_render_what_changed(what_changed)`: renders the What Changed table as markdown.
- `app.py` — `display_vendor_docs_results()`: layout is Final Review expander → What Changed table → Security Documentation Review. If session state predates the prompt change, falls back to loading from `{vendor}_final_vendor_risk_review.md`.
- `app.py` — `get_latest_review_path()`: updated glob to exclude `*_final_vendor_risk_review.md` so generated output files are never mistaken for initial reviews.
- Same exclusion fix applied to `risk_summary_generator._load_initial_review()`.

## Slash command registration

- `.claude/commands/vendor-risk-review.md` created as a copy of `SKILL.md`
- Claude Code CLI now discovers `/vendor-risk-review` automatically when launched from the project directory
- If `SKILL.md` is updated, re-run: `cp SKILL.md .claude/commands/vendor-risk-review.md`

---

## Known Issues / Next Steps
- Debug print statements still present in `to_excel()` in `CompletedQuestionnaireReviewer` — remove before production use.
- If `SKILL.md` is updated, `.claude/commands/vendor-risk-review.md` must be manually kept in sync.
