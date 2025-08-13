from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont

# 日本語フォントを登録
pdfmetrics.registerFont(UnicodeCIDFont('HeiseiKakuGo-W5'))

# PDFの作成
c = canvas.Canvas("test.pdf", pagesize=A4)

# ページ1
c.setFont('HeiseiKakuGo-W5', 12)
c.drawString(100, 750, "これはテストPDFです。")
c.drawString(100, 700, "1ページ目のテキストです。")
c.drawString(100, 650, "")  # 空白行
c.drawString(100, 600, "空白行のあとのテキストです。")
c.showPage()

# ページ2
c.drawString(100, 750, "2ページ目です。")
c.drawString(100, 700, "")  # 空白行
c.drawString(100, 650, "")  # 空白行
c.drawString(100, 600, "複数の空白行の後のテキストです。")
c.showPage()

# ページ3（空白ページ）
c.showPage()

# ページ4
c.drawString(100, 750, "最後のページです。")
c.showPage()

c.save()
print("test.pdf を作成しました")