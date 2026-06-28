import os
import tempfile
import unittest

from pelican import signals
from pelican.tests.support import get_settings

from . import markdown_it_reader


class TestMarkdownTakeover(unittest.TestCase):
    """Test taking over the extensions"""

    def setUp(self) -> None:
        self.settings = get_settings()

    def test_register(self):
        self.assertFalse(signals.readers_init.has_receivers_for("md"))
        markdown_it_reader.register()
        self.assertTrue(signals.readers_init.has_receivers_for("md"))


class TestReading(unittest.TestCase):
    """Exercise the reader end-to-end against temporary Markdown files."""

    def setUp(self) -> None:
        self.reader = markdown_it_reader.MDITReader(get_settings())

    def _read(self, text):
        with tempfile.NamedTemporaryFile(
            "w", suffix=".md", delete=False, encoding="utf-8"
        ) as fp:
            fp.write(text)
            path = fp.name
        try:
            return self.reader.read(path)
        finally:
            os.unlink(path)

    def test_yaml_frontmatter_metadata(self):
        content, metadata = self._read(
            "---\n"
            "title: Hello World\n"
            "date: 2021-06-11 10:00\n"
            "category: server admin\n"
            "tags:\n"
            "  - apple\n"
            "  - macintosh\n"
            "---\n\n"
            "Body text.\n"
        )
        self.assertEqual(str(metadata["title"]), "Hello World")
        self.assertEqual(str(metadata["category"]), "server admin")
        self.assertEqual(
            sorted(str(t) for t in metadata["tags"]), ["apple", "macintosh"]
        )
        self.assertEqual(metadata["date"].year, 2021)
        self.assertIn("<p>Body text.</p>", content)

    def test_single_scalar_tag(self):
        _, metadata = self._read("---\ntitle: One Tag\ntags: apple\n---\n\nx\n")
        self.assertEqual([str(t) for t in metadata["tags"]], ["apple"])

    def test_fenced_code_inside_ordered_list(self):
        """The regression: fences nested in a list must stay inside the list
        and be highlighted, not collapse into an inline code span."""
        content, _ = self._read(
            "---\ntitle: List Code\n---\n\n"
            "1. First step\n\n"
            "   ```bash\n"
            "   echo hello\n"
            "   ```\n\n"
            "2. Second step\n\n"
            "   ```bash\n"
            "   echo world\n"
            "   ```\n"
        )
        # A real fenced block becomes a Pygments codehilite <div>, not <p><code>.
        self.assertIn('<div class="codehilite">', content)
        self.assertNotIn("<p><code>bash", content)
        # The list stays intact as a single ordered list with both items.
        self.assertEqual(content.count("<ol>"), 1)
        self.assertEqual(content.count("<li>"), 2)

    def test_pelican_link_placeholder(self):
        content, _ = self._read("---\ntitle: Link\n---\n\n[x]({filename}/other.md)\n")
        self.assertIn('href="{filename}/other.md"', content)

    def test_legacy_metadata_without_yaml_header(self):
        """Files without a --- fence still use the simple key: value parser."""
        content, metadata = self._read("title: Legacy\ncategory: news\n\nBody.\n")
        self.assertEqual(str(metadata["title"]), "Legacy")
        self.assertEqual(str(metadata["category"]), "news")
        self.assertIn("<p>Body.</p>", content)


if __name__ == "__main__":
    unittest.main()
