from pypdf import PdfReader

# PDFファイルの読み込み
reader = PdfReader("\\\\RASPBERRYPI-1\\share-1\\電子書籍\\紙1枚に書くだけでうまくいく プロジェクト進行の技術が身につく本.pdf")

# ページ数の取得
number_of_pages = len(reader.pages)

# ページの取得。この場合は、1ページ目を取得する。
page = reader.pages[0]

# テキストの抽出
text = page.extract_text()
print(text)
page = reader.pages[1]
text = page.extract_text()
print(text)
page = reader.pages[2]
text = page.extract_text()
print(text)
