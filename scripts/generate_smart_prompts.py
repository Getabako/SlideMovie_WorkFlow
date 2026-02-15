#!/usr/bin/env python3
"""
スマートプロンプト生成スクリプト

スライドの内容を詳細に分析し、適切な画像生成プロンプトを作成します。
"""

import os
import re
import sys
import json
import argparse
from pathlib import Path
from typing import List, Dict, Optional


class SlideContentAnalyzer:
    """スライド内容分析クラス"""

    # 技術キーワードと対応する画像コンセプト
    TECH_CONCEPTS = {
        # HTML関連
        'html': 'HTML code structure with brackets and tags on a dark screen, programming concept',
        'タグ': 'HTML tags visualization, code elements floating in digital space',
        '見出し': 'text hierarchy visualization with h1 h2 h3 headings, typography',
        '段落': 'paragraph text blocks, document structure illustration',
        'リスト': 'bullet points and numbered list visualization',
        'リンク': 'hyperlink chain connecting web pages, internet connectivity',
        'index.html': 'HTML file icon with code, web development',

        # CSS関連
        'css': 'CSS stylesheet code with colors and styles, web design',
        'スタイル': 'design styling palette, colors and fonts',
        'デザイン': 'modern web design mockup, creative layout',
        'レイアウト': 'grid layout visualization, responsive design',
        'フォント': 'typography showcase with different fonts',
        '色': 'color palette, gradient colors, design spectrum',
        'カラー': 'vibrant color wheel, design colors',
        'margin': 'CSS box model visualization with margins and padding',
        'padding': 'CSS spacing illustration',
        'flexbox': 'flexible box layout diagram',
        'grid': 'CSS grid layout structure',

        # JavaScript関連
        'javascript': 'JavaScript code on screen, dynamic programming',
        'js': 'JavaScript yellow logo with code',
        'プログラミング': 'programming code on multiple screens',
        '関数': 'function diagram with input output arrows',
        '変数': 'variable containers with data',
        'イベント': 'click and interaction events, user interface',
        'dom': 'DOM tree structure, HTML document hierarchy',
        'クリック': 'mouse click interaction, button press',
        'ボタン': 'interactive button UI element',

        # GitHub関連
        'github': 'GitHub octocat logo, version control',
        'git': 'Git branching diagram, version control',
        'リポジトリ': 'repository folder structure, code storage',
        'コミット': 'git commit history timeline',
        'プッシュ': 'upload arrow, cloud synchronization',
        'デプロイ': 'rocket launch deployment, going live',
        'pages': 'GitHub Pages hosting, website deployment',
        '公開': 'website going live, launch celebration',

        # Web一般
        'ウェブ': 'world wide web connectivity, global internet',
        'web': 'web browser window, internet browsing',
        'サイト': 'website mockup on devices',
        'ホームページ': 'homepage design mockup',
        'ブラウザ': 'web browser interface, Chrome Firefox Safari',
        'url': 'URL address bar, web address',
        'インターネット': 'global internet network visualization',

        # ポートフォリオ関連
        'ポートフォリオ': 'professional portfolio showcase, creative work display',
        'プロフィール': 'personal profile card, about me section',
        '作品': 'creative works gallery, project showcase',
        '実績': 'achievement badges, accomplishment display',
        '自己紹介': 'personal introduction card, meeting illustration',
        '経歴': 'career timeline, professional journey',
        'スキル': 'skill icons and badges, competency display',

        # AI関連
        'ai': 'artificial intelligence brain, neural network',
        '人工知能': 'AI robot assistant, intelligent machine',
        'gemini': 'Gemini AI logo, Google AI',
        '生成': 'AI content generation, creative automation',
        '自動': 'automation gears, automatic process',

        # 講座・学習関連
        '講座': 'online learning classroom, educational setting',
        '学習': 'studying with books and laptop, learning concept',
        'コース': 'course pathway, learning journey',
        '目標': 'target goal, achievement aim',
        '完成': 'completion celebration, finished project',
        'ステップ': 'step by step progress, staircase advancement',
        '準備': 'preparation checklist, getting ready',
        '環境': 'development environment setup, tools installation',
    }

    # スライドタイプと対応する画像スタイル
    SLIDE_TYPES = {
        'title': 'hero image, bold and impactful, cinematic',
        'introduction': 'welcoming atmosphere, friendly and approachable',
        'concept': 'abstract conceptual visualization, idea representation',
        'tutorial': 'step-by-step guide, instructional diagram',
        'code': 'code editor screenshot style, dark theme programming',
        'demo': 'live demonstration, hands-on practical',
        'summary': 'key points recap, bullet point visualization',
        'conclusion': 'celebration, achievement, completion',
        'resources': 'resource library, tools collection',
    }

    def __init__(self, md_file: str):
        """初期化"""
        self.md_file = Path(md_file)

    def parse_slides(self) -> List[Dict]:
        """マークダウンファイルからスライドを解析"""
        with open(self.md_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # スライドを分割
        slides = content.split('\n---\n')

        slide_data = []
        content_slide_index = 0

        for i, slide in enumerate(slides):
            # ヘッダー（marp設定）をスキップ
            if i == 0 and 'marp: true' in slide:
                continue

            content_slide_index += 1

            # タイトルを抽出
            title_match = re.search(r'^#+ (.+)$', slide, re.MULTILINE)
            title = title_match.group(1).strip() if title_match else ""

            # 箇条書きを抽出
            bullets = re.findall(r'^[-*•]\s+(.+)$', slide, re.MULTILINE)

            # コードブロックを検出
            has_code = bool(re.search(r'```', slide))
            code_language = ""
            code_match = re.search(r'```(\w+)', slide)
            if code_match:
                code_language = code_match.group(1)

            # 数字付きリストを抽出
            numbered_items = re.findall(r'^\d+\.\s+(.+)$', slide, re.MULTILINE)

            # キーワードを抽出（太字、リンクテキストなど）
            bold_text = re.findall(r'\*\*(.+?)\*\*', slide)

            slide_data.append({
                'index': content_slide_index,
                'raw_content': slide.strip(),
                'title': title,
                'bullets': bullets,
                'numbered_items': numbered_items,
                'has_code': has_code,
                'code_language': code_language,
                'bold_keywords': bold_text,
            })

        return slide_data

    def detect_slide_type(self, slide: Dict) -> str:
        """スライドのタイプを検出"""
        title = slide['title'].lower()
        content = slide['raw_content'].lower()

        # タイトルスライド
        if slide['index'] == 1 or '講座' in title or 'コース' in title:
            return 'title'

        # コードスライド
        if slide['has_code']:
            return 'code'

        # 目次・イントロダクション
        if '目次' in title or 'はじめ' in title or '自己紹介' in title:
            return 'introduction'

        # リソース・リンク集
        if 'リンク' in title or 'リソース' in title or 'おまけ' in title:
            return 'resources'

        # まとめ・振り返り
        if 'まとめ' in title or '振り返り' in title or 'ポイント' in title:
            return 'summary'

        # 完了・お疲れ様
        if 'お疲れ' in title or '完了' in title or '完成' in title:
            return 'conclusion'

        # 実践・デモ
        if '実践' in title or 'やってみ' in title or '作成' in title:
            return 'demo'

        # コンセプト説明
        if '?' in title or 'とは' in title or '理解' in title:
            return 'concept'

        # デフォルトはチュートリアル
        return 'tutorial'

    def needs_instructor(self, slide: Dict) -> bool:
        """講師を表示すべきスライドかどうかを判定"""
        title = slide['title'].lower()
        content = slide['raw_content'].lower()
        slide_type = self.detect_slide_type(slide)

        # 講義場面として講師を表示するスライドタイプ
        instructor_types = ['title', 'introduction', 'concept', 'summary', 'conclusion']

        # 講義関連キーワード
        lecture_keywords = ['講座', '学習', 'コース', '目標', 'まとめ', 'ポイント',
                           'お疲れ', '完成', '振り返り', 'はじめ', '紹介', '説明',
                           '全体像', '構成', 'コマ目', 'おまけ', '次回', '今回']

        # スライドタイプで判定
        if slide_type in instructor_types:
            return True

        # キーワードで判定
        for keyword in lecture_keywords:
            if keyword in title or keyword in content:
                return True

        return False

    def extract_keywords(self, slide: Dict) -> List[str]:
        """スライドからキーワードを抽出"""
        keywords = []

        # タイトルから
        keywords.append(slide['title'])

        # 箇条書きから
        keywords.extend(slide['bullets'][:3])  # 最初の3つ

        # 太字キーワード
        keywords.extend(slide['bold_keywords'])

        # コード言語
        if slide['code_language']:
            keywords.append(slide['code_language'])

        return keywords

    def generate_prompt(self, slide: Dict) -> str:
        """スライドの内容に基づいて画像生成プロンプトを作成"""
        slide_type = self.detect_slide_type(slide)
        keywords = self.extract_keywords(slide)

        # キーワードから技術コンセプトを検索
        concepts = []
        for keyword in keywords:
            keyword_lower = keyword.lower()
            for tech_key, concept in self.TECH_CONCEPTS.items():
                if tech_key in keyword_lower:
                    concepts.append(concept)
                    break

        # ユニークなコンセプトのみ
        concepts = list(dict.fromkeys(concepts))[:3]

        # プロンプトを構築
        style = self.SLIDE_TYPES.get(slide_type, 'professional presentation')

        if concepts:
            main_concept = concepts[0]
            prompt = f"Create a professional illustration: {main_concept}. Style: {style}. "
        else:
            # デフォルトプロンプト
            prompt = f"Create a professional illustration for a presentation about: {slide['title']}. Style: {style}. "

        # 共通の画像要件を追加
        prompt += "Modern flat design, clean composition, vibrant colors, suitable for educational presentation. No text or words in the image. High quality, 3:4 vertical aspect ratio."

        return prompt

    def process_all_slides(self) -> List[Dict]:
        """すべてのスライドを処理してプロンプトを生成"""
        slides = self.parse_slides()

        results = []
        for slide in slides:
            prompt = self.generate_prompt(slide)
            needs_instr = self.needs_instructor(slide)
            results.append({
                'slide_number': slide['index'],
                'title': slide['title'],
                'slide_type': self.detect_slide_type(slide),
                'keywords': self.extract_keywords(slide),
                'prompt': prompt,
                'needs_instructor': needs_instr,
            })

        return results


def main():
    parser = argparse.ArgumentParser(
        description='Generate smart image prompts from slide content'
    )
    parser.add_argument('md_file', help='Path to markdown file')
    parser.add_argument(
        '--output',
        help='Output JSON file for prompts',
        default=None
    )

    args = parser.parse_args()

    analyzer = SlideContentAnalyzer(args.md_file)
    prompts = analyzer.process_all_slides()

    # 出力ファイルパスを決定
    if args.output:
        output_path = Path(args.output)
    else:
        md_path = Path(args.md_file)
        output_path = md_path.parent / 'image_prompts.json'

    # JSONとして保存
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump({
            'source_file': str(args.md_file),
            'total_slides': len(prompts),
            'prompts': prompts
        }, f, ensure_ascii=False, indent=2)

    print(f"Generated {len(prompts)} prompts")
    print(f"Output saved to: {output_path}")

    # サンプル出力
    print("\n=== Sample Prompts ===")
    for p in prompts[:5]:
        print(f"\nSlide {p['slide_number']}: {p['title']}")
        print(f"  Type: {p['slide_type']}")
        print(f"  Prompt: {p['prompt'][:100]}...")


if __name__ == '__main__':
    main()
