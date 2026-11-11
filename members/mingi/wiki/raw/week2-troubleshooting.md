# 2주차에 겪은 문제 기록

실제로 겪은 증상과 해결만 사실대로 적었어요. "내가 배운 것" 칸은 직접 채워요. 개념 페이지의 "내가 막힌 점"에 옮겨 쓸 재료예요.

| # | 단계 | 증상 / 에러 | 원인 | 해결 | 내가 배운 것 |
| --- | --- | --- | --- | --- | --- |
| 1 | 1단계 | `/docs`가 빈 화면 | 확인 안 됨 (다시 하니 정상) | 재시도 |  |
| 2 | 1단계 | `/docs`, POST, Try it out이 무엇인지 헷갈림 | 개념 | 설명 듣고 직접 호출 |  |
| 3 | 2단계 | Claude API 비용이 드는지 궁금 | 구독과 API 결제는 별개 | Gemini 무료 등급으로 변경 |  |
| 4 | 2단계 | `ModuleNotFoundError: No module named 'app'` | `week2`가 아닌 폴더에서 uvicorn 실행 | `week2` 폴더에서 실행 |  |
| 5 | 2단계 | 키 파일 이름이 `env` | 앞의 점 누락. `load_dotenv`가 못 찾고 `.gitignore`도 안 막음 | `.env`로 변경, `git check-ignore`로 확인 |  |
| 6 | 2단계 | `ChatRequest`, `ChatResponse` 없음, 안 쓰는 anthropic import | 코드 일부만 붙여넣음 | 모델 클래스 추가, import 정리 |  |
| 7 | 2단계 | 500 Internal Server Error → `404 models/gemini-2.5-flash is no longer available` | 모델 이름이 오래됨 | `gemini-3.8-flash`로 변경 |  |
| 8 | 3단계 | `redis-test`를 따로 작성해야 하는지 헷갈림 | `--name`으로 붙인 컨테이너 이름 | 공식 이미지 그대로 실행 |  |
| 9 | 3단계 | `docker-compose.yml` 위치를 모름 | `build: .`, `env_file`이 compose 파일 위치 기준 | `week2` 폴더에 둠 |  |
| 10 | 3단계 | `.dockerignore`가 비어 있음 | 내용 미작성 | `.venv/`, `.env`, `__pycache__/` 추가 |  |
| 11 | 4단계 | 첫 측정 4.38초가 맞는지 헷갈림 | PowerShell `Start-Job` 준비 시간 포함 | 세 엔드포인트 비교로 해석 |  |
