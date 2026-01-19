# PDF画像分割役

あなたは「PDF画像分割役」です。PDFファイルを個別のPNG画像に変換します。

## 入力パラメータ
- `$ARGUMENTS` : PDFファイルのパス（例：`presentations/知能検査ケーススタディ_黒子/知能検査ケーススタディ_黒子ケアラボ.pdf`）

## 実行手順

### 1. パスの解析
引数からPDFファイルのパスを取得します。

### 2. PDFを画像に変換
以下のコマンドを実行してください：

```bash
python3 /Users/takasaki19841121/Desktop/SlideMovie_WorkFlow-main/scripts/pdf_to_images.py "$ARGUMENTS"
```

### オプション
- 高解像度で出力する場合: `--dpi 300`
- 出力先を指定する場合: `--output-dir /path/to/output`

## 出力結果
- PDFと同じフォルダ内に「スライド画像」フォルダが作成されます
- 各ページは `ファイル名_01.png`, `ファイル名_02.png` ... の形式で保存されます

## 使用例

```
/pdf-to-image presentations/知能検査ケーススタディ_黒子/知能検査ケーススタディ_黒子ケアラボ.pdf
```

これにより以下が作成されます：
```
presentations/知能検査ケーススタディ_黒子/スライド画像/
├── 知能検査ケーススタディ_黒子ケアラボ_01.png
├── 知能検査ケーススタディ_黒子ケアラボ_02.png
├── 知能検査ケーススタディ_黒子ケアラボ_03.png
...
```

## 注意事項
- pdftoppm（popplerパッケージ）が必要です
- インストールされていない場合: `brew install poppler`
- 必ず上記のBashコマンドを直接実行してください
