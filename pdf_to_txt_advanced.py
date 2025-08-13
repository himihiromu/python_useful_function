#!/usr/bin/env python3
"""
改良版PDFテキスト抽出スクリプト
ヘッダー、フッター、サイドバーのタイトルを自動除去
"""

import sys
import os
import re
from pypdf import PdfReader
from pathlib import Path
from typing import List, Tuple, Optional, Dict
from collections import Counter
import argparse

class AdvancedPDFExtractor:
    """高度なPDFテキスト抽出クラス"""
    
    def __init__(self):
        self.common_headers = []
        self.common_footers = []
        self.page_patterns = {}
        
    def extract_with_layout(self, pdf_path: str) -> Dict[int, Dict]:
        """
        レイアウト情報を含めてテキストを抽出
        """
        reader = PdfReader(pdf_path)
        pages_data = {}
        
        for page_num, page in enumerate(reader.pages):
            try:
                # テキストとその位置情報を取得
                text_content = []
                
                # 基本的なテキスト抽出
                text = page.extract_text()
                
                # より詳細な抽出を試みる（pypdfの拡張機能を使用）
                if hasattr(page, 'extract_text_with_layout'):
                    # レイアウト情報付きで抽出（将来的な機能）
                    layout_text = page.extract_text_with_layout()
                    text_content = self.parse_layout_text(layout_text)
                else:
                    # 通常のテキストを行単位で分割
                    text_content = text.split('\n') if text else []
                
                pages_data[page_num] = {
                    'text': text,
                    'lines': text_content,
                    'page_num': page_num + 1
                }
                
            except Exception as e:
                print(f"警告: ページ {page_num + 1} の処理中にエラー: {e}", file=sys.stderr)
                pages_data[page_num] = {
                    'text': '',
                    'lines': [],
                    'page_num': page_num + 1
                }
        
        return pages_data
    
    def detect_repeated_patterns(self, pages_data: Dict) -> Dict[str, int]:
        """
        全ページで繰り返されるパターンを検出（ヘッダー/フッター候補）
        """
        line_counter = Counter()
        
        # 各ページの最初と最後の数行を収集
        for page_num, data in pages_data.items():
            lines = data['lines']
            if not lines:
                continue
            
            # 最初の3行と最後の3行を候補として収集
            for line in lines[:3] + lines[-3:]:
                if line and len(line.strip()) > 0:
                    # 数字だけの行やページ番号っぽいものも記録
                    normalized = self.normalize_for_comparison(line.strip())
                    if normalized:
                        line_counter[normalized] += 1
        
        # 全ページ数の半分以上で出現するパターンを検出
        total_pages = len(pages_data)
        repeated_patterns = {}
        
        for pattern, count in line_counter.items():
            if count >= total_pages * 0.5:  # 50%以上のページで出現
                repeated_patterns[pattern] = count
        
        return repeated_patterns
    
    def normalize_for_comparison(self, text: str) -> str:
        """
        比較のためにテキストを正規化
        ページ番号を含む行も検出できるように
        """
        # ページ番号パターンを一般化
        text = re.sub(r'\d+', '[NUM]', text)
        
        # 日付パターンを一般化
        text = re.sub(r'\d{4}[年/-]\d{1,2}[月/-]\d{1,2}日?', '[DATE]', text)
        
        # 余分な空白を正規化
        text = ' '.join(text.split())
        
        return text
    
    def identify_header_footer_patterns(self, pages_data: Dict) -> Tuple[List[str], List[str]]:
        """
        ヘッダーとフッターのパターンを特定
        """
        headers = []
        footers = []
        
        # 繰り返しパターンを検出
        repeated = self.detect_repeated_patterns(pages_data)
        
        # 各パターンがヘッダーかフッターか判定
        for pattern in repeated.keys():
            occurrences_top = 0
            occurrences_bottom = 0
            
            for page_num, data in pages_data.items():
                lines = data['lines']
                if not lines:
                    continue
                
                # 最初の3行にあるか
                for line in lines[:3]:
                    if self.normalize_for_comparison(line.strip()) == pattern:
                        occurrences_top += 1
                        break
                
                # 最後の3行にあるか
                for line in lines[-3:]:
                    if self.normalize_for_comparison(line.strip()) == pattern:
                        occurrences_bottom += 1
                        break
            
            # 位置に基づいて分類
            if occurrences_top > occurrences_bottom:
                headers.append(pattern)
            else:
                footers.append(pattern)
        
        return headers, footers
    
    def detect_sidebar_titles(self, lines: List[str]) -> List[int]:
        """
        サイドバーのタイトル（章名など）を検出
        短い行で、前後に空行があるものを候補とする
        """
        sidebar_indices = []
        
        for i, line in enumerate(lines):
            if not line.strip():
                continue
            
            # 短い行（20文字以下）で、章番号や「第」を含む
            if len(line.strip()) <= 20:
                if any(keyword in line for keyword in ['第', '章', 'Chapter', 'Section', '節']):
                    # 前後が空行または存在しない
                    prev_empty = (i == 0) or (not lines[i-1].strip())
                    next_empty = (i == len(lines)-1) or (not lines[i+1].strip())
                    
                    if prev_empty or next_empty:
                        sidebar_indices.append(i)
            
            # ページ番号のみの行
            if re.match(r'^\s*\d+\s*$', line) or re.match(r'^\s*[-‐]\s*\d+\s*[-‐]\s*$', line):
                sidebar_indices.append(i)
        
        return sidebar_indices
    
    def clean_page_text(self, lines: List[str], headers: List[str], footers: List[str]) -> List[str]:
        """
        ページからヘッダー、フッター、サイドバーを除去
        """
        if not lines:
            return []
        
        cleaned_lines = []
        sidebar_indices = self.detect_sidebar_titles(lines)
        
        for i, line in enumerate(lines):
            # サイドバーとして検出された行はスキップ
            if i in sidebar_indices:
                continue
            
            normalized = self.normalize_for_comparison(line.strip())
            
            # ヘッダー/フッターパターンと一致する行はスキップ
            if normalized in headers or normalized in footers:
                continue
            
            # ページ番号のみの行をスキップ
            if re.match(r'^\s*\d+\s*$', line.strip()):
                continue
            
            # 章タイトルの重複を除去（同じ章タイトルが複数回出現する場合）
            if i > 0 and len(line.strip()) <= 30:
                # 前の数行に同じテキストがないか確認
                duplicate = False
                for j in range(max(0, i-5), i):
                    if lines[j].strip() == line.strip():
                        duplicate = True
                        break
                if duplicate:
                    continue
            
            cleaned_lines.append(line)
        
        return cleaned_lines
    
    def extract_clean_text(self, pdf_path: str, 
                          remove_patterns: List[str] = None,
                          auto_detect: bool = True) -> Dict[int, str]:
        """
        クリーンなテキストを抽出
        
        Args:
            pdf_path: PDFファイルパス
            remove_patterns: 追加で除去するパターン
            auto_detect: ヘッダー/フッターの自動検出を行うか
        
        Returns:
            ページ番号をキーとしたクリーンなテキストの辞書
        """
        # レイアウト情報付きで抽出
        pages_data = self.extract_with_layout(pdf_path)
        
        # ヘッダー/フッターの自動検出
        headers = []
        footers = []
        if auto_detect:
            headers, footers = self.identify_header_footer_patterns(pages_data)
            
            if headers:
                print(f"検出されたヘッダーパターン: {len(headers)}個")
                for h in headers[:3]:
                    print(f"  - {h[:50]}...")
            
            if footers:
                print(f"検出されたフッターパターン: {len(footers)}個")
                for f in footers[:3]:
                    print(f"  - {f[:50]}...")
        
        # 各ページをクリーニング
        clean_pages = {}
        for page_num, data in pages_data.items():
            lines = data['lines']
            
            # ヘッダー/フッター/サイドバーを除去
            cleaned_lines = self.clean_page_text(lines, headers, footers)
            
            # 追加の除去パターンを適用
            if remove_patterns:
                text = '\n'.join(cleaned_lines)
                for pattern in remove_patterns:
                    if pattern.startswith('regex:'):
                        text = re.sub(pattern[6:], '', text)
                    else:
                        text = text.replace(pattern, '')
                cleaned_lines = text.split('\n')
            
            # 空行を整理
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
            
            clean_pages[page_num] = '\n'.join(final_lines).strip()
        
        return clean_pages

def main():
    parser = argparse.ArgumentParser(
        description="高度なPDFテキスト抽出（ヘッダー/フッター/サイドバー自動除去）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  # 基本的な使用（自動検出）
  python pdf_to_txt_advanced.py document.pdf
  
  # ページごとに保存
  python pdf_to_txt_advanced.py document.pdf -p
  
  # 自動検出を無効化
  python pdf_to_txt_advanced.py document.pdf --no-auto-detect
  
  # 追加の除去パターン指定
  python pdf_to_txt_advanced.py document.pdf -r "Copyright" -r "All rights reserved"
  
  # 章タイトルの重複除去を強化
  python pdf_to_txt_advanced.py document.pdf --aggressive
"""
    )
    
    parser.add_argument('pdf_file', help='PDFファイルパス')
    parser.add_argument('-p', '--pages', action='store_true',
                       help='ページごとに別ファイルに保存')
    parser.add_argument('-o', '--output', help='出力先')
    parser.add_argument('-r', '--remove', action='append',
                       help='除去する文字列パターン（複数指定可）')
    parser.add_argument('--no-auto-detect', action='store_true',
                       help='ヘッダー/フッターの自動検出を無効化')
    parser.add_argument('--aggressive', action='store_true',
                       help='より積極的な除去（短い繰り返し行も除去）')
    
    args = parser.parse_args()
    
    # PDFファイルの存在確認
    if not os.path.exists(args.pdf_file):
        print(f"エラー: PDFファイル '{args.pdf_file}' が見つかりません。", file=sys.stderr)
        sys.exit(1)
    
    # 抽出器を初期化
    extractor = AdvancedPDFExtractor()
    
    # テキスト抽出
    print(f"PDFを解析中: {args.pdf_file}")
    clean_pages = extractor.extract_clean_text(
        args.pdf_file,
        remove_patterns=args.remove,
        auto_detect=not args.no_auto_detect
    )
    
    # 出力
    if args.pages:
        # ページごとに保存
        if args.output:
            output_dir = Path(args.output)
        else:
            pdf_name = Path(args.pdf_file).stem
            output_dir = Path(f"{pdf_name}_clean_pages")
        
        output_dir.mkdir(exist_ok=True)
        
        saved_count = 0
        for page_num, text in clean_pages.items():
            if text.strip():
                output_file = output_dir / f"page_{page_num + 1:04d}.txt"
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(f"ページ番号: {page_num + 1}\n")
                    f.write("=" * 50 + "\n\n")
                    f.write(text)
                print(f"  ページ {page_num + 1} → {output_file.name}")
                saved_count += 1
        
        print(f"\n完了: {saved_count} ページを {output_dir} に保存しました。")
        
    else:
        # 1つのファイルに保存
        if args.output:
            output_file = args.output
        else:
            output_file = Path(args.pdf_file).stem + "_clean.txt"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            for page_num, text in clean_pages.items():
                if text.strip():
                    f.write(f"\n===== ページ {page_num + 1} =====\n\n")
                    f.write(text)
                    f.write("\n")
        
        print(f"\nテキストを {output_file} に保存しました。")

if __name__ == "__main__":
    main()