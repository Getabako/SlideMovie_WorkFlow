#!/usr/bin/env python3
"""
欠けている音声ファイルを手動生成するスクリプト
VOICEPEAKの140文字制限に対応
"""

import subprocess
import json
from pathlib import Path
import time

# 設定
VOICEPEAK_PATH = "/Applications/voicepeak.app/Contents/MacOS/voicepeak"
NARRATOR = "Japanese Female 1"
SPEED = 150
OUTPUT_DIR = Path("/Users/takasaki19841121/Desktop/SlideMovie_WorkFlow-main/presentations/⑦ホームページ作り/video_output/audio")
SCRIPT_FILE = Path("/Users/takasaki19841121/Desktop/SlideMovie_WorkFlow-main/presentations/⑦ホームページ作り/video_output/script.json")

# 再生成するスライド（原稿を修正したスライド）
# 7-13は完了、残りの16-22を再生成
MISSING_SLIDES = [16, 17, 18, 19, 20, 21, 22]

def split_text(text: str, max_chars: int = 130) -> list:
    """テキストを130文字以下のチャンクに分割"""
    # 改行とスペースを正規化
    clean_text = text.replace('\n', ' ').replace('　', ' ')
    clean_text = ' '.join(clean_text.split())

    if len(clean_text) <= max_chars:
        return [clean_text]

    chunks = []

    # 句点で分割
    sentences = []
    temp = ""
    for char in clean_text:
        temp += char
        if char in '。！？':
            sentences.append(temp)
            temp = ""
    if temp:
        sentences.append(temp)

    current_chunk = ""
    for sentence in sentences:
        if len(current_chunk) + len(sentence) <= max_chars:
            current_chunk += sentence
        else:
            if current_chunk:
                chunks.append(current_chunk)

            # 文が長すぎる場合は読点で分割
            if len(sentence) > max_chars:
                sub_parts = sentence.split('、')
                sub_chunk = ""
                for i, part in enumerate(sub_parts):
                    if i < len(sub_parts) - 1:
                        part_with_comma = part + '、'
                    else:
                        part_with_comma = part

                    if len(sub_chunk) + len(part_with_comma) <= max_chars:
                        sub_chunk += part_with_comma
                    else:
                        if sub_chunk:
                            chunks.append(sub_chunk)
                        sub_chunk = part_with_comma
                if sub_chunk:
                    current_chunk = sub_chunk
                else:
                    current_chunk = ""
            else:
                current_chunk = sentence

    if current_chunk:
        chunks.append(current_chunk)

    return chunks

def generate_single_audio(text: str, output_file: Path) -> bool:
    """VOICEPEAKで単一の音声を生成"""
    wav_file = output_file.with_suffix('.wav')

    cmd = [
        VOICEPEAK_PATH,
        '-s', text,
        '-o', str(wav_file),
        '-n', NARRATOR,
        '--speed', str(SPEED)
    ]

    print(f"    生成中: {len(text)}文字")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            print(f"    エラー: {result.stderr}")
            return False

        # WAVをMP3に変換
        convert_cmd = [
            'ffmpeg', '-y', '-i', str(wav_file),
            '-codec:a', 'libmp3lame', '-qscale:a', '2',
            str(output_file)
        ]
        subprocess.run(convert_cmd, capture_output=True, check=True)

        # WAVファイルを削除
        if wav_file.exists():
            wav_file.unlink()

        return output_file.exists()
    except subprocess.TimeoutExpired:
        print("    タイムアウト")
        return False
    except Exception as e:
        print(f"    例外: {e}")
        return False

def generate_audio_for_slide(slide_index: int, text: str) -> bool:
    """スライドの音声を生成"""
    output_file = OUTPUT_DIR / f"slide_{slide_index:03d}.mp3"
    print(f"\nスライド {slide_index}: {len(text)}文字")

    chunks = split_text(text)
    print(f"  {len(chunks)}チャンクに分割")

    if len(chunks) == 1:
        return generate_single_audio(chunks[0], output_file)

    # 複数チャンクの場合
    temp_dir = OUTPUT_DIR / "temp_chunks"
    temp_dir.mkdir(exist_ok=True)
    temp_files = []

    try:
        for i, chunk in enumerate(chunks):
            print(f"  チャンク {i+1}/{len(chunks)}")
            temp_file = temp_dir / f"chunk_{i:03d}.mp3"
            if not generate_single_audio(chunk, temp_file):
                print(f"  チャンク {i+1} 生成失敗")
                return False
            temp_files.append(temp_file)
            time.sleep(1)  # VOICEPEAKに休憩を与える

        # 音声ファイルを結合
        concat_list = temp_dir / "concat.txt"
        with open(concat_list, 'w') as f:
            for tf in temp_files:
                f.write(f"file '{tf.name}'\n")

        concat_cmd = [
            'ffmpeg', '-y', '-f', 'concat', '-safe', '0',
            '-i', str(concat_list), '-codec:a', 'libmp3lame', '-qscale:a', '2',
            str(output_file)
        ]
        subprocess.run(concat_cmd, capture_output=True, check=True)

        print(f"  結合完了: {output_file.name}")
        return output_file.exists()

    finally:
        # クリーンアップ
        for tf in temp_files:
            if tf.exists():
                tf.unlink()
        if temp_dir.exists():
            for f in temp_dir.glob("*"):
                f.unlink()
            temp_dir.rmdir()

def main():
    # スクリプトを読み込む
    with open(SCRIPT_FILE, 'r', encoding='utf-8') as f:
        script_data = json.load(f)

    slides = {s['index']: s['script'] for s in script_data['slides']}

    print("=== 欠けている音声ファイルを生成 ===")
    print(f"VOICEPEAK: {NARRATOR}, 速度: {SPEED}")

    for slide_index in MISSING_SLIDES:
        if slide_index in slides:
            text = slides[slide_index]
            success = generate_audio_for_slide(slide_index, text)
            if success:
                print(f"  ✓ スライド {slide_index} 完了")
            else:
                print(f"  ✗ スライド {slide_index} 失敗")
        else:
            print(f"  スライド {slide_index} が見つかりません")

    # 確認
    print("\n=== 確認 ===")
    for slide_index in MISSING_SLIDES:
        output_file = OUTPUT_DIR / f"slide_{slide_index:03d}.mp3"
        if output_file.exists():
            print(f"  ✓ slide_{slide_index:03d}.mp3 存在")
        else:
            print(f"  ✗ slide_{slide_index:03d}.mp3 欠落")

if __name__ == "__main__":
    main()
