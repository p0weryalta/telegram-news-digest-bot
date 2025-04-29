import logging
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

# Обработчики команд
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    keyboard = [
        [InlineKeyboardButton("Проверить сейчас", callback_data=CHECK_NOW_CALLBACK)]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f'Привет, {update.effective_user.first_name}! Я бот для отправки дайджеста новостей.\n\n'
        f'Я периодически проверяю sitemap.xml указанного сайта и отправляю подборку новых статей.',
        reply_markup=reply_markup
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /help"""
    keyboard = [
        [InlineKeyboardButton("Проверить сейчас", callback_data=CHECK_NOW_CALLBACK)]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        'Список доступных команд:\n'
        '/start - начать работу с ботом\n'
        '/help - показать справку\n'
        '/digest - запросить дайджест прямо сейчас\n'
        '/status - проверить статус планировщика\n'
        '/setchat - установить текущий чат для отправки дайджеста (только для админа)',
        reply_markup=reply_markup
    )

async def digest_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /digest - отправляет дайджест по запросу"""
    if not sitemap_parser:
        await update.message.reply_text('Ошибка: парсер не инициализирован')
        return
    
    await update.message.reply_text('Запрашиваю новые статьи... Пожалуйста, подождите.')
    
    try:
        # Парсим sitemap и получаем новые статьи
        articles = sitemap_parser.parse_sitemap()
        
        if not articles:
            keyboard = [
                [InlineKeyboardButton("Проверить снова", callback_data=CHECK_NOW_CALLBACK)]
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
            [InlineKeyboardButton("Проверить снова", callback_data=CHECK_NOW_CALLBACK)]
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

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /status - проверяет статус планировщика"""
    if not digest_scheduler:
        await update.message.reply_text('Планировщик дайджеста не инициализирован')
        return
    
    status = "работает" if digest_scheduler.is_running else "остановлен"
    
    keyboard = [
        [InlineKeyboardButton("Проверить сейчас", callback_data=CHECK_NOW_CALLBACK)]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f'Статус планировщика дайджеста: {status}\n'
        f'Интервал: {digest_scheduler.interval_hours} час(ов)\n'
        f'ID чата для отправки: {digest_scheduler.digest_chat_id or "не установлен"}',
        reply_markup=reply_markup
    )

async def setchat_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /setchat - устанавливает текущий чат для отправки дайджеста"""
    # Проверяем, является ли пользователь администратором
    if ADMIN_ID and str(update.effective_user.id) != ADMIN_ID:
        await update.message.reply_text('У вас нет прав для выполнения этой команды')
        return
    
    chat_id = update.effective_chat.id
    
    if not digest_scheduler:
        await update.message.reply_text('Ошибка: планировщик не инициализирован')
        return
    
    # Устанавливаем ID текущего чата для отправки дайджеста
    digest_scheduler.digest_chat_id = chat_id
    
    keyboard = [
        [InlineKeyboardButton("Проверить сейчас", callback_data=CHECK_NOW_CALLBACK)]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f'Текущий чат (ID: {chat_id}) установлен для отправки дайджеста',
        reply_markup=reply_markup
    )

# Обработчик для inline кнопок
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик нажатий inline кнопок"""
    query = update.callback_query
    await query.answer()  # Отвечаем на запрос, чтобы убрать "часики" с кнопки
    
    if query.data == CHECK_NOW_CALLBACK:
        await query.edit_message_text("Запрашиваю новые статьи... Пожалуйста, подождите.")
        
        if not sitemap_parser:
            await query.edit_message_text('Ошибка: парсер не инициализирован')
            return
        
        try:
            # Парсим sitemap и получаем новые статьи
            articles = sitemap_parser.parse_sitemap()
            
            if not articles:
                keyboard = [
                    [InlineKeyboardButton("Проверить снова", callback_data=CHECK_NOW_CALLBACK)]
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
                [InlineKeyboardButton("Проверить снова", callback_data=CHECK_NOW_CALLBACK)]
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
    text = update.message.text
    logger.info(f"Пользователь {update.effective_user.id} отправил сообщение: {text}")
    
    # Для простых сообщений просто отвечаем базовой информацией с кнопкой
    keyboard = [
        [InlineKeyboardButton("Проверить сейчас", callback_data=CHECK_NOW_CALLBACK)]
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
async def error(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Логирование ошибок, вызванных обновлениями."""
    logger.error(f'Произошла ошибка: {context.error} при обработке {update}')

def main():
    """Запуск бота."""
    global sitemap_parser, digest_scheduler
    
    # Инициализируем парсер sitemap
    sitemap_parser = SitemapParser(SITEMAP_URL)
    
    # Создаем приложение
    application = Application.builder().token(TOKEN).build()

    # Добавляем обработчики команд
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("digest", digest_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("setchat", setchat_command))
    
    # Обработчик callback от inline кнопок
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Обработчик текстовых сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Обработчик ошибок
    application.add_error_handler(error)
    
    # Инициализируем и запускаем планировщик дайджеста
    bot = application.bot
    digest_scheduler = DigestScheduler(
        bot=bot,
        sitemap_parser=sitemap_parser,
        digest_chat_id=DIGEST_CHAT_ID,
        interval_hours=DIGEST_INTERVAL_HOURS,
        max_articles=MAX_ARTICLES_IN_DIGEST
    )
    digest_scheduler.start()

    # Запускаем бота
    logger.info("Бот запущен")
    
    # Используем более простой метод запуска для версии python-telegram-bot 20.8
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main() 