#!/usr/bin/env python3
"""
原稿から音声を生成するスクリプト
gTTS (Google Translate TTS)を使用して音声を生成します
"""

import sys
import os
import json
import time
from pathlib import Path
from gtts import gTTS
from pydub import AudioSegment

def generate_audio_for_slide(script_text, output_file, max_retries=3, speed_factor=1.2):
    """
    1つの原稿から音声を生成（リトライ機能付き）

    Args:
        script_text: 原稿テキスト
        output_file: 出力ファイルパス
        max_retries: 最大リトライ回数
        speed_factor: 音声速度の倍率（1.2 = 1.2倍速）
    """
    # 空のテキストの場合は無音のオーディオを生成
    if not script_text or not script_text.strip():
        print(f"    警告: テキストが空のため、無音オーディオを生成します")
        # 1秒の無音オーディオを生成
        silence = AudioSegment.silent(duration=1000)
        silence.export(output_file, format="mp3")
        return

    for attempt in range(max_retries):
        try:
            # gTTSで日本語音声を生成（一時ファイル）
            temp_file = str(output_file).replace('.mp3', '_temp.mp3')
            tts = gTTS(text=script_text, lang='ja', slow=False)
            tts.save(temp_file)

            # pydubで音声を速度調整
            audio = AudioSegment.from_mp3(temp_file)
            # 速度を上げる（frame_rateを変更）
            faster_audio = audio._spawn(audio.raw_data, overrides={
                "frame_rate": int(audio.frame_rate * speed_factor)
            })
            # 元のサンプルレートに戻す
            faster_audio = faster_audio.set_frame_rate(audio.frame_rate)
            faster_audio.export(output_file, format="mp3")

            # 一時ファイルを削除
            os.remove(temp_file)

            return  # 成功したら終了
        except Exception as e:
            wait_time = (attempt + 1) * 5
            if attempt < max_retries - 1:
                print(f"    エラー発生（試行 {attempt + 1}/{max_retries}）: {str(e)[:100]}")
                print(f"    {wait_time}秒待機してリトライします...")
                time.sleep(wait_time)
            else:
                print(f"    最大リトライ回数に達しました。エラー: {e}")
                raise

def generate_all_audio(script_file, output_dir):
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
    for i, slide in enumerate(slides):
        output_file = output_dir / f"slide_{slide['index']:02d}.mp3"
        print(f"  スライド {slide['index']}: {slide['title']}")

        generate_audio_for_slide(slide['script'], str(output_file))

        audio_files.append({
            'index': slide['index'],
            'title': slide['title'],
            'audio_file': str(output_file),
            'script': slide['script']
        })

        print(f"    保存完了: {output_file}")

        # レート制限対策：各スライド間に2秒待機（最後のスライドを除く）
        if i < len(slides) - 1:
            print(f"    2秒待機中...")
            time.sleep(2)

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
    metadata_file = generate_all_audio(script_file, output_dir)

    print(f"\n音声生成完了！")

    # GitHub Actions用に環境変数に保存
    if 'GITHUB_ENV' in os.environ:
        with open(os.environ['GITHUB_ENV'], 'a') as f:
            f.write(f"AUDIO_METADATA={metadata_file}\n")
            f.write(f"AUDIO_DIR={output_dir}\n")

if __name__ == "__main__":
    main()
