#!/usr/bin/env python3
"""
音声ファイルから字幕とタイミング情報を生成するスクリプト
"""

import sys
import os
import json
from pathlib import Path
from pydub import AudioSegment

def get_audio_duration(audio_file):
    """
    音声ファイルの長さを秒単位で取得

    Args:
        audio_file: 音声ファイルのパス

    Returns:
        音声の長さ（秒）
    """
    audio = AudioSegment.from_file(audio_file)
    return len(audio) / 1000.0  # ミリ秒から秒に変換

def split_text_into_segments(text, max_chars_per_line=31, max_lines=2):
    """
    テキストを字幕用のセグメントに分割（最大2行、31文字/行まで）

    Args:
        text: 原稿テキスト
        max_chars_per_line: 1行あたりの最大文字数
        max_lines: 1セグメントあたりの最大行数

    Returns:
        分割されたテキストのリスト（改行を含む）
    """
    # 句読点で分割
    sentences = []
    current = ""

    for char in text:
        current += char
        if char in ['。', '！', '？', '\n']:
            if current.strip():
                sentences.append(current.strip())
            current = ""

    if current.strip():
        sentences.append(current.strip())

    # 各文をセグメント化
    segments = []
    for sentence in sentences:
        # 1行に収まる場合
        if len(sentence) <= max_chars_per_line:
            segments.append(sentence)
        # 2行に収まる可能性がある場合
        elif len(sentence) <= max_chars_per_line * max_lines:
            # 読点で分割して改行位置を探す
            parts = sentence.split('、')
            line1 = ""
            line2 = ""

            for i, part in enumerate(parts):
                test_line1 = line1 + part + ('、' if i < len(parts) - 1 else '')

                # 1行目に追加できる場合
                if len(test_line1) <= max_chars_per_line:
                    line1 = test_line1
                # 1行目が一杯なので2行目へ
                else:
                    # 残りを2行目に
                    remaining_parts = parts[i:]
                    line2 = '、'.join(remaining_parts)

                    # 2行目が長すぎる場合は調整
                    if len(line2) > max_chars_per_line:
                        # 2行目も読点で分割
                        line2_parts = line2.split('、')
                        line2 = ""
                        for j, part2 in enumerate(line2_parts):
                            test_line2 = line2 + part2 + ('、' if j < len(line2_parts) - 1 else '')
                            if len(test_line2) <= max_chars_per_line:
                                line2 = test_line2
                            else:
                                break
                    break

            # 改行して結合
            if line2:
                segments.append(line1.rstrip('、') + '\n' + line2.rstrip('、'))
            else:
                segments.append(line1.rstrip('、'))
        # 2行でも収まらない場合は強制分割
        else:
            parts = sentence.split('、')
            current_segment = ""
            current_length = 0

            for part in parts:
                test_segment = current_segment + part + '、'
                if len(test_segment) <= max_chars_per_line * max_lines:
                    current_segment = test_segment
                else:
                    if current_segment:
                        segments.append(current_segment.rstrip('、'))
                    current_segment = part + '、'

            if current_segment:
                segments.append(current_segment.rstrip('、'))

    return segments

def generate_timings(audio_metadata_file, output_file):
    """
    音声メタデータから字幕タイミング情報を生成

    Args:
        audio_metadata_file: 音声メタデータJSONファイル
        output_file: 出力ファイルパス
    """
    # メタデータを読み込む
    with open(audio_metadata_file, 'r', encoding='utf-8') as f:
        metadata = json.load(f)

    slides_data = []
    current_time = 0
    fps = 30  # Remotionのフレームレート

    print("字幕とタイミング情報を生成中...")

    for audio_info in metadata['audio_files']:
        audio_file = audio_info['audio_file']
        script = audio_info['script']

        print(f"\nスライド {audio_info['index']}: {audio_info['title']}")

        # 音声の長さを取得
        duration = get_audio_duration(audio_file)
        print(f"  音声長さ: {duration:.2f}秒")

        # 字幕セグメントを生成
        subtitle_segments = split_text_into_segments(script)
        print(f"  字幕セグメント数: {len(subtitle_segments)}")

        # 各セグメントのタイミングを計算（文字数ベース + ギャップ追加）
        subtitles = []
        GAP_DURATION = 0.5  # セグメント間のギャップ（秒）

        if subtitle_segments:
            # 各セグメントの文字数を計算
            segment_lengths = [len(segment) for segment in subtitle_segments]
            total_chars = sum(segment_lengths)

            # ギャップを考慮した利用可能時間を計算
            total_gap_time = GAP_DURATION * (len(subtitle_segments) - 1)  # 最後のセグメント後にはギャップなし
            available_duration = duration - total_gap_time

            segment_start_time = current_time

            for i, segment in enumerate(subtitle_segments):
                # 文字数の割合で時間を配分（ギャップを除いた時間で）
                char_ratio = segment_lengths[i] / total_chars if total_chars > 0 else 1.0 / len(subtitle_segments)
                segment_duration = available_duration * char_ratio

                start_time = segment_start_time
                end_time = start_time + segment_duration

                subtitles.append({
                    'text': segment,
                    'start': start_time,
                    'end': end_time,
                    'startFrame': int(start_time * fps),
                    'endFrame': int(end_time * fps)
                })

                # 最後以外のセグメントにはギャップを追加（待機アニメーション表示用）
                if i < len(subtitle_segments) - 1:
                    segment_start_time = end_time + GAP_DURATION
                else:
                    segment_start_time = end_time

            print(f"  セグメント間ギャップ: {GAP_DURATION}秒 × {len(subtitle_segments) - 1}回 = {total_gap_time:.2f}秒")

        slides_data.append({
            'index': audio_info['index'],
            'title': audio_info['title'],
            'audioFile': audio_file,
            'duration': duration,
            'durationFrames': int(duration * fps),
            'startTime': current_time,
            'endTime': current_time + duration,
            'startFrame': int(current_time * fps),
            'endFrame': int((current_time + duration) * fps),
            'subtitles': subtitles,
            'fullScript': script
        })

        current_time += duration

    # タイミング情報を保存
    output_data = {
        'fps': fps,
        'totalDuration': current_time,
        'totalFrames': int(current_time * fps),
        'slides': slides_data
    }

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    print(f"\n字幕・タイミング情報を保存: {output_file}")
    print(f"総再生時間: {current_time:.2f}秒 ({int(current_time * fps)}フレーム)")

    return output_file

def main():
    if len(sys.argv) < 2:
        print("使用方法: python generate_timings.py <audio_metadata_json>")
        sys.exit(1)

    audio_metadata_file = sys.argv[1]

    if not os.path.exists(audio_metadata_file):
        print(f"エラー: 音声メタデータファイルが見つかりません: {audio_metadata_file}")
        sys.exit(1)

    # 出力ファイル
    metadata_path = Path(audio_metadata_file)
    output_file = metadata_path.parent / 'video_timings.json'

    # タイミング情報を生成
    timings_file = generate_timings(audio_metadata_file, output_file)

    # GitHub Actions用に環境変数に保存
    if 'GITHUB_ENV' in os.environ:
        with open(os.environ['GITHUB_ENV'], 'a') as f:
            f.write(f"TIMINGS_FILE={timings_file}\n")

if __name__ == "__main__":
    main()
