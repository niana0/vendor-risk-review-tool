"""
Risk Summary Generator - Updates specific sections of an initial vendor risk review
with findings from uploaded vendor documents.
"""
import os
import glob
from typing import Dict, List, Any
from openai import OpenAI

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "output")


class RiskSummaryGenerator:

    COMPLETION_MODEL = "gpt-4o"

    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        self.client = OpenAI(api_key=api_key) if api_key else None
        self.summary = ""

    def generate(
        self,
        question_mappings: List[Dict[str, Any]],
        evidence_library: List[Dict[str, Any]]
    ) -> str:
        """Update specific sections of the initial review with findings from uploaded documents."""

        if not self.client:
            return "OpenAI API key not configured."

        initial_review = self._load_initial_review()
        qa_context = self._build_qa_context(question_mappings)
        doc_sources = self._list_sources(evidence_library)

        prompt = f"""You are a Vendor GRC reviewer at Datadog. An initial vendor risk review has already been completed. The vendor has now provided security documentation (e.g. SOC 2 reports, pen test reports, security policies), which has been analyzed using a security questionnaire. Your task is to produce the Final Vendor Risk Review — a complete review document that reproduces every section of the initial review, with targeted updates to three sections where the uploaded documents provide relevant information.

## Initial Vendor Risk Review

{initial_review if initial_review else "(No initial review found — generate sections from scratch based on the questionnaire answers below.)"}

## Completed Security Questionnaire (Q&A from Uploaded Documents)

{qa_context}

## Documents Reviewed

{doc_sources}

---

## Risk Triage Criteria

Apply these criteria when re-evaluating risk levels based on document findings:

**Security Risk:**
- HIGH (any one = HIGH): vendor accesses customer data; could impact production confidentiality/integrity/availability; no information security program; SaaS vendor with no penetration testing; security breach in past 2 years
- MEDIUM: vendor accesses internal Datadog data (not production/customer); SOC 2 Type II or ISO 27001 certified; some open audit findings or exceptions
- LOW: vendor does not process Datadog or customer data meaningfully; SOC 2 Type II or ISO 27001 certified AND conducted penetration testing with no critical/high findings

**Privacy Risk:**
- HIGH (any one = HIGH): vendor processes customer personal data (subprocessor); vendor uses AI or automated decision-making; sensitive/special category data; cross-border transfers without adequate mechanism; review triggered by breach
- MEDIUM: vendor processes internal employee personal data (non-sensitive); no customer data, no sensitive categories, no AI
- LOW: no personal data exchanged, or minimal non-sensitive data with no system integration

Note: HIGH triggers from the initial review (e.g., customer data access) remain HIGH unless the document evidence directly eliminates that trigger. Certifications and clean pen tests are mitigating factors but do not override a categorical HIGH trigger on their own.

---

## Instructions

Reproduce the full initial review below, section by section, exactly as written. Then apply the following targeted updates:

**Risk Assessment (Security Risk and Combined Risk Level):**
- Re-evaluate the security risk level using the triage criteria above, taking into account both the factors identified in the initial review AND what the uploaded documents show (SOC 2 opinion, pen test findings, exceptions, audit period, certifications).
- If the vendor has a SOC 2 Type II report with an unqualified opinion and a penetration test with no critical or high findings, this is a significant mitigating factor — apply the criteria and state the updated risk level with a clear rationale.
- If HIGH triggers from the initial review still apply (e.g., customer data access), explain whether the documents mitigate or leave those triggers unchanged.
- Update the security risk level and rationale in the Risk Assessment section if warranted. Update the Combined Risk Level accordingly.
- Do not change the privacy risk level unless the documents directly address a privacy-specific trigger.

**Privacy Implementation Controls:**
- Reproduce the full table with all rows.
- If the uploaded documents provide clear, direct information for a control (e.g., the SOC 2 report confirms RBAC is in place), update the Guidance column for that row to reflect what the documents show. Be specific — state the document type and what it confirms.
- If the documents do not clearly address a control, carry the original guidance forward unchanged. Do not guess or infer.
- Column must be named "Guidance".

**Actions & Follow-ups:**
- Go through every action from the initial review one by one.
- If the uploaded documents fully resolve an action (e.g., a SOC 2 report was provided and the action was "request SOC 2 report"), remove that action — it is closed.
- If the documents partially address an action, keep it and note what remains outstanding in the action text.
- If the documents do not address an action, carry it forward unchanged.
- The result should be a clean, current list of what still needs to be done.

**Risk Review Summary:**
- Reproduce the Recommended Disposition, security risk summary, and privacy risk summary from the initial review.
- Update the security risk summary to reflect the re-evaluated risk level and what the documents confirmed (certifications, pen test outcome, exceptions, audit opinion). Be specific.
- Update the privacy risk summary only where the documents provide materially relevant information.
- Update the Recommended Disposition if the re-evaluated risk level or document findings warrant a change.

---

Now produce the output in two parts:

**Part 1 — What Changed**

Start with a section titled "## What Changed from Initial Review" containing a markdown table with three columns: Section | Before | After.

Rules:
- Include only sections where content actually changed — do not include unchanged sections.
- "Section" should name the specific part that changed (e.g., "Security Risk Level", "RBAC Guidance", "Security Risk Summary", "Combined Risk Level").
- "Before" should quote the exact original text (truncated to ~150 characters if long, ending with "...").
- "After" should quote the exact updated text (truncated to ~150 characters if long, ending with "...").
- If no changes were made at all, write: "No changes from initial review — all sections carried forward as written."
- Do not include a preamble or explanation before the table.

**Part 2 — Final Vendor Risk Review**

Immediately after the What Changed section, output the full Final Vendor Risk Review using the same section structure and headings as the initial review. Do not add a preamble or explanation between the two parts.

---
*Sources consulted: initial vendor risk review + vendor-provided documentation reviewed by the Vendor Security Assessment Tool.*
"""

        try:
            response = self.client.chat.completions.create(
                model=self.COMPLETION_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=4000,
                temperature=0
            )
            self.summary = response.choices[0].message.content.strip()
        except Exception as e:
            self.summary = f"Error generating summary: {e}"

        return self.summary

    def _load_initial_review(self) -> str:
        """Load the most recent initial vendor risk review if it exists.
        Excludes generated output files such as *_final_vendor_risk_review.md."""
        pattern = os.path.join(os.path.abspath(OUTPUT_DIR), "*_review.md")
        files = [
            f for f in glob.glob(pattern)
            if not os.path.basename(f).endswith("_final_vendor_risk_review.md")
        ]
        if not files:
            return ""
        path = max(files, key=os.path.getmtime)
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()

    def _build_qa_context(self, mappings: List[Dict[str, Any]]) -> str:
        """Format completed Q&A pairs for the prompt."""
        lines = []
        for m in mappings:
            confidence = m.get("confidence", "")
            answer = m.get("answer", "")
            source = "; ".join([e["source"] for e in m.get("evidence", []) if e.get("source")])
            lines.append(
                f"**{m['question_id']}**: {m['question']}\n"
                f"Answer [{confidence}]: {answer}\n"
                f"Source: {source if source else 'N/A'}\n"
            )
        return "\n".join(lines)

    def _list_sources(self, evidence_library: List[Dict[str, Any]]) -> str:
        """List unique document sources from the evidence library."""
        seen = set()
        sources = []
        for ev in evidence_library:
            # Extract just the filename (before the first parenthesis)
            source = ev.get("source", "")
            doc_name = source.split("(")[0].strip()
            if doc_name and doc_name not in seen:
                seen.add(doc_name)
                sources.append(f"- {doc_name}")
        return "\n".join(sources) if sources else "- No documents listed"

    def to_docx(self, output_path: str = "output/vendor_risk_summary.docx") -> str:
        """Save the generated summary as a Word document."""
        from src.docx_utils import markdown_to_docx
        doc = markdown_to_docx(self.summary)
        doc.save(output_path)
        return output_path

    def to_markdown(self, output_path: str = "output/vendor_risk_summary.md") -> str:
        """Save the generated summary to a markdown file."""
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(self.summary)
        return output_path
