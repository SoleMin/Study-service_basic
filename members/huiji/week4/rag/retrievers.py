from typing import List
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from sentence_transformers import CrossEncoder

class RerankRetriever(BaseRetriever):
    base_retriever: BaseRetriever   # k=15로 만든 벡터 retriever
    top_n: int = 5
    model: CrossEncoder

    class Config:
        arbitrary_types_allowed = True

    def _get_relevant_documents(self, query: str, *, run_manager=None) -> List[Document]:
        candidates = self.base_retriever.invoke(query)
        if not candidates:
            return []
        pairs = [(query, d.page_content) for d in candidates]
        scores = self.model.predict(pairs)
        ranked = sorted(zip(candidates, scores), key=lambda x: x[1], reverse=True)
        return [d for d, _ in ranked[: self.top_n]]