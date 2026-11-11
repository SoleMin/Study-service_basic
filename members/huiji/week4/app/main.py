import sys
from pathlib import Path

TEAM_REPO = r"C:\Users\bagaj\Documents\GitHub\DockerPractice\Study-service_basic"  # team/ 폴더가 들어 있는 곳

sys.path.insert(0, TEAM_REPO)
sys.path.insert(0, r"C:\Users\bagaj\Documents\GitHub\DockerPractice\Study-service_basic\members\huiji\week4")  # rag/가 들어 있는 곳

from team.eval.evaluate import evaluate, load_questions
from rag.retrievers import RerankRetriever
# vectorstore, reranker_model은 3주차 코드에서 가져오기

from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from sentence_transformers import CrossEncoder

from team.eval.evaluate import evaluate
from rag.retrievers import RerankRetriever

questions = load_questions(Path(TEAM_REPO) / "team" / "eval" / "questions.jsonl")

# 3주차와 같은 임베딩 모델 (노트북에서 embeddings를 만든 코드와 똑같이)
embeddings = HuggingFaceEmbeddings(model_name="BAAI/bge-m3")

from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

SKIP = {"index.md", "_template.md", "README.md"}
loader = DirectoryLoader(
    str(Path(TEAM_REPO) / "team" / "wiki"), glob="*.md",
    loader_cls=TextLoader, loader_kwargs={"encoding": "utf-8"},
)
docs = [d for d in loader.load() if Path(d.metadata["source"]).name not in SKIP]

splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
chunks = splitter.split_documents(docs)

# 청크 ID 부여 (페이지이름::번호)
counter = {}
for c in chunks:
    p = Path(c.metadata["source"]).stem
    counter[p] = counter.get(p, 0) + 1
    c.metadata["id"] = f"{p}::{counter[p]:03d}"

vectorstore = Chroma.from_documents(
    chunks, embeddings,
    ids=[c.metadata["id"] for c in chunks],
    collection_name="team_wiki_500_50",
    collection_metadata={"hnsw:space": "cosine"},   # 팀 기준선과 동일하게
)  # persist_directory를 빼서 메모리에만 만듭니다 (팀 기준선과 같은 방식)
print(vectorstore._collection.count(), "개 청크 로드됨")   # 수십~수백 개여야 정상

reranker_model = CrossEncoder("BAAI/bge-reranker-v2-m3", max_length=512)

baseline = vectorstore.as_retriever(search_kwargs={"k": 5})
rerank = RerankRetriever(
    base_retriever=vectorstore.as_retriever(search_kwargs={"k": 15}),
    top_n=5,
    model=reranker_model,
)

print("== baseline ==")
evaluate(baseline, questions, k=5)

print("== rerank ==")
evaluate(rerank, questions, k=5)