# 今日出門決策助手

輸入台灣縣市、行程和個人體感，用 Open-Meteo 的目前天氣與今日預報，產生出門舒適度、穿搭圖和配件建議。

## 本機啟動

需要 Python 3.12。以下指令在專案根目錄執行。

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m flask --app app run --port 5000
```

開啟 <http://127.0.0.1:5000>。若 macOS 的 AirPlay 已占用 5000，啟動時改用 `--port 5001`，並開啟 <http://127.0.0.1:5001>。

## 規則與分數

`cities.py` 記錄 22 個縣市的代表點。Flask 查詢 Open-Meteo 時使用台灣時區，並只取得今天的資料。`decision_engine.py` 比較個人化體感、最高降雨機率、目前風速與最高紫外線指數。

| 行程 | 體感 | 降雨 | 風速 | 紫外線 |
| --- | ---: | ---: | ---: | ---: |
| 機車通勤 | 30% | 35% | 30% | 5% |
| 校園／上班步行 | 45% | 25% | 15% | 15% |
| 戶外約會出遊 | 35% | 25% | 15% | 25% |

怕熱把體感加 2°C，怕冷減 2°C。各項天氣負擔換算為 0–100，舒適度為 100 減去加權總負擔。綠燈是 75 分以上，黃燈是 50–74 分，紅燈是 49 分以下。溫差達 7°C 便顯示分層穿搭提醒。降雨機率達 50% 或目前有降水訊號時建議帶雨具，機車通勤或風速達 35 km/h 時優先建議雨衣。紫外線指數達 3 時提示防曬。這些量化門檻是課程規則。

## 更換圖片

原創 SVG 放在 `static/images/outfits/`，檔名和顯示名稱集中在 `outfit_assets.py`。可將自己的 PNG 或 WebP 放進同一資料夾，再更新對應表。改完圖或樣式後同步 Vercel 使用的靜態副本，並將兩邊都納入 Git。

```bash
cp -R static/. public/static/
python -m unittest discover -s tests -v
```

## Vercel

從 Vercel 匯入 GitHub 儲存庫，以儲存庫根目錄作為專案根目錄。Vercel 可辨識 `app.py` 裡的 `app`，使用 `.python-version` 指定的 Python 3.12 和 `requirements.txt` 的套件。圖片和樣式在 `public/static/`，對應到本機 Flask 使用的相同 `/static/` 網址。 [Vercel Flask 文件](https://vercel.com/docs/frameworks/backend/flask)

氣象資料由 [Open-Meteo](https://open-meteo.com/) 提供，資料採 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)。公開 API 的免費端點適用於非商業用途。 [Open-Meteo 使用條款](https://open-meteo.com/en/terms)
