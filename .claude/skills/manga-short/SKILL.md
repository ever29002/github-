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
| awaiting_art | Claude in Chrome がPCのChromeにつながっていれば、[gemini-browser.md](gemini-browser.md) の手順で Gemini アプリを操作して `images/panel1〜4.png`（縦長）を作る。`GEMINI_API_KEY` があれば `python3 manga-shorts/scripts/gen_art.py <job>` でもよい。どちらも無ければ**人に依頼**。画像ができたら検品へ | 編集長 → art-checker |
| qc_passed | 音声と動画を作る | video-editor |
| rendered | 投稿文（`captions.md`）を書き、**人に依頼**: 動画と投稿文を見て公開してよいか確認。依頼したら `set_state.py <job> awaiting_check` | 編集長 → 人 |
| awaiting_check | 人がOKして投稿したら `set_state.py <job> published` | 人 |

`awaiting_art` で検品が不合格だったら、`prompts.md` 末尾の `- retry:` / `- retryN:` 行（art-checker が追記）を足して、不合格のコマだけ作り直す（`gen_art.py <job> --panel N`、またはブラウザで同じプロンプトに一文足して再生成）。同じジョブで3回まで。3回とも不合格なら人に見てもらう。

`nlm` が認証エラーで止まったら、人に `nlm login` を頼む（Chromeが開いてログインするだけ）。NotebookLM は非公式APIなので、動かないときは公式ページを直接読む方法に切り替えて進める。

## 人に依頼するときの書き方
何をするか、どのファイルを使うか、どこに保存するかを1〜3行で。例:
「`jobs/2026-10-20-cable-box/prompts.md` の4つのプロンプトを同じチャットで順にGeminiに貼り、3面図と商品画像を添付して生成し、`images/panel1.png`〜`panel4.png` として保存してください。」

## やらないこと
- Gemini 以外のサイトのブラウザ操作（商品の公式画像を開く以外）、SNSへの投稿、外部へのメール送信。
- Gemini の利用上限を回避するような操作（大量の連続生成、複数アカウント）。1本あたり4〜8枚程度にとどめる。
- `official_specs` にない効果の記述（manga-writer に戻す）。
