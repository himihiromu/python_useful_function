#!/usr/bin/env python3
"""
VOICEVOXを使用してテキストファイルを音声ファイルに変換するスクリプト

使用前に:
1. VOICEVOXを起動してください（デフォルトポート: 50021）
2. 必要なライブラリをインストール: pip install requests
"""

import sys
import os
import json
import time
import wave
from pathlib import Path
import requests
from typing import Dict, List, Optional
import argparse
import re

# VOICEVOXのデフォルトホストとポート
VOICEVOX_HOST = "http://127.0.0.1:50021"

# 利用可能なスピーカー（キャラクター）の定義
SPEAKERS = {
    # 四国めたん
    "shikoku_metan_normal": 2,
    "shikoku_metan_amagami": 0,
    "shikoku_metan_sexy": 6,
    "shikoku_metan_tsundere": 4,
    
    # ずんだもん
    "zundamon_normal": 3,
    "zundamon_amagami": 1,
    "zundamon_sexy": 7,
    "zundamon_tsundere": 5,
    
    # 春日部つむぎ
    "kasukabe_tsumugi": 8,
    
    # 雨晴はう
    "amehare_hau": 10,
    
    # 波音リツ
    "namine_ritsu": 9,
    
    # 玄野武宏
    "kurono_takehiro": 11,
    
    # 白上虎太郎
    "shirakami_kotaro": 12,
    
    # 青山龍星
    "aoyama_ryusei": 13,
    
    # 冥鳴ひまり
    "meimei_himari": 14,
    
    # 九州そら
    "kyushu_sora_normal": 16,
    "kyushu_sora_amagami": 15,
    "kyushu_sora_sexy": 18,
    "kyushu_sora_tsundere": 17,
    "kyushu_sora_sasayaki": 19,
    
    # もち子さん
    "mochiko": 20,
    
    # 剣崎雌雄
    "kenzaki_mesuo": 21,
    
    # WhiteCUL
    "whitecul_normal": 23,
    "whitecul_takabisha": 24,
    "whitecul_yandere": 25,
    "whitecul_larking": 26,
    
    # 後鬼
    "goki_normal": 27,
    "goki_tsumutai": 28,
    
    # No.7
    "no7_normal": 29,
    "no7_announce": 30,
    "no7_reading": 31,
    
    # ちび式じい
    "chibisikijii": 42,
    
    # 櫻歌ミコ
    "ouka_miko_normal": 43,
    "ouka_miko_romance": 44,
    "ouka_miko_tsundere": 45,
    "ouka_miko_sexy": 46,
    
    # 小夜/SAYO
    "sayo": 47,
    
    # ナースロボ＿タイプＴ
    "nurserobo_typet_normal": 48,
    "nurserobo_typet_fun": 49,
    "nurserobo_typet_shy": 50,
    
    # †聖騎士 紅桜†
    "seikishi_benizakura": 51,
    
    # 雀松朱司
    "wakamatshu_akashi": 52,
    
    # 麒ヶ島宗麟
    "kigashima_sourin": 53,
}

def check_voicevox_connection() -> bool:
    """VOICEVOXサーバーへの接続を確認"""
    try:
        response = requests.get(f"{VOICEVOX_HOST}/version", timeout=3)
        if response.status_code == 200:
            print(f"✓ VOICEVOXサーバー (ver. {response.text.strip()}) に接続しました")
            return True
    except requests.exceptions.RequestException:
        pass
    
    print("✗ VOICEVOXサーバーに接続できません")
    print("  VOICEVOXを起動してください")
    return False

def get_available_speakers() -> Dict[str, int]:
    """利用可能なスピーカーのリストを取得"""
    try:
        response = requests.get(f"{VOICEVOX_HOST}/speakers")
        if response.status_code == 200:
            speakers_data = response.json()
            available = {}
            for speaker in speakers_data:
                for style in speaker.get("styles", []):
                    # スピーカー名とスタイル名を組み合わせ
                    key = f"{speaker['name']}_{style['name']}".lower().replace(" ", "_")
                    available[key] = style["id"]
            return available
    except:
        pass
    return SPEAKERS

def list_speakers():
    """利用可能なスピーカーを表示"""
    speakers = get_available_speakers()
    
    print("\n利用可能なスピーカー（キャラクター）:")
    print("=" * 60)
    
    # カテゴリごとに整理
    categorized = {}
    for key, speaker_id in sorted(speakers.items()):
        base_name = key.rsplit("_", 1)[0] if "_" in key else key
        if base_name not in categorized:
            categorized[base_name] = []
        categorized[base_name].append((key, speaker_id))
    
    for base_name, variations in categorized.items():
        if len(variations) == 1:
            print(f"  {variations[0][0]:<30} (ID: {variations[0][1]})")
        else:
            print(f"\n  {base_name}:")
            for key, speaker_id in variations:
                style = key.replace(base_name + "_", "")
                print(f"    {key:<28} (ID: {speaker_id})")
    
    print("\n使用例: python text_to_voicevox.py ./texts -s zundamon_normal")

def text_to_speech(text: str, speaker_id: int, output_path: str, speed: float = 1.0, pitch: float = 0.0) -> bool:
    """
    テキストを音声ファイルに変換
    
    Args:
        text: 変換するテキスト
        speaker_id: スピーカーID
        output_path: 出力ファイルパス
        speed: 話速（0.5〜2.0）
        pitch: 音高（-0.15〜0.15）
    
    Returns:
        成功時True、失敗時False
    """
    try:
        # テキストを分割（長すぎる場合）
        max_length = 200  # 文字数制限
        text_parts = []
        
        if len(text) <= max_length:
            text_parts = [text]
        else:
            # 句読点で分割
            sentences = re.split(r'[。！？\n]', text)
            current_part = ""
            
            for sentence in sentences:
                if not sentence.strip():
                    continue
                    
                if len(current_part) + len(sentence) + 1 <= max_length:
                    current_part += sentence + "。"
                else:
                    if current_part:
                        text_parts.append(current_part)
                    current_part = sentence + "。"
            
            if current_part:
                text_parts.append(current_part)
        
        audio_data_list = []
        
        for i, part in enumerate(text_parts):
            if not part.strip():
                continue
                
            # 音声合成用のクエリを作成
            query_response = requests.post(
                f"{VOICEVOX_HOST}/audio_query",
                params={
                    "text": part,
                    "speaker": speaker_id
                },
                timeout=30
            )
            
            if query_response.status_code != 200:
                print(f"  ✗ クエリ作成に失敗 (part {i+1}/{len(text_parts)})")
                continue
            
            query = query_response.json()
            
            # 話速と音高を調整
            query["speedScale"] = speed
            query["pitchScale"] = pitch
            
            # 音声合成
            synthesis_response = requests.post(
                f"{VOICEVOX_HOST}/synthesis",
                params={"speaker": speaker_id},
                json=query,
                timeout=60
            )
            
            if synthesis_response.status_code != 200:
                print(f"  ✗ 音声合成に失敗 (part {i+1}/{len(text_parts)})")
                continue
            
            audio_data_list.append(synthesis_response.content)
        
        if not audio_data_list:
            return False
        
        # 音声データを結合して保存
        with open(output_path, "wb") as f:
            if len(audio_data_list) == 1:
                f.write(audio_data_list[0])
            else:
                # 複数の音声データを結合（簡易的な結合）
                for i, audio_data in enumerate(audio_data_list):
                    if i == 0:
                        f.write(audio_data)
                    else:
                        # WAVヘッダーをスキップして追加
                        f.write(audio_data[44:])  # WAVヘッダーは44バイト
        
        return True
        
    except Exception as e:
        print(f"  ✗ エラー: {e}")
        return False

def process_text_file(file_path: Path, output_dir: Path, speaker_id: int, speed: float, pitch: float) -> bool:
    """
    テキストファイルを音声ファイルに変換
    
    Args:
        file_path: 入力テキストファイルパス
        output_dir: 出力ディレクトリ
        speaker_id: スピーカーID
        speed: 話速
        pitch: 音高
    
    Returns:
        成功時True、失敗時False
    """
    try:
        # テキストファイルを読み込み
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()
        
        # ヘッダー情報を除去（PDFから抽出したテキストの場合）
        lines = text.split("\n")
        filtered_lines = []
        skip_header = False
        
        for line in lines:
            if line.startswith("PDFファイル:") or line.startswith("ページ番号:"):
                skip_header = True
                continue
            if skip_header and line.startswith("=" * 10):
                skip_header = False
                continue
            if not skip_header and line.strip():
                filtered_lines.append(line)
        
        text = "\n".join(filtered_lines).strip()
        
        if not text:
            print(f"  ⚠ {file_path.name}: テキストが空です")
            return False
        
        # 出力ファイル名
        output_file = output_dir / f"{file_path.stem}.wav"
        
        print(f"  処理中: {file_path.name} → {output_file.name}")
        
        # 音声変換
        success = text_to_speech(text, speaker_id, str(output_file), speed, pitch)
        
        if success:
            print(f"    ✓ 完了: {output_file.name}")
            return True
        else:
            print(f"    ✗ 失敗: {file_path.name}")
            return False
            
    except Exception as e:
        print(f"  ✗ エラー ({file_path.name}): {e}")
        return False

def main():
    parser = argparse.ArgumentParser(
        description="VOICEVOXを使用してテキストファイルを音声ファイルに変換",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  # スピーカー一覧を表示
  python text_to_voicevox.py --list
  
  # ずんだもんの声で変換
  python text_to_voicevox.py ./texts -s zundamon_normal
  
  # 四国めたんのあまあま声で変換（話速1.2倍）
  python text_to_voicevox.py ./texts -s shikoku_metan_amagami --speed 1.2
  
  # スピーカーIDを直接指定
  python text_to_voicevox.py ./texts --speaker-id 3
  
  # 単一ファイルを変換
  python text_to_voicevox.py ./texts/page_0001.txt -s zundamon_normal
"""
    )
    
    parser.add_argument("input_path", nargs="?", help="入力テキストファイルまたはディレクトリのパス")
    parser.add_argument("-s", "--speaker", help="スピーカー名（例: zundamon_normal）")
    parser.add_argument("--speaker-id", type=int, help="スピーカーID（数値）")
    parser.add_argument("-o", "--output", help="出力ディレクトリ（デフォルト: input_path_voices）")
    parser.add_argument("--speed", type=float, default=1.0, help="話速（0.5〜2.0、デフォルト: 1.0）")
    parser.add_argument("--pitch", type=float, default=0.0, help="音高（-0.15〜0.15、デフォルト: 0.0）")
    parser.add_argument("--list", action="store_true", help="利用可能なスピーカー一覧を表示")
    parser.add_argument("--host", default="http://127.0.0.1:50021", help="VOICEVOXサーバーのURL")
    
    args = parser.parse_args()
    
    # VOICEVOXサーバーのURLを設定
    global VOICEVOX_HOST
    VOICEVOX_HOST = args.host
    
    # スピーカー一覧表示
    if args.list:
        if check_voicevox_connection():
            list_speakers()
        return
    
    # 入力パスチェック
    if not args.input_path:
        parser.print_help()
        return
    
    input_path = Path(args.input_path)
    if not input_path.exists():
        print(f"エラー: 入力パス '{input_path}' が見つかりません")
        sys.exit(1)
    
    # VOICEVOXサーバーへの接続確認
    if not check_voicevox_connection():
        sys.exit(1)
    
    # スピーカーID決定
    speaker_id = None
    speakers = get_available_speakers()
    
    if args.speaker_id:
        speaker_id = args.speaker_id
        print(f"スピーカーID: {speaker_id}")
    elif args.speaker:
        if args.speaker in speakers:
            speaker_id = speakers[args.speaker]
            print(f"スピーカー: {args.speaker} (ID: {speaker_id})")
        else:
            print(f"エラー: スピーカー '{args.speaker}' が見つかりません")
            print("利用可能なスピーカーを確認するには --list オプションを使用してください")
            sys.exit(1)
    else:
        # デフォルトはずんだもん
        speaker_id = 3
        print("スピーカー: zundamon_normal (ID: 3) [デフォルト]")
    
    # 話速と音高の範囲チェック
    speed = max(0.5, min(2.0, args.speed))
    pitch = max(-0.15, min(0.15, args.pitch))
    
    if speed != args.speed:
        print(f"警告: 話速を {args.speed} から {speed} に調整しました（範囲: 0.5〜2.0）")
    if pitch != args.pitch:
        print(f"警告: 音高を {args.pitch} から {pitch} に調整しました（範囲: -0.15〜0.15）")
    
    # 出力ディレクトリ
    if args.output:
        output_dir = Path(args.output)
    else:
        if input_path.is_dir():
            output_dir = Path(f"{input_path}_voices")
        else:
            output_dir = input_path.parent / f"{input_path.stem}_voices"
    
    output_dir.mkdir(exist_ok=True)
    print(f"出力ディレクトリ: {output_dir}")
    
    # ファイルリスト作成
    if input_path.is_file():
        text_files = [input_path] if input_path.suffix == ".txt" else []
    else:
        text_files = sorted(input_path.glob("*.txt"))
    
    if not text_files:
        print("エラー: 処理するテキストファイルが見つかりません")
        sys.exit(1)
    
    print(f"\n{len(text_files)} 個のファイルを処理します")
    print("=" * 60)
    
    # 各ファイルを処理
    success_count = 0
    for text_file in text_files:
        if process_text_file(text_file, output_dir, speaker_id, speed, pitch):
            success_count += 1
        time.sleep(0.5)  # サーバー負荷軽減のため少し待機
    
    # 結果表示
    print("=" * 60)
    print(f"完了: {success_count}/{len(text_files)} ファイルを変換しました")
    
    if success_count > 0:
        print(f"音声ファイルは {output_dir} に保存されました")

if __name__ == "__main__":
    main()