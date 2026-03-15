import os
from pathlib import Path

import chromadb

from app.config import REGULATORY_DATA_DIR, settings

CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
COLLECTION_NAME = "regulatory_docs"


def _chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    words = text.split()
    chunks = []
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunk = " ".join(words[start:end])
        if chunk.strip():
            chunks.append(chunk)
        start = end - overlap
    return chunks


def _load_regulatory_docs() -> list[tuple[str, str]]:
    """Load all markdown files from regulatory_data directory.
    Returns list of (filename, content) tuples."""
    docs: list[tuple[str, str]] = []
    reg_dir = Path(REGULATORY_DATA_DIR)
    if not reg_dir.exists():
        return docs
    for md_file in sorted(reg_dir.glob("*.md")):
        content = md_file.read_text(encoding="utf-8")
        docs.append((md_file.stem, content))
    return docs


class RAGService:
    def __init__(self):
        self._client = None
        self.collection = None

    def _get_client(self):
        if self._client is None:
            persist_dir = settings.chroma_persist_dir
            os.makedirs(persist_dir, exist_ok=True)
            self._client = chromadb.PersistentClient(path=persist_dir)
        return self._client

    def initialize(self):
        """Load regulatory documents and index them."""
        self.collection = self._get_client().get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )

        # Skip if already populated
        if self.collection.count() > 0:
            return

        docs = _load_regulatory_docs()
        all_chunks = []
        all_ids = []
        all_metadata = []

        for doc_name, content in docs:
            chunks = _chunk_text(content)
            for i, chunk in enumerate(chunks):
                all_chunks.append(chunk)
                all_ids.append(f"{doc_name}_chunk_{i}")
                all_metadata.append({"source": doc_name, "chunk_index": i})

        if all_chunks:
            self.collection.add(
                documents=all_chunks,
                ids=all_ids,
                metadatas=all_metadata,  # type: ignore[arg-type]
            )

    def retrieve(self, query: str, top_k: int = 5) -> list[dict]:
        """Retrieve relevant regulatory text chunks for a query."""
        if self.collection is None or self.collection.count() == 0:
            self.initialize()

        assert self.collection is not None  # guaranteed after initialize()

        if self.collection.count() == 0:
            return []

        results = self.collection.query(
            query_texts=[query],
            n_results=min(top_k, self.collection.count()),
        )

        chunks = []
        if results and results.get("documents") and results.get("metadatas"):
            docs = results["documents"][0]
            metas = results["metadatas"][0]
            dists = results["distances"][0] if results.get("distances") else [None] * len(docs)
            for i, doc in enumerate(docs):
                chunks.append(
                    {
                        "text": doc,
                        "source": metas[i].get("source", "unknown") if i < len(metas) else "unknown",
                        "distance": dists[i] if i < len(dists) else None,
                    }
                )
        return chunks

    def get_context_for_template(self, template_type: str, questionnaire_data: dict) -> str:
        """Build a regulatory context string for a specific template type."""
        queries = {
            "ai_acceptable_use": [
                "AI ethics principles acceptable use transparency accountability",
                "Privacy Act personal information AI tools approved prohibited",
                "AI governance policies staff training human oversight",
            ],
            "data_classification": [
                "data classification personal information sensitive confidential restricted",
                "Privacy Act APPs collection use disclosure security personal information",
                "AI data handling cross-border disclosure encryption access controls",
            ],
            "incident_response": [
                "notifiable data breaches NDB scheme OAIC notification serious harm",
                "AI incident response detection containment recovery lessons learned",
                "privacy breach automated decisions fairness accountability",
            ],
            "vendor_risk_assessment": [
                "APP 8 cross-border disclosure overseas providers vicarious liability",
                "vendor data processing agreements sub-processors audit rights",
                "AI vendor risk management due diligence onboarding assessment",
            ],
            "ai_ethics_framework": [
                "Australia AI ethics principles fairness transparency accountability",
                "human oversight AI decision-making bias testing explainability",
                "responsible AI governance safety fairness privacy contestability",
            ],
            "employee_ai_training": [
                "OAIC guidance staff training AI privacy awareness obligations",
                "AI acceptable use employee responsibilities data handling",
                "shadow AI risks training frequency compliance awareness",
            ],
            "ai_risk_register": [
                "AI risk assessment likelihood impact mitigation controls",
                "privacy risks automated decisions cross-border data security",
                "AI6 essential practices risk management governance framework",
            ],
            "privacy_policy": [
                "Australian Privacy Principles APP 1 privacy policy requirements",
                "POLA Act automated decision disclosure transparency obligations",
                "personal information collection use disclosure consent APP 3 APP 6",
            ],
            "board_ai_briefing": [
                "board directors duty of care AI governance material risks",
                "Corporations Act AI oversight executive accountability",
                "AI regulatory landscape POLA Act Privacy Act compliance timeline",
            ],
            "remediation_action_plan": [
                "compliance remediation action plan gap analysis prioritisation",
                "AI governance implementation roadmap timeline milestones",
                "regulatory compliance deadlines POLA Act December 2026",
            ],
            "ai_transparency_statement": [
                "AI transparency explainability disclosure public accountability",
                "POLA Act automated decision disclosure types personal information",
                "AI ethics principle 6 transparency explainability AI6 share information",
            ],
            "ai_data_retention": [
                "APP 11 destruction de-identification personal information retention",
                "data retention AI outputs prompts logs deletion obligations",
                "AI data lifecycle management storage archival destruction",
            ],
            "ai_procurement": [
                "AI vendor evaluation procurement assessment criteria due diligence",
                "APP 8 cross-border disclosure vendor data processing agreements",
                "AI tool onboarding privacy impact assessment security certification",
            ],
        }

        template_queries = queries.get(template_type, queries["ai_acceptable_use"])

        all_chunks = []
        seen = set()
        for query in template_queries:
            chunks = self.retrieve(query, top_k=3)
            for chunk in chunks:
                if chunk["text"] not in seen:
                    seen.add(chunk["text"])
                    all_chunks.append(chunk)

        if not all_chunks:
            return ""

        context_parts = []
        for chunk in all_chunks[:8]:
            context_parts.append(f"[Source: {chunk['source']}]\n{chunk['text']}")

        return "\n\n---\n\n".join(context_parts)


# Singleton
rag_service = RAGService()
