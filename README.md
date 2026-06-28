Markdown-IT reader: A Plugin for Pelican
====================================================

[![Build Status](https://img.shields.io/github/actions/workflow/status/gaige/markdown-it-reader/main.yml?branch=main)](https://github.com/gaige/markdown-it-reader/actions)
[![PyPI Version](https://img.shields.io/pypi/v/pelican-markdown-it-reader)](https://pypi.org/project/pelican-markdown-it-reader/)
![License](https://img.shields.io/pypi/l/pelican-markdown-it-reader?color=blue)

Reader plugin for Markdown-IT-py replacement

This is double-opinionated, in that it's opinionated using Markdown-IT
and again because we add in some additions; in particular:

- Tables
- footnotes
- Pygment-based syntax highlighting

Installation
------------

This plugin can be installed via:

    python -m pip install pelican-markdown-it-reader


Usage
-----

There are currently no configuration items.

Once installed it takes over responsibility for reading the following file extensions:

 - `md`
 - `markdown`
 - `mkd`
 - `mdown`

By taking over `link_open` and `image` render rules, the plugin handles replacing the
pelican link placeholders with appropriate `href` items which are then rendered to html.

### Metadata

The reader parses a YAML frontmatter header delimited by `---` (terminated by a
line of `---` or `...`), for example:

```markdown
---
title: My Post
date: 2021-06-11 10:00
category: server admin
tags:
  - apple
  - macintosh
---

Body text...
```

List-form values (such as `tags`) are supported, and `FORMATTED_FIELDS` (e.g.
`summary`) are rendered through Markdown-IT as well. Because the reader handles
YAML frontmatter itself, you do **not** need the `pelican-yaml-metadata` plugin;
in fact you should remove it, since whichever reader registers last wins the
Markdown extensions and `yaml-metadata` renders bodies with python-markdown
(which, among other things, cannot render fenced code blocks nested inside
lists).

Files without a `---` header fall back to a simple `key: value` metadata parser
for backwards compatibility.

Contributing
------------

Contributions are welcome and much appreciated. Every little bit helps.
You can contribute by improving the documentation, adding missing features,
and fixing bugs. You can also help out by reviewing and commenting on [existing issues][].

To start contributing to this plugin, review the [Contributing to Pelican][] documentation, beginning with the **Contributing Code** section.

[existing issues]: https://github.com/gaige/markdown-it-reader/issues
[Contributing to Pelican]: https://docs.getpelican.com/en/latest/contribute.html


Updating
--------

We use dependabot for updating dependencies, conventional commits for commit messages,
and github actions for release.

To generate a release:

1. `cz bump --dry-run [--increment patch]` to verify changes
2. `cz bump [--increment patch]` to finalize
3. `git push` to send code and `git push <tag>` to send the tag (or the less-safe `--tags`)


License
-------

This project is licensed under the MIT license.
