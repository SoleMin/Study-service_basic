from sentence_transformers import CrossEncoder
from rag.retrievers import RerankRetriever

reranker_model = CrossEncoder("BAAI/bge-reranker-v2-m3", max_length=512)  # 한 번만 로드

vector_retriever = vectorstore.as_retriever(search_kwargs={"k": 15})  # 후보는 넉넉히
rerank_retriever = RerankRetriever(
    base_retriever=vector_retriever, top_n=5, model=reranker_model
)