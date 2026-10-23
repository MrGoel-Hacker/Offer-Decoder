"""Render scanned-PDF pages to JPEG data-URLs for the vision models (pypdfium2, in-memory)."""
import base64
import io
import logging
import traceback

logger = logging.getLogger("pdf_scan")

MAX_PAGES = 4
MAX_EDGE = 2000          # px, keeps each JPEG well under the 5 MB image limit
JPEG_QUALITY = 82


def render_pdf_pages(data: bytes):
    """Return (list of JPEG data-URLs, error tag). Up to MAX_PAGES pages."""
    try:
        import pypdfium2 as pdfium
    except ImportError:
        logger.error("pypdfium2 not installed - cannot render scanned PDFs")
        return [], "renderer-unavailable"
    try:
        pdf = pdfium.PdfDocument(data)
        n = min(len(pdf), MAX_PAGES)
        out = []
        for i in range(n):
            page = pdf[i]
            w, h = page.get_size()
            scale = min(MAX_EDGE / max(w, h, 1), 3.0)
            scale = max(scale, 1.2)
            pil = page.render(scale=scale).to_pil().convert("RGB")
            buf = io.BytesIO()
            pil.save(buf, "JPEG", quality=JPEG_QUALITY, optimize=True)
            out.append("data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode())
            page.close()
        pdf.close()
        return out, ""
    except Exception as e:
        logger.warning("pdf render failed:\n%s", traceback.format_exc())
        frames = traceback.extract_tb(e.__traceback__)
        loc = f"{frames[-1].filename.split('/')[-1]}:{frames[-1].lineno}" if frames else "?"
        return [], "render-" + (type(e).__name__ + "@" + loc + " " + str(e))[:150]
