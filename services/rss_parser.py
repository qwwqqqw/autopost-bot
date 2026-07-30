import httpx
import re
import logging
import asyncio
from bs4 import BeautifulSoup
from typing import List, Dict
from config import NEWS_URL

logger = logging.getLogger(__name__)

async def fetch_article_data(client: httpx.AsyncClient, href: str, title: str) -> Dict[str, str]:
    try:
        response = await client.get(href)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            
            og_img = soup.find("meta", property="og:image")
            img_url = og_img["content"] if og_img else None
            
            paragraphs = soup.find_all("p")
            import re
            def clean_text(p_tag):
                t = p_tag.get_text()
                return re.sub(r'\s+', ' ', t).strip()
                
            full_text = "\n\n".join([clean_text(p) for p in paragraphs if len(clean_text(p)) > 40])
            
            date_div = soup.find("div", class_=lambda c: c and "date" in str(c))
            date_str = date_div.get_text(strip=True) if date_div else ""
            if date_str:
                import re
                def repl(m):
                    hh = int(m.group(1))
                    mm = m.group(2)
                    new_hh = (hh + 3) % 24
                    return f'{new_hh:02d}:{mm}'
                date_str = re.sub(r'(\d{1,2}):(\d{2})', repl, date_str)
            
            if not full_text:
                full_text = title

            return {
                "title": title,
                "link": href,
                "summary": full_text,
                "source": "РБК (Животные)",
                "image": img_url,
                "date": date_str
            }
    except Exception as e:
        logger.error(f"Ошибка при парсинге статьи {href}: {e}")
        
    return {
        "title": title,
        "link": href,
        "summary": title,
        "source": "РБК (Животные)",
        "image": None,
        "date": ""
    }

async def fetch_rbc_pets_news(limit: int = 10) -> List[Dict[str, str]]:
    """
    Парсинг новостей (по умолчанию https://www.rbc.ru/life/tag/pets).
    Возвращает список словарей: title, link, summary, source, image.
    """
    url = NEWS_URL
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7"
    }

    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True, headers=headers) as client:
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
                
                tasks = [fetch_article_data(client, h, t) for h, t in found_links]
                articles = await asyncio.gather(*tasks)
                return list(articles)

    except Exception as e:
        logger.error(f"Ошибка при парсинге: {e}")

    return []
