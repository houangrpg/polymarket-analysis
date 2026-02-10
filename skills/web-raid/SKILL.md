# Skill: Web-Raid (系統冒險檢測)

用於對特定網頁進行自動化功能、安全性及效能檢測，並產出遊戲化的冒險報告。

## 流程 (SOP)
1. **偵查 (Recon)**: 
   - 檢查連線協議 (HTTP/HTTPS) 及 SSL 狀態。
   - 使用 `browser:snapshot` 獲取頁面結構。
2. **滲透 (Infiltration)**:
   - 識別登入欄位，配合 Memory 帳密執行自動登入。
   - 若有驗證碼，執行 `browser:screenshot` 並使用 AI 視覺辨識。
3. **數據採集 (Looting)**:
   - 檢查 `browser:console` 錯誤日誌。
   - 測試核心功能點擊與頁面跳轉速度。
4. **戰利品彙整 (Reporting)**:
   - 執行 `python3 scripts/web_raid_engine.py` 產出 HTML。
   - 更新 `raid_index.html` 紀錄。
   - 自動 Git Push 至 GitHub Pages。

## 增加測試項目的方法
- **新增邏輯**: 在 `scripts/web_raid_engine.py` 中增加檢查項 (例如：SEO 檢查、無障礙檢查)。
- **新增 UI 模組**: 在 HTML 模板中新增 `quest-card` CSS 類別來呈現新維度的數據。

## 指令範例
- "對 [URL] 進行 Web-Raid"
- "更新 HIS 的冒險報告"
