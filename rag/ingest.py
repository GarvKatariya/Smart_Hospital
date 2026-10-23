"""Document ingestion for RAG pipeline."""
import os
from typing import List, Dict

def load_documents(docs_dir: str) -> List[Dict]:
    """Load all markdown documents from the documents directory."""
    documents = []
    for filename in os.listdir(docs_dir):
        if filename.endswith('.md'):
            filepath = os.path.join(docs_dir, filename)
            with open(filepath, 'r') as f:
                content = f.read()
            documents.append({
                'content': content,
                'source': filename,
                'title': filename.replace('.md', '').replace('_', ' ').title()
            })
    return documents
