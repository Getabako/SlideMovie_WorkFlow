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

    # VOICEPEAKのパス（macOS）
    VOICEPEAK_PATH = "/Applications/voicepeak.app/Contents/MacOS/voicepeak"

    # 利用可能なナレーター（VOICEPEAK 6ナレーターセット）
    VOICEPEAK_NARRATORS = [
        "Japanese Female 1",
        "Japanese Female 2",
        "Japanese Female 3",
        "Japanese Male 1",
        "Japanese Male 2",
        "Japanese Male 3",
    ]

    def __init__(
        self,
        md_file: str,
        output_dir: str = None,
        fps: int = 30,
        skip_script: bool = False,
        skip_audio: bool = False,
        voice_engine: str = "voicepeak",
        narrator: str = "Japanese Female 1",
        speed: int = 120,
        pitch: int = 0
    ):
        """
        初期化

        Args:
            md_file: マークダウンファイルのパス
            output_dir: 出力ディレクトリ
            fps: フレームレート
            skip_script: 原稿生成をスキップ
            skip_audio: 音声生成をスキップ
            voice_engine: 音声エンジン（voicepeak, gtts, edge_tts）
            narrator: VOICEPEAKのナレーター名
            speed: 話速（50-200、デフォルト120でハキハキ）
            pitch: 声の高さ（-300〜300）
        """
        self.md_file = Path(md_file)
        self.fps = fps
        self.skip_script = skip_script
        self.skip_audio = skip_audio
        self.voice_engine = voice_engine
        self.narrator = narrator
        self.speed = speed
        self.pitch = pitch

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

    def _split_text_for_voicepeak(self, text: str, max_chars: int = 130) -> List[str]:
        """テキストを140文字以下のチャンクに分割（句読点で区切る）"""
        # 改行をスペースに、全角スペースを半角に
        clean_text = text.replace('\n', ' ').replace('　', ' ')
        clean_text = ' '.join(clean_text.split())

        if len(clean_text) <= max_chars:
            return [clean_text]

        chunks = []
        current_chunk = ""

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
                    for part in sub_parts:
                        if len(sub_chunk) + len(part) + 1 <= max_chars:
                            sub_chunk += part + '、' if part != sub_parts[-1] else part
                        else:
                            if sub_chunk:
                                chunks.append(sub_chunk)
                            sub_chunk = part + '、' if part != sub_parts[-1] else part
                    if sub_chunk:
                        current_chunk = sub_chunk
                else:
                    current_chunk = sentence

        if current_chunk:
            chunks.append(current_chunk)

        return chunks

    def _generate_audio_voicepeak(self, text: str, output_file: Path) -> bool:
        """VOICEPEAKで音声を生成（140文字制限対応）"""
        # テキストを分割
        chunks = self._split_text_for_voicepeak(text)

        if len(chunks) == 1:
            # 1チャンクの場合は直接生成
            return self._generate_single_voicepeak(chunks[0], output_file)
        else:
            # 複数チャンクの場合は個別に生成して結合
            print(f"        ({len(chunks)}チャンクに分割)")
            temp_files = []
            temp_dir = output_file.parent / "temp_chunks"
            temp_dir.mkdir(exist_ok=True)

            try:
                for i, chunk in enumerate(chunks):
                    temp_file = temp_dir / f"chunk_{i:03d}.mp3"
                    if not self._generate_single_voicepeak(chunk, temp_file):
                        return False
                    temp_files.append(temp_file)

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

                return output_file.exists()

            finally:
                # 一時ファイルをクリーンアップ
                for tf in temp_files:
                    if tf.exists():
                        tf.unlink()
                if temp_dir.exists():
                    for f in temp_dir.glob("*"):
                        f.unlink()
                    temp_dir.rmdir()

    def _generate_single_voicepeak(self, text: str, output_file: Path) -> bool:
        """VOICEPEAKで単一のテキストから音声を生成"""
        wav_file = output_file.with_suffix('.wav')

        cmd = [
            self.VOICEPEAK_PATH,
            '-s', text,
            '-o', str(wav_file),
            '-n', self.narrator,
            '--speed', str(self.speed),
            '--pitch', str(self.pitch)
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )

            if not wav_file.exists():
                print(f"      VOICEPEAKエラー: 音声ファイルが生成されませんでした")
                if result.stderr:
                    print(f"      {result.stderr[:200]}")
                return False

            # wavをmp3に変換
            convert_cmd = [
                'ffmpeg', '-y', '-i', str(wav_file),
                '-codec:a', 'libmp3lame', '-qscale:a', '2',
                str(output_file)
            ]
            subprocess.run(convert_cmd, capture_output=True, check=True)

            # 一時wavファイルを削除
            wav_file.unlink()

            return True

        except subprocess.TimeoutExpired:
            print(f"      VOICEPEAKタイムアウト")
            return False
        except Exception as e:
            print(f"      VOICEPEAKエラー: {e}")
            return False

    async def generate_audio(self, script_data: Dict) -> List[Dict]:
        """音声を生成（VOICEPEAK優先、フォールバックでgTTS/Edge TTS）"""
        print("\n=== ステップ2: 音声生成 ===")

        self.audio_dir.mkdir(parents=True, exist_ok=True)

        if self.skip_audio:
            # 既存の音声ファイルをチェック
            existing_files = list(self.audio_dir.glob("slide_*.mp3"))
            if existing_files:
                print(f"既存の音声ファイルを使用: {len(existing_files)}件")
                return self._get_audio_metadata()

        # 音声エンジンの選択
        use_voicepeak = False
        use_gtts = False

        if self.voice_engine == "voicepeak":
            # VOICEPEAKの存在確認
            if os.path.exists(self.VOICEPEAK_PATH):
                use_voicepeak = True
                print(f"  音声エンジン: VOICEPEAK")
                print(f"  ナレーター: {self.narrator}")
                print(f"  話速: {self.speed} / 声の高さ: {self.pitch}")
            else:
                print(f"  警告: VOICEPEAKが見つかりません。フォールバックを使用します。")
                self.voice_engine = "gtts"

        if self.voice_engine == "gtts":
            try:
                from gtts import gTTS
                use_gtts = True
                print("  音声エンジン: gTTS")
            except ImportError:
                self.voice_engine = "edge_tts"

        if self.voice_engine == "edge_tts":
            try:
                import edge_tts
                print("  音声エンジン: Edge TTS")
            except ImportError:
                raise ImportError("音声エンジンが利用できません。VOICEPEAKをインストールするか、gTTS/edge-ttsをpipでインストールしてください")

        audio_files = []

        for slide in script_data['slides']:
            idx = slide['index']
            text = slide['script']
            output_file = self.audio_dir / f"slide_{idx:03d}.mp3"

            print(f"  スライド {idx}: 音声生成中...")

            if text and text.strip():
                success = False

                try:
                    if use_voicepeak:
                        # VOICEPEAKで音声生成
                        success = self._generate_audio_voicepeak(text, output_file)
                    elif use_gtts:
                        # gTTSで音声生成
                        from gtts import gTTS
                        tts = gTTS(text, lang='ja')
                        tts.save(str(output_file))
                        success = True
                    else:
                        # Edge TTSで音声生成
                        import edge_tts
                        communicate = edge_tts.Communicate(text, "ja-JP-NanamiNeural")
                        await communicate.save(str(output_file))
                        success = True

                    if success and output_file.exists():
                        # 音声の長さを取得
                        duration = self._get_audio_duration(output_file)

                        audio_files.append({
                            'index': idx,
                            'file': f"audio/slide_{idx:03d}.mp3",
                            'duration': duration,
                            'text': text
                        })

                        print(f"    完了: {duration:.2f}秒")
                    else:
                        print(f"    失敗: 音声ファイルが生成されませんでした")

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
        """テキストから字幕を生成（音声と字幕を同期させるため文字数に比例して配分）"""
        if not text:
            return []

        # 文単位で分割（句読点で区切る）
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

        for i, sentence in enumerate(sentences):
            # 文字数に比例した時間配分（音声と字幕を同期させるため）
            ratio = len(sentence) / total_chars
            sent_duration = duration * ratio
            sent_frames = round(frame_duration * ratio)

            # 最後の文は確実に終了時間まで
            if i == len(sentences) - 1:
                sent_end_time = end_time
                sent_end_frame = end_frame
            else:
                sent_end_time = current_time + sent_duration
                sent_end_frame = current_frame + sent_frames

            # 字幕テキストが長すぎる場合は切り詰め
            display_text = sentence if len(sentence) <= 50 else sentence[:50] + '...'

            subtitles.append({
                'text': display_text,
                'start': current_time,
                'end': sent_end_time,
                'startFrame': current_frame,
                'endFrame': sent_end_frame
            })

            current_time = sent_end_time
            current_frame = sent_end_frame

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
                    timeout=1800  # 30分タイムアウト
                )
                chunk_videos.append(chunk_video)
                print(f"    完了")

            except subprocess.TimeoutExpired:
                print(f"    タイムアウト - スキップ")
            except subprocess.CalledProcessError as e:
                print(f"    エラー: {e.stderr[:200] if e.stderr else 'Unknown error'}")
                # エラーでもファイルが生成されていたらリストに追加
                if chunk_video.exists():
                    chunk_videos.append(chunk_video)
                    print(f"    ファイルは生成されました")

        if not chunk_videos:
            # 既存のチャンクファイルを探す
            existing_chunks = sorted(chunks_dir.glob("chunk_*.mp4"))
            if existing_chunks:
                print(f"  既存のチャンクファイルを使用: {len(existing_chunks)}件")
                chunk_videos = existing_chunks
            else:
                raise RuntimeError("チャンクのレンダリングに失敗しました")

        # ffmpegでチャンクを結合
        print(f"\n  チャンク結合中... ({len(chunk_videos)}ファイル)")

        concat_list = chunks_dir / "concat_list.txt"
        with open(concat_list, 'w', encoding='utf-8') as f:
            for chunk_video in sorted(chunk_videos):  # ソートして順番を保証
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
                text=True,
                timeout=300  # 5分タイムアウト
            )
            print(f"  結合完了: {output_video}")

            # ファイルサイズを表示
            if output_video.exists():
                size_mb = output_video.stat().st_size / (1024 * 1024)
                print(f"  サイズ: {size_mb:.1f}MB")

                # 動画の長さを取得
                try:
                    probe_result = subprocess.run(
                        ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                         '-of', 'default=noprint_wrappers=1:nokey=1', str(output_video)],
                        capture_output=True, text=True
                    )
                    duration = float(probe_result.stdout.strip())
                    minutes = int(duration // 60)
                    seconds = int(duration % 60)
                    print(f"  長さ: {minutes}分{seconds}秒")
                except Exception:
                    pass

            return output_video

        except subprocess.TimeoutExpired:
            print(f"エラー: チャンク結合がタイムアウトしました")
            raise RuntimeError("チャンク結合タイムアウト")
        except subprocess.CalledProcessError as e:
            print(f"エラー: チャンク結合に失敗しました")
            if e.stderr:
                print(e.stderr[:500])
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
    parser.add_argument(
        '--voice-engine',
        choices=['voicepeak', 'gtts', 'edge_tts'],
        default='voicepeak',
        help='音声エンジン (デフォルト: voicepeak)'
    )
    parser.add_argument(
        '--narrator',
        default='Japanese Female 1',
        help='VOICEPEAKナレーター名 (デフォルト: Japanese Female 1)'
    )
    parser.add_argument(
        '--speed',
        type=int,
        default=120,
        help='話速 50-200 (デフォルト: 120、ハキハキ話す)'
    )
    parser.add_argument(
        '--pitch',
        type=int,
        default=0,
        help='声の高さ -300〜300 (デフォルト: 0)'
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
        skip_audio=args.skip_audio,
        voice_engine=args.voice_engine,
        narrator=args.narrator,
        speed=args.speed,
        pitch=args.pitch
    )

    creator.process()


if __name__ == '__main__':
    main()
