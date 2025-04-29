#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import os
import re
from typing import List, Optional, Tuple
import xml.etree.ElementTree as ET
from urllib.parse import urlparse

import requests
from dotenv import load_dotenv
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# Загрузка переменных окружения из .env файла
load_dotenv()

# Получение токена бота из переменных окружения
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise ValueError("Не задан токен Telegram бота. Пожалуйста, добавьте TELEGRAM_BOT_TOKEN в .env файл.")

# Настройка логирования
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
numeric_level = getattr(logging, LOG_LEVEL, logging.INFO)
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=numeric_level
)
logger = logging.getLogger(__name__)

# Константы
MAX_MESSAGE_LENGTH = 4096  # Максимальная длина сообщения в Telegram
MAX_URLS_PER_MESSAGE = 50  # Максимальное количество URL в одном сообщении

# Регулярное выражение для проверки URL
URL_PATTERN = re.compile(
    r'^https?://'  # http:// или https://
    r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'  # домен
    r'localhost|'  # localhost
    r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # или IP
    r'(?::\d+)?'  # опциональный порт
    r'(?:/?|[/?]\S+)$', re.IGNORECASE
)

# Регулярное выражение для проверки имени файла sitemap
SITEMAP_PATTERN = re.compile(r'sitemap.*\.xml$', re.IGNORECASE)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /start."""
    user = update.effective_user
    await update.message.reply_html(
        f"Привет, {user.mention_html()}! 👋\n\n"
        f"Я бот для парсинга sitemap-файлов. Отправь мне URL sitemap.xml, "
        f"и я извлеку из него все URL.\n\n"
        f"Используй /help для получения дополнительной информации."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /help."""
    help_text = (
        "🤖 <b>Команды бота</b>:\n\n"
        "/start - Начать работу с ботом\n"
        "/help - Показать это сообщение\n"
        "/parse <i>URL</i> - Парсить указанный sitemap\n\n"
        "Также вы можете просто отправить URL sitemap-файла в чат, "
        "и я постараюсь его обработать.\n\n"
        "<b>Примеры использования</b>:\n"
        "/parse https://example.com/sitemap.xml\n"
        "https://example.com/sitemap.xml"
    )
    await update.message.reply_text(help_text, parse_mode=ParseMode.HTML)

async def parse_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /parse."""
    if not context.args or not context.args[0]:
        await update.message.reply_text(
            "⚠️ Пожалуйста, укажите URL sitemap файла.\n"
            "Пример: /parse https://example.com/sitemap.xml"
        )
        return

    url = context.args[0]
    await handle_url(update, url)

def parse_sitemap(url: str) -> Tuple[List[str], Optional[str]]:
    """
    Парсит sitemap по указанному URL и возвращает список URL и сообщение об ошибке (если есть).
    
    Args:
        url: URL sitemap-файла
        
    Returns:
        Tuple[List[str], Optional[str]]: Список URL и сообщение об ошибке (если есть)
    """
    urls = []
    error = None
    
    # Проверяем, что URL валидный
    if not URL_PATTERN.match(url):
        return [], f"⚠️ Некорректный URL: {url}"
    
    # Проверяем, что URL ведет на sitemap файл
    parsed_url = urlparse(url)
    path = parsed_url.path
    
    if not path or not SITEMAP_PATTERN.search(path):
        return [], f"⚠️ URL не похож на sitemap файл: {url}"
    
    try:
        # Загружаем sitemap файл
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        # Проверяем, что ответ содержит XML
        content_type = response.headers.get('Content-Type', '')
        if 'text/xml' not in content_type and 'application/xml' not in content_type:
            return [], f"⚠️ Ответ не является XML: {content_type}"
        
        # Парсим XML
        root = ET.fromstring(response.content)
        
        # Находим все URL в sitemap
        # Обрабатываем оба формата sitemap: xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
        # и xmlns="http://www.google.com/schemas/sitemap/0.84"
        namespaces = {
            'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9',
            'sm_old': 'http://www.google.com/schemas/sitemap/0.84'
        }
        
        # Ищем URL в стандартном формате
        for url_elem in root.findall('.//sm:url/sm:loc', namespaces) or root.findall('.//sm_old:url/sm_old:loc', namespaces):
            if url_elem.text and url_elem.text.strip():
                urls.append(url_elem.text.strip())
        
        # Если URL не найдены, пробуем искать без пространства имен
        if not urls:
            for url_elem in root.findall('.//url/loc') or root.findall('.//sitemap/loc'):
                if url_elem.text and url_elem.text.strip():
                    urls.append(url_elem.text.strip())
        
        if not urls:
            return [], "⚠️ В sitemap не найдено URL"
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка при загрузке sitemap: {e}")
        return [], f"⚠️ Ошибка при загрузке sitemap: {str(e)}"
    except ET.ParseError as e:
        logger.error(f"Ошибка при парсинге XML: {e}")
        return [], f"⚠️ Ошибка при парсинге XML: {str(e)}"
    except Exception as e:
        logger.error(f"Непредвиденная ошибка: {e}")
        return [], f"⚠️ Непредвиденная ошибка: {str(e)}"
    
    return urls, error

async def send_url_batches(update: Update, urls: List[str]) -> None:
    """
    Отправляет пользователю списки URL пакетами, чтобы не превышать лимиты Telegram.
    
    Args:
        update: Объект обновления Telegram
        urls: Список URL для отправки
    """
    if not urls:
        await update.message.reply_text("⚠️ Не найдено URL для отправки.")
        return
    
    # Отправляем общую информацию о количестве найденных URL
    await update.message.reply_text(f"🔍 Найдено URL: {len(urls)}")
    
    # Разбиваем URL на пакеты, чтобы не превышать лимиты Telegram
    for i in range(0, len(urls), MAX_URLS_PER_MESSAGE):
        batch = urls[i:i + MAX_URLS_PER_MESSAGE]
        message = "\n".join(batch)
        
        # Проверяем, не превышает ли сообщение максимальную длину
        if len(message) > MAX_MESSAGE_LENGTH:
            # Если превышает, разбиваем на более мелкие части
            current_message = ""
            for url in batch:
                if len(current_message) + len(url) + 1 > MAX_MESSAGE_LENGTH:
                    await update.message.reply_text(current_message)
                    current_message = url + "\n"
                else:
                    current_message += url + "\n"
            
            if current_message:
                await update.message.reply_text(current_message)
        else:
            await update.message.reply_text(message)

async def handle_url(update: Update, url: str) -> None:
    """
    Обрабатывает URL, переданный пользователем.
    
    Args:
        update: Объект обновления Telegram
        url: URL для обработки
    """
    await update.message.reply_text(f"🔄 Парсинг sitemap: {url}")
    
    # Парсим sitemap
    urls, error = parse_sitemap(url)
    
    # Если возникла ошибка, отправляем сообщение об ошибке
    if error:
        await update.message.reply_text(error)
        return
    
    # Отправляем найденные URL
    await send_url_batches(update, urls)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик текстовых сообщений"""
    text = update.message.text
    
    # Проверяем, содержит ли сообщение URL
    if URL_PATTERN.match(text):
        await handle_url(update, text)
    else:
        await update.message.reply_text(
            "🤔 Отправьте мне URL на sitemap.xml файл.\n"
            "Например: https://example.com/sitemap.xml\n\n"
            "Или используйте команду /help для получения справки."
        )

def main() -> None:
    """Запускает бота."""
    # Создаем приложение и передаем ему токен бота
    application = Application.builder().token(TOKEN).build()

    # Регистрируем обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("parse", parse_command))
    
    # Добавляем обработчик текстовых сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Запускаем бота
    logger.info("Бот запущен")
    application.run_polling()

if __name__ == "__main__":
    main() 