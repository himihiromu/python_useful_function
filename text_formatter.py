#!/usr/bin/env python3
"""
日本語テキストを自然な位置で区切り、音声読み上げ用に整形するスクリプト

複数の整形方法を提供：
1. 句読点ベースの改善版分割
2. 文字数ベースの分割
3. 形態素解析を使った分割（オプション）
4. VOICEVOX専用のSSML風記法
"""

import re
import sys
import argparse
from pathlib import Path
from typing import List, Optional
import unicodedata

# 形態素解析（オプション）
try:
    import MeCab
    MECAB_AVAILABLE = True
except ImportError:
    MECAB_AVAILABLE = False

class TextFormatter:
    """日本語テキストを音声読み上げ用に整形するクラス"""
    
    def __init__(self):
        self.mecab = None
        if MECAB_AVAILABLE:
            try:
                self.mecab = MeCab.Tagger()
            except:
                pass
    
    def clean_text(self, text: str, aggressive: bool = True) -> str:
        """強化版テキストクリーニング
        
        Args:
            text: クリーニング対象のテキスト
            aggressive: True の場合、より積極的に空白を除去
        """
        # 不可視文字・制御文字を除去
        # ゼロ幅スペース、ゼロ幅非接合子などを削除
        text = re.sub(r'[\u200b\u200c\u200d\u2060\ufeff]', '', text)
        
        # タブを半角スペースに変換
        text = text.replace('\t', ' ')
        
        # 全角スペースの処理
        # 文中の全角スペースは半角に、行頭の全角スペース（字下げ）は保持
        lines = text.split('\n')
        cleaned_lines = []
        for line in lines:
            # 行頭の全角スペースを一時的に保護
            indent = ''
            stripped = line.lstrip('　')
            if len(line) != len(stripped):
                indent = '　' * (len(line) - len(stripped))
            
            # 文中の全角スペースを半角に
            stripped = stripped.replace('　', ' ')
            
            # 連続する半角スペースを1つに
            stripped = re.sub(r' {2,}', ' ', stripped)
            
            # 句読点前後の不要な空白を除去
            stripped = re.sub(r' ([。、！？）」』】\)])', r'\1', stripped)
            stripped = re.sub(r'([（「『【\(]) ', r'\1', stripped)
            
            if aggressive:
                # より積極的な空白除去
                # 日本語文字と英数字の間の空白を除去（必要に応じて）
                stripped = re.sub(r'([ぁ-ゔァ-ヶー一-龠々〆〇]) +([ぁ-ゔァ-ヶー一-龠々〆〇])', r'\1\2', stripped)
                # ただし、英数字の前後の空白は維持（読みやすさのため）
            
            # 字下げを戻す（意図的な字下げは保持）
            if not aggressive and indent:
                cleaned_lines.append(indent + stripped)
            else:
                cleaned_lines.append(stripped.strip())
        
        text = '\n'.join(cleaned_lines)
        
        # 改行の正規化
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        
        # 連続する空行を削減
        # ただし、段落の区切りとして1つの空行は保持
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # 文末の空白を除去
        lines = text.split('\n')
        lines = [line.rstrip() for line in lines]
        text = '\n'.join(lines)
        
        # ファイル全体の前後の空白を除去
        return text.strip()
    
    def remove_meaningless_spaces(self, text: str) -> str:
        """意味のない空白を徹底的に除去"""
        # 特殊な空白文字をすべて検出して除去
        # Unicode空白文字のパターン
        space_chars = [
            '\u0020',  # 通常の半角スペース
            '\u00A0',  # ノーブレークスペース
            '\u1680',  # オガム文字スペース
            '\u2000', '\u2001', '\u2002', '\u2003', '\u2004',  # 各種EMスペース
            '\u2005', '\u2006', '\u2007', '\u2008', '\u2009',  # 各種薄いスペース
            '\u200A',  # ヘアスペース
            '\u202F',  # 狭いノーブレークスペース
            '\u205F',  # 中数学スペース
            '\u3000',  # 全角スペース
        ]
        
        # 特殊空白を通常スペースに統一
        for space_char in space_chars:
            if space_char != '\u0020' and space_char != '\u3000':
                text = text.replace(space_char, ' ')
        
        # 行ごとに処理
        lines = text.split('\n')
        cleaned = []
        
        for line in lines:
            # 行頭・行末の空白を除去
            line = line.strip()
            
            if not line:
                cleaned.append('')
                continue
            
            # 文中の処理
            # 日本語文字間の半角スペースを除去
            line = re.sub(r'([ぁ-ゔァ-ヶー一-龠々〆〇]) +([ぁ-ゔァ-ヶー一-龠々〆〇])', r'\1\2', line)
            
            # 日本語と記号間の不要な空白を除去
            line = re.sub(r'([ぁ-ゔァ-ヶー一-龠]) +([。、！？」』）】])', r'\1\2', line)
            line = re.sub(r'([「『（【]) +([ぁ-ゔァ-ヶー一-龠])', r'\1\2', line)
            
            # 数字と単位の間の空白を除去
            line = re.sub(r'(\d) +([年月日時分秒円個本枚冊])', r'\1\2', line)
            
            # 連続する空白を1つに
            line = re.sub(r' {2,}', ' ', line)
            
            cleaned.append(line)
        
        # 連続する空行を1つに
        result = []
        prev_empty = False
        for line in cleaned:
            if not line:
                if not prev_empty:
                    result.append(line)
                    prev_empty = True
            else:
                result.append(line)
                prev_empty = False
        
        return '\n'.join(result)
    
    def method1_punctuation_advanced(self, text: str, max_length: int = 50) -> str:
        """
        方法1: 句読点ベースの改善版分割
        - 句読点で基本分割
        - 長い文は接続助詞や並列助詞でも分割
        - 括弧内は分割しない
        """
        lines = []
        
        # まず句読点で分割
        sentences = re.split(r'([。！？])', text)
        
        current_sentence = ""
        for i in range(0, len(sentences), 2):
            if i < len(sentences):
                part = sentences[i]
                if i + 1 < len(sentences):
                    part += sentences[i + 1]  # 句読点を追加
                
                current_sentence += part
                
                # 文が長すぎる場合は追加の分割
                if len(current_sentence) > max_length:
                    # 読点で分割を試みる
                    if '、' in current_sentence:
                        sub_parts = current_sentence.split('、')
                        temp_line = ""
                        for j, sub_part in enumerate(sub_parts):
                            if j < len(sub_parts) - 1:
                                sub_part += '、'
                            
                            if len(temp_line) + len(sub_part) <= max_length:
                                temp_line += sub_part
                            else:
                                if temp_line:
                                    lines.append(temp_line)
                                temp_line = sub_part
                        
                        if temp_line:
                            lines.append(temp_line)
                        current_sentence = ""
                    else:
                        # 接続助詞での分割
                        split_points = ['が、', 'けれど', 'しかし', 'また、', 'そして', 'ので', 'から']
                        split_done = False
                        
                        for point in split_points:
                            if point in current_sentence:
                                parts = current_sentence.split(point, 1)
                                if len(parts) == 2:
                                    lines.append(parts[0] + point)
                                    current_sentence = parts[1]
                                    split_done = True
                                    break
                        
                        if not split_done:
                            lines.append(current_sentence)
                            current_sentence = ""
                
                # 句読点で文が終わった場合
                elif current_sentence.endswith(('。', '！', '？')):
                    lines.append(current_sentence)
                    current_sentence = ""
        
        # 残りの文を追加
        if current_sentence:
            lines.append(current_sentence)
        
        # 空行と改行を適切に配置
        formatted_lines = []
        for line in lines:
            line = line.strip()
            if line:
                formatted_lines.append(line)
                # 段落の区切りと思われる場所に空行を追加
                if line.endswith('。') and len(line) > 30:
                    formatted_lines.append('')
        
        return '\n'.join(formatted_lines)
    
    def method2_voicevox_tags(self, text: str) -> str:
        """
        方法2: VOICEVOX用の特殊タグを挿入
        - 短い休止: [pau:0.5] （0.5秒の休止）
        - 長い休止: [pau:1.0]
        - 読み指定: [読み:よみ]
        """
        # 句読点の後に休止を挿入
        text = re.sub(r'。', '。[pau:0.8]', text)
        text = re.sub(r'、', '、[pau:0.3]', text)
        text = re.sub(r'！', '！[pau:0.8]', text)
        text = re.sub(r'？', '？[pau:0.8]', text)
        
        # 段落の区切り（連続する改行）により長い休止
        text = re.sub(r'\n\n+', '\n[pau:1.5]\n', text)
        
        # 括弧の前後に短い休止
        text = re.sub(r'「', '[pau:0.2]「', text)
        text = re.sub(r'」', '」[pau:0.2]', text)
        
        # 数字の読み方を明示（例）
        # text = re.sub(r'(\d+)年', r'[\1:ねん]', text)
        
        return text
    
    def method3_morphological(self, text: str, max_length: int = 40) -> str:
        """
        方法3: 形態素解析を使った文節での分割
        MeCabを使用して文節境界を検出
        """
        if not self.mecab:
            print("警告: MeCabが利用できません。方法1を使用します。")
            return self.method1_punctuation_advanced(text, max_length)
        
        lines = []
        current_line = ""
        
        # 形態素解析
        node = self.mecab.parseToNode(text)
        
        while node:
            word = node.surface
            features = node.feature.split(',')
            pos = features[0]  # 品詞
            
            # 文節の区切りを検出
            is_bunsetsu_end = False
            
            # 助詞、助動詞、句読点で文節の区切りとする
            if pos in ['助詞', '助動詞', '記号']:
                is_bunsetsu_end = True
            
            current_line += word
            
            # 文節の区切りで、かつ一定の長さを超えたら改行
            if is_bunsetsu_end and len(current_line) >= max_length:
                lines.append(current_line)
                current_line = ""
            
            # 句点で必ず改行
            if word in ['。', '！', '？']:
                lines.append(current_line)
                current_line = ""
            
            node = node.next
        
        if current_line:
            lines.append(current_line)
        
        return '\n'.join(lines)
    
    def method4_semantic_breaks(self, text: str) -> str:
        """
        方法4: 意味的な区切りでの分割（セマンティック改行）
        - 主語の後
        - 目的語の後
        - 長い修飾句の後
        """
        # パターンベースの分割点を定義
        break_patterns = [
            (r'(は、|が、|を、|に、|で、|と、|から、|まで、|より、)', r'\1\n'),  # 助詞の後
            (r'(という|といった|などの|ような|ために)', r'\1\n'),  # 連体修飾の後
            (r'(であり、|であって、|ですが、|ですけれど、)', r'\1\n'),  # 丁寧語の接続
            (r'(、.{20,}?、)', lambda m: m.group(1).replace('、', '、\n')),  # 長い句の後
        ]
        
        result = text
        for pattern, replacement in break_patterns:
            result = re.sub(pattern, replacement, result)
        
        # 連続する改行を整理
        result = re.sub(r'\n{3,}', '\n\n', result)
        
        # 短すぎる行を結合
        lines = result.split('\n')
        merged_lines = []
        temp_line = ""
        
        for line in lines:
            line = line.strip()
            if len(line) < 10 and temp_line:
                temp_line += line
            else:
                if temp_line:
                    merged_lines.append(temp_line)
                temp_line = line
        
        if temp_line:
            merged_lines.append(temp_line)
        
        return '\n'.join(merged_lines)
    
    def method5_hybrid(self, text: str) -> str:
        """
        方法5: ハイブリッド方式（複数の方法を組み合わせ）
        最もバランスの良い結果を生成
        """
        # まず徹底的な空白除去
        text = self.remove_meaningless_spaces(text)
        
        # 強化版クリーニング
        text = self.clean_text(text, aggressive=True)
        
        # 句読点ベースの分割
        text = self.method1_punctuation_advanced(text, max_length=45)
        
        # VOICEVOXタグを追加（オプション）
        # text = self.method2_voicevox_tags(text)
        
        return text
    
    def method6_clean_only(self, text: str) -> str:
        """
        方法6: 空白除去のみ（改行は維持）
        PDFから抽出したテキストの空白問題を解決することに特化
        """
        # 意味のない空白を徹底除去
        text = self.remove_meaningless_spaces(text)
        
        # 強化版クリーニング
        text = self.clean_text(text, aggressive=True)
        
        # 各行の処理
        lines = text.split('\n')
        result = []
        
        for line in lines:
            line = line.strip()
            if line:
                # 文が長すぎる場合のみ、句読点で改行
                if len(line) > 80:
                    # 句点での改行
                    line = line.replace('。', '。\n')
                    # 読点が多い場合も考慮
                    parts = line.split('\n')
                    new_parts = []
                    for part in parts:
                        if part.count('、') > 3 and len(part) > 60:
                            # 3つ目の読点あたりで改行
                            count = 0
                            new_part = ''
                            for char in part:
                                new_part += char
                                if char == '、':
                                    count += 1
                                    if count == 3:
                                        new_part += '\n'
                                        count = 0
                            new_parts.append(new_part)
                        else:
                            new_parts.append(part)
                    line = '\n'.join(new_parts)
                
                result.append(line)
            else:
                result.append('')
        
        # 連続する空行を1つに
        final_result = []
        prev_empty = False
        for line in result:
            if not line.strip():
                if not prev_empty:
                    final_result.append('')
                    prev_empty = True
            else:
                final_result.append(line)
                prev_empty = False
        
        return '\n'.join(final_result)

def process_file(input_path: Path, output_path: Path, method: str, formatter: TextFormatter) -> None:
    """ファイルを処理して整形済みテキストを保存"""
    
    with open(input_path, 'r', encoding='utf-8') as f:
        text = f.read()
    
    # PDFから抽出したテキストのヘッダーを除去
    lines = text.split('\n')
    filtered_lines = []
    skip_header = False
    
    for line in lines:
        if line.startswith('PDFファイル:') or line.startswith('ページ番号:'):
            skip_header = True
            continue
        if skip_header and line.startswith('=' * 10):
            skip_header = False
            continue
        if not skip_header:
            filtered_lines.append(line)
    
    text = '\n'.join(filtered_lines)
    
    # まず意味のない空白を除去
    text = formatter.remove_meaningless_spaces(text)
    
    # 選択した方法で整形
    if method == 'punctuation':
        formatted = formatter.method1_punctuation_advanced(text)
    elif method == 'voicevox':
        formatted = formatter.method2_voicevox_tags(text)
    elif method == 'morphological':
        formatted = formatter.method3_morphological(text)
    elif method == 'semantic':
        formatted = formatter.method4_semantic_breaks(text)
    elif method == 'hybrid':
        formatted = formatter.method5_hybrid(text)
    elif method == 'clean':
        formatted = formatter.method6_clean_only(text)
    else:
        formatted = formatter.method5_hybrid(text)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(formatted)
    
    print(f"  ✓ {input_path.name} → {output_path.name}")

def main():
    parser = argparse.ArgumentParser(
        description="日本語テキストを音声読み上げ用に整形",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
整形方法:
  punctuation   : 句読点ベースの改善版分割（デフォルト）
  voicevox     : VOICEVOX用の休止タグを挿入
  morphological: 形態素解析を使った文節分割（MeCab必要）
  semantic     : 意味的な区切りでの分割
  hybrid       : 複数の方法を組み合わせ（空白除去強化版）
  clean        : 空白除去に特化（改行は最小限）

使用例:
  # 句読点ベースで整形（デフォルト）
  python text_formatter.py input.txt
  
  # ディレクトリ内の全ファイルを整形
  python text_formatter.py ./texts -o ./formatted_texts
  
  # VOICEVOX用タグを挿入
  python text_formatter.py input.txt -m voicevox
  
  # 形態素解析を使用（MeCabのインストールが必要）
  python text_formatter.py input.txt -m morphological
"""
    )
    
    parser.add_argument('input_path', help='入力ファイルまたはディレクトリ')
    parser.add_argument('-o', '--output', help='出力先（デフォルト: input_formatted）')
    parser.add_argument('-m', '--method', 
                       choices=['punctuation', 'voicevox', 'morphological', 'semantic', 'hybrid', 'clean'],
                       default='hybrid',
                       help='整形方法を選択（デフォルト: hybrid）')
    parser.add_argument('--check-mecab', action='store_true', 
                       help='MeCabが利用可能か確認')
    
    args = parser.parse_args()
    
    # MeCabの確認
    if args.check_mecab:
        if MECAB_AVAILABLE:
            print("✓ MeCabが利用可能です")
            formatter = TextFormatter()
            if formatter.mecab:
                print("✓ MeCabが正常に初期化されました")
            else:
                print("✗ MeCabの初期化に失敗しました")
        else:
            print("✗ MeCabがインストールされていません")
            print("\nインストール方法:")
            print("  Ubuntu/Debian: sudo apt-get install mecab libmecab-dev mecab-ipadic-utf8")
            print("  Mac: brew install mecab mecab-ipadic")
            print("  Python: pip install mecab-python3")
        return
    
    input_path = Path(args.input_path)
    if not input_path.exists():
        print(f"エラー: {input_path} が見つかりません")
        sys.exit(1)
    
    # 出力先の決定
    if args.output:
        output_base = Path(args.output)
    else:
        if input_path.is_dir():
            output_base = Path(f"{input_path}_formatted")
        else:
            output_base = input_path.parent / f"{input_path.stem}_formatted.txt"
    
    formatter = TextFormatter()
    
    # ファイル処理
    if input_path.is_file():
        if args.output and Path(args.output).suffix == '':
            output_base.mkdir(exist_ok=True)
            output_path = output_base / input_path.name
        else:
            output_path = output_base
        
        process_file(input_path, output_path, args.method, formatter)
        print(f"\n整形完了: {output_path}")
    else:
        output_base.mkdir(exist_ok=True)
        text_files = sorted(input_path.glob('*.txt'))
        
        print(f"{len(text_files)} 個のファイルを処理します")
        for text_file in text_files:
            output_path = output_base / text_file.name
            process_file(text_file, output_path, args.method, formatter)
        
        print(f"\n整形完了: {len(text_files)} ファイルを {output_base} に保存")

if __name__ == '__main__':
    main()