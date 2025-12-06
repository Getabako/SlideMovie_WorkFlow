#!/usr/bin/env python3
"""
キャラクター付き動画作成スクリプト

スライドから以下を自動生成して動画を作成:
1. 原稿生成（Gemini API）
2. 音声生成（Edge TTS）
3. 字幕・タイミング計算
4. Remotionで動画レンダリング

キャラクターは:
- 話している時: talk1.png〜talk6.png をループ
- 待機中: idle1.png〜idle6.png をループ
"""

import os
import sys
import json
import asyncio
import subprocess
import shutil
import re
from pathlib import Path
from typing import List, Dict, Optional
import argparse

# 音声の長さを取得するためのimport
try:
    from mutagen.mp3 import MP3
except ImportError:
    MP3 = None


class VideoWithCharacterCreator:
    """キャラクター付き動画作成クラス"""

    def __init__(
        self,
        md_file: str,
        output_dir: str = None,
        fps: int = 30,
        skip_script: bool = False,
        skip_audio: bool = False
    ):
        """
        初期化

        Args:
            md_file: マークダウンファイルのパス
            output_dir: 出力ディレクトリ
            fps: フレームレート
            skip_script: 原稿生成をスキップ
            skip_audio: 音声生成をスキップ
        """
        self.md_file = Path(md_file)
        self.fps = fps
        self.skip_script = skip_script
        self.skip_audio = skip_audio

        # ディレクトリ設定
        self.presentation_dir = self.md_file.parent
        self.presentation_name = self.md_file.stem

        if output_dir:
            self.output_dir = Path(output_dir)
        else:
            self.output_dir = self.presentation_dir / "video_output"

        self.output_dir.mkdir(parents=True, exist_ok=True)

        # プロジェクトルート
        self.project_root = Path(__file__).parent.parent
        self.remotion_dir = self.project_root / "remotion-project"
        self.scripts_dir = self.project_root / "scripts"

        # 中間ファイルパス
        self.script_json = self.output_dir / "script.json"
        self.audio_dir = self.output_dir / "audio"
        self.slides_dir = self.output_dir / "slides"
        self.timings_json = self.remotion_dir / "timings.json"
        self.slides_metadata = self.remotion_dir / "slides_metadata.json"

    def parse_slides(self) -> List[Dict]:
        """マークダウンからスライドを解析"""
        with open(self.md_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # スライドを分割
        slides_raw = re.split(r'(?:^|\n)---(?:\n|$)', content)

        slides = []
        for slide_raw in slides_raw:
            slide_raw = slide_raw.strip()
            if not slide_raw or slide_raw.startswith('marp:'):
                continue

            lines = slide_raw.split('\n')
            title = ''
            content_lines = []

            for line in lines:
                if line.startswith('# '):
                    title = line[2:].strip()
                elif line.strip():
                    if not (line.strip().startswith('<style>') or
                            line.strip().startswith('</style>') or
                            line.strip().startswith('![') or
                            line.strip().startswith('@import')):
                        content_lines.append(line)

            content_text = '\n'.join(content_lines).strip()
            if title or content_text:
                slides.append({
                    'index': len(slides) + 1,
                    'title': title,
                    'content': content_text
                })

        return slides

    def generate_script(self, slides: List[Dict]) -> Dict:
        """原稿を生成（Gemini API使用）"""
        print("\n=== ステップ1: 原稿生成 ===")

        if self.skip_script and self.script_json.exists():
            print(f"既存の原稿を使用: {self.script_json}")
            with open(self.script_json, 'r', encoding='utf-8') as f:
                return json.load(f)

        # APIキー確認
        api_key = os.environ.get('GOOGLE_AI_API_KEY')
        if not api_key:
            raise ValueError("GOOGLE_AI_API_KEY環境変数が設定されていません")

        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-2.0-flash-exp')
        except ImportError:
            raise ImportError("google-generativeai パッケージをインストールしてください")

        scripts = []
        for i, slide in enumerate(slides):
            print(f"  スライド {slide['index']}/{len(slides)}: {slide['title'][:30]}...")

            prompt = f"""
あなたはプレゼンテーションの原稿を作成する専門家です。
以下のスライドの原稿を自然な日本語で作成してください。

タイトル: {slide['title']}
内容:
{slide['content']}

要件:
1. 自然な話し言葉で書いてください
2. 30〜60秒程度で読める長さにしてください
3. 聞き手に語りかける口調にしてください
4. スライド番号の言及は避けてください

原稿のみを出力してください。
"""
            try:
                response = model.generate_content(prompt)
                script_text = response.text.strip()

                scripts.append({
                    'index': slide['index'],
                    'title': slide['title'],
                    'script': script_text
                })

                print(f"    完了: {len(script_text)}文字")

                # レート制限対策
                if i < len(slides) - 1:
                    import time
                    time.sleep(5)

            except Exception as e:
                print(f"    エラー: {e}")
                scripts.append({
                    'index': slide['index'],
                    'title': slide['title'],
                    'script': slide['title'] or "スライドの内容です。"
                })

        script_data = {
            'slides': scripts,
            'total_slides': len(slides)
        }

        with open(self.script_json, 'w', encoding='utf-8') as f:
            json.dump(script_data, f, ensure_ascii=False, indent=2)

        print(f"  原稿を保存: {self.script_json}")
        return script_data

    async def generate_audio(self, script_data: Dict) -> List[Dict]:
        """音声を生成（gTTS使用、Edge TTSはフォールバック）"""
        print("\n=== ステップ2: 音声生成 ===")

        self.audio_dir.mkdir(parents=True, exist_ok=True)

        if self.skip_audio:
            # 既存の音声ファイルをチェック
            existing_files = list(self.audio_dir.glob("slide_*.mp3"))
            if existing_files:
                print(f"既存の音声ファイルを使用: {len(existing_files)}件")
                return self._get_audio_metadata()

        # gTTSを優先的に使用
        try:
            from gtts import gTTS
            use_gtts = True
            print("  音声エンジン: gTTS")
        except ImportError:
            use_gtts = False
            try:
                import edge_tts
                print("  音声エンジン: Edge TTS")
            except ImportError:
                raise ImportError("gTTS または edge-tts パッケージをインストールしてください")

        audio_files = []

        for slide in script_data['slides']:
            idx = slide['index']
            text = slide['script']
            output_file = self.audio_dir / f"slide_{idx:03d}.mp3"

            print(f"  スライド {idx}: 音声生成中...")

            if text and text.strip():
                try:
                    if use_gtts:
                        # gTTSで音声生成
                        tts = gTTS(text, lang='ja')
                        tts.save(str(output_file))
                    else:
                        # Edge TTSで音声生成
                        import edge_tts
                        communicate = edge_tts.Communicate(text, "ja-JP-NanamiNeural")
                        await communicate.save(str(output_file))

                    # 音声の長さを取得
                    duration = self._get_audio_duration(output_file)

                    audio_files.append({
                        'index': idx,
                        'file': f"audio/slide_{idx:03d}.mp3",
                        'duration': duration,
                        'text': text
                    })

                    print(f"    完了: {duration:.2f}秒")

                except Exception as e:
                    print(f"    エラー: {e}")
            else:
                print(f"    スキップ（テキストなし）")

        return audio_files

    def _get_audio_duration(self, audio_file: Path) -> float:
        """音声ファイルの長さを取得"""
        if MP3:
            try:
                audio = MP3(str(audio_file))
                return audio.info.length
            except Exception:
                pass

        # ffprobeで取得
        try:
            result = subprocess.run(
                ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                 '-of', 'default=noprint_wrappers=1:nokey=1', str(audio_file)],
                capture_output=True, text=True
            )
            return float(result.stdout.strip())
        except Exception:
            return 5.0  # デフォルト

    def _get_audio_metadata(self) -> List[Dict]:
        """既存の音声ファイルからメタデータを取得"""
        audio_files = []
        for audio_file in sorted(self.audio_dir.glob("slide_*.mp3")):
            idx = int(audio_file.stem.split('_')[1])
            duration = self._get_audio_duration(audio_file)
            audio_files.append({
                'index': idx,
                'file': f"audio/{audio_file.name}",
                'duration': duration,
                'text': ''
            })
        return audio_files

    def generate_slide_images(self) -> int:
        """Marpでスライド画像を生成"""
        print("\n=== ステップ3: スライド画像生成 ===")

        self.slides_dir.mkdir(parents=True, exist_ok=True)

        # Marp CLIでスライドを画像化
        output_pattern = str(self.slides_dir / "slide")

        cmd = [
            'npx', '@marp-team/marp-cli',
            str(self.md_file),
            '--images', 'png',
            '--allow-local-files',
            '-o', output_pattern + '.png'
        ]

        try:
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)

            # 生成された画像ファイルを取得
            slide_images = sorted(self.slides_dir.glob("slide.*.png"))

            # ファイル名をリネーム (slide.001.png -> slide_01.png)
            for img in slide_images:
                match = re.search(r'slide\.(\d+)\.png', img.name)
                if match:
                    num = int(match.group(1))
                    new_name = self.slides_dir / f"slide_{num:02d}.png"
                    img.rename(new_name)

            slide_count = len(slide_images)
            print(f"  {slide_count}枚のスライド画像を生成")

            return slide_count

        except subprocess.CalledProcessError as e:
            print(f"エラー: Marpの実行に失敗しました")
            print(e.stderr)
            return 0

    def generate_timings(self, audio_files: List[Dict], script_data: Dict) -> Dict:
        """タイミングデータを生成"""
        print("\n=== ステップ4: タイミング計算 ===")

        slides = []
        current_time = 0.0
        current_frame = 0

        for audio in audio_files:
            idx = audio['index']
            duration = audio['duration']
            duration_frames = int(duration * self.fps)

            # 原稿テキストを取得
            script_text = ""
            for s in script_data['slides']:
                if s['index'] == idx:
                    script_text = s['script']
                    break

            # 字幕を生成（文単位で分割）
            subtitles = self._generate_subtitles(
                script_text, current_time, current_time + duration,
                current_frame, current_frame + duration_frames
            )

            slides.append({
                'index': idx,
                'title': next((s['title'] for s in script_data['slides'] if s['index'] == idx), ''),
                'audioFile': audio['file'],
                'duration': duration,
                'durationFrames': duration_frames,
                'startTime': current_time,
                'endTime': current_time + duration,
                'startFrame': current_frame,
                'endFrame': current_frame + duration_frames,
                'subtitles': subtitles,
                'fullScript': script_text
            })

            current_time += duration
            current_frame += duration_frames

        timings = {
            'fps': self.fps,
            'totalFrames': current_frame,
            'totalDuration': current_time,
            'slides': slides
        }

        print(f"  総時間: {current_time:.1f}秒 ({current_frame}フレーム)")

        return timings

    def _generate_subtitles(
        self, text: str, start_time: float, end_time: float,
        start_frame: int, end_frame: int
    ) -> List[Dict]:
        """テキストから字幕を生成"""
        if not text:
            return []

        # 文単位で分割
        sentences = re.split(r'[。！？\n]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]

        if not sentences:
            return []

        # 各文の長さに基づいて時間を配分
        total_chars = sum(len(s) for s in sentences)
        if total_chars == 0:
            return []

        duration = end_time - start_time
        frame_duration = end_frame - start_frame

        subtitles = []
        current_time = start_time
        current_frame = start_frame

        for sentence in sentences:
            # 文字数に応じた時間配分
            ratio = len(sentence) / total_chars
            sent_duration = duration * ratio
            sent_frames = int(frame_duration * ratio)

            subtitles.append({
                'text': sentence,
                'start': current_time,
                'end': current_time + sent_duration,
                'startFrame': current_frame,
                'endFrame': current_frame + sent_frames
            })

            current_time += sent_duration
            current_frame += sent_frames

        return subtitles

    def setup_remotion(self, timings: Dict, slide_count: int):
        """Remotion用にファイルを配置"""
        print("\n=== ステップ5: Remotion設定 ===")

        # timings.json を配置
        with open(self.timings_json, 'w', encoding='utf-8') as f:
            json.dump(timings, f, ensure_ascii=False, indent=2)
        print(f"  タイミングファイル: {self.timings_json}")

        # slides_metadata.json を配置
        slides_metadata = {'total_slides': slide_count}
        with open(self.slides_metadata, 'w', encoding='utf-8') as f:
            json.dump(slides_metadata, f, ensure_ascii=False, indent=2)
        print(f"  スライドメタデータ: {self.slides_metadata}")

        # 音声ファイルをRemotionのpublicにコピー
        remotion_audio_dir = self.remotion_dir / "public" / "audio"
        remotion_audio_dir.mkdir(parents=True, exist_ok=True)

        for audio_file in self.audio_dir.glob("*.mp3"):
            shutil.copy(audio_file, remotion_audio_dir / audio_file.name)
        print(f"  音声ファイルをコピー: {remotion_audio_dir}")

        # スライド画像をRemotionのpublicにコピー
        remotion_slides_dir = self.remotion_dir / "public" / "slides"
        remotion_slides_dir.mkdir(parents=True, exist_ok=True)

        for slide_file in self.slides_dir.glob("slide_*.png"):
            shutil.copy(slide_file, remotion_slides_dir / slide_file.name)
        print(f"  スライド画像をコピー: {remotion_slides_dir}")

    def render_video(self) -> Path:
        """Remotionで動画をレンダリング（チャンク分割方式）"""
        print("\n=== ステップ6: 動画レンダリング ===")

        output_video = self.output_dir / f"{self.presentation_name}.mp4"
        chunks_dir = self.output_dir / "chunks"
        chunks_dir.mkdir(parents=True, exist_ok=True)

        # timings.jsonを読み込んでスライド情報を取得
        with open(self.timings_json, 'r', encoding='utf-8') as f:
            timings = json.load(f)

        slides = timings['slides']
        total_slides = len(slides)

        # チャンクサイズ（1チャンクあたりのスライド数）
        chunk_size = 5
        chunk_videos = []
        total_chunks = (total_slides + chunk_size - 1) // chunk_size

        print(f"  総スライド数: {total_slides}")
        print(f"  チャンクサイズ: {chunk_size}スライド/チャンク")
        print(f"  総チャンク数: {total_chunks}")

        # スライドをチャンクに分割してレンダリング
        for chunk_idx in range(0, total_slides, chunk_size):
            chunk_end = min(chunk_idx + chunk_size, total_slides)
            chunk_slides = slides[chunk_idx:chunk_end]

            # このチャンクのフレーム範囲を計算
            start_frame = chunk_slides[0]['startFrame']
            end_frame = chunk_slides[-1]['endFrame']

            chunk_num = chunk_idx // chunk_size + 1
            chunk_video = chunks_dir / f"chunk_{chunk_num:03d}.mp4"

            # 既存のチャンクをスキップ
            if chunk_video.exists():
                print(f"  チャンク {chunk_num}/{total_chunks}: スキップ（既存）")
                chunk_videos.append(chunk_video)
                continue

            print(f"  チャンク {chunk_num}/{total_chunks}: "
                  f"スライド {chunk_idx+1}-{chunk_end} (フレーム {start_frame}-{end_frame})")

            # Remotionでこのチャンクをレンダリング（絶対パスを使用）
            cmd = [
                'npx', 'remotion', 'render',
                'Video',
                str(chunk_video.absolute()),
                '--codec', 'h264',
                '--frames', f'{start_frame}-{end_frame}',
                '--timeout', '180000',
                '--concurrency', '1',
                '--log', 'error',
            ]

            try:
                result = subprocess.run(
                    cmd,
                    cwd=str(self.remotion_dir),
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=600  # 10分タイムアウト
                )
                chunk_videos.append(chunk_video)
                print(f"    完了")

            except subprocess.TimeoutExpired:
                print(f"    タイムアウト - スキップ")
            except subprocess.CalledProcessError as e:
                print(f"    エラー: {e.stderr[:200] if e.stderr else 'Unknown error'}")
                # エラーでも続行を試みる

        if not chunk_videos:
            raise RuntimeError("チャンクのレンダリングに失敗しました")

        # ffmpegでチャンクを結合
        print(f"\n  チャンク結合中...")

        concat_list = chunks_dir / "concat_list.txt"
        with open(concat_list, 'w', encoding='utf-8') as f:
            for chunk_video in chunk_videos:
                f.write(f"file '{chunk_video.name}'\n")

        concat_cmd = [
            'ffmpeg', '-y',
            '-f', 'concat',
            '-safe', '0',
            '-i', str(concat_list),
            '-c', 'copy',
            str(output_video)
        ]

        try:
            result = subprocess.run(
                concat_cmd,
                cwd=str(chunks_dir),
                check=True,
                capture_output=True,
                text=True
            )
            print(f"  完了: {output_video}")

            # ファイルサイズを表示
            if output_video.exists():
                size_mb = output_video.stat().st_size / (1024 * 1024)
                print(f"  サイズ: {size_mb:.1f}MB")

            return output_video

        except subprocess.CalledProcessError as e:
            print(f"エラー: チャンク結合に失敗しました")
            print(e.stderr)
            raise

    def process(self):
        """全体のワークフローを実行"""
        print(f"\n{'='*50}")
        print(f"キャラクター付き動画作成")
        print(f"{'='*50}")
        print(f"入力: {self.md_file}")
        print(f"出力: {self.output_dir}")

        # 1. スライド解析
        slides = self.parse_slides()
        print(f"\nスライド数: {len(slides)}")

        # 2. 原稿生成
        script_data = self.generate_script(slides)

        # 3. 音声生成
        audio_files = asyncio.run(self.generate_audio(script_data))

        # 4. スライド画像生成
        slide_count = self.generate_slide_images()

        # 5. タイミング計算
        timings = self.generate_timings(audio_files, script_data)

        # 6. Remotion設定
        self.setup_remotion(timings, slide_count)

        # 7. 動画レンダリング
        output_video = self.render_video()

        print(f"\n{'='*50}")
        print(f"完了！")
        print(f"{'='*50}")
        print(f"出力動画: {output_video}")

        return output_video


def main():
    parser = argparse.ArgumentParser(
        description='キャラクター付きプレゼン動画を作成'
    )
    parser.add_argument('md_file', help='マークダウンファイルのパス')
    parser.add_argument(
        '--output-dir', '-o',
        help='出力ディレクトリ'
    )
    parser.add_argument(
        '--fps',
        type=int,
        default=30,
        help='フレームレート (デフォルト: 30)'
    )
    parser.add_argument(
        '--skip-script',
        action='store_true',
        help='原稿生成をスキップ（既存のscript.jsonを使用）'
    )
    parser.add_argument(
        '--skip-audio',
        action='store_true',
        help='音声生成をスキップ（既存の音声ファイルを使用）'
    )

    args = parser.parse_args()

    if not os.path.exists(args.md_file):
        print(f"エラー: ファイルが見つかりません: {args.md_file}")
        sys.exit(1)

    creator = VideoWithCharacterCreator(
        md_file=args.md_file,
        output_dir=args.output_dir,
        fps=args.fps,
        skip_script=args.skip_script,
        skip_audio=args.skip_audio
    )

    creator.process()


if __name__ == '__main__':
    main()
