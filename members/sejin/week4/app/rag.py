"""4주차 RAG: 팀 위키(team/wiki)에 질문하면 답과 출처를 돌려준다. api.py가 불러 쓴다.
명령줄 확인 (week4 폴더에서):  python app/rag.py "Redis TTL은 몇 초로 정했어?"
"""

import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_anthropic import ChatAnthropic
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough



BASE_DIR = Path(__file__).resolve().parent.parent        # week3/
load_dotenv(BASE_DIR / ".env")

WIKI_DIR = Path(os.getenv("WIKI_DIR") or BASE_DIR.parents[2] / "team" / "wiki")   # 환경 변수가 없을 때만 기본값 계산
SKIP_FILES = {"index.md", "_template.md", "README.md"}  
LLM_MODEL = os.getenv("LLM_MODEL", "claude-haiku-5-5")
CHUNK_SIZE, CHUNK_OVERLAP, TOP_K = 500, 50, 5             # 스터디 기준선


def load_chunks():
    """① 로드 + ② 분할: 팀 위키를 읽어 청크로 자르고 '페이지이름-번호' ID를 붙인다 (팀 evaluate.py와 같은 규칙)"""
    loader = DirectoryLoader(str(WIKI_DIR), glob="*.md",
                             loader_cls=TextLoader, loader_kwargs={"encoding": "utf-8"})
    pages = [d for d in loader.load() if Path(d.metadata["source"]).name not in SKIP_FILES]
    for d in pages:
        d.page_content = "\n".join(l for l in d.page_content.splitlines()
                                   if not l.startswith("<!-- merge_wiki.py"))   # 자동 생성 표시 줄 제거
        d.metadata["page"] = Path(d.metadata["source"]).stem                    # 예: redis-ttl-cache_mingi

    splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
    chunks = []
    for page in pages:
        for i, c in enumerate(splitter.split_documents([page])):
            c.metadata["id"] = f"{page.metadata['page']}-{i}"
            chunks.append(c)
    return chunks



def get_vectordb(embeddings):
    """④ 저장: chroma_db가 있으면 열기만, 비어 있으면 처음 한 번 임베딩해서 넣는다"""
    db = Chroma(collection_name=f"team_wiki_{CHUNK_SIZE}", embedding_function=embeddings,
                persist_directory=str(BASE_DIR / "chroma_db"),
                collection_metadata={"hnsw:space": "cosine"})
    if db._collection.count() == 0:
        print("벡터 DB가 비어 있어 새로 만듭니다 (약 2분)...")
        chunks = load_chunks()
        db.add_documents(chunks, ids=[c.metadata["id"] for c in chunks])
    return db


NO_ANSWER = "위키에 없는 내용입니다"

PROMPT = ChatPromptTemplate.from_messages([
    ("system", "너는 AI 엔지니어링 스터디의 튜터다. 아래 [자료]만 근거로 한국어로 3~5문장으로 답한다. "
               "자료에 없는 내용이면 '위키에 없는 내용입니다'라고 답한다.\n\n[자료]\n{context}"),
    ("human", "{question}"),
])


def format_docs(docs):
    """청크 5개를 [페이지 이름] + 내용 형태의 글 하나로 합친다"""
    return "\n\n".join(f"[{d.metadata['page']}]\n{d.page_content}" for d in docs)


def build_rag_chain():
    """③ 임베딩 모델, ④ 벡터 DB, ⑤ 검색기, ⑥ Claude를 준비해 체인 하나로 잇는다 (한 번만 호출)"""
    embeddings = HuggingFaceEmbeddings(model_name="BAAI/bge-m3",
                                       encode_kwargs={"normalize_embeddings": True})
    retriever = get_vectordb(embeddings).as_retriever(search_kwargs={"k": TOP_K})
    llm = ChatAnthropic(model=LLM_MODEL, max_tokens=16000)
    answer_chain = PROMPT | llm | StrOutputParser()
    return (
        {"docs": retriever, "question": RunnablePassthrough()}
        | RunnablePassthrough.assign(context=lambda x: format_docs(x["docs"]))
        | RunnablePassthrough.assign(answer=answer_chain)
    )


def ask(rag_chain, question):
    """질문 하나 → (답, 출처 페이지 목록). 위키에 없다고 답하면 출처는 비운다"""
    out = rag_chain.invoke(question)
    if NO_ANSWER in out["answer"]:
        return out["answer"], []
    sources = list(dict.fromkeys(d.metadata["page"] for d in out["docs"]))
    return out["answer"], sources


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('사용법: python app/rag.py "질문"')
        sys.exit(1)
    question = " ".join(sys.argv[1:])

    rag_chain = build_rag_chain()                 # 모델 로드 + DB 열기 (느린 부분, 한 번만)
    t0 = time.perf_counter()
    answer, sources = ask(rag_chain, question)    # 검색 + 답변 (질문마다)
    print(answer)
    print("출처:", ", ".join(sources) if sources else "없음")
    print(f"({time.perf_counter() - t0:.2f}초)")

