"""
Access Control Demo - RAG with Department-Based Filtering

This script demonstrates:
1. Loading documents separately with different metadata per department
2. Database indexing for vector search and department filtering
3. Semantic search with department-level access control filtering

Prerequisites:
- PostgreSQL with pgvector: docker run --name pgvector-container \
  -e POSTGRES_USER=langchain \
  -e POSTGRES_PASSWORD=langchain \
  -e POSTGRES_DB=langchain \
  -p 6024:5432 \
  -d pgvector/pgvector:pg16

- Run schema from l3_prod_setup_notes.md (CREATE TABLE documents, etc.)
"""

from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
import psycopg
from pgvector.psycopg import register_vector
import hashlib
from psycopg.types.json import Json

load_dotenv()

CONNECTION_STRING = "postgresql://langchain:langchain@localhost:6024/langchain"
EMBEDDINGS_MODEL = OpenAIEmbeddings(model="text-embedding-3-small")

# Document configuration: (file_path, loader_type, department, access_level, doc_type, extraction_method)
DOCUMENT_CONFIGS = [
    # Engineering documents
    (
        "test_documents/03_aws_ec2_pricing.txt",
        "text",
        "engineering",
        "internal",
        "text",
        "textloader",
    ),
    (
        "test_documents/04_cloud_computing_guide.txt",
        "text",
        "engineering",
        "internal",
        "text",
        "textloader",
    ),
    (
        "test_documents/06_engineering_budget.txt",
        "text",
        "engineering",
        "internal",
        "text",
        "textloader",
    ),
    # Finance documents
    (
        "test_documents/01_financial_report.txt",
        "text",
        "finance",
        "internal",
        "text",
        "textloader",
    ),
    (
        "test_documents/financial_report.pdf",
        "pdf",
        "finance",
        "internal",
        "pdf",
        "pypdfloader",
    ),
    # HR documents
    (
        "test_documents/05_hr_salary_data.txt",
        "text",
        "hr",
        "confidential",
        "text",
        "textloader",
    ),
]


def sha256_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_documents(config: tuple) -> list:
    """Load documents from a single file with the given configuration."""
    file_path, loader_type, department, access_level, doc_type, extraction_method = config

    if loader_type == "pdf":
        loader = PyPDFLoader(file_path)
    else:
        loader = TextLoader(file_path)

    docs = loader.load()
    return docs, {
        "department": department,
        "access_level": access_level,
        "doc_type": doc_type,
        "extraction_method": extraction_method,
        "source_file": file_path,
    }


def ensure_doc_type_constraint(conn) -> None:
    """
    Ensure doc_type constraint allows 'text' (for .txt files).
    The original schema only allowed pdf, docx, html, code, email.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            ALTER TABLE documents DROP CONSTRAINT IF EXISTS documents_doc_type_check;
            ALTER TABLE documents ADD CONSTRAINT documents_doc_type_check
                CHECK (doc_type IN ('pdf', 'docx', 'html', 'code', 'email', 'text'));
            """
        )
    conn.commit()
    print("doc_type constraint updated to include 'text'.")


def ensure_indexes(conn) -> None:
    """
    Create all required indexes for vector search and department filtering.
    Idempotent - uses IF NOT EXISTS where supported.
    """
    with conn.cursor() as cur:
        # Metadata GIN index for JSONB queries
        cur.execute(
            "CREATE INDEX IF NOT EXISTS documents_metadata_gin ON documents USING gin (metadata);"
        )
        # Department index for fast filtering
        cur.execute(
            "CREATE INDEX IF NOT EXISTS documents_department_idx ON documents (department);"
        )
        # Access level index for access control
        cur.execute(
            "CREATE INDEX IF NOT EXISTS documents_access_level_idx ON documents (access_level);"
        )
        # HNSW index for approximate nearest neighbor vector search (fast, good recall)
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS documents_hnsw_idx
            ON documents USING hnsw (embedding vector_cosine_ops);
            """
        )
    conn.commit()
    print("Indexes created/verified successfully.")


def load_and_store_department_documents(clear_existing: bool = False) -> None:
    """
    Load documents from each department separately and store with appropriate metadata.
    """
    splitter = RecursiveCharacterTextSplitter(chunk_size=100, chunk_overlap=20)

    with psycopg.connect(CONNECTION_STRING) as conn:
        register_vector(conn)
        ensure_doc_type_constraint(conn)

        if clear_existing:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM documents;")
                conn.commit()
                print("Cleared existing documents.")

        for config in DOCUMENT_CONFIGS:
            try:
                docs, meta_defaults = load_documents(config)
            except FileNotFoundError as e:
                print(f"Skipping {config[0]}: {e}")
                continue

            # Merge loader metadata with our department metadata
            for doc in docs:
                doc.metadata = {**doc.metadata, **meta_defaults}

            splitted_docs = splitter.split_documents(docs)
            texts = [doc.page_content for doc in splitted_docs]

            if not texts:
                continue

            embeddings = EMBEDDINGS_MODEL.embed_documents(texts)

            with conn.cursor() as cur:
                for i, (doc, emb) in enumerate(zip(splitted_docs, embeddings)):
                    meta = doc.metadata or {}
                    cur.execute(
                        """
                        INSERT INTO documents (
                            content, embedding,
                            source_file, page_number, chunk_index, total_chunks, doc_hash,
                            department, access_level, created_by,
                            doc_type, chunk_type, extraction_method, extraction_confidence, chunk_length,
                            metadata
                        )
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                        """,
                        (
                            doc.page_content,
                            emb,
                            meta.get("source", meta.get("source_file")),
                            meta.get("page"),
                            i,
                            len(splitted_docs),
                            sha256_hash(doc.page_content),
                            meta_defaults["department"],
                            meta_defaults["access_level"],
                            "system",
                            meta_defaults["doc_type"],
                            "text",
                            meta_defaults["extraction_method"],
                            0.95,
                            len(doc.page_content),
                            Json(meta),
                        ),
                    )
            conn.commit()
            dept = meta_defaults["department"]
            print(f"Stored {len(splitted_docs)} chunks from {config[0]} -> department: {dept}")

        ensure_indexes(conn)


def query_by_department(query: str, department: str, k: int = 5) -> list:
    """
    Semantic search filtered by department (access control).
    Uses cosine distance for similarity.
    """
    query_embedding = EMBEDDINGS_MODEL.embed_query(query)

    with psycopg.connect(CONNECTION_STRING) as conn:
        register_vector(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, content, department, access_level, source_file,
                       1 - (embedding <=> %s::vector) AS similarity
                FROM documents
                WHERE department = %s
                ORDER BY embedding <=> %s::vector
                LIMIT %s;
                """,
                (query_embedding, department, query_embedding, k),
            )
            rows = cur.fetchall()
    return rows


def query_all_departments(query: str, k: int = 3) -> dict:
    """
    Demo: run the same query against each department and show department-filtered results.
    """
    departments = ["engineering", "finance", "hr"]
    results = {}
    for dept in departments:
        rows = query_by_department(query, dept, k=k)
        results[dept] = rows
    return results


def print_query_results(query: str, results: dict) -> None:
    """Pretty-print query results by department."""
    print(f"\n{'='*60}")
    print(f"Query: \"{query}\"")
    print("=" * 60)
    for department, rows in results.items():
        print(f"\n--- Department: {department.upper()} ---")
        if not rows:
            print("  (No results)")
            continue
        for r in rows:
            doc_id, content, dept, access, source, sim = r
            preview = content[:120].replace("\n", " ") + "..." if len(content) > 120 else content
            print(f"  [sim={sim:.3f}] {preview}")
            print(f"    source: {source}, access: {access}")


def main():
    """Run the full access control demo."""
    import sys

    # 1. Load documents (clear first for clean demo)
    clear = "--clear" in sys.argv or "-c" in sys.argv
    print("Loading documents with department metadata...")
    load_and_store_department_documents(clear_existing=clear)

    # 2. Demo department-filtered queries
    demo_queries = [
        ("What is AWS EC2 pricing?", "engineering"),
        ("What is Q4 revenue?", "finance"),
        ("What are salary ranges for engineers?", "hr"),
    ]

    print("\n" + "=" * 60)
    print("DEPARTMENT-FILTERED SEMANTIC SEARCH DEMO")
    print("=" * 60)

    for query, expected_dept in demo_queries:
        print(f"\n>>> Query: \"{query}\" (expected: {expected_dept})")
        rows = query_by_department(query, expected_dept, k=3)
        for r in rows:
            _, content, dept, access, source, sim = r
            preview = content[:100].replace("\n", " ")
            print(f"  [{dept}] sim={sim:.3f}: {preview}...")

    # 3. Cross-department comparison: same query, different departments
    print("\n" + "=" * 60)
    print("CROSS-DEPARTMENT COMPARISON: \"cloud cost\"")
    print("=" * 60)

    all_results = query_all_departments("cloud cost", k=2)
    print_query_results("cloud cost", all_results)


if __name__ == "__main__":
    main()
