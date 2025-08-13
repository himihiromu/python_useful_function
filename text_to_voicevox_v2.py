#!/usr/bin/env python3
"""
改良版 VOICEVOX音声変換スクリプト
日本語の自然な区切りに対応
"""

import sys
import os
import json
import time
import re
from pathlib import Path
import requests
from typing import Dict, List, Optional, Tuple
import argparse

VOICEVOX_HOST = "http://127.0.0.1:50021"

# 短縮版スピーカーリスト（主要なもののみ）
SPEAKERS = {
    "zundamon": 3,
    "metan": 2,
    "tsumugi": 8,
    "ritsu": 9,
    "sora": 16,
    "mochiko": 20,
    "sayo": 47,
}

class VoicevoxConverter:
    """改良版VOICEVOX音声変換クラス"""
    
    def __init__(self, host: str = VOICEVOX_HOST):
        self.host = host
        
    def split_text_naturally(self, text: str) -> List[str]:
        """
        テキストを自然な位置で分割
        優先順位：
        1. 句点（。！？）
        2. 読点が多い場合は読点でも分割
        3. 200文字を超える場合は強制分割
        """
        MAX_LENGTH = 150  # VOICEVOXが自然に読める長さ
        MIN_LENGTH = 20   # 短すぎる文は結合
        
        # まず句点で分割
        sentences = re.split(r'([。！？])', text)
        
        # 句点を文末に戻す
        merged = []
        for i in range(0, len(sentences), 2):
            if i < len(sentences):
                sentence = sentences[i]
                if i + 1 < len(sentences):
                    sentence += sentences[i + 1]
                if sentence.strip():
                    merged.append(sentence.strip())
        
        # 長すぎる文をさらに分割
        result = []
        for sentence in merged:
            if len(sentence) <= MAX_LENGTH:
                result.append(sentence)
            else:
                # 読点で分割を試みる
                parts = sentence.split('、')
                current = ""
                for i, part in enumerate(parts):
                    if i < len(parts) - 1:
                        part += '、'
                    
                    if len(current) + len(part) <= MAX_LENGTH:
                        current += part
                    else:
                        if current:
                            result.append(current)
                        current = part
                
                if current:
                    result.append(current)
        
        # 短すぎる文を前後と結合
        final_result = []
        temp = ""
        for sentence in result:
            if len(sentence) < MIN_LENGTH and temp:
                if len(temp) + len(sentence) <= MAX_LENGTH:
                    temp += sentence
                else:
                    final_result.append(temp)
                    temp = sentence
            else:
                if temp:
                    final_result.append(temp)
                temp = sentence
        
        if temp:
            final_result.append(temp)
        
        return final_result
    
    def adjust_query_for_natural_speech(self, query: dict) -> dict:
        """
        音声合成クエリを調整して自然な読み上げに
        """
        # 句読点での間の調整
        if 'pauseLength' in query:
            query['pauseLength'] = 0.8  # 句点での間
        
        if 'pauseLengthScale' in query:
            query['pauseLengthScale'] = 1.2  # 全体的な間を少し長く
        
        # イントネーションの調整
        if 'intonationScale' in query:
            query['intonationScale'] = 1.1  # より自然な抑揚
        
        return query
    
    def text_to_speech_advanced(
        self, 
        text: str, 
        speaker_id: int, 
        output_path: str,
        speed: float = 1.0,
        pitch: float = 0.0,
        pause_scale: float = 1.0,
        intonation_scale: float = 1.0
    ) -> bool:
        """
        改良版音声変換
        - 自然な位置での分割
        - 句読点での適切な間
        - イントネーション調整
        """
        try:
            # テキストを自然に分割
            text_parts = self.split_text_naturally(text)
            
            if not text_parts:
                return False
            
            audio_data_list = []
            
            for i, part in enumerate(text_parts):
                print(f"    処理中 {i+1}/{len(text_parts)}: {part[:30]}...")
                
                # 音声合成用のクエリを作成
                query_response = requests.post(
                    f"{self.host}/audio_query",
                    params={"text": part, "speaker": speaker_id},
                    timeout=30
                )
                
                if query_response.status_code != 200:
                    print(f"      ✗ クエリ作成失敗")
                    continue
                
                query = query_response.json()
                
                # パラメータ調整
                query["speedScale"] = speed
                query["pitchScale"] = pitch
                query["pauseLengthScale"] = pause_scale
                query["intonationScale"] = intonation_scale
                
                # 自然な読み上げのための追加調整
                query = self.adjust_query_for_natural_speech(query)
                
                # 文末に適切な間を追加
                if part.endswith('。'):
                    query["postPhonemeLength"] = 0.5  # 文末の間
                elif part.endswith('、'):
                    query["postPhonemeLength"] = 0.2  # 読点の間
                
                # 音声合成
                synthesis_response = requests.post(
                    f"{self.host}/synthesis",
                    params={"speaker": speaker_id},
                    json=query,
                    timeout=60
                )
                
                if synthesis_response.status_code != 200:
                    print(f"      ✗ 音声合成失敗")
                    continue
                
                audio_data_list.append(synthesis_response.content)
            
            if not audio_data_list:
                return False
            
            # 音声データを結合して保存
            self.save_audio_with_gaps(audio_data_list, output_path)
            
            return True
            
        except Exception as e:
            print(f"  ✗ エラー: {e}")
            return False
    
    def save_audio_with_gaps(self, audio_data_list: List[bytes], output_path: str):
        """
        音声データを適切な間を空けて結合
        """
        import wave
        import struct
        
        # 最初の音声からパラメータを取得
        with wave.open(output_path, 'wb') as output_wav:
            # 最初のWAVファイルからパラメータを読み取り
            import io
            with wave.open(io.BytesIO(audio_data_list[0]), 'rb') as first_wav:
                params = first_wav.getparams()
                output_wav.setparams(params)
                
                # すべての音声データを結合
                for i, audio_data in enumerate(audio_data_list):
                    with wave.open(io.BytesIO(audio_data), 'rb') as wav:
                        frames = wav.readframes(wav.getnframes())
                        output_wav.writeframes(frames)
                        
                        # 文の間に無音を挿入（最後以外）
                        if i < len(audio_data_list) - 1:
                            # 0.3秒の無音を追加
                            silence_duration = 0.3
                            num_silence_frames = int(params.framerate * silence_duration)
                            silence = struct.pack('<' + ('h' * num_silence_frames * params.nchannels), 
                                                *([0] * num_silence_frames * params.nchannels))
                            output_wav.writeframes(silence)

def main():
    parser = argparse.ArgumentParser(
        description="改良版VOICEVOX音声変換（自然な日本語読み上げ）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  # 基本的な使用
  python text_to_voicevox_v2.py input.txt
  
  # ディレクトリ一括処理
  python text_to_voicevox_v2.py ./texts -s zundamon
  
  # 詳細な調整
  python text_to_voicevox_v2.py input.txt \\
    --speaker metan \\
    --speed 1.1 \\
    --pause-scale 1.2 \\
    --intonation-scale 1.1
  
  # 整形済みテキストから音声生成
  python text_formatter.py ./texts -o ./formatted
  python text_to_voicevox_v2.py ./formatted -s zundamon
"""
    )
    
    parser.add_argument('input_path', help='入力ファイルまたはディレクトリ')
    parser.add_argument('-s', '--speaker', default='zundamon',
                       choices=list(SPEAKERS.keys()),
                       help='スピーカー（簡略名）')
    parser.add_argument('-o', '--output', help='出力ディレクトリ')
    parser.add_argument('--speed', type=float, default=1.0,
                       help='話速（0.5-2.0）')
    parser.add_argument('--pitch', type=float, default=0.0,
                       help='音高（-0.15-0.15）')
    parser.add_argument('--pause-scale', type=float, default=1.0,
                       help='句読点での間の長さ（0.5-2.0）')
    parser.add_argument('--intonation-scale', type=float, default=1.0,
                       help='イントネーションの強さ（0.0-2.0）')
    parser.add_argument('--host', default=VOICEVOX_HOST,
                       help='VOICEVOXサーバーURL')
    
    args = parser.parse_args()
    
    # 入力パス確認
    input_path = Path(args.input_path)
    if not input_path.exists():
        print(f"エラー: {input_path} が見つかりません")
        sys.exit(1)
    
    # VOICEVOXサーバー確認
    converter = VoicevoxConverter(args.host)
    try:
        response = requests.get(f"{args.host}/version", timeout=3)
        if response.status_code == 200:
            print(f"✓ VOICEVOX (ver. {response.text.strip()}) に接続")
    except:
        print("✗ VOICEVOXサーバーに接続できません")
        sys.exit(1)
    
    # スピーカーID
    speaker_id = SPEAKERS[args.speaker]
    print(f"スピーカー: {args.speaker} (ID: {speaker_id})")
    
    # 出力ディレクトリ
    if args.output:
        output_dir = Path(args.output)
    else:
        if input_path.is_dir():
            output_dir = Path(f"{input_path}_voices_v2")
        else:
            output_dir = input_path.parent / "voices_v2"
    
    output_dir.mkdir(exist_ok=True)
    
    # ファイル処理
    if input_path.is_file():
        text_files = [input_path]
    else:
        text_files = sorted(input_path.glob('*.txt'))
    
    print(f"\n{len(text_files)} ファイルを処理します")
    print("=" * 60)
    
    success_count = 0
    for text_file in text_files:
        print(f"\n処理: {text_file.name}")
        
        with open(text_file, 'r', encoding='utf-8') as f:
            text = f.read()
        
        # PDFヘッダー除去
        lines = text.split('\n')
        filtered = []
        skip = False
        for line in lines:
            if line.startswith(('PDFファイル:', 'ページ番号:')):
                skip = True
                continue
            if skip and line.startswith('='):
                skip = False
                continue
            if not skip:
                filtered.append(line)
        
        text = '\n'.join(filtered).strip()
        
        if not text:
            print("  ⚠ テキストが空です")
            continue
        
        output_file = output_dir / f"{text_file.stem}.wav"
        
        if converter.text_to_speech_advanced(
            text, 
            speaker_id, 
            str(output_file),
            speed=args.speed,
            pitch=args.pitch,
            pause_scale=args.pause_scale,
            intonation_scale=args.intonation_scale
        ):
            print(f"  ✓ 完了: {output_file.name}")
            success_count += 1
        else:
            print(f"  ✗ 失敗")
        
        time.sleep(0.3)
    
    print("=" * 60)
    print(f"完了: {success_count}/{len(text_files)} ファイル")
    if success_count > 0:
        print(f"保存先: {output_dir}")

if __name__ == '__main__':
    main()