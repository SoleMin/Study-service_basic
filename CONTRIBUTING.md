# 기여 방법

## 매주 과제 올리는 순서

```bash
# 1. 최신 main 받기
git switch main
git pull origin main

# 2. 이번 주 브랜치 만들기
git switch -c <이름>/week2        # 예: mingi/week2

# 3. members/<이름>/week2/ 에서 작업하고 커밋
git add members/<이름>/
git commit -m "week2: FastAPI /chat과 Redis 캐시"

# 4. 올리기
git push -u origin <이름>/week2
```

그다음 GitHub에서 Pull Request를 만들어요. 템플릿(한 것, 왜 3줄, 못 한 것)이 자동으로 채워져요. 그 주 리뷰어 2명 중 1명 이상이 승인하면 머지해요.

## 규칙

- **브랜치 이름**: 개인 과제는 `<이름>/weekN`, 팀 위키는 `<이름>/wiki-<주제>`, 팀 프로젝트는 `team/<모듈>`
- **커밋 메시지**: `weekN: 한 일` 형식으로 짧게 (예: `week1: PyTorch 학습 Dockerfile`)
- **내 폴더만 고치기**: 개인 과제 PR은 `members/<이름>/`만 바꿔요. `team/`, `README.md`를 고칠 때는 PR을 따로 올려요.
- **main에 직접 push하지 않기**: 모든 변경은 PR로 해요.
- **비밀값 확인**: 커밋 전에 `git status`로 `.env`나 키 파일이 없는지 봐요.

## 팀 위키에 페이지 올리기

1. `members/<이름>/wiki/pages/`에 쓴 페이지 중 실습으로 확인한 것을 고른다
2. `team/wiki/`로 복사하고, `team/wiki/index.md` 표에 한 줄 추가
3. PR을 올리고 리뷰어 1명 승인 후 머지
4. 같은 개념의 페이지가 이미 있으면 새로 만들지 않고 기존 페이지에 합친다

## 충돌이 났을 때

```bash
git switch main && git pull origin main
git switch <내 브랜치>
git merge main          # 충돌 난 파일을 열어 <<<<<<< ======= >>>>>>> 부분 정리
git add <파일> && git commit
git push
```
