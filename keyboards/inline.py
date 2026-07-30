from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_post_editor_keyboard(has_photo: bool, watermark_applied: bool) -> InlineKeyboardMarkup:
    """Клавиатура управления создаваемым постом перед публикацией."""
    buttons = []
    
    buttons.append([InlineKeyboardButton(text="ИИ-Рерайт", callback_data="ai_rewrite_post")])
    buttons.append([
        InlineKeyboardButton(text="Изменить текст", callback_data="edit_text_content"),
        InlineKeyboardButton(text="Изменить фото", callback_data="edit_photo_content")
    ])
    
    if has_photo:
        wm_text = "Удалить Watermark" if watermark_applied else "Добавить Watermark"
        buttons.append([InlineKeyboardButton(text=wm_text, callback_data="toggle_watermark")])
        
    buttons.append([
        InlineKeyboardButton(text="Опубликовать сейчас", callback_data="publish_now"),
        InlineKeyboardButton(text="Запланировать", callback_data="schedule_time")
    ])
    buttons.append([InlineKeyboardButton(text="Отменить создание", callback_data="cancel_post")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_rss_navigation_keyboard(index: int, total_count: int) -> InlineKeyboardMarkup:
    """Клавиатура навигации по новостям про животных (стрелочки влево/вправо)."""
    prev_idx = index - 1 if index > 0 else total_count - 1
    next_idx = index + 1 if index < total_count - 1 else 0
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="◀️", callback_data=f"rss_nav_{prev_idx}"),
                InlineKeyboardButton(text=f"[{index + 1}/{total_count}]", callback_data="rss_noop"),
                InlineKeyboardButton(text="▶️", callback_data=f"rss_nav_{next_idx}")
            ],
            [
                InlineKeyboardButton(text="Опубликовать в канал", callback_data=f"rss_pub_{index}"),
                InlineKeyboardButton(text="Запланировать", callback_data=f"rss_sched_{index}")
            ]
        ]
    )
    return keyboard

def get_settings_keyboard(watermark_enabled: bool) -> InlineKeyboardMarkup:
    """Клавиатура управления настройками."""
    wm_status = "✅ Вкл" if watermark_enabled else "❌ Выкл"
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=f"Водяной знак: {wm_status}", callback_data="toggle_setting_watermark")
            ],
            [
                InlineKeyboardButton(text="Изменить текст водяного знака", callback_data="edit_setting_watermark_text")
            ]
        ]
    )
    return keyboard

def get_scheduled_posts_keyboard(posts: list) -> InlineKeyboardMarkup:
    """Список отложенных постов с кнопками взаимодействия."""
    buttons = []
    for post in posts:
        post_id = post["id"]
        time_str = post["publish_time"]
        snippet = (post["content_text"] or "Фото пост")[:25]
        buttons.append([
            InlineKeyboardButton(text=f"📌 #{post_id} [{time_str}] {snippet}...", callback_data=f"view_post_{post_id}"),
            InlineKeyboardButton(text="🗑", callback_data=f"cancel_sched_{post_id}")
        ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)
