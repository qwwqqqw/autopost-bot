# 🚀 AutoPoster Telegram Bot

---

## Основные возможности

* **ИИ-Рерайтинг** - автоматический рерайт текста парсируемых новостей в один клик. Бот сам переписывает текст в уникальный формат перед публикацией.
* **RSS-Парсер новостей:** - мониторинг новостных лент с удобным предпросмотром через инлайн-кнопки и мгновенной публикацией в канал.
![Демонстрация работы](Desktop-2026.07.30-16.31.49.04-Trim-_online-video-cutter.com_.gif)
* **Отложенный постинг** - публикация постов точно в выбранную дату и время через асинхронный фоновый планировщик.
* **Watermark:** - возможность добавить аккуратный полупрозрачный водяной знака с любым текстом на загружаемые фотографии. 
![Watermark](image.png)
* **Асинхронная БД** -  хранение очереди публикаций и пользовательских настроек.

---

## 📂 Структура проекта

```text
tg_content_bot/
├── config.py              # Загрузка .env настроек и конфигурации
├── main.py                # Запуск бота и фоновой службы планировщика
├── database/
│   └── db.py              # Асинхронная работа с SQLite (очередь, настройки)
├── services/
│   ├── scheduler.py       # Служба фоновой публикации по таймеру
│   ├── watermark.py       # Модуль наложения водяных знаков (Pillow)
│   ├── ai_rewrite.py      # Интеграция с Google Gemini API
│   └── rss_parser.py      # Парсинг лент через BeautifulSoup и httpx
├── handlers/
│   ├── common.py          # Главное меню бота и управление настройками
│   ├── create_post.py     # Обработка времени для отложенных публикаций
│   ├── scheduled.py       # Управление очередью (просмотр и отмена)
│   └── rss_feed.py        # Обработка и ИИ-публикация новостей
├── keyboards/
│   ├── inline.py          # Инлайн-кнопки навигации по RSS и настроек
│   └── reply.py           # Основное reply-меню бота (3 кнопки)
├── requirements.txt       # Список Python-зависимостей
└── .env.example
```

---

## 🚀 Быстрый запуск

### 1. Подготовка окружения
```bash
git clone https://github.com/qwwqqqw/autopost-bot.git
cd tg_content_bot

# Создание и активация виртуального окружения
python -m venv venv
venv\Scripts\activate # Windows
# source venv/bin/activate # Linux/macOS

# Установка зависимостей
pip install -r requirements.txt
```

### 2. Настройка переменных `.env`
Создайте файл `.env` на основе примера `.env.example`:

```env
# Токен Telegram-бота от @BotFather
BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyZ

# ID администратора в Telegram
ADMIN_ID=123456789

# ID или Юзернейм Telegram-канала для публикации
CHANNEL_ID=@my_channel_username

# Водяной знак по умолчанию
DEFAULT_WATERMARK=@MyChannel

# API Ключ Google Gemini для ИИ-рерайта
GEMINI_API_KEY=YOUR_GEMINI_API_KEY_HERE
```

### 3. Запуск бота
```bash
python main.py
```

---

## 📂 Структура проекта

```text
tg_content_bot/
├── config.py              # Загрузка .env настроек и конфигурации
├── main.py                # Запуск бота и фоновой службы планировщика
├── database/
│   └── db.py              # Асинхронная работа с SQLite (очередь, настройки)
├── services/
│   ├── scheduler.py       # Служба фоновой публикации по таймеру
│   ├── watermark.py       # Модуль наложения водяных знаков (Pillow)
│   ├── ai_rewrite.py      # Интеграция с Google Gemini API
│   └── rss_parser.py      # Парсинг лент через BeautifulSoup и httpx
├── handlers/
│   ├── common.py          # Главное меню бота и управление настройками
│   ├── create_post.py     # Обработка времени для отложенных публикаций
│   ├── scheduled.py       # Управление очередью (просмотр и отмена)
│   └── rss_feed.py        # Обработка и ИИ-публикация новостей
├── keyboards/
│   ├── inline.py          # Инлайн-кнопки навигации по RSS и настроек
│   └── reply.py           # Основное reply-меню бота (3 кнопки)
├── requirements.txt       # Список Python-зависимостей
├── .env.example           # Пример конфигурации
└── .gitignore             # Исключения для Git (секреты, venv, бд)
```

---

## 🛠 Технологический стек


* **Python 3.10+** 
* **aiogram 3.x** —  асинхронный фреймворк для Telegram Bot API
* **Gemini API** — ИИ-модель для автоматического рерайта контента
* **Pillow (PIL)** — наложение watermark
* **BeautifulSoup4 & httpx** — асинхронный веб-скрейпинг новостей
* **aiosqlite** — асинхронное взаимодействие с базой данных SQLite
* **python-dotenv** — управление конфигурацией и .env
