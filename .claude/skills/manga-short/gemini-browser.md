# Gemini アプリでの漫画イラスト作成（Claude in Chrome）

こうきさんの判断で、漫画イラストは PC の Chrome で Gemini アプリ（Google AI Pro）を操作して作る。
Google の規約は自動操作を想定していないため、アカウントに影響が出るおそれがあることは本人了承済み。
イラストは任意（台本の `draw` があるシーンだけ、1本あたり1〜2枚）。人が使うのと同じペースで操作する。
商品は公式写真で見せるので、Gemini に商品を描かせたり、商品写真を添付したりしない。

## 前提
- `mcp__claude-in-chrome__*` が使え、PCの Chrome がつながっている（`list_connected_browsers`）。
- Gemini にログイン済み。3面図を作ったチャット「Manga Character Reference Sheet」を使い回す（3面図がチャット内にあるので毎回添付しなくてよい）。

## 手順
1. Gemini のタブでそのチャットを開く。
2. **プロンプトを送る**: `prompts.md` の `## images/mangaN.png` の下のブロックを1行にし、「attached character reference sheet」を「character reference sheet earlier in this chat」に置き換える。入力欄に入れて送信する（JS なら `rich-textarea .ql-editor` に `document.execCommand('insertText', false, text)` してから `button[aria-label*="送信"]` をクリック）。
3. **待つ**: `model-response img`（naturalWidth > 300）の数が1つ増え、停止ボタンが消えるまで。
4. **取り込む**: Gemini はファイルを直接渡せないので、画面に出して撮る。最後の画像を canvas で dataURL にし、`position:fixed` の白いオーバーレイに等倍（`max-width:none`）で左上に置く（`innerHTML` は Trusted Types で拒否されるので `createElement` を使う）。
   - 画面に収まらなければ、上端（offset 0）と下側（offset N）の2枚を `screenshot`（scale 1、`save_to_disk: true`）で撮り、つなぐ:
     `python3 manga-shorts/scripts/stitch_tiles.py <job>/images/mangaN.png <1枚目> <2枚目> --size <幅>x<高さ> --viewport <innerWidth>x<innerHeight> --offset N`
   - 終わったらオーバーレイを消す。
5. 検品へ。

## 注意
- 取り込めるのは Gemini の表示サイズ（長辺1024px）。動画ではカードの中に収まる大きさで出るので、十分な解像度。
- 1枚の指示でも、中で2コマに分けて描かれることがある。気になる場合は「no panel borders inside the image」を足して作り直す。
- 家電や道具が出る場面では、「no appliance that looks like the product」と書かないと商品に似た物が描かれる。
