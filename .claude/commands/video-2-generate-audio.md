# ステップ2: 音声生成

VOICEPEAKを使用して音声ファイルを生成するサブタスク

## 引数
$ARGUMENTS - プレゼンテーションのMarkdownファイルパス

## タスク
1. Markdownファイルからスクリプトを読み取り
2. 各スライドの原稿からVOICEPEAKで音声を生成
3. 音声ファイルを `presentations/[プレゼン名]/video_output/audio/` に保存

## 音声設定（必須）
- Voice Engine: VOICEPEAK
- Narrator: Japanese Female 1
- Speed: 150（テンポ良く）
- 出力形式: WAV

## VOICEPEAKコマンド例
```bash
/Applications/voicepeak.app/Contents/MacOS/voicepeak -s "テキスト" -o output.wav -n "Japanese Female 1" --speed 150
```

## 重要な注意事項
- 全スライドの音声を生成すること
- 間延びしない速度設定（speed 150）を使用
- 生成後、音声ファイル数がスライド数と一致することを確認

## 確認コマンド
```bash
ls presentations/[プレゼン名]/video_output/audio/*.wav | wc -l
```

## 完了報告
音声生成が完了したら、以下を報告:
- 生成した音声ファイル数
- 使用した音声設定
