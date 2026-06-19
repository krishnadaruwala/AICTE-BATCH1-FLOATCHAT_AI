from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOCS_PATH = os.path.join(BASE_DIR, "..", "docs")

documents = []

for file in os.listdir(DOCS_PATH):
    if file.endswith(".pdf"):
        loader = PyPDFLoader(
            os.path.join(DOCS_PATH, file)
        )
        documents.extend(loader.load())

splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200
)

chunks = splitter.split_documents(documents)
print("PDF documents loaded:", len(documents))
print("Chunks created:", len(chunks))

embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)

db = FAISS.from_documents(
    chunks,
    embeddings
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

VECTOR_PATH = os.path.join(BASE_DIR, "..", "vectorstore")

db.save_local(VECTOR_PATH)

print("Vector store created.")