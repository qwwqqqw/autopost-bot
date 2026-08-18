import httpx
import re
import logging
from bs4 import BeautifulSoup
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

async def fetch_tg_channel_posts(channel_name: str, limit: int = 5) -> List[Dict]:
    """
    Парсит последние посты из публичного Telegram канала через t.me/s/
    Возвращает список словарей: [{'link': url, 'text': text, 'photo': photo_url, 'video': video_url}, ...]
    """
    url = f"https://t.me/s/{channel_name.replace('@', '')}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
    }
    
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(url, headers=headers)
            if response.status_code != 200:
                logger.error(f"Ошибка получения канала {channel_name}: HTTP {response.status_code}")
                return []
            
            soup = BeautifulSoup(response.text, "html.parser")
            messages = soup.find_all("div", class_="tgme_widget_message")
            
            results = []
            
            for msg in reversed(messages):
                if len(results) >= limit:
                    break
                    
                date_link_tag = msg.find("a", class_="tgme_widget_message_date")
                if not date_link_tag:
                    continue
                post_link = date_link_tag.get("href")
                
                text_tag = msg.find("div", class_="tgme_widget_message_text")
                text = ""
                if text_tag:
                    for br in text_tag.find_all("br"):
                        br.replace_with("\n")
                    text = text_tag.get_text().strip()
                
                if not text:
                    continue
                
                photo_urls = []
                photo_wraps = msg.find_all("a", class_="tgme_widget_message_photo_wrap")
                for photo_wrap in photo_wraps:
                    if photo_wrap.has_attr("style"):
                        style = photo_wrap["style"]
                        match = re.search(r"background-image:url\('(.+?)'\)", style)
                        if match:
                            photo_urls.append(match.group(1))
                
                video_url = None
                video_tag = msg.find("video")
                if video_tag:
                    video_url = video_tag.get("src") or video_tag.get("data-src")
                if not video_url:
                    video_player = msg.find("div", class_="tgme_widget_message_video_player")
                    if video_player:
                        inner_video = video_player.find("video")
                        if inner_video:
                            video_url = inner_video.get("src") or inner_video.get("data-src")
                if video_url:
                    photo_urls = []
                
                results.append({
                    "link": post_link,
                    "text": text,
                    "photos": photo_urls,
                    "video": video_url,
                    "source": channel_name
                })
            
            return list(reversed(results))
            
    except Exception as e:
        logger.error(f"Ошибка парсинга канала {channel_name}: {e}")
        return []
