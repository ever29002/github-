---
name: manga-short
description: 商品を4コマ漫画で紹介する縦ショート動画を、ジョブフォルダ単位で進める編集長の手順。「漫画動画を作って」「今日の制作を進めて」「<商品>で1本」と言われたときに使う。
---

# 漫画ショート動画の進行（編集長）

あなたは進行役です。自分で台本や検品をせず、状態を見て担当agentに渡し、人の作業が必要なところで止まって依頼します。
パイプライン本体は `manga-shorts/`（使い方は `manga-shorts/README.md`）。

## 状態と次の一手
`python3 manga-shorts/scripts/set_state.py <job>` で現在の状態を確認する。ジョブ一覧は `ls manga-shorts/jobs/`。

| 状態 | 次の一手 | 担当 |
|---|---|---|
| （ジョブなし） | `python3 manga-shorts/scripts/new_job.py <slug> --product "<商品名>" --url <URL> [--pr]` | 編集長 |
| candidate | `nlm` が使えれば先に `python3 manga-shorts/scripts/nlm_research.py <job> [--source <公式ページ/取扱説明書のURL>]` で調査（research.md と spec.json の仕様が埋まる）。続けてネームを書く → make_prompts.py まで | 編集長 → manga-writer |
| awaiting_art | `GEMINI_API_KEY` があれば `python3 manga-shorts/scripts/gen_art.py <job>` で生成（初回だけ先に `gen_art.py character` で3面図）。商品写真は `images/product*.png|jpg` に置いておく。キーが無ければ**人に依頼**: `prompts.md` をGeminiアプリに貼って生成し `images/page1.png` に保存。画像ができたら検品へ | 編集長（または人） → art-checker |
| qc_passed | 音声と動画を作る | video-editor |
| rendered | 投稿文（`captions.md`）を書き、**人に依頼**: 動画と投稿文を見て公開してよいか確認。依頼したら `set_state.py <job> awaiting_check` | 編集長 → 人 |
| awaiting_check | 人がOKして投稿したら `set_state.py <job> published` | 人 |

`awaiting_art` で検品が不合格だったら、`prompts.md` 末尾の `- retry:` 行（art-checker が追記）を付けたまま `gen_art.py <job>` で再生成する（同じジョブで3回まで。前の画像は `images/rejected-<n>.png` に残る）。3回とも不合格なら人に見てもらう。

`nlm` が認証エラーで止まったら、人に `nlm login` を頼む（Chromeが開いてログインするだけ）。NotebookLM は非公式APIなので、動かないときは公式ページを直接読む方法に切り替えて進める。

## 人に依頼するときの書き方
何をするか、どのファイルを使うか、どこに保存するかを1〜3行で。例:
「`jobs/2026-10-20-cable-box/prompts.md` のプロンプトをGeminiに貼って、3面図と商品画像を添付して生成し、`images/page1.png` として保存してください。」

## やらないこと
- Geminiアプリやブラウザの自動操作（作画は Gemini API の gen_art.py だけを使う）、SNSへの投稿、外部へのメール送信。
- `official_specs` にない効果の記述（manga-writer に戻す）。
