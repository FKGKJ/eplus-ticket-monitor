# E+ 雲端自動監票系統 (GitHub Actions + Discord 推播)

本專案透過 GitHub Actions 每 5 分鐘在雲端自動檢查 **エアトリ presents 毎日がクリスマス — 2026 夏川椎菜**（16:30 與 19:30 兩場次）的 E+ 售票狀態，一旦釋出新票立即透過 Discord Webhook 推播通知。

## 快速啟用步驟（設定完成後電腦即可關機）

### 步驟 1：設定 Discord Webhook Secret
1. 進入您的 GitHub 儲存庫頁面，點選上方選單的 **`Settings`**。
2. 在左側選單展開 **`Secrets and variables`** ➔ 點選 **`Actions`**。
3. 點擊綠色的 **`New repository secret`** 按鈕：
   - **Name** 輸入：`DISCORD_WEBHOOK_URL`
   - **Secret** 貼上您的 Discord Webhook 網址（`https://discord.com/api/webhooks/...`）
4. 點擊 **`Add secret`** 儲存。

### 步驟 2：手動觸發一次測試（確認 Discord 收到雲端通知）
1. 點選儲存庫上方的 **`Actions`** 頁籤。
2. 左側點選 **`E+ Ticket Monitor`**。
3. 點擊右側的 **`Run workflow`** ➔ 綠色 **`Run workflow`** 按鈕。
4. 等待約 15～20 秒執行完成，您的 Discord 頻道就會收到 **「☁️ 【GitHub Actions 雲端監票啟動測試成功！】」** 訊息！收到後您就可以安心將電腦關機了。
