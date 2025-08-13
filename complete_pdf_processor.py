#!/usr/bin/env python3
"""
完全版PDFテキスト処理スクリプト
PDF抽出 → ヘッダー/フッター除去 → 空白整形 → 音声変換 の統合
"""

import sys
import os
import re
from pathlib import Path
from typing import List, Set, Dict, Optional
from collections import Counter
import argparse

# 既存のモジュールをインポート（相対パス）
# text_formatter.py の関数を使用
sys.path.append(str(Path(__file__).parent))

def detect_repeated_patterns(text_files: List[Path]) -> Set[str]:
    """複数ファイルで繰り返されるパターンを検出"""
    line_counter = Counter()
    total_files = len(text_files)
    
    for file_path in text_files:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        unique_lines = set()
        
        # 最初と最後の行を収集
        for line in lines[:5] + lines[-5:]:
            cleaned = line.strip()
            if cleaned and len(cleaned) < 150:  # 適度な長さ
                unique_lines.add(cleaned)
        
        for line in unique_lines:
            line_counter[line] += 1
    
    # 40%以上のファイルで出現するパターン
    repeated_patterns = set()
    threshold = max(2, total_files * 0.4)
    
    for line, count in line_counter.items():
        if count >= threshold:
            repeated_patterns.add(line)
    
    return repeated_patterns

def is_sidebar_title(line: str) -> bool:
    """サイドバーのタイトル（章名など）かどうか判定"""
    line = line.strip()
    
    # 短い行で章・節・部を含む
    if len(line) <= 30:
        chapter_keywords = [
            '第', '章', '節', '部', 'Chapter', 'Section', 'Part', 
            '編', '項', '条', '款', '号'
        ]
        if any(keyword in line for keyword in chapter_keywords):
            return True
    
    # 数字だけの行（ページ番号）
    if re.match(r'^\s*\d+\s*$', line):
        return True
    
    # ページ番号のパターン
    page_patterns = [
        r'^\s*[-‐]\s*\d+\s*[-‐]\s*$',
        r'^\s*\[\s*\d+\s*\]\s*$',
        r'^\s*\(\s*\d+\s*\)\s*$',
        r'^P\.\s*\d+',
        r'^p\.\s*\d+',
        r'^\d+\s*ページ',
        r'^ページ\s*\d+',
    ]
    
    for pattern in page_patterns:
        if re.match(pattern, line):
            return True
    
    return False

def clean_extracted_text(text: str, repeated_patterns: Set[str]) -> str:
    """抽出されたテキストをクリーニング"""
    lines = text.split('\n')
    cleaned_lines = []
    prev_line = ""
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        
        # 空行の処理
        if not stripped:
            if cleaned_lines and cleaned_lines[-1].strip():
                cleaned_lines.append('')
            continue
        
        # PDFヘッダー情報をスキップ
        if (stripped.startswith('PDFファイル:') or 
            stripped.startswith('ページ番号:') or 
            stripped.startswith('=' * 10)):
            continue
        
        # 繰り返しパターンをスキップ
        if stripped in repeated_patterns:
            continue
        
        # サイドバータイトルをスキップ
        if is_sidebar_title(stripped):
            continue
        
        # 重複する短い行をスキップ
        if len(stripped) < 50 and stripped == prev_line.strip():
            continue
        
        cleaned_lines.append(line)
        prev_line = line
    
    # 連続する空行を1つに
    final_lines = []
    prev_empty = False
    for line in cleaned_lines:
        if not line.strip():
            if not prev_empty:
                final_lines.append('')
                prev_empty = True
        else:
            final_lines.append(line)
            prev_empty = False
    
    return '\n'.join(final_lines).strip()

def main():
    parser = argparse.ArgumentParser(
        description="統合PDF処理スクリプト",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
完全な処理フロー:
1. PDFからテキスト抽出
2. ヘッダー/フッター/章タイトルを自動除去
3. 空白の正規化
4. ページごとに保存

使用例:
  # 基本的な処理
  python complete_pdf_processor.py document.pdf
  
  # メールアドレスも除去
  python complete_pdf_processor.py document.pdf -r "user@example.com"
  
  # 章タイトルは残す
  python complete_pdf_processor.py document.pdf --keep-chapters
"""
    )
    
    parser.add_argument('input', help='PDFファイルまたはテキストディレクトリ')
    parser.add_argument('-o', '--output', help='出力ディレクトリ名')
    parser.add_argument('-r', '--remove', action='append', 
                       help='除去する文字列パターン（複数指定可）')
    parser.add_argument('--keep-chapters', action='store_true',
                       help='章タイトルを残す')
    
    args = parser.parse_args()
    
    input_path = Path(args.input)
    
    if not input_path.exists():
        print(f"エラー: {input_path} が見つかりません")
        sys.exit(1)
    
    # 出力ディレクトリの決定
    if args.output:
        output_dir = Path(args.output)
    else:
        output_dir = Path(f"{input_path.stem}_processed")
    
    # PDFファイルの場合は先にテキスト抽出
    if input_path.suffix.lower() == '.pdf':
        print("PDFからテキストを抽出中...")
        temp_dir = Path(f"{input_path.stem}_temp_pages")
        
        # pdf_to_txt.py を使用してテキスト抽出
        import subprocess
        cmd = ['uv', 'run', 'python', 'pdf_to_txt.py', str(input_path), '-p', str(temp_dir)]
        if args.remove:
            for pattern in args.remove:
                cmd.extend(['-r', pattern])
        
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            input_path = temp_dir
        except subprocess.CalledProcessError as e:
            print(f"エラー: PDF抽出に失敗しました: {e}")
            sys.exit(1)
    
    # テキストファイルを収集
    if input_path.is_dir():
        text_files = sorted(input_path.glob('*.txt'))
    else:
        text_files = [input_path]
    
    if not text_files:
        print("エラー: テキストファイルが見つかりません")
        sys.exit(1)
    
    print(f"{len(text_files)} 個のファイルを処理します")
    
    # 繰り返しパターンを検出
    print("ヘッダー/フッターパターンを検出中...")
    repeated_patterns = detect_repeated_patterns(text_files)
    
    if repeated_patterns:
        print(f"  {len(repeated_patterns)} 個のパターンを検出")
        for pattern in list(repeated_patterns)[:3]:
            print(f"    - {pattern[:50]}...")
    
    # 出力ディレクトリ作成
    output_dir.mkdir(exist_ok=True)
    
    # 各ファイルを処理
    print("\nファイルを処理中...")
    processed_count = 0
    
    for file_path in text_files:
        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read()
        
        # クリーニング
        cleaned_text = clean_extracted_text(text, repeated_patterns)
        
        # 空白整形（text_formatter の機能を使用）
        from text_formatter import TextFormatter
        formatter = TextFormatter()
        
        # 空白除去
        cleaned_text = formatter.remove_meaningless_spaces(cleaned_text)
        cleaned_text = formatter.clean_text(cleaned_text, aggressive=True)
        
        # 保存
        if cleaned_text.strip():
            output_file = output_dir / file_path.name
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(cleaned_text)
            
            print(f"  ✓ {file_path.name}")
            processed_count += 1
    
    print(f"\n完了: {processed_count} ファイルを {output_dir} に保存しました")
    
    # 一時ディレクトリの削除
    if 'temp_dir' in locals() and temp_dir.exists():
        import shutil
        shutil.rmtree(temp_dir)
        print(f"一時ディレクトリ {temp_dir} を削除しました")

if __name__ == "__main__":
    main()