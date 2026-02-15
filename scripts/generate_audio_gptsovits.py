#!/usr/bin/env python3
"""GPT-SoVITSを使って30スライド分の音声を生成するスクリプト"""

import json
import requests
import os
import time
import sys
from pathlib import Path

# 設定
API_URL = "http://127.0.0.1:9880"
SUBTITLES_PATH = "/Users/takasaki19841121/Desktop/ifJukuManager/SlideMovie_WorkFlow-main/presentations/子どもへのIT・AI教育/subtitles.json"
OUTPUT_DIR = "/Users/takasaki19841121/Desktop/ifJukuManager/SlideMovie_WorkFlow-main/presentations/子どもへのIT・AI教育/audio"

def generate_audio(text: str, output_path: str, max_retries: int = 3) -> bool:
    """GPT-SoVITS APIを呼び出して音声を生成（リトライ機能付き）"""
    for attempt in range(max_retries):
        try:
            # GPT-SoVITS API - GETリクエストでルートエンドポイントを使用
            params = {
                "text": text,
                "text_language": "ja",
                "speed": 1.0
            }

            response = requests.get(
                API_URL,
                params=params,
                timeout=300,  # 5分タイムアウト
                stream=True
            )

            if response.status_code == 200:
                # ストリーミングで受信
                with open(output_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)

                # ファイルサイズを確認
                file_size = os.path.getsize(output_path)
                if file_size > 1000:  # 1KB以上なら成功
                    return True
                else:
                    print(f"  警告: ファイルサイズが小さすぎます ({file_size} bytes)")
                    if attempt < max_retries - 1:
                        print(f"  リトライ中...")
                        time.sleep(5)
                        continue
                    return False
            else:
                print(f"  APIエラー: {response.status_code}")
                if attempt < max_retries - 1:
                    print(f"  リトライ中...")
                    time.sleep(5)
                    continue
                return False

        except requests.exceptions.Timeout:
            print(f"  タイムアウト（試行 {attempt + 1}/{max_retries}）")
            if attempt < max_retries - 1:
                print(f"  10秒待機後リトライ...")
                time.sleep(10)
                continue
            return False
        except Exception as e:
            print(f"  エラー: {e}")
            if attempt < max_retries - 1:
                print(f"  5秒待機後リトライ...")
                time.sleep(5)
                continue
            return False

    return False

def main():
    # 出力ディレクトリ作成
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 字幕データ読み込み
    with open(SUBTITLES_PATH, "r", encoding="utf-8") as f:
        subtitles = json.load(f)

    # 開始スライド番号（引数で指定可能）
    start_slide = int(sys.argv[1]) if len(sys.argv) > 1 else 1

    print(f"合計 {len(subtitles)} スライド分の音声を生成します（スライド{start_slide}から開始）")
    print(f"出力先: {OUTPUT_DIR}")
    sys.stdout.flush()

    success_count = 0
    for item in subtitles:
        slide_num = item["slide"]

        # 指定されたスライド番号より前はスキップ
        if slide_num < start_slide:
            continue

        text = item["text"]
        output_path = os.path.join(OUTPUT_DIR, f"slide_{slide_num:03d}.wav")

        # 既存ファイルがあればスキップ
        if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
            print(f"スライド {slide_num}: スキップ（既存）")
            success_count += 1
            continue

        print(f"\nスライド {slide_num}/{len(subtitles)}: 生成中...")
        print(f"  テキスト: {text[:60]}...")
        sys.stdout.flush()

        if generate_audio(text, output_path):
            print(f"  → 完了: {output_path}")
            success_count += 1
        else:
            print(f"  → 失敗")

        # 各スライド間に3秒待機（サーバー負荷軽減）
        time.sleep(3)
        sys.stdout.flush()

    print(f"\n完了: {success_count}/{len(subtitles)} スライド")

if __name__ == "__main__":
    main()
