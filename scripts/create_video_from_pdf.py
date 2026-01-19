#!/usr/bin/env python3
"""
PDF解説動画作成スクリプト

複数のPDFファイルを番号順に読み取り、内容を解析して
キャラクターが解説する動画を生成します。

機能:
1. PDFファイルを番号順に結合（ファイル名の数字でソート）
2. 各ページの内容を読み取り（テキスト+画像OCR）
3. 解説用の原稿を自動生成
4. キャラクター付き動画を作成
"""

import os
import sys
import json
import re
import asyncio
import subprocess
import shutil
import tempfile
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import argparse
import base64

# PDF処理用
try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

# 音声の長さを取得するためのimport
try:
    from mutagen.mp3 import MP3
except ImportError:
    MP3 = None


def extract_number_from_filename(filename: str) -> int:
    """ファイル名から数字を抽出してソート用のキーを返す"""
    # ファイル名の先頭の数字を抽出 (例: "01_xxx.pdf" -> 1, "2.xxx.pdf" -> 2)
    match = re.match(r'^(\d+)', Path(filename).stem)
    if match:
        return int(match.group(1))
    # 先頭に数字がない場合はファイル名全体で比較
    return float('inf')


class PDFVideoCreator:
    """PDF解説動画作成クラス"""

    # VOICEPEAKのパス（macOS）
    VOICEPEAK_PATH = "/Applications/voicepeak.app/Contents/MacOS/voicepeak"

    def __init__(
        self,
        pdf_dir: str,
        output_dir: str = None,
        fps: int = 30,
        voice_engine: str = "voicepeak",
        narrator: str = "Japanese Female 1",
        speed: int = 120,
        pitch: int = 0,
        skip_script: bool = False,
        skip_audio: bool = False
    ):
        """
        初期化

        Args:
            pdf_dir: PDFファイルが含まれるディレクトリ
            output_dir: 出力ディレクトリ
            fps: フレームレート
            voice_engine: 音声エンジン（voicepeak, gtts, edge_tts）
            narrator: VOICEPEAKのナレーター名
            speed: 話速（50-200）
            pitch: 声の高さ（-300〜300）
            skip_script: 原稿生成をスキップ
            skip_audio: 音声生成をスキップ
        """
        self.pdf_dir = Path(pdf_dir)
        self.fps = fps
        self.voice_engine = voice_engine
        self.narrator = narrator
        self.speed = speed
        self.pitch = pitch
        self.skip_script = skip_script
        self.skip_audio = skip_audio

        # 出力ディレクトリ
        if output_dir:
            self.output_dir = Path(output_dir)
        else:
            self.output_dir = self.pdf_dir / "video_output"

        self.output_dir.mkdir(parents=True, exist_ok=True)

        # プロジェクトルート
        self.project_root = Path(__file__).parent.parent
        self.remotion_dir = self.project_root / "remotion-project"

        # 中間ファイルパス
        self.script_json = self.output_dir / "script.json"
        self.audio_dir = self.output_dir / "audio"
        self.slides_dir = self.output_dir / "slides"
        self.timings_json = self.remotion_dir / "timings.json"
        self.slides_metadata = self.remotion_dir / "slides_metadata.json"

    def find_pdf_files(self) -> List[Path]:
        """PDFファイルを取得（merged.pdf を優先、なければプレゼン名.pdf）"""
        # merged.pdf があればそれを優先使用
        merged_pdf = self.pdf_dir / "merged.pdf"
        if merged_pdf.exists():
            print(f"\n=== PDFファイル検出 ===")
            print(f"  merged.pdf を使用")
            return [merged_pdf]

        # なければプレゼン名.pdf を使用（フォルダ名と同じ名前のPDF）
        presentation_pdf = self.pdf_dir / f"{self.pdf_dir.name}.pdf"
        if presentation_pdf.exists():
            print(f"\n=== PDFファイル検出 ===")
            print(f"  {presentation_pdf.name} を使用")
            return [presentation_pdf]

        # なければ個別のPDFを番号順にソート
        pdf_files = list(self.pdf_dir.glob("*.pdf"))

        if not pdf_files:
            raise FileNotFoundError(f"PDFファイルが見つかりません: {self.pdf_dir}")

        # 番号順にソート
        pdf_files.sort(key=lambda p: extract_number_from_filename(p.name))

        print(f"\n=== PDFファイル検出 ===")
        for i, pdf in enumerate(pdf_files, 1):
            print(f"  {i}. {pdf.name}")

        return pdf_files

    def extract_pdf_content(self, pdf_path: Path) -> List[Dict]:
        """PDFからページごとの内容を抽出（テキスト+画像OCR）"""
        if fitz is None:
            raise ImportError("PyMuPDFをインストールしてください: pip install PyMuPDF")

        pages = []
        doc = fitz.open(str(pdf_path))

        for page_num in range(len(doc)):
            page = doc[page_num]

            # テキストを抽出
            text = page.get_text("text").strip()

            # 画像としてレンダリング（OCR用とスライド用）
            # 高解像度でレンダリング
            mat = fitz.Matrix(2.0, 2.0)  # 2倍の解像度
            pix = page.get_pixmap(matrix=mat)

            # 一時ファイルに保存
            img_data = pix.tobytes("png")

            pages.append({
                'pdf_name': pdf_path.stem,
                'page_num': page_num + 1,
                'text': text,
                'image_data': img_data,
                'width': pix.width,
                'height': pix.height
            })

        doc.close()
        return pages

    def analyze_page_with_vision(self, page: Dict, api_key: str) -> str:
        """Gemini Vision APIでページ画像を解析してテキスト内容を理解"""
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)

            # 画像データをbase64エンコード
            img_base64 = base64.b64encode(page['image_data']).decode('utf-8')

            # Vision対応モデルを使用（レート制限が緩やかなモデル）
            model = genai.GenerativeModel('gemini-2.0-flash')

            # テキストが少ない場合は画像から内容を読み取る
            existing_text = page.get('text', '').strip()

            if len(existing_text) < 50:
                # テキストが画像化されている可能性が高い
                prompt = """この画像はプレゼンテーションスライドです。
画像内のすべてのテキスト、図表、概念を詳しく読み取ってください。

以下の形式で出力してください:
【タイトル】（あれば）
【メインコンテンツ】
【補足情報】（図表や注釈があれば）

日本語で出力してください。"""
            else:
                prompt = f"""この画像はプレゼンテーションスライドです。
既に抽出されたテキスト:
{existing_text}

このテキストと画像を参照し、以下を補完してください:
1. 図表やグラフの内容説明
2. テキストで表現されていない視覚的な情報
3. レイアウトから読み取れる重要度や関連性

補完情報を日本語で出力してください。"""

            # 画像を含むリクエスト
            response = model.generate_content([
                prompt,
                {
                    'mime_type': 'image/png',
                    'data': img_base64
                }
            ])

            return response.text.strip()

        except Exception as e:
            print(f"      Vision API エラー: {e}")
            return page.get('text', '')

    def generate_explanation_script(self, all_pages: List[Dict], api_key: str) -> Dict:
        """ページ内容から解説原稿を生成"""
        print("\n=== ステップ2: 解説原稿生成 ===")

        if self.skip_script and self.script_json.exists():
            print(f"既存の原稿を使用: {self.script_json}")
            with open(self.script_json, 'r', encoding='utf-8') as f:
                return json.load(f)

        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-2.0-flash')
        except ImportError:
            raise ImportError("google-generativeai パッケージをインストールしてください")

        scripts = []

        for i, page in enumerate(all_pages):
            print(f"  ページ {i+1}/{len(all_pages)}: {page['pdf_name']} - P{page['page_num']}")

            # ページ内容を解析（Vision APIで画像からも読み取り）
            page_content = self.analyze_page_with_vision(page, api_key)

            # 解説原稿を生成
            prompt = f"""あなたは講師「塾頭高崎翔太」として、プレゼンテーションの解説を行います。

以下のスライド内容について、視聴者に分かりやすく解説する原稿を作成してください。

【スライド内容】
{page_content}

【要件】
1. 自然な話し言葉で、講師が視聴者に語りかける口調
2. 30〜60秒程度で読める長さ（150〜300文字程度）
3. スライドの内容を補足・解説する形で
4. 難しい概念は噛み砕いて説明
5. 「では」「さて」などの接続詞で始めると自然

原稿のみを出力してください。"""

            try:
                response = model.generate_content(prompt)
                script_text = response.text.strip()

                scripts.append({
                    'index': i + 1,
                    'pdf_name': page['pdf_name'],
                    'page_num': page['page_num'],
                    'title': f"{page['pdf_name']} - {page['page_num']}ページ目",
                    'content': page_content[:500],  # 内容の要約
                    'script': script_text
                })

                print(f"    完了: {len(script_text)}文字")

                # レート制限対策（10リクエスト/分の制限に対応）
                if i < len(all_pages) - 1:
                    import time
                    time.sleep(8)  # 8秒待機で約7リクエスト/分

            except Exception as e:
                print(f"    エラー: {e}")
                scripts.append({
                    'index': i + 1,
                    'pdf_name': page['pdf_name'],
                    'page_num': page['page_num'],
                    'title': f"{page['pdf_name']} - {page['page_num']}ページ目",
                    'content': page_content[:500],
                    'script': f"こちらのスライドについて解説します。{page_content[:100]}"
                })

        script_data = {
            'slides': scripts,
            'total_slides': len(scripts)
        }

        with open(self.script_json, 'w', encoding='utf-8') as f:
            json.dump(script_data, f, ensure_ascii=False, indent=2)

        print(f"  原稿を保存: {self.script_json}")
        return script_data

    def save_slide_images(self, all_pages: List[Dict]) -> int:
        """ページ画像をスライド画像として保存"""
        print("\n=== ステップ3: スライド画像保存 ===")

        self.slides_dir.mkdir(parents=True, exist_ok=True)

        for i, page in enumerate(all_pages):
            output_path = self.slides_dir / f"slide_{i+1:02d}.png"
            with open(output_path, 'wb') as f:
                f.write(page['image_data'])

        print(f"  {len(all_pages)}枚のスライド画像を保存")
        return len(all_pages)

    def _split_text_for_voicepeak(self, text: str, max_chars: int = 130) -> List[str]:
        """テキストを140文字以下のチャンクに分割"""
        clean_text = text.replace('\n', ' ').replace('　', ' ')
        clean_text = ' '.join(clean_text.split())

        if len(clean_text) <= max_chars:
            return [clean_text]

        chunks = []
        current_chunk = ""

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
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

            if not wav_file.exists():
                print(f"      VOICEPEAKエラー: 音声ファイルが生成されませんでした")
                return False

            convert_cmd = [
                'ffmpeg', '-y', '-i', str(wav_file),
                '-codec:a', 'libmp3lame', '-qscale:a', '2',
                str(output_file)
            ]
            subprocess.run(convert_cmd, capture_output=True, check=True)
            wav_file.unlink()

            return True

        except Exception as e:
            print(f"      VOICEPEAKエラー: {e}")
            return False

    def _generate_audio_voicepeak(self, text: str, output_file: Path) -> bool:
        """VOICEPEAKで音声を生成（140文字制限対応）"""
        chunks = self._split_text_for_voicepeak(text)

        if len(chunks) == 1:
            return self._generate_single_voicepeak(chunks[0], output_file)
        else:
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
                for tf in temp_files:
                    if tf.exists():
                        tf.unlink()
                if temp_dir.exists():
                    for f in temp_dir.glob("*"):
                        f.unlink()
                    temp_dir.rmdir()

    def _get_audio_duration(self, audio_file: Path) -> float:
        """音声ファイルの長さを取得"""
        if MP3:
            try:
                audio = MP3(str(audio_file))
                return audio.info.length
            except Exception:
                pass

        try:
            result = subprocess.run(
                ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                 '-of', 'default=noprint_wrappers=1:nokey=1', str(audio_file)],
                capture_output=True, text=True
            )
            return float(result.stdout.strip())
        except Exception:
            return 5.0

    async def generate_audio(self, script_data: Dict) -> List[Dict]:
        """音声を生成"""
        print("\n=== ステップ4: 音声生成 ===")

        self.audio_dir.mkdir(parents=True, exist_ok=True)

        if self.skip_audio:
            existing_files = list(self.audio_dir.glob("slide_*.mp3"))
            if existing_files:
                print(f"既存の音声ファイルを使用: {len(existing_files)}件")
                return self._get_audio_metadata()

        use_voicepeak = False
        if self.voice_engine == "voicepeak" and os.path.exists(self.VOICEPEAK_PATH):
            use_voicepeak = True
            print(f"  音声エンジン: VOICEPEAK")
            print(f"  ナレーター: {self.narrator}")

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
                        success = self._generate_audio_voicepeak(text, output_file)
                    else:
                        # フォールバック: gTTS
                        from gtts import gTTS
                        tts = gTTS(text, lang='ja')
                        tts.save(str(output_file))
                        success = True

                    if success and output_file.exists():
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

        return audio_files

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

    def _generate_subtitles(
        self, text: str, start_time: float, end_time: float,
        start_frame: int, end_frame: int
    ) -> List[Dict]:
        """テキストから字幕を生成"""
        if not text:
            return []

        sentences = re.split(r'[。！？\n]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]

        if not sentences:
            return []

        total_chars = sum(len(s) for s in sentences)
        if total_chars == 0:
            return []

        duration = end_time - start_time
        frame_duration = end_frame - start_frame

        subtitles = []
        current_time = start_time
        current_frame = start_frame

        for i, sentence in enumerate(sentences):
            ratio = len(sentence) / total_chars
            sent_duration = duration * ratio
            sent_frames = round(frame_duration * ratio)

            if i == len(sentences) - 1:
                sent_end_time = end_time
                sent_end_frame = end_frame
            else:
                sent_end_time = current_time + sent_duration
                sent_end_frame = current_frame + sent_frames

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

    def generate_timings(self, audio_files: List[Dict], script_data: Dict) -> Dict:
        """タイミングデータを生成"""
        print("\n=== ステップ5: タイミング計算 ===")

        slides = []
        current_time = 0.0
        current_frame = 0

        for audio in audio_files:
            idx = audio['index']
            duration = audio['duration']
            duration_frames = int(duration * self.fps)

            script_text = ""
            for s in script_data['slides']:
                if s['index'] == idx:
                    script_text = s['script']
                    break

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

    def setup_remotion(self, timings: Dict, slide_count: int):
        """Remotion用にファイルを配置"""
        print("\n=== ステップ6: Remotion設定 ===")

        with open(self.timings_json, 'w', encoding='utf-8') as f:
            json.dump(timings, f, ensure_ascii=False, indent=2)
        print(f"  タイミングファイル: {self.timings_json}")

        slides_metadata = {'total_slides': slide_count}
        with open(self.slides_metadata, 'w', encoding='utf-8') as f:
            json.dump(slides_metadata, f, ensure_ascii=False, indent=2)

        remotion_audio_dir = self.remotion_dir / "public" / "audio"
        remotion_audio_dir.mkdir(parents=True, exist_ok=True)

        for audio_file in self.audio_dir.glob("*.mp3"):
            shutil.copy(audio_file, remotion_audio_dir / audio_file.name)

        remotion_slides_dir = self.remotion_dir / "public" / "slides"
        remotion_slides_dir.mkdir(parents=True, exist_ok=True)

        for slide_file in self.slides_dir.glob("slide_*.png"):
            shutil.copy(slide_file, remotion_slides_dir / slide_file.name)

        print(f"  ファイルをRemotionにコピー完了")

    def render_video(self) -> Path:
        """Remotionで動画をレンダリング"""
        print("\n=== ステップ7: 動画レンダリング ===")

        # プレゼン名（フォルダ名）を動画ファイル名にする
        presentation_name = self.pdf_dir.name
        output_video = self.output_dir / f"{presentation_name}.mp4"
        chunks_dir = self.output_dir / "chunks"
        chunks_dir.mkdir(parents=True, exist_ok=True)

        with open(self.timings_json, 'r', encoding='utf-8') as f:
            timings = json.load(f)

        slides = timings['slides']
        total_slides = len(slides)
        chunk_size = 5
        chunk_videos = []
        total_chunks = (total_slides + chunk_size - 1) // chunk_size

        print(f"  総スライド数: {total_slides}")
        print(f"  総チャンク数: {total_chunks}")

        for chunk_idx in range(0, total_slides, chunk_size):
            chunk_end = min(chunk_idx + chunk_size, total_slides)
            chunk_slides = slides[chunk_idx:chunk_end]

            start_frame = chunk_slides[0]['startFrame']
            end_frame = chunk_slides[-1]['endFrame']

            chunk_num = chunk_idx // chunk_size + 1
            chunk_video = chunks_dir / f"chunk_{chunk_num:03d}.mp4"

            if chunk_video.exists():
                print(f"  チャンク {chunk_num}/{total_chunks}: スキップ（既存）")
                chunk_videos.append(chunk_video)
                continue

            print(f"  チャンク {chunk_num}/{total_chunks}: フレーム {start_frame}-{end_frame}")

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
                subprocess.run(
                    cmd,
                    cwd=str(self.remotion_dir),
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=1800
                )
                chunk_videos.append(chunk_video)
                print(f"    完了")

            except Exception as e:
                print(f"    エラー: {e}")
                if chunk_video.exists():
                    chunk_videos.append(chunk_video)

        if not chunk_videos:
            existing_chunks = sorted(chunks_dir.glob("chunk_*.mp4"))
            if existing_chunks:
                chunk_videos = existing_chunks

        print(f"\n  チャンク結合中... ({len(chunk_videos)}ファイル)")

        concat_list = chunks_dir / "concat_list.txt"
        with open(concat_list, 'w', encoding='utf-8') as f:
            for chunk_video in sorted(chunk_videos):
                f.write(f"file '{chunk_video.name}'\n")

        concat_cmd = [
            'ffmpeg', '-y',
            '-f', 'concat',
            '-safe', '0',
            '-i', str(concat_list),
            '-c', 'copy',
            str(output_video)
        ]

        subprocess.run(
            concat_cmd,
            cwd=str(chunks_dir),
            check=True,
            capture_output=True,
            text=True,
            timeout=300
        )

        print(f"  結合完了: {output_video}")

        if output_video.exists():
            size_mb = output_video.stat().st_size / (1024 * 1024)
            print(f"  サイズ: {size_mb:.1f}MB")

        return output_video

    def process(self):
        """全体のワークフローを実行"""
        print(f"\n{'='*50}")
        print(f"PDF解説動画作成")
        print(f"{'='*50}")
        print(f"入力: {self.pdf_dir}")
        print(f"出力: {self.output_dir}")

        # APIキー確認
        api_key = os.environ.get('GOOGLE_AI_API_KEY')
        if not api_key:
            raise ValueError("GOOGLE_AI_API_KEY環境変数が設定されていません")

        # 1. PDFファイル検出
        pdf_files = self.find_pdf_files()

        # 2. PDF内容抽出
        print("\n=== ステップ1: PDF内容抽出 ===")
        all_pages = []
        for pdf_file in pdf_files:
            print(f"  {pdf_file.name} を読み込み中...")
            pages = self.extract_pdf_content(pdf_file)
            all_pages.extend(pages)
            print(f"    {len(pages)}ページ")

        print(f"  合計: {len(all_pages)}ページ")

        # 3. 解説原稿生成
        script_data = self.generate_explanation_script(all_pages, api_key)

        # 4. スライド画像保存
        slide_count = self.save_slide_images(all_pages)

        # 5. 音声生成
        audio_files = asyncio.run(self.generate_audio(script_data))

        # 6. タイミング計算
        timings = self.generate_timings(audio_files, script_data)

        # 7. Remotion設定
        self.setup_remotion(timings, slide_count)

        # 8. 動画レンダリング
        output_video = self.render_video()

        print(f"\n{'='*50}")
        print(f"完了！")
        print(f"{'='*50}")
        print(f"出力動画: {output_video}")

        return output_video


def main():
    parser = argparse.ArgumentParser(
        description='PDFファイルから解説動画を作成'
    )
    parser.add_argument('pdf_dir', help='PDFファイルが含まれるディレクトリ')
    parser.add_argument('--output-dir', '-o', help='出力ディレクトリ')
    parser.add_argument('--fps', type=int, default=30, help='フレームレート')
    parser.add_argument(
        '--voice-engine',
        choices=['voicepeak', 'gtts', 'edge_tts'],
        default='voicepeak',
        help='音声エンジン'
    )
    parser.add_argument(
        '--narrator',
        default='Japanese Female 1',
        help='VOICEPEAKナレーター名'
    )
    parser.add_argument('--speed', type=int, default=120, help='話速')
    parser.add_argument('--pitch', type=int, default=0, help='声の高さ')
    parser.add_argument('--skip-script', action='store_true', help='原稿生成をスキップ')
    parser.add_argument('--skip-audio', action='store_true', help='音声生成をスキップ')

    args = parser.parse_args()

    if not os.path.isdir(args.pdf_dir):
        print(f"エラー: ディレクトリが見つかりません: {args.pdf_dir}")
        sys.exit(1)

    creator = PDFVideoCreator(
        pdf_dir=args.pdf_dir,
        output_dir=args.output_dir,
        fps=args.fps,
        voice_engine=args.voice_engine,
        narrator=args.narrator,
        speed=args.speed,
        pitch=args.pitch,
        skip_script=args.skip_script,
        skip_audio=args.skip_audio
    )

    creator.process()


if __name__ == '__main__':
    main()
