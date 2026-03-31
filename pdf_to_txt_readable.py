#!/usr/bin/env python3
"""
PDF テキスト抽出スクリプト（読みやすさ重視版）
縦書きPDFでも読みやすい形式で出力
"""

import sys
import os
import re
from pathlib import Path

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

def clean_text(text):
    """テキストのクリーニング処理"""
    if not text:
        return ""
    
    # 改行の正規化
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    
    # 過度な空白の削除
    text = re.sub(r'[ \t]+', ' ', text)  # 水平方向の連続空白を1つに
    text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)  # 3つ以上の改行を2つに
    
    # 各行の前後の空白を削除
    lines = text.split('\n')
    lines = [line.strip() for line in lines]
    
    # 空行の処理
    cleaned_lines = []
    prev_empty = False
    for line in lines:
        if line:
            cleaned_lines.append(line)
            prev_empty = False
        elif not prev_empty:
            cleaned_lines.append('')
            prev_empty = True
    
    return '\n'.join(cleaned_lines)

def extract_with_pdfplumber_layout(pdf_path):
    """
    pdfplumberを使用してレイアウトを考慮したテキスト抽出
    layout=Trueオプションを使用して、より自然な読み順でテキストを抽出
    """
    all_text = []
    
    with pdfplumber.open(pdf_path) as pdf:
        number_of_pages = len(pdf.pages)
        print(f"総ページ数: {number_of_pages} (pdfplumber layout解析使用)")
        
        for page_num, page in enumerate(pdf.pages):
            try:
                # layout=Trueで抽出（読みやすい順序で抽出）
                text = page.extract_text(layout=True, x_tolerance=3, y_tolerance=3)
                
                if text and text.strip():
                    # 縦書き特有の不要な空白を調整
                    text = clean_text(text)
                    
                    all_text.append(f"\n===== ページ {page_num + 1} =====\n")
                    all_text.append(text)
                else:
                    all_text.append(f"\n===== ページ {page_num + 1} (テキストなし) =====\n")
                    
            except Exception as e:
                # layout=Trueが失敗した場合は通常の方法で試す
                try:
                    text = page.extract_text()
                    if text and text.strip():
                        text = clean_text(text)
                        all_text.append(f"\n===== ページ {page_num + 1} =====\n")
                        all_text.append(text)
                    else:
                        all_text.append(f"\n===== ページ {page_num + 1} (テキストなし) =====\n")
                except Exception as e2:
                    print(f"警告: ページ {page_num + 1} の処理中にエラーが発生しました: {e2}", file=sys.stderr)
                    all_text.append(f"\n===== ページ {page_num + 1} (エラー) =====\n")
    
    return all_text, number_of_pages

def extract_with_pdfplumber_words(pdf_path):
    """
    pdfplumberのextract_wordsを使用して単語単位で抽出し、
    位置情報を基に正しい読み順に並べ替える
    """
    all_text = []
    
    with pdfplumber.open(pdf_path) as pdf:
        number_of_pages = len(pdf.pages)
        print(f"総ページ数: {number_of_pages} (pdfplumber 単語解析使用)")
        
        for page_num, page in enumerate(pdf.pages):
            try:
                # 単語単位で抽出（位置情報付き）
                words = page.extract_words(
                    x_tolerance=3,
                    y_tolerance=3,
                    keep_blank_chars=False,
                    use_text_flow=True  # テキストフローを考慮
                )
                
                if words:
                    # 縦書きか横書きかを判定
                    # 単語の配置パターンから推測
                    is_vertical = False
                    if len(words) > 10:
                        # Y座標の変化が大きく、X座標の変化が小さい場合は縦書き
                        x_variance = max(w['x0'] for w in words) - min(w['x0'] for w in words)
                        y_variance = max(w['top'] for w in words) - min(w['top'] for w in words)
                        if x_variance > y_variance * 1.5:
                            is_vertical = True
                    
                    if is_vertical:
                        # 縦書きの場合：右から左、上から下
                        words.sort(key=lambda w: (-w['x0'], w['top']))
                    else:
                        # 横書きの場合：上から下、左から右
                        words.sort(key=lambda w: (w['top'], w['x0']))
                    
                    # 単語を結合してテキストを構築
                    lines = []
                    current_line = []
                    last_y = None
                    y_threshold = 5  # 同じ行とみなすY座標の閾値
                    
                    for word in words:
                        current_y = word['top']
                        
                        if last_y is None or abs(current_y - last_y) < y_threshold:
                            current_line.append(word['text'])
                        else:
                            if current_line:
                                lines.append(' '.join(current_line))
                            current_line = [word['text']]
                        
                        last_y = current_y
                    
                    if current_line:
                        lines.append(' '.join(current_line))
                    
                    text = '\n'.join(lines)
                    text = clean_text(text)
                    
                    all_text.append(f"\n===== ページ {page_num + 1} =====\n")
                    all_text.append(text)
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
                text = clean_text(text)
                all_text.append(f"\n===== ページ {page_num + 1} =====\n")
                all_text.append(text)
            else:
                all_text.append(f"\n===== ページ {page_num + 1} (テキストなし) =====\n")
                
        except Exception as e:
            print(f"警告: ページ {page_num + 1} の処理中にエラーが発生しました: {e}", file=sys.stderr)
            all_text.append(f"\n===== ページ {page_num + 1} (エラー) =====\n")
    
    return all_text, number_of_pages

def pdf_to_text(pdf_path, output_mode='stdout', output_path=None, remove_patterns=None, extraction_method='layout'):
    """
    PDFファイルからテキストを抽出する関数
    
    Args:
        pdf_path: PDFファイルのパス
        output_mode: 出力モード ('stdout', 'single', 'page')
        output_path: 出力先のパス
        remove_patterns: 除去する文字列のパターンのリスト
        extraction_method: 抽出方法 ('layout', 'words', 'simple')
    """
    try:
        # 抽出方法に応じて処理
        if USE_PDFPLUMBER:
            try:
                if extraction_method == 'words':
                    all_text, number_of_pages = extract_with_pdfplumber_words(pdf_path)
                    print("単語解析での抽出に成功しました")
                elif extraction_method == 'simple':
                    # 通常のpdfplumber（レイアウト無視）
                    with pdfplumber.open(pdf_path) as pdf:
                        all_text = []
                        number_of_pages = len(pdf.pages)
                        print(f"総ページ数: {number_of_pages} (pdfplumber simple使用)")
                        for page_num, page in enumerate(pdf.pages):
                            text = page.extract_text()
                            if text and text.strip():
                                text = clean_text(text)
                                all_text.append(f"\n===== ページ {page_num + 1} =====\n")
                                all_text.append(text)
                            else:
                                all_text.append(f"\n===== ページ {page_num + 1} (テキストなし) =====\n")
                    print("シンプル抽出に成功しました")
                else:  # layout（デフォルト）
                    all_text, number_of_pages = extract_with_pdfplumber_layout(pdf_path)
                    print("レイアウト解析での抽出に成功しました")
                    
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
            
            # 各ページを個別に処理して保存
            page_count = 0
            for i in range(0, len(all_text), 2):  # ページ区切りとテキストのペア
                if i + 1 < len(all_text) and "=====" in all_text[i]:
                    page_match = re.search(r'ページ (\d+)', all_text[i])
                    if page_match and "(テキストなし)" not in all_text[i] and "(エラー)" not in all_text[i]:
                        page_num = int(page_match.group(1))
                        page_text = all_text[i + 1] if i + 1 < len(all_text) else ""
                        
                        if page_text.strip():
                            page_count += 1
                            output_file = output_dir / f"page_{page_num:04d}.txt"
                            
                            with open(output_file, 'w', encoding='utf-8') as f:
                                f.write(f"PDFファイル: {pdf_path}\n")
                                f.write(f"ページ番号: {page_num}/{number_of_pages}\n")
                                f.write("=" * 50 + "\n\n")
                                f.write(page_text)
                            
                            print(f"ページ {page_num} を {output_file} に保存しました。")
            
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
        print("  python pdf_to_txt_readable.py <PDFファイルパス> [オプション]")
        print("")
        print("オプション:")
        print("  （引数なし）                        : 標準出力に表示")
        print("  -s <出力ファイル>                  : 1つのファイルに全ページを保存")
        print("  -p [出力ディレクトリ]              : ページごとに別ファイルに保存")
        print("  -m <方法>                          : 抽出方法を指定")
        print("                                       layout: レイアウト解析（デフォルト、読みやすい）")
        print("                                       words: 単語解析（位置情報を考慮）")
        print("                                       simple: シンプル（レイアウト無視）")
        print("  -r <除去する文字列>                : 指定した文字列を除去")
        print("  -rx <正規表現パターン>             : 正規表現パターンにマッチする文字列を除去")
        print("  -rf <ファイルパス>                 : ファイルから除去パターンを読み込み")
        print("")
        print("例:")
        print("  # レイアウト解析で読みやすく抽出（デフォルト）")
        print("  python pdf_to_txt_readable.py sample.pdf -s output.txt")
        print("")
        print("  # 単語解析で縦書きを考慮して抽出")
        print("  python pdf_to_txt_readable.py sample.pdf -s output.txt -m words")
        print("")
        print("  # シンプルに抽出（高速だが読みにくい場合がある）")
        print("  python pdf_to_txt_readable.py sample.pdf -s output.txt -m simple")
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
    extraction_method = 'layout'  # デフォルトはレイアウト解析
    
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
        elif arg == '-m' and i + 1 < len(sys.argv):
            extraction_method = sys.argv[i + 1]
            if extraction_method not in ['layout', 'words', 'simple']:
                print(f"エラー: 不正な抽出方法 '{extraction_method}'", file=sys.stderr)
                print("使用可能: layout, words, simple", file=sys.stderr)
                sys.exit(1)
            i += 2
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
    
    print(f"抽出方法: {extraction_method}")
    
    # テキスト抽出の実行
    pdf_to_text(pdf_file, output_mode, output_path, remove_patterns, extraction_method)