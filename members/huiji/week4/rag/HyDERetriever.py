from typing import List
from pydantic import ConfigDict
from sentence_transformers import CrossEncoder
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

HYDE_PROMPT = ChatPromptTemplate.from_template(
    "당신은 쿠버네티스, Docker, FastAPI, RAG를 다루는 기술 위키 작성자입니다.\n"
    "아래 질문에 답하는 위키 문서의 한 단락(3~5문장)을 한국어로 쓰세요.\n"
    "- 질문과 관련된 전문 용어와 명령어를 포함하세요.\n"
    "- 확실하지 않아도 그럴듯하게 쓰세요. 정확성보다 용어가 중요합니다.\n"
    "- 인사말이나 '질문에 답하자면' 같은 말은 쓰지 마세요.\n\n"
    "질문: {question}"
)

def make_hyde_chain(llm):
    return HYDE_PROMPT | llm | StrOutputParser()


class HyDERetriever(BaseRetriever):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    base_retriever: BaseRetriever
    hyde_chain: object
    include_query: bool = True
    verbose: bool = False

    def _get_relevant_documents(self, query: str, *, run_manager=None) -> List[Document]:
        fake = self.hyde_chain.invoke({"question": query})
        text = f"{query}\n{fake}" if self.include_query else fake
        if self.verbose:
            print(f"[HyDE] {query!r} -> {fake[:80]!r}...")
        return self.base_retriever.invoke(text)


class HyDERerank(BaseRetriever):
    """후보는 가짜 문서로 뽑고, 채점은 원래 질문으로 한다."""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    vector_retriever: BaseRetriever   # k=15짜리
    hyde_chain: object
    reranker: CrossEncoder
    top_n: int = 5

    def _get_relevant_documents(self, query: str, *, run_manager=None) -> List[Document]:
        fake = self.hyde_chain.invoke({"question": query})
        cands = self.vector_retriever.invoke(f"{query}\n{fake}")
        if not cands:
            return []
        scores = self.reranker.predict([(query, d.page_content) for d in cands])
        ranked = sorted(zip(cands, scores), key=lambda x: x[1], reverse=True)
        return [d for d, _ in ranked[: self.top_n]]