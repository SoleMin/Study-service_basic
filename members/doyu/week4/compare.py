"""4주차: 기준선 vs BM25 vs 하이브리드(RRF) vs 리랭커를 팀 질문셋으로 비교

팀 공통 채점 함수(team/eval/evaluate.py)를 그대로 써서 Recall@5, MRR@5, 질문당 검색 시간을 잰다.
사용: python compare.py [--exclude rag-evaluation_mingi] [--only 이름 ...] [--show-misses]
"""
import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from hybrid import RerankRetriever, build_bm25, build_hybrid, build_vector, kiwi_tokens, load_chunks, space_tokens, team_repo_root

# 팀 저장소 위치. .env의 TEAM_REPO로 바꿀 수 있다
TEAM_REPO = Path(os.getenv("TEAM_REPO") or team_repo_root())
sys.path.append(str(TEAM_REPO / "team" / "eval"))
from evaluate import evaluate, load_questions  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*", help="이 이름의 변형만 실행")
    ap.add_argument("--show-misses", action="store_true")
    ap.add_argument("--exclude", nargs="*", default=[], help="검색 대상에서 뺄 페이지 이름 (예: 평가 결과를 적어 둔 페이지)")
    args = ap.parse_args()

    questions = load_questions(TEAM_REPO / "team" / "eval" / "questions.jsonl")
    pages, chunks = load_chunks(TEAM_REPO / "team" / "wiki")
    if args.exclude:
        chunks = [c for c in chunks if c.metadata["page"] not in args.exclude]
        pages = [p for p in pages if Path(p.metadata["source"]).stem not in args.exclude]
        print("뺀 페이지:", ", ".join(args.exclude))
    print(f"페이지 {len(pages)}개 → 청크 {len(chunks)}개, 질문 {len(questions)}개\n")

    vector = lambda k: build_vector(chunks, k)  # noqa: E731
    variants = {
        "기준선 (벡터)": lambda: vector(5),
        "BM25 (띄어쓰기)": lambda: build_bm25(chunks, 5, space_tokens),
        "BM25 (형태소)": lambda: build_bm25(chunks, 5, kiwi_tokens),
        "하이브리드 0.5:0.5": lambda: build_hybrid(vector(20), build_bm25(chunks, 20, kiwi_tokens), [0.5, 0.5]),
        "하이브리드 벡터0.7": lambda: build_hybrid(vector(20), build_bm25(chunks, 20, kiwi_tokens), [0.7, 0.3]),
        "하이브리드 벡터0.3": lambda: build_hybrid(vector(20), build_bm25(chunks, 20, kiwi_tokens), [0.3, 0.7]),
        "리랭커 (벡터10→5)": lambda: RerankRetriever(vector(10), top_n=5, candidates=10),
        "리랭커 (벡터20→5)": lambda: RerankRetriever(vector(20), top_n=5),
        "하이브리드+리랭커": lambda: RerankRetriever(build_hybrid(vector(20), build_bm25(chunks, 20, kiwi_tokens), [0.5, 0.5]), top_n=5),
    }

    rows = []
    for name, make in variants.items():
        if args.only and name not in args.only:
            continue
        retriever = make()
        retriever.invoke("워밍업")  # 모델 첫 로드 시간은 빼고 잰다
        print(f"── {name}")
        r = evaluate(retriever, questions, k=5, show_misses=args.show_misses)
        rows.append((name, r))

    base = next((r for n, r in rows if n.startswith("기준선")), None)
    print("\n| 기법 | Recall@5 | MRR@5 | MRR 차이 | 질문당 검색(ms) |")
    print("| --- | --- | --- | --- | --- |")
    for name, r in rows:
        diff = f"{r['mrr'] - base['mrr']:+.3f}" if base else "-"
        print(f"| {name} | {r['recall']:.3f} | {r['mrr']:.3f} | {diff} | {r['avg_ms']:.0f} |")

    print("\n질문별 정답 순위 (- = 5위 안에 없음)")
    print("| id | " + " | ".join(n for n, _ in rows) + " |")
    print("| --- |" + " --- |" * len(rows))
    for i, q in enumerate(questions):
        ranks = [r["rows"][i]["rank"] for _, r in rows]
        if len(set(ranks)) > 1 or ranks[0] != 1:  # 모두 1위인 질문은 빼고 차이가 난 것만
            print(f"| {q['id']} | " + " | ".join(str(x) if x else "-" for x in ranks) + " |")


if __name__ == "__main__":
    main()
