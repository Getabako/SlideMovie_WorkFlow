#!/bin/bash

# プレゼンテーション動画作成一括実行スクリプト
# 使用方法: ./generate_presentation_video.sh <markdown_file> [duration]

set -e  # エラーが発生したら即座に終了

# 引数チェック
if [ $# -lt 1 ]; then
    echo "使用方法: $0 <markdown_file> [duration]"
    echo "  markdown_file: プレゼンテーションのマークダウンファイル"
    echo "  duration: 各スライドの表示時間（秒、デフォルト: 5）"
    exit 1
fi

MD_FILE="$1"
DURATION="${2:-5}"

# ファイル存在チェック
if [ ! -f "$MD_FILE" ]; then
    echo "エラー: ファイルが見つかりません: $MD_FILE"
    exit 1
fi

# スクリプトディレクトリ
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# 環境変数チェック
if [ -z "$GOOGLE_AI_API_KEY" ]; then
    echo "エラー: GOOGLE_AI_API_KEY環境変数が設定されていません"
    echo "export GOOGLE_AI_API_KEY='your-api-key'"
    exit 1
fi

echo "======================================"
echo "プレゼンテーション動画作成ワークフロー"
echo "======================================"
echo "入力ファイル: $MD_FILE"
echo "スライド表示時間: ${DURATION}秒"
echo ""

# ステップ1: 画像生成
echo "【ステップ1/2】画像生成"
echo "--------------------------------------"

python3 "$SCRIPT_DIR/generate_slide_images.py" "$MD_FILE"

if [ $? -ne 0 ]; then
    echo "エラー: 画像生成に失敗しました"
    exit 1
fi

echo ""
echo "✓ 画像生成完了"
echo ""

# ステップ2: 動画作成
echo "【ステップ2/2】動画作成"
echo "--------------------------------------"

python3 "$SCRIPT_DIR/create_presentation_video.py" "$MD_FILE" --duration "$DURATION"

if [ $? -ne 0 ]; then
    echo "エラー: 動画作成に失敗しました"
    exit 1
fi

echo ""
echo "✓ 動画作成完了"
echo ""

# 出力ファイル情報
PRESENTATION_DIR="$(dirname "$MD_FILE")"
PRESENTATION_NAME="$(basename "$MD_FILE" .md)"
OUTPUT_DIR="$PRESENTATION_DIR/output"
OUTPUT_VIDEO="$OUTPUT_DIR/${PRESENTATION_NAME}.mp4"

if [ -f "$OUTPUT_VIDEO" ]; then
    echo "======================================"
    echo "完了！"
    echo "======================================"
    echo "出力動画: $OUTPUT_VIDEO"

    # 動画情報を表示
    if command -v ffprobe &> /dev/null; then
        echo ""
        echo "動画情報:"
        ffprobe -v error -show_entries format=duration,size,bit_rate \
            -show_entries stream=width,height,codec_name \
            -of default=noprint_wrappers=1 "$OUTPUT_VIDEO" 2>&1 | grep -E '(width|height|duration|size|codec_name)'
    fi
else
    echo "警告: 出力ファイルが見つかりません: $OUTPUT_VIDEO"
    exit 1
fi
