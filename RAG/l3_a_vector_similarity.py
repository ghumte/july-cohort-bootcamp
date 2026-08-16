from langchain_text_splitters import RecursiveCharacterTextSplitter
from pathlib import Path
from langchain_core.documents import Document
import hashlib
import datetime
from langchain_openai import OpenAIEmbeddings
from dotenv import load_dotenv
import numpy as np
load_dotenv()

embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

pdf_path = Path(__file__).parent / "test_documents" / "02_legal_contract.txt"

t = pdf_path.read_text()

def chunk_document_with_metadata(text, extraction_metadata, access_metadata):
    document_id = hashlib.sha256(text.encode()).hexdigest()

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=100,
                    chunk_overlap=20,
                    separators=["\n\n", "\n", " ", ""])
    chunks = text_splitter.split_text(text)

    documents = []
    
    for idx, chunk in enumerate(chunks):
        chunk_metadata = {
            **extraction_metadata,
            **access_metadata,
            "document_id": document_id,
            "chunk_id": f"{document_id}_{idx}",
            "chunk_index": idx,
            "chunk_size": len(chunk),
            "chunk_timestamp": datetime.datetime.now().isoformat(),
        }

        doc = Document(page_content=chunk, metadata=chunk_metadata)
        documents.append(doc)

    return documents


extraction_metadata = {
    "source": "02_legal_contract.txt",
    "pages": 1,
    "quality": 0.8,
    "extraction_method": "azure document intelligence",
}

access_metadata = {
    "access_level": "public",
    "department": "Legal"
}

documents = chunk_document_with_metadata(t, extraction_metadata, access_metadata)

for doc in documents:
    print(doc.metadata)
    print(doc.page_content)
    print("-" * 100)

embedding_docs = embeddings.embed_documents([f"{doc.page_content}" for doc in documents])

for emb, doc in zip(embedding_docs, documents):
    print("*" * 100)
    print(f"Length of embedding: {len(emb)}")
    print(f"Embedding: {emb}")
    print("*" * 100)
    print(doc.page_content)
    print("-" * 100)
    print()

query = "Liability and Damages"
query_embedding = embeddings.embed_query(query)

print("*" * 100)
print(f"Length of query embedding: {len(query_embedding)}")
print(f"Query embedding: {query_embedding}")
print("*" * 100)
print()

def cosine_similarity(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

similarities = [cosine_similarity(query_embedding, emb) for emb in embedding_docs]

sorted_indices = np.argsort(similarities)[::-1]

for idx in sorted_indices:
    print("*" * 100)
    print(f"Similarity: {similarities[idx]}")
    print(f"Document: {documents[idx].page_content}")
    print("*" * 100)
    print()
    print("-" * 100)
    print()