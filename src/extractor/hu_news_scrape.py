import requests
import re

from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from newspaper import Article #newspaper3k
import pandas as pd
import json
from datetime import datetime

RELEVANT_SITES = ['https://www.telex.hu'
                                        ,'https://www.blikk.hu'
                                        ,'https://www.origo.hu'
                                        ,'https://444.hu'
                                        ,'https://24.hu'
                                        ,'https://mandiner.hu'
                                        ,'https://index.hu'
                                        ,'https://www.portfolio.hu'
                                        ,'https://borsonline.hu'
                                        ,'https://hvg.hu'
                                        ,'https://kiskegyed.hu'
                                        ,'https://www.rtl.hu'
                                        ,'https://www.femina.hu'
                                        ,'https://www.nemzetisport.hu'
                                        ,'https://www.nlc.hu'
                                        ,'https://www.ripost.hu'
                                        ,'https://www.penzcentrum.hu' # TOP 17 useable site by https://bpdigital.hu/seo-szempontbol-legertekesebb-magyar-weboldalak/
                                       ]

def filter_links(soup, prefix):
    """
    Szűri a valószínű hírcikk linkeket különböző hírportálokról.
    """
    domain = urlparse(prefix).netloc.replace('www.', '')
    filtered = set()

    for a_tag in soup.find_all('a', href=True):
        href = a_tag['href']

        href_domain = urlparse(href).netloc.replace('www.', '')
        
        if href_domain.startswith(domain):
            full_url = href
        elif href.startswith('/'):
            full_url = prefix + href
        else:
            continue
        
        try:
            parsed = urlparse(full_url)
            if domain not in parsed.netloc:
                continue

            if re.search(r'https?://', parsed.path):
                continue
            
            path = parsed.path.strip('/')
            path_parts = path.split('/')

            if len(path_parts) < 2:
                continue

            # Kizárandó részek
            excluded = [
                'category', 'categories', 'author', 'szerzo', 'tag', 'video', 'videos', 'galeria', 'shorts',
                'feed', 'hirek', 'kapcsolat', 'adatvedelem', 'rolunk', 'mediaajanlat', 'tamogatas',
                'szerzoi-jog', 'dokumentum', 'velemeny', 'etikai', 'aszf', 'streaming', 'brandchannel',
                'brandcontent', 'pr-cikkek', 'cimke', 'nagyitas', 'dosszie', 'arfolyam','rovat', 'impresszum', 'rss'
            ]
            if any(part in excluded for part in path_parts):
                continue

            # Dátumminta (választható)
            has_date = any(re.fullmatch(r'\d{4}/\d{2}/\d{2}', p) or re.fullmatch(r'\d{8}', p) for p in path_parts)

            # Slug-elem vizsgálata (utolsó és utolsó előtti elem)
            slug_candidates = path_parts[-2:] if len(path_parts) >= 2 else [path_parts[-1]]
            has_good_slug = False
            for slug in slug_candidates:
                if '-' in slug and len(slug) >= 20 and slug.count('-') >= 2:
                    has_good_slug = True
                    break
            
            # Végső feltétel
            if has_good_slug or has_date or len(path_parts)>2:
                filtered.add(full_url)

        except:
            continue

    return list(filtered)

def get_relevant_links_of_site(site_url):
    response = requests.get(site_url)
    soup = BeautifulSoup(response.text, "html.parser")

    return filter_links(soup, site_url)

def get_multiple_site_links(site_lst):
    result_lst = []
    for site in site_lst:
        result_lst += get_relevant_links_of_site(site)
    return result_lst

def extract_article_data(url, only_today=False):
    try:
        article = Article(url, language='hu')
        article.download()
        article.parse()
        soup = BeautifulSoup(article.html, 'html.parser')

        article_date = article.publish_date.date()
        
        if only_today and article_date != datetime.today().date():
            return {"url": url, "error": "Not published today"}

        body = soup.body
        if body:
                noise_keywords = ['popular', 'related', 'ajanlott', 'more-tags']
                structure_keywords = ['nav', 'menu', 'header', 'footer', 'bottom', 'site-footer']
                for tag in body.find_all():
                    if tag.name == 'app-root':
                        continue
                    if tag.attrs:
                        attrs = ' '.join(map(str, tag.attrs.values())).lower()
                        if any(k in attrs for k in noise_keywords + structure_keywords) or tag.name in ['nav', 'footer', 'header']:
                            tag.decompose()

        # --- Author Extraction ---
        author = None
        author_meta = soup.find('meta', {'name': 'author'})
        if author_meta:
            author = author_meta.get('content')
        elif article.authors:
            author = article.authors

        # --- Keyword Extraction from Meta ---
        keywords = []
        keywords_meta = soup.find('meta', {'name': 'keywords'})
        if keywords_meta:
            keywords = [kw.strip() for kw in keywords_meta.get('content', '').split(',') if kw.strip()]

        # --- Fallback: og:tag metatags ---
        if not keywords:
            tags_meta = soup.find_all('meta', {'property': 'article:tag'})
            keywords = [tag.get('content') for tag in tags_meta if tag.get('content')]

        # --- Fallback: Extract from JavaScript object (e.g., Origo-style window._ain) ---
        if not author or not keywords:
            for script in soup.find_all("script", {"type": "text/javascript"}):
                if 'window._ain' in script.text:
                    match = re.search(r"window\._ain\s*=\s*({.*?});", script.text, re.DOTALL)
                    if match:
                        raw_json = match.group(1)
                        try:
                            json_str = re.sub(r'([,{]\s*)([a-zA-Z0-9_]+)\s*:', r'\1"\2":', raw_json.replace("'", '"'))
                            ain_data = json.loads(json_str)
                            author = author or ain_data.get("authors")
                            tags = ain_data.get("tags", '')
                            if not keywords and tags:
                                keywords = tags.split(', ')
                        except json.JSONDecodeError:
                            pass
                    break
        
        # --- Fallback: Author from DOM, link-based like tag detection ---
        if not author:
            valid_author_keywords = ['author', 'szerzo', 'szerző', 'írta']
            
            # --- 1. Keresés linkek alapján (a href + class alapján) ---
            for container in soup.find_all(['div', 'section', 'ul']):
                links = container.find_all('a', href=True)
                author_links = []
                for a in links:
                    href = a['href'].lower()
                    classes = ' '.join(a.get('class', [])).lower()
                    if any(kw in href for kw in valid_author_keywords) or any(kw in classes for kw in valid_author_keywords):
                        author_links.append(a)
                if author_links:
                    for a in author_links:
                        author = a.get_text(strip=True)
                        if author:
                            break
                if author:
                    break
        
            # --- 2. Keresés class nevek alapján bárhol a DOM-ban ---
            if not author:
                author_class_candidates = soup.find_all(class_=lambda c: c and ("author-name" in c.lower() or "author_name" in c.lower()))
                for tag in author_class_candidates:
                    text = tag.get_text(strip=True)
                    if text:
                        author = text
                        break

        # --- Fallback: Keywords from link structure ---
        if not keywords:

            for container in soup.find_all(['div', 'section', 'ul']):
                tag_links = [a for a in container.find_all('a', href=True)
                             if any(v in urlparse(a['href']).path.lower() for v in ['tag', 'cimke', 'category'])]
                if len(tag_links) >= 2:
                    keywords = list({a.get_text(strip=True) for a in tag_links if a.get_text(strip=True)})
                    break

        return {
            "url": url,
            "title": article.title,
            "text": article.text,
            "author": author,
            "page": url.split("//")[-1].split("/")[0].split(".")[-2],
            "date": article_date,
            "keywords": keywords,
        }

    except Exception as e:
        return {"url": url, "error": str(e)}