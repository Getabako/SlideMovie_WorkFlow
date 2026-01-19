#!/usr/bin/env python3
"""
サムネイル生成スクリプト
Gemini gemini-2.5-flash-preview-05-20 を使用して動画のサムネイルを生成
"""

import argparse
import base64
import json
import os
import re
import sys
from pathlib import Path

import requests
from google import genai
from google.genai import types
from PIL import Image
import io


def extract_video_info(presentation_dir: Path) -> dict:
    """動画の情報を抽出"""
    info = {
        "title": presentation_dir.name,
        "script": "",
        "slide_count": 0
    }

    # スクリプトファイルを読み込み
    script_file = presentation_dir / "video_output" / "scripts.json"
    if script_file.exists():
        with open(script_file, "r", encoding="utf-8") as f:
            scripts = json.load(f)
            info["script"] = "\n".join([s.get("script", "") for s in scripts[:5]])  # 最初の5スライド
            info["slide_count"] = len(scripts)

    # PDFからタイトルを取得
    merged_pdf = presentation_dir / "merged.pdf"
    if not merged_pdf.exists():
        # フォルダ名.pdf を探す
        pdf_files = list(presentation_dir.glob("*.pdf"))
        if pdf_files:
            merged_pdf = pdf_files[0]

    return info


def generate_thumbnail_prompt(video_info: dict, title: str) -> str:
    """サムネイル生成用のプロンプトを作成"""

    # タイトルから主要なキーワードを抽出
    keywords = []
    if "AI" in title:
        keywords.append("AI・人工知能")
    if "画像生成" in title:
        keywords.append("画像生成")
    if "ホームページ" in title:
        keywords.append("ウェブサイト作成")
    if "バナー" in title:
        keywords.append("バナーデザイン")
    if "スプレッドシート" in title:
        keywords.append("表計算")
    if "ディープ" in title or "リサーチ" in title:
        keywords.append("調査・リサーチ")
    if "資料" in title:
        keywords.append("資料作成")
    if "スライド" in title:
        keywords.append("プレゼンテーション")

    keyword_text = "、".join(keywords) if keywords else "IT・プログラミング教育"

    prompt = f"""
YouTubeサムネイル画像を生成してください。

【動画タイトル】
{title}

【動画の内容キーワード】
{keyword_text}

【サムネイルの要件】
1. サイズ: 1280x720ピクセル（16:9）
2. 背景: 動画の内容に合ったグラデーションまたはテクノロジー感のある背景
3. メインテキスト: タイトルの核心部分を大きく表示
   - 文字は白または黄色で、黒い縁取り（3-4px）
   - 発光エフェクト（グロー効果）
   - 立体的な浮き出し効果（ドロップシャドウ）
4. キャラクター配置: 右下に配置、動画内容に合ったポーズ・表情
5. ロゴ: 左上または右上の角に小さく配置

【重要な注意事項 - キャラクターについて】
- キャラクターは黒いヘアバンドで目が完全に隠れています
- 目は絶対に見えてはいけません
- ヘアバンドは額から目を覆う位置にあります
- 髪は黒くてボサボサ
- 黒いTシャツと黒いハーフパンツを着用
- 赤い下駄を履いている
- 腕にサイバー風のタトゥー
- 笑顔で親しみやすい表情（口は見える）
- ノートパソコンを持っているポーズが基本

【テキストエフェクト詳細】
- 縁取り: 黒色、太さ3-4px
- ドロップシャドウ: 黒、オフセット4px、ブラー8px
- グロー効果: 白または黄色、半径10px
- グラデーション: テキストに微妙なグラデーション

【配色】
- 背景: 青系グラデーション（#1a237e → #4fc3f7）またはテクノロジー感のある色
- メインテキスト: 白または黄色
- サブテキスト: 水色または白

視聴者が思わずクリックしたくなるような、魅力的で目立つサムネイルを生成してください。
"""
    return prompt


def generate_thumbnail(
    presentation_name: str,
    api_key: str,
    character_image_path: str,
    logo_path: str,
    output_dir: Path = None
) -> Path:
    """サムネイルを生成"""

    # パス設定
    base_dir = Path(__file__).parent.parent
    presentations_dir = base_dir / "presentations"
    presentation_dir = presentations_dir / presentation_name

    if output_dir is None:
        output_dir = presentation_dir / "video_output"

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "thumbnail.png"

    # 動画情報を取得
    video_info = extract_video_info(presentation_dir)

    # タイトル整形
    title = presentation_name
    # 数字プレフィックスを除去してタイトルを取得
    clean_title = re.sub(r'^[①-⑳\d]+', '', title)

    # プロンプト生成
    prompt = generate_thumbnail_prompt(video_info, title)

    print(f"\n=== サムネイル生成開始 ===")
    print(f"  プレゼン名: {presentation_name}")
    print(f"  出力先: {output_path}")

    # Gemini クライアント初期化
    client = genai.Client(api_key=api_key)

    # キャラクター画像を読み込み
    character_path = Path(character_image_path)
    if not character_path.exists():
        print(f"  警告: キャラクター画像が見つかりません: {character_path}")
        character_image = None
    else:
        with open(character_path, "rb") as f:
            character_data = f.read()
        character_image = types.Part.from_bytes(
            data=character_data,
            mime_type="image/png"
        )
        print(f"  キャラクター画像読み込み完了")

    # ロゴ画像を読み込み
    logo_path = Path(logo_path)
    if not logo_path.exists():
        print(f"  警告: ロゴ画像が見つかりません: {logo_path}")
        logo_image = None
    else:
        with open(logo_path, "rb") as f:
            logo_data = f.read()
        logo_image = types.Part.from_bytes(
            data=logo_data,
            mime_type="image/png"
        )
        print(f"  ロゴ画像読み込み完了")

    # コンテンツを構築
    contents = [prompt]
    if character_image:
        contents.append("【参照キャラクター画像】このキャラクターを使用してください（目はヘアバンドで完全に隠れている点を厳守）:")
        contents.append(character_image)
    if logo_image:
        contents.append("【ロゴ画像】このロゴをサムネイルの角に配置してください:")
        contents.append(logo_image)

    print(f"  Gemini API呼び出し中...")

    # 画像生成
    try:
        response = client.models.generate_content(
            model="gemini-3-pro-image-preview",
            contents=contents,
            config=types.GenerateContentConfig(
                response_modalities=["image", "text"],
                temperature=1.0,
            )
        )

        # レスポンスから画像を抽出
        image_saved = False
        for part in response.candidates[0].content.parts:
            if hasattr(part, 'inline_data') and part.inline_data:
                # 画像データを保存
                image_data = part.inline_data.data

                # PILで開いてリサイズ（必要に応じて）
                image = Image.open(io.BytesIO(image_data))

                # 1280x720にリサイズ（アスペクト比維持）
                target_size = (1280, 720)
                image = image.resize(target_size, Image.Resampling.LANCZOS)

                # 保存
                image.save(output_path, "PNG", quality=95)
                image_saved = True
                print(f"  サムネイル保存完了: {output_path}")
                break
            elif hasattr(part, 'text') and part.text:
                print(f"  モデルからのテキスト応答: {part.text[:200]}...")

        if not image_saved:
            print(f"  エラー: 画像が生成されませんでした")
            return None

    except Exception as e:
        print(f"  エラー: {e}")
        import traceback
        traceback.print_exc()
        return None

    print(f"\n=== サムネイル生成完了 ===")
    return output_path


def main():
    parser = argparse.ArgumentParser(description="YouTubeサムネイル生成")
    parser.add_argument("presentation", help="プレゼンテーション名")
    parser.add_argument("--api-key", default=os.environ.get("GOOGLE_AI_API_KEY"),
                        help="Google AI API Key")
    parser.add_argument("--character",
                        default="/Users/takasaki19841121/Desktop/SlideMovie_WorkFlow-main/presentations/character/塾頭高崎翔太/塾頭高崎翔太_pc.png",
                        help="キャラクター画像のパス")
    parser.add_argument("--logo",
                        default="/Users/takasaki19841121/Desktop/SlideMovie_WorkFlow-main/remotion-project/public/logo.png",
                        help="ロゴ画像のパス")
    parser.add_argument("--output-dir", help="出力ディレクトリ（省略時はvideo_output）")

    args = parser.parse_args()

    if not args.api_key:
        print("エラー: API keyが設定されていません")
        print("--api-key オプションまたは GOOGLE_AI_API_KEY 環境変数を設定してください")
        sys.exit(1)

    output_dir = Path(args.output_dir) if args.output_dir else None

    result = generate_thumbnail(
        presentation_name=args.presentation,
        api_key=args.api_key,
        character_image_path=args.character,
        logo_path=args.logo,
        output_dir=output_dir
    )

    if result:
        print(f"\n成功: {result}")
    else:
        print("\n失敗: サムネイル生成に失敗しました")
        sys.exit(1)


if __name__ == "__main__":
    main()
