#
# Copyright (C) 2024 Guido Berhoerster <guido+particiapi@berhoerster.name>
#
# Licensed under the EUPL-1.2 or later
#

import xml.etree.ElementTree as etree
import re

import markdown
from markdown.blockprocessors import BlockProcessor, EmptyBlockProcessor
from markdown.inlinepatterns import LinkInlineProcessor, LINK_RE
from markdown.extensions import Extension


BLOCK_PROCESSORS_WHITELIST = { "empty" }
INLINE_PATTERN_WHITELIST = {
    "backtick",
    "escape",
    "link",
    "autolink",
    "automail",
    "linebreak",
    "entity",
    "not_strong",
    "em_strong",
    "em_strong2",
}


class EscapedHTML(Extension):
    def extendMarkdown(self, md):
        md.preprocessors.deregister("html_block")
        md.inlinePatterns.deregister("html")


class SingleBlockProcessor(BlockProcessor):
    def test(self, parent, block):
        return True

    def run(self, parent, blocks):
        result = []
        while blocks:
            block = blocks.pop(0)
            if block.strip():
                result.append(block.lstrip())

        div = etree.SubElement(parent, "div")
        div.text = "\n\n".join(result)


class OnlyInlineElements(Extension):
    def extendMarkdown(self, md):
        for name in list(md.parser.blockprocessors._data.keys()):
            if name not in BLOCK_PROCESSORS_WHITELIST:
                md.parser.blockprocessors.deregister(name)
        md.parser.blockprocessors.register(SingleBlockProcessor(md.parser), "singleblock", 90)


class SanitizedLinkInlineProcessor(LinkInlineProcessor):
    href_re = re.compile(r"^([Ff]|[Hh][Tt])[Tt][Pp][Ss]?://")

    def getLink(self, data, index):
        href, title, index, handled = super().getLink(data, index)
        if not self.href_re.match(href):
            href = "about:blank"
        return href, title, index, handled


class SanitizedLinks(Extension):
    def extendMarkdown(self, md):
        for name in list(md.inlinePatterns._data.keys()):
            if name not in INLINE_PATTERN_WHITELIST:
                md.inlinePatterns.deregister(name)
        md.inlinePatterns.register(SanitizedLinkInlineProcessor(LINK_RE, md), "link", 160)


def render_markdown(src):
    return markdown.markdown(src, extensions=[EscapedHTML(), SanitizedLinks(), OnlyInlineElements()])
