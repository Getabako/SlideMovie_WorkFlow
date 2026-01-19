#!/usr/bin/env python3
"""
タイミング更新と動画レンダリングスクリプト
既存の音声ファイルからtimings.jsonを更新し、Remotionでレンダリング
"""

import json
import shutil
import subprocess
from pathlib import Path
from mutagen.mp3 import MP3

# 設定
PROJECT_ROOT = Path("/Users/takasaki19841121/Desktop/SlideMovie_WorkFlow-main")
PRESENTATION_DIR = PROJECT_ROOT / "presentations/⑦ホームページ作り"
VIDEO_OUTPUT_DIR = PRESENTATION_DIR / "video_output"
AUDIO_DIR = VIDEO_OUTPUT_DIR / "audio"
SCRIPT_FILE = VIDEO_OUTPUT_DIR / "script.json"
REMOTION_DIR = PROJECT_ROOT / "remotion-project"
FPS = 30

def get_audio_duration(audio_file: Path) -> float:
    """MP3ファイルの長さを取得（秒）"""
    try:
        audio = MP3(str(audio_file))
        return audio.info.length
    except Exception as e:
        print(f"  警告: {audio_file.name} の長さを取得できません: {e}")
        return 5.0  # デフォルト5秒

def prepare_slides():
    """スライド画像をRemotionにコピー"""
    print("=== スライド画像を準備 ===")

    # スライド画像を探す
    slide_patterns = [
        PRESENTATION_DIR / "images",
        PRESENTATION_DIR,
    ]

    source_slides = []
    for pattern_dir in slide_patterns:
        if pattern_dir.exists():
            # *.png, *.jpg を探す
            for ext in ['*.png', '*.PNG', '*.jpg', '*.JPG']:
                files = sorted(pattern_dir.glob(ext))
                if files:
                    source_slides = files
                    break
        if source_slides:
            break

    if not source_slides:
        # test_output.XXX.png を使用
        source_slides = sorted(PRESENTATION_DIR.glob("test_output.*.png"))

    if not source_slides:
        # ⑦ホームページ作り.XXX.png を使用
        source_slides = sorted(PRESENTATION_DIR.glob("⑦ホームページ作り.*.png"))

    if not source_slides:
        print("  エラー: スライド画像が見つかりません")
        return False

    print(f"  {len(source_slides)}枚のスライド画像を発見")

    # Remotionにコピー
    dest_dir = REMOTION_DIR / "public/slides"
    dest_dir.mkdir(parents=True, exist_ok=True)

    for i, src in enumerate(source_slides, 1):
        dest = dest_dir / f"slide_{i:02d}.png"
        shutil.copy2(src, dest)
        print(f"  コピー: {src.name} -> {dest.name}")

    return True

def update_timings():
    """timings.jsonを更新"""
    print("\n=== timings.json を更新 ===")

    # スクリプトを読み込む
    with open(SCRIPT_FILE, 'r', encoding='utf-8') as f:
        script_data = json.load(f)

    slides = script_data['slides']
    total_slides = len(slides)
    print(f"  スライド数: {total_slides}")

    # 音声ファイルから長さを取得してtimingsを作成
    timings = []
    current_frame = 0

    for slide in slides:
        index = slide['index']
        audio_file = AUDIO_DIR / f"slide_{index:03d}.mp3"

        if audio_file.exists():
            duration = get_audio_duration(audio_file)
        else:
            print(f"  警告: slide_{index:03d}.mp3 が見つかりません")
            duration = 5.0

        duration_frames = int(duration * FPS)

        timing = {
            "slideIndex": index,
            "startFrame": current_frame,
            "durationInFrames": duration_frames,
            "audioFile": f"audio/slide_{index:03d}.mp3",
            "script": slide.get('script', '')[:100] + "..." if len(slide.get('script', '')) > 100 else slide.get('script', '')
        }
        timings.append(timing)

        print(f"  スライド {index}: {duration:.1f}秒 ({duration_frames}フレーム)")
        current_frame += duration_frames

    # timings.jsonを保存
    timings_data = {
        "fps": FPS,
        "totalSlides": total_slides,
        "totalFrames": current_frame,
        "totalDuration": current_frame / FPS,
        "slides": timings
    }

    timings_file = REMOTION_DIR / "timings.json"
    with open(timings_file, 'w', encoding='utf-8') as f:
        json.dump(timings_data, f, indent=2, ensure_ascii=False)

    print(f"\n  合計: {current_frame}フレーム ({current_frame / FPS:.1f}秒 = {current_frame / FPS / 60:.1f}分)")
    print(f"  timings.json を保存: {timings_file}")

    return timings_data

def copy_audio_files():
    """音声ファイルをRemotionにコピー"""
    print("\n=== 音声ファイルをコピー ===")

    dest_dir = REMOTION_DIR / "public/audio"
    dest_dir.mkdir(parents=True, exist_ok=True)

    audio_files = sorted(AUDIO_DIR.glob("slide_*.mp3"))
    for src in audio_files:
        dest = dest_dir / src.name
        shutil.copy2(src, dest)

    print(f"  {len(audio_files)}個の音声ファイルをコピー")
    return True

def render_video(timings_data):
    """Remotionで動画をレンダリング"""
    print("\n=== Remotionで動画レンダリング ===")

    total_frames = timings_data['totalFrames']
    output_file = VIDEO_OUTPUT_DIR / "final_video.mp4"

    # チャンク分割でレンダリング（メモリ効率のため）
    chunk_size = 3000  # 約100秒分
    chunks = []

    for start in range(0, total_frames, chunk_size):
        end = min(start + chunk_size, total_frames)
        chunks.append((start, end))

    print(f"  {len(chunks)}チャンクでレンダリング")

    chunk_dir = VIDEO_OUTPUT_DIR / "chunks"
    chunk_dir.mkdir(exist_ok=True)

    chunk_files = []
    for i, (start, end) in enumerate(chunks, 1):
        chunk_file = chunk_dir / f"chunk_{i:03d}.mp4"
        print(f"\n  チャンク {i}/{len(chunks)}: フレーム {start}-{end}")

        cmd = [
            'npx', 'remotion', 'render',
            'Video',
            str(chunk_file),
            '--frames', f'{start}-{end-1}',
            '--props', json.dumps({"showCharacter": True}),
            '--concurrency', '2'
        ]

        result = subprocess.run(
            cmd,
            cwd=str(REMOTION_DIR),
            capture_output=True,
            text=True,
            timeout=1800  # 30分タイムアウト
        )

        if result.returncode != 0:
            print(f"  エラー: {result.stderr}")
            return False

        if chunk_file.exists():
            chunk_files.append(chunk_file)
            print(f"  ✓ チャンク {i} 完了")
        else:
            print(f"  ✗ チャンク {i} 失敗")
            return False

    # チャンクを結合
    print("\n  チャンクを結合中...")
    concat_file = chunk_dir / "concat_list.txt"
    with open(concat_file, 'w') as f:
        for cf in chunk_files:
            f.write(f"file '{cf.name}'\n")

    concat_cmd = [
        'ffmpeg', '-y', '-f', 'concat', '-safe', '0',
        '-i', str(concat_file),
        '-c', 'copy',
        str(output_file)
    ]

    subprocess.run(concat_cmd, capture_output=True, check=True)

    if output_file.exists():
        size_mb = output_file.stat().st_size / (1024 * 1024)
        print(f"\n✓ 動画生成完了: {output_file}")
        print(f"  ファイルサイズ: {size_mb:.1f}MB")
        return True
    else:
        print("  ✗ 動画生成失敗")
        return False

def main():
    print("=== 動画生成を開始 ===\n")

    # 1. スライド準備
    if not prepare_slides():
        return False

    # 2. 音声コピー
    copy_audio_files()

    # 3. timings更新
    timings_data = update_timings()

    # 4. レンダリング
    success = render_video(timings_data)

    if success:
        print("\n=== 全て完了 ===")
    else:
        print("\n=== 処理中にエラーが発生しました ===")

    return success

if __name__ == "__main__":
    main()
