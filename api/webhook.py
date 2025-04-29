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
        [
            InlineKeyboardButton("📰 Получить дайджест", callback_data="check_now"),
            InlineKeyboardButton("ℹ️ Помощь", callback_data="help")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f'👋 Здравствуйте, {update.effective_user.first_name}!\n\n'
        f'Я бот для мониторинга новостей через sitemap.xml. Каждые {DIGEST_INTERVAL_HOURS} часов '
        f'я проверяю обновления и отправляю дайджест с новыми статьями.\n\n'
        f'🔍 Вы можете получить дайджест прямо сейчас, нажав кнопку ниже.',
        reply_markup=reply_markup
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /help"""
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    
    keyboard = [
        [
            InlineKeyboardButton("📰 Получить дайджест", callback_data="check_now"),
            InlineKeyboardButton("⚙️ Настройки", callback_data="settings")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        '📋 Доступные команды:\n\n'
        '🔹 /start - запустить бота\n'
        '🔹 /help - показать это сообщение\n'
        '🔹 /digest - получить свежий дайджест\n'
        '🔹 /status - проверить статус бота\n'
        '🔹 /settings - настройки уведомлений\n'
        f'🔹 /setchat - установить чат для дайджеста (только для админа)\n\n'
        f'⏰ Автоматическая отправка дайджеста: каждые {DIGEST_INTERVAL_HOURS} часов\n'
        f'📊 Максимум статей в дайджесте: {MAX_ARTICLES_IN_DIGEST}',
        reply_markup=reply_markup
    )

async def digest_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /digest"""
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    
    progress_message = await update.message.reply_text('🔄 Собираю свежие новости... Пожалуйста, подождите.')
    
    try:
        articles = sitemap_parser.parse_sitemap()
        
        if not articles:
            keyboard = [
                [InlineKeyboardButton("🔄 Проверить снова", callback_data="check_now")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await progress_message.edit_text(
                '📭 Новых статей пока нет.\n'
                'Попробуйте проверить позже.',
                reply_markup=reply_markup
            )
            return
        
        digest_text = sitemap_parser.format_digest(articles, MAX_ARTICLES_IN_DIGEST)
        
        keyboard = [
            [
                InlineKeyboardButton("🔄 Обновить", callback_data="check_now"),
                InlineKeyboardButton("⚙️ Настройки", callback_data="settings")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await progress_message.edit_text(
            f'📰 Свежий дайджест:\n\n{digest_text}',
            parse_mode='Markdown',
            disable_web_page_preview=True,
            reply_markup=reply_markup
        )
    except Exception as e:
        logger.error(f"Ошибка при формировании дайджеста: {e}")
        await progress_message.edit_text(
            '❌ Произошла ошибка при получении новостей.\n'
            'Пожалуйста, попробуйте позже или обратитесь к администратору.'
        )

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /status"""
    try:
        chat_id = os.getenv('DIGEST_CHAT_ID', 'Не установлен')
        await update.message.reply_text(
            '📊 Статус бота:\n\n'
            f'🔹 Мониторинг: {SITEMAP_URL}\n'
            f'🔹 Интервал проверки: {DIGEST_INTERVAL_HOURS} часов\n'
            f'🔹 Чат для дайджеста: {chat_id}\n'
            f'🔹 Максимум статей: {MAX_ARTICLES_IN_DIGEST}'
        )
    except Exception as e:
        logger.error(f"Ошибка при получении статуса: {e}")
        await update.message.reply_text('❌ Ошибка при получении статуса бота')

async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /settings"""
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    
    keyboard = [
        [InlineKeyboardButton("📱 Настроить уведомления", callback_data="notifications")],
        [InlineKeyboardButton("⏰ Изменить время отправки", callback_data="change_time")],
        [InlineKeyboardButton("📊 Количество статей", callback_data="article_count")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        '⚙️ Настройки:\n\n'
        'Выберите параметр для настройки:',
        reply_markup=reply_markup
    )

async def setchat_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /setchat"""
    if ADMIN_ID and str(update.effective_user.id) != ADMIN_ID:
        await update.message.reply_text('⛔️ У вас нет прав для выполнения этой команды')
        return
    
    chat_id = update.effective_chat.id
    os.environ['DIGEST_CHAT_ID'] = str(chat_id)
    
    await update.message.reply_text(
        f'✅ Чат успешно установлен\n\n'
        f'🔹 ID чата: {chat_id}\n'
        f'🔹 Дайджесты будут отправляться сюда каждые {DIGEST_INTERVAL_HOURS} часов'
    )

# Обработчик для inline кнопок
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик нажатий inline кнопок"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "check_now":
        await query.edit_message_text("🔄 Собираю свежие новости... Пожалуйста, подождите.")
        
        try:
            articles = sitemap_parser.parse_sitemap()
            
            if not articles:
                keyboard = [
                    [InlineKeyboardButton("🔄 Проверить снова", callback_data="check_now")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(
                    '📭 Новых статей пока нет.\n'
                    'Попробуйте проверить позже.',
                    reply_markup=reply_markup
                )
                return
            
            digest_text = sitemap_parser.format_digest(articles, MAX_ARTICLES_IN_DIGEST)
            
            keyboard = [
                [
                    InlineKeyboardButton("🔄 Обновить", callback_data="check_now"),
                    InlineKeyboardButton("⚙️ Настройки", callback_data="settings")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                f'📰 Свежий дайджест:\n\n{digest_text}',
                parse_mode='Markdown',
                disable_web_page_preview=True,
                reply_markup=reply_markup
            )
        except Exception as e:
            logger.error(f"Ошибка при обработке кнопки check_now: {e}")
            await query.edit_message_text(
                '❌ Произошла ошибка при получении новостей.\n'
                'Пожалуйста, попробуйте позже или обратитесь к администратору.'
            )
    elif query.data == "help":
        await help_command(update, context)
    elif query.data == "settings":
        await settings_command(update, context)
    elif query.data in ["notifications", "change_time", "article_count"]:
        await query.edit_message_text(
            '🚧 Эта функция находится в разработке.\n'
            'Она будет доступна в следующих обновлениях.'
        )

# Обработчик текстовых сообщений
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик для всех текстовых сообщений"""
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    
    text = update.message.text
    logger.info(f"Пользователь {update.effective_user.id} отправил сообщение: {text}")
    
    keyboard = [
        [
            InlineKeyboardButton("📰 Получить дайджест", callback_data="check_now"),
            InlineKeyboardButton("ℹ️ Помощь", callback_data="help")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        '👋 Я бот для мониторинга новостей.\n\n'
        'Доступные команды:\n'
        '🔹 /start - запустить бота\n'
        '🔹 /help - показать помощь\n'
        '🔹 /digest - получить свежий дайджест\n'
        '🔹 /status - проверить статус\n'
        '🔹 /settings - настройки',
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