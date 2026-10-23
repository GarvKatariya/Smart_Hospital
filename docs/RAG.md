# RAG Pipeline Documentation

The Retrieval-Augmented Generation (RAG) pipeline empowers the Hospital Chatbot and AI context modules by combining semantic search with Generative LLM responses.

## Architecture

1. **Document Sources**:
   - Hospital Policies (PDFs, Markdown)
   - Doctor Schedules & Specializations (JSON/CSV)
   - General FAQs and Medical Triage Guidelines

2. **Chunking Strategy**:
   - **Chunk Size**: 500 tokens
   - **Overlap**: 50 tokens
   - **Strategy**: Semantic boundary splitting (paragraph-level where possible)

3. **Embedding Model**:
   - Local: `sentence-transformers/all-MiniLM-L6-v2` (Fast, efficient)
   - Remote (Optional): Gemini Embeddings

4. **Vector Store**:
   - **FAISS (Facebook AI Similarity Search)**: Used for local, in-memory exact/approximate nearest neighbor search.

5. **Retrieval Settings**:
   - **Top-K**: 3-5 relevant chunks retrieved per query.
   - **Distance Metric**: L2 (Euclidean) or Cosine Similarity.

6. **Prompt Construction**:
   - The retrieved context is injected into a strict prompt template.
   - Template structure:
     ```
     Context: {retrieved_chunks}
     
     User Query: {query}
     
     Instructions: Answer the query ONLY using the provided context. If the answer is not in the context, say "I cannot answer this based on my knowledge base."
     ```

7. **Hallucination Safeguards**:
   - Strict LLM system prompts.
   - Low temperature (`temperature=0.1`) for factual queries.
   - Grounding confidence thresholds for vector distances.

8. **Fallback Behavior**:
   - If the vector store finds no results above the similarity threshold, the LLM is bypassed or prompted to explicitly state it does not have the information.
