from bs4 import BeautifulSoup, Tag

class SoupParser:
    def getText(self, node):
        return node.get_text(strip=True)

    def getTag(self, node):
        return node.name

    def getAttribute(self, node, attr):
        return node.get(attr, '')

    def getElementsByTag(self, node, tag):
        return node.find_all(tag)

    def getElementsByTags(self, node, tags):
        return node.find_all(tags)

    def getChildren(self, node):
        return list(node.children)

    def remove(self, node):
        node.decompose()

    def stripTags(self, node, *tags):
        for tag in node.find_all(tags):
            tag.unwrap()

    def css_select(self, node, selector):
        return node.select(selector)