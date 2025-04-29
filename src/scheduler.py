import logging
import schedule
import time
import threading
import asyncio
from datetime import datetime
from telegram import Bot
from telegram.error import TelegramError

logger = logging.getLogger(__name__)

class DigestScheduler:
    def __init__(self, sitemap_parser, digest_chat_id=None, interval_hours=1, max_articles=10, bot_token=None):
        """
        Инициализация планировщика дайджеста
        
        :param sitemap_parser: Экземпляр парсера sitemap
        :param digest_chat_id: ID чата для отправки дайджеста
        :param interval_hours: Интервал отправки дайджеста (в часах)
        :param max_articles: Максимальное число статей в дайджесте
        :param bot_token: Токен бота для отправки сообщений
        """
        self.bot_token = bot_token
        self.sitemap_parser = sitemap_parser
        self.digest_chat_id = digest_chat_id
        self.interval_hours = interval_hours
        self.max_articles = max_articles
        self.is_running = False
        self.scheduler_thread = None
    
    async def send_digest_async(self):
        """Отправляет дайджест в Telegram (асинхронная версия)"""
        try:
            logger.info("Начинаем парсинг sitemap.xml...")
            articles = self.sitemap_parser.parse_sitemap()
            
            if not articles:
                logger.info("Нет новых статей для отправки")
                return
            
            logger.info(f"Найдено {len(articles)} новых статей")
            
            digest_text = self.sitemap_parser.format_digest(articles, self.max_articles)
            
            # Отправляем дайджест в Telegram
            if self.digest_chat_id and self.bot_token:
                bot = Bot(token=self.bot_token)
                await bot.send_message(
                    chat_id=self.digest_chat_id,
                    text=f'📰 Свежий дайджест:\n\n{digest_text}',
                    parse_mode='Markdown',
                    disable_web_page_preview=True
                )
                logger.info(f"Дайджест отправлен в чат {self.digest_chat_id}")
            else:
                logger.warning("Не указан ID чата или токен бота для отправки дайджеста")
        
        except TelegramError as e:
            logger.error(f"Ошибка Telegram при отправке дайджеста: {e}")
        except Exception as e:
            logger.error(f"Ошибка при формировании и отправке дайджеста: {e}")
    
    def send_digest(self):
        """Запускает асинхронную функцию отправки дайджеста"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self.send_digest_async())
        finally:
            loop.close()
    
    def start(self):
        """Запускает планировщик"""
        if self.is_running:
            logger.warning("Планировщик уже запущен")
            return
        
        if not self.bot_token:
            logger.error("Невозможно запустить планировщик: не указан токен бота")
            return
            
        if not self.digest_chat_id:
            logger.warning("Не указан ID чата для отправки дайджеста")
            return
        
        logger.info(f"Запуск планировщика дайджеста с интервалом {self.interval_hours} час(ов)")
        
        # Планируем запуск каждый час (или другой интервал)
        schedule.every(self.interval_hours).hours.do(self.send_digest)
        
        # Запускаем планировщик в отдельном потоке
        def run_scheduler():
            self.is_running = True
            while self.is_running:
                schedule.run_pending()
                time.sleep(1)
                
        self.scheduler_thread = threading.Thread(target=run_scheduler)
        self.scheduler_thread.daemon = True
        self.scheduler_thread.start()
        
        logger.info(f"Планировщик запущен. Следующий дайджест будет отправлен через {self.interval_hours} час(ов)")
    
    def stop(self):
        """Останавливает планировщик"""
        if not self.is_running:
            logger.warning("Планировщик уже остановлен")
            return
        
        logger.info("Остановка планировщика дайджеста")
        self.is_running = False
        schedule.clear()
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=1)
        logger.info("Планировщик дайджеста остановлен") 