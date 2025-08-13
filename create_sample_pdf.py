from pypdf import PdfWriter
from pypdf.generic import RectangleObject
from pypdf import PageObject
import io

# PDFライターの作成
writer = PdfWriter()

# サンプルテキストを含むページを作成
page1 = PageObject.create_blank_page(width=595, height=842)  # A4サイズ
page2 = PageObject.create_blank_page(width=595, height=842)
page3 = PageObject.create_blank_page(width=595, height=842)

# ページを追加
writer.add_page(page1)
writer.add_page(page2)
writer.add_page(page3)

# メタデータの追加
writer.add_metadata({
    '/Title': 'サンプルPDF',
    '/Author': 'テストユーザー',
    '/Subject': 'PDFテキスト抽出のテスト'
})

# PDFファイルを保存
with open('sample.pdf', 'wb') as output_file:
    writer.write(output_file)

print("sample.pdf を作成しました")