# 動画修正コマンド

既存の動画の原稿やキャラクターアニメーションを修正し、再レンダリングします。

## 引数
- `$ARGUMENTS`: プレゼンテーション名（例: `⑦ホームページ作り`）

## このコマンドで修正できる問題

1. **プレースホルダー原稿の修正**
   - 「スライドの内容です」などの仮テキストを実際の内容に置き換え

2. **キャラクターアニメーションの改善**
   - idle状態（待機）とtalk状態（発話）の切り替え
   - 文と文の間に自然なポーズを追加

3. **音声ファイルの再生成**
   - VOICEPEAKの140文字制限に対応した分割生成
   - 修正した原稿に合わせた音声再生成

4. **動画の再レンダリング**
   - チャンク分割レンダリング（メモリ効率化）
   - timings.jsonの自動更新

## 処理手順

### 1. 原稿の問題を確認

```bash
# script.jsonでプレースホルダーテキストを検索
grep -n "スライドの内容です" "presentations/$ARGUMENTS/video_output/script.json"
```

問題のあるスライドが見つかった場合：
- 元のマークダウンファイル（`presentations/$ARGUMENTS/$ARGUMENTS.md`）を読んで実際の内容を確認
- script.jsonの該当スライドのscriptフィールドを適切な内容に更新

### 2. 音声ファイルの再生成（VOICEPEAKの場合）

修正した原稿の音声を再生成するスクリプト：

```python
#!/usr/bin/env python3
import subprocess
import json
from pathlib import Path
import time

VOICEPEAK_PATH = "/Applications/voicepeak.app/Contents/MacOS/voicepeak"
NARRATOR = "Japanese Female 1"
SPEED = 150
OUTPUT_DIR = Path("presentations/$ARGUMENTS/video_output/audio")
SCRIPT_FILE = Path("presentations/$ARGUMENTS/video_output/script.json")

# 再生成するスライド番号のリスト
MISSING_SLIDES = [7, 8, 9, 10, 11, 12, 13]  # 必要に応じて変更

def split_text(text: str, max_chars: int = 130) -> list:
    """VOICEPEAKの140文字制限に対応するためテキストを分割"""
    clean_text = text.replace('\n', ' ').replace('　', ' ')
    clean_text = ' '.join(clean_text.split())

    if len(clean_text) <= max_chars:
        return [clean_text]

    chunks = []
    sentences = []
    temp = ""
    for char in clean_text:
        temp += char
        if char in '。！？':
            sentences.append(temp)
            temp = ""
    if temp:
        sentences.append(temp)

    current_chunk = ""
    for sentence in sentences:
        if len(current_chunk) + len(sentence) <= max_chars:
            current_chunk += sentence
        else:
            if current_chunk:
                chunks.append(current_chunk)
            if len(sentence) > max_chars:
                # 読点で分割
                sub_parts = sentence.split('、')
                sub_chunk = ""
                for i, part in enumerate(sub_parts):
                    part_with_comma = part + '、' if i < len(sub_parts) - 1 else part
                    if len(sub_chunk) + len(part_with_comma) <= max_chars:
                        sub_chunk += part_with_comma
                    else:
                        if sub_chunk:
                            chunks.append(sub_chunk)
                        sub_chunk = part_with_comma
                current_chunk = sub_chunk if sub_chunk else ""
            else:
                current_chunk = sentence

    if current_chunk:
        chunks.append(current_chunk)

    return chunks

def generate_audio(text: str, output_file: Path) -> bool:
    """音声生成（チャンク分割対応）"""
    chunks = split_text(text)

    if len(chunks) == 1:
        # 単一チャンク
        wav_file = output_file.with_suffix('.wav')
        cmd = [VOICEPEAK_PATH, '-s', chunks[0], '-o', str(wav_file),
               '-n', NARRATOR, '--speed', str(SPEED)]
        subprocess.run(cmd, capture_output=True, timeout=120)
        # WAV→MP3変換
        subprocess.run(['ffmpeg', '-y', '-i', str(wav_file),
                       '-codec:a', 'libmp3lame', '-qscale:a', '2',
                       str(output_file)], capture_output=True)
        wav_file.unlink()
        return output_file.exists()

    # 複数チャンクの場合
    temp_dir = OUTPUT_DIR / "temp_chunks"
    temp_dir.mkdir(exist_ok=True)
    temp_files = []

    for i, chunk in enumerate(chunks):
        temp_file = temp_dir / f"chunk_{i:03d}.mp3"
        wav_file = temp_file.with_suffix('.wav')
        cmd = [VOICEPEAK_PATH, '-s', chunk, '-o', str(wav_file),
               '-n', NARRATOR, '--speed', str(SPEED)]
        subprocess.run(cmd, capture_output=True, timeout=120)
        subprocess.run(['ffmpeg', '-y', '-i', str(wav_file),
                       '-codec:a', 'libmp3lame', '-qscale:a', '2',
                       str(temp_file)], capture_output=True)
        wav_file.unlink()
        temp_files.append(temp_file)
        time.sleep(1)

    # 結合
    concat_list = temp_dir / "concat.txt"
    with open(concat_list, 'w') as f:
        for tf in temp_files:
            f.write(f"file '{tf.name}'\n")

    subprocess.run(['ffmpeg', '-y', '-f', 'concat', '-safe', '0',
                   '-i', str(concat_list), '-codec:a', 'libmp3lame',
                   '-qscale:a', '2', str(output_file)], capture_output=True)

    # クリーンアップ
    for tf in temp_files:
        tf.unlink()
    concat_list.unlink()
    temp_dir.rmdir()

    return output_file.exists()
```

### 3. timings.jsonの更新

```python
from mutagen.mp3 import MP3

def update_timings():
    FPS = 30
    timings = []
    current_frame = 0

    with open(SCRIPT_FILE, 'r') as f:
        script_data = json.load(f)

    for slide in script_data['slides']:
        index = slide['index']
        audio_file = OUTPUT_DIR / f"slide_{index:03d}.mp3"
        duration = MP3(str(audio_file)).info.length if audio_file.exists() else 5.0
        duration_frames = int(duration * FPS)

        timings.append({
            "slideIndex": index,
            "startFrame": current_frame,
            "durationInFrames": duration_frames,
            "audioFile": f"audio/slide_{index:03d}.mp3",  # audio/プレフィックス必須
            "script": slide.get('script', '')[:100] + "..."
        })
        current_frame += duration_frames

    timings_data = {
        "fps": FPS,
        "totalSlides": len(script_data['slides']),
        "totalFrames": current_frame,
        "totalDuration": current_frame / FPS,
        "slides": timings
    }

    with open("remotion-project/timings.json", 'w') as f:
        json.dump(timings_data, f, indent=2, ensure_ascii=False)
```

### 4. キャラクターアニメーションの修正（必要な場合）

`remotion-project/src/Video.tsx`で、idle/talk状態の切り替えを確認：

```tsx
// 字幕の開始直後と終了直前はidle状態にして、文と文の間の「間」を表現
let isTalking = false;
if (currentSubtitle) {
  const subtitleDurationFrames = currentSubtitle.endFrame - currentSubtitle.startFrame;
  const frameInSubtitle = frame - currentSubtitle.startFrame;

  const pauseFrames = 3;
  if (subtitleDurationFrames <= pauseFrames * 2) {
    isTalking = true;
  } else {
    isTalking = frameInSubtitle >= pauseFrames &&
                frameInSubtitle < subtitleDurationFrames - pauseFrames;
  }
}

const images = isTalking ? talkImages : idleImages;
const animationSpeed = isTalking ? 3 : 5;  // talkは速く、idleはゆっくり
```

### 5. 動画の再レンダリング

```bash
cd remotion-project

# チャンク分割でレンダリング（メモリ効率のため）
TOTAL_FRAMES=$(jq '.totalFrames' timings.json)
CHUNK_SIZE=3000  # 約100秒分

for START in $(seq 0 $CHUNK_SIZE $TOTAL_FRAMES); do
  END=$((START + CHUNK_SIZE - 1))
  if [ $END -ge $TOTAL_FRAMES ]; then
    END=$((TOTAL_FRAMES - 1))
  fi

  CHUNK_NUM=$((START / CHUNK_SIZE + 1))
  CHUNK_FILE="../presentations/$ARGUMENTS/video_output/chunks/chunk_$(printf '%03d' $CHUNK_NUM).mp4"

  npx remotion render Video "$CHUNK_FILE" \
    --frames $START-$END \
    --concurrency 2
done

# チャンクを結合
cd "../presentations/$ARGUMENTS/video_output/chunks"
for i in chunk_*.mp4; do echo "file '$i'"; done > concat_list.txt
ffmpeg -y -f concat -safe 0 -i concat_list.txt -c copy ../final_video.mp4
```

## 重要なポイント

### 音声と字幕の同期（最重要）

**字幕は文字数に比例して時間を配分すること！**

音声合成は文字数に比例して読み上げ時間が決まるため、字幕も同様に文字数比例で配分しないとズレが発生します。

```python
# 正しい字幕タイミング計算
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

**NG: 均等割りは使わない**
```python
# これはNG - ズレの原因になる
frame_per_sentence = duration_frames / len(sentences)
```

### VOICEPEAKの制限
- 1回のリクエストは140文字まで
- それ以上は句点（。）や読点（、）で分割して複数生成→結合

### audioFileパスの注意
- timings.jsonのaudioFileは`audio/slide_001.mp3`形式（audio/プレフィックス必須）
- ファイル実体は`remotion-project/public/audio/slide_001.mp3`

### Remotionのコンポジション名
- 正しいID: `Video`（`SlideVideo`ではない）

### チャンクレンダリング
- 長い動画（10分以上）はメモリ不足を避けるため3000フレームずつ分割
- 各チャンク約2分でレンダリング完了
- 最後にffmpegで結合

## トラブルシューティング

### 音声が見つからない場合
```bash
ls presentations/$ARGUMENTS/video_output/audio/ | wc -l
```

### レンダリングエラーの場合
```bash
# Remotionのログを確認
cd remotion-project && npx remotion render Video test.mp4 --frames 0-100 2>&1
```

### 動画が結合できない場合
```bash
# concat_list.txtの内容を確認
cat presentations/$ARGUMENTS/video_output/chunks/concat_list.txt
```
