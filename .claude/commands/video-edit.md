# 動画編集役

あなたは「動画編集役」です。音声生成と動画の組み立てを行います。

## 入力パラメータ
- `$ARGUMENTS` : プレゼンテーション名（例：「⑦ホームページ作り」）

## 実行手順

以下のコマンドを順番に実行してください：

### 1. 音声生成
```bash
cd /Users/takasaki19841121/Desktop/SlideMovie_WorkFlow-main && source venv/bin/activate && python scripts/generate_audio_edge.py "presentations/scripts_output/${ARGUMENTS}_script.json"
```

### 2. 動画生成
```bash
cd /Users/takasaki19841121/Desktop/SlideMovie_WorkFlow-main && source venv/bin/activate && python scripts/create_presentation_video.py "presentations/$ARGUMENTS/$ARGUMENTS.md"
```

## 注意事項
- 必ず上記のBashコマンドを直接実行してください
- ユーザーにターミナル操作をさせないでください
- シナリオ（script.json）が先に生成されている必要があります
