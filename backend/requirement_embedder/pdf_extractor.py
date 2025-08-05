import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[2]))
import os
import json, requests, random
from pathlib import Path
from backend.requirement_embedder.embedder import get_embedding, build_embed_input
from db.lancedb_manager import RequirementDatabase
from langchain_docling import DoclingLoader
from docling.document_converter import *

def parse_markdown_table(md_text: str) -> dict:
    """
    Parse a markdown table into list of dicts, each dict representing a row.
    Assumes simple pipe-separated tables like:

    | Key           | Value           |
    |---------------|-----------------|
    | Requirement ID| REQ_001         |
    | Description   | Pump Rate       |
    .
    .
    .

    """
    lines = [line.strip() for line in md_text.strip().splitlines() if line.strip()]
    if len(lines) < 3:
        return {}

    records = {}
    for line in lines[2:]:  # Skip header and separator
        parts = [cell.strip() for cell in line.strip('|').split('|')]
        if len(parts) == 2:
            key, value = parts
            records[key] = value
    return records

    

def extract_pdf_to_text(pdf_path: str, output_path: str):
    converter = DocumentConverter()
    documents = converter.convert(pdf_path)
    markdown_pages = documents.document.export_to_markdown()  # list of markdown strings

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(markdown_pages)




def process_text_file(text_path: str) -> dict:
    """Returns a consistent dictionary structure for each requirement"""
    with open(text_path, "r", encoding="utf-8") as f:
        md_text = f.read()
    
    rows = parse_markdown_table(md_text)
    
    if not rows:
        return {
            "requirement_id": "REQ_0",
            "chunk_id": 0,
            "text": md_text,
            "title": "Untitled",
            "metadata": {}
        }
    
    return {
        "text": rows.get("Name") or rows.get("Description") or "",
        "requirement_id": rows.get("Name", f"REQ_{random.randint(0, 1000)}"),
        "title": rows.get("Name", ""),
        "metadata": {k: v for k, v in rows.items() if k in ["Name", "Display Message", "Status", "Button Bar", "Display Title", "Log Message","Set"]},
    }

'''
Here we are checking if the pdf is converted to markdown using docling and saved as a text. This step
also helps in understanding if the pdf is already converted or not. If yes ignored
- in the extract_pdf_to_text we have converted the pdf to docling markdwon and have stored as txt.
- The process
'''
def main():
    raw_pdf_dir = Path("RAG_DATA/raw_pdfs/")
    extracted_text_dir = Path("RAG_DATA/extracted_texts/")
    extracted_text_dir.mkdir(parents=True, exist_ok=True)

    db = RequirementDatabase()

    for pdf_file in raw_pdf_dir.glob("*.pdf"):
        text_path = extracted_text_dir / f"{pdf_file.stem}.txt"

        if not text_path.exists():
            print(f" Extracting text: {pdf_file.name}")
            extract_pdf_to_text(str(pdf_file), str(text_path))
        else:
            print(f" Skipping extraction (already done): {pdf_file.name}")

        record = process_text_file(str(text_path))
        embed_input = build_embed_input(record["text"], record["metadata"])
    # ... rest of your code using dict access instead of list indices
        embedding = get_embedding(embed_input)
        db.upsert_requirement(
            requirement_id=record["requirement_id"],
            document_id=pdf_file.stem,
            chunk_id=random.randint(0,999),
            text=record["text"],
            metadata=record["metadata"],
            embedding=embedding,
        )

        print(f" Inserted {len(record)} chunks from {pdf_file.name}\n")

if __name__ == "__main__":
   main()

    #file_path = Path("data/extracted_texts/AG-UIC-SW-964.txt")
    #text_content = file_path.read_text(encoding="utf-8")  # read file content as string

    #a = query_deepseek_api(text_content)

    #print(a)