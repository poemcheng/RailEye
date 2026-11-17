# RailEye v0.5 — 延遲土壤含水量與降雨事件

## 開啟
已建置網站的 `#hydro` 頁籤為新模組；保留環境、臺鐵分級、監測與協作頁。程式在部署時由 `scripts/prepare_hydro_site.py` 添加三個靜態資產引用。原始碼本機預覽先執行 `python scripts/prepare_hydro_site.py --in-place`。

## 來源與論文
Palazzolo, N., Cancelliere, A., Zofei, R. D., and Peres, D. J. (2025). Use of delayed ERA5-Land soil moisture products for improving landslide early warning. NHESS 25, 4907–4919. https://doi.org/10.5194/nhess-25-4907-2025 (CC BY 4.0).

借用 D、E、S2、0–15 日延遲與四層深度定義。沒有取得原文模型權重，沒有聲稱重現其 ANN。頁面文獻圖是原文表 3、4 的已發表平均 TSS，不是本系統效能；test 與 all 分開。原文使用 CTRL-T；本版是獨立的可測試 dry-gap-v1 事件初篩，並非 CTRL-T。預設乾期 24h、濕小時 0.2 mm 是研究參數，非臺鐵安全門檻。

## 已實作
- 明確指定 `models=era5_land` 的 Open-Meteo archive 取得前三層 0–7 / 7–28 / 28–100 cm；返回網格及查詢座標分開保存。
- 第四層 Open-Meteo 公開文件標 100–255 cm，與論文/CDS 100–289 cm 不同。未擅自重新命名，s4 留 null。只有正式 CDS 適配器成功取得才能填值。
- `valid_at`、未知的 `available_at`、保守 `first_seen_at`、`fetched_at`、值雜湊分開。快取保留同一網格/值版本的首次取得時間；不能回推真實歷史發布時間。快取被淘汰時採新首次取得時間，不冒認歷史可用。
- 延遲 k 相對事件起始時間；嚴格取同小時，不插值。超出當前資料可用時點的資料不能選。
- 使用氣象模式過去雨量估計重建事件；不把它稱為測站雨量。未發布/未到時/缺測/重複時刻均明確處理。缺測中斷事件，沒有完整前導乾期則起點不確定。
- D 為首個濕小時起至末個濕小時止，包含中間乾時段、不包含尾端乾期。事件結束必須已觀察到指定乾期。
- 未完成事件或起點不明事件不作原文完整事件 ln(D),ln(E),ln(S2) 輸入。即使特徵完整，模型與崩塌機率仍未啟用。
- 每次部署另留公開環境與土壤資料、SHA256 manifest 的 Actions artifact，保存 30 天；不是不可變、永久資料庫。長期科研需在到期前另存。

## CDS 正式四層
CDS 帳號須先同意 ERA5-Land 授權條款。在 GitHub Repository Secrets 設定 `CDSAPI_KEY`，不要將 token 放到程式、聊天或 JSON。可選 collector 每 20h 以後重新嘗試少量區域近 25 日資料；等待超過時間預算即失敗，不把空值填成成功。`collect_era5_cds.py` 明確處理 swvl1–4、原始單位、UTC、網格、未確認版本；遇到多個 expver 會停止，要求人工處理，不偷偷合併。

直接 CDS 有效性仍需以實際回應驗證；未設定金鑰時只運作明確標示的第三方前三層。參考 https://cds.climate.copernicus.eu/datasets/reanalysis-era5-land 和 https://open-meteo.com/en/docs/historical-weather-api 。

## 更新與限制
沿用每半小時環境部署。土壤 HTTP 請求有 20h 快取，不代表土壤每半小時更新；網格再分析本身約有多日發布延遲。前端每 5 分鐘刷新快照；超過 36h 未下載的土壤來源不可作當前特徵。資料年齡另顯示，不以最近下載時間冒充觀測時間。

維持 `slope_probability=null`，不控制 A–D、DWS、TSR，不宣布坡體安全。跨路線訓練、機率校準、Gold Labels、人因實驗未在本次完成。當前資料不可用來宣稱已具備線上預警準確率。

## 測試
`node tests/hydro-core.cjs`、`python -m unittest discover -s tests -p test_soil.py -v`。離線 UI 測試使用明確標示 SYNTHETIC_TEST_ONLY fixture；真實公開資料取得與 HTTPS 發布由部署後檢查另行記錄。
