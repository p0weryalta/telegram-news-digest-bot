import os
import json
import logging
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
from sitemap_parser import SitemapParser
from dotenv import load_dotenv
from http.server import BaseHTTPRequestHandler
from io import BytesIO

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Загрузка переменных окружения
load_dotenv()

# Получение токена бота из переменных окружения
BOT_TOKEN = os.getenv('TELEGRAM_TOKEN')
SITEMAP_URL = os.getenv('SITEMAP_URL', 'https://www.ozon.ru/sitemap.xml')

# Проверка, что токен получен
if not BOT_TOKEN:
    logger.error("TELEGRAM_TOKEN не найден в переменных окружения!")
    
parser = SitemapParser(SITEMAP_URL)

async def send_digest_to_chat(chat_id):
    """Отправить дайджест в указанный чат"""
    try:
        articles = parser.parse_sitemap()
        if not articles:
            message = "Нет новых статей для отображения в дайджесте."
        else:
            message = parser.format_digest(articles)
        
        # Отправляем сообщение через API Telegram
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        data = {
            'chat_id': chat_id,
            'text': message,
            'parse_mode': 'Markdown'
        }
        response = requests.post(url, json=data)
        response.raise_for_status()
        logger.info(f"Дайджест успешно отправлен в чат {chat_id}")
        return True
    except Exception as e:
        logger.error(f"Ошибка при отправке дайджеста: {e}")
        return False

async def start_command(update: Update, context: CallbackContext):
    """Обработчик команды /start"""
    await update.message.reply_text(
        "👋 Привет! Я бот для получения дайджеста новостей.\n\n"
        "Используйте команду /digest, чтобы получить текущий дайджест."
    )

async def digest_command(update: Update, context: CallbackContext):
    """Обработчик команды /digest"""
    chat_id = update.effective_chat.id
    await update.message.reply_text("Собираю дайджест новостей...")
    
    success = await send_digest_to_chat(chat_id)
    
    if not success:
        await update.message.reply_text("Произошла ошибка при формировании дайджеста. Попробуйте позже.")

async def help_command(update: Update, context: CallbackContext):
    """Обработчик команды /help"""
    help_text = (
        "📚 *Справка по использованию бота*\n\n"
        "/start - Начать работу с ботом\n"
        "/digest - Получить текущий дайджест новостей\n"
        "/help - Показать эту справку"
    )
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def echo(update: Update, context: CallbackContext):
    """Эхо-ответ на текстовые сообщения, которые не являются командами"""
    await update.message.reply_text(
        "Я не понимаю это сообщение. Используйте /help, чтобы увидеть список доступных команд."
    )

# Функция для обработки вебхуков Telegram
async def process_telegram_update(update_json):
    """Обработать обновление от Telegram"""
    try:
        # Создаем объект Application в режиме вебхука
        application = Application.builder().token(BOT_TOKEN).build()
        
        # Регистрируем обработчики команд
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("digest", digest_command))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
        
        # Создаем объект Update из JSON
        update = Update.de_json(update_json, application.bot)
        
        # Обрабатываем обновление через асинхронный диспетчер
        await application.process_update(update)
        
        return True
    except Exception as e:
        logger.error(f"Ошибка при обработке вебхука: {e}")
        return False

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Обработчик GET-запросов для проверки работоспособности"""
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b'Telegram Bot Webhook is running!')

    def do_POST(self):
        """Обработчик POST-запросов (вебхуки от Telegram)"""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            # Парсим JSON данные от Telegram
            update_json = json.loads(post_data.decode('utf-8'))
            
            # Создаем и запускаем асинхронную задачу для обработки вебхука
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            success = loop.run_until_complete(process_telegram_update(update_json))
            
            if success:
                self.send_response(200)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(b'OK')
            else:
                self.send_response(500)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(b'Error processing webhook')
                
        except Exception as e:
            logger.error(f"Ошибка при обработке POST-запроса: {e}")
            self.send_response(500)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(f"Error: {str(e)}".encode('utf-8')) 