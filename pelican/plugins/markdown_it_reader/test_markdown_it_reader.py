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
