# ワークフロー管理

あなたは「ワークフロー管理者」です。スライド動画作成の全工程を管理・実行します。

## 入力パラメータ
- `$ARGUMENTS` : 「工程 プレゼンテーション名」形式
  - 例：「画像生成から ⑦ホームページ作り」
  - 例：「全工程 新しい講座」

## 使用方法

```
/workflow 画像生成から ⑦ホームページ作り
/workflow シナリオから ⑦ホームページ作り
/workflow 全工程 新しい講座
```

## 実行手順

### 「画像生成から」の場合

ユーザーからAPIキーを取得してから、以下を**順番に**実行：

#### ステップ1: プロンプト生成
```bash
cd /Users/takasaki19841121/Desktop/SlideMovie_WorkFlow-main && source venv/bin/activate && python scripts/generate_smart_prompts.py "presentations/<プレゼンテーション名>/<プレゼンテーション名>.md"
```

#### ステップ2: 画像生成
```bash
cd /Users/takasaki19841121/Desktop/SlideMovie_WorkFlow-main && source venv/bin/activate && export GOOGLE_AI_API_KEY="<APIキー>" && python scripts/generate_images_smart.py "presentations/<プレゼンテーション名>/image_prompts.json" --output-dir "presentations/<プレゼンテーション名>/images"
```

#### ステップ3: 画像挿入
```bash
cd /Users/takasaki19841121/Desktop/SlideMovie_WorkFlow-main && source venv/bin/activate && python scripts/insert_images_to_slides.py "presentations/<プレゼンテーション名>/<プレゼンテーション名>.md" --images-dir "presentations/<プレゼンテーション名>/images"
```

#### ステップ4: スライド画像化
```bash
cd /Users/takasaki19841121/Desktop/SlideMovie_WorkFlow-main/presentations/<プレゼンテーション名> && npx @marp-team/marp-cli "<プレゼンテーション名>.md" --images png --allow-local-files -o "<プレゼンテーション名>.png"
```

#### ステップ5: シナリオ生成
```bash
cd /Users/takasaki19841121/Desktop/SlideMovie_WorkFlow-main && source venv/bin/activate && python scripts/generate_script.py "presentations/<プレゼンテーション名>/<プレゼンテーション名>.md"
```

#### ステップ6: 音声生成
```bash
cd /Users/takasaki19841121/Desktop/SlideMovie_WorkFlow-main && source venv/bin/activate && python scripts/generate_audio_edge.py "presentations/scripts_output/<プレゼンテーション名>_script.json"
```

#### ステップ7: 動画生成
```bash
cd /Users/takasaki19841121/Desktop/SlideMovie_WorkFlow-main && source venv/bin/activate && python scripts/create_presentation_video.py "presentations/<プレゼンテーション名>/<プレゼンテーション名>.md"
```

### 「シナリオから」の場合
ステップ5〜7を実行

### 「画像化から」の場合
ステップ4〜7を実行

## 注意事項
- 必ず上記のBashコマンドを直接実行してください
- **ユーザーにターミナル操作をさせないでください**
- APIキーは最初に一度だけ確認してください
- 各ステップ完了後に次のステップに進んでください
