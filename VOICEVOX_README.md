# VOICEVOX テキスト音声変換スクリプト

PDFから抽出したテキストファイルを、VOICEVOXを使用して音声ファイルに変換するスクリプトです。

## 前提条件

1. **VOICEVOXのインストールと起動**
   - [VOICEVOX公式サイト](https://voicevox.hiroshiba.jp/)からダウンロード
   - インストール後、VOICEVOXを起動（デフォルトポート: 50021）

2. **必要なライブラリのインストール**
   ```bash
   uv pip install requests
   # または
   pip install requests
   ```

## 使用方法

### 基本的な流れ

1. **PDFからテキストを抽出（メールアドレスを除去）**
   ```bash
   # ページごとにテキストファイルを作成
   uv run python pdf_to_txt.py "your_book.pdf" -r "your@email.com" -p extracted_texts
   ```

2. **VOICEVOXを起動**
   - VOICEVOXアプリケーションを起動してください
   - 起動すると自動的にAPIサーバーが立ち上がります

3. **テキストを音声に変換**
   ```bash
   # デフォルト（ずんだもん）で変換
   uv run python text_to_voicevox.py extracted_texts
   
   # 四国めたん（あまあま）で変換
   uv run python text_to_voicevox.py extracted_texts -s shikoku_metan_amagami
   
   # 話速を1.2倍にして変換
   uv run python text_to_voicevox.py extracted_texts -s zundamon_normal --speed 1.2
   ```

### コマンドオプション

#### text_to_voicevox.py のオプション

- `input_path`: 入力テキストファイルまたはディレクトリのパス
- `-s, --speaker`: スピーカー名（例: zundamon_normal）
- `--speaker-id`: スピーカーID（数値で直接指定）
- `-o, --output`: 出力ディレクトリ（デフォルト: input_path_voices）
- `--speed`: 話速（0.5〜2.0、デフォルト: 1.0）
- `--pitch`: 音高（-0.15〜0.15、デフォルト: 0.0）
- `--list`: 利用可能なスピーカー一覧を表示
- `--host`: VOICEVOXサーバーのURL（デフォルト: http://127.0.0.1:50021）

### 利用可能なキャラクター（主要なもの）

```bash
# スピーカー一覧を表示
uv run python text_to_voicevox.py --list
```

主要なキャラクター:
- **ずんだもん**: zundamon_normal, zundamon_amagami, zundamon_sexy, zundamon_tsundere
- **四国めたん**: shikoku_metan_normal, shikoku_metan_amagami, shikoku_metan_sexy, shikoku_metan_tsundere
- **春日部つむぎ**: kasukabe_tsumugi
- **九州そら**: kyushu_sora_normal, kyushu_sora_amagami, kyushu_sora_sexy, kyushu_sora_tsundere
- **もち子さん**: mochiko
- **小夜/SAYO**: sayo

### 実行例

```bash
# 1. PDFからテキスト抽出（メールアドレスを除去）
uv run python pdf_to_txt.py "紙1枚に書くだけでうまくいく プロジェクト進行の技術が身につく本.pdf" \
  -r "himihiromu@icloud.com" -p book_texts

# 2. VOICEVOXで音声に変換（ずんだもん、話速1.1倍）
uv run python text_to_voicevox.py book_texts -s zundamon_normal --speed 1.1

# 3. 音声ファイルは book_texts_voices/ ディレクトリに保存されます
```

### トラブルシューティング

1. **「VOICEVOXサーバーに接続できません」エラー**
   - VOICEVOXアプリケーションが起動していることを確認
   - ファイアウォールやセキュリティソフトが通信をブロックしていないか確認

2. **音声が途切れる、不自然**
   - 長いテキストは自動的に分割されますが、句読点を適切に配置すると改善されます
   - `--speed`オプションで話速を調整してください

3. **特定のキャラクターが使えない**
   - VOICEVOXのバージョンによって利用可能なキャラクターが異なります
   - `--list`オプションで実際に利用可能なキャラクターを確認してください

## 注意事項

- 大量のテキストを処理する場合、時間がかかることがあります
- 各ファイルの処理間に0.5秒の待機時間を設けてサーバー負荷を軽減しています
- 生成された音声ファイルはWAV形式（非圧縮）のため、ファイルサイズが大きくなります