# ステップ3: タイミング設定

音声ファイルから動画のタイミングデータを生成するサブタスク

## 引数
$ARGUMENTS - プレゼンテーションのパス

## タスク
1. 各音声ファイルの長さを取得（ffprobe使用）
2. スライドごとの開始フレーム、終了フレームを計算
3. 字幕タイミングデータを生成
4. `remotion-project/public/timings.json` を更新

## タイミング計算
- フレームレート: 30fps
- 各スライドのフレーム数 = 音声長(秒) × 30

## 重要: 音声と字幕の同期

**字幕は文字数に比例して時間を配分すること！**

音声合成は文字数に比例して読み上げ時間が決まるため、字幕も同様に文字数比例で配分しないとズレが発生します。

### 正しい字幕タイミング計算
```python
# 各文の文字数に比例して時間を配分
total_chars = sum(len(s) for s in sentences)
current_frame = start_frame

for i, sentence in enumerate(sentences):
    ratio = len(sentence) / total_chars  # 文字数比率
    sent_frames = round(duration_frames * ratio)

    # 最後の文は確実に終了フレームまで
    if i == len(sentences) - 1:
        end_frame = slide_end_frame
    else:
        end_frame = current_frame + sent_frames

    subtitles.append({
        'text': sentence[:50],
        'startFrame': current_frame,
        'endFrame': end_frame
    })
    current_frame = end_frame
```

### NG: 均等割りは使わない
```python
# これはNG - ズレの原因になる
frame_per_sentence = duration_frames / len(sentences)
```

## timings.json フォーマット
```json
{
  "slides": [
    {
      "index": 1,
      "audioFile": "audio/slide_001.wav",
      "startFrame": 0,
      "durationFrames": 150,
      "script": "原稿テキスト",
      "subtitles": [...]
    }
  ],
  "totalFrames": 12345,
  "fps": 30
}
```

## 確認コマンド
```bash
cat remotion-project/public/timings.json | head -50
```

## 完了報告
タイミング設定が完了したら、以下を報告:
- 総フレーム数
- スライド数
- 動画の総時間（分:秒）
