"""
docker run --name pgvector-container \
  -e POSTGRES_USER=langchain \
  -e POSTGRES_PASSWORD=langchain \
  -e POSTGRES_DB=langchain \
  -p 6024:5432 \
  -d pgvector/pgvector:pg16
"""
from langchain_openai import OpenAIEmbeddings
from dotenv import load_dotenv
from langchain_postgres import PGVector
from langchain_community.document_loaders import TextLoader
from langchain_core.documents import Document
from langchain_core.indexing.base import InMemoryRecordManager
from langchain_core.indexing import index
load_dotenv()

embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
record_manager = InMemoryRecordManager(namespace = "langchain_demo")
connection = "postgresql+psycopg://langchain:langchain@localhost:6024/langchain"  # Uses psycopg3!
collection_name = "rag_demo"


record_manager.create_schema()

cats_loader = TextLoader("test_documents/cat.txt")
dogs_loader = TextLoader("test_documents/dog.txt")
dogs_loader_v2 = TextLoader("test_documents/dog_v2.txt")

cats_docs = cats_loader.load()
dogs_docs = dogs_loader.load()
dogs_docs_v2 = dogs_loader_v2.load()

print("********** Loading example document **********")
print(cats_docs)

vector_store = PGVector(
    embeddings=embeddings,
    collection_name=collection_name,
    connection=connection,
)

index_1 = index(cats_docs, record_manager, vector_store, source_id_key="source")
print("Indexing the cats documents **********",index_1)

index_2 = index(dogs_docs, record_manager, vector_store, source_id_key="source")
print("Indexing the dogs documents **********",index_2)

index_3 = index(dogs_docs_v2, record_manager, vector_store, source_id_key="source")
print("Indexing the dogs documents v2 **********",index_3)

# Repeat the indexing process
index_4 = index(cats_docs, record_manager, vector_store, source_id_key="source")
print("Indexing the cats document again **********",index_4)

# Modify the document
with open("test_documents/cat.txt", "w") as f:
    f.write("I love stuart little")

# reindex

cats_loader_v2 = TextLoader("test_documents/cat.txt")
cats_docs_v2 = cats_loader_v2.load()
index_5 = index(cats_docs_v2, record_manager, vector_store, source_id_key="source")
print("Indexing the cats document again **********",index_5)