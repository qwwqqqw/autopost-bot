import httpx
import logging
from config import AI_API_KEY

logger = logging.getLogger(__name__)

async def rewrite_text_with_gemini(text: str) -> str:
    """
    Автоматический рерайт текста новости/поста с помощью Google Gemini API.
    Делает текст уникальным, добавляет эмодзи и форматирует под Telegram.
    """
    if not AI_API_KEY:
        logger.warning("AI_API_KEY не установлен. Рерайт пропущен.")
        return text
        
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={AI_API_KEY}"
    
    prompt = (
        "Ты — профессиональный SMM-редактор популярного Telegram-канала. "
        "Сделай очень краткий выжимку-рерайт текста ниже: выдели самую основную суть и напиши её буквально в 2-3 коротких предложениях. "
        "Текст должен быть увлекательным и легко читаться. "
        "ОТВЕЧАЙ ТОЛЬКО ГОТОВЫМ ТЕКСТОМ БЕЗ ПРИВЕТСТВИЙ, ПОЯСНЕНИЙ И ЛИШНЕЙ ВОДЫ.\n\n"
        f"Исходный текст:\n{text}"
    )
    
    payload = {
        "contents": [
            {
                "parts": [{"text": prompt}]
            }
        ]
    }
    
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(url, json=payload)
            if response.status_code == 200:
                data = response.json()
                result = data["candidates"][0]["content"]["parts"][0]["text"]
                return result.strip()
            else:
                logger.error(f" API Error {response.status_code}: {response.text}")
                return text
    except Exception as e:
        logger.error(f"Ошибка при вызове API: {e}")
        return text
