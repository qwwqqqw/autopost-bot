import httpx
import re
import logging
import asyncio
from bs4 import BeautifulSoup
from typing import List, Dict
import random

logger = logging.getLogger(__name__)

async def fetch_article_text(client: httpx.AsyncClient, href: str, title: str, source_name: str, css_selector: str = "p") -> Dict[str, str]:
    try:
        response = await client.get(href)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            
            clean_img_tag = soup.select_one("div.photoview__open img, img.picture__image")
            if clean_img_tag and clean_img_tag.has_attr("src"):
                img_url = clean_img_tag["src"]
            else:
                og_img = soup.find("meta", property="og:image")
                img_url = og_img["content"] if og_img else None
                
                if img_url and ("share_" in img_url or "/sharing/" in img_url):
                    img_url = None
            
            paragraphs = soup.select(css_selector)
            def clean_text(p_tag):
                t = p_tag.get_text()
                return re.sub(r'\s+', ' ', t).strip()
                
            full_text = "\n\n".join([clean_text(p) for p in paragraphs if len(clean_text(p)) > 20])
            full_text = re.sub(r'^[А-ЯЁа-яёA-Za-z\s,0-9]+[-—]\s*РИА Новости\.?\s*', '', full_text)
            
            if not full_text:
                full_text = title

            return {
                "title": title,
                "link": href,
                "summary": full_text,
                "source": source_name,
                "image": img_url,
                "date": ""
            }
    except Exception as e:
        logger.error(f"Ошибка при парсинге статьи {href}: {e}")
        
    return {
        "title": title,
        "link": href,
        "summary": title,
        "source": source_name,
        "image": None,
        "date": ""
    }

async def fetch_rbc_news(client: httpx.AsyncClient, limit: int = 5) -> List[Dict[str, str]]:
    url = "https://www.rbc.ru/life/tag/pets"
    articles = []
    try:
        response = await client.get(url)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            links_seen = set()
            found_links = []
            for a in soup.find_all("a", href=True):
                href = a.get("href", "")
                if "/life/news/" not in href:
                    continue
                if not href.startswith("http"):
                    href = "https://www.rbc.ru" + href
                if href in links_seen:
                    continue
                title = a.get_text(strip=True)
                if not title or len(title) < 10:
                    continue
                links_seen.add(href)
                found_links.append((href, title))
                if len(found_links) >= limit:
                    break
            
            tasks = [fetch_article_text(client, h, t, "РБК", "p") for h, t in found_links]
            articles = list(await asyncio.gather(*tasks))
    except Exception as e:
        logger.error(f"Ошибка RBC: {e}")
    return articles

async def fetch_ria_news(client: httpx.AsyncClient, limit: int = 5) -> List[Dict[str, str]]:
    url = "https://ria.ru/tag_zhivotnye_3/"
    articles = []
    try:
        response = await client.get(url)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            links_seen = set()
            found_links = []
            for a in soup.find_all("a", class_="list-item__title", href=True):
                href = a.get("href", "")
                if not href.startswith("http"):
                    href = "https://ria.ru" + href
                if href in links_seen:
                    continue
                title = a.get_text(strip=True)
                if not title or len(title) < 10:
                    continue
                links_seen.add(href)
                found_links.append((href, title))
                if len(found_links) >= limit:
                    break
            
            tasks = [fetch_article_text(client, h, t, "РИА Новости", "div.article__block[data-type='text']") for h, t in found_links]
            articles = list(await asyncio.gather(*tasks))
    except Exception as e:
        logger.error(f"Ошибка RIA: {e}")
    return articles

async def fetch_lenta_news(client: httpx.AsyncClient, limit: int = 5) -> List[Dict[str, str]]:
    url = "https://lenta.ru/rubrics/life/animals/"
    articles = []
    try:
        response = await client.get(url)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            links_seen = set()
            found_links = []
            for a in soup.find_all("a", href=True):
                href = a.get("href", "")
                if "/news/" not in href and "/articles/" not in href:
                    continue
                if not href.startswith("http"):
                    href = "https://lenta.ru" + href
                if href in links_seen:
                    continue
                title = a.get_text(strip=True)
                if not title or len(title) < 10:
                    continue
                links_seen.add(href)
                found_links.append((href, title))
                if len(found_links) >= limit:
                    break
            
            tasks = [fetch_article_text(client, h, t, "Lenta.ru", "p.topic-body__content-text") for h, t in found_links]
            articles = list(await asyncio.gather(*tasks))
    except Exception as e:
        logger.error(f"Ошибка Lenta: {e}")
    return articles

async def fetch_all_news(limit_per_source: int = 5) -> List[Dict[str, str]]:
    """Собирает новости со всех источников и возвращает перемешанный список."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7"
    }
    
    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True, headers=headers) as client:
        results = await asyncio.gather(
            fetch_rbc_news(client, limit_per_source),
            fetch_ria_news(client, limit_per_source),
            fetch_lenta_news(client, limit_per_source)
        )
    
    all_articles = []
    for r in results:
        all_articles.extend(r)
        
    random.shuffle(all_articles)
    return all_articles

# Алиас для обратной совместимости с существующим UI (если вызывается из rss_feed.py)
async def fetch_rbc_pets_news(limit: int = 10) -> List[Dict[str, str]]:
    return await fetch_all_news(limit // 3 + 1)
