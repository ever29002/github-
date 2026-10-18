# manga-shorts

商品を紹介する、親しみやすい縦ショート動画（1080x1920、20〜30秒）を0円で作るパイプライン。

- **何の商品か一目で分かる**: 主役はメーカー公式の商品写真。メーカー名・商品名・型番を全シーンの上部に出す。商品は AI に描かせない。
- **親しみやすい**: パステルの水玉背景、白ふち取りのテロップ、ポンと出る動きと効果音、ずんだもん（VOICEVOX）の話し言葉。
- **正確**: 数字・機能は公式の仕様（`spec.json` の `official_specs`）だけ。台本の point が公式仕様と一致しないと止まる。
- **0円**: 音声は VOICEVOX、効果音は render.py が合成、BGM は無料素材。漫画イラストは任意で、Gemini アプリで作る。

構成: つかみ（困りごと）→ 商品紹介（公式写真と名前）→ ポイント2〜3個（公式の数字を大きく）→ 使い方3ステップ → まとめ。

## 必要なもの（すべて無料）
- Python 3.10+、`pip install pillow pyyaml`
- ffmpeg（libx264 入り）
- 日本語フォント（Windows の BIZ UDゴシック/游ゴシック、macOS のヒラギノ、Linux の Noto/IPA を自動で探す）。丸ゴシックにしたい場合は Zen Maru Gothic などの無料フォントを `assets/fonts/` に置くとそれを使う
- 音声: [VOICEVOX](https://voicevox.hiroshiba.jp/)（起動しておくと `http://127.0.0.1:50021` で使える）。無い場合は `--engine silent` で無音
- NotebookLM 連携（任意）: [notebooklm-mcp-cli](https://github.com/jacob-bd/notebooklm-mcp-cli) の `nlm` コマンド。`nlm login` しておく。非公式の内部APIを使うため、予告なく動かなくなることがある
- 漫画イラスト（任意）: Gemini アプリ。`gen_art.py`（Gemini API）は有料なので既定では使わない

## 流れ
```
python3 scripts/new_job.py hotcook --product "シャープ ヘルシオ ホットクック KN-HW24K" --url https://... --pr
#  → jobs/<日付>-hotcook/ ができる（spec.json, name.yaml, captions.md）
python3 scripts/nlm_research.py jobs/<日付>-hotcook --source https://<取扱説明書のURL>
#  → research.md と spec.json の official_specs が埋まる
#  [編集長/人] メーカー公式の商品写真を images/product1.jpg に置き、spec.json の asset_sources に出典を書く
#  [manga-writer] research.md と spec.json をもとに name.yaml（シーン構成）を書く
python3 scripts/render.py jobs/<日付>-hotcook --preview   # preview.png で各シーンの見た目を確認
python3 scripts/make_prompts.py jobs/<日付>-hotcook       # 漫画イラストを使うときだけ prompts.md ができる
#  [art-checker] 写真の出典と見た目、漫画イラストを検品して qc.json を書く
python3 scripts/tts.py jobs/<日付>-hotcook               # VOICEVOX（--engine silent で無音）
python3 scripts/gen_bgm.py                                # 初回だけ: 0円のBGM → assets/bgm/pop-loop.wav
python3 scripts/render.py jobs/<日付>-hotcook --bgm assets/bgm/pop-loop.wav --bgm-volume 0.25
#  → video.mp4
#  [人] 動画と captions.md を確認して投稿
```

Claude Code では `manga-short` スキル（`.claude/skills/manga-short/`）が状態を見て、`.claude/agents/` の manga-writer / art-checker / video-editor に順に渡す。

## name.yaml のシーン
| type | 画面 | 主な項目 |
|---|---|---|
| `hook` | 大きなテロップ＋写真（または漫画） | `text`（1行9字まで、`\n` で改行）、任意で `image`/`draw` |
| `product` | 公式写真を大きく、メーカー・名前・型番 | `image` |
| `point` | 写真＋公式の数字を特大で | `big`、`text`、`spec`（official_specs の item をそのまま） |
| `steps` | 番号付きの3ステップが順に出る | `title`、`steps` |
| `outro` | 写真＋名前＋リンク誘導 | `text` |

各シーンに `narration`（読み上げ文）を書く。`theme` は orange / green / blue / pink。

## ジョブフォルダ
| ファイル | 中身 |
|---|---|
| `status.json` | 状態と履歴（candidate → awaiting_art → qc_passed → rendered → awaiting_check → published） |
| `spec.json` | 商品名、URL、PRかどうか、公式スペック、素材の出典 |
| `research.md` | NotebookLM の調査結果（仕様・使い方・注意点・ネタ候補） |
| `name.yaml` | 台本（シーン構成・テロップ・ナレーション） |
| `images/product*.jpg` | メーカー公式の商品写真 |
| `images/manga*.png` | 任意の漫画イラスト |
| `prompts.md` | 漫画イラストの作画プロンプト（使うときだけ） |
| `preview.png` | 各シーンの見た目の一覧 |
| `qc.json` | 検品結果 |
| `audio/` | シーンごとの音声と、効果音を混ぜた narration.wav |
| `video.mp4` | 完成動画 |
| `captions.md` | 各SNSの投稿文 |

`jobs/` の中身は git に入れない。

## 注意
- 効果・機能の説明は `spec.json` の公式スペックの範囲にとどめる。PR・アフィリエイトの表記を入れる（PR のジョブは動画にPRバッジが出る）。
- 商品画像はメーカー公式の製品ページやニュースリリースの画像だけを使い、出典を `asset_sources` に書く。メーカーサイトの画像は多くが無断の商用利用・転載を禁じているので、公開する動画にはASPの提供素材（各プログラムの条件どおり）かメーカーの許諾を得た画像を使う。
- 字幕フォント M PLUS Rounded 1c は SIL Open Font License（`assets/fonts/OFL.txt`）。
- VOICEVOX の音声は、キャラクターごとの規約に従いクレジット（例: 「VOICEVOX:ずんだもん」）を入れる。
- BGM は商用利用できる無料音源だけを使う。
