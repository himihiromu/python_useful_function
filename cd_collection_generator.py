#!/usr/bin/env python3
"""
CD取り込み済みリスト生成スクリプト
cd-rippingディレクトリから取り込み済みCDの一覧をマークダウン形式で生成します。

フォルダ構造:
  cd-ripping/
    アーティスト名/
      アルバム名/
        *.flac
"""

import os
from pathlib import Path
from typing import Dict, List, Tuple
import argparse


def scan_cd_collection(base_path: Path) -> Dict[str, List[Tuple[str, int]]]:
    """
    指定されたディレクトリからアーティストとアルバムの情報を収集
    flacファイルが存在しないフォルダは自動的に除外されます。
    
    Args:
        base_path: スキャンするベースディレクトリのパス
    
    Returns:
        アーティスト名をキー、(アルバム名, 曲数)のタプルのリストを値とする辞書
    """
    collection = {}
    
    if not base_path.exists():
        raise FileNotFoundError(f"ディレクトリが見つかりません: {base_path}")
    
    # アーティストディレクトリをスキャン
    for artist_dir in sorted(base_path.iterdir()):
        if not artist_dir.is_dir():
            continue
        
        artist_name = artist_dir.name
        albums = []
        
        # アルバムディレクトリをスキャン
        for album_dir in sorted(artist_dir.iterdir()):
            if not album_dir.is_dir():
                continue
            
            # flacファイルが存在するか確認（flacファイルがないフォルダは除外）
            flac_files = list(album_dir.glob("*.flac"))
            if flac_files:  # flacファイルが1つ以上存在する場合のみ対象
                track_count = len(flac_files)
                albums.append((album_dir.name, track_count))
            # else: flacファイルがないフォルダはスキップ
        
        if albums:
            collection[artist_name] = albums
    
    return collection


def generate_markdown(collection: Dict[str, List[Tuple[str, int]]], output_path: Path = None) -> str:
    """
    コレクション情報をマークダウン形式で生成
    
    Args:
        collection: アーティストと(アルバム、曲数)のタプルの辞書
        output_path: 出力ファイルパス（指定時はファイルに保存）
    
    Returns:
        生成されたマークダウン文字列
    """
    lines = []
    lines.append("# CD取り込み済みリスト")
    lines.append("")
    
    # 統計情報
    total_artists = len(collection)
    total_albums = sum(len(albums) for albums in collection.values())
    total_tracks = sum(track_count for albums in collection.values() for _, track_count in albums)
    lines.append(f"**総アーティスト数**: {total_artists}")
    lines.append(f"**総アルバム数**: {total_albums}")
    lines.append(f"**総曲数**: {total_tracks}")
    lines.append("")
    lines.append("---")
    lines.append("")
    
    # アーティストごとのリスト
    lines.append("## アーティスト別一覧")
    lines.append("")
    
    for artist_name in sorted(collection.keys()):
        albums = collection[artist_name]
        artist_total_tracks = sum(track_count for _, track_count in albums)
        lines.append(f"### {artist_name} （全{len(albums)}枚、{artist_total_tracks}曲）")
        lines.append("")
        
        for album_name, track_count in sorted(albums, key=lambda x: x[0]):
            lines.append(f"- {album_name} （{track_count}曲）")
        
        lines.append("")
    
    # アルファベット順の全アルバムリスト
    lines.append("---")
    lines.append("")
    lines.append("## 全アルバム一覧（アルファベット順）")
    lines.append("")
    
    all_albums = []
    for artist_name, albums in collection.items():
        for album_name, track_count in albums:
            all_albums.append((artist_name, album_name, track_count))
    
    all_albums.sort(key=lambda x: (x[1].lower(), x[0].lower()))
    
    for artist_name, album_name, track_count in all_albums:
        lines.append(f"- **{album_name}** （{track_count}曲） / {artist_name}")
    
    markdown_content = "\n".join(lines)
    
    # ファイルに保存
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(markdown_content)
        print(f"マークダウンファイルを生成しました: {output_path}")
    
    return markdown_content


def main():
    """メイン処理"""
    parser = argparse.ArgumentParser(
        description="CD取り込み済みリストをマークダウン形式で生成"
    )
    parser.add_argument(
        "--input",
        "-i",
        type=str,
        default="cd-ripping",
        help="スキャンするディレクトリのパス（デフォルト: cd-ripping）"
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default="cd_collection.md",
        help="出力するマークダウンファイルのパス（デフォルト: cd_collection.md）"
    )
    parser.add_argument(
        "--print",
        "-p",
        action="store_true",
        help="標準出力にも表示"
    )
    
    args = parser.parse_args()
    
    try:
        # CDコレクションをスキャン
        base_path = Path(args.input)
        print(f"ディレクトリをスキャン中: {base_path}")
        collection = scan_cd_collection(base_path)
        
        if not collection:
            print("取り込み済みのCDが見つかりませんでした。")
            return
        
        # マークダウンを生成
        output_path = Path(args.output)
        markdown_content = generate_markdown(collection, output_path)
        
        # 標準出力に表示
        if args.print:
            print("\n" + "=" * 60)
            print(markdown_content)
            print("=" * 60 + "\n")
        
        # 統計情報を表示
        total_artists = len(collection)
        total_albums = sum(len(albums) for albums in collection.values())
        total_tracks = sum(track_count for albums in collection.values() for _, track_count in albums)
        print(f"\n✓ {total_artists} アーティスト、{total_albums} アルバム、{total_tracks} 曲を検出しました。")
        
    except FileNotFoundError as e:
        print(f"エラー: {e}")
        return 1
    except Exception as e:
        print(f"予期しないエラーが発生しました: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())