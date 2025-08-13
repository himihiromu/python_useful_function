# プロジェクトの技術メモ

このドキュメントは、プロジェクトで遭遇した技術的な課題と解決策を記録しています。

## シェルスクリプトでのファイル名処理

### 空白を含むファイル名の安全な処理方法

ファイル名に空白や特殊文字が含まれる場合、通常のfor文では正しく動作しません。

**問題のあるコード:**
```bash
# 空白を含むファイル名で失敗する例
files=$(find . -name "*.pdf")
for file in $files; do
    echo "$file"  # ファイル名が空白で分割される
done
```

**推奨する解決方法:**
```bash
# null文字区切りで安全に処理
find . -name "*.pdf" -print0 | while IFS= read -r -d '' file; do
    echo "$file"  # 空白を含むファイル名も正しく処理
done
```

**重要なポイント:**
- `find ... -print0`: ヌル文字区切りで出力
- `while IFS= read -r -d ''`: ヌル文字区切りで読み取り
- 変数は必ずダブルクォートで囲む: `"$variable"`
- `basename`コマンドでファイル名抽出を簡潔化

### 実装例: sample.sh

PDFファイルを処理するスクリプトで、日本語や空白を含むファイル名にも対応:

```bash
find "$base_input_dir" -maxdepth 2 -name "*.pdf" -print0 | while IFS= read -r -d '' pdf_file
do
    pdf_file_name="${pdf_file}"
    # 処理...
    file_name=$(basename "$pdf_file" .pdf)
    # 出力...
done
```

この方法により、「紙1枚に書くだけでうまくいく プロジェクト進行の技術が身につく本.pdf」のようなファイル名も正しく処理できます。