"""InGRID brand assets (docs/brand/README.md): the files exist, parse, have their stated sizes,
and every page links them.

The rasters are drawn by scripts/brand/build_icons.py with Chromium; this suite reads them as
bytes only (PNG headers, the ICO directory), so it needs no browser.
"""
import json
import re
import struct
import unittest
import xml.dom.minidom
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GRID = ROOT / 'src' / 'grid'
HEAD_TAGS = ('<link rel="icon" href="/favicon.ico" sizes="32x32">',
             '<link rel="icon" href="/favicon.svg" type="image/svg+xml">',
             '<link rel="apple-touch-icon" href="/apple-touch-icon.png">',
             '<link rel="manifest" href="/site.webmanifest">',
             '<meta name="theme-color" content="#0b1018" media="(prefers-color-scheme: dark)">',
             '<meta name="theme-color" content="#f4f6fa" media="(prefers-color-scheme: light)">')
MARK_PATH = 'd="M6 6H16V26H26"'


def png_size(data):
    if data[:8] != b'\x89PNG\r\n\x1a\n' or data[12:16] != b'IHDR':
        raise AssertionError('not a PNG')
    return struct.unpack('>II', data[16:24])


class BrandAssets(unittest.TestCase):
    def test_the_svgs_are_well_formed_xml(self):
        # An XML comment may not hold "--": a browser then refuses the whole image.
        for name in ('ingrid-mark.svg', 'ingrid-logo.svg', 'favicon.svg'):
            xml.dom.minidom.parse(str(GRID / name))

    def test_the_mark_is_one_colour_and_the_logo_carries_it_unchanged(self):
        mark = (GRID / 'ingrid-mark.svg').read_text(encoding='utf-8')
        self.assertIn('currentColor', mark)
        self.assertIsNone(re.search(r'#[0-9a-fA-F]{3,6}\b', mark), 'the mark names no colour')
        for banned in ('Gradient', 'filter', 'opacity'):
            self.assertNotIn(banned, mark)
        logo = (GRID / 'ingrid-logo.svg').read_text(encoding='utf-8')
        self.assertIn(MARK_PATH, logo)
        self.assertNotIn('<text', logo, 'the wordmark is outlined, so it renders without Inter')

    def test_the_favicon_follows_the_colour_scheme(self):
        favicon = (GRID / 'favicon.svg').read_text(encoding='utf-8')
        self.assertIn('@media (prefers-color-scheme: dark)', favicon)
        for colour in ('#2563eb', '#ffffff', '#7cc4ff', '#0b1018'):
            self.assertIn(colour, favicon)

    def test_the_png_icons_have_their_stated_sizes(self):
        for name, side in (('apple-touch-icon.png', 180), ('icon-192.png', 192),
                           ('icon-512.png', 512), ('icon-maskable-512.png', 512)):
            self.assertEqual((side, side), png_size((GRID / name).read_bytes()), name)

    def test_the_ico_holds_16_32_and_48_as_png_payloads(self):
        data = (GRID / 'favicon.ico').read_bytes()
        reserved, kind, count = struct.unpack('<HHH', data[:6])
        self.assertEqual((0, 1, 3), (reserved, kind, count))
        sides = []
        for index in range(count):
            width, height, _, _, planes, bits, size, offset = struct.unpack(
                '<BBBBHHII', data[6 + 16 * index:22 + 16 * index])
            self.assertEqual((width, width), png_size(data[offset:offset + size]))
            self.assertEqual((width, 1, 32), (height, planes, bits))
            sides.append(width)
        self.assertEqual([16, 32, 48], sides)

    def test_the_manifest_names_the_product_and_its_icons(self):
        manifest = json.loads((GRID / 'site.webmanifest').read_text(encoding='utf-8'))
        self.assertEqual(('InGRID', 'InGRID'), (manifest['name'], manifest['short_name']))
        self.assertEqual(('standalone', '/'), (manifest['display'], manifest['start_url']))
        self.assertEqual(('#0b1018', '#0b1018'), (manifest['theme_color'], manifest['background_color']))
        for icon in manifest['icons']:
            self.assertTrue((GRID / icon['src'].lstrip('/')).is_file(), icon['src'])
        self.assertIn('maskable', {icon.get('purpose') for icon in manifest['icons']})

    def test_every_page_links_the_icons_and_the_manifest(self):
        for page in sorted(GRID.glob('*.html')):
            html = page.read_text(encoding='utf-8')
            head = html[:html.index('</head>')]
            for tag in HEAD_TAGS:
                self.assertEqual(1, head.count(tag), (page.name, tag))

    def test_the_shell_bar_draws_the_mark(self):
        shell = (GRID / 'shell.js').read_text(encoding='utf-8')
        self.assertIn("path.setAttribute('d', 'M6 6H16V26H26')", shell)
        self.assertIn("svg.setAttribute('viewBox', '0 0 32 32')", shell)


if __name__ == '__main__':
    unittest.main()
