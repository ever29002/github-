# manga-shorts

商品の使い方・効果を4コマ漫画で説明し、1コマずつ動かして縦ショート動画（1080x1920）にするパイプライン。
コマは1枚ずつ縦長（9:16）で描き、動画では画面いっぱいに出す。1ページに4コマを並べると1コマが横長の帯になり、縦画面では小さく見えるため。
作画は、PCのChromeで Gemini アプリを操作する（Claude in Chrome、手順は `.claude/skills/manga-short/gemini-browser.md`）か、Gemini API（`gen_art.py`、1枚あたり数円〜十数円）で行う。それ以外（ネーム、作画プロンプト、コマ切り出し、音声、合成）は Claude Code の agent とスクリプトが担当する。動画生成AIは使わない。

## 必要なもの
- Python 3.10+、`pip install pillow pyyaml`
- ffmpeg（libx264 入り。字幕は Pillow で描くので libass は不要）
- 日本語フォント（Linux の IPA/Noto、macOS のヒラギノ、Windows の游ゴシック/メイリオを自動で探す。`--font` で指定も可）
- NotebookLM 連携（任意）: [notebooklm-mcp-cli](https://github.com/jacob-bd/notebooklm-mcp-cli) の `nlm` コマンド。`nlm login` で Chrome からログインしておく。非公式の内部APIを使うため、予告なく動かなくなることがある
- 作画の自動化（任意）: `pip install google-genai` と、Google AI Studio で発行した `GEMINI_API_KEY`（課金を有効にしたプロジェクト）。Google AI Pro の契約とは別料金。モデルは `--model` か `GEMINI_IMAGE_MODEL` で変えられる（既定 `gemini-2.5-flash-image`）
- 音声: [VOICEVOX](https://voicevox.hiroshiba.jp/)（無料。起動しておくと `http://127.0.0.1:50021` で使える）。無い場合は `--engine silent` で字幕だけの動画になる

## 流れ
```
python3 scripts/new_job.py cable-box --product "ケーブル収納ボックス" --url https://... --pr
#  → jobs/<日付>-cable-box/ ができる（spec.json, name.yaml, captions.md）
python3 scripts/nlm_research.py jobs/<日付>-cable-box --source https://<取扱説明書のURL>
#  → NotebookLM に公式ページを入れて質問し、research.md と spec.json の仕様を埋める（PCで nlm が使える場合）
#  [manga-writer] research.md と spec.json をもとに name.yaml を書く
python3 scripts/make_prompts.py jobs/<日付>-cable-box
python3 scripts/gen_art.py character                   # 初回だけ: 3面図 → assets/characters/guide.png
python3 scripts/gen_art.py jobs/<日付>-cable-box       # 商品写真を images/product1.jpg に置いてから → images/panel1〜4.png
#  （APIを使わないときは、Chrome で Gemini アプリを操作して同じ4枚を作る。gemini-browser.md 参照）
#  [art-checker] crop_panels.py で切り出し、画像を見て qc.json を書く
python3 scripts/crop_panels.py jobs/<日付>-cable-box
python3 scripts/tts.py jobs/<日付>-cable-box            # VOICEVOX（--engine silent で無音）
python3 scripts/render.py jobs/<日付>-cable-box --bgm assets/bgm/track.mp3
#  → video.mp4
#  [人] 動画と captions.md を確認して投稿
```

Claude Code では `manga-short` スキル（`.claude/skills/manga-short/`）が状態を見て、`.claude/agents/` の manga-writer / art-checker / video-editor に順に渡す。

## ジョブフォルダ
| ファイル | 中身 |
|---|---|
| `status.json` | 状態と履歴（candidate → awaiting_art → qc_passed → rendered → awaiting_check → published） |
| `spec.json` | 商品名、URL、PRかどうか、公式スペック、素材の出典 |
| `research.md` | NotebookLM の調査結果（仕様・使い方・注意点・ネタ候補） |
| `name.yaml` | 4コマのネーム（作画指示・字幕・読み上げ文） |
| `prompts.md` | Gemini に貼る作画プロンプト |
| `images/panel1〜4.png` | 生成したコマ（1コマ1枚、縦長。再生成前の画像は `rejected-panel<N>-<n>.png`） |
| `qc.json` | 検品結果 |
| `panels/` | 切り出したコマ |
| `audio/` | コマごとの音声と結合した narration.wav |
| `video.mp4` | 完成動画 |
| `captions.md` | 各SNSの投稿文 |

`jobs/` の中身は git に入れない。

## 注意
- 効果・機能の説明は `spec.json` の公式スペックの範囲にとどめる。PR・アフィリエイトの表記を入れる（PR のジョブは動画にPRバッジが出る）。
- 商品画像はメーカー公式のプレス素材など、利用許諾のあるものだけを使う。
- VOICEVOX の音声は、キャラクターごとの規約に従いクレジット（例: 「VOICEVOX:ずんだもん」）を入れる。
- BGM は商用利用できる音源だけを使う。
