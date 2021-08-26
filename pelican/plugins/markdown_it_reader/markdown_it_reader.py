from markdown_it import MarkdownIt
from mdit_py_plugins.deflist import deflist_plugin
from mdit_py_plugins.footnote import footnote_plugin
from pygments import highlight
from pygments.formatters.html import HtmlFormatter
from pygments.lexers import get_lexer_by_name, guess_lexer
from pygments.lexers.special import TextLexer
from pygments.util import ClassNotFound

from pelican import signals
from pelican.readers import BaseReader
from pelican.utils import pelican_open


class MDITReader(BaseReader):
    enabled = True
    file_extensions = ["md", "markdown", "mkd", "mdown"]
    extensions = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # TODO: Do actual configuration

    #    settings = self.settings["MARKDOWN_IT"]
    #        settings.setdefault('extension_configs', {})
    #        settings.setdefault('extensions', [])
    #        for extension in settings['extension_configs'].keys():
    #            if extension not in settings['extensions']:
    #                settings['extensions'].append(extension)
    #        if 'markdown.extensions.meta' not in settings['extensions']:
    #            settings['extensions'].append('markdown.extensions.meta')

    def read(self, filename):
        with pelican_open(filename) as fp:
            text = list(fp.splitlines())

        content = None
        metadata = {}
        for i, line in enumerate(text):
            kv = line.split(":", 1)
            if len(kv) == 2:
                name, value = kv[0].lower(), kv[1].strip()
                metadata[name] = self.process_metadata(name, value)
            else:
                content = "\n".join(text[i:])
                break

        # add footnote and deflist plugins, enable tables
        # add in our processors for links
        md = (
            MarkdownIt("commonmark")
            .use(footnote_plugin)
            .use(deflist_plugin)
            .enable("table")
        )

        def replace_pelican_placeholdlers(original_url) -> str:
            new_url = original_url
            for placeholder in (
                "author",
                "category",
                "index",
                "tag",
                "filename",
                "static",
                "attach",
            ):
                new_url = new_url.replace(
                    "%7B" + placeholder + "%7D", "{" + placeholder + "}"
                )
                new_url = new_url.replace(
                    "%7C" + placeholder + "%7C", "{" + placeholder + "}"
                )
            return new_url

        def render_pelican_link(self, tokens, idx, options, env):
            tokens[idx].attrSet(
                "href", replace_pelican_placeholdlers(tokens[idx].attrGet("href"))
            )
            # pass token to default renderer.
            return self.renderToken(tokens, idx, options, env)

        def render_pelican_image(self, tokens, idx, options, env):
            tokens[idx].attrSet(
                "src", replace_pelican_placeholdlers(tokens[idx].attrGet("src"))
            )
            # pass token to default renderer.
            return self.image(tokens, idx, options, env)

        md.add_render_rule("link_open", render_pelican_link)
        md.add_render_rule("image", render_pelican_image)

        def get_lexer(info, content):
            try:
                if info and info != "":
                    lexer = get_lexer_by_name(info)
                else:
                    lexer = guess_lexer(content)
            except ClassNotFound:
                lexer = TextLexer
            return lexer

        def render_fence(self, tokens, idx, options, env):
            token = tokens[idx]
            lexer = get_lexer(token.info, token.content)
            output = highlight(
                token.content,
                lexer,
                HtmlFormatter(cssclass="codehilite", wrapcode=True),
            )
            return output

        md.add_render_rule("fence", render_fence)
        output = md.render(content)
        return output, metadata


def add_reader(readers):
    for ext in MDITReader.file_extensions:
        readers.reader_classes[ext] = MDITReader


def register():
    signals.readers_init.connect(add_reader)
