"""3주차: 팀 위키로 답하는 RAG (LangChain + bge-m3 + Chroma + Claude)

흐름: 로드 → 분할 → 임베딩 → 저장 → 검색 → 생성
사용: python rag.py "도커 이미지와 컨테이너의 차이는?"
"""
import os
import sys
from functools import lru_cache
from pathlib import Path

import anthropic
from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_core.runnables import RunnableLambda, RunnablePassthrough
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

load_dotenv()

def default_wiki_root():
    # 팀 저장소의 members/ 폴더 (각자 wiki/pages/*.md)
    here = Path(__file__).resolve()
    if here.parents[2].name == "members":  # 팀 저장소 members/doyu/week3/ 안에서 실행
        return here.parents[2]
    return here.parents[2] / "Study-service_basic" / "members"  # 개인 저장소 옆에 팀 저장소를 클론한 경우


WIKI_ROOT = Path(os.getenv("WIKI_ROOT") or default_wiki_root())
MODEL = "claude-opus-5-5"


# ── 1. 로드 ─────────────────────────────────────
def load_wiki(root: Path = WIKI_ROOT):
    loader = DirectoryLoader(
        str(root),
        glob="*/wiki/pages/*.md",
        loader_cls=TextLoader,
        loader_kwargs={"encoding": "utf-8"},
    )
    docs = loader.load()
    for d in docs:
        p = Path(d.metadata["source"])  # members/<이름>/wiki/pages/<페이지>.md
        d.metadata["page"] = f"{p.parents[2].name}/{p.stem}"  # 이름이 같은 페이지가 있어서 멤버 이름을 붙인다
    return docs


# ── 2. 분할 + 청크 ID ───────────────────────────
def split_docs(docs, chunk_size=500, chunk_overlap=50):
    splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    chunks = splitter.split_documents(docs)
    counter = {}
    for c in chunks:
        page = c.metadata["page"]
        counter[page] = counter.get(page, 0) + 1
        c.metadata["id"] = f"{page}::{counter[page]:03d}"
    ids = [c.metadata["id"] for c in chunks]
    assert len(ids) == len(set(ids)), "중복 청크 ID"
    return chunks


# ── 3. 임베딩 + 4. 저장 ─────────────────────────
@lru_cache(maxsize=1)
def get_embeddings():
    return HuggingFaceEmbeddings(model_name="BAAI/bge-m3", encode_kwargs={"normalize_embeddings": True})


def build_store(chunks, name="wiki_500_50", persist_dir="chroma_db"):
    store = Chroma(collection_name=name, embedding_function=get_embeddings(), persist_directory=persist_dir)
    if store._collection.count() != len(chunks):  # 청크가 바뀌었을 때만 다시 넣는다
        store.reset_collection()
        store.add_documents(chunks, ids=[c.metadata["id"] for c in chunks])
    return store


# ── 5. 검색 + 6. 생성 (LCEL) ────────────────────
SYSTEM = (
    "너는 스터디 팀 위키 도우미야. <context> 안의 위키 내용만 근거로 한국어로 짧게 답해. "
    "문맥에 답이 없으면 위키에 없다고 말해."
)


def format_docs(docs):
    return "\n\n".join(f"[{d.metadata['page']}]\n{d.page_content}" for d in docs)


def ask_claude(x):
    client = anthropic.Anthropic()  # ANTHROPIC_API_KEY를 .env에서 읽는다
    resp = client.beta.messages.create(
        model=MODEL,
        max_tokens=16000,
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",  # 안전 분류기가 거절하면 서버가 다른 모델로 다시 시도
        system=SYSTEM,
        messages=[{"role": "user", "content": f"<context>\n{x['context']}\n</context>\n\n질문: {x['question']}"}],
    )
    if resp.stop_reason == "refusal":
        return "(답변이 거절됐어요)"
    return "".join(b.text for b in resp.content if b.type == "text")


def unique_pages(docs):
    return list(dict.fromkeys(d.metadata["page"] for d in docs))  # 검색 순서 유지


def build_chain(retriever):
    return (
        {"question": RunnablePassthrough(), "docs": retriever}
        | RunnablePassthrough.assign(context=lambda x: format_docs(x["docs"]))
        | RunnablePassthrough.assign(answer=RunnableLambda(ask_claude))
        | RunnableLambda(lambda x: {"answer": x["answer"], "sources": unique_pages(x["docs"])})
    )


def main():
    question = " ".join(sys.argv[1:]) or "도커 이미지와 컨테이너의 차이는?"
    chunks = split_docs(load_wiki())
    retriever = build_store(chunks).as_retriever(search_kwargs={"k": 5})

    if not os.getenv("ANTHROPIC_API_KEY"):
        print("ANTHROPIC_API_KEY가 없어서 검색 결과만 보여줘요.")
        for rank, d in enumerate(retriever.invoke(question), 1):
            print(rank, d.metadata["id"], "|", d.page_content[:60].replace("\n", " "))
        return

    result = build_chain(retriever).invoke(question)
    print("질문:", question)
    print("답변:", result["answer"])
    print("출처:", ", ".join(result["sources"]))


if __name__ == "__main__":
    main()
