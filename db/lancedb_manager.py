import pyarrow as pa
import lancedb, json
from typing import Optional, Dict, Any, List, Union


class RequirementDatabase:
    def __init__(self, db_path: str = "db/lancedb", embedding_dim: int = 384):
        self.db_path = db_path
        self.embedding_dim = embedding_dim or 384
        self.schema = self._create_schema()
        self.db = lancedb.connect(self.db_path)
        # Try open dataset, else create new
        try:
            self.dataset = self.db.open_table("requirements")
        except Exception:
            self.dataset = self.db.create_table("requirements", schema=self.schema)

    def _create_schema(self) -> pa.Schema:
        """
        Creates the Apache Arrow schema for the LanceDB dataset.
        """
        return pa.schema([
            pa.field("requirement_id", pa.string(), nullable=False),
            pa.field("document_id", pa.string(), nullable=True),
            pa.field("chunk_id", pa.int64(), nullable=True),
            pa.field("text", pa.string(), nullable=True),
            # metadata stored as a map (string->string) to allow dynamic attributes
            pa.field("metadata", pa.string()),
            # embedding vector (fixed length list of float32)
            pa.field("embedding", pa.list_(pa.float32(), self.embedding_dim), nullable=False),
        ])

    def upsert_requirement(
        self,
        requirement_id: str,
        document_id: Optional[str],
        chunk_id: Optional[int],
        text: Optional[str],
        metadata: Optional[Dict[str, str]],
        embedding: Union[List[float], Any]  # Can be numpy array or list
    ) -> None:
        """
        Insert or update a requirement chunk.

        Args:
            requirement_id: Primary key (string).
            document_id: Source document id.
            chunk_id: Chunk index.
            text: Raw chunk text.
            metadata: Dynamic key-value pairs.
            embedding: Embedding vector as list or numpy array.
        """
        if hasattr(embedding, "tolist"):
            embedding = embedding.tolist()

        # Validate embedding length (assuming 384 here; change as needed)
        EXPECTED_EMBEDDING_LENGTH = 384
        if not isinstance(embedding, list):
            raise TypeError(f"Embedding must be a list, got {type(embedding)}")
        if len(embedding) != EXPECTED_EMBEDDING_LENGTH:
            raise ValueError(f"Embedding length {len(embedding)} != expected {EXPECTED_EMBEDDING_LENGTH}")

        # Optional: validate element types
        if not all(isinstance(x, (float, int)) for x in embedding):
            raise TypeError("Embedding vector must contain only floats or ints")
        '''
        print(f" embedding length = {len(embedding)}")

        print(" Embedding to be stored:", embedding)
        print("Type:", type(embedding))
        print("Length:", len(embedding))'''
    
        record = {
            "requirement_id": requirement_id,
            "document_id": document_id,
            "chunk_id": chunk_id,
            "text": text,
            "metadata": json.dumps(metadata) if metadata else "",
            "embedding": embedding,
        }
        # Note: LanceDB currently appends. Implement update logic if needed.
        self.dataset.add([record])

    # lancedb_manager.py
    def query_similar(self, query_embedding: list[float], top_k: int = 5):
        results = self.dataset.search(query_embedding).limit(top_k).to_pandas()
        # Only keep the fields you want
        records = results[["requirement_id", "document_id", "metadata"]].to_dict(orient="records")
        return records
    
    def close(self):
        """
        Close the DB connection if needed.
        """
        # Currently LanceDB has no explicit close method
        pass
