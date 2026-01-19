#!/usr/bin/env python3
"""VOICEPEAKで音声を生成するスクリプト"""
import json
import subprocess
import os
import time

BASE_DIR = "/Users/takasaki19841121/Desktop/SlideMovie_WorkFlow-main"
SCRIPT_PATH = f"{BASE_DIR}/presentations/⑦ホームページ作り/video_output/script.json"
AUDIO_DIR = f"{BASE_DIR}/presentations/⑦ホームページ作り/video_output/audio"
VOICEPEAK_PATH = "/Applications/voicepeak.app/Contents/MacOS/voicepeak"
NARRATOR = "Japanese Female 1"
SPEED = 150

def generate_audio():
    # script.jsonを読み込み
    with open(SCRIPT_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)

    slides = data.get('slides', [])
    total = len(slides)
    print(f"Total slides: {total}")

    os.makedirs(AUDIO_DIR, exist_ok=True)

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

        print(f"Generating audio for slide {slide_index}/{total}...")

        # VOICEPEAKを実行
        cmd = [
            VOICEPEAK_PATH,
            "-s", script,
            "-o", output_file,
            "-n", NARRATOR,
            "--speed", str(SPEED)
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if result.returncode == 0:
                # 生成されたか確認
                if os.path.exists(output_file):
                    size = os.path.getsize(output_file)
                    print(f"  Done: {output_file} ({size} bytes)")
                else:
                    print(f"  Warning: File not created")
            else:
                print(f"  Error: {result.stderr}")
        except subprocess.TimeoutExpired:
            print(f"  Timeout generating audio for slide {slide_index}")
        except Exception as e:
            print(f"  Error: {e}")

        # VOICEPEAKが安定するよう少し待つ
        time.sleep(1)

    # 生成された音声ファイルの数を確認
    wav_files = [f for f in os.listdir(AUDIO_DIR) if f.endswith('.wav')]
    print(f"\nGenerated {len(wav_files)} audio files")

if __name__ == "__main__":
    generate_audio()
