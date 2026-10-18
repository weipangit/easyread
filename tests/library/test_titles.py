import tempfile
import unittest
from pathlib import Path

from pypdf import PdfWriter

from easyread.library.library import TITLES_FILE, Library


def _pdf(width: int) -> bytes:
    import io
    buf = io.BytesIO()
    w = PdfWriter()
    w.add_blank_page(width=width, height=80)
    w.write(buf)
    return buf.getvalue()


class TitlesFileTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.lib = Library(Path(tmp.name))
        self.path = self.lib.root / TITLES_FILE

    def test_follows_add_and_trash(self):
        a, _ = self.lib.create_from_pdf(_pdf(60), "a.pdf", {"title_en": "beta paper"})
        self.lib.create_from_pdf(_pdf(61), "b.pdf", {"title_en": "Alpha\n Paper"})
        self.lib.list()
        self.assertEqual(self.path.read_text(encoding="utf-8"), "Alpha Paper\nbeta paper\n")
        self.lib.trash(a.id)
        self.lib.list()
        self.assertNotIn("beta paper", self.path.read_text(encoding="utf-8"))

    def test_unchanged_content_is_not_rewritten(self):
        self.lib.create_from_pdf(_pdf(60), "a.pdf", {"title_en": "Paper"})
        self.lib.list()
        before = self.path.stat().st_mtime_ns
        self.lib.list()
        self.assertEqual(self.path.stat().st_mtime_ns, before)
        self.assertEqual(len(self.lib.all()), 1)


if __name__ == "__main__":
    unittest.main()
