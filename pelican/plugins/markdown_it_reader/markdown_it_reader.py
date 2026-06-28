import datetime
import logging
import re

from markdown_it import MarkdownIt
from mdit_py_plugins.deflist import deflist_plugin
from mdit_py_plugins.footnote import footnote_plugin
from pygments import highlight
from pygments.formatters.html import HtmlFormatter
from pygments.lexers import get_lexer_by_name, guess_lexer
from pygments.lexers.special import TextLexer
from pygments.util import ClassNotFound
import yaml

from pelican import signals
from pelican.contents import Author, Category, Tag
from pelican.readers import DUPLICATES_DEFINITIONS_ALLOWED, BaseReader
from pelican.utils import get_date, pelican_open

__log__ = logging.getLogger(__name__)

# A file whose first non-blank line is "---" carries a YAML frontmatter header,
# terminated by a line of "---" or "...". Everything after it is the body.
YAML_HEADER_RE = re.compile(
    r"\s*^-{3}$" r"(?P<metadata>.+?)" r"^(?:-{3}|\.{3})$" r"(?P<content>.*)",
    re.MULTILINE | re.DOTALL,
)

PELICAN_PLACEHOLDERS = (
    "author",
    "category",
    "index",
    "tag",
    "filename",
    "static",
    "attach",
)

# Metadata fields for which Pelican forbids multiple definitions (minus the
# fields that are legitimately list-valued).
DUPES_NOT_ALLOWED = {k for k, v in DUPLICATES_DEFINITIONS_ALLOWED.items() if not v} - {
    "tags",
    "authors",
}

# Sentinel marking a parsed value that should be dropped from the output.
_DEL = object()


def _as_list(obj):
    return list(obj) if isinstance(obj, (list, tuple)) else [obj]


def _strip(obj):
    return str(obj).strip()


def _parse_date(obj):
    # YAML may load an unquoted date as a datetime.date; normalise to a string
    # so Pelican's own date parsing (and timezone handling) applies.
    if isinstance(obj, datetime.date):
        obj = obj.isoformat()
    return get_date(str(obj).strip().replace("_", " "))


# Convert YAML-loaded values into the objects Pelican expects. Unlike the
# Markdown metadata extension, YAML hands us real lists/dates, so we cannot
# reuse BaseReader.process_metadata (which parses strings).
YAML_METADATA_PROCESSORS = {
    "tags": lambda x, y: [Tag(_strip(t), y) for t in _as_list(x)] or _DEL,
    "date": lambda x, y: _parse_date(x),
    "modified": lambda x, y: _parse_date(x),
    "category": lambda x, y: Category(_strip(x), y) if x else _DEL,
    "author": lambda x, y: Author(_strip(x), y) if x else _DEL,
    "authors": lambda x, y: [Author(_strip(a), y) for a in _as_list(x)] or _DEL,
    "slug": lambda x, y: _strip(x) or _DEL,
    "save_as": lambda x, y: _strip(x) or _DEL,
    "status": lambda x, y: _strip(x) or _DEL,
}


def _replace_pelican_placeholders(url):
    if url is None:
        return url
    for placeholder in PELICAN_PLACEHOLDERS:
        url = url.replace("%7B" + placeholder + "%7D", "{" + placeholder + "}")
        url = url.replace("%7C" + placeholder + "%7C", "{" + placeholder + "}")
    return url


def _get_lexer(info, content):
    try:
        if info:
            return get_lexer_by_name(info)
        return guess_lexer(content)
    except ClassNotFound:
        return TextLexer


class MDITReader(BaseReader):
    enabled = True
    file_extensions = ["md", "markdown", "mkd", "mdown"]
    extensions = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._md = self._build_md()

    def _build_md(self):
        # Markdown-IT with tables, footnotes, definition lists, Pelican link
        # placeholder rewriting, and Pygments syntax highlighting.
        md = (
            MarkdownIt("commonmark")
            .use(footnote_plugin)
            .use(deflist_plugin)
            .enable("table")
        )

        def render_pelican_link(self, tokens, idx, options, env):
            tokens[idx].attrSet(
                "href", _replace_pelican_placeholders(tokens[idx].attrGet("href"))
            )
            return self.renderToken(tokens, idx, options, env)

        def render_pelican_image(self, tokens, idx, options, env):
            tokens[idx].attrSet(
                "src", _replace_pelican_placeholders(tokens[idx].attrGet("src"))
            )
            return self.image(tokens, idx, options, env)

        def render_fence(self, tokens, idx, options, env):
            token = tokens[idx]
            lexer = _get_lexer(token.info, token.content)
            return highlight(
                token.content,
                lexer,
                HtmlFormatter(cssclass="codehilite", wrapcode=True),
            )

        md.add_render_rule("link_open", render_pelican_link)
        md.add_render_rule("image", render_pelican_image)
        md.add_render_rule("fence", render_fence)
        return md

    def read(self, filename):
        with pelican_open(filename) as text:
            match = YAML_HEADER_RE.fullmatch(text)

        if match:
            content = match.group("content")
            metadata = self._parse_yaml_metadata(
                yaml.safe_load(match.group("metadata"))
            )
        else:
            content, metadata = self._parse_legacy_metadata(text)

        return self._md.render(content), metadata

    def _parse_legacy_metadata(self, text):
        """Parse simple ``key: value`` headers (no YAML frontmatter fence).

        Retained for backwards compatibility with files that don't use a
        ``---``-delimited YAML header.
        """
        lines = list(text.splitlines())
        metadata = {}
        content = ""
        for i, line in enumerate(lines):
            kv = line.split(":", 1)
            if len(kv) == 2:
                name, value = kv[0].lower(), kv[1].strip()
                metadata[name] = self.process_metadata(name, value)
            else:
                content = "\n".join(lines[i:])
                break
        return content, metadata

    def _parse_yaml_metadata(self, meta):
        """Map a YAML-loaded mapping onto Pelican metadata."""
        if not isinstance(meta, dict):
            __log__.error("YAML metadata header did not parse as a mapping")
            return {}

        output = {}
        for name, value in meta.items():
            if value is None:
                continue

            name = name.lower()
            is_list = isinstance(value, list)
            if is_list:
                value = [x for x in value if x is not None]

            if name in self.settings["FORMATTED_FIELDS"]:
                # Render formatted fields (e.g. summary) as Markdown too.
                value = self._md.render("\n".join(value) if is_list else str(value))
            elif is_list and len(value) > 1 and name == "author":
                # Up-convert multiple "author" values to "authors".
                name = "authors"
            elif is_list and name in DUPES_NOT_ALLOWED and value:
                if len(value) > 1:
                    __log__.warning(
                        "Duplicate definition of '%s' (%r) - using the first",
                        name,
                        value,
                    )
                value = value[0]

            if name in YAML_METADATA_PROCESSORS:
                value = YAML_METADATA_PROCESSORS[name](value, self.settings)
            if value is not _DEL:
                output[name] = value

        return output


def add_reader(readers):
    for ext in MDITReader.file_extensions:
        readers.reader_classes[ext] = MDITReader


def register():
    signals.readers_init.connect(add_reader)
