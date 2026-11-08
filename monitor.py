from datetime import datetime, timezone, timedelta
import json
import os
import re
import subprocess
import sys
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")

JST = timezone(timedelta(hours=8))

DETAIL_URL = "https://eplus.jp/sf/detail/1682650001-P0030148P0030149P0030150P0030151P0030152P0030153P0030154P0030155P0030156P0030157P0030158P0030159P0030160P0030161P0030162P0030163P0030164?P1=0402&P59=1&P6=001&block=true"
WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL", "").strip()


def fetch_html() -> str:
    # Use curl for high compatibility with E+ TLS/headers
    res = subprocess.run(
        [
            "curl",
            "-s",
            "-L",
            "-A",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
            DETAIL_URL,
        ],
        capture_output=True,
        timeout=30,
        check=False,
    )
    if res.returncode == 0 and res.stdout:
        return res.stdout.decode("utf-8", errors="replace")

    req = urllib.request.Request(
        DETAIL_URL,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
        },
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.read().decode("utf-8", errors="replace")


def send_discord(message: str) -> None:
    if not WEBHOOK_URL:
        print("⚠️ 未設定 DISCORD_WEBHOOK_URL 環境變數，跳過 Discord 推播。")
        return

    payload = json.dumps(
        {
            "username": "E+ 雲端監票小幫手",
            "content": message,
        },
        ensure_ascii=False,
    ).encode("utf-8")

    req = urllib.request.Request(
        WEBHOOK_URL,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        print(f"✅ Discord 推播成功 (HTTP {resp.status})")


def check_once(send_test: bool = False) -> bool:
    text = fetch_html()
    articles = re.findall(
        r'<article class="block-ticket-article.*?</article>', text, re.S
    )

    now = datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S (UTC+8)")
    print(f"[{now}] E+ 雲端票務檢查結果 (エアトリ presents 毎日がクリスマス - 2026 夏川椎菜):")

    available_lines = []
    all_lines = []

    for art in articles:
        prm_match = re.search(r"P3=0156:P21=(\d+)", art)
        if not prm_match:
            continue
        p21 = prm_match.group(1)
        date_m = re.search(r'block-ticket-article__date">(.*?)</span>', art)
        time_m = re.search(r'block-ticket-fixed__time">(.*?)</span>', art)
        title_m = re.search(r'block-ticket-article__title">(.*?)</span>', art)
        statuses = [
            s.strip()
            for s in re.findall(r'ticket-status__item[^>]*>(.*?)</span>', art)
            if s.strip()
        ]
        status_str = " / ".join(statuses) if statuses else "未知"

        date_str = date_m.group(1).strip() if date_m else ""
        time_str = time_m.group(1).strip() if time_m else ""
        title_str = (
            title_m.group(1).strip().replace("\xa0", " ") if title_m else ""
        )

        line = f"P3=0156:P21={p21}: {date_str} {time_str} | {title_str} -> 【{status_str}】"
        print(f"  - {line}")
        all_lines.append(line)

        if "受付中" in status_str or "予定枚数終了" not in status_str:
            available_lines.append(line)

    if available_lines:
        joined_avail = "\n".join(f"• {l}" for l in available_lines)
        joined_all = "\n".join(f"• {l}" for l in all_lines)
        msg = (
            f"🚨 **【E+ 雲端釋票通知！】** @everyone\n"
            f"您監控的 **2026 夏川椎菜** 場次狀態已變更（不再是予定枚数終了）！\n\n"
            f"✅ **可購買場次**：\n{joined_avail}\n\n"
            f"📋 **當日兩場完整狀態**：\n{joined_all}\n"
            f"🕒 **檢查時間**：{now}\n"
            f"🔗 **立刻前往售票頁面**：{DETAIL_URL}"
        )
        send_discord(msg)
        return True

    print("  ❌ 兩場公演 (16:30 與 19:30) 目前皆仍為「予定枚数終了」（已售完）。")
    if send_test:
        joined_all = "\n".join(f"• {l}" for l in all_lines)
        test_msg = (
            f"☁️ **【GitHub Actions 雲端監票啟動測試成功！】**\n"
            f"🕒 **檢查時間**：{now}\n"
            f"📋 **目前最新票況**：\n{joined_all}\n"
            f"✨ 雲端排程已正常運作，現在**您可以安心將電腦關機**！只要任一場次釋出新票，雲端會立即在此頻道標記通知您。\n"
            f"🔗 **售票頁面**：{DETAIL_URL}"
        )
        send_discord(test_msg)
    return False


if __name__ == "__main__":
    is_manual_test = os.environ.get("GITHUB_EVENT_NAME") == "workflow_dispatch"
    check_once(send_test=is_manual_test)
