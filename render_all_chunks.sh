#!/bin/bash

cd "/Users/takasaki19841121/Desktop/SlideMovie_WorkFlow-main/remotion-project"

TOTAL_FRAMES=77935
CHUNK_SIZE=3000
OUTPUT_DIR="/Users/takasaki19841121/Desktop/SlideMovie_WorkFlow-main/presentations/⑦ホームページ作り/video_output/chunks"

for START in 0 3000 6000 9000 12000 15000 18000 21000 24000 27000 30000 33000 36000 39000 42000 45000 48000 51000 54000 57000 60000 63000 66000 69000 72000 75000; do
  END=$((START + CHUNK_SIZE - 1))
  if [ $END -ge $TOTAL_FRAMES ]; then
    END=$((TOTAL_FRAMES - 1))
  fi
  CHUNK_NUM=$((START / CHUNK_SIZE + 1))
  CHUNK_FILE="$OUTPUT_DIR/chunk_$(printf '%03d' $CHUNK_NUM).mp4"

  if [ -f "$CHUNK_FILE" ]; then
    echo "Chunk $CHUNK_NUM already exists, skipping..."
    continue
  fi

  echo "Rendering chunk $CHUNK_NUM: frames $START-$END"
  npx remotion render Video "$CHUNK_FILE" --frames $START-$END --timeout 600000 --concurrency 1 --log error 2>&1 | tail -1
  echo "---"
done

echo "All chunks rendered!"

# Concat all chunks
cd "$OUTPUT_DIR"
ls chunk_*.mp4 | sort | while read f; do echo "file '$f'"; done > concat_list.txt
ffmpeg -y -f concat -safe 0 -i concat_list.txt -c copy ../output.mp4

echo "Final video created at: $OUTPUT_DIR/../output.mp4"
