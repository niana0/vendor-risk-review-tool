"""
CLI runner for the Vendor Security Assessment Tool.
Usage: python run.py --docs doc1.pdf doc2.pdf --questionnaire questionnaire.xlsx
"""
import argparse
import os
from dotenv import load_dotenv
from src.document_parser import DocumentParser
from src.evidence_extractor import EvidenceExtractor
from src.questionnaire_mapper import QuestionnaireMapper
from src.risk_assessor import RiskAssessor
from src.risk_summary_generator import RiskSummaryGenerator
from src.security_doc_reviewer import SecurityDocReviewer

load_dotenv()


def main():
    parser = argparse.ArgumentParser(description="Vendor Security Assessment Tool - CLI")
    parser.add_argument("--docs", nargs="+", required=True, help="Vendor document paths (PDF, Excel)")
    parser.add_argument("--questionnaire", required=True, help="Questionnaire Excel file path")
    parser.add_argument("--output", default="output", help="Output directory (default: output)")
    args = parser.parse_args()

    os.makedirs(args.output, exist_ok=True)

    print(f"\n📁 Documents: {args.docs}")
    print(f"📋 Questionnaire: {args.questionnaire}")
    print(f"📂 Output: {args.output}\n")

    # Step 1: Parse documents
    print("📄 Parsing vendor documents...")
    parser_obj = DocumentParser()
    parsed_docs = parser_obj.parse_all(args.docs)
    print(f"   → Parsed {len(parsed_docs)} document(s)")

    # Step 2: Extract evidence
    print("🔍 Extracting document content...")
    extractor = EvidenceExtractor()
    evidence = extractor.extract_all(parsed_docs)
    print(f"   → Extracted {len(evidence)} chunks")

    # Step 3: Load questionnaire and map evidence
    print("📋 Loading questionnaire...")
    mapper = QuestionnaireMapper()
    questions = mapper.load_questionnaire(args.questionnaire)
    print(f"   → Found {len(questions)} questions")

    print("🤖 Answering questions with GPT-4o (this may take a few minutes)...")
    mappings = mapper.map_evidence_to_questions(questions, evidence)

    # Step 4: Risk assessment
    print("⚠️  Performing risk assessment...")
    assessor = RiskAssessor()
    risk_assessment = assessor.assess(mappings)

    # Step 5: Review security documents (SOC, pen test)
    print("🔐 Reviewing security documents (SOC, pen test)...")
    sec_reviewer = SecurityDocReviewer()
    sec_reviewer.review(parsed_docs)
    print(f"   → Found {len(sec_reviewer.findings)} security document(s)")

    # Step 6: Generate vendor risk summary
    print("📝 Generating vendor risk review summary...")
    summary_gen = RiskSummaryGenerator()
    summary_gen.generate(mappings, evidence)

    # Step 7: Save outputs
    print("💾 Saving outputs...")
    excel_path = os.path.join(args.output, "completed_questionnaire.xlsx")
    risk_docx_path = os.path.join(args.output, "risk_assessment_report.docx")
    summary_path = os.path.join(args.output, "vendor_risk_summary.docx")
    sec_doc_path = os.path.join(args.output, "security_doc_review.docx")

    mapper.to_excel(excel_path)
    assessor.to_docx(risk_docx_path)
    summary_gen.to_docx(summary_path)
    sec_reviewer.to_docx(sec_doc_path)

    print(f"\n✅ Done!\n")
    print(f"   📊 Completed questionnaire  : {excel_path}")
    print(f"   📄 Risk assessment report   : {risk_docx_path}")
    print(f"   📋 Vendor risk summary      : {summary_path}")
    print(f"   🔐 Security doc review      : {sec_doc_path}\n")

    # Print quick summary
    print(f"Overall Risk : {risk_assessment['overall_risk']}")
    print(f"Risk Score   : {risk_assessment['risk_score']}/100")
    print(f"Questions    : {risk_assessment['summary']['total_questions']}")
    print(f"High conf.   : {risk_assessment['summary']['answered_high_confidence']}")
    print(f"Not found    : {risk_assessment['summary']['insufficient_evidence']}\n")


if __name__ == "__main__":
    main()
