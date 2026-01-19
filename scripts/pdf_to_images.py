#!/usr/bin/env python3
"""
PDFを画像に分割するスクリプト

使用方法:
    python scripts/pdf_to_images.py <PDFファイルパス> [--dpi DPI] [--output-dir 出力先]

例:
    python scripts/pdf_to_images.py "presentations/プレゼン名/スライド.pdf"
    python scripts/pdf_to_images.py "presentations/プレゼン名/スライド.pdf" --dpi 300
"""

import argparse
import subprocess
import sys
from pathlib import Path


def pdf_to_images(pdf_path: str, output_dir: str = None, dpi: int = 200) -> list[str]:
    """
    PDFを画像に変換する

    Args:
        pdf_path: PDFファイルのパス
        output_dir: 出力先ディレクトリ（指定しない場合はPDFと同じフォルダに「スライド画像」を作成）
        dpi: 解像度（デフォルト: 200）

    Returns:
        生成された画像ファイルのパスリスト
    """
    pdf_path = Path(pdf_path).resolve()

    if not pdf_path.exists():
        raise FileNotFoundError(f"PDFファイルが見つかりません: {pdf_path}")

    if not pdf_path.suffix.lower() == '.pdf':
        raise ValueError(f"PDFファイルではありません: {pdf_path}")

    # 出力先ディレクトリを決定
    if output_dir:
        output_path = Path(output_dir).resolve()
    else:
        output_path = pdf_path.parent / "スライド画像"

    output_path.mkdir(parents=True, exist_ok=True)

    # ファイル名のベース（拡張子なし）
    base_name = pdf_path.stem

    # pdftoppmを使用してPDFを画像に変換
    output_prefix = output_path / base_name

    print(f"変換開始: {pdf_path}")
    print(f"出力先: {output_path}")
    print(f"解像度: {dpi} DPI")

    try:
        result = subprocess.run(
            [
                "pdftoppm",
                "-png",
                "-r", str(dpi),
                str(pdf_path),
                str(output_prefix)
            ],
            capture_output=True,
            text=True,
            check=True
        )
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"pdftoppmの実行に失敗しました: {e.stderr}")
    except FileNotFoundError:
        raise RuntimeError("pdftoppmがインストールされていません。Homebrewでインストールしてください: brew install poppler")

    # 生成されたファイルをリネーム（pdftoppmは -01, -02 形式で出力するため）
    generated_files = sorted(output_path.glob(f"{base_name}-*.png"))
    renamed_files = []

    for i, old_path in enumerate(generated_files, start=1):
        new_name = f"{base_name}_{i:02d}.png"
        new_path = output_path / new_name
        old_path.rename(new_path)
        renamed_files.append(str(new_path))
        print(f"  生成: {new_name}")

    print(f"\n完了: {len(renamed_files)}枚の画像を生成しました")
    print(f"保存先: {output_path}")

    return renamed_files


def main():
    parser = argparse.ArgumentParser(
        description="PDFを画像に分割する",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
例:
    python scripts/pdf_to_images.py "presentations/プレゼン名/スライド.pdf"
    python scripts/pdf_to_images.py "presentations/プレゼン名/スライド.pdf" --dpi 300
    python scripts/pdf_to_images.py "presentations/プレゼン名/スライド.pdf" --output-dir ./output
        """
    )
    parser.add_argument("pdf_path", help="変換するPDFファイルのパス")
    parser.add_argument("--dpi", type=int, default=200, help="解像度（デフォルト: 200）")
    parser.add_argument("--output-dir", help="出力先ディレクトリ（デフォルト: PDFと同じフォルダに「スライド画像」を作成）")

    args = parser.parse_args()

    try:
        pdf_to_images(args.pdf_path, args.output_dir, args.dpi)
    except Exception as e:
        print(f"エラー: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
