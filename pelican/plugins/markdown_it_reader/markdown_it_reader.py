from pelican import signals
from pelican.readers import BaseReader
from pelican.utils import pelican_open

from markdown_it import MarkdownIt
from mdit_py_plugins.front_matter import front_matter_plugin
from mdit_py_plugins.footnote import footnote_plugin

from pygments import highlight
from pygments.lexers import get_lexer_by_name,guess_lexer
from pygments.formatters import HtmlFormatter

class MDITReader(BaseReader):
    enabled = True
    file_extensions = ['md', 'markdown', 'mkd', 'mdown']
    extensions = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        settings = self.settings['MARKDOWN_IT']
#        settings.setdefault('extension_configs', {})
#        settings.setdefault('extensions', [])
#        for extension in settings['extension_configs'].keys():
#            if extension not in settings['extensions']:
#                settings['extensions'].append(extension)
#        if 'markdown.extensions.meta' not in settings['extensions']:
#            settings['extensions'].append('markdown.extensions.meta')
#        self._source_path = None

    def read(self, filename):
        with pelican_open(filename) as fp:
            text = list(fp.splitlines())

        content = None
        metadata = {}
        for i, line in enumerate(text):
            kv = line.split(':', 1)
            if len(kv) == 2:
                name, value = kv[0].lower(), kv[1].strip()
                metadata[name] = self.process_metadata(name, value)
            else:
                content = "\n".join(text[i:])
                break

        md = MarkdownIt("commonmark").use(front_matter_plugin).use(footnote_plugin).enable('table')

        def replace_pelican_placeholdlers( original_url) -> str:
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
                new_url = new_url.replace("%7B" + placeholder + "%7D",
                                          "{" + placeholder + "}")
                new_url = new_url.replace("%7C" + placeholder + "%7C",
                                          "{" + placeholder + "}")
            return new_url

        def render_pelican_link(self, tokens, idx, options, env):
            tokens[idx].attrSet("href", replace_pelican_placeholdlers(
                tokens[idx].attrGet("href")))
            # pass token to default renderer.
            return self.renderToken(tokens, idx, options, env)

        def render_pelican_image(self, tokens, idx, options, env):
            tokens[idx].attrSet("src", replace_pelican_placeholdlers(
                tokens[idx].attrGet("src")))
            # pass token to default renderer.
            return self.renderToken(tokens, idx, options, env)


        md.add_render_rule("link_open", render_pelican_link)
        md.add_render_rule("image", render_pelican_image)

        def render_code_inline(self, tokens, idx, options, env):
            print(f"code type:[{idx}] {tokens[idx]} {tokens[idx].content}")
            return self.code_inline(tokens, idx, options, env)

        def render_fence(self, tokens, idx, options, env):
            token = tokens[idx]
            if token.info and token.info!='':
                lexer = get_lexer_by_name(token.info)
            else:
                lexer = guess_lexer(token.content)
            output = highlight(token.content, lexer, HtmlFormatter())
            print(f"fence type:[{idx}] {token} {token.content}")
            return (output)

        def render_code_block(self, tokens, idx, options, env):
            print(f"code type:[{idx}] {tokens[idx]} {tokens[idx].content}")
            return self.renderToken(tokens, idx, options, env)
        #md.add_render_rule("code_inline", render_code_inline)
        #md.add_render_rule("code_block", render_code_block)
        md.add_render_rule("fence", render_fence)
        output = md.render(content)
        return output, metadata


def add_reader(readers):
    for ext in MDITReader.file_extensions:
        readers.reader_classes[ext] = MDITReader


def register():
    signals.readers_init.connect(add_reader)
