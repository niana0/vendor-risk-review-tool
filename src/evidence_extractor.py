"""
Evidence Extractor - Extracts security control statements and evidence
"""
import re
from typing import Dict, List, Any
import json


class EvidenceExtractor:
    """Extract security evidence from parsed documents"""

    # Security-related keywords
    SECURITY_KEYWORDS = [
        'encryption', 'authentication', 'authorization', 'access control',
        'audit', 'logging', 'monitoring', 'backup', 'disaster recovery',
        'incident response', 'vulnerability', 'patch management', 'firewall',
        'antivirus', 'malware', 'penetration test', 'security assessment',
        'compliance', 'gdpr', 'hipaa', 'soc 2', 'iso 27001', 'pci dss',
        'data protection', 'privacy', 'confidentiality', 'integrity',
        'availability', 'multi-factor', 'mfa', '2fa', 'ssl', 'tls',
        'certificate', 'key management', 'secrets', 'password policy',
        'security training', 'awareness', 'background check', 'vendor management'
    ]

    def __init__(self):
        self.evidence_library = []

    def extract_from_text(self, text: str, source_ref: str) -> List[Dict[str, Any]]:
        """Extract all paragraphs from text as evidence chunks"""
        evidence_items = []

        # Split into paragraphs by blank lines or large whitespace blocks
        paragraphs = re.split(r'\n{2,}', text)

        for paragraph in paragraphs:
            paragraph = paragraph.strip()

            # Skip very short chunks (headers, page numbers, etc.)
            if len(paragraph) < 50:
                continue

            # If paragraph is too long, break it into ~500 char chunks at sentence boundaries
            if len(paragraph) > 500:
                sentences = re.split(r'(?<=[.!?])\s+', paragraph)
                chunk = ""
                for sentence in sentences:
                    if len(chunk) + len(sentence) <= 500:
                        chunk += " " + sentence
                    else:
                        if chunk.strip():
                            evidence_items.append({
                                "text": chunk.strip(),
                                "source": source_ref,
                                "type": "paragraph"
                            })
                        chunk = sentence
                if chunk.strip():
                    evidence_items.append({
                        "text": chunk.strip(),
                        "source": source_ref,
                        "type": "paragraph"
                    })
            else:
                evidence_items.append({
                    "text": paragraph,
                    "source": source_ref,
                    "type": "paragraph"
                })

        return evidence_items

    def extract_from_table(self, table_data: List[List], source_ref: str) -> List[Dict[str, Any]]:
        """Extract evidence from tables"""
        evidence_items = []

        if not table_data or len(table_data) < 2:
            return evidence_items

        # Assume first row is headers
        headers = table_data[0] if table_data else []

        for row_idx, row in enumerate(table_data[1:], 1):
            row_text = ' '.join([str(cell) for cell in row if cell])

            # Check for security keywords in row
            row_lower = row_text.lower()
            matched_keywords = [kw for kw in self.SECURITY_KEYWORDS if kw in row_lower]

            if matched_keywords:
                evidence_items.append({
                    "text": row_text,
                    "keywords": matched_keywords,
                    "source": f"{source_ref} (Row {row_idx})",
                    "confidence": "high",  # Table data usually more structured
                    "type": "table_entry",
                    "row_data": dict(zip(headers, row)) if len(headers) == len(row) else None
                })

        return evidence_items

    def extract_certifications(self, text: str, source_ref: str) -> List[Dict[str, Any]]:
        """Extract certification and compliance statements"""
        certs = []

        # Common certification patterns
        cert_patterns = [
            r'SOC\s*[123]\s*Type\s*[12]',
            r'ISO\s*27001',
            r'ISO\s*27017',
            r'ISO\s*27018',
            r'PCI\s*DSS',
            r'HIPAA',
            r'GDPR',
            r'CCPA',
            r'FedRAMP'
        ]

        for pattern in cert_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                # Get context around match
                start = max(0, match.start() - 100)
                end = min(len(text), match.end() + 100)
                context = text[start:end].strip()

                certs.append({
                    "certification": match.group(),
                    "context": context,
                    "source": source_ref,
                    "confidence": "high",
                    "type": "certification"
                })

        return certs

    def extract_all(self, parsed_documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract evidence from all parsed documents"""
        self.evidence_library = []

        for doc in parsed_documents:
            filename = doc.get('filename', 'unknown')

            # Extract from PDF pages
            if doc['type'] == 'pdf':
                for page in doc.get('pages', []):
                    page_num = page['page_num']
                    text = page['text']
                    source_ref = f"{filename} (Page {page_num})"

                    # Extract text evidence
                    self.evidence_library.extend(self.extract_from_text(text, source_ref))

                    # Extract certifications
                    self.evidence_library.extend(self.extract_certifications(text, source_ref))

                # Extract from tables
                for table in doc.get('tables', []):
                    source_ref = f"{filename} (Page {table['page']}, Table {table['table_index']})"
                    self.evidence_library.extend(self.extract_from_table(table['data'], source_ref))

            # Extract from Excel sheets
            elif doc['type'] == 'excel':
                for sheet in doc.get('sheets', []):
                    sheet_name = sheet['sheet_name']
                    source_ref = f"{filename} (Sheet: {sheet_name})"

                    # Convert sheet data to text for keyword extraction
                    all_text = ' '.join([
                        ' '.join([str(cell) for cell in row if cell])
                        for row in sheet['data']
                    ])

                    self.evidence_library.extend(self.extract_from_text(all_text, source_ref))
                    self.evidence_library.extend(self.extract_from_table(sheet['data'], source_ref))

        return self.evidence_library

    def to_json(self, output_path: str = "evidence_library.json"):
        """Save evidence library to JSON"""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.evidence_library, f, indent=2, ensure_ascii=False)
        return output_path
