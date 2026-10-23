"""Build RAG index from hospital knowledge base documents."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from rag.ingest import load_documents
from rag.chunk import chunk_documents
from rag.embeddings import EmbeddingService
from rag.retriever import FAISSRetriever
from app.core.config import settings

def main():
    docs_dir = os.path.join(os.path.dirname(__file__), '..', 'rag', 'documents')
    index_dir = settings.FAISS_INDEX_DIR
    
    print('Loading documents...')
    documents = load_documents(docs_dir)
    print(f'Loaded {len(documents)} documents')
    
    print('Chunking documents...')
    chunks = chunk_documents(documents, chunk_size=settings.CHUNK_SIZE, chunk_overlap=settings.CHUNK_OVERLAP)
    print(f'Created {len(chunks)} chunks')
    
    print('Generating embeddings...')
    embedding_service = EmbeddingService(model_name=settings.EMBEDDING_MODEL)
    texts = [c['content'] for c in chunks]
    embeddings = embedding_service.encode(texts)
    print(f'Generated embeddings: shape {embeddings.shape}')
    
    print('Building FAISS index...')
    retriever = FAISSRetriever(index_dir)
    retriever.build_index(embeddings, chunks)
    retriever.save()
    
    print(f'RAG index built successfully! {len(chunks)} chunks indexed.')
    
    # Verify with test query
    print('\nVerifying with test query...')
    query_emb = embedding_service.encode_query('What departments are available?')
    results = retriever.search(query_emb, top_k=3)
    for r in results:
        print(f'  Score: {r["score"]:.3f} | Source: {r["source"]} | Preview: {r["content"][:100]}...')

if __name__ == '__main__':
    main()
