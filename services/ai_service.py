import os, re, json, requests
from typing import Dict, Any, List, Optional

DEFAULT_GEMINI_MODEL = "gemini-1.5-flash"

class AIService:
    _instance = None

    def __init__(self):
        self.api_key = os.getenv('GOOGLE_API_KEY') or os.getenv('GEMINI_API_KEY') or ''
        self.model = os.getenv('GEMINI_MODEL') or DEFAULT_GEMINI_MODEL
        self._genai_configured = False
        self._setup_sdk()

    def _setup_sdk(self):
        if self.api_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.api_key)
                self._genai_configured = True
            except Exception as e:
                print(f"[AI Service] google.generativeai configuration note: {e}")
                self._genai_configured = False

    def reload_config(self):
        self.api_key = os.getenv('GOOGLE_API_KEY') or os.getenv('GEMINI_API_KEY') or ''
        self.model = os.getenv('GEMINI_MODEL') or DEFAULT_GEMINI_MODEL
        self._setup_sdk()

    def _call_gemini_api(self, prompt: str, system_instruction: Optional[str] = None) -> str:
        """Call Gemini API via SDK if installed, or direct HTTPS REST endpoint."""
        if not self.api_key:
            raise ValueError("Gemini API key is not configured.")

        # Attempt SDK call first if available
        if self._genai_configured:
            try:
                import google.generativeai as genai
                model = genai.GenerativeModel(self.model, system_instruction=system_instruction)
                response = model.generate_content(prompt)
                return response.text
            except Exception as sdk_err:
                print(f"[AI Service] SDK call error: {sdk_err}, falling back to REST endpoint...")

        # Direct REST API call
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        headers = {"Content-Type": "application/json"}
        
        contents = []
        if system_instruction:
            contents.append({
                "role": "user",
                "parts": [{"text": f"SYSTEM INSTRUCTION: {system_instruction}"}]
            })
            contents.append({
                "role": "model",
                "parts": [{"text": "Understood. I will strictly follow these instructions."}]
            })
            
        contents.append({
            "role": "user",
            "parts": [{"text": prompt}]
        })

        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": 0.2,
                "topP": 0.95,
                "maxOutputTokens": 4096
            }
        }

        resp = requests.post(url, headers=headers, json=payload, timeout=60)
        if resp.status_code != 200:
            raise RuntimeError(f"Gemini API returned HTTP {resp.status_code}: {resp.text}")

        res_data = resp.json()
        try:
            candidates = res_data.get('candidates', [])
            if candidates and 'content' in candidates[0]:
                parts = candidates[0]['content'].get('parts', [])
                if parts:
                    return parts[0].get('text', '')
        except Exception as pe:
            raise RuntimeError(f"Failed parsing Gemini API response: {pe}")

        return ""

    def _sanitize_json_output(self, raw_text: str) -> str:
        text = raw_text.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            text = "\n".join(lines).strip()
        return text

    def analyze_document(self, extracted_text: str, filename: str = "Document") -> Dict[str, Any]:
        """Generate structured analysis of document text using Gemini, or fallback to real-text heuristic extraction."""
        if not extracted_text or not extracted_text.strip():
            return self._empty_analysis(filename, "Document text was empty.")

        # Limit document text to prevent exceeding context window (keep first ~40,000 chars)
        truncated_text = extracted_text[:40000]
        if len(extracted_text) > 40000:
            truncated_text += "\n\n[... Note: Text truncated for analysis due to length ...]"

        # If API key is not present, generate realistic heuristic analysis from REAL text
        if not self.api_key:
            return self._generate_heuristic_analysis(extracted_text, filename, missing_key=True)

        system_instruction = (
            "You are AI DOC, a world-class AI document intelligence platform. "
            "Analyze the uploaded document with rigorous factual accuracy. "
            "Base every single point, date, obligation, party, and term strictly on the provided text. "
            "Do NOT hallucinate or assume facts not stated in the document. "
            "If information is missing, explicitly note that it is not provided. "
            "You MUST output valid, parseable JSON conforming strictly to the requested schema."
        )

        prompt = f"""Analyze the following real document text from file '{filename}'.

Document Text:
\"\"\"
{truncated_text}
\"\"\"

Output a single JSON object with EXACTLY this structure:
{{
  "document_type": "Specific type of document (e.g., Commercial Lease, Employment Agreement, NDA, Invoice, Policy, Report, Resume, Notice, General)",
  "summary": "Clear, professional executive summary of the document (2-4 paragraphs).",
  "main_purpose": "Primary objective or intent of this document.",
  "key_points": [
    "Crucial takeaway or main clause 1",
    "Crucial takeaway or main clause 2",
    "Crucial takeaway or main clause 3"
  ],
  "important_dates": [
    {{
      "date": "Exact date string as found in document",
      "event": "Description of deadline, effective date, expiration, or milestone",
      "type": "Effective Date | Deadline | Expiration | Renewal | Milestone"
    }}
  ],
  "parties_or_entities": [
    {{
      "name": "Name of party, organization, or authority",
      "role": "Role (e.g. Employer, Contractor, Licensor, Client, Auditor, Individual)",
      "type": "Organization | Individual | Department | Authority"
    }}
  ],
  "obligations": [
    {{
      "party": "Party responsible",
      "responsibility": "What they must do, deliver, or refrain from doing"
    }}
  ],
  "risks_or_warnings": [
    {{
      "title": "Concise risk or attention title",
      "severity": "Attention | Important | Informational",
      "description": "Specific condition, potential liability, penalty, or missing required detail"
    }}
  ],
  "action_items": [
    "Recommended concrete next step for the user"
  ],
  "simplified_explanation": "A plain-language, easy-to-understand breakdown of complex sections or clauses.",
  "key_terms": [
    {{
      "term": "Specialized term or acronym from the text",
      "explanation": "Clear, simple explanation of what it means in context"
    }}
  ]
}}
"""
        try:
            raw_response = self._call_gemini_api(prompt, system_instruction=system_instruction)
            cleaned_json = self._sanitize_json_output(raw_response)
            data = json.loads(cleaned_json)
            return self._normalize_analysis(data, filename)
        except Exception as e:
            print(f"[AI Service] Error calling Gemini: {e}. Falling back to real-text heuristic analysis.")
            return self._generate_heuristic_analysis(extracted_text, filename, error_note=str(e))

    def ask_question(self, extracted_text: str, question: str, conversation_history: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
        """Answer user questions grounded exclusively in the uploaded document text."""
        if not question or not question.strip():
            return {
                "success": False,
                "error": "Question cannot be empty. Please ask a specific question about the document."
            }

        if not extracted_text or not extracted_text.strip():
            return {
                "success": False,
                "error": "No document text available to answer from."
            }

        truncated_text = extracted_text[:40000]

        if not self.api_key:
            return self._heuristic_qa(extracted_text, question)

        system_instruction = (
            "You are the AI DOC Assistant. Your job is to answer user questions accurately based "
            "STRICTLY on the provided document text. "
            "Cite relevant sections or clauses where possible. "
            "If the document does not contain enough information to answer the question, clearly state: "
            "'The uploaded document does not provide information about this.' "
            "Do not make up facts or extrapolate beyond the document."
        )

        history_context = ""
        if conversation_history:
            for item in conversation_history[-4:]:
                history_context += f"User: {item.get('question', '')}\nAssistant: {item.get('answer', '')}\n"

        history_block = f"Recent Conversation History:\n{history_context}\n" if history_context else ""

        prompt = f"""Document Content:
\"\"\"
{truncated_text}
\"\"\"

{history_block}
User Question: {question.strip()}

Provide a helpful, direct, and structured answer based strictly on the document text.
"""
        try:
            raw_answer = self._call_gemini_api(prompt, system_instruction=system_instruction)
            return {
                "success": True,
                "answer": raw_answer.strip(),
                "model": self.model
            }
        except Exception as e:
            print(f"[AI Service] Gemini Q&A error: {e}. Falling back to document excerpt matcher.")
            return self._heuristic_qa(extracted_text, question, error_note=str(e))

    def _normalize_analysis(self, data: dict, filename: str) -> dict:
        """Ensure all expected keys exist and have valid types."""
        return {
            "document_type": str(data.get("document_type") or "General Document"),
            "summary": str(data.get("summary") or "Summary generated from document content."),
            "main_purpose": str(data.get("main_purpose") or "To document terms, details, and information."),
            "key_points": list(data.get("key_points") or []),
            "important_dates": list(data.get("important_dates") or []),
            "parties_or_entities": list(data.get("parties_or_entities") or []),
            "obligations": list(data.get("obligations") or []),
            "risks_or_warnings": list(data.get("risks_or_warnings") or []),
            "action_items": list(data.get("action_items") or []),
            "simplified_explanation": str(data.get("simplified_explanation") or ""),
            "key_terms": list(data.get("key_terms") or []),
            "analysis_engine": "Gemini AI"
        }

    def _generate_heuristic_analysis(self, text: str, filename: str, missing_key: bool = False, error_note: Optional[str] = None) -> dict:
        """Extract structured real data from the actual document text using rule-based parsing."""
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if len(s.strip()) > 15]

        # Determine document type heuristic
        lower_text = text.lower()
        doc_type = "General Document"
        if any(w in lower_text for w in ["agreement", "contract", "parties", "hereby agreed"]):
            doc_type = "Legal Agreement / Contract"
        elif any(w in lower_text for w in ["invoice", "bill to", "due date", "amount due", "subtotal"]):
            doc_type = "Financial Invoice / Statement"
        elif any(w in lower_text for w in ["policy", "privacy policy", "terms of service", "terms & conditions"]):
            doc_type = "Policy / Terms Document"
        elif any(w in lower_text for w in ["resume", "curriculum vitae", "education", "experience", "skills"]):
            doc_type = "Resume / Curriculum Vitae"
        elif any(w in lower_text for w in ["report", "audit", "findings", "executive summary"]):
            doc_type = "Audit / Business Report"

        # Summary from first few key paragraphs
        summary_paras = []
        for p in paragraphs[:4]:
            if len(p) > 40 and not p.startswith("---"):
                summary_paras.append(p)
        summary = " ".join(summary_paras) if summary_paras else (sentences[0] if sentences else "Document uploaded and parsed successfully.")
        if len(summary) > 600:
            summary = summary[:597] + "..."

        # Important dates extraction via regex
        date_pattern = r'\b(?:(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4}|\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\b\d{4}-\d{2}-\d{2}\b)'
        found_dates = re.findall(date_pattern, text, re.IGNORECASE)
        important_dates = []
        seen_dates = set()
        for d in found_dates:
            d_clean = d.strip()
            if d_clean not in seen_dates:
                seen_dates.add(d_clean)
                ctx = "Mentioned in document"
                for s in sentences:
                    if d in s:
                        ctx = s[:120] + ("..." if len(s) > 120 else "")
                        break
                dtype = "Milestone"
                if any(w in ctx.lower() for w in ["effective", "commence", "start"]):
                    dtype = "Effective Date"
                elif any(w in ctx.lower() for w in ["due", "deadline", "by"]):
                    dtype = "Deadline"
                elif any(w in ctx.lower() for w in ["expire", "term", "end"]):
                    dtype = "Expiration"
                elif any(w in ctx.lower() for w in ["renew"]):
                    dtype = "Renewal"

                important_dates.append({
                    "date": d_clean,
                    "event": ctx,
                    "type": dtype
                })
            if len(important_dates) >= 6:
                break

        # Key points extraction
        key_points = []
        for s in sentences:
            s_low = s.lower()
            if any(k in s_low for k in ["important", "agrees", "provided that", "responsible", "purpose", "shall not", "includes", "scope"]):
                if s not in key_points and len(s) < 250:
                    key_points.append(s)
            if len(key_points) >= 5:
                break
        if not key_points and sentences:
            key_points = sentences[:4]

        # Obligations: sentences containing "shall", "must", "agrees to"
        obligations = []
        for s in sentences:
            s_low = s.lower()
            if any(w in s_low for w in [" shall ", " must ", " required to ", " agrees to ", "responsible for"]):
                party_match = re.search(r'\b(user|client|customer|company|contractor|party|parties|employee|employer)\b', s_low)
                party = party_match.group(1).capitalize() if party_match else "Specified Party"
                obligations.append({
                    "party": party,
                    "responsibility": s.strip()
                })
            if len(obligations) >= 5:
                break

        # Entities extraction: emails and capitalized entities
        parties = []
        emails = re.findall(r'[\w\.-]+@[\w\.-]+', text)
        for em in set(emails[:3]):
            parties.append({
                "name": em,
                "role": "Contact / Signatory",
                "type": "Individual"
            })
        org_matches = re.findall(r'\b([A-Z][A-Za-z0-9&]+(?:\s+[A-Z][A-Za-z0-9&]+)*\s+(?:Inc|LLC|Ltd|Corporation|Company|Bank|Department|Pvt))\b', text)
        for org in set(org_matches[:4]):
            parties.append({
                "name": org,
                "role": "Entity / Organization",
                "type": "Organization"
            })

        # Risks / Warnings: sentences with penalties, termination, liability
        risks = []
        for s in sentences:
            s_low = s.lower()
            if any(w in s_low for w in ["liability", "penalty", "indemn", "breach", "terminate", "forfeit", "loss", "dispute", "confidential"]):
                sev = "Important" if "terminate" in s_low or "breach" in s_low else "Attention"
                risks.append({
                    "title": "Significant Clause / Condition",
                    "severity": sev,
                    "description": s.strip()
                })
            if len(risks) >= 4:
                break

        if not risks:
            risks.append({
                "title": "Document Notice",
                "severity": "Informational",
                "description": "No explicit penalty or liability clauses detected in basic scan."
            })

        action_items = [
            "Review extracted key terms and verify accuracy against the original document.",
            "Confirm all important dates and calendar any upcoming deadlines.",
            "Verify obligations for all involved parties prior to sign-off or action."
        ]

        # Key terms from document
        key_terms = []
        term_matches = re.findall(r'\"([A-Za-z\s]{3,30})\"\s+means\s+([^.]+)', text, re.IGNORECASE)
        for tm, exp in term_matches[:4]:
            key_terms.append({
                "term": tm.strip(),
                "explanation": exp.strip()
            })
        if not key_terms:
            key_terms = [
                {"term": "Document Scope", "explanation": f"Refers to the overall content and specifications set forth in {filename}."},
                {"term": "Effective Period", "explanation": "The timeline during which the provisions of this document apply."}
            ]

        engine_note = "Local Heuristic Intelligence Engine"
        if missing_key:
            engine_note += " (Gemini API key not configured; configure GOOGLE_API_KEY in .env for advanced AI)"
        elif error_note:
            engine_note += f" (Gemini API fallback: {error_note[:60]})"

        return {
            "document_type": doc_type,
            "summary": summary,
            "main_purpose": f"To establish the provisions, details, and context specified in {filename}.",
            "key_points": key_points,
            "important_dates": important_dates,
            "parties_or_entities": parties,
            "obligations": obligations,
            "risks_or_warnings": risks,
            "action_items": action_items,
            "simplified_explanation": f"This document ({doc_type}) sets forth terms and information regarding {filename}. Key terms and dates should be carefully reviewed.",
            "key_terms": key_terms,
            "analysis_engine": engine_note
        }

    def _heuristic_qa(self, text: str, question: str, error_note: Optional[str] = None) -> dict:
        """Answer question by searching document paragraphs for highest keyword overlap."""
        q_words = set(re.findall(r'\w+', question.lower())) - {'what', 'when', 'where', 'who', 'how', 'is', 'the', 'a', 'an', 'in', 'on', 'of', 'for', 'to', 'this', 'document', 'about'}
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

        scored_paras = []
        for p in paragraphs:
            p_words = set(re.findall(r'\w+', p.lower()))
            overlap = len(q_words & p_words)
            if overlap > 0:
                scored_paras.append((overlap, p))

        scored_paras.sort(key=lambda x: x[0], reverse=True)

        if scored_paras:
            top_matches = [p for _, p in scored_paras[:3]]
            answer_body = "\n\n".join(top_matches)
            answer = f"Based on the uploaded document:\n\n{answer_body}"
        else:
            answer = f"The uploaded document does not appear to explicitly address '{question}'. Please check your phrasing or review the document summary."

        if error_note:
            answer += f"\n\n*(Note: Generated via document text search; Gemini API returned: {error_note[:80]})*"
        elif not self.api_key:
            answer += "\n\n*(Note: Generated via document text search because GOOGLE_API_KEY is not configured)*"

        return {
            "success": True,
            "answer": answer,
            "model": "local-search"
        }

    def _empty_analysis(self, filename: str, reason: str) -> dict:
        return {
            "document_type": "Empty Document",
            "summary": f"Could not analyze {filename}: {reason}",
            "main_purpose": "N/A",
            "key_points": [],
            "important_dates": [],
            "parties_or_entities": [],
            "obligations": [],
            "risks_or_warnings": [{"title": "Extraction Empty", "severity": "Attention", "description": reason}],
            "action_items": ["Upload a non-empty document with extractable text."],
            "simplified_explanation": reason,
            "key_terms": [],
            "analysis_engine": "None"
        }

ai_service = AIService()
