docs = {
    "docker-basics": "도커 이미지는 앱과 실행 환경을 묶은 읽기 전용 템플릿이고, 컨테이너는 이미지를 실행한 프로세스예요.",
    "fastapi-intro": "FastAPI는 파이썬으로 REST API를 만드는 프레임워크이고 /docs에서 자동 문서를 제공해요.",
    "k8s-basics": "쿠버네티스에서 Deployment는 Pod 개수를 유지하고 Service는 Pod에 접근하는 주소를 제공해요.",
}


def to_words(text):
    return set(text.replace(".", "").replace(",", "").replace("?", "").split())

store = {name: to_words(text) for name, text in docs.items()}   

def retrieve(question, k=2):
    q = to_words(question)
    scored = sorted(store.items(), key=lambda kv: len(q & kv[1]), reverse=True)
    return [name for name, _ in scored[:k]]

def ask(question):
    names = retrieve(question)
    context = "\n".join(f"[{n}] {docs[n]}" for n in names)
    print("질문:", question)
    print("검색된 출처:", names)
    print("LLM에게 줄 프롬프트:\n문맥:\n" + context + "\n질문: " + question + "\n")

ask("도커 이미지와 컨테이너의 차이는?")
ask("Deployment는 뭐 하는 거야?")