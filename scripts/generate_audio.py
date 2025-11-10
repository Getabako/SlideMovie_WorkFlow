#!/usr/bin/env python3
"""
原稿から音声を生成するスクリプト
Edge TTSを使用して音声を生成します
"""

import sys
import os
import json
import asyncio
from pathlib import Path
import edge_tts

async def generate_audio_for_slide(script_text, output_file, voice='ja-JP-NanamiNeural'):
    """
    1つの原稿から音声を生成

    Args:
        script_text: 原稿テキスト
        output_file: 出力ファイルパス
        voice: 使用する音声
    """
    communicate = edge_tts.Communicate(script_text, voice)
    await communicate.save(output_file)

async def generate_all_audio(script_file, output_dir):
    """
    原稿ファイルから全ての音声を生成

    Args:
        script_file: 原稿JSONファイルのパス
        output_dir: 音声ファイルの出力ディレクトリ
    """
    # 原稿ファイルを読み込む
    with open(script_file, 'r', encoding='utf-8') as f:
        script_data = json.load(f)

    slides = script_data['slides']
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"音声生成中: {len(slides)}スライド")

    # 各スライドの音声を生成
    audio_files = []
    for slide in slides:
        output_file = output_dir / f"slide_{slide['index']:02d}.mp3"
        print(f"  スライド {slide['index']}: {slide['title']}")

        await generate_audio_for_slide(slide['script'], str(output_file))

        audio_files.append({
            'index': slide['index'],
            'title': slide['title'],
            'audio_file': str(output_file),
            'script': slide['script']
        })

        print(f"    保存完了: {output_file}")

    # メタデータを保存
    metadata_file = output_dir / 'audio_metadata.json'
    with open(metadata_file, 'w', encoding='utf-8') as f:
        json.dump({
            'audio_files': audio_files,
            'total_slides': len(slides)
        }, f, ensure_ascii=False, indent=2)

    print(f"\n音声メタデータを保存: {metadata_file}")
    return str(metadata_file)

def main():
    if len(sys.argv) < 2:
        print("使用方法: python generate_audio.py <script_json_file>")
        sys.exit(1)

    script_file = sys.argv[1]

    if not os.path.exists(script_file):
        print(f"エラー: 原稿ファイルが見つかりません: {script_file}")
        sys.exit(1)

    # 出力ディレクトリ
    script_path = Path(script_file)
    output_dir = script_path.parent.parent / "audio_output"

    # 音声を生成
    metadata_file = asyncio.run(generate_all_audio(script_file, output_dir))

    print(f"\n音声生成完了！")

    # GitHub Actions用に環境変数に保存
    if 'GITHUB_ENV' in os.environ:
        with open(os.environ['GITHUB_ENV'], 'a') as f:
            f.write(f"AUDIO_METADATA={metadata_file}\n")
            f.write(f"AUDIO_DIR={output_dir}\n")

if __name__ == "__main__":
    main()
