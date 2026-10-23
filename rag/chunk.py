"""Text chunking for RAG pipeline."""
from typing import List, Dict

def chunk_documents(documents: List[Dict], chunk_size: int = 500, chunk_overlap: int = 50) -> List[Dict]:
    """Split documents into chunks with overlap."""
    chunks = []
    for doc in documents:
        text = doc['content']
        # Split by paragraphs first, then by size
        paragraphs = text.split('\n\n')
        current_chunk = ''
        chunk_id = 0
        
        for para in paragraphs:
            if len(current_chunk) + len(para) > chunk_size and current_chunk:
                chunks.append({
                    'content': current_chunk.strip(),
                    'source': doc['source'],
                    'title': doc['title'],
                    'chunk_id': chunk_id
                })
                # Keep overlap
                words = current_chunk.split()
                overlap_words = words[-chunk_overlap:] if len(words) > chunk_overlap else words
                current_chunk = ' '.join(overlap_words) + '\n\n' + para
                chunk_id += 1
            else:
                current_chunk += '\n\n' + para if current_chunk else para
        
        if current_chunk.strip():
            chunks.append({
                'content': current_chunk.strip(),
                'source': doc['source'],
                'title': doc['title'],
                'chunk_id': chunk_id
            })
    
    return chunks
