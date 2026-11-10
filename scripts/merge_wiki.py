"""개인 위키 -> 팀 위키 병합 스크립트

members/<이름>/wiki/pages/*.md 를 team/wiki/<파일이름>_<이름>.md 로 모으고, team/wiki/index.md 를 다시 만들어요.
매주 개인 위키 정리가 끝난 뒤 저장소 루트에서 실행하고, 바뀐 결과를 PR로 올려요 (리뷰 1명 승인).

    python scripts/merge_wiki.py --dry-run     # 무엇이 바뀌는지만 보기
    python scripts/merge_wiki.py               # 실제로 병합
    python scripts/merge_wiki.py --include-drafts   # 초안 페이지도 포함

규칙
    - 예: members/mingi/wiki/pages/docker-compose.md -> team/wiki/docker-compose_mingi.md
    - index.md 의 주차 칸은 제목의 "N주차" -> 파일 이름 앞 번호(1-xxx.md) -> 처음 추가한 커밋 메시지(week2) 순으로 찾고,
      못 찾으면 "-" 로 둬요.
    - 원본은 개인 위키예요. team/wiki/ 의 복사본은 매번 다시 만들어지니 고치려면 원본을 고쳐요.
    - 복사본 맨 위에 자동 생성 표시를 넣어요. 이 표시가 없는 파일(사람이 직접 합친 페이지)은 건드리지 않아요.
    - 원본이 사라진 복사본은 지워요 (자동 생성 표시가 있는 것만).
    - 초안은 기본으로 건너뛰어요: 제목에 "초안"이 있거나 <!-- TODO 가 남아 있는 페이지.
    - 페이지 안의 상대 링크(../raw/... 등)는 새 위치에서도 원본을 가리키도록 고쳐요.
    - 제목과 파일 이름이 비슷한 페이지는 "같은 주제 후보"로 index.md 에 적어요. 합칠지는 세션에서 정해요.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MEMBERS = ROOT / "members"
TEAM_WIKI = ROOT / "team" / "wiki"
SKIP_MEMBERS = {"_template"}
SKIP_FILES = {"README.md", "index.md", "_template.md"}
MARKER = "<!-- merge_wiki.py 자동 생성"

INDEX_HEADER = """# 팀 위키 색인

개인 위키(`members/<이름>/wiki/pages/`)를 `scripts/merge_wiki.py`로 모은 목록이에요. 이 파일은 스크립트가 다시 만들어요.
페이지를 고치려면 `team/wiki/`가 아니라 원본 개인 위키를 고친 뒤 스크립트를 다시 실행해요.
"""

LINK_RE = re.compile(r"(\[[^\]]*\]\()([^)\s]+)(\))")
WEEK_RE = re.compile(r"(\d+)\s*주차")


# ---------------------------------------------------------------- 페이지 읽기

def read_page(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    title = next((l.lstrip("#").strip() for l in lines if l.startswith("# ")), path.stem)
    member = path.parts[-4]                # members/<이름>/wiki/pages/x.md
    week = find_week(title, path.stem) or week_from_git(path)
    return {
        "member": member,
        "name": path.stem,
        "out": f"{path.stem}_{member}",    # 팀 위키 파일 이름: 파일이름_이름
        "src": path,
        "text": text,
        "title": title,
        "week": week,
        "summary": find_summary(lines),
        "draft": "초안" in title or "<!-- TODO" in text,
    }


def find_week(title: str, stem: str) -> str:
    m = WEEK_RE.search(title)
    if m:
        return m.group(1)
    m = re.match(r"(\d+)-", stem)          # 1-docker-concepts.md 처럼 번호로 시작하면
    return m.group(1) if m else ""


def week_from_git(path: Path) -> str:
    """제목에 주차가 없으면, 그 파일을 처음 추가한 커밋 메시지에서 찾기 (week2, 2주차)"""
    try:
        out = subprocess.run(["git", "log", "--diff-filter=A", "--format=%s", "--", str(path)],
                             cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=10).stdout
    except (OSError, subprocess.SubprocessError):
        return ""
    m = re.search(r"(\d+)\s*주차|week\s*(\d+)", out, re.IGNORECASE)
    return (m.group(1) or m.group(2)) if m else ""


def find_summary(lines: list[str], width: int = 60) -> str:
    """'한 줄 정의/요약' 아래 첫 문장, 없으면 본문 첫 문장"""
    def clean(s: str) -> str:
        s = re.sub(r"[*`>]|^- ", "", s).strip()
        return s if len(s) <= width else s[:width].rstrip() + "…"

    def usable(s: str) -> bool:
        s = s.strip()
        return bool(s) and not s.startswith(("#", "|", "```", "<!--", "(")) and s != "-"

    for i, l in enumerate(lines):
        if l.startswith("#") and ("한 줄 정의" in l or "한 줄 요약" in l):
            for nxt in lines[i + 1:]:
                if nxt.startswith("#"):
                    break
                if usable(nxt):
                    return clean(nxt)
    for heading in ("내 정리", ""):          # 내 정리 아래 첫 문장, 없으면 본문 첫 문장
        start = next((i for i, l in enumerate(lines) if l.startswith("#") and heading in l), None)
        if start is None:
            continue
        for l in lines[start + 1:]:
            if usable(l):
                return clean(l)
    return ""


# ---------------------------------------------------------------- 복사본 만들기

def rewrite_links(text: str, src_dir: Path, dst_dir: Path) -> str:
    """상대 링크를 새 위치 기준으로 다시 계산"""
    def fix(m: re.Match) -> str:
        target = m.group(2)
        if re.match(r"^[a-z]+:|^#|^/", target):
            return m.group(0)
        path, _, anchor = target.partition("#")
        new = os.path.relpath((src_dir / path).resolve(), dst_dir.resolve()).replace(os.sep, "/")
        return f"{m.group(1)}{new}{'#' + anchor if anchor else ''}{m.group(3)}"
    return LINK_RE.sub(fix, text)


def build_copy(page: dict, dst: Path) -> str:
    rel_src = page["src"].relative_to(ROOT).as_posix()
    header = f"{MARKER}: 원본 {rel_src} . 수정은 원본에서 하세요 -->\n\n"
    return header + rewrite_links(page["text"], page["src"].parent, dst.parent)


# ---------------------------------------------------------------- 같은 주제 후보

def tokens(page: dict) -> set[str]:
    text = f"{page['name']} {page['title']}".lower()
    eng = set(re.findall(r"[a-z]{2,}", text))
    kor = {w[:2] for w in re.findall(r"[가-힣]{2,}", text)}   # 앞 두 글자만: 조사(는, 와, 에서) 차이 무시
    stop = {"md", "the", "and", "to", "use", "when", "vs", "what",
            "주차", "무엇", "언제", "필요", "하는", "차이", "기본", "초안", "핵심", "개념", "함수"}
    return (eng | kor) - stop


def similar_groups(pages: list[dict], threshold: float = 0.3) -> list[list[str]]:
    """제목과 파일 이름 단어가 많이 겹치는 페이지끼리 묶기 (다른 멤버끼리만)"""
    ids = [p["out"] for p in pages]
    parent = list(range(len(pages)))

    def root(i: int) -> int:
        while parent[i] != i:
            i = parent[i]
        return i

    toks = [tokens(p) for p in pages]
    for a, b in combinations(range(len(pages)), 2):
        if pages[a]["member"] == pages[b]["member"] or not toks[a] or not toks[b]:
            continue
        jac = len(toks[a] & toks[b]) / len(toks[a] | toks[b])
        if jac >= threshold:
            parent[root(a)] = root(b)

    groups: dict[int, list[str]] = {}
    for i in range(len(pages)):
        groups.setdefault(root(i), []).append(ids[i])
    return [sorted(g) for g in groups.values() if len(g) > 1]


# ---------------------------------------------------------------- 색인

def build_index(pages: list[dict], groups: list[list[str]], skipped: list[dict]) -> str:
    out = [INDEX_HEADER, "| 주차 | 페이지 | 한 줄 요약 | 작성자 |", "| --- | --- | --- | --- |"]
    for p in sorted(pages, key=lambda p: (p["week"] or "99").zfill(2) + p["member"] + p["name"]):
        link = f"[{p['title']}]({p['out']}.md)"
        out.append(f"| {p['week'] or '-'} | {link} | {p['summary'].replace('|', '/')} | {p['member']} |")
    if groups:
        out += ["", "## 같은 주제 후보", "",
                "제목과 파일 이름이 비슷한 페이지예요(자동 추정이라 틀릴 수 있어요). 세션에서 하나로 합칠지 정하고, 합친 페이지는 자동 생성 표시 없이 따로 둬요.", ""]
        out += [f"- {', '.join(g)}" for g in groups]
    if skipped:
        out += ["", "## 초안이라 건너뛴 페이지", ""]
        out += [f"- {p['member']}/{p['name']}: {p['title']}" for p in skipped]
    return "\n".join(out) + "\n"


# ---------------------------------------------------------------- 실행

def main() -> None:
    ap = argparse.ArgumentParser(description="개인 위키를 team/wiki/로 병합")
    ap.add_argument("--dry-run", action="store_true", help="파일을 쓰지 않고 바뀔 내용만 출력")
    ap.add_argument("--include-drafts", action="store_true", help="초안 페이지도 포함")
    args = ap.parse_args()

    sources = sorted(p for p in MEMBERS.glob("*/wiki/pages/*.md")
                     if p.parts[-4] not in SKIP_MEMBERS and p.name not in SKIP_FILES)
    pages = [read_page(p) for p in sources]
    skipped = [] if args.include_drafts else [p for p in pages if p["draft"]]
    pages = [p for p in pages if p not in skipped]

    stats = {"새로 추가": [], "갱신": [], "그대로": [], "삭제": [], "직접 관리라 건너뜀": []}
    wanted = set()
    for p in pages:
        dst = TEAM_WIKI / f"{p['out']}.md"
        wanted.add(dst.resolve())
        new = build_copy(p, dst)
        label = p["out"]
        if dst.exists():
            old = dst.read_text(encoding="utf-8")
            if not old.startswith(MARKER):
                stats["직접 관리라 건너뜀"].append(label)
                continue
            if old == new:
                stats["그대로"].append(label)
                continue
            stats["갱신"].append(label)
        else:
            stats["새로 추가"].append(label)
        if not args.dry_run:
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_text(new, encoding="utf-8")

    for old in list(TEAM_WIKI.glob("*.md")) + list(TEAM_WIKI.glob("*/*.md")):
        if old.resolve() not in wanted and old.read_text(encoding="utf-8").startswith(MARKER):
            stats["삭제"].append(old.relative_to(TEAM_WIKI).as_posix())
            if not args.dry_run:
                old.unlink()

    groups = similar_groups(pages)
    index = build_index(pages, groups, skipped)
    if not args.dry_run:
        (TEAM_WIKI / "index.md").write_text(index, encoding="utf-8")

    print(("[미리 보기] " if args.dry_run else "") + f"개인 위키 {len(sources)}페이지 중 {len(pages)}개 병합")
    for k, v in stats.items():
        if v and k != "그대로":
            print(f"- {k} {len(v)}: {', '.join(v)}")
    if stats["그대로"]:
        print(f"- 그대로 {len(stats['그대로'])}개")
    if skipped:
        print(f"- 초안이라 건너뜀 {len(skipped)}: {', '.join(p['member'] + '/' + p['name'] for p in skipped)}")
    for g in groups:
        print(f"- 같은 주제 후보: {', '.join(g)}")
    if not args.dry_run:
        print("다음: git add team/wiki && git commit, PR로 올려 리뷰 받기")


if __name__ == "__main__":
    main()
