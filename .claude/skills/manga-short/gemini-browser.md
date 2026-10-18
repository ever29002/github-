# Gemini アプリでの作画（Claude in Chrome）

こうきさんの判断で、作画は PC の Chrome で Gemini アプリ（Google AI Pro）を操作して行う。
Google の規約は自動操作を想定していないため、アカウントに影響が出るおそれがあることは本人了承済み。
1本あたり4〜8枚程度、人が使うのと同じペースで操作する。

## 前提
- `mcp__claude-in-chrome__*` が使え、PCの Chrome がつながっている（`list_connected_browsers`）。
- Gemini にログイン済み。3面図を作ったチャット「Manga Character Reference Sheet」を使い回す（3面図がチャット内にあるので毎回添付しなくてよい）。

## 手順
1. Gemini のタブでそのチャットを開く。
2. **商品写真を添付**: 別タブでメーカー公式の商品画像（spec.json の url のページにある白背景の画像）を開き、ページをクリックしてから次の JS で画像をクリップボードに入れる。Gemini のタブで入力欄をクリックし `ctrl+v`。入力欄の上にサムネイルが出れば成功。
   ```js
   const i=document.images[0]; const c=document.createElement('canvas'); c.width=i.naturalWidth; c.height=i.naturalHeight;
   const x=c.getContext('2d'); x.fillStyle='#fff'; x.fillRect(0,0,c.width,c.height); x.drawImage(i,0,0);
   const b=await new Promise(r=>c.toBlob(r,'image/png')); await navigator.clipboard.write([new ClipboardItem({'image/png':b})]);
   ```
   `upload_image` のドラッグ＆ドロップは Gemini では添付されない。
3. **プロンプトを送る**: `prompts.md` の `### コマN` ブロックを1行にし、「attached character reference sheet」を「character reference sheet earlier in this chat」に、「attached product photo」を「product photo attached earlier in this chat」に置き換える。入力欄に入れて送信する（JS なら `rich-textarea .ql-editor` に `document.execCommand('insertText', false, text)` してから `button[aria-label*="送信"]` をクリック）。
4. **待つ**: `model-response img`（naturalWidth > 300）の数が1つ増え、停止ボタンが消えるまで。
5. **取り込む**: Gemini はファイルを直接渡せないので、画面に出して撮る。最後の画像を canvas で dataURL にし、`position:fixed` の白いオーバーレイに等倍（`max-width:none`）で左上に置く（`innerHTML` は Trusted Types で拒否されるので `createElement` を使う）。
   - 572x1024 の画像なら、上端（offset 0）と offset 190 の2枚を `screenshot`（scale 1、`save_to_disk: true`）で撮る。
   - `python3 manga-shorts/scripts/stitch_tiles.py <job>/images/panelN.png <1枚目> <2枚目> --size 572x1024 --viewport <innerWidth>x<innerHeight> --offset 190`
   - 終わったらオーバーレイを消す。
6. コマ1〜4を順に繰り返し、`crop_panels.py` → 検品へ。

## 注意
- 取り込めるのは Gemini の表示サイズ（長辺1024px）。動画では約2倍に拡大されるので、細かい線は少しぼやける。
- 1コマの指示でも、中で2コマに分けて描かれることがある。気になる場合は「no panel borders inside the image」を足して作り直す。
- 商品と違う物（「古くて重いベビーカー」など）を描かせるコマでは、「clearly NOT the product」と書かないと商品そっくりに描かれる。
