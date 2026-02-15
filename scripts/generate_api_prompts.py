#!/usr/bin/env python3
"""
Marpマークダウンからスライドごとのapi用画像生成プロンプトを生成する。
「プロンプト重視」モード: テキスト内容・デザイン指示をすべて含む詳細プロンプト。

Usage:
  python scripts/generate_api_prompts.py presentations/プレゼン名/プレゼン名.md

出力: presentations/プレゼン名/api_prompts.json
"""

import sys
import json
import re
from pathlib import Path


def parse_marp_slides(md_path: Path) -> list[dict]:
    """Marpマークダウンをスライドごとにパースする"""
    text = md_path.read_text(encoding='utf-8')
    
    # フロントマターを除去
    text = re.sub(r'^---\n.*?\n---\n', '', text, count=1, flags=re.DOTALL)
    
    # スライド分割
    raw_slides = re.split(r'\n---\n', text)
    
    slides = []
    for i, raw in enumerate(raw_slides, 1):
        raw = raw.strip()
        if not raw:
            continue
        
        # タイトル抽出
        title = ''
        title_match = re.search(r'^#+\s+(.+)$', raw, re.MULTILINE)
        if title_match:
            title = title_match.group(1).strip()
        
        # speaker_notesを抽出（原稿メモ）
        notes = ''
        notes_match = re.search(
            r'<!--\s*(?:speaker_notes|notes|ノート|原稿)\s*[:：]?\s*(.*?)-->',
            raw, re.DOTALL
        )
        if notes_match:
            notes = notes_match.group(1).strip()
        
        # Markdown記法を整理
        clean = raw
        clean = re.sub(r'<!--.*?-->', '', clean, flags=re.DOTALL)  # コメント除去
        clean = re.sub(r'^#+\s+', '', clean, flags=re.MULTILINE)  # 見出し記号除去
        clean = re.sub(r'\*\*(.+?)\*\*', r'\1', clean)  # 太字除去
        clean = re.sub(r'!\[.*?\]\(.*?\)', '', clean)  # 画像除去
        clean = clean.strip()
        
        # 長すぎる場合は切り詰め
        if len(clean) > 500:
            clean = clean[:500] + '...'
        
        slides.append({
            'number': i,
            'title': title or f'スライド{i}',
            'content': clean,
            'speaker_notes': notes,
            'raw': raw
        })
    
    return slides


def detect_slide_type(content: str) -> str:
    """スライド種別を推定"""
    lower = content.lower()
    if any(w in lower for w in ['ワーク', '記入', '練習', '書いて', 'やってみよう']):
        return 'workshop'
    if any(w in lower for w in ['q&a', 'よくある質問', '質問']):
        return 'qa'
    if any(w in lower for w in ['まとめ', 'ふりかえり', '振り返り']):
        return 'summary'
    if any(w in lower for w in ['目次', 'アジェンダ', '本日の流れ']):
        return 'agenda'
    if any(w in lower for w in ['参考文献', 'リソース', '参考']):
        return 'references'
    return 'content'


DESIGN_HINTS = {
    'workshop': 'ワークシート形式。記入欄、チェックボックス、タイマーなどを含む実践的なデザイン。薄い罫線のある用紙風。',
    'qa': 'Q&Aフォーマット。質問と回答が明確に区別されたデザイン。クエスチョンマークアイコン。',
    'summary': 'チェックリスト形式のまとめデザイン。達成感のある暖色系アクセント。',
    'agenda': '番号付きリスト形式。フロー図やタイムライン風デザイン。',
    'references': '書籍・論文リスト風。落ち着いた学術的デザイン。本棚シルエット。',
    'content': 'プロフェッショナルなプレゼンテーションデザイン。情報が整理され読みやすいレイアウト。',
}


def generate_prompt(slide: dict) -> str:
    """1スライド分のAPI用詳細プロンプトを生成"""
    slide_type = detect_slide_type(slide['content'])
    design_hint = DESIGN_HINTS.get(slide_type, DESIGN_HINTS['content'])
    
    prompt = f"""以下の内容を含む、完成されたプレゼンテーションスライド画像を1枚生成してください。16:9横向き。

タイトル: {slide['title']}

内容:
{slide['content']}

デザイン要件:
- {design_hint}
- 日本語テキストを画像内に直接レンダリングすること
- タイトルは大きく目立つように配置
- 内容テキストは読みやすいフォントサイズで配置
- ダーク系の洗練された背景（ダークブルー、ダークティール、ダークパープルなど）
- テキストは白で大きく読みやすく
- プロフェッショナルで教育向けのデザイン
"""
    return prompt.strip()


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/generate_api_prompts.py <marp_md_path>")
        sys.exit(1)
    
    md_path = Path(sys.argv[1])
    if not md_path.exists():
        print(f"ファイルが見つかりません: {md_path}")
        sys.exit(1)
    
    slides = parse_marp_slides(md_path)
    print(f"スライド数: {len(slides)}")
    
    # プロンプト生成
    prompts = {}
    for slide in slides:
        prompt = generate_prompt(slide)
        prompts[str(slide['number'])] = prompt
        print(f"  スライド{slide['number']}: {slide['title'][:40]}")
    
    # 出力
    output_path = md_path.parent / 'api_prompts.json'
    output_path.write_text(json.dumps(prompts, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"\n出力: {output_path}")
    print(f"プロンプト数: {len(prompts)}")


if __name__ == '__main__':
    main()
