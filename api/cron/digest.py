from http.server import BaseHTTPRequestHandler
import asyncio
import json
import logging
import os
import sys
from datetime import datetime

# Добавляем корневую директорию проекта в путь для импорта
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from telegram import Bot
from src.config import TOKEN, SITEMAP_URL, DIGEST_CHAT_ID, MAX_ARTICLES_IN_DIGEST
from src.sitemap_parser import SitemapParser

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Глобальные переменные
sitemap_parser = SitemapParser(SITEMAP_URL)

async def send_digest():
    """Отправляет дайджест в Telegram"""
    # Проверяем, задан ли ID чата для отправки
    chat_id = os.environ.get('DIGEST_CHAT_ID', DIGEST_CHAT_ID)
    
    if not chat_id:
        logger.warning("Не указан ID чата для отправки дайджеста")
        return {"status": "error", "message": "Не указан ID чата для отправки дайджеста"}
    
    try:
        logger.info("Начинаем парсинг sitemap.xml...")
        articles = sitemap_parser.parse_sitemap()
        
        if not articles:
            logger.info("Нет новых статей для отправки")
            return {"status": "success", "message": "Нет новых статей для отправки"}
        
        logger.info(f"Найдено {len(articles)} новых статей")
        
        # Форматируем дайджест
        digest_text = sitemap_parser.format_digest(articles, MAX_ARTICLES_IN_DIGEST)
        
        # Создаем экземпляр бота
        bot = Bot(token=TOKEN)
        
        # Отправляем дайджест в Telegram
        await bot.send_message(
            chat_id=chat_id,
            text=digest_text,
            parse_mode='Markdown',
            disable_web_page_preview=True
        )
        
        logger.info(f"Дайджест отправлен в чат {chat_id}")
        return {"status": "success", "message": f"Дайджест отправлен в чат {chat_id}"}
        
    except Exception as e:
        error_message = f"Ошибка при формировании и отправке дайджеста: {e}"
        logger.error(error_message)
        return {"status": "error", "message": error_message}

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Для Vercel Cron, нам нужно отправить ответ сразу, 
        # но продолжить выполнение функции в фоне
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        
        # Отправляем первичный ответ
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.wfile.write(json.dumps({
            "status": "processing", 
            "message": f"Запуск обработки дайджеста в {now}"
        }).encode('utf-8'))
        
        # Выполняем отправку дайджеста асинхронно
        result = asyncio.run(send_digest())
        
        # Логируем результат (хотя клиент его уже не получит)
        logger.info(f"Результат отправки дайджеста: {result}") 