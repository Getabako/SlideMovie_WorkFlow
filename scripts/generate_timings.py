#!/usr/bin/env python3
"""
音声ファイルから字幕とタイミング情報を生成するスクリプト
"""

import sys
import os
import json
import re
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

def find_line_break_position(text, max_chars):
    """
    意味の区切りを考慮して最適な改行位置を見つける

    Args:
        text: 分割するテキスト
        max_chars: 1行の最大文字数

    Returns:
        改行位置（文字インデックス）、見つからない場合はNone
    """
    if len(text) <= max_chars:
        return None

    # 改行候補位置を探す（優先順位順）
    break_candidates = []

    # 1. 読点（、）の後
    for match in re.finditer(r'、', text[:max_chars + 5]):
        pos = match.end()
        if pos <= max_chars:
            break_candidates.append((pos, 3))

    # 2. 助詞の後（ただし形式名詞の前は除く）
    particles = ['は', 'が', 'を', 'に', 'で', 'と', 'へ', 'や', 'の', 'から', 'まで', 'より', 'も', 'し', 'ば', 'て']
    formal_nouns = ['こと', 'もの', 'ため', 'よう', 'ところ', 'はず', 'わけ']

    for particle in particles:
        for match in re.finditer(re.escape(particle), text[:max_chars + 5]):
            pos = match.end()
            if pos > max_chars:
                continue

            # 形式名詞の前でないかチェック
            next_text = text[pos:pos + 3]
            is_before_formal_noun = any(next_text.startswith(fn) for fn in formal_nouns)

            if not is_before_formal_noun:
                break_candidates.append((pos, 2))

    # 優先度順にソート（優先度が高い順、同じ優先度なら理想的な位置に近い順）
    if break_candidates:
        ideal_pos = max_chars * 0.6  # 理想は60%くらいの位置
        break_candidates.sort(key=lambda x: (-x[1], abs(x[0] - ideal_pos)))
        return break_candidates[0][0]

    # 見つからない場合はNone
    return None

def split_into_two_lines(text, max_chars_per_line):
    """
    テキストを2行に分割（意味の区切りを考慮）

    Args:
        text: 分割するテキスト
        max_chars_per_line: 1行の最大文字数

    Returns:
        改行を含むテキスト、または元のテキスト（分割不可の場合）
    """
    if len(text) <= max_chars_per_line:
        return text

    if len(text) > max_chars_per_line * 2:
        # 2行でも収まらない場合はNone（別処理が必要）
        return None

    # 最適な改行位置を探す
    break_pos = find_line_break_position(text, max_chars_per_line)

    if break_pos:
        line1 = text[:break_pos].strip()
        line2 = text[break_pos:].strip()

        # 2行目も31文字以内に収まるか確認
        if len(line2) <= max_chars_per_line:
            return line1 + '\n' + line2

    # 見つからない場合は強制的に分割（できるだけ良い位置で）
    for i in range(max_chars_per_line, max(max_chars_per_line // 2, len(text) - max_chars_per_line), -1):
        if i < len(text) and text[i] in ['、', '。', ' ', '　']:
            line1 = text[:i + 1].strip('、。 　')
            line2 = text[i + 1:].strip('、。 　')
            if len(line2) <= max_chars_per_line:
                return line1 + '\n' + line2

    # 最後の手段：max_chars_per_lineで強制分割
    return text[:max_chars_per_line] + '\n' + text[max_chars_per_line:]

def split_text_into_segments(text, max_chars_per_line=31, max_lines=2):
    """
    テキストを字幕用のセグメントに分割（最大2行、31文字/行まで）
    意味の区切り（助詞、読点など）を考慮して改行位置を決定

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
            # 新しい改行ロジックを使用
            result = split_into_two_lines(sentence, max_chars_per_line)
            if result:
                segments.append(result)
            else:
                # 2行でも収まらない場合は強制分割
                segments.append(sentence[:max_chars_per_line] + '\n' + sentence[max_chars_per_line:max_chars_per_line * 2])
        # 2行でも収まらない場合は複数セグメントに分割
        else:
            # 読点で分割
            parts = sentence.split('、')
            current_segment = ""

            for i, part in enumerate(parts):
                part_with_comma = part + ('、' if i < len(parts) - 1 else '')

                # 現在のセグメントに追加できるか確認
                test_segment = current_segment + part_with_comma

                if len(test_segment) <= max_chars_per_line * max_lines:
                    current_segment = test_segment
                else:
                    # 現在のセグメントを保存
                    if current_segment:
                        # 2行に分割できるか試す
                        result = split_into_two_lines(current_segment.rstrip('、'), max_chars_per_line)
                        if result:
                            segments.append(result)
                        else:
                            segments.append(current_segment.rstrip('、'))
                    current_segment = part_with_comma

            # 残りを保存
            if current_segment:
                result = split_into_two_lines(current_segment.rstrip('、'), max_chars_per_line)
                if result:
                    segments.append(result)
                else:
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
        GAP_DURATION = 0.3  # セグメント間のギャップ（秒）- 短くして音声とのズレを減らす

        if subtitle_segments:
            # 各セグメントの文字数を計算（改行を除く）
            segment_lengths = [len(segment.replace('\n', '')) for segment in subtitle_segments]
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

                # デバッグ出力
                print(f"    セグメント {i + 1}: \"{segment.replace(chr(10), ' / ')}\" ({segment_lengths[i]}文字) = {start_time:.2f}s - {end_time:.2f}s ({segment_duration:.2f}s)")

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
