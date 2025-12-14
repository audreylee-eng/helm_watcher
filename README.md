# Stock watcher

這個專案使用 Playwright 定期檢查商品頁面是否補貨，並在狀態從缺貨轉為有貨時透過 Discord Webhook 以及 Telegram Bot 通知。

## 設定 Discord Webhook Secret
1. 在 GitHub Repository 中進入 **Settings → Secrets and variables → Actions**。
2. 新增一個 Repository secret：
   - Name: `DISCORD_WEBHOOK_URL`
   - Value: 你的 Discord Webhook URL

## 設定 Telegram Bot Secrets
1. 建立一個 Telegram Bot 並取得 Token（使用 [BotFather](https://core.telegram.org/bots#6-botfather)）。
2. 取得要接收通知的 Chat ID（可使用 Bot 取得或透過 API 查詢）。
3. 在 GitHub Repository 中新增以下 Repository secrets：
   - Name: `TELEGRAM_BOT_TOKEN`
   - Value: 你的 Telegram Bot Token
   - Name: `TELEGRAM_CHAT_ID`
   - Value: 接收通知的 Chat ID

## 調整追蹤設定
編輯專案根目錄的 `config.json`：
```json
{
  "product_url": "https://example.com/product"
}
```
- `product_url`: 要監控的商品頁面網址。

程式會在商品頁面中依序點擊「Small」與「Matte Black」選項，並檢查「Add to cart」按鈕是否為 disabled 狀態，決定庫存狀態：
- 按鈕 disabled：`out_of_stock`
- 按鈕可點擊：`in_stock`
- 找不到按鈕：`unknown`

狀態會記錄在 `state.json`，只有當狀態從 `out_of_stock` 變為 `in_stock` 時才會發送通知，以避免重複提醒。

## GitHub Actions 執行頻率
`.github/workflows/stock.yml` 會每 10 分鐘執行一次，並支援 `workflow_dispatch` 讓你手動觸發檢查。
若要讓 GitHub Actions 送出通知，請在 Repository secrets 中同時設定 Discord 與 Telegram 相關環境變數，工作流程會自動載入：
- `DISCORD_WEBHOOK_URL`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

## 本地手動測試
1. 安裝依賴：
   ```bash
   python -m pip install --upgrade pip
   pip install playwright
   playwright install --with-deps chromium
   ```
2. 設定環境變數（選擇性，但若要測試通知需要）：
   ```bash
   export DISCORD_WEBHOOK_URL="<你的 Discord Webhook URL>"
   export TELEGRAM_BOT_TOKEN="<你的 Telegram Bot Token>"
   export TELEGRAM_CHAT_ID="<你的 Telegram Chat ID>"
   ```
3. 執行檢查程式：
   ```bash
   python checker.py
   ```
執行後會顯示前後狀態並更新 `state.json`。當狀態由 `out_of_stock` 變為 `in_stock` 且有設定 Webhook/Telegram 時會立即發送通知。
