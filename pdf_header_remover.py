#!/usr/bin/env python3
"""
既存のテキストファイルからヘッダー/フッター/章タイトルを除去
PDFから抽出済みのテキストファイルの後処理用
"""

import re
import sys
from pathlib import Path
import argparse
from typing import List, Set, Tuple
from collections import Counter

class HeaderFooterRemover:
    """ヘッダー/フッター除去クラス"""
    
    def __init__(self):
        self.chapter_patterns = [
            # 日本語の章パターン
            r'^第[一二三四五六七八九十\d]+章',
            r'^第[一二三四五六七八九十\d]+節',
            r'^第[一二三四五六七八九十\d]+部',
            r'^\d+\.\d+',  # 1.1, 2.3 など
            r'^\d+章',
            r'^\d+節',
            
            # 英語の章パターン
            r'^Chapter\s+\d+',
            r'^Section\s+\d+',
            r'^Part\s+\d+',
            
            # ページ番号パターン
            r'^\s*\d+\s*$',  # 数字のみ
            r'^\s*[-‐]\s*\d+\s*[-‐]\s*$',  # -1-, -23- など
            r'^\s*\[\s*\d+\s*\]\s*$',  # [1], [23] など
            r'^\s*\(\s*\d+\s*\)\s*$',  # (1), (23) など
            r'^P\.\s*\d+',  # P.1, P.23 など
            r'^p\.\s*\d+',  # p.1, p.23 など
            r'^\d+\s*ページ',  # 1ページ など
            r'^ページ\s*\d+',  # ページ1 など
        ]
        
    def detect_repeated_lines(self, files: List[Path]) -> Set[str]:
        """
        複数ファイルで繰り返される行を検出
        """
        line_counter = Counter()
        total_files = len(files)
        
        for file_path in files:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            # 各ファイルの最初と最後の行を収集
            unique_lines = set()
            
            # 最初の5行
            for line in lines[:5]:
                cleaned = line.strip()
                if cleaned and len(cleaned) < 100:  # 長すぎる行は本文の可能性
                    unique_lines.add(cleaned)
            
            # 最後の5行
            for line in lines[-5:]:
                cleaned = line.strip()
                if cleaned and len(cleaned) < 100:
                    unique_lines.add(cleaned)
            
            # カウント
            for line in unique_lines:
                line_counter[line] += 1
        
        # 半数以上のファイルで出現する行を抽出
        repeated_lines = set()
        threshold = total_files * 0.4  # 40%以上で出現
        
        for line, count in line_counter.items():
            if count >= threshold:
                repeated_lines.add(line)
                print(f"  繰り返しパターン検出: '{line[:50]}...' ({count}/{total_files}ファイル)")
        
        return repeated_lines
    
    def is_chapter_title(self, line: str) -> bool:
        """
        章タイトルかどうか判定
        """
        line = line.strip()
        
        # パターンマッチング
        for pattern in self.chapter_patterns:
            if re.match(pattern, line):
                return True
        
        # 短い行で特定のキーワードを含む
        if len(line) < 30:
            keywords = ['章', '節', '部', 'Chapter', 'Section', 'Part']
            if any(keyword in line for keyword in keywords):
                # 前後の文脈を考慮（実装簡略化のため、ここでは長さのみ）
                return True
        
        return False
    
    def clean_single_file(self, file_path: Path, repeated_lines: Set[str], 
                         remove_chapters: bool = True) -> str:
        """
        単一ファイルをクリーニング
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        cleaned_lines = []
        skip_next = False
        prev_line = ""
        
        for i, line in enumerate(lines):
            # スキップフラグが立っている場合
            if skip_next:
                skip_next = False
                continue
            
            stripped = line.strip()
            
            # 空行は保持（ただし連続は1つに）
            if not stripped:
                if cleaned_lines and not cleaned_lines[-1].strip():
                    continue
                cleaned_lines.append(line)
                prev_line = line
                continue
            
            # 繰り返し行（ヘッダー/フッター）を除去
            if stripped in repeated_lines:
                continue
            
            # 章タイトルを除去
            if remove_chapters and self.is_chapter_title(stripped):
                # 次の行が空行なら一緒に除去
                if i + 1 < len(lines) and not lines[i + 1].strip():
                    skip_next = True
                continue
            
            # ページ番号のみの行を除去
            if re.match(r'^\s*\d+\s*$', stripped):
                continue
            
            # 同じ短い行が近くで繰り返される場合（章タイトルの重複）
            if len(stripped) < 30 and prev_line.strip() == stripped:
                continue
            
            cleaned_lines.append(line)
            prev_line = line
        
        return ''.join(cleaned_lines)
    
    def process_directory(self, input_dir: Path, output_dir: Path, 
                         remove_chapters: bool = True):
        """
        ディレクトリ内の全テキストファイルを処理
        """
        # テキストファイルを収集
        text_files = sorted(input_dir.glob('*.txt'))
        
        if not text_files:
            print("エラー: テキストファイルが見つかりません")
            return
        
        print(f"{len(text_files)} 個のファイルを処理します")
        
        # 繰り返しパターンを検出
        print("\n繰り返しパターンを検出中...")
        repeated_lines = self.detect_repeated_lines(text_files)
        
        # 出力ディレクトリを作成
        output_dir.mkdir(exist_ok=True)
        
        # 各ファイルを処理
        print(f"\nファイルをクリーニング中...")
        for file_path in text_files:
            cleaned_text = self.clean_single_file(
                file_path, repeated_lines, remove_chapters
            )
            
            output_path = output_dir / file_path.name
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(cleaned_text)
            
            print(f"  ✓ {file_path.name}")
        
        print(f"\n完了: クリーンなファイルを {output_dir} に保存しました")

def main():
    parser = argparse.ArgumentParser(
        description="テキストファイルからヘッダー/フッター/章タイトルを除去",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  # ディレクトリ内の全ファイルを処理
  python pdf_header_remover.py ./pages -o ./clean_pages
  
  # 章タイトルは残す
  python pdf_header_remover.py ./pages -o ./clean_pages --keep-chapters
  
  # 単一ファイルを処理
  python pdf_header_remover.py input.txt -o output.txt
  
PDFから抽出したテキストのパターンを自動検出して除去します：
- 全ページで繰り返されるヘッダー/フッター
- ページ番号
- 章タイトル（第1章、Chapter 1 など）
- 重複する短い行
"""
    )
    
    parser.add_argument('input', help='入力ファイルまたはディレクトリ')
    parser.add_argument('-o', '--output', required=True,
                       help='出力ファイルまたはディレクトリ')
    parser.add_argument('--keep-chapters', action='store_true',
                       help='章タイトルを残す')
    
    args = parser.parse_args()
    
    input_path = Path(args.input)
    output_path = Path(args.output)
    
    if not input_path.exists():
        print(f"エラー: {input_path} が見つかりません")
        sys.exit(1)
    
    remover = HeaderFooterRemover()
    
    if input_path.is_dir():
        # ディレクトリ処理
        remover.process_directory(
            input_path, output_path, 
            remove_chapters=not args.keep_chapters
        )
    else:
        # 単一ファイル処理
        repeated_lines = set()  # 単一ファイルでは繰り返し検出しない
        
        cleaned_text = remover.clean_single_file(
            input_path, repeated_lines,
            remove_chapters=not args.keep_chapters
        )
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(cleaned_text)
        
        print(f"完了: {output_path} に保存しました")

if __name__ == "__main__":
    main()