from __future__ import annotations

import argparse
import html
import io
import re
import sys
import uuid
import zipfile
from dataclasses import dataclass
from pathlib import Path

import fitz  # PyMuPDF
from PIL import Image, ImageChops, ImageOps


@dataclass
class PageImage:
    filename: str
    media_type: str
    data: bytes
    width: int
    height: int


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^\w\s-]", "", value)
    value = re.sub(r"[-\s]+", "-", value)
    return value or "book"


def render_page(page: fitz.Page, dpi: int) -> Image.Image:
    scale = dpi / 72.0
    matrix = fitz.Matrix(scale, scale)
    pix = page.get_pixmap(matrix=matrix, alpha=False)
    return Image.open(io.BytesIO(pix.tobytes("png")))


def trim_white_margin(img: Image.Image, threshold: int = 245, padding: int = 8) -> Image.Image:
    gray = img.convert("L")
    bg = Image.new("L", gray.size, 255)
    diff = ImageChops.difference(gray, bg)

    mask = diff.point(lambda x: 255 if x > (255 - threshold) else 0)
    bbox = mask.getbbox()
    if not bbox:
        return img

    left, top, right, bottom = bbox
    left = max(0, left - padding)
    top = max(0, top - padding)
    right = min(img.width, right + padding)
    bottom = min(img.height, bottom + padding)
    return img.crop((left, top, right, bottom))


def resize_with_aspect(
    img: Image.Image,
    max_width: int | None,
    max_height: int | None,
    background: str = "white",
) -> Image.Image:
    if max_width is None and max_height is None:
        return img

    src_w, src_h = img.size

    if max_width is None:
        ratio = max_height / src_h
        new_size = (max(1, int(src_w * ratio)), max_height)
        return img.resize(new_size, Image.Resampling.LANCZOS)

    if max_height is None:
        ratio = max_width / src_w
        new_size = (max_width, max(1, int(src_h * ratio)))
        return img.resize(new_size, Image.Resampling.LANCZOS)

    img = ImageOps.contain(img, (max_width, max_height), Image.Resampling.LANCZOS)
    canvas = Image.new("RGB" if img.mode != "L" else "L", (max_width, max_height), 255)
    x = (max_width - img.width) // 2
    y = (max_height - img.height) // 2
    canvas.paste(img, (x, y))
    return canvas


def maybe_binarize(img: Image.Image, threshold: int = 180) -> Image.Image:
    gray = img.convert("L")
    bw = gray.point(lambda x: 255 if x >= threshold else 0, mode="1")
    return bw.convert("L")


def encode_image(
    img: Image.Image,
    page_no: int,
    image_format: str,
    jpeg_quality: int,
    png_compress_level: int,
    progressive: bool,
) -> PageImage:
    image_format = image_format.lower()
    buf = io.BytesIO()

    if image_format == "jpeg":
        if img.mode not in ("L", "RGB"):
            img = img.convert("RGB")
        media_type = "image/jpeg"
        filename = f"images/page-{page_no:04d}.jpg"
        img.save(
            buf,
            format="JPEG",
            quality=jpeg_quality,
            optimize=True,
            progressive=progressive,
        )
    elif image_format == "png":
        if img.mode not in ("L", "RGB"):
            img = img.convert("RGB")
        media_type = "image/png"
        filename = f"images/page-{page_no:04d}.png"
        img.save(
            buf,
            format="PNG",
            optimize=True,
            compress_level=png_compress_level,
        )
    else:
        raise ValueError(f"Unsupported image format: {image_format}")

    data = buf.getvalue()
    return PageImage(
        filename=filename,
        media_type=media_type,
        data=data,
        width=img.width,
        height=img.height,
    )


def build_page_xhtml(title: str, img_path: str, width: int, height: int) -> str:
    safe_title = html.escape(title)
    safe_img_path = html.escape(img_path)

    return f"""<?xml version="1.0" encoding="utf-8"?>
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="ja">
  <head>
    <title>{safe_title}</title>
    <meta charset="utf-8"/>
    <meta name="viewport" content="width={width}, height={height}"/>
    <style>
      html, body {{
        margin: 0;
        padding: 0;
        background: #ffffff;
      }}
      body {{
        text-align: center;
      }}
      img {{
        display: block;
        width: 100%;
        height: auto;
        margin: 0 auto;
      }}
    </style>
  </head>
  <body>
    <img src="{safe_img_path}" alt="{safe_title}"/>
  </body>
</html>
"""


def build_nav_xhtml(book_title: str, chapter_count: int) -> str:
    items = "\n".join(
        f'        <li><a href="text/page-{i:04d}.xhtml">Page {i}</a></li>'
        for i in range(1, chapter_count + 1)
    )
    safe_title = html.escape(book_title)

    return f"""<?xml version="1.0" encoding="utf-8"?>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" xml:lang="ja">
  <head>
    <title>{safe_title}</title>
    <meta charset="utf-8"/>
  </head>
  <body>
    <nav epub:type="toc" id="toc">
      <h1>{safe_title}</h1>
      <ol>
{items}
      </ol>
    </nav>
  </body>
</html>
"""


def build_content_opf(
    book_id: str,
    title: str,
    language: str,
    author: str,
    page_images: list[PageImage],
) -> str:
    manifest_items = [
        '    <item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>'
    ]
    spine_items = []

    for idx, page_img in enumerate(page_images, start=1):
        xhtml_id = f"page-{idx:04d}"
        image_id = f"img-{idx:04d}"

        manifest_items.append(
            f'    <item id="{xhtml_id}" href="text/page-{idx:04d}.xhtml" media-type="application/xhtml+xml"/>'
        )
        manifest_items.append(
            f'    <item id="{image_id}" href="{page_img.filename}" media-type="{page_img.media_type}"/>'
        )
        spine_items.append(f'    <itemref idref="{xhtml_id}"/>')

    safe_title = html.escape(title)
    safe_author = html.escape(author)
    safe_language = html.escape(language)

    return f"""<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="bookid">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:identifier id="bookid">urn:uuid:{book_id}</dc:identifier>
    <dc:title>{safe_title}</dc:title>
    <dc:language>{safe_language}</dc:language>
    <dc:creator>{safe_author}</dc:creator>
  </metadata>
  <manifest>
{chr(10).join(manifest_items)}
  </manifest>
  <spine>
{chr(10).join(spine_items)}
  </spine>
</package>
"""


def build_container_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>
"""


def create_epub(
    output_path: Path,
    title: str,
    author: str,
    language: str,
    page_images: list[PageImage],
) -> None:
    book_id = str(uuid.uuid4())

    with zipfile.ZipFile(output_path, "w") as zf:
        # mimetype は先頭・無圧縮
        zi = zipfile.ZipInfo("mimetype")
        zi.compress_type = zipfile.ZIP_STORED
        zf.writestr(zi, "application/epub+zip")

        zf.writestr("META-INF/container.xml", build_container_xml())
        zf.writestr("OEBPS/nav.xhtml", build_nav_xhtml(title, len(page_images)))

        for idx, page_img in enumerate(page_images, start=1):
            page_xhtml = build_page_xhtml(
                title=f"{title} - Page {idx}",
                img_path=f"../{page_img.filename}",
                width=page_img.width,
                height=page_img.height,
            )
            zf.writestr(f"OEBPS/text/page-{idx:04d}.xhtml", page_xhtml)
            zf.writestr(f"OEBPS/{page_img.filename}", page_img.data)

        zf.writestr(
            "OEBPS/content.opf",
            build_content_opf(
                book_id=book_id,
                title=title,
                language=language,
                author=author,
                page_images=page_images,
            ),
        )


def convert_pdf_to_image_epub(
    input_pdf: Path,
    output_epub: Path,
    title: str,
    author: str,
    language: str,
    dpi: int,
    grayscale: bool,
    trim: bool,
    trim_threshold: int,
    trim_padding: int,
    max_width: int | None,
    max_height: int | None,
    image_format: str,
    jpeg_quality: int,
    png_compress_level: int,
    progressive_jpeg: bool,
    binarize: bool,
    binarize_threshold: int,
    verbose: bool = True,
) -> None:
    doc = fitz.open(input_pdf)
    page_images: list[PageImage] = []

    for i, page in enumerate(doc, start=1):
        img = render_page(page, dpi=dpi)

        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")

        if trim:
            img = trim_white_margin(
                img,
                threshold=trim_threshold,
                padding=trim_padding,
            )

        if grayscale:
            img = img.convert("L")

        if binarize:
            img = maybe_binarize(img, threshold=binarize_threshold)

        img = resize_with_aspect(
            img,
            max_width=max_width,
            max_height=max_height,
            background="white",
        )

        page_img = encode_image(
            img=img,
            page_no=i,
            image_format=image_format,
            jpeg_quality=jpeg_quality,
            png_compress_level=png_compress_level,
            progressive=progressive_jpeg,
        )
        page_images.append(page_img)

        if verbose:
            print(
                f"    [{i}/{len(doc)}] "
                f"{page_img.filename} "
                f"{page_img.width}x{page_img.height} "
                f"{len(page_img.data) / 1024:.1f} KB"
            )

    create_epub(
        output_path=output_epub,
        title=title,
        author=author,
        language=language,
        page_images=page_images,
    )


def collect_pdf_files(input_path: Path, recursive: bool) -> list[Path]:
    if input_path.is_file():
        if input_path.suffix.lower() != ".pdf":
            raise ValueError(f"Input file is not a PDF: {input_path}")
        return [input_path]

    if not input_path.is_dir():
        raise FileNotFoundError(f"Input path not found: {input_path}")

    pattern = "**/*.pdf" if recursive else "*.pdf"
    return sorted(p for p in input_path.glob(pattern) if p.is_file())


def resolve_output_path(
    input_pdf: Path,
    input_root: Path,
    output_dir: Path,
    preserve_structure: bool,
) -> Path:
    if preserve_structure and input_root.is_dir():
        relative_parent = input_pdf.parent.relative_to(input_root)
        target_dir = output_dir / relative_parent
    else:
        target_dir = output_dir

    target_dir.mkdir(parents=True, exist_ok=True)
    return target_dir / f"{input_pdf.stem}.epub"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert one or more PDFs into image-only EPUB files."
    )

    parser.add_argument(
        "input_path",
        type=Path,
        help="Input PDF file or directory containing PDFs",
    )
    parser.add_argument(
        "output_dir",
        type=Path,
        help="Output directory for EPUB files",
    )

    parser.add_argument("--author", default="Unknown", help="Book author")
    parser.add_argument("--language", default="ja", help="Language code, e.g. ja, en")
    parser.add_argument("--dpi", type=int, default=220, help="Render DPI")
    parser.add_argument("--grayscale", action="store_true", help="Convert images to grayscale")
    parser.add_argument("--trim", action="store_true", help="Trim white margins")
    parser.add_argument("--trim-threshold", type=int, default=245, help="White threshold for trim")
    parser.add_argument("--trim-padding", type=int, default=8, help="Padding after trim")
    parser.add_argument("--max-width", type=int, default=None, help="Max output width")
    parser.add_argument("--max-height", type=int, default=None, help="Max output height")
    parser.add_argument(
        "--image-format",
        choices=["jpeg", "png"],
        default="jpeg",
        help="Image format inside EPUB",
    )
    parser.add_argument("--jpeg-quality", type=int, default=85, help="JPEG quality")
    parser.add_argument("--png-compress-level", type=int, default=9, help="PNG compress level")
    parser.add_argument("--progressive-jpeg", action="store_true", help="Use progressive JPEG")
    parser.add_argument("--binarize", action="store_true", help="Convert to black/white")
    parser.add_argument("--binarize-threshold", type=int, default=180, help="Threshold for binarize")

    parser.add_argument("--recursive", action="store_true", help="Search PDFs recursively")
    parser.add_argument(
        "--preserve-structure",
        action="store_true",
        help="Preserve input directory structure under output_dir",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing EPUB files",
    )
    parser.add_argument(
        "--continue-on-error",
        action="store_true",
        help="Continue processing remaining PDFs even if one fails",
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    input_path = args.input_path
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    pdf_files = collect_pdf_files(input_path, recursive=args.recursive)

    if not pdf_files:
        print("No PDF files found.")
        return 1

    print(f"Found {len(pdf_files)} PDF file(s).")

    success_count = 0
    fail_count = 0

    input_root = input_path if input_path.is_dir() else input_path.parent

    for idx, pdf_path in enumerate(pdf_files, start=1):
        output_epub = resolve_output_path(
            input_pdf=pdf_path,
            input_root=input_root,
            output_dir=output_dir,
            preserve_structure=args.preserve_structure,
        )

        if output_epub.exists() and not args.overwrite:
            print(f"[{idx}/{len(pdf_files)}] SKIP  {pdf_path} -> {output_epub} (already exists)")
            continue

        print(f"[{idx}/{len(pdf_files)}] START {pdf_path}")
        print(f"               OUT   {output_epub}")

        try:
            convert_pdf_to_image_epub(
                input_pdf=pdf_path,
                output_epub=output_epub,
                title=pdf_path.stem,
                author=args.author,
                language=args.language,
                dpi=args.dpi,
                grayscale=args.grayscale,
                trim=args.trim,
                trim_threshold=args.trim_threshold,
                trim_padding=args.trim_padding,
                max_width=args.max_width,
                max_height=args.max_height,
                image_format=args.image_format,
                jpeg_quality=args.jpeg_quality,
                png_compress_level=args.png_compress_level,
                progressive_jpeg=args.progressive_jpeg,
                binarize=args.binarize,
                binarize_threshold=args.binarize_threshold,
                verbose=True,
            )
            size_mb = output_epub.stat().st_size / (1024 * 1024)
            print(f"[{idx}/{len(pdf_files)}] DONE  {output_epub} ({size_mb:.2f} MB)")
            success_count += 1
        except Exception as e:
            print(f"[{idx}/{len(pdf_files)}] ERROR {pdf_path}")
            print(f"               {type(e).__name__}: {e}")
            fail_count += 1
            if not args.continue_on_error:
                print("Stopped due to error. Use --continue-on-error to keep going.")
                return 1

    print("")
    print("Summary")
    print(f"  Success: {success_count}")
    print(f"  Failed : {fail_count}")
    print(f"  Total  : {len(pdf_files)}")

    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
