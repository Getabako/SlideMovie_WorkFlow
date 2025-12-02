#!/usr/bin/env python3
"""
プレゼンテーション動画作成スクリプト

生成された画像付きスライドをMarpで画像化し、ffmpegで動画として結合します。
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path
from typing import List


class SlideVideoCreator:
    """スライド動画作成クラス"""

    def __init__(self, md_file: str, output_dir: str = None, duration: int = 5):
        """
        初期化

        Args:
            md_file: マークダウンファイルのパス
            output_dir: 出力ディレクトリ
            duration: 各スライドの表示時間（秒）
        """
        self.md_file = Path(md_file)
        self.duration = duration

        if output_dir:
            self.output_dir = Path(output_dir)
        else:
            self.output_dir = self.md_file.parent / "output"

        self.output_dir.mkdir(exist_ok=True)

        # スライド画像の出力先
        self.slides_dir = self.md_file.parent
        self.presentation_name = self.md_file.stem

    def generate_slide_images(self) -> List[Path]:
        """
        Marpを使用してスライドを個別画像として出力

        Returns:
            生成された画像ファイルのリスト
        """
        print(f"Generating slide images from: {self.md_file}")

        # Marp CLIでスライドを画像として出力
        output_pattern = str(self.slides_dir / f"{self.presentation_name}")

        cmd = [
            'npx', '@marp-team/marp-cli',
            str(self.md_file),
            '--images', 'png',
            '--allow-local-files',
            '-o', output_pattern + '.png'
        ]

        try:
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            print(result.stdout)

            # 生成された画像ファイルを取得
            slide_images = sorted(self.slides_dir.glob(f"{self.presentation_name}.*.png"))

            if not slide_images:
                print("Error: No slide images generated")
                return []

            print(f"✓ Generated {len(slide_images)} slide images")
            return slide_images

        except subprocess.CalledProcessError as e:
            print(f"Error running Marp: {e}")
            print(e.stderr)
            return []

    def create_video_from_images(self, image_files: List[Path]) -> Path:
        """
        ffmpegを使用して画像から動画を作成

        Args:
            image_files: 画像ファイルのリスト

        Returns:
            生成された動画ファイルのパス
        """
        print(f"\nCreating video from {len(image_files)} slides...")

        # 一時的なファイルリストを作成
        filelist_path = self.output_dir / "filelist.txt"
        video_output = self.output_dir / f"{self.presentation_name}.mp4"

        with open(filelist_path, 'w') as f:
            for img in image_files:
                # ffmpeg concat demuxerの形式
                f.write(f"file '{img.absolute()}'\n")
                f.write(f"duration {self.duration}\n")

            # 最後の画像も表示するため
            if image_files:
                f.write(f"file '{image_files[-1].absolute()}'\n")

        # ffmpegで動画作成
        cmd = [
            'ffmpeg',
            '-y',  # 上書き確認なし
            '-f', 'concat',
            '-safe', '0',
            '-i', str(filelist_path),
            '-vsync', 'vfr',
            '-pix_fmt', 'yuv420p',
            '-vf', 'scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2',
            str(video_output)
        ]

        try:
            subprocess.run(cmd, check=True, capture_output=True)
            print(f"✓ Video created: {video_output}")

            # 一時ファイル削除
            filelist_path.unlink()

            return video_output

        except subprocess.CalledProcessError as e:
            print(f"Error creating video: {e}")
            return None

    def create_video_with_transitions(self, image_files: List[Path]) -> Path:
        """
        トランジション効果付きで動画を作成

        Args:
            image_files: 画像ファイルのリスト

        Returns:
            生成された動画ファイルのパス
        """
        print(f"\nCreating video with transitions from {len(image_files)} slides...")

        video_output = self.output_dir / f"{self.presentation_name}_transitions.mp4"

        # 各スライドを個別の動画に変換
        temp_videos = []
        temp_dir = self.output_dir / "temp"
        temp_dir.mkdir(exist_ok=True)

        for i, img in enumerate(image_files):
            temp_video = temp_dir / f"slide_{i:03d}.mp4"

            cmd = [
                'ffmpeg',
                '-y',
                '-loop', '1',
                '-i', str(img),
                '-c:v', 'libx264',
                '-t', str(self.duration),
                '-pix_fmt', 'yuv420p',
                '-vf', 'scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2',
                str(temp_video)
            ]

            subprocess.run(cmd, check=True, capture_output=True)
            temp_videos.append(temp_video)

        # 動画を結合（フェードトランジション付き）
        filelist_path = temp_dir / "concat.txt"
        with open(filelist_path, 'w') as f:
            for video in temp_videos:
                f.write(f"file '{video.absolute()}'\n")

        cmd = [
            'ffmpeg',
            '-y',
            '-f', 'concat',
            '-safe', '0',
            '-i', str(filelist_path),
            '-c', 'copy',
            str(video_output)
        ]

        try:
            subprocess.run(cmd, check=True, capture_output=True)
            print(f"✓ Video with transitions created: {video_output}")

            # 一時ファイル削除
            import shutil
            shutil.rmtree(temp_dir)

            return video_output

        except subprocess.CalledProcessError as e:
            print(f"Error creating video: {e}")
            return None

    def process(self, with_transitions: bool = False):
        """
        スライドから動画を作成

        Args:
            with_transitions: トランジション効果を付けるか
        """
        # 1. スライド画像を生成
        slide_images = self.generate_slide_images()

        if not slide_images:
            print("Error: Failed to generate slide images")
            return

        # 2. 動画を作成
        if with_transitions:
            video_path = self.create_video_with_transitions(slide_images)
        else:
            video_path = self.create_video_from_images(slide_images)

        if video_path:
            print(f"\n✓ Successfully created video!")
            print(f"  Output: {video_path}")
            print(f"  Slides: {len(slide_images)}")
            print(f"  Duration per slide: {self.duration}s")
            print(f"  Total duration: {len(slide_images) * self.duration}s")


def main():
    parser = argparse.ArgumentParser(description='Create video from presentation slides')
    parser.add_argument('md_file', help='Path to markdown file')
    parser.add_argument('--output', '-o', help='Output directory', default=None)
    parser.add_argument('--duration', '-d', type=int, default=5,
                       help='Duration per slide in seconds (default: 5)')
    parser.add_argument('--transitions', '-t', action='store_true',
                       help='Add transitions between slides')

    args = parser.parse_args()

    creator = SlideVideoCreator(
        md_file=args.md_file,
        output_dir=args.output,
        duration=args.duration
    )

    creator.process(with_transitions=args.transitions)


if __name__ == '__main__':
    main()
