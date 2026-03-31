#!/usr/bin/env python3
"""
PDFの内部構造を解析するスクリプト
文字がどのような単位で格納されているか調査
"""

import sys
import pdfplumber
from collections import Counter

def analyze_pdf_structure(pdf_path, page_num=0):
    """PDFの内部構造を詳細に解析"""
    
    with pdfplumber.open(pdf_path) as pdf:
        if page_num >= len(pdf.pages):
            print(f"エラー: ページ {page_num} は存在しません")
            return
        
        page = pdf.pages[page_num]
        
        print(f"\n===== ページ {page_num + 1} の解析 =====")
        print(f"ページサイズ: {page.width} x {page.height}")
        print(f"回転: {page.rotation}度")
        
        # 1. extract_text() の結果
        print("\n【1. extract_text()の結果（最初の200文字）】")
        text = page.extract_text()
        if text:
            print(text[:200])
        
        # 2. extract_words() の解析
        print("\n【2. extract_words()の解析】")
        words = page.extract_words(
            x_tolerance=3,
            y_tolerance=3,
            keep_blank_chars=False,
            use_text_flow=False
        )
        
        if words:
            print(f"抽出された単語数: {len(words)}")
            print("\n最初の10個の単語:")
            for i, word in enumerate(words[:10]):
                print(f"  {i+1}. '{word['text']}' "
                      f"位置:({word['x0']:.1f}, {word['top']:.1f}) "
                      f"サイズ:({word['width']:.1f} x {word['height']:.1f}) "
                      f"方向:{word.get('upright', 'N/A')}")
            
            # 単語の長さ分布
            word_lengths = Counter(len(w['text']) for w in words)
            print("\n単語の文字数分布:")
            for length, count in sorted(word_lengths.items())[:10]:
                print(f"  {length}文字: {count}個")
        
        # 3. extract_text_lines() の解析
        print("\n【3. extract_text_lines()の解析】")
        lines = page.extract_text_lines(
            layout=False,
            strip=False,
            return_chars=True
        )
        
        if lines:
            print(f"抽出された行数: {len(lines)}")
            print("\n最初の5行の詳細:")
            for i, line in enumerate(lines[:5]):
                print(f"\n行 {i+1}:")
                print(f"  テキスト: '{line['text'][:50]}...' ")
                print(f"  位置: ({line.get('x0', 0):.1f}, {line.get('top', 0):.1f})")
                if 'width' in line and 'height' in line:
                    print(f"  サイズ: {line['width']:.1f} x {line['height']:.1f}")
                
                # この行に含まれる文字の詳細
                if 'chars' in line and line['chars']:
                    print(f"  文字数: {len(line['chars'])}")
                    print(f"  最初の5文字:")
                    for j, char in enumerate(line['chars'][:5]):
                        print(f"    '{char.get('text', '')}' "
                              f"位置:({char.get('x0', 0):.1f}, {char.get('top', 0):.1f}) "
                              f"サイズ:{char.get('size', 0):.1f} "
                              f"フォント:{char.get('fontname', 'N/A')}")
        
        # 4. chars（文字）の直接解析
        print("\n【4. 文字単位での解析】")
        chars = page.chars
        
        if chars:
            print(f"総文字数: {len(chars)}")
            
            # フォント情報の集計
            fonts = Counter(char.get('fontname', 'unknown') for char in chars)
            print("\n使用フォント:")
            for font, count in fonts.most_common(5):
                print(f"  {font}: {count}文字")
            
            # 文字サイズの集計
            sizes = Counter(round(char.get('size', 0)) for char in chars if char.get('size'))
            print("\n文字サイズ分布:")
            for size, count in sorted(sizes.items(), reverse=True)[:5]:
                print(f"  {size}pt: {count}文字")
            
            # 最初の20文字の詳細
            print("\n最初の20文字の詳細:")
            for i, char in enumerate(chars[:20]):
                text = char.get('text', '')
                x0 = char.get('x0', 0)
                top = char.get('top', 0)
                matrix = char.get('matrix', None)
                print(f"  {i+1}. '{text}' 位置:({x0:.1f}, {top:.1f}) "
                      f"matrix:{matrix}")
            
            # 文字の配置パターンを分析
            print("\n【文字配置パターンの分析】")
            
            # 連続する文字のX, Y座標の差を計算
            x_diffs = []
            y_diffs = []
            
            for i in range(min(100, len(chars)-1)):
                if chars[i].get('text', '').strip() and chars[i+1].get('text', '').strip():
                    x_diff = chars[i+1].get('x0', 0) - chars[i].get('x0', 0)
                    y_diff = chars[i+1].get('top', 0) - chars[i].get('top', 0)
                    x_diffs.append(abs(x_diff))
                    y_diffs.append(abs(y_diff))
            
            if x_diffs and y_diffs:
                avg_x_diff = sum(x_diffs) / len(x_diffs)
                avg_y_diff = sum(y_diffs) / len(y_diffs)
                
                print(f"連続文字間の平均X座標差: {avg_x_diff:.2f}")
                print(f"連続文字間の平均Y座標差: {avg_y_diff:.2f}")
                
                if avg_y_diff > avg_x_diff * 2:
                    print("→ 縦書きの可能性が高い（Y方向の移動が主）")
                elif avg_x_diff > avg_y_diff * 2:
                    print("→ 横書きの可能性が高い（X方向の移動が主）")
                else:
                    print("→ 混在または判定困難")
        
        # 5. テキストの変換行列（matrix）を調査
        print("\n【5. 変換行列（Matrix）の分析】")
        if chars:
            matrices = set()
            for char in chars[:100]:  # 最初の100文字をサンプリング
                matrix = char.get('matrix', None)
                if matrix:
                    matrices.add(tuple(matrix) if matrix else None)
            
            print(f"検出された異なる変換行列: {len(matrices)}個")
            for i, matrix in enumerate(list(matrices)[:5]):
                if matrix:
                    print(f"  Matrix {i+1}: {matrix}")
                    # matrix = (a, b, c, d, e, f)
                    # 通常の横書き: (1, 0, 0, 1, x, y)
                    # 90度回転（縦書き）: (0, 1, -1, 0, x, y)
                    if len(matrix) >= 4:
                        a, b, c, d = matrix[:4]
                        if abs(a) > 0.5 and abs(d) > 0.5 and abs(b) < 0.5 and abs(c) < 0.5:
                            print(f"    → 通常の横書き")
                        elif abs(b) > 0.5 and abs(c) > 0.5:
                            print(f"    → 回転あり（縦書きの可能性）")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("使用方法: python pdf_analyze_structure.py <PDFファイル> [ページ番号]")
        print("例: python pdf_analyze_structure.py sample.pdf 5")
        sys.exit(1)
    
    pdf_file = sys.argv[1]
    page_num = int(sys.argv[2]) - 1 if len(sys.argv) > 2 else 5  # デフォルトは6ページ目（index 5）
    
    analyze_pdf_structure(pdf_file, page_num)