"""질문셋으로 리트리버 채점: Recall@k, MRR@k, 질문당 평균 검색 시간

사용: python evaluate.py --sizes 200 500 1000 --k 5
"""
import argparse
import json
import time

from rag import build_store, load_wiki, split_docs


def load_questions(path="questions.jsonl"):
    questions = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                q = json.loads(line)
                q["answers"] = q.get("answer_pages") or [q["answer_page"]]  # 한 페이지만 적은 형식도 받는다
                questions.append(q)
    return questions


def evaluate(retrieve, questions, k=5):
    hits, rr_sum, elapsed, misses = 0, 0.0, [], []
    for q in questions:
        start = time.perf_counter()
        docs = retrieve(q["question"])[:k]
        elapsed.append(time.perf_counter() - start)
        pages = [d.metadata["page"] for d in docs]
        rank = next((i for i, p in enumerate(pages, 1) if p in q["answers"]), None)
        if rank:
            hits += 1
            rr_sum += 1 / rank
        else:
            misses.append((q["question"], pages[:3]))
    n = len(questions)
    return {
        "recall": hits / n,
        "mrr": rr_sum / n,
        "avg_ms": sum(elapsed) / n * 1000,
        "misses": misses,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sizes", type=int, nargs="+", default=[500])
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--show-misses", action="store_true")
    args = ap.parse_args()

    docs, questions = load_wiki(), load_questions()
    print(f"문서 {len(docs)}개, 질문 {len(questions)}개, k={args.k}\n")
    print("| chunk_size | overlap | 청크 수 | Recall@k | MRR@k | 평균 검색(ms) |")
    print("| --- | --- | --- | --- | --- | --- |")
    for size in args.sizes:
        overlap = size // 10
        chunks = split_docs(docs, size, overlap)
        retriever = build_store(chunks, name=f"wiki_{size}_{overlap}").as_retriever(search_kwargs={"k": args.k})
        r = evaluate(retriever.invoke, questions, args.k)
        print(f"| {size} | {overlap} | {len(chunks)} | {r['recall']:.2f} | {r['mrr']:.3f} | {r['avg_ms']:.0f} |")
        if args.show_misses:
            for question, top in r["misses"]:
                print(f"  못 찾음: {question} → {top}")


if __name__ == "__main__":
    main()
