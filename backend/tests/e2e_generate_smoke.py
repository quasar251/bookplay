"""Phase 4 端到端验收脚本 —— 真实注册新书生成链路（S10）

前置条件：
- 后端已在 http://127.0.0.1:8000 启动（python -m uvicorn app.main:app）
- backend/.env 配置了可用的 DeepSeek API Key

流程：
1. POST /api/books 注册一本新书（真实文本）
2. 轮询 GET /api/tasks/{task_id} 直到 success/failed
3. GET /api/books/{book_id} 校验回写（状态、章节、game）
4. GET /api/books/{book_id}/game 校验游戏 JSON 结构

说明：会真实调用 LLM，耗时取决于网络与生成规模。
"""

import json
import sys
import time
import urllib.request

BASE = "http://127.0.0.1:8000"

BOOK_TITLE = "掌控习惯与身份（端到端验收）"
BOOK_TEXT = (
    "本书讲一个朴素的观点：你不该追求'坚持'某个习惯，而该先决定自己是谁。"
    "如果你想成为长期阅读的人，那就每天做一件读者身份会做的事——翻开两页也算。"
    "习惯不是靠意志力堆出来的，而是靠环境设计：把想养成的行为变得显而易见、"
    "有吸引力、简单易行、令人满足。反之想戒掉的坏习惯，就让它看不见、费力、"
    "无聊、没有即时奖励。失败的人常常试图用动机对抗阻力，聪明的人只是降低阻力。"
    "每一次行动都是在为想成为的那个身份投下一票，票数够多，身份自然稳固。"
)


def _req(method: str, path: str, body=None, timeout: int = 60):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(
        BASE + path,
        data=data,
        headers={"Content-Type": "application/json"} if data else {},
        method=method,
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main() -> int:
    print(f"[1/4] POST /api/books register: {BOOK_TITLE}")
    res = _req("POST", "/api/books", {
        "book_title": BOOK_TITLE,
        "book_text": BOOK_TEXT,
        "book_type": "non_fiction",
        "max_scenes": 1,
    })
    assert res["code"] == 0, f"register failed: {res}"
    book_id = res["data"]["book_id"]
    task_id = res["data"]["task_id"]
    print(f"      book_id={book_id} task_id={task_id}")

    print(f"[2/4] polling task {task_id} …")
    deadline = time.time() + 240
    task = None
    while time.time() < deadline:
        time.sleep(3)
        task = _req("GET", f"/api/tasks/{task_id}", timeout=30)
        status = task["status"]
        msg = task.get("message", "")
        print(f"      status={status} progress={task.get('progress')} msg={msg[:60]}")
        if status in ("success", "failed"):
            break
    assert task is not None and task["status"] == "success", (
        f"task not finished: {task}"
    )

    print("[3/4] verify book writeback …")
    detail = _req("GET", f"/api/books/{book_id}")
    book = detail["book"]
    assert book["status"] == "completed", book["status"]
    assert book["generation"]["status"] == "completed", book["generation"]
    assert detail["has_game"] is True
    assert len(detail["chapters"]) >= 1, "chapters missing"
    print(f"      status=completed, chapters={len(detail['chapters'])}, "
          f"quotes={len(detail['quotes'])}, has_game=True")

    print("[4/4] verify game JSON …")
    game_res = _req("GET", f"/api/books/{book_id}/game")
    game = game_res["game"]
    total_scenes = sum(
        len(ch.get("scenes", [])) for ch in game.get("chapters", [])
    )
    assert total_scenes >= 1, "no scenes in game"
    print(f"      book_title={game.get('book_title')!r}, "
          f"chapters={len(game.get('chapters', []))}, scenes={total_scenes}")

    print("=" * 56)
    print("✅ Phase 4 端到端生成链路通过（注册 → 生成 → 回写 → game 可读）")
    print("=" * 56)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:  # noqa: BLE001
        print(f"\n❌ 端到端验收失败: {type(e).__name__}: {e}")
        sys.exit(1)
