from datetime import datetime
from pathlib import Path

out = Path("/app/out")
out.mkdir(exist_ok=True)
(out / "result.txt").write_text(f"컨테이너가 쓴 파일 ({datetime.now():%H:%M:%S})\n",
                                encoding="utf-8")
print("저장 완료:", out / "result.txt")
