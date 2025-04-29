import logging
import schedule
import time
import threading
from datetime import datetime
from telegram.error import TelegramError

logger = logging.getLogger(__name__)

class DigestScheduler:
    def __init__(self, bot, sitemap_parser, digest_chat_id, interval_hours=1, max_articles=10):
        """
        Инициализация планировщика дайджеста
        
        :param bot: Экземпляр бота телеграм
        :param sitemap_parser: Экземпляр парсера sitemap
        :param digest_chat_id: ID чата для отправки дайджеста
        :param interval_hours: Интервал отправки дайджеста (в часах)
        :param max_articles: Максимальное число статей в дайджесте
        """
        self.bot = bot
        self.sitemap_parser = sitemap_parser
        self.digest_chat_id = digest_chat_id
        self.interval_hours = interval_hours
        self.max_articles = max_articles
        self.is_running = False
        self.scheduler_thread = None
    
    def send_digest(self):
        """Отправляет дайджест в Telegram"""
        try:
            logger.info("Начинаем парсинг sitemap.xml...")
            articles = self.sitemap_parser.parse_sitemap()
            
            if not articles:
                logger.info("Нет новых статей для отправки")
                return
            
            logger.info(f"Найдено {len(articles)} новых статей")
            
            digest_text = self.sitemap_parser.format_digest(articles, self.max_articles)
            
            # Отправляем дайджест в Telegram
            if self.digest_chat_id:
                self.bot.send_message(
                    chat_id=self.digest_chat_id,
                    text=digest_text,
                    parse_mode='Markdown',
                    disable_web_page_preview=True
                )
                logger.info(f"Дайджест отправлен в чат {self.digest_chat_id}")
            else:
                logger.warning("Не указан ID чата для отправки дайджеста")
        
        except TelegramError as e:
            logger.error(f"Ошибка Telegram при отправке дайджеста: {e}")
        except Exception as e:
            logger.error(f"Ошибка при формировании и отправке дайджеста: {e}")
    
    def start(self):
        """Запускает планировщик"""
        if self.is_running:
            logger.warning("Планировщик уже запущен")
            return
        
        logger.info(f"Запуск планировщика дайджеста с интервалом {self.interval_hours} час(ов)")
        
        # Планируем запуск каждый час (или другой интервал)
        schedule.every(self.interval_hours).hours.do(self.send_digest)
        
        # Отправляем первый дайджест сразу при запуске
        self.send_digest()
        
        # Запускаем планировщик в отдельном потоке
        def run_scheduler():
            self.is_running = True
            while self.is_running:
                schedule.run_pending()
                time.sleep(1)
                
        self.scheduler_thread = threading.Thread(target=run_scheduler)
        self.scheduler_thread.daemon = True
        self.scheduler_thread.start()
    
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