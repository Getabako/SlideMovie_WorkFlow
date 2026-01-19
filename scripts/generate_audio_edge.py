#!/usr/bin/env python3
"""
Edge TTSを使用した音声生成スクリプト
Python 3.13互換
"""

import sys
import os
import json
import asyncio
from pathlib import Path
import edge_tts

async def generate_audio_for_slide(text, output_file, voice="ja-JP-NanamiNeural"):
    """1つのスライドの音声を生成"""
    if not text or not text.strip():
        print(f"    警告: テキストが空です")
        # 無音ファイルは作成しない
        return None

    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_file)
    return output_file

async def generate_all_audio(script_file, output_dir):
    """全スライドの音声を生成"""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 原稿を読み込み
    with open(script_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    slides = data.get('slides', [])
    print(f"スライド数: {len(slides)}")

    audio_files = []

    for i, slide in enumerate(slides):
        script_text = slide.get('script', '')
        output_file = output_dir / f"slide_{i+1:03d}.mp3"

        print(f"スライド {i+1}: 音声生成中...")

        try:
            result = await generate_audio_for_slide(script_text, str(output_file))
            if result:
                audio_files.append({
                    'slide': i + 1,
                    'file': str(output_file),
                    'text': script_text[:50] + '...' if len(script_text) > 50 else script_text
                })
                print(f"    完了: {output_file}")
        except Exception as e:
            print(f"    エラー: {e}")

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
        print("使用方法: python generate_audio_edge.py <script_json_file>")
        sys.exit(1)

    script_file = sys.argv[1]

    if not os.path.exists(script_file):
        print(f"エラー: 原稿ファイルが見つかりません: {script_file}")
        sys.exit(1)

    # 出力ディレクトリ
    script_path = Path(script_file)
    output_dir = script_path.parent.parent / "audio_output"

    # 音声を生成
    asyncio.run(generate_all_audio(script_file, output_dir))

    print(f"\n音声生成完了！")

if __name__ == "__main__":
    main()
