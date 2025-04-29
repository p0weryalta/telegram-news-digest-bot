import logging
import os
import sys
from pathlib import Path

# Добавляем корневой каталог в путь импорта
root_dir = Path(__file__).parent.parent
sys.path.append(str(root_dir))

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from src.config import TOKEN, SITEMAP_URL, DIGEST_CHAT_ID, MAX_ARTICLES_IN_DIGEST, DIGEST_INTERVAL_HOURS, ADMIN_ID
from src.sitemap_parser import SitemapParser
from src.scheduler import DigestScheduler

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Глобальные переменные
sitemap_parser = None
digest_scheduler = None

# Константы для callback данных
CHECK_NOW_CALLBACK = "check_now"
HELP_CALLBACK = "help"
SETTINGS_CALLBACK = "settings"
NOTIFICATIONS_CALLBACK = "notifications"
CHANGE_TIME_CALLBACK = "change_time"
ARTICLE_COUNT_CALLBACK = "article_count"

# Обработчики команд
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    keyboard = [
        [
            InlineKeyboardButton("📰 Получить дайджест", callback_data=CHECK_NOW_CALLBACK),
            InlineKeyboardButton("ℹ️ Помощь", callback_data=HELP_CALLBACK)
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
    keyboard = [
        [
            InlineKeyboardButton("📰 Получить дайджест", callback_data=CHECK_NOW_CALLBACK),
            InlineKeyboardButton("⚙️ Настройки", callback_data=SETTINGS_CALLBACK)
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
    if not sitemap_parser:
        await update.message.reply_text('❌ Ошибка: парсер не инициализирован')
        return
    
    progress_message = await update.message.reply_text('🔄 Собираю свежие новости... Пожалуйста, подождите.')
    
    try:
        articles = sitemap_parser.parse_sitemap()
        
        if not articles:
            keyboard = [
                [InlineKeyboardButton("🔄 Проверить снова", callback_data=CHECK_NOW_CALLBACK)]
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
                InlineKeyboardButton("🔄 Обновить", callback_data=CHECK_NOW_CALLBACK),
                InlineKeyboardButton("⚙️ Настройки", callback_data=SETTINGS_CALLBACK)
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
    if not digest_scheduler:
        await update.message.reply_text('❌ Планировщик дайджеста не инициализирован')
        return
    
    status = "✅ работает" if digest_scheduler.is_running else "⛔️ остановлен"
    chat_id = digest_scheduler.digest_chat_id or "Не установлен"
    
    await update.message.reply_text(
        '📊 Статус бота:\n\n'
        f'🔹 Мониторинг: {SITEMAP_URL}\n'
        f'🔹 Интервал проверки: {DIGEST_INTERVAL_HOURS} часов\n'
        f'🔹 Статус планировщика: {status}\n'
        f'🔹 Чат для дайджеста: {chat_id}\n'
        f'🔹 Максимум статей: {MAX_ARTICLES_IN_DIGEST}'
    )

async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /settings"""
    keyboard = [
        [InlineKeyboardButton("📱 Настроить уведомления", callback_data=NOTIFICATIONS_CALLBACK)],
        [InlineKeyboardButton("⏰ Изменить время отправки", callback_data=CHANGE_TIME_CALLBACK)],
        [InlineKeyboardButton("📊 Количество статей", callback_data=ARTICLE_COUNT_CALLBACK)]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        '⚙️ Настройки:\n\n'
        'Выберите параметр для настройки:',
        reply_markup=reply_markup
    )

async def setchat_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /setchat"""
    # Проверяем, является ли пользователь администратором
    if ADMIN_ID and str(update.effective_user.id) != ADMIN_ID:
        await update.message.reply_text('⛔️ У вас нет прав для выполнения этой команды')
        return
    
    chat_id = update.effective_chat.id
    
    if not digest_scheduler:
        await update.message.reply_text('❌ Ошибка: планировщик не инициализирован')
        return
    
    # Устанавливаем ID текущего чата для отправки дайджеста
    digest_scheduler.digest_chat_id = chat_id
    
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
    
    if query.data == CHECK_NOW_CALLBACK:
        await query.edit_message_text("🔄 Собираю свежие новости... Пожалуйста, подождите.")
        
        if not sitemap_parser:
            await query.edit_message_text('❌ Ошибка: парсер не инициализирован')
            return
        
        try:
            articles = sitemap_parser.parse_sitemap()
            
            if not articles:
                keyboard = [
                    [InlineKeyboardButton("🔄 Проверить снова", callback_data=CHECK_NOW_CALLBACK)]
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
                    InlineKeyboardButton("🔄 Обновить", callback_data=CHECK_NOW_CALLBACK),
                    InlineKeyboardButton("⚙️ Настройки", callback_data=SETTINGS_CALLBACK)
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
    elif query.data == HELP_CALLBACK:
        await help_command(update, context)
    elif query.data == SETTINGS_CALLBACK:
        await settings_command(update, context)
    elif query.data in [NOTIFICATIONS_CALLBACK, CHANGE_TIME_CALLBACK, ARTICLE_COUNT_CALLBACK]:
        await query.edit_message_text(
            '🚧 Эта функция находится в разработке.\n'
            'Она будет доступна в следующих обновлениях.'
        )

# Обработчик текстовых сообщений
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик для всех текстовых сообщений"""
    text = update.message.text
    logger.info(f"Пользователь {update.effective_user.id} отправил сообщение: {text}")
    
    keyboard = [
        [
            InlineKeyboardButton("📰 Получить дайджест", callback_data=CHECK_NOW_CALLBACK),
            InlineKeyboardButton("ℹ️ Помощь", callback_data=HELP_CALLBACK)
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

def main():
    """Запуск бота."""
    global sitemap_parser, digest_scheduler
    
    # Инициализируем парсер и планировщик
    sitemap_parser = SitemapParser(SITEMAP_URL)
    digest_scheduler = DigestScheduler(
        sitemap_parser=sitemap_parser,
        digest_chat_id=DIGEST_CHAT_ID,
        max_articles=MAX_ARTICLES_IN_DIGEST,
        interval_hours=DIGEST_INTERVAL_HOURS,
        bot_token=TOKEN
    )
    
    # Создаем приложение
    application = Application.builder().token(TOKEN).build()
    
    # Добавляем обработчики команд
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("digest", digest_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("settings", settings_command))
    application.add_handler(CommandHandler("setchat", setchat_command))
    
    # Добавляем обработчик callback от inline кнопок
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Добавляем обработчик сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Добавляем обработчик ошибок
    application.add_error_handler(error)
    
    logger.info("Бот запущен. Нажмите Ctrl+C для остановки.")
    
    # Запускаем планировщик
    if digest_scheduler.digest_chat_id:
        digest_scheduler.start()
        logger.info(f"Планировщик запущен с интервалом {DIGEST_INTERVAL_HOURS} часов.")
    else:
        logger.warning("Планировщик не запущен: ID чата для дайджеста не установлен. Используйте /setchat")
    
    # Запускаем бота в режиме long polling
    application.run_polling()
    
    # Останавливаем планировщик при завершении работы
    if digest_scheduler and digest_scheduler.is_running:
        digest_scheduler.stop()
        logger.info("Планировщик остановлен.")

if __name__ == '__main__':
    main() 