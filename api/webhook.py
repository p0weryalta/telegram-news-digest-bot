from http.server import BaseHTTPRequestHandler
import json
import logging
import os
import sys
from urllib.parse import parse_qs

# Добавляем корневую директорию проекта в путь для импорта
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    CallbackContext,
    CallbackQueryHandler,
    ContextTypes
)

from src.config import TOKEN, SITEMAP_URL, DIGEST_CHAT_ID, MAX_ARTICLES_IN_DIGEST, DIGEST_INTERVAL_HOURS, ADMIN_ID
from src.sitemap_parser import SitemapParser

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Глобальные переменные
sitemap_parser = SitemapParser(SITEMAP_URL)

# Обработчики команд
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    
    keyboard = [
        [InlineKeyboardButton("Проверить сейчас", callback_data="check_now")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f'Привет, {update.effective_user.first_name}! Я бот для отправки дайджеста новостей.\n\n'
        f'Я периодически проверяю sitemap.xml указанного сайта и отправляю подборку новых статей.',
        reply_markup=reply_markup
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /help"""
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    
    keyboard = [
        [InlineKeyboardButton("Проверить сейчас", callback_data="check_now")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        'Список доступных команд:\n'
        '/start - начать работу с ботом\n'
        '/help - показать справку\n'
        '/digest - запросить дайджест прямо сейчас\n'
        '/setchat - установить текущий чат для отправки дайджеста (только для админа)',
        reply_markup=reply_markup
    )

async def digest_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /digest - отправляет дайджест по запросу"""
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    
    await update.message.reply_text('Запрашиваю новые статьи... Пожалуйста, подождите.')
    
    try:
        # Парсим sitemap и получаем новые статьи
        articles = sitemap_parser.parse_sitemap()
        
        if not articles:
            keyboard = [
                [InlineKeyboardButton("Проверить снова", callback_data="check_now")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                'Нет новых статей для отображения.',
                reply_markup=reply_markup
            )
            return
        
        # Форматируем дайджест
        digest_text = sitemap_parser.format_digest(articles, MAX_ARTICLES_IN_DIGEST)
        
        # Создаем клавиатуру с кнопкой для повторной проверки
        keyboard = [
            [InlineKeyboardButton("Проверить снова", callback_data="check_now")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Отправляем дайджест
        await update.message.reply_text(
            digest_text,
            parse_mode='Markdown',
            disable_web_page_preview=True,
            reply_markup=reply_markup
        )
    except Exception as e:
        logger.error(f"Ошибка при обработке команды digest: {e}")
        await update.message.reply_text(f'Произошла ошибка: {str(e)}')

async def setchat_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /setchat - устанавливает текущий чат для отправки дайджеста"""
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    
    # Проверяем, является ли пользователь администратором
    if ADMIN_ID and str(update.effective_user.id) != ADMIN_ID:
        await update.message.reply_text('У вас нет прав для выполнения этой команды')
        return
    
    chat_id = update.effective_chat.id
    
    # Здесь нужно сохранить ID чата куда-то, откуда его можно будет извлечь при выполнении cron-задачи
    # В Vercel лучше использовать базу данных или KV-хранилище
    # Для примера, запишем в переменную окружения (не будет работать между деплоями)
    os.environ['DIGEST_CHAT_ID'] = str(chat_id)
    
    keyboard = [
        [InlineKeyboardButton("Проверить сейчас", callback_data="check_now")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f'Текущий чат (ID: {chat_id}) установлен для отправки дайджеста',
        reply_markup=reply_markup
    )

# Обработчик для inline кнопок
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик нажатий inline кнопок"""
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    
    query = update.callback_query
    await query.answer()  # Отвечаем на запрос, чтобы убрать "часики" с кнопки
    
    if query.data == "check_now":
        await query.edit_message_text("Запрашиваю новые статьи... Пожалуйста, подождите.")
        
        try:
            # Парсим sitemap и получаем новые статьи
            articles = sitemap_parser.parse_sitemap()
            
            if not articles:
                keyboard = [
                    [InlineKeyboardButton("Проверить снова", callback_data="check_now")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(
                    'Нет новых статей для отображения.',
                    reply_markup=reply_markup
                )
                return
            
            # Форматируем дайджест
            digest_text = sitemap_parser.format_digest(articles, MAX_ARTICLES_IN_DIGEST)
            
            # Создаем клавиатуру с кнопкой для повторной проверки
            keyboard = [
                [InlineKeyboardButton("Проверить снова", callback_data="check_now")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Отправляем дайджест
            await query.edit_message_text(
                digest_text,
                parse_mode='Markdown',
                disable_web_page_preview=True,
                reply_markup=reply_markup
            )
        except Exception as e:
            logger.error(f"Ошибка при обработке кнопки check_now: {e}")
            await query.edit_message_text(f'Произошла ошибка: {str(e)}')

# Обработчик текстовых сообщений
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик для всех текстовых сообщений"""
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    
    text = update.message.text
    logger.info(f"Пользователь {update.effective_user.id} отправил сообщение: {text}")
    
    # Для простых сообщений просто отвечаем базовой информацией с кнопкой
    keyboard = [
        [InlineKeyboardButton("Проверить сейчас", callback_data="check_now")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        'Я бот для отправки дайджеста новостей. Используйте команды:\n'
        '/start - начать работу с ботом\n'
        '/help - показать доступные команды\n'
        '/digest - запросить дайджест новостей',
        reply_markup=reply_markup
    )

# Обработчик ошибок
async def error(update, context):
    """Логирование ошибок, вызванных обновлениями."""
    logger.error(f'Произошла ошибка: {context.error} при обработке {update}')

# Инициализация бота
def create_application():
    """Создание приложения бота"""
    application = Application.builder().token(TOKEN).build()
    
    # Добавляем обработчики команд
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("digest", digest_command))
    application.add_handler(CommandHandler("setchat", setchat_command))
    
    # Обработчик callback от inline кнопок
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Обработчик текстовых сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Обработчик ошибок
    application.add_error_handler(error)
    
    return application

# Обработчик HTTP-запросов от Vercel
class handler(BaseHTTPRequestHandler):
    async def process_update(self, update_data):
        application = create_application()
        update = Update.de_json(update_data, application.bot)
        await application.process_update(update)
        
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length).decode('utf-8')
        
        # Обрабатываем данные
        try:
            update_data = json.loads(post_data)
            
            # Используем асинхронный обработчик
            import asyncio
            asyncio.run(self.process_update(update_data))
            
            # Отправляем успешный ответ
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "success"}).encode('utf-8'))
            
        except Exception as e:
            logger.error(f"Ошибка обработки webhook: {e}")
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode('utf-8'))
    
    def do_GET(self):
        # Для проверки, что webhook доступен
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({"status": "webhook active"}).encode('utf-8')) 