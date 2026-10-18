# manga-shorts

商品の使い方・効果を4コマ漫画で説明し、1コマずつ動かして縦ショート動画（1080x1920）にするパイプライン。
作画は人が Gemini アプリで行い、それ以外（ネーム、作画プロンプト、コマ切り出し、音声、合成）は Claude Code の agent とスクリプトが担当する。動画生成AIは使わないので、追加費用はほぼかからない。

## 必要なもの
- Python 3.10+、`pip install pillow pyyaml`
- ffmpeg（libx264 入り。字幕は Pillow で描くので libass は不要）
- 日本語フォント（Linux の IPA/Noto、macOS のヒラギノ、Windows の游ゴシック/メイリオを自動で探す。`--font` で指定も可）
- 音声: [VOICEVOX](https://voicevox.hiroshiba.jp/)（無料。起動しておくと `http://127.0.0.1:50021` で使える）。無い場合は `--engine silent` で字幕だけの動画になる

## 流れ
```
python3 scripts/new_job.py cable-box --product "ケーブル収納ボックス" --url https://... --pr
#  → jobs/<日付>-cable-box/ ができる（spec.json, name.yaml, captions.md）
#  [manga-writer] spec.json に公式スペックを転記し、name.yaml を書く
python3 scripts/make_prompts.py jobs/<日付>-cable-box
#  [人] prompts.md を Gemini アプリに貼り、3面図と商品画像を添付して生成 → images/page1.png に保存
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
| `name.yaml` | 4コマのネーム（作画指示・字幕・読み上げ文） |
| `prompts.md` | Gemini に貼る作画プロンプト |
| `images/page1.png` | 人が生成した4コマ |
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
