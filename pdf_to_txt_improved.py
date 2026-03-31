#!/usr/bin/env python3
"""
改良版PDFテキスト抽出スクリプト
pdfplumberを使用して日本語PDFの文字化けを解決
"""

import sys
import os
import re
from pathlib import Path

# 複数のPDFライブラリを試す
try:
    import pdfplumber
    USE_PDFPLUMBER = True
except ImportError:
    USE_PDFPLUMBER = False

try:
    from pypdf import PdfReader
    USE_PYPDF = True
except ImportError:
    USE_PYPDF = False

def extract_with_pdfplumber(pdf_path):
    """pdfplumberを使用してテキストを抽出"""
    all_text = []
    
    with pdfplumber.open(pdf_path) as pdf:
        number_of_pages = len(pdf.pages)
        print(f"総ページ数: {number_of_pages} (pdfplumber使用)")
        
        for page_num, page in enumerate(pdf.pages):
            try:
                text = page.extract_text()
                
                if text and text.strip():
                    # 改行の正規化
                    text = text.replace('\r\n', '\n').replace('\r', '\n')
                    
                    # 連続する空白行を1つにまとめる
                    lines = text.split('\n')
                    cleaned_lines = []
                    prev_empty = False
                    
                    for line in lines:
                        if line.strip():
                            cleaned_lines.append(line)
                            prev_empty = False
                        elif not prev_empty:
                            cleaned_lines.append('')
                            prev_empty = True
                    
                    cleaned_text = '\n'.join(cleaned_lines)
                    
                    all_text.append(f"\n===== ページ {page_num + 1} =====\n")
                    all_text.append(cleaned_text)
                else:
                    all_text.append(f"\n===== ページ {page_num + 1} (テキストなし) =====\n")
                    
            except Exception as e:
                print(f"警告: ページ {page_num + 1} の処理中にエラーが発生しました: {e}", file=sys.stderr)
                all_text.append(f"\n===== ページ {page_num + 1} (エラー) =====\n")
    
    return all_text, number_of_pages

def extract_with_pypdf(pdf_path):
    """pypdfを使用してテキストを抽出（フォールバック）"""
    all_text = []
    
    reader = PdfReader(pdf_path)
    number_of_pages = len(reader.pages)
    print(f"総ページ数: {number_of_pages} (pypdf使用)")
    
    for page_num in range(number_of_pages):
        try:
            page = reader.pages[page_num]
            text = page.extract_text()
            
            if text and text.strip():
                # 改行の正規化
                text = text.replace('\r\n', '\n').replace('\r', '\n')
                
                # 連続する空白行を1つにまとめる
                lines = text.split('\n')
                cleaned_lines = []
                prev_empty = False
                
                for line in lines:
                    if line.strip():
                        cleaned_lines.append(line)
                        prev_empty = False
                    elif not prev_empty:
                        cleaned_lines.append('')
                        prev_empty = True
                
                cleaned_text = '\n'.join(cleaned_lines)
                
                all_text.append(f"\n===== ページ {page_num + 1} =====\n")
                all_text.append(cleaned_text)
            else:
                all_text.append(f"\n===== ページ {page_num + 1} (テキストなし) =====\n")
                
        except Exception as e:
            print(f"警告: ページ {page_num + 1} の処理中にエラーが発生しました: {e}", file=sys.stderr)
            all_text.append(f"\n===== ページ {page_num + 1} (エラー) =====\n")
    
    return all_text, number_of_pages

def pdf_to_text(pdf_path, output_mode='stdout', output_path=None, remove_patterns=None):
    """
    PDFファイルからテキストを抽出する関数
    
    Args:
        pdf_path: PDFファイルのパス
        output_mode: 出力モード ('stdout', 'single', 'page')
        output_path: 出力先のパス
        remove_patterns: 除去する文字列のパターンのリスト
    """
    try:
        # まずpdfplumberを試す
        if USE_PDFPLUMBER:
            try:
                all_text, number_of_pages = extract_with_pdfplumber(pdf_path)
                print("pdfplumberでの抽出に成功しました")
            except Exception as e:
                print(f"pdfplumberでエラーが発生しました: {e}")
                if USE_PYPDF:
                    print("pypdfにフォールバックします...")
                    all_text, number_of_pages = extract_with_pypdf(pdf_path)
                else:
                    raise
        elif USE_PYPDF:
            all_text, number_of_pages = extract_with_pypdf(pdf_path)
        else:
            print("エラー: pdfplumberまたはpypdfをインストールしてください", file=sys.stderr)
            print("インストール: uv pip install pdfplumber pypdf", file=sys.stderr)
            sys.exit(1)
        
        # 特定の文字列を除去
        if remove_patterns:
            processed_text = []
            for text_part in all_text:
                for pattern in remove_patterns:
                    if pattern.startswith('regex:'):
                        regex_pattern = pattern[6:]
                        text_part = re.sub(regex_pattern, '', text_part)
                    else:
                        text_part = text_part.replace(pattern, '')
                processed_text.append(text_part)
            all_text = processed_text
        
        # 結果の出力
        if output_mode == 'page':
            # ページごとに別ファイルに出力
            if not output_path:
                pdf_name = Path(pdf_path).stem
                output_dir = Path(f"{pdf_name}_pages")
            else:
                output_dir = Path(output_path)
            
            output_dir.mkdir(exist_ok=True)
            
            # pdfplumberを使って再度ページごとに処理
            if USE_PDFPLUMBER:
                with pdfplumber.open(pdf_path) as pdf:
                    page_count = 0
                    for page_num, page in enumerate(pdf.pages):
                        try:
                            text = page.extract_text()
                            
                            if text and text.strip():
                                page_count += 1
                                output_file = output_dir / f"page_{page_num + 1:04d}.txt"
                                
                                # テキストの処理
                                text = text.replace('\r\n', '\n').replace('\r', '\n')
                                
                                # 特定の文字列を除去
                                if remove_patterns:
                                    for pattern in remove_patterns:
                                        if pattern.startswith('regex:'):
                                            regex_pattern = pattern[6:]
                                            text = re.sub(regex_pattern, '', text)
                                        else:
                                            text = text.replace(pattern, '')
                                
                                # 連続する空白行を整理
                                lines = text.split('\n')
                                cleaned_lines = []
                                prev_empty = False
                                
                                for line in lines:
                                    if line.strip():
                                        cleaned_lines.append(line)
                                        prev_empty = False
                                    elif not prev_empty:
                                        cleaned_lines.append('')
                                        prev_empty = True
                                
                                cleaned_text = '\n'.join(cleaned_lines)
                                
                                with open(output_file, 'w', encoding='utf-8') as f:
                                    f.write(f"PDFファイル: {pdf_path}\n")
                                    f.write(f"ページ番号: {page_num + 1}/{number_of_pages}\n")
                                    f.write("=" * 50 + "\n\n")
                                    f.write(cleaned_text)
                                
                                print(f"ページ {page_num + 1} を {output_file} に保存しました。")
                            else:
                                print(f"ページ {page_num + 1} はテキストがないためスキップしました。")
                                
                        except Exception as e:
                            print(f"警告: ページ {page_num + 1} の処理中にエラーが発生しました: {e}", file=sys.stderr)
            else:
                # pypdfの場合（既存のコードと同じ）
                reader = PdfReader(pdf_path)
                page_count = 0
                for page_num in range(number_of_pages):
                    try:
                        page = reader.pages[page_num]
                        text = page.extract_text()
                        
                        if text and text.strip():
                            page_count += 1
                            output_file = output_dir / f"page_{page_num + 1:04d}.txt"
                            
                            # テキストの処理（同上）
                            text = text.replace('\r\n', '\n').replace('\r', '\n')
                            
                            if remove_patterns:
                                for pattern in remove_patterns:
                                    if pattern.startswith('regex:'):
                                        regex_pattern = pattern[6:]
                                        text = re.sub(regex_pattern, '', text)
                                    else:
                                        text = text.replace(pattern, '')
                            
                            lines = text.split('\n')
                            cleaned_lines = []
                            prev_empty = False
                            
                            for line in lines:
                                if line.strip():
                                    cleaned_lines.append(line)
                                    prev_empty = False
                                elif not prev_empty:
                                    cleaned_lines.append('')
                                    prev_empty = True
                            
                            cleaned_text = '\n'.join(cleaned_lines)
                            
                            with open(output_file, 'w', encoding='utf-8') as f:
                                f.write(f"PDFファイル: {pdf_path}\n")
                                f.write(f"ページ番号: {page_num + 1}/{number_of_pages}\n")
                                f.write("=" * 50 + "\n\n")
                                f.write(cleaned_text)
                            
                            print(f"ページ {page_num + 1} を {output_file} に保存しました。")
                        else:
                            print(f"ページ {page_num + 1} はテキストがないためスキップしました。")
                            
                    except Exception as e:
                        print(f"警告: ページ {page_num + 1} の処理中にエラーが発生しました: {e}", file=sys.stderr)
            
            print(f"\n合計 {page_count} ページのテキストを {output_dir} ディレクトリに保存しました。")
            
        elif output_mode == 'single':
            # 1つのファイルに全ページを出力
            result = ''.join(all_text)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(result)
            print(f"\nテキストを {output_path} に保存しました。")
            
        else:  # stdout
            # 標準出力
            result = ''.join(all_text)
            print("\n抽出されたテキスト:")
            print("=" * 50)
            print(result)
            
    except FileNotFoundError:
        print(f"エラー: PDFファイル '{pdf_path}' が見つかりません。", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"エラー: PDFの処理中に問題が発生しました: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    # コマンドライン引数の処理
    if len(sys.argv) < 2 or sys.argv[1] in ['-h', '--help']:
        print("使用方法:")
        print("  python pdf_to_txt_improved.py <PDFファイルパス> [オプション]")
        print("")
        print("オプション:")
        print("  （引数なし）                        : 標準出力に表示")
        print("  -s <出力ファイル>                  : 1つのファイルに全ページを保存")
        print("  -p [出力ディレクトリ]              : ページごとに別ファイルに保存")
        print("  -r <除去する文字列>                : 指定した文字列を除去")
        print("  -rx <正規表現パターン>             : 正規表現パターンにマッチする文字列を除去")
        print("  -rf <ファイルパス>                 : ファイルから除去パターンを読み込み")
        print("")
        print("例:")
        print("  python pdf_to_txt_improved.py sample.pdf")
        print("  python pdf_to_txt_improved.py sample.pdf -s output.txt")
        print("  python pdf_to_txt_improved.py sample.pdf -p")
        sys.exit(1 if len(sys.argv) < 2 else 0)
    
    pdf_file = sys.argv[1]
    
    # PDFファイルの存在確認
    if not os.path.exists(pdf_file):
        print(f"エラー: PDFファイル '{pdf_file}' が見つかりません。", file=sys.stderr)
        sys.exit(1)
    
    # 出力モードとパスの決定
    output_mode = 'stdout'
    output_path = None
    remove_patterns = []
    
    # 引数の解析
    i = 2
    while i < len(sys.argv):
        arg = sys.argv[i]
        
        if arg == '-s' and i + 1 < len(sys.argv):
            output_mode = 'single'
            output_path = sys.argv[i + 1]
            i += 2
        elif arg == '-p':
            output_mode = 'page'
            if i + 1 < len(sys.argv) and not sys.argv[i + 1].startswith('-'):
                output_path = sys.argv[i + 1]
                i += 2
            else:
                i += 1
        elif arg == '-r' and i + 1 < len(sys.argv):
            remove_patterns.append(sys.argv[i + 1])
            i += 2
        elif arg == '-rx' and i + 1 < len(sys.argv):
            remove_patterns.append('regex:' + sys.argv[i + 1])
            i += 2
        elif arg == '-rf' and i + 1 < len(sys.argv):
            try:
                with open(sys.argv[i + 1], 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            remove_patterns.append(line)
            except FileNotFoundError:
                print(f"エラー: 除去パターンファイル '{sys.argv[i + 1]}' が見つかりません。", file=sys.stderr)
                sys.exit(1)
            i += 2
        elif not arg.startswith('-'):
            output_mode = 'single'
            output_path = arg
            i += 1
        else:
            print(f"エラー: 不明なオプション '{arg}'", file=sys.stderr)
            sys.exit(1)
    
    # 除去パターンの情報を表示
    if remove_patterns:
        print(f"除去パターン数: {len(remove_patterns)}")
        for pattern in remove_patterns[:5]:
            if pattern.startswith('regex:'):
                print(f"  - 正規表現: {pattern[6:][:50]}..." if len(pattern[6:]) > 50 else f"  - 正規表現: {pattern[6:]}")
            else:
                print(f"  - 文字列: {pattern[:50]}..." if len(pattern) > 50 else f"  - 文字列: {pattern}")
        if len(remove_patterns) > 5:
            print(f"  ... 他 {len(remove_patterns) - 5} 個のパターン")
        print()
    
    # テキスト抽出の実行
    pdf_to_text(pdf_file, output_mode, output_path, remove_patterns)