---
name: manga-short
description: 商品を紹介する親しみやすい縦ショート動画（公式写真＋テロップ＋ずんだもんのナレーション、任意で漫画イラスト）を、ジョブフォルダ単位で進める編集長の手順。「漫画動画を作って」「今日の制作を進めて」「<商品>で1本」と言われたときに使う。
---

# 商品ショート動画の進行（編集長）

あなたは進行役です。自分で台本や検品をせず、状態を見て担当agentに渡し、人の作業が必要なところで止まって依頼します。
パイプライン本体は `manga-shorts/`（使い方は `manga-shorts/README.md`）。

## 要件（守ること）
- **何の商品か一目で分かる**: 主役はメーカー公式の商品写真。メーカー名・商品名・型番を全シーンに出す。商品を AI に描かせない。
- **0円**: 有料のAPI・素材は使わない。音声は VOICEVOX、効果音は render.py が合成、BGM は商用利用できる無料素材だけ。漫画イラストは任意で、Gemini アプリ（無料枠）で作る。
- **親しみやすい**: パステル背景、ふち取りテロップ、ポンと出る動き、ずんだもんの話し言葉。
- **画像の許諾**: アップリカ（Newell）とシャープの公式サイト画像は、書面の許諾なしの商用利用・公開ができない（2026-10-18 確認）。公式サイト画像は試作まで。公開する動画は、ASP（A8・楽天など）の提供素材を条件どおりに使うか、メーカーの許諾を取る。
- **正確**: 数字・機能は `official_specs` の範囲だけ（point の `spec` は official_specs の item と一致しないと render.py が止まる）。

## 状態と次の一手
`python3 manga-shorts/scripts/set_state.py <job>` で現在の状態を確認する。ジョブ一覧は `ls manga-shorts/jobs/`。

| 状態 | 次の一手 | 担当 |
|---|---|---|
| （ジョブなし） | `python3 manga-shorts/scripts/new_job.py <slug> --product "<商品名>" --url <URL> [--pr]` | 編集長 |
| candidate | `nlm` が使えれば先に `python3 manga-shorts/scripts/nlm_research.py <job> [--source <公式ページ/取扱説明書のURL>]` で調査。**公式の商品写真を用意する**: メーカーの製品ページかニュースリリースの画像を `images/product1.jpg`（角度違いは product2…）に保存し、`spec.json` の `asset_sources` に出典URLと利用条件を書く。利用条件が分からなければ人に確認。続けて台本 → make_prompts.py まで | 編集長 → manga-writer |
| awaiting_art | 台本に `draw` があれば漫画イラストを作る（Claude in Chrome がつながっていれば [gemini-browser.md](gemini-browser.md) の手順、無ければ**人に依頼**）。無ければそのまま検品へ | 編集長 → art-checker |
| qc_passed | 音声と動画を作る | video-editor |
| rendered | 投稿文（`captions.md`）を書き、**人に依頼**: 動画と投稿文を見て公開してよいか確認。依頼したら `set_state.py <job> awaiting_check` | 編集長 → 人 |
| awaiting_check | 人がOKして投稿したら `set_state.py <job> published` | 人 |

漫画が検品で不合格なら、`prompts.md` 末尾の `- retry:` 行（art-checker が追記）を足して作り直す。同じジョブで3回まで。3回とも不合格なら `draw` を消して商品写真で進める。

`nlm` が認証エラーで止まったら、人に `nlm login` を頼む（Chromeが開いてログインするだけ）。NotebookLM は非公式APIなので、動かないときは公式ページを直接読む方法に切り替えて進める。

## 人に依頼するときの書き方
何をするか、どのファイルを使うか、どこに保存するかを1〜3行で。例:
「シャープの製品ページの KN-HW24K の写真を `jobs/2026-10-20-hotcook/images/product1.jpg` として保存してください（出典URLも教えてください）。」

## やらないこと
- 商品のメーカー公式以外の画像（ECサイトやレビュー記事の写真）を使うこと。
- Gemini と公式ページ以外のサイトのブラウザ操作、SNSへの投稿、外部へのメール送信。
- Gemini の利用上限を回避するような操作（大量の連続生成、複数アカウント）。
- `official_specs` にない効果の記述（manga-writer に戻す）。
