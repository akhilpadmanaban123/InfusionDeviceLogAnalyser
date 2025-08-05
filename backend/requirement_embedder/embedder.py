from sentence_transformers import SentenceTransformer

model = SentenceTransformer("all-MiniLM-L6-v2")  # Or any other small embedding model

def build_embed_input(chunk_text: str, metadata: dict) -> str:
    """
    Combine text + metadata into a single embedding input.
    """
    meta_str = " ".join(f"{k}: {v}" for k, v in metadata.items()) if metadata else ""
    return f"{chunk_text} {meta_str}"


def get_embedding(text: str) -> list[float]:
    """
    Generate embedding vector for a given string.
    """
    return model.encode(text).tolist()
