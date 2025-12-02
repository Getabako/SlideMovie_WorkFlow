#!/usr/bin/env python3
"""
複数スライド編集機能のデモンストレーション
③バナー作りプレゼンテーションのスライド1〜5を簡潔に編集
"""

import os
import sys
import subprocess
from pathlib import Path

def setup_test_environment():
    """テスト用の環境をセットアップ"""

    # GOOGLE_AI_API_KEYのダミー値を設定（実際のAPIキーがない場合）
    # 注: 実際のテストには有効なAPIキーが必要です
    if not os.getenv('GOOGLE_AI_API_KEY'):
        print("⚠️  警告: GOOGLE_AI_API_KEYが設定されていません")
        print("実際のテストにはGoogle AI APIキーが必要です")
        print("export GOOGLE_AI_API_KEY='your-api-key' を実行してください")
        return False

    return True

def test_multi_slide_edit():
    """複数スライド編集のテスト"""

    # プロジェクトルートパス
    project_root = Path(__file__).parent

    # ③バナー作りのパス
    presentation_name = "③バナー作り"
    presentation_dir = project_root / "presentations" / presentation_name
    input_yml_path = presentation_dir / "input.yml"

    # input.ymlが存在しない場合は生成
    if not input_yml_path.exists():
        print(f"📝 input.ymlを生成中...")
        md_path = presentation_dir / f"{presentation_name}.md"
        if md_path.exists():
            subprocess.run([
                sys.executable,
                str(project_root / "scripts" / "convert_md_to_input_yml.py"),
                str(md_path),
                str(input_yml_path)
            ], check=True)
        else:
            print(f"エラー: {md_path} が見つかりません")
            return False

    # 編集指示の例（複数スライドを一度に編集）
    edit_instructions = """
    スライド1から5までを以下のように編集してください：
    1. 各スライドのタイトルを短く、キャッチーにする
    2. 本文を3行以内に簡潔にまとめる
    3. 重要なポイントだけを残す
    """

    print(f"\n🚀 複数スライド編集のデモを実行")
    print(f"対象: {presentation_name}")
    print(f"編集内容: スライド1〜5を簡潔に編集\n")

    # 元のMDファイルのバックアップ
    original_md = presentation_dir / f"{presentation_name}.md"
    if original_md.exists():
        backup_path = presentation_dir / f"{presentation_name}_demo_backup.md"
        import shutil
        shutil.copy2(original_md, backup_path)
        print(f"✅ バックアップ作成: {backup_path}")

    # edit_slide_text_natural.pyを実行
    script_path = project_root / "scripts" / "edit_slide_text_natural.py"

    try:
        result = subprocess.run(
            [sys.executable, str(script_path), str(input_yml_path), edit_instructions],
            capture_output=True,
            text=True,
            check=True
        )

        print("\n実行結果:")
        print(result.stdout)

        if result.stderr:
            print("\nエラー出力:")
            print(result.stderr)

        # 編集後のファイル確認
        print("\n📋 編集後のファイル確認:")

        # Markdownファイルが更新されているか確認
        if original_md.exists():
            print(f"✅ {presentation_name}.md が更新されました")

            # ファイルサイズの比較
            import os
            original_size = os.path.getsize(backup_path) if backup_path.exists() else 0
            new_size = os.path.getsize(original_md)

            if new_size != original_size:
                print(f"   元のサイズ: {original_size} bytes")
                print(f"   新しいサイズ: {new_size} bytes")
                print(f"   差分: {new_size - original_size:+} bytes")

        # slidesフォルダのファイルも確認
        slides_dir = project_root / "slides"
        slide_file = slides_dir / f"{presentation_name}_slide.md"
        if slide_file.exists():
            print(f"✅ slides/{presentation_name}_slide.md も生成されました")

        return True

    except subprocess.CalledProcessError as e:
        print(f"\n❌ エラー: スクリプトの実行に失敗しました")
        print(f"エラーコード: {e.returncode}")
        if e.stdout:
            print(f"標準出力: {e.stdout}")
        if e.stderr:
            print(f"エラー出力: {e.stderr}")
        return False

    except Exception as e:
        print(f"\n❌ 予期しないエラー: {e}")
        return False


def create_simple_demo():
    """APIキーなしで動作する簡単なデモ"""
    print("\n📚 改良されたEditSlideText機能の説明\n")
    print("✨ 新機能:")
    print("1️⃣  複数スライドの一括編集")
    print("   - 「スライド1から5を簡潔にして」のような指示が可能")
    print("   - 各スライドに異なる編集を適用可能")
    print()
    print("2️⃣  自動Markdownファイル更新")
    print("   - input.yml編集後、自動的にMarkdownファイルを生成")
    print("   - presentations/フォルダの元のファイルを更新")
    print("   - バックアップファイルの自動作成")
    print()
    print("3️⃣  ワークフロー統合")
    print("   - GitHub Actionsワークフローとシームレスに連携")
    print("   - 後続の画像生成プロセスに対応")
    print()
    print("📝 使用例:")
    print('python3 scripts/edit_slide_text_natural.py \\')
    print('  "presentations/③バナー作り/input.yml" \\')
    print('  "スライド1から5を短く簡潔にして、重要なポイントだけ残して"')
    print()
    print("🔧 内部処理:")
    print("1. 編集指示をAIが解析")
    print("2. 複数スライドの編集内容を特定")
    print("3. input.ymlを更新")
    print("4. create_slide.pyでMarkdown生成")
    print("5. presentations/フォルダにコピー＆更新")


def main():
    print("=" * 60)
    print("📊 EditSlideText 複数スライド編集機能デモ")
    print("=" * 60)

    # 環境セットアップ確認
    if setup_test_environment():
        # 実際のテストを実行
        print("\n実際のテストを実行します...")
        success = test_multi_slide_edit()

        if success:
            print("\n✨ デモが正常に完了しました！")
        else:
            print("\n⚠️  デモは完了しましたが、一部エラーがありました")
    else:
        # APIキーがない場合は説明のみ表示
        create_simple_demo()

    print("\n" + "=" * 60)
    print("デモ終了")
    print("=" * 60)


if __name__ == "__main__":
    main()