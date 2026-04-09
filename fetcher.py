"""
Fetching de noticias desde RSS feeds, NewsAPI y archive.ph para paywalls.
"""
import os
import time
import requests
import feedparser
from datetime import datetime, timedelta, timezone
from bs4 import BeautifulSoup
from config import RSS_FEEDS, NEWSAPI_QUERIES, SELECTION

NEWSAPI_KEY = os.getenv("NEWS_API_KEY")
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; NewsCuratorBot/1.0)"}


def fetch_rss_feeds() -> list[dict]:
    """Trae artículos de todos los RSS feeds configurados, publicados en las últimas 48hs."""
    articles = []
    cutoff = datetime.now(timezone.utc) - timedelta(hours=48)

    for feed_cfg in RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_cfg["url"])
            for entry in feed.entries[:15]:  # máximo 15 por feed
                published = _parse_date(entry)
                if published and published < cutoff:
                    continue

                article = {
                    "title": entry.get("title", "").strip(),
                    "url": entry.get("link", ""),
                    "summary": _clean_html(entry.get("summary", entry.get("description", ""))),
                    "source": feed_cfg["name"],
                    "category_hint": feed_cfg["category"],
                    "published": published.isoformat() if published else "",
                }
                if article["title"] and article["url"]:
                    articles.append(article)

            print(f"  RSS [{feed_cfg['name']}]: {len(feed.entries)} entradas")
        except Exception as e:
            print(f"  RSS [{feed_cfg['name']}] error: {e}")

    return articles


def fetch_newsapi() -> list[dict]:
    """Trae artículos de NewsAPI usando las queries configuradas."""
    if not NEWSAPI_KEY:
        print("  NewsAPI: no hay API key configurada")
        return []

    articles = []
    seen_urls = set()
    from_date = (datetime.now(timezone.utc) - timedelta(hours=48)).strftime("%Y-%m-%dT%H:%M:%SZ")

    for query_cfg in NEWSAPI_QUERIES:
        try:
            resp = requests.get(
                "https://newsapi.org/v2/everything",
                params={
                    "q": query_cfg["q"],
                    "from": from_date,
                    "sortBy": "relevancy",
                    "pageSize": 10,
                    "language": "en",
                    "apiKey": NEWSAPI_KEY,
                },
                timeout=10,
            )
            data = resp.json()

            if data.get("status") != "ok":
                print(f"  NewsAPI [{query_cfg['q'][:40]}...] error: {data.get('message')}")
                continue

            for item in data.get("articles", []):
                url = item.get("url", "")
                if url in seen_urls or "[Removed]" in item.get("title", ""):
                    continue
                seen_urls.add(url)

                articles.append({
                    "title": item.get("title", "").strip(),
                    "url": url,
                    "summary": item.get("description", "") or item.get("content", ""),
                    "source": item.get("source", {}).get("name", "NewsAPI"),
                    "category_hint": query_cfg["category"],
                    "published": item.get("publishedAt", ""),
                })

            print(f"  NewsAPI [{query_cfg['category']}]: {len(data.get('articles', []))} artículos")
            time.sleep(0.3)  # rate limiting
        except Exception as e:
            print(f"  NewsAPI [{query_cfg['category']}] error: {e}")

    return articles


def try_fetch_full_content(url: str) -> str:
    """
    Intenta obtener el contenido completo del artículo.
    Para medios con paywall (FT, Economist), prueba archive.ph primero.
    """
    PAYWALLED_DOMAINS = ["ft.com", "economist.com", "wsj.com", "bloomberg.com", "nytimes.com", "theverge.com", "wired.com"]
    is_paywalled = any(domain in url for domain in PAYWALLED_DOMAINS)

    if is_paywalled:
        content = _fetch_via_archive(url)
        if content:
            return content

    return _fetch_direct(url)


def _fetch_via_archive(url: str) -> str:
    """Intenta leer el artículo via archive.ph (requiere URL con timestamp, no página de espera)."""
    import re
    try:
        archive_url = f"https://archive.ph/newest/{url}"
        resp = requests.get(archive_url, headers=HEADERS, timeout=15, allow_redirects=True)
        # Exige timestamp en la URL final: archive.ph/20241231123456/... → artículo real
        # Si queda como /newest/ o /wip/ → página de espera, descartar
        if resp.status_code == 200 and re.search(r"archive\.ph/\d{14}/", resp.url):
            soup = BeautifulSoup(resp.text, "lxml")
            for tag in soup(["script", "style", "nav", "header", "footer", "aside"]):
                tag.decompose()
            text = soup.get_text(separator=" ", strip=True)
            if len(text) > 500:
                return text[:3000]
    except Exception:
        pass

    return ""


def _fetch_direct(url: str) -> str:
    """Fetching directo del artículo."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "lxml")
            for tag in soup(["script", "style", "nav", "header", "footer", "aside"]):
                tag.decompose()
            # Intentar extraer solo el cuerpo del artículo
            article_tag = soup.find("article") or soup.find(class_=lambda c: c and "article" in c.lower())
            target = article_tag or soup.find("body") or soup
            text = target.get_text(separator=" ", strip=True)
            return text[:3000] if len(text) > 200 else ""
    except Exception:
        pass
    return ""


def _parse_date(entry) -> datetime | None:
    """Parsea la fecha de publicación de una entrada RSS."""
    for field in ["published_parsed", "updated_parsed"]:
        t = getattr(entry, field, None)
        if t:
            try:
                return datetime(*t[:6], tzinfo=timezone.utc)
            except Exception:
                pass
    return None


def _clean_html(text: str) -> str:
    """Limpia HTML del summary del RSS."""
    if not text:
        return ""
    soup = BeautifulSoup(text, "lxml")
    return soup.get_text(separator=" ", strip=True)[:1000]
