import os
from dotenv import load_dotenv

# Загрузка переменных окружения из .env файла
load_dotenv()

# Константы бота
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')  # Токен бота Telegram
if not TOKEN:
    raise ValueError("Не задан TELEGRAM_BOT_TOKEN в .env файле")

# Настройки парсинга
SITEMAP_URL = os.getenv('SITEMAP_URL')  # URL для sitemap.xml
if not SITEMAP_URL:
    raise ValueError("Не задан SITEMAP_URL в .env файле")

# Настройки дайджеста
DIGEST_CHAT_ID = os.getenv('DIGEST_CHAT_ID')  # ID чата для отправки дайджеста
MAX_ARTICLES_IN_DIGEST = int(os.getenv('MAX_ARTICLES_IN_DIGEST', '50'))  # Максимальное число статей в дайджесте
DIGEST_INTERVAL_HOURS = int(os.getenv('DIGEST_INTERVAL_HOURS', '1'))  # Интервал отправки дайджеста (в часах)

# Другие настройки
ADMIN_ID = os.getenv('ADMIN_ID')  # ID администратора (опционально) 