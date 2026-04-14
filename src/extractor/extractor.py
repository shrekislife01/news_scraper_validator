import re
import json
import ast
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from urllib.parse import urlparse
from dateutil.parser import parse as parse_date
from html import unescape

from collections import Counter

TAG_HREF_PATTERNS = re.compile(r'/(tag|cimke|category|tema|topics)/', re.IGNORECASE)

from src.extractor.formatter import OutputFormatterHU
from src.extractor.parser import SoupParser

class NewsExtractor:
    def __init__(self, html, url):
        self.url = url
        self.html = html
        self.soup = BeautifulSoup(html, 'html.parser')
        self.domain = urlparse(url).netloc
        self.article_root = self.locate_article_root()

    def extract(self, with_kw = False):
        if with_kw:
            return {
                "url": self.url,
                "page": self.domain,
                "title": self.get_title(),
                "text": self.get_main_text(),
                "author": self.get_author(),
                "date": self.get_publish_date(),
                "keywords": self.get_keywords()
            }
        else:
            return {
                "url": self.url,
                "page": self.domain,
                "title": self.get_title(),
                "text": self.get_main_text(),
                "author": self.get_author(),
                "date": self.get_publish_date()
            }
    
    def locate_article_root(self):
        """Find the DOM subtree that most likely contains the article."""
        soup_copy = BeautifulSoup(str(self.soup), 'html.parser')

        # Quick wins first
        candidates = []
        # Prefer explicit containers
        candidates += soup_copy.select('article, main article, [role="main"] article')
        # Common CMS ids/classes
        candidates += soup_copy.select(
            '#content, .content, #main, .main, .post, #post, .article, #article, .story, #story'
        )
        best_node, best_score = None, 0

        # Evaluate explicit candidates first
        for tag in candidates or soup_copy.find_all(['article', 'section', 'div']):
            score = self.score_node(tag)
            if score > best_score:
                best_score, best_node = score, tag

        return best_node
    
    def get_title(self):
        og_title = self.soup.find('meta', property='og:title') or self.soup.find('meta', attrs={'name': 'og:title'})
        
        if og_title:
            og_text = og_title['content'].strip() if og_title and og_title.get('content') else ''

            return og_text
            
        title_tag = self.soup.find('title')
        h1_tags = self.soup.find_all('h1')

        title_text = title_tag.get_text(strip=True) if title_tag else ''
        h1_text = max((h.get_text(strip=True) for h in h1_tags), key=len, default='') if h1_tags else ''

        candidates = [h1_text, og_text, title_text]
        return max(candidates, key=len) if candidates else ''

    def score_node(self, node):
        paragraphs = node.find_all('p')
        if not paragraphs:
            return 0

        text_len = sum(len(p.get_text(strip=True)) for p in paragraphs)
        link_len = sum(len(a.get_text(strip=True)) for a in node.find_all('a'))
        link_density = link_len / text_len if text_len > 0 else 0

        punctuation_count = sum(p.get_text().count('.') for p in paragraphs)
        bonus = 100 if node.name == 'article' else 0

        return text_len * (1 - link_density) + punctuation_count * 10 + bonus

    def get_main_text(self):
        best_node = None
        best_score = 0
        soup_copy = BeautifulSoup(str(self.soup), 'html.parser')

        for tag in soup_copy.find_all(['article', 'section', 'div']):
            score = self.score_node(tag)
            if score > best_score:
                best_score = score
                best_node = tag

        if best_node:
            cleaned_text = self.clean_node(best_node)
            return cleaned_text.strip()

        # Fallback: collect <p> tags longer than 40 chars
        fallback = [p.get_text(" ", strip=True) for p in soup_copy.find_all('p') if len(p.get_text(" ", strip=True)) > 40]
        return '\n\n'.join(fallback)

    def clean_node(self, node):
        # Remove garbage tags and classes
        for bad in node.find_all(['script', 'style', 'footer', 'nav', 'aside']):
            bad.decompose()
        for bad in node.find_all(class_=lambda c: c and any(x in c.lower() for x in [
            'related', 'promo', 'comment', 'share', 'subscribe', 'footer', 'disclaimer', 'tags', 'author'
        ])):
            bad.decompose()
    
        paragraphs = []
        short_streak = 0
    
        for p in node.find_all('p'):
            txt = p.get_text(" ",strip=True)
            if not txt:
                continue
            if len(p.find_all('a')) > 2:
                continue
            if any(bad_phrase in txt.lower() for bad_phrase in ['read more', 'leave a comment', 'you might also like', 'follow us']):
                continue
    
            if len(txt) < 40:
                short_streak += 1
                if short_streak >= 2:
                    break
                continue
            else:
                short_streak = 0
    
            paragraphs.append(unescape(txt))
            if len(paragraphs) >= 20:
                break
    
        return '\n\n'.join(paragraphs)
        
    def get_author(self):
        if not self.domain == 'mandiner.hu':
            meta = self.soup.find('meta', attrs={'name': 'author'})
            if meta and meta.get('content'):
                print("Got author from meta")
                return meta['content'].strip()
            main_soup = self.soup
            #if self.article_root:
            #    main_soup = self.article_root
            #else:
            #   main_soup = self.soup
            # fallback: common class names
            keywords = ['author', 'szerzo', 'szerző', 'írta']
            exclude = ['szerzoim', 'authors', 'szerzőim', 'szerzok','authorlist','irok','írók']
            
            for tag in main_soup.find_all(True, class_=lambda x: x and any(k in x.lower() for k in keywords)):
                
                cls = ' '.join(tag.get('class', [])).lower()
                if any(bad in cls for bad in exclude):
                    continue
                # Iterate through likely sub-tags
                for child in tag.find_all(['a', 'span', 'div', 'p', 'strong'], recursive=True):
                    # Remove <time> elements entirely before getting text
                    for time_tag in child.find_all('time'):
                        time_tag.decompose()  # removes it from the tree
            
                    text = child.get_text(separator=' ', strip=True)
            
                    # Filter out irrelevant or overly long content
                    if text and len(text.split()) <= 10:
                        return text.split(',')[0].strip()
        
                # Fallback for common class names: get first direct text if no child matches
                text = tag.get_text(separator=' ', strip=True)
                if text and len(text.split()) <= 10:
                    #print("Got author from common class, direct text")
                    return text.split(',')[0].strip()
    
            # fallback: link-based detection
            for a in main_soup.find_all('a', href=True):
                href = a['href'].lower()
                classes = ' '.join(a.get('class', [])).lower()
                if any(k in href or k in classes for k in keywords):
                    #print("Got author from link-based detection")
                    return a.get_text(strip=True)
    
            # Origo/JS-based (window._ain)
            for script in self.soup.find_all("script", {"type": "text/javascript"}):
                if 'window._ain' in script.text:
                    match = re.search(r"window\._ain\s*=\s*({.*?});", script.text, re.DOTALL)
                    if match:
                        try:
                            raw_json = match.group(1).replace("'", '"')
                            json_str = re.sub(r'([,{]\s*)([a-zA-Z0-9_]+)\s*:', r'\1"\2":', raw_json)
                            ain = json.loads(json_str)
                            author = ain.get("authors")
                            if isinstance(author, list):
                                #print("Got author from JS based stuff")
                                return ', '.join(author)
                            return author
                        except json.JSONDecodeError:
                            pass
                        
        # --- JSON-LD structured data ---
        script = self.soup.find("script", {"class": "structured-data", "type": "application/ld+json"})
        if script and script.string:
            try:
                data = json.loads(script.string)
                graph = data.get("@graph", [])
                for item in graph:
                    if item.get("@type") == "NewsArticle":
                        author_info = item.get("author")
                        if isinstance(author_info, dict):
                            #print("Got author from Mandiner JSON-LD (single)")
                            return author_info.get("name", "").strip()
                        elif isinstance(author_info, list):
                            names = [a.get("name", "").strip() for a in author_info if "name" in a]
                            if names:
                                #print("Got author from Mandiner JSON-LD (multi)")
                                return ", ".join(names)
            except json.JSONDecodeError:
                pass
                
        return None

    def get_publish_date(self):
        """3 strategies for publishing date extraction. The strategies
        are descending in accuracy and the next strategy is only
        attempted if a preferred one fails.

        1. Pubdate from URL
        2. Pubdate from metadata
        3. Raw regex searches in the HTML + added heuristics
        """

        def parse_date_str(date_str):
            if date_str:
                try:
                    return parse_date(date_str)
                except (ValueError, OverflowError, AttributeError, TypeError):
                    # near all parse failures are due to URL dates without a day
                    # specifier, e.g. /2014/04/
                    return None

        _STRICT_DATE_REGEX_PREFIX = r'(?<=\W)'
        DATE_REGEX = r'([\./\-_]{0,1}(19|20)\d{2})[\./\-_]{0,1}(([0-3]{0,1}[0-9][\./\-_])|(\w{3,5}[\./\-_]))([0-3]{0,1}[0-9][\./\-]{0,1})?'
        STRICT_DATE_REGEX = _STRICT_DATE_REGEX_PREFIX + DATE_REGEX
        
        date_match = re.search(STRICT_DATE_REGEX, self.url)
        if date_match:
            date_str = date_match.group(0)
            datetime_obj = parse_date_str(date_str)
            if datetime_obj:
                return datetime_obj

        PUBLISH_DATE_TAGS = [
            {'attribute': 'property', 'value': 'rnews:datePublished',
             'content': 'content'},
            {'attribute': 'property', 'value': 'article:published_time',
             'content': 'content'},
            {'attribute': 'name', 'value': 'OriginalPublicationDate',
             'content': 'content'},
            {'attribute': 'itemprop', 'value': 'datePublished',
             'content': 'datetime'},
            {'attribute': 'property', 'value': 'og:published_time',
             'content': 'content'},
            {'attribute': 'name', 'value': 'article_date_original',
             'content': 'content'},
            {'attribute': 'name', 'value': 'publication_date',
             'content': 'content'},
            {'attribute': 'name', 'value': 'sailthru.date',
             'content': 'content'},
            {'attribute': 'name', 'value': 'PublishDate',
             'content': 'content'},
            {'attribute': 'pubdate', 'value': 'pubdate',
             'content': 'datetime'},
            {'attribute': 'name', 'value': 'publish_date',
             'content': 'content'},
        ]
        for tag_config in PUBLISH_DATE_TAGS:
            elements = self.soup.find_all(attrs={tag_config['attribute']: tag_config['value']})
            if elements:
                content = elements[0].get(tag_config['content'])
                if content:
                    try:
                        return parse_date(content)
                    except Exception:
                        continue

        return None

    def get_keywords(self):
        dom = self.domain
        soup = self.soup
        keywords = set()

        # ========== TELEX ==========
        # In head: <meta name="article:tag" content="...">
        if dom == "telex.hu":
            head = soup.head or soup
            for meta in head.find_all("meta", {"name": "article:tag"}):
                content = meta.get("content")
                if content:
                    keywords.add(content.strip())
            # optional: fallback to meta keywords in head
            for meta in head.find_all("meta", {"name": "keywords"}):
                content = meta.get("content")
                if content:
                    for kw in content.split(","):
                        kw = kw.strip()
                        if kw:
                            keywords.add(kw)

        # ========== BLIKK / 444 / 24 / INDEX / HVG / KISKEGYED ==========
        # In head: <meta name="keywords" content="...">
        elif dom in {
            "blikk.hu",
            "444.hu",
            "24.hu",
            "index.hu",
            "hvg.hu",
            "kiskegyed.hu",
        }:
            head = soup.head or soup
            for meta in head.find_all("meta", {"name": "keywords"}):
                content = meta.get("content")
                if content:
                    for kw in content.split(","):
                        kw = kw.strip()
                        if kw:
                            keywords.add(kw)

        # ========== ORIGO ==========
        # In <app-root>: <a class="tag" href="/sport/cimke/...">Text</a>
        elif dom == "origo.hu":
            root = soup.find("app-root") or soup
            # explicit tag class
            for a in root.find_all("a", class_=lambda c: c and "tag" in c.lower()):
                text = a.get_text(strip=True)
                if text:
                    keywords.add(text)
            # links with /cimke/, /tag/ etc. inside app-root only
            for a in root.find_all("a", href=True):
                if TAG_HREF_PATTERNS.search(a["href"]):
                    text = a.get_text(strip=True)
                    if text:
                        keywords.add(text)

        # ========== BORSONLINE ==========
        # In app route: <div class="tags-wrapper"><a class="tag" ...>Text</a>...</div>
        elif dom == "borsonline.hu":
            root = soup.find("app-root") or soup
            wrapper = root.find("div", class_=lambda c: c and "tags-wrapper" in c)
            if wrapper:
                for a in wrapper.find_all("a", class_=lambda c: c and "tag" in c):
                    text = a.get_text(strip=True)
                    if text:
                        keywords.add(text)

        # ========== MANDINER ==========
        # In <app-root>: <div class="trending-topics"><a class="trending-topics-topic" ...>Text</a>...</div>
        elif dom == "mandiner.hu":
            root = soup.find("app-root") or soup
            for a in root.select("div.trending-topics a.trending-topics-topic"):
                text = a.get_text(strip=True)
                if text:
                    keywords.add(text)

        # ========== PORTFOLIO ==========
        # <ul class="tags"><li>Címkék:</li><li><a href="/cimke/...">Text</a></li>...</ul>
        elif dom == "portfolio.hu":
            root = soup
            ul = root.find("ul", class_=lambda c: c and "tags" in c.lower())
            if ul:
                for a in ul.find_all("a"):
                    txt = a.get_text(strip=True).strip(",")
                    if txt:
                        keywords.add(txt)

        # ========== PAPAGENO ==========
        # <script type="application/ld+json" class="yoast-schema-graph">{"@graph":[{"@type":"Article", "keywords":[...]}]}</script>
        elif dom == "papageno.hu":
            for script in soup.find_all("script", {
                "type": "application/ld+json",
                "class": "yoast-schema-graph"
            }):
                if not script.string:
                    continue
                try:
                    data = json.loads(script.string)
                    graph = data.get("@graph", [])
                    for item in graph:
                        if "keywords" in item:
                            kws = item["keywords"]
                            if isinstance(kws, list):
                                for kw in kws:
                                    kw = str(kw).strip().strip("”").strip("“").strip('"')
                                    if kw:
                                        keywords.add(kw)
                            elif isinstance(kws, str):
                                for kw in kws.split(","):
                                    kw = kw.strip().strip("”").strip("“").strip('"')
                                    if kw:
                                        keywords.add(kw)
                except Exception:
                    continue

        # ========== GENERIC FALLBACK (other domains) ==========
        else:
            # 1) meta keywords in head
            head = soup.head or soup
            for meta in head.find_all("meta", {"name": "keywords"}):
                content = meta.get("content")
                if content:
                    for kw in content.split(","):
                        kw = kw.strip()
                        if kw:
                            keywords.add(kw)

            # 2) anchors that look like tags anywhere
            for a in soup.find_all("a", class_=lambda c: c and "tag" in c.lower()):
                text = a.get_text(strip=True)
                if text:
                    keywords.add(text)

            # 3) href-based tag/category links
            for a in soup.find_all("a", href=True):
                if TAG_HREF_PATTERNS.search(a["href"]):
                    text = a.get_text(strip=True)
                    if text:
                        keywords.add(text)

        return list(keywords)
        