# PDF結合コマンド

指定されたフォルダ内のPDFファイルを番号順に結合します。

## 引数
- `$ARGUMENTS`: プレゼンテーション名（例: `子どもへのIT・AI教育`）

## 処理手順

1. **PDFファイルの検出**
   ```
   presentations/$ARGUMENTS/*.pdf を検索
   ```

2. **番号順にソート**
   - ファイル名の先頭の数字で並び替え
   - 例: `01_xxx.pdf` → `02_xxx.pdf` → `10_xxx.pdf`

3. **PDFを結合**
   ```bash
   # PyMuPDFまたはpdfuniteを使用
   python scripts/merge_pdfs.py "presentations/$ARGUMENTS"
   ```

4. **出力ファイル**
   ```
   presentations/$ARGUMENTS/merged.pdf
   ```

## PDFファイルの命名規則

ファイル名の**先頭に番号**を付けてください：

```
presentations/子どもへのIT・AI教育/
├── 01_AI時代の子育て_新しい学びの地図.pdf
├── 02_Architecting_the_Digital_Future.pdf
├── 03_デジタル消費者から創造者へ.pdf
```

または：

```
├── 1.概要.pdf
├── 2.詳細.pdf
├── 10.まとめ.pdf  # 数値として10としてソート（文字列ソートではない）
```

## 出力

- 結合PDF: `presentations/$ARGUMENTS/merged.pdf`
- ログ: 結合順序を表示

## 必要なパッケージ

```bash
pip install PyMuPDF
```

## 使用例

```
/pdf-merge 子どもへのIT・AI教育
```

結果:
```
=== PDF結合 ===
入力: presentations/子どもへのIT・AI教育/

検出されたPDFファイル（結合順）:
  1. 01_AI時代の子育て_新しい学びの地図.pdf
  2. 02_Architecting_the_Digital_Future.pdf
  3. 03_デジタル消費者から創造者へ.pdf

結合中...
完了: presentations/子どもへのIT・AI教育/merged.pdf
総ページ数: 45ページ
```
