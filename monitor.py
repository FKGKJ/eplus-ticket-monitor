from datetime import datetime, timezone, timedelta
import json
import os
import re
import subprocess
import sys
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")

JST = timezone(timedelta(hours=8))

# 售票網址設定
EPLUS_DETAIL_URL = "https://eplus.jp/sf/detail/1682650001-P0030148P0030149P0030150P0030151P0030152P0030153P0030154P0030155P0030156P0030157P0030158P0030159P0030160P0030161P0030162P0030163P0030164?P1=0402&P59=1&P6=001&block=true"
EPLUS_DIRECT_NIGHT_URL = "https://atom.eplus.jp/sys/main.jsp?prm=U=82:P2=168265:P5=0001:P3=0156:P21=002:P7=1:P6=001:P1=0402:P0=GGWC01:P55=//eplus.jp%2Fsf%2Fdetail%2F1682650001-P0030148P0030149P0030150P0030151P0030152P0030153P0030154P0030155P0030156P0030157P0030158P0030159P0030160P0030161P0030162P0030163P0030164%3FP1%2a0402%26P59%2a1%26P6%2a001%26block%2atrue"

PIA_BUNDLE_URL = "https://t.pia.jp/pia/event/event.do?eventBundleCd=b2671107"
PIA_DIRECT_URL = "https://t.pia.jp/pia/ticketInformation.do?eventCd=2636612&rlsCd=001"

LAWSON_EVENT_URL = "https://l-tike.com/concert/mevent/?mid=469819"
LAWSON_SEARCH_URL = "https://l-tike.com/search/?lcd=73366"
LAWSON_DIRECT_ORDER_URL = "https://l-tike.com/order/?gLcode=73366&gPfKey=20260925000002302801%2C20260925000002302802&gEntryMthd=02&gScheduleNo=1&gCarrierCd=08&gPfName=%E5%A4%8F%E5%B7%9D%E6%A4%8E%E8%8F%9C&gBaseVenueCd=36261"

# Discord Webhooks (僅從 GitHub Secrets 環境變數讀取，不寫死於程式碼中)
WEBHOOK_EPLUS = os.environ.get("DISCORD_WEBHOOK_URL", "").strip()
WEBHOOK_LAWSON = (
    os.environ.get("DISCORD_WEBHOOK_LAWSON", "").strip() or WEBHOOK_EPLUS
)
WEBHOOK_PIA = (
    os.environ.get("DISCORD_WEBHOOK_PIA", "").strip() or WEBHOOK_EPLUS
)

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"


def fetch_html(url: str, timeout_sec: int = 12) -> str:
    res = subprocess.run(
        [
            "curl",
            "-s",
            "-L",
            "--compressed",
            "-m",
            str(timeout_sec),
            "-A",
            UA,
            "-H",
            "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "-H",
            "Accept-Language: ja,en-US;q=0.9,en;q=0.8,zh-TW;q=0.7",
            "-H",
            "Cache-Control: no-cache",
            url,
        ],
        capture_output=True,
        timeout=timeout_sec + 3,
        check=False,
    )
    if res.returncode == 0 and res.stdout:
        return res.stdout.decode("utf-8", errors="replace")

    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": UA,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "ja,en-US;q=0.9,en;q=0.8,zh-TW;q=0.7",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
        return resp.read().decode("utf-8", errors="replace")


def send_discord(webhook_url: str, username: str, message: str) -> None:
    if not webhook_url:
        print(f"⚠️ 未設定對應的 Discord Webhook Secret，跳過 [{username}] 推播。")
        return
    payload = json.dumps(
        {"username": username, "content": message},
        ensure_ascii=False,
    ).encode("utf-8")

    req = urllib.request.Request(
        webhook_url,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "User-Agent": UA,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            print(f"✅ Discord 推播成功 [{username}] (HTTP {resp.status})")
    except Exception as e:
        print(f"⚠️ Discord 推播失敗 [{username}]: {e}")


def check_eplus(now: str, send_test: bool = False) -> None:
    text = fetch_html(EPLUS_DETAIL_URL)
    articles = re.findall(
        r'<article class="block-ticket-article.*?</article>', text, re.S
    )

    print(f"[{now}] [1/3] E+ 檢查結果 (2026 夏川椎菜):")
    night_available_lines = []
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

        is_night = ("19:30" in time_str) or (p21 == "002")
        if is_night and ("受付中" in status_str or "予定枚数終了" not in status_str):
            night_available_lines.append(line)

    if night_available_lines:
        joined_avail = "\n".join(f"• {l}" for l in night_available_lines)
        joined_all = "\n".join(f"• {l}" for l in all_lines)
        msg = (
            f"🚨 **【E+ 夜場 (19:30 LIVE) 釋票通知！】** @everyone\n"
            f"您監控的 **2026 夏川椎菜 19:30 夜公演** 狀態已變更（不再是予定枚数終了）！\n\n"
            f"✅ **可購買夜場**：\n{joined_avail}\n\n"
            f"📋 **當日兩場完整狀態**：\n{joined_all}\n"
            f"🕒 **檢查時間**：{now}\n"
            f"👉 **直接進 19:30 選張數頁面**：{EPLUS_DIRECT_NIGHT_URL}\n"
            f"🔗 **E+ 列表頁**：{EPLUS_DETAIL_URL}"
        )
        send_discord(WEBHOOK_EPLUS, "E+ 雲端監票小幫手", msg)
    elif send_test:
        joined_all = "\n".join(f"• {l}" for l in all_lines)
        test_msg = (
            f"☁️ **【GitHub Actions 雲端監票啟動測試成功 (E+)！】**\n"
            f"🕒 **檢查時間**：{now}\n"
            f"📋 **目前最新票況（已設定僅針對 19:30 夜場發警報）**：\n{joined_all}\n"
            f"🔗 **售票頁面**：{EPLUS_DETAIL_URL}"
        )
        send_discord(WEBHOOK_EPLUS, "E+ 雲端監票小幫手", test_msg)


def check_pia(now: str, send_test: bool = False) -> None:
    text = fetch_html(PIA_BUNDLE_URL)
    match = re.search(
        r'<p class="ticketSalesCard-2024__title">\s*一般発売\s*／\s*夏川椎菜\s*</p>.*?<p class="ticketSalesCard-2024__status[^>]*>(.*?)</p>',
        text,
        re.S,
    )
    status_str = (
        re.sub(r"<[^>]+>", "", match.group(1)).strip() if match else "未知"
    )
    print(f"[{now}] [2/3] チケットぴあ (337-990) 檢查結果: 【{status_str}】")

    is_available = (
        status_str != "未知"
        and "予定枚数終了" not in status_str
        and "受付終了" not in status_str
        and (
            "販売期間中" in status_str
            or "発売中" in status_str
            or "残りわずか" in status_str
            or "空席" in status_str
        )
    )

    if is_available:
        msg = (
            f"🚨 **【チケットぴあ (Pia) 釋票通知！】** @everyone\n"
            f"🎤 **夏川椎菜「毎日がクリスマス 2026」12/17(木) (Pコード: 337-990)**\n"
            f"📊 **目前狀態**：【{status_str}】\n"
            f"🕒 **檢查時間**：{now}\n"
            f"👉 **立刻點此搶票 (夏川椎菜專頁)**：{PIA_DIRECT_URL}\n"
            f"🔗 **Pia 總頁**：{PIA_BUNDLE_URL}"
        )
        send_discord(WEBHOOK_PIA, "Pia 雲端監票小幫手", msg)
    elif send_test:
        test_msg = (
            f"☁️ **【GitHub Actions 雲端監票啟動測試成功 (チケットぴあ)！】**\n"
            f"🕒 **檢查時間**：{now}\n"
            f"📋 **目前最新票況 (Pコード: 337-990)**：【{status_str}】\n"
            f"🔗 **直達搶票頁面**：{PIA_DIRECT_URL}"
        )
        send_discord(WEBHOOK_PIA, "Pia 雲端監票小幫手", test_msg)


def check_lawson(now: str, send_test: bool = False) -> None:
    status_str = "未知"
    blocked_note = ""
    try:
        event_text = fetch_html(LAWSON_EVENT_URL, timeout_sec=10)
        match = re.search(
            r'<h3 class="lt-title-m[^>]*>[^<]*?夏川椎菜[^<]*?</h3>.*?<span class="lt-ticket-list-item__status[^>]*>(.*?)</span>',
            event_text,
            re.S,
        )
        if match:
            status_str = re.sub(
                r"^warning", "", re.sub(r"<[^>]+>", "", match.group(1))
            ).strip()
        else:
            blocked_note = "（註：Lawson 防火牆可能阻擋 GitHub 美國雲端 IP）"
    except Exception as e:
        print(f"⚠️ Lawson 雲端連線受限: {e}")
        blocked_note = "（註：Lawson 鎖日本海外機房 IP，雲端連線被擋）"

    print(f"[{now}] [3/3] ローチケ (L: 73366) 檢查結果: 【{status_str}】 {blocked_note}")

    is_available = (
        status_str != "未知"
        and "予定枚数終了" not in status_str
        and "終了" not in status_str
        and "発売中" in status_str
    )

    if is_available:
        msg = (
            f"🚨 **【ローチケ (Lawson) 釋票通知！】** @everyone\n"
            f"🎤 **夏川椎菜「毎日がクリスマス 2026」12/17(木) (Lコード: 73366)**\n"
            f"📊 **目前狀態**：【{status_str}】\n"
            f"🕒 **檢查時間**：{now}\n"
            f"👉 **立刻點此直達選票頁 (免選日期)**：\n{LAWSON_DIRECT_ORDER_URL}"
        )
        send_discord(WEBHOOK_LAWSON, "Lawson 雲端監票小幫手", msg)
    elif send_test:
        test_msg = (
            f"☁️ **【GitHub Actions 雲端監票啟動測試成功 (ローチケ Lawson)！】**\n"
            f"🕒 **檢查時間**：{now}\n"
            f"📋 **目前最新票況 (Lコード: 73366)**：【{status_str}】{blocked_note}\n"
            f"🔗 **直達搶票頁面 (免選日期)**：\n{LAWSON_DIRECT_ORDER_URL}"
        )
        send_discord(WEBHOOK_LAWSON, "Lawson 雲端監票小幫手", test_msg)


def check_all(send_test: bool = False) -> None:
    now = datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S (UTC+8)")
    try:
        check_eplus(now, send_test=send_test)
    except Exception as e:
        print(f"⚠️ E+ 檢查發生錯誤: {e}")

    try:
        check_pia(now, send_test=send_test)
    except Exception as e:
        print(f"⚠️ Pia 檢查發生錯誤: {e}")

    try:
        check_lawson(now, send_test=send_test)
    except Exception as e:
        print(f"⚠️ Lawson 檢查發生錯誤: {e}")


if __name__ == "__main__":
    is_manual_test = os.environ.get("GITHUB_EVENT_NAME") == "workflow_dispatch"
    check_all(send_test=is_manual_test)
