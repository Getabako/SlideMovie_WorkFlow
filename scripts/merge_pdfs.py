#!/usr/bin/env python3
"""
PDF結合スクリプト

指定されたディレクトリ内のPDFファイルを番号順に結合します。
"""

import os
import sys
import re
from pathlib import Path
import argparse

try:
    import fitz  # PyMuPDF
except ImportError:
    print("エラー: PyMuPDFをインストールしてください")
    print("  pip install PyMuPDF")
    sys.exit(1)


def extract_number_from_filename(filename: str) -> int:
    """ファイル名から数字を抽出してソート用のキーを返す"""
    stem = Path(filename).stem

    # 丸数字の対応（①〜⑳）
    circled_numbers = '①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳'
    if stem and stem[0] in circled_numbers:
        return circled_numbers.index(stem[0]) + 1

    # ファイル名の先頭の数字を抽出 (例: "01_xxx.pdf" -> 1, "2.xxx.pdf" -> 2)
    match = re.match(r'^(\d+)', stem)
    if match:
        return int(match.group(1))
    # 先頭に数字がない場合はファイル名全体で比較（最後にソート）
    return float('inf')


def merge_pdfs(pdf_dir: str, output_file: str = None) -> Path:
    """
    PDFファイルを番号順に結合

    Args:
        pdf_dir: PDFファイルが含まれるディレクトリ
        output_file: 出力ファイル名（デフォルト: merged.pdf）

    Returns:
        結合されたPDFファイルのパス
    """
    pdf_dir = Path(pdf_dir)

    if not pdf_dir.is_dir():
        raise NotADirectoryError(f"ディレクトリが見つかりません: {pdf_dir}")

    # PDFファイルを検索
    pdf_files = list(pdf_dir.glob("*.pdf"))

    # merged.pdfは除外
    pdf_files = [f for f in pdf_files if f.name != "merged.pdf"]

    if not pdf_files:
        raise FileNotFoundError(f"PDFファイルが見つかりません: {pdf_dir}")

    # 番号順にソート
    pdf_files.sort(key=lambda p: extract_number_from_filename(p.name))

    print(f"\n{'='*50}")
    print(f"PDF結合")
    print(f"{'='*50}")
    print(f"入力: {pdf_dir}")
    print(f"\n検出されたPDFファイル（結合順）:")
    for i, pdf in enumerate(pdf_files, 1):
        print(f"  {i}. {pdf.name}")

    # 出力ファイルパス（デフォルトはフォルダ名.pdf）
    if output_file:
        output_path = Path(output_file)
    else:
        output_path = pdf_dir / f"{pdf_dir.name}.pdf"

    # 結合処理
    print(f"\n結合中...")

    merged_doc = fitz.open()
    total_pages = 0

    for pdf_file in pdf_files:
        try:
            doc = fitz.open(str(pdf_file))
            merged_doc.insert_pdf(doc)
            page_count = len(doc)
            total_pages += page_count
            print(f"  + {pdf_file.name} ({page_count}ページ)")
            doc.close()
        except Exception as e:
            print(f"  ! エラー: {pdf_file.name} - {e}")

    # 保存
    merged_doc.save(str(output_path))
    merged_doc.close()

    print(f"\n{'='*50}")
    print(f"完了!")
    print(f"{'='*50}")
    print(f"出力: {output_path}")
    print(f"総ページ数: {total_pages}ページ")

    return output_path


def main():
    parser = argparse.ArgumentParser(
        description='PDFファイルを番号順に結合'
    )
    parser.add_argument(
        'pdf_dir',
        help='PDFファイルが含まれるディレクトリ'
    )
    parser.add_argument(
        '--output', '-o',
        help='出力ファイル名（デフォルト: merged.pdf）'
    )

    args = parser.parse_args()

    try:
        merge_pdfs(args.pdf_dir, args.output)
    except Exception as e:
        print(f"エラー: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
