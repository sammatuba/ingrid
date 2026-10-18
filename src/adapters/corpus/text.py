"""Text layers: the extracted text of one document version, in pages a locator can cite.

A text layer is a derived artifact of exact bytes, never a substitute for them. It holds
the source version's SHA-256, the exact text this extraction produced, and one entry per
page with half-open offsets into that text. Offsets count Unicode code points of the
decoded text, the same unit the review core's ``Passage`` offsets use, so a quote taken
from a page can be registered as a passage without re-counting anything.

Two readers, both optional in the sense that neither is installed by this package:

* PDF through ``pypdf`` when it is importable. This adapter never installs it; a caller
  that wants PDF text puts the unpacked library on ``sys.path`` first
  (``sys.path.insert(0, ".local/pylib")``). When the import fails, the layer is recorded
  with status ``not_extracted`` and the reason names the missing reader: the bytes are
  still acquired with their fingerprint, and no text is invented.
* HTML through the standard library's ``html.parser``, always available.

There is no OCR here. A scanned PDF is recorded as bytes with status ``not_extracted``
and a reason that says so; the acquisition record still carries its digest and length.
No model, network, credential or clock is consulted: this module reads the bytes it is
given and nothing else.
"""
from __future__ import annotations

import hashlib
import io
import re
from dataclasses import dataclass
from html.parser import HTMLParser

#: Between two pages' texts inside a layer's ``text``. A locator is page-relative, so the
#: separator is only reachable by a quote that spans a page break; it is part of the text.
PAGE_SEPARATOR = "\n\n"

#: The reason recorded when the PDF reader is not importable in this interpreter.
PDF_READER_MISSING = (
    "pdf_reader_unavailable: pypdf is not importable in this interpreter; unpack it at "
    ".local/pylib and add that directory to sys.path")

UNSUPPORTED = "unsupported_content_type"

#: HTML elements whose boundaries separate text runs. Not a renderer: one newline each.
HTML_BLOCK_TAGS = frozenset({
    "address", "article", "aside", "blockquote", "br", "caption", "dd", "div", "dl", "dt",
    "fieldset", "figcaption", "figure", "footer", "form", "h1", "h2", "h3", "h4", "h5", "h6",
    "header", "hr", "li", "main", "nav", "ol", "p", "pre", "section", "table", "tbody",
    "td", "tfoot", "th", "thead", "tr", "ul",
})
#: Elements whose content is not document text.
HTML_SKIP_TAGS = frozenset({"script", "style", "noscript", "template", "svg"})

_META_CHARSET = re.compile(rb'<meta[^>]+charset\s*=\s*["\']?\s*([A-Za-z0-9_.:-]+)', re.I)
_BLANK_RUN = re.compile(r"[ \t]*(?:\n[ \t]*){3,}")


class TextLayerError(ValueError):
    """A refused layer, locator or quote. The code is stable; the detail names the cause."""

    def __init__(self, code, detail=""):
        self.code = code
        self.detail = detail
        super().__init__(code if not detail else "%s: %s" % (code, detail))


@dataclass(frozen=True)
class Page:
    """One page of a layer: its number (1-based) and half-open offsets into the text."""

    number: int
    start: int
    end: int

    @property
    def chars(self):
        return self.end - self.start


@dataclass(frozen=True)
class TextLayer:
    """The text layer of one document version, or the record that there is none.

    ``sha256`` is the fingerprint of the *document bytes* this layer came from, so a
    layer can always be matched back to its immutable source version. ``pages`` holds one
    entry per document page, empty ones included, so page numbers never shift.
    """

    content_type: str
    sha256: str
    status: str
    reason: str | None = None
    method: str | None = None
    method_version: str | None = None
    text: str = ""
    pages: tuple[Page, ...] = ()
    page_count: int | None = None
    charset: str | None = None
    charset_source: str | None = None

    @property
    def extracted(self):
        return self.status == "extracted"

    @property
    def text_chars(self):
        return len(self.text)

    def pages_without_text(self):
        """The page numbers that produced no text, in order."""
        return tuple(page.number for page in self.pages if page.chars == 0)

    def page(self, number):
        """The page with this 1-based number, or a refusal naming the range."""
        for page in self.pages:
            if page.number == number:
                return page
        raise TextLayerError("UNKNOWN_PAGE", "page %r is not in this layer" % (number,))

    def page_text(self, number):
        page = self.page(number)
        return self.text[page.start:page.end]

    def locator(self, page_number, start, end):
        """One page-relative span as a locator with global offsets and its exact quote.

        Offsets are code points *within the page*; the returned ``start``/``end`` are the
        layer-wide offsets a ``Passage`` record wants, and ``quote`` is the exact text
        between them. Both offset forms travel in the one locator, and
        :func:`validate_locator` refuses a locator whose forms disagree.
        """
        page = self.page(page_number)
        if type(start) is not int or type(end) is not int or not 0 <= start < end <= page.chars:
            raise TextLayerError(
                "INVALID_LOCATOR",
                "page %s offsets %r..%r outside 0..%s" % (page.number, start, end, page.chars))
        return {
            "page": page.number,
            "page_start": start,
            "page_end": end,
            "start": page.start + start,
            "end": page.start + end,
            "quote": self.text[page.start + start:page.start + end],
            "quote_digest": hashlib.sha256(
                self.text[page.start + start:page.start + end].encode("utf-8")).hexdigest(),
            "sha256": self.sha256,
        }

    def payload(self):
        """The layer as JSON-safe data, including every page's offsets."""
        return {
            "content_type": self.content_type,
            "sha256": self.sha256,
            "status": self.status,
            "reason": self.reason,
            "method": self.method,
            "method_version": self.method_version,
            "charset": self.charset,
            "charset_source": self.charset_source,
            "page_count": self.page_count,
            "text_chars": self.text_chars,
            "pages": [{"number": page.number, "start": page.start, "end": page.end}
                      for page in self.pages],
            "text": self.text,
        }

    @classmethod
    def from_payload(cls, data):
        """The layer a stored payload holds; offsets are checked against the text."""
        if type(data) is not dict or type(data.get("text")) is not str:
            raise TextLayerError("INVALID_LAYER", "payload is not a text layer")
        pages = tuple(Page(number=item["number"], start=item["start"], end=item["end"])
                      for item in data.get("pages", ()))
        layer = cls(content_type=data["content_type"], sha256=data["sha256"],
                    status=data["status"], reason=data.get("reason"),
                    method=data.get("method"), method_version=data.get("method_version"),
                    text=data["text"], pages=pages, page_count=data.get("page_count"),
                    charset=data.get("charset"), charset_source=data.get("charset_source"))
        cursor = 0
        for page in layer.pages:
            if page.start < cursor or page.end < page.start or page.end > len(layer.text):
                raise TextLayerError("INVALID_LAYER", "page %s offsets are not in order" % page.number)
            cursor = page.end
        return layer


def validate_locator(layer, locator, quote):
    """Check a locator against a layer and its quote; refuse any disagreement.

    Every part of the locator must agree with the layer and with every other part: the
    page offsets lie within the page, the layer-wide offsets are those offsets shifted by
    the page's own start, the quote is the text between them, and the quote digest is the
    digest of the quote. A locator that is right in one form and wrong in another is
    refused rather than recorded, because the ``Passage`` it would produce cites the wrong
    text even though the quote it carries looks right.
    """
    if not isinstance(layer, TextLayer) or type(locator) is not dict:
        raise TextLayerError("INVALID_LOCATOR", "expected a TextLayer and a locator object")
    if locator.get("sha256") != layer.sha256:
        raise TextLayerError("LAYER_MISMATCH", "locator names another layer")
    page = layer.page(locator.get("page"))
    if (type(locator.get("page_start")) is not int or type(locator.get("page_end")) is not int
            or not 0 <= locator["page_start"] < locator["page_end"] <= page.chars):
        raise TextLayerError("INVALID_LOCATOR", "page offsets are outside the page")
    start, end = page.start + locator["page_start"], page.start + locator["page_end"]
    if (type(locator.get("start")) is not int or type(locator.get("end")) is not int
            or locator["start"] != start or locator["end"] != end):
        raise TextLayerError(
            "INVALID_LOCATOR",
            "layer offsets %r..%r are not the page offsets %r..%r shifted by %r"
            % (locator.get("start"), locator.get("end"),
               locator["page_start"], locator["page_end"], page.start))
    expected = layer.text[start:end]
    if expected != quote:
        raise TextLayerError("INVALID_LOCATOR", "quote is not the text between the offsets")
    if locator.get("quote_digest") != hashlib.sha256(quote.encode("utf-8")).hexdigest():
        raise TextLayerError("INVALID_LOCATOR", "quote_digest is not the digest of the quote")
    return locator


def sniff_content_type(content):
    """The content type of exact bytes from their shape, never from their wording.

    A leading ``%PDF-`` header or an HTML document declaration is enough; a decodable
    text file is ``text/plain``; anything else stays ``application/octet-stream``. This
    reads no date, title or other statement out of the content.
    """
    if content[:5] == b"%PDF-":
        return "application/pdf"
    head = content[:512].lstrip(b"\xef\xbb\xbf\x00 \t\r\n")
    lowered = head[:256].lower()
    if lowered.startswith(b"<!doctype html") or lowered.startswith(b"<html"):
        return "text/html"
    try:
        content.decode("utf-8")
    except UnicodeDecodeError:
        return "application/octet-stream"
    return "text/plain"


def _pypdf():
    """The importable ``pypdf`` module, or ``None``. Imported here and never installed."""
    try:
        import pypdf
    except ImportError:
        return None
    return pypdf


def _layer(content, content_type, **kwargs):
    digest = hashlib.sha256(content).hexdigest()
    return TextLayer(content_type=content_type, sha256=digest, **kwargs)


def _join(page_texts):
    """Page texts joined by the documented separator, with page offsets."""
    pages, parts, cursor = [], [], 0
    for index, body in enumerate(page_texts):
        pages.append(Page(number=index + 1, start=cursor, end=cursor + len(body)))
        parts.append(body)
        cursor += len(body) + len(PAGE_SEPARATOR)
    return PAGE_SEPARATOR.join(parts), tuple(pages)


def extract_pdf(content, content_type="application/pdf"):
    """A PDF's text through ``pypdf`` when it is importable, or the record that it is not."""
    reader_module = _pypdf()
    if reader_module is None:
        return _layer(content, content_type, status="not_extracted", reason=PDF_READER_MISSING)
    version = getattr(reader_module, "__version__", "unknown")
    try:
        document = reader_module.PdfReader(io.BytesIO(content), strict=False)
        page_count = len(document.pages)
        if getattr(document, "is_encrypted", False):
            return _layer(content, content_type, status="not_extracted", page_count=page_count,
                          reason="pdf_encrypted: the text of an encrypted document is not read here")
        if page_count == 0:
            return _layer(content, content_type, status="not_extracted", page_count=0,
                          reason="pdf_empty: the document declares no pages")
        page_texts = [(page.extract_text() or "") for page in document.pages]
    except Exception as exc:  # a third-party reader over untrusted bytes; the type is the reason
        return _layer(content, content_type, status="not_extracted",
                      reason="pdf_unreadable: %s" % type(exc).__name__)
    if not any(body.strip() for body in page_texts):
        return _layer(content, content_type, status="not_extracted", page_count=page_count,
                      reason=("no_text_layer: %s pages carry no extractable text (a scanned "
                              "document needs OCR, which this adapter does not do)" % page_count))
    text, pages = _join(page_texts)
    return _layer(content, content_type, status="extracted", method="pypdf",
                  method_version=str(version), text=text, pages=pages, page_count=page_count)


class _HtmlText(HTMLParser):
    """Collects the document text; block elements become newlines and script is dropped."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.skipping = []

    def handle_starttag(self, tag, attrs):
        if tag in HTML_SKIP_TAGS:
            self.skipping.append(tag)
        elif tag in HTML_BLOCK_TAGS:
            self.parts.append("\n")

    def handle_startendtag(self, tag, attrs):
        if tag in HTML_BLOCK_TAGS and not self.skipping:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if self.skipping:
            # Leave the skipped region only when the outermost skipped element closes, so
            # text after a nested close is still skipped.
            if tag in self.skipping:
                self.skipping = self.skipping[:self.skipping.index(tag)]
            return
        if tag in HTML_BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.skipping:
            self.parts.append(data)


def decode_text(content, charset=None):
    """The document's text and the charset it was decoded with.

    A caller that has the HTTP header passes its charset. Otherwise a declared
    ``<meta ... charset=...>`` in the first bytes is read, then UTF-8, then Latin-1; the
    returned source says which one was used, so a mojibake quote is never silent.
    """
    if charset:
        try:
            return content.decode(charset, "strict"), charset, "supplied"
        except LookupError:
            pass  # a declared name this interpreter does not know: the paths below still apply
        except UnicodeDecodeError:
            # The response said one thing and sent another; keep the layer and let the
            # recorded charset say which name was tried.
            return content.decode(charset, "replace"), charset, "supplied"
    declared = _META_CHARSET.search(content[:2048])
    if declared:
        name = declared.group(1).decode("ascii", "replace")
        try:
            return content.decode(name, "strict"), name, "meta"
        except (LookupError, UnicodeDecodeError):
            pass
    try:
        return content.decode("utf-8", "strict"), "utf-8", "default"
    except UnicodeDecodeError:
        return content.decode("latin-1"), "latin-1", "fallback"


def extract_html(content, content_type="text/html", charset=None):
    """An HTML document's text, one page covering it, with the charset used."""
    decoded, used, source = decode_text(content, charset)
    parser = _HtmlText()
    parser.feed(decoded)
    parser.close()
    text = _BLANK_RUN.sub("\n\n", "".join(parser.parts).strip())
    return _layer(content, content_type, status="extracted", method="html.parser",
                  method_version="stdlib", text=text, pages=(Page(1, 0, len(text)),),
                  page_count=1, charset=used, charset_source=source)


def extract_text(content, content_type="text/plain", charset=None):
    """A plain-text document as one page, with the charset used."""
    decoded, used, source = decode_text(content, charset)
    text = decoded.strip()
    return _layer(content, content_type, status="extracted", method="identity",
                  method_version="stdlib", text=text, pages=(Page(1, 0, len(text)),),
                  page_count=1, charset=used, charset_source=source)


def extract(content, content_type, charset=None):
    """The text layer of exact bytes for one content type; never guesses a missing reader.

    A content type with no reader here is recorded, not repaired: the layer carries
    status ``not_extracted`` and the reason, and the bytes keep their own record.
    """
    if type(content) is not bytes:
        raise TextLayerError("INVALID_CONTENT", "content must be bytes")
    if content_type == "application/pdf":
        return extract_pdf(content)
    if content_type in ("text/html", "application/xhtml+xml"):
        return extract_html(content, content_type, charset)
    if type(content_type) is str and content_type.startswith("text/"):
        return extract_text(content, content_type, charset)
    return _layer(content, content_type or "application/octet-stream", status="not_extracted",
                  reason="%s: no reader for %r here" % (UNSUPPORTED, content_type))
