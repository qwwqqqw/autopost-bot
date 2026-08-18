from PIL import Image, ImageDraw, ImageFont, ImageEnhance
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

def add_watermark(input_path: str, watermark_text: str = "@MyChannel", output_path: str = None) -> str:
    """
    Наложение полупрозрачного брендированного водяного знака на изображение.
    Возвращает путь к сохраненному итоговому файлу.
    """
    if not output_path:
        p = Path(input_path)
        output_path = str(p.parent / f"wm_{p.name}")
        
    try:
        base_image = Image.open(input_path).convert("RGBA")
        
        watermark = Image.new("RGBA", base_image.size, (255, 255, 255, 0))
        draw = ImageDraw.Draw(watermark)
        
        width, height = base_image.size
        
        font_size = max(18, int(width / 25))
        
        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except OSError:
            font = ImageFont.load_default()
            
        bbox = draw.textbbox((0, 0), watermark_text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        margin = 20
        x = width - text_width - margin
        y = height - text_height - margin
        
        padding = 10
        draw.rectangle(
            [x - padding, y - padding, x + text_width + padding, y + text_height + padding],
            fill=(0, 0, 0, 140)
        )
        draw.text((x, y), watermark_text, font=font, fill=(255, 255, 255, 220))
        
        # Объединяем слои
        out = Image.alpha_composite(base_image, watermark)
        out_rgb = out.convert("RGB")
        
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        out_rgb.save(output_path, "JPEG", quality=92)
        return output_path
    except Exception as e:
        logger.error(f"Ошибка при нанесении watermark: {e}")
        return input_path
