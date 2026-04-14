from html import unescape
import re
import logging

from src.extractor.parser import SoupParser

log = logging.getLogger(__name__)

TABSSPACE = re.compile(r'[\s\t]+')

def inner_trim(value):
    if isinstance(value, str):
        value = re.sub(TABSSPACE, ' ', value)
        value = ''.join(value.splitlines())
        return value.strip()
    return ''

class OutputFormatterHU:
    def __init__(self, config):
        self.top_node = None
        self.config = config
        self.parser = SoupParser()
        self.language = 'hu'
        self.stopwords_class = config.stopwords_class  # Assume already HU

    def get_formatted(self, top_node):
        """Returns cleaned body text of a Hungarian article."""
        self.top_node = top_node
        self.remove_negative_score_nodes()
        self.links_to_text()
        self.add_newlines_to_br_and_li()
        self.replace_with_text()
        self.remove_empty_tags()
        self.remove_trailing_media_div()
        return self.convert_to_text()

    def convert_to_text(self):
        texts = []
        for node in list(self.top_node):
            try:
                txt = self.parser.getText(node)
            except ValueError as err:
                log.info("Skipping node due to parser error: %s", err)
                continue

            if txt:
                txt = unescape(txt)
                lines = inner_trim(txt).split(r'\n')
                lines = [line.strip() for line in lines]
                texts.extend(lines)

        return '\n\n'.join(texts)

    def add_newlines_to_br_and_li(self):
        for br in self.parser.getElementsByTag(self.top_node, 'br'):
            br.insert_after('\n')  # You can't set .text, insert newline after <br>
    
        for ul in self.parser.getElementsByTag(self.top_node, 'ul'):
            lis = self.parser.getElementsByTag(ul, 'li')
            for li in lis[:-1]:  # skip the last <li> (assumes last shouldn't get \n)
                li.clear()
                li.append(self.parser.getText(li) + '\n')

    def links_to_text(self):
        self.parser.stripTags(self.top_node, 'a')

    def remove_negative_score_nodes(self):
        for node in self.parser.css_select(self.top_node, "*[gravityScore]"):
            score = float(self.parser.getAttribute(node, 'gravityScore') or 0)
            if score < 1:
                node.getparent().remove(node)

    def replace_with_text(self):
        self.parser.stripTags(self.top_node, 'b', 'strong', 'i', 'br', 'sup')

    def remove_empty_tags(self):
        all_nodes = self.parser.getElementsByTags(self.top_node, ['*'])
        all_nodes.reverse()
        for el in all_nodes:
            tag = self.parser.getTag(el)
            if tag == 'br':
                continue
        
            text = self.parser.getText(el)
            if text:
                continue
        
            has_object = self.parser.getElementsByTag(el, 'object')
            has_embed = self.parser.getElementsByTag(el, 'embed')
            if not has_object and not has_embed:
                self.parser.remove(el)

    def remove_trailing_media_div(self):
        def get_depth(node, depth=1):
            children = self.parser.getChildren(node)
            if not children:
                return depth
            return max(get_depth(c, depth + 1) for c in children)
    
        top_nodes = self.parser.getChildren(self.top_node)
        if len(top_nodes) < 3:
            return
    
        last = top_nodes[-1]
    
        from bs4 import Tag
        if not isinstance(last, Tag):
            return
    
        last_class = self.parser.getAttribute(last, 'class')
        if last_class == 'zn-body__read-all':
            return
    
        if get_depth(last) >= 2:
            self.parser.remove(last)
