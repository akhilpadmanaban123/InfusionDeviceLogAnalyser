import os
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[2]))
from openai import OpenAI
from backend.config import OPENAI_API_KEY, OPENAI_BASE_URL
from db.lancedb_manager import RequirementDatabase
from backend.requirement_embedder.embedder import get_embedding, build_embed_input
from backend.requirement_embedder.pdf_extractor import extract_pdf_to_text, process_text_file
import random

class QueryHandler:
    def __init__(self, rag_data_path):
        self.rag_data_path = Path(rag_data_path)
        self.powerlog_info = self._load_powerlog_info()
        self.client = OpenAI(
            api_key=OPENAI_API_KEY,
            base_url=OPENAI_BASE_URL
        )
        self.req_db = RequirementDatabase()
        self.confirmation_pending = False
        self.pending_query = None

    

    def _load_powerlog_info(self):
        file_path = self.rag_data_path / 'powerlogInfo.txt'
        if file_path.exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        return ""

    def _is_requirement_query(self, query):
        keywords = ["requirement", "show", "find"]
        return any(keyword in query.lower() for keyword in keywords)

    def _sync_requirements(self):
        raw_pdf_dir = self.rag_data_path / "raw_pdfs"
        extracted_text_dir = self.rag_data_path / "extracted_texts"
        extracted_text_dir.mkdir(parents=True, exist_ok=True)

        pdf_files = {p.stem for p in raw_pdf_dir.glob("*.pdf")}
        extracted_files = {p.stem for p in extracted_text_dir.glob("*.txt")}

        new_pdfs = pdf_files - extracted_files

        if new_pdfs:
            print(f"Found {len(new_pdfs)} new PDFs to extract.")
            for pdf_stem in new_pdfs:
                pdf_file = raw_pdf_dir / f"{pdf_stem}.pdf"
                text_path = extracted_text_dir / f"{pdf_stem}.txt"
                print(f"📄 Extracting text: {pdf_file.name}")
                extract_pdf_to_text(str(pdf_file), str(text_path))

                record = process_text_file(str(text_path))
                embed_input = build_embed_input(record["text"], record["metadata"])
                embedding = get_embedding(embed_input)
                self.req_db.upsert_requirement(
                    requirement_id=record["requirement_id"],
                    document_id=pdf_file.stem,
                    chunk_id=random.randint(0,999),
                    text=record["text"],
                    metadata=record["metadata"],
                    embedding=embedding,
                )
                print(f" Inserted chunks from {pdf_file.name}\n")
            return "Refreshing requirement database..."
        return None

    def _handle_requirement_query(self, query):
        embedding_input = build_embed_input(query, metadata={})
        embedding = get_embedding(embedding_input)
        embedding = [float(x) for x in embedding]

        results = self.req_db.query_similar(query_embedding=embedding, top_k=1)

        if not results:
            return " No matching requirements found for your query."

        prompt = f"""You are an assistant helping engineers answer technical queries using requirement documents.

User query:
\"{query}\"

Relevant requirement records:
{results}

Based on this, provide a clear and concise answer to the user's query. But once fetching the data, dont rephrase any values or contents. The contents need to be as it is, Make a statement to explain user's query seperately so that it sounds cool. Make the response visually appealing too.
If the answer isn't explicitly available, say "No relevant requirement found."
"""

        return self._get_llm_response(prompt)

    def _get_llm_response(self, prompt):
        try:
            response = self.client.chat.completions.create(
                model="deepseek/deepseek-r1-0528-qwen3-8b:free",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7
            )

            if response and response.choices and response.choices[0] and response.choices[0].message:
                return response.choices[0].message.content.strip()
            else:
                print(f"LLM response was empty or malformed: {response}")
                return "I apologize, but I received an empty or malformed response from the AI. Please try again."
        except Exception as e:
            print(f"Error calling LLM: {e}")
            return "I apologize, but I encountered an error while trying to process your request. Please try again later."

    def handle_query(self, query):
        if self.confirmation_pending:
            if query.lower() in ['yes', 'y', 'sure']:
                self.confirmation_pending = False
                original_query = self.pending_query
                self.pending_query = None
                sync_message = self._sync_requirements()
                if sync_message:
                    return sync_message
                return self._handle_requirement_query(original_query)
            else:
                self.confirmation_pending = False
                original_query = self.pending_query
                self.pending_query = None
                prompt = f"""You are a helpful assistant that answers questions about PowerLog files and battery/power-related concepts. If the answer is not in the provided information or is outside the scope of battery/power-related topics, state that you don't know. Format your responses using Markdown for bolding, italics, and lists.

                User Question: {original_query}
                """
                return self._get_llm_response(prompt)

        if self._is_requirement_query(query):
            self.confirmation_pending = True
            self.pending_query = query
            return "It looks like you're asking for a requirement. Do you want me to search the requirement database?"
        
        prompt = f"""You are a helpful assistant that answers questions about PowerLog files and battery/power-related concepts. If the answer is not in the provided information or is outside the scope of battery/power-related topics, state that you don't know. Format your responses using Markdown for bolding, italics, and lists.

        User Question: {query}
        """
        return self._get_llm_response(prompt)
