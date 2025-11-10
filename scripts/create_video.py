#!/usr/bin/env python3
"""
スライドからゆっくり動画風の動画を作成するメインスクリプト
全体のワークフローを統合します
"""

import sys
import os
import json
import shutil
import subprocess
from pathlib import Path

def run_command(cmd, cwd=None, description=""):
    """コマンドを実行して結果を表示"""
    if description:
        print(f"\n{'='*60}")
        print(f"{description}")
        print(f"{'='*60}")

    print(f"実行: {' '.join(cmd) if isinstance(cmd, list) else cmd}")

    result = subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
        shell=isinstance(cmd, str)
    )

    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)

    if result.returncode != 0:
        raise RuntimeError(f"コマンド実行エラー: {' '.join(cmd) if isinstance(cmd, list) else cmd}")

    return result

def main():
    if len(sys.argv) < 2:
        print("使用方法: python create_video.py <input_yaml_file>")
        sys.exit(1)

    input_file = sys.argv[1]

    if not os.path.exists(input_file):
        print(f"エラー: 入力ファイルが見つかりません: {input_file}")
        sys.exit(1)

    # プロジェクトルートディレクトリ
    root_dir = Path(__file__).parent.parent
    scripts_dir = root_dir / "scripts"
    remotion_dir = root_dir / "remotion-project"

    print(f"\n{'#'*60}")
    print(f"# ゆっくり動画生成ワークフロー開始")
    print(f"# 入力ファイル: {input_file}")
    print(f"{'#'*60}\n")

    # ステップ1: スライド作成
    run_command(
        ["python3", str(scripts_dir / "create_slide.py"), input_file],
        description="ステップ 1/6: スライド作成"
    )

    # スライドファイルを取得
    with open(input_file, 'r', encoding='utf-8') as f:
        import yaml
        data = yaml.safe_load(f)
        topic = data.get('topic', 'presentation')
        safe_topic = topic.replace(' ', '_').replace('/', '_').replace('\\', '_')

    slide_file = root_dir / "slides" / f"{safe_topic}_slide.md"

    if not slide_file.exists():
        raise RuntimeError(f"スライドファイルが見つかりません: {slide_file}")

    # ステップ2: 原稿生成
    run_command(
        ["python3", str(scripts_dir / "generate_script.py"), str(slide_file)],
        description="ステップ 2/6: 原稿生成"
    )

    script_file = root_dir / "scripts_output" / f"{safe_topic}_slide_script.json"

    if not script_file.exists():
        raise RuntimeError(f"原稿ファイルが見つかりません: {script_file}")

    # ステップ3: 音声生成
    run_command(
        ["python3", str(scripts_dir / "generate_audio.py"), str(script_file)],
        description="ステップ 3/6: 音声生成"
    )

    audio_metadata = root_dir / "audio_output" / "audio_metadata.json"

    if not audio_metadata.exists():
        raise RuntimeError(f"音声メタデータが見つかりません: {audio_metadata}")

    # ステップ4: タイミング情報生成
    run_command(
        ["python3", str(scripts_dir / "generate_timings.py"), str(audio_metadata)],
        description="ステップ 4/6: タイミング情報生成"
    )

    timings_file = root_dir / "audio_output" / "video_timings.json"

    if not timings_file.exists():
        raise RuntimeError(f"タイミングファイルが見つかりません: {timings_file}")

    # ステップ5: Remotionプロジェクトにファイルをコピー
    print(f"\n{'='*60}")
    print("ステップ 5/6: Remotionプロジェクトへのファイル配置")
    print(f"{'='*60}")

    # タイミングJSONをコピー
    shutil.copy(timings_file, remotion_dir / "timings.json")
    print(f"コピー: {timings_file} -> {remotion_dir / 'timings.json'}")

    # 音声ファイルをpublicディレクトリにコピー
    with open(audio_metadata, 'r', encoding='utf-8') as f:
        audio_data = json.load(f)

    audio_public_dir = remotion_dir / "public" / "audio"
    audio_public_dir.mkdir(exist_ok=True)

    # タイミングデータを読み込んで、音声ファイルのパスを更新
    with open(timings_file, 'r', encoding='utf-8') as f:
        timings_data = json.load(f)

    for slide in timings_data['slides']:
        audio_src = Path(slide['audioFile'])
        audio_dst = audio_public_dir / audio_src.name
        shutil.copy(audio_src, audio_dst)
        print(f"コピー: {audio_src} -> {audio_dst}")

        # パスを相対パスに更新
        slide['audioFile'] = f"audio/{audio_src.name}"

    # 更新したタイミングデータを保存
    with open(remotion_dir / "timings.json", 'w', encoding='utf-8') as f:
        json.dump(timings_data, f, ensure_ascii=False, indent=2)

    print("ファイル配置完了")

    # ステップ6: Remotionで動画をレンダリング
    run_command(
        ["npm", "install"],
        cwd=remotion_dir,
        description="ステップ 6/6: Remotionで動画をレンダリング（依存関係のインストール）"
    )

    # 出力ディレクトリを作成
    output_dir = remotion_dir / "out"
    output_dir.mkdir(exist_ok=True)

    run_command(
        ["npm", "run", "build"],
        cwd=remotion_dir,
        description="動画のレンダリング"
    )

    output_video = output_dir / "video.mp4"

    if not output_video.exists():
        raise RuntimeError(f"動画ファイルが生成されませんでした: {output_video}")

    print(f"\n{'#'*60}")
    print(f"# 動画生成完了！")
    print(f"# 出力ファイル: {output_video}")
    print(f"{'#'*60}\n")

    return str(output_video)

if __name__ == "__main__":
    try:
        video_file = main()
        print(f"\n成功: 動画が生成されました: {video_file}")
    except Exception as e:
        print(f"\nエラー: {e}", file=sys.stderr)
        sys.exit(1)
