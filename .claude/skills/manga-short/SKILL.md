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
| candidate | ネームを書く → make_prompts.py まで | manga-writer |
| awaiting_art | **人に依頼**: `prompts.md` をGeminiアプリに貼り、3面図と商品画像を添付して生成、`images/page1.png` に保存してもらう。画像が置かれていれば検品へ | 人 → art-checker |
| qc_passed | 音声と動画を作る | video-editor |
| rendered | 投稿文（`captions.md`）を書き、**人に依頼**: 動画と投稿文を見て公開してよいか確認。依頼したら `set_state.py <job> awaiting_check` | 編集長 → 人 |
| awaiting_check | 人がOKして投稿したら `set_state.py <job> published` | 人 |

`awaiting_art` で検品が不合格だったら、`qc.json` の `retry_hint` を `prompts.md` の末尾に足して、人に再生成を依頼する（同じジョブで3回まで）。

## 人に依頼するときの書き方
何をするか、どのファイルを使うか、どこに保存するかを1〜3行で。例:
「`jobs/2026-10-20-cable-box/prompts.md` のプロンプトをGeminiに貼って、3面図と商品画像を添付して生成し、`images/page1.png` として保存してください。」

## やらないこと
- Geminiアプリやブラウザの自動操作、SNSへの投稿、外部へのメール送信。
- `official_specs` にない効果の記述（manga-writer に戻す）。
