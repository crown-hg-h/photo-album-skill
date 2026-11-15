"""Export ordered images, optionally prepending them to an unchanged album PDF."""
import argparse
import hashlib
import io
import json
import math
from pathlib import Path
from PIL import Image, ImageOps
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader


def fingerprint(page):
    objects = page['/Resources'].get('/XObject', {})
    streams = sorted(hashlib.sha256(obj.get_object()._data).hexdigest() for obj in objects.values())
    return hashlib.sha256(page.get_contents().get_data()).hexdigest(), streams


def export(manifest, output, append=None):
    manifest = Path(manifest).resolve(); output = Path(output).resolve()
    report_path = output.with_suffix('.verification.json')
    if output.exists() or report_path.exists():
        raise FileExistsError('Choose a new output version; existing files are preserved')
    data = json.loads(manifest.read_text(encoding='utf-8'))
    width, height = map(float, data['page_mm'])
    if not all(math.isfinite(n) and n > 0 for n in [width, height]):
        raise ValueError('Page dimensions must be finite and positive')
    paths = [(manifest.parent / p).resolve() for p in data['images']]
    if not paths:
        raise ValueError('Image list is empty')
    old = PdfReader(append) if append else None
    if old:
        for page in old.pages:
            if abs(float(page.mediabox.width)-width*mm) > .01 or abs(float(page.mediabox.height)-height*mm) > .01:
                raise ValueError('Existing PDF page size differs from the new pages')
    for path in paths:
        with Image.open(path) as image:
            image = ImageOps.exif_transpose(image)
            if abs((image.width/image.height)/(width/height)-1) > .001:
                raise ValueError(f'Image ratio does not match page: {path}')
    buffer = io.BytesIO()
    document = canvas.Canvas(buffer, pagesize=(width*mm, height*mm), pageCompression=1)
    for path in paths:
        with Image.open(path) as image:
            image = ImageOps.exif_transpose(image).convert('RGB')
            document.drawImage(ImageReader(image), 0, 0, width=width*mm, height=height*mm)
            document.showPage()
    document.save(); buffer.seek(0)
    front = PdfReader(buffer); writer = PdfWriter()
    for page in front.pages: writer.add_page(page)
    if old:
        for page in old.pages: writer.add_page(page)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('xb') as stream: writer.write(stream)
    final = PdfReader(output)
    expected = len(paths) + (len(old.pages) if old else 0)
    if len(final.pages) != expected:
        raise ValueError('Exported PDF page count mismatch')
    if old:
        for i, page in enumerate(old.pages):
            if fingerprint(page) != fingerprint(final.pages[len(paths)+i]):
                raise ValueError(f'Existing page changed: {i+1}')
    with output.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    report = {'pages': expected, 'new_pages': len(paths), 'page_mm': [width, height],
              'original_pages_unchanged': True if old else None,
              'new_images_losslessly_embedded': True, 'visual_review': 'required',
              'sha256': digest}
    report_path.write_text(json.dumps(report, indent=2)+'\n')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest', type=Path)
    parser.add_argument('--append-pdf', type=Path)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(export(args.manifest, args.out, args.append_pdf)))


if __name__ == '__main__':
    main()
