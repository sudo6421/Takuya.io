# Takuya.io

拓也さんの料金表をJSONで取得し、見積もりを計算するWebAPIです。

## GitHubから入手する

このリポジトリの「Code → Download ZIP」でダウンロードして展開してください。
Gitを使う場合は「Code」からリポジトリURLをコピーして `git clone` し、取得したフォルダーに移動します。
以下の手順はすべて、そのフォルダー内で実行します。GitHubでのコード配布だけではAPIサーバーは起動しません。

## 起動

Python 3.10以上をインストールし、このREADMEと同じフォルダーで実行します。

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe app.py
```

macOS/Linuxでは `.venv\Scripts\python.exe` を `.venv/bin/python` に読み替えてください。
起動後は http://127.0.0.1:5000 にアクセスできます。停止は Ctrl+C。
これはローカル開発サーバーです。公開運用には別途WSGIサーバー等を用意してください。

## エンドポイント

| メソッド | URL | 動作 |
|---|---|---|
| GET | `/` | APIの案内 |
| GET | `/api/v1/prices` | 料金表・ID・条件・計算上の仮定 |
| POST | `/api/v1/quotes` | 見積もり計算（保存しないため200） |

```powershell
Invoke-RestMethod http://127.0.0.1:5000/api/v1/prices
$body = @{plan='visit-90'; region='tokyo'; discounts=@('repeater'); extension_units=1} | ConvertTo-Json
Invoke-RestMethod http://127.0.0.1:5000/api/v1/quotes -Method Post -ContentType 'application/json' -Body $body
```

この例の合計は 18,400円（16,000 − 1,600 + 延長3,000 + 交通費1,000）。

## 見積もりの入力

| フィールド | 型・指定値 | 省略時 |
|---|---|---|
| plan | `visit-60`, `visit-90`, `visit-120`, `stay`, `date`, `charter` | 必須 |
| region | `tokyo` 都内 / `nearby` 原文の近郊 / `remote` 遠方 | 必須 |
| extension_units | 延長30分の回数、整数0〜48 | 0 |
| days | 貸切日数、整数1〜365、貸切専用 | 1 |
| discounts | IDの配列: `repeater` 10%、`younger` 10%、`top` 20% | `[]` |
| options | IDの配列。`GET /api/v1/prices` のoptionsを参照 | `[]` |
| photography | `none`, `body`, `anonymous`, `face`, `commercial` | `none` |
| shooting_only | 撮影のみか、JSONのtrue/false | false |
| round_trip_fare | 遠方の往復交通費、整数円0〜10000000 | 遠方では必須 |
| round_trip_minutes | 遠方の往復所要時間、整数分1〜10000000 | 遠方では必須 |
| start_time | デート開始時刻、`HH:MM` | デートでは必須 |

不明フィールド、型違い、配列内の重複、不正な組合せは400。JSON以外は415、本文16KiB超は413、存在しないURLは404、未対応メソッドは405。エラーもJSONです。

## 計算ルール・未定義関連

- 割引は通常出張・ステイの基本料のみ、併用は加算（最大40%）という実装上の仮定です。延長・交通費・オプションには適用しません。
- 通常出張は選択した基本プランに30分ごとの延長を加算。プランは自動で変更しません。延長上限48回・貸切上限365日は入力制限として設けています。
- ステイは22時〜翌9時の固定枠です。
- デートは単独の2時間枠として扱い、`discounts: ["repeater"]` と開始14:00〜20:00が必須。リピーター指定は利用条件の確認にだけ使い、デート料金は割引しません。併用デートには未対応です。
- 貸切は1日55,000円、2日以上は `日数×50,000−日数×10,000`。3日は120,000円です。交通費は別に加算します。
- 遠方料金は通常交通費と置き換え、`往復交通費 + ceil(往復分数×1000/60)`。円未満切り上げは実装上の仮定。`prepaid_amount` は合計に含まれる事前振込分で、再加算しません。
- 撮影のみは通常出張の基本料を半額にし、その後に割引を適用します。半額対象範囲と適用順は仮定です。3Pコースは価格未提供のため未対応です。「お客様が複数:無料」と3Pコースは同一視しません。
- 撮影は通常出張の総時間120分以内のみ算定。顔出し・営利目的・120分超などは `status: requires_consultation`、`total: null` として未確定のまま返します。`known_subtotal` は確定できた項目だけの小計です。
- 各オプションは1回分。税額は原文に規定がないため追加しません。外見情報・問い合わせ案内は料金データに含めていません。
- これらの仮定はAPIの `assumptions` にも返します。

## ファイルとテスト

`app.py` はHTTP処理、`pricing.py` は料金データ・検証・計算、`test_api.py` は正常系・境界値・HTTPエラーのテストです。

```powershell
.venv\Scripts\python.exe -m unittest -v
```
