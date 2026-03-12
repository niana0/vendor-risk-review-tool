# Vendor GRC Review: AI-Assisted Workflow
### Presentation Summary

Streamlining vendor security reviews with AI-driven analysis and document intelligence.

---

### The Problem

Vendor risk reviews are time-intensive and require pulling context from multiple sources simultaneously: Jira tickets, vendor websites, prior precedents, security certifications, and breach history. A single review can take 1–3 hours of research and writing before any vendor documentation is even analyzed. As the volume of vendor requests grows, this becomes a bottleneck — reviews slow down procurement, and documentation quality varies with available time.

---

### The Solution: A Two-Part AI-Assisted Workflow

The workflow consists of two connected tools that cover the full review lifecycle — from a new ticket to a finalized, documented risk assessment.

**Part 1 — The `/vendor-risk-review` Skill (Claude Code)**

A custom skill invoked directly from the terminal or IDE. Given a vendor name or Jira ticket ID, it:
- Fetches the PRIV and VRM tickets and all comments
- Searches for precedent tickets — same vendor, same vendor category, similar use cases
- Runs a live web search for security certifications, known breaches, CVEs, and privacy compliance posture
- Applies the internal privacy and security triage matrices to determine risk levels
- Produces a structured initial review: vendor overview, risk assessment (privacy + security, step-by-step), precedent analysis, privacy implementation controls, actions table, and risk summary
- Saves the review to a vendor-named markdown file, which the Streamlit app picks up automatically

**Part 2 — The Vendor Security Assessment Tool (Streamlit web app)**

A local web UI that picks up where the skill left off. It displays the initial review automatically and offers three review modes via tabs:

| Tab | Use case | Input | Output |
|---|---|---|---|
| Vendor Documentation Review | Vendor provided SOC 2, pen test, or policies | Vendor PDFs/Excel | Security doc findings + Final Vendor Risk Review (if initial review exists) |
| Completed Questionnaire Review | Vendor filled out our security questionnaire | Vendor-completed Excel | Annotated questionnaire with security findings flagged (High/Medium/Low) |
| Auto-Fill Questionnaire | Need to fill our questionnaire from vendor docs | Vendor docs + blank Excel | Completed questionnaire answered from vendor docs using RAG + GPT-4o |

Each tab is self-contained — reviewers use whichever mode matches the documentation they have.

---

### How It Works in Practice

| Step | Action | Time |
|---|---|---|
| 1 | Run `/vendor-risk-review <ticket-id>` | ~2–3 min |
| 2 | Review the initial output, adjust if needed | ~10–15 min |
| 3 | Upload vendor security docs to the relevant tab | ~2 min |
| 4 | Review the final output, finalize disposition | ~15–20 min |
| 5 | Post summaries to Jira | ~2 min |

Total: **~30–40 minutes** for a complete documented review, versus 2–3 hours manually.

---

### What It Doesn't Do

The tool assists the reviewer — it does not make decisions. Every output requires human review before being finalized or posted to Jira. The reviewer remains responsible for the disposition. The tool handles the research, structure, and first draft; the reviewer applies judgment.

---

### Manager Q&A

**Q: Is the AI making the compliance decision?**
No. The tool produces a research summary and a draft risk assessment, but the reviewer reads, validates, and approves every output before anything is posted to Jira or shared. The disposition — Approve, Approve with Conditions, Further Review Required, Reject — is always a human decision. The AI handles the grunt work: pulling context, applying the triage matrix, and drafting the document.

---

**Q: What if the AI gets something wrong?**
That's why the workflow includes a human review step. The reviewer checks the output against what they know — the triage criteria, internal precedents, and their own judgment. In practice, the main failure modes are missing context (e.g., a ticket with sparse information) or an overly conservative risk determination. Both are easy to catch on review. The tool also cites every source (Jira ticket, web URL, document page reference), so claims can be verified directly.

---

**Q: How is this different from just asking ChatGPT to write a review?**
Several ways. First, it's connected to live internal data — it reads Jira tickets and comments in real time, not a static description you paste in. Second, it applies our specific triage criteria and review structure, not a generic framework. Third, when vendor documents are uploaded, it extracts answers with source citations and confidence levels, rather than summarizing loosely. Finally, outputs are saved as structured files in a defined format, ready for posting to Jira and archiving.

---

**Q: Could this be used by other teams beyond Privacy and Security?**
Yes, with some adaptation. The skill and triage logic are specific to our VRM/PRIV process today, but the underlying structure — pull ticket context, search for precedents, apply criteria, produce a draft — is applicable to other review workflows. The Vendor Security Assessment Tool is already general-purpose for any vendor that provides a SOC 2, pen test, security questionnaire, or policy documents.

---

**Q: How do we maintain it as our process changes?**
The review structure, triage criteria, and output format live in a single file (`SKILL.md`). When the internal privacy triage matrix changes, or a new control category is added, we update that file. No code changes required for most process updates. The Streamlit app has a separate questionnaire file (`.xlsx`) that maps security questions to document evidence — that can also be updated independently.

---

**Q: What does it cost to run?**
The skill uses the Claude API (Anthropic). The Vendor Security Assessment Tool uses the OpenAI API for document analysis (GPT-4o) and embeddings (text-embedding-3-large). The Streamlit app runs locally, so there's no hosting cost.

Cost per review depends on which tabs are used:

| Scenario | Estimated cost |
|---|---|
| Skill only (no vendor docs) | ~$0.07 |
| Skill + Vendor Documentation Review (SOC 2 + pen test + 1 policy) | ~$0.27 |
| Skill + Completed Questionnaire Review (50-question questionnaire) | ~$0.16 |
| Skill + both of the above | ~$0.36 |
| Skill + Auto-Fill Questionnaire (50 questions, large doc set) | ~$0.45 |
| All three tabs + skill | ~$0.74 |

The most expensive path is Auto-Fill Questionnaire, where the RAG pipeline retrieves 8 document chunks per question and sends them to GPT-4o in batches — costs scale with questionnaire length and document volume. Most reviews fall in the **$0.07–$0.45 range**, under $1 in all cases, which is negligible relative to reviewer time saved.

*Pricing basis: Claude Sonnet 4.6 at $3.00/$15.00 per MTok (input/output); GPT-4o at $2.50/$10.00 per MTok; text-embedding-3-large at $0.13/MTok. Verify current API rates before presenting.*

---

**Q: What data does the tool access?**
The skill accesses Jira (read-only via the Atlassian API) and performs web searches. The Vendor Security Assessment Tool processes uploaded vendor documents locally and sends excerpts to the OpenAI API for analysis — no Datadog internal data is sent to external APIs. Vendor documents are not stored or retained beyond the session.

---

**Q: Why does the workflow start in the terminal instead of the web app? Can everything be done in one place?**
The split exists for a practical reason: the initial review needs Jira access and live web search, and the Streamlit app doesn't have either. The `/vendor-risk-review` skill piggybacks on Claude Code's built-in Atlassian MCP integration and web search — no additional APIs needed. The Streamlit app handles the document analysis side using OpenAI.

To unify everything in the UI would require adding a Jira REST API integration, a web search API, and the Anthropic SDK to the Streamlit app — doable, but not yet built. The end state would be: enter a ticket ID in the UI, the app fetches Jira context and searches the web, generates the initial review, and you upload vendor docs — all in one session. That's the natural next version if the tool gets adopted more broadly.

---

**Q: What happens when there's no Jira ticket?**
The skill works without a ticket — you can invoke it with just a vendor name and it will conduct the web research and produce an initial review based on public information. You then fill in the internal context manually. This is useful for proactive reviews or when a ticket hasn't been created yet. The Streamlit app also works independently — any of the three review tabs can be used without a prior initial review.

---

**Q: How long did this take to build?**
The initial skill and tool were built and iterated over a few sessions. Most of the development time went into the triage logic, the output structure, and aligning the tool's questionnaire with real vendor documentation patterns (SOC 2 report formats, CAIQ structures). Ongoing maintenance is low — mostly updating the skill file when the review process evolves.
