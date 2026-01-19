#!/usr/bin/env python3
"""VOICEPEAKで音声を生成するスクリプト（長いテキストを分割して処理）"""
import json
import subprocess
import os
import time
import tempfile
import wave

BASE_DIR = "/Users/takasaki19841121/Desktop/SlideMovie_WorkFlow-main"
SCRIPT_PATH = f"{BASE_DIR}/presentations/⑦ホームページ作り/video_output/script.json"
AUDIO_DIR = f"{BASE_DIR}/presentations/⑦ホームページ作り/video_output/audio"
VOICEPEAK_PATH = "/Applications/voicepeak.app/Contents/MacOS/voicepeak"
NARRATOR = "Japanese Female 1"
SPEED = 150
MAX_CHARS = 130  # VOICEPEAKの制限は140文字、余裕を持って130

def split_text(text, max_chars=MAX_CHARS):
    """テキストを句点・読点で分割して、max_chars以下のチャンクに分ける"""
    # 改行を削除
    text = text.replace('\n', '')

    # 文を分割（。！？で分割）
    sentences = []
    current = ""
    for char in text:
        current += char
        if char in '。！？':
            sentences.append(current)
            current = ""
    if current.strip():
        sentences.append(current)

    # 文をmax_chars以下のチャンクにグループ化
    chunks = []
    current_chunk = ""

    for sentence in sentences:
        # 単一の文がmax_charsを超える場合は、読点で分割
        if len(sentence) > max_chars:
            # 読点で分割
            parts = sentence.split('、')
            for i, part in enumerate(parts):
                part_with_comma = part + ('、' if i < len(parts) - 1 else '')
                if len(current_chunk) + len(part_with_comma) <= max_chars:
                    current_chunk += part_with_comma
                else:
                    if current_chunk:
                        chunks.append(current_chunk)
                    current_chunk = part_with_comma
        else:
            if len(current_chunk) + len(sentence) <= max_chars:
                current_chunk += sentence
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = sentence

    if current_chunk:
        chunks.append(current_chunk)

    return chunks

def concat_wav_files(wav_files, output_path):
    """複数のWAVファイルを結合"""
    if not wav_files:
        return False

    if len(wav_files) == 1:
        os.rename(wav_files[0], output_path)
        return True

    # 最初のファイルからパラメータを取得
    with wave.open(wav_files[0], 'rb') as first:
        params = first.getparams()

    # 結合
    with wave.open(output_path, 'wb') as output:
        output.setparams(params)
        for wav_file in wav_files:
            with wave.open(wav_file, 'rb') as w:
                output.writeframes(w.readframes(w.getnframes()))

    return True

def generate_audio_for_text(text, output_path, temp_dir, slide_id=""):
    """テキストから音声を生成（必要に応じて分割）"""
    chunks = split_text(text)

    if len(chunks) == 0:
        return False

    if len(chunks) == 1 and len(chunks[0]) <= MAX_CHARS:
        # 分割不要、直接生成
        cmd = [
            VOICEPEAK_PATH,
            "-s", chunks[0],
            "-o", output_path,
            "-n", NARRATOR,
            "--speed", str(SPEED)
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            time.sleep(1)  # VOICEPEAK安定のため待機
            return os.path.exists(output_path)
        except Exception as e:
            print(f"    Error generating single chunk: {e}")
            return False

    # 複数チャンクの場合、個別に生成して結合
    # スライドごとにユニークな一時ディレクトリを使用
    slide_temp_dir = os.path.join(temp_dir, f"slide_{slide_id}")
    os.makedirs(slide_temp_dir, exist_ok=True)

    temp_files = []
    for i, chunk in enumerate(chunks):
        temp_path = os.path.join(slide_temp_dir, f"chunk_{i:03d}.wav")
        cmd = [
            VOICEPEAK_PATH,
            "-s", chunk,
            "-o", temp_path,
            "-n", NARRATOR,
            "--speed", str(SPEED)
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            time.sleep(1)  # VOICEPEAK安定のため待機
            if os.path.exists(temp_path):
                temp_files.append(temp_path)
                print(f"    Chunk {i+1}/{len(chunks)} OK")
            else:
                print(f"    Chunk {i+1}/{len(chunks)} failed: {chunk[:30]}...")
        except Exception as e:
            print(f"    Error in chunk {i+1}: {e}")
        time.sleep(0.5)

    if not temp_files:
        # クリーンアップ
        try:
            os.rmdir(slide_temp_dir)
        except:
            pass
        return False

    # 結合
    try:
        success = concat_wav_files(temp_files, output_path)
    except Exception as e:
        print(f"    Error concatenating: {e}")
        success = False

    # 一時ファイル削除
    for f in temp_files:
        try:
            os.remove(f)
        except:
            pass

    # 一時ディレクトリ削除
    try:
        os.rmdir(slide_temp_dir)
    except:
        pass

    return success

def generate_audio():
    # script.jsonを読み込み
    with open(SCRIPT_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)

    slides = data.get('slides', [])
    total = len(slides)
    print(f"Total slides: {total}")

    os.makedirs(AUDIO_DIR, exist_ok=True)

    # 一時ディレクトリ
    temp_dir = os.path.join(AUDIO_DIR, "temp_chunks")
    os.makedirs(temp_dir, exist_ok=True)

    for i, slide in enumerate(slides):
        slide_index = slide.get('index', i + 1)
        script = slide.get('script', '')

        if not script.strip():
            print(f"Slide {slide_index}: No script, skipping")
            continue

        output_file = os.path.join(AUDIO_DIR, f"slide_{slide_index:03d}.wav")

        # 既に存在する場合はスキップ
        if os.path.exists(output_file):
            print(f"Slide {slide_index}: Already exists, skipping")
            continue

        print(f"Generating audio for slide {slide_index}/{total} ({len(script)} chars)...")

        success = generate_audio_for_text(script, output_file, temp_dir, slide_id=str(slide_index))

        if success:
            size = os.path.getsize(output_file)
            print(f"  Done: {output_file} ({size} bytes)")
        else:
            print(f"  Failed to generate audio for slide {slide_index}")

        time.sleep(1)

    # 一時ディレクトリ削除
    try:
        os.rmdir(temp_dir)
    except:
        pass

    # 生成された音声ファイルの数を確認
    wav_files = [f for f in os.listdir(AUDIO_DIR) if f.endswith('.wav')]
    print(f"\nGenerated {len(wav_files)} audio files")

if __name__ == "__main__":
    generate_audio()
