#!/usr/bin/env python3
import os
import requests
import argparse
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN не найден в переменных окружения")

def setup_webhook(webhook_url):
    """
    Настраивает вебхук для Telegram бота
    
    :param webhook_url: URL для вебхука (например, https://your-vercel-app.vercel.app/api/webhook)
    """
    api_url = f"https://api.telegram.org/bot{TOKEN}/setWebhook"
    
    payload = {
        "url": webhook_url,
        "allowed_updates": ["message", "callback_query"],
        "drop_pending_updates": True
    }
    
    response = requests.post(api_url, json=payload)
    
    if response.status_code == 200 and response.json().get("ok"):
        print(f"✅ Вебхук успешно установлен на {webhook_url}")
        print(f"Детали ответа: {response.json()}")
    else:
        print(f"❌ Ошибка при установке вебхука: {response.text}")

def get_webhook_info():
    """Получает информацию о текущем вебхуке"""
    api_url = f"https://api.telegram.org/bot{TOKEN}/getWebhookInfo"
    
    response = requests.get(api_url)
    
    if response.status_code == 200:
        webhook_info = response.json()
        print("Информация о текущем вебхуке:")
        print(f"URL: {webhook_info.get('result', {}).get('url', 'Не установлен')}")
        print(f"Ожидает обновлений: {webhook_info.get('result', {}).get('pending_update_count', 0)}")
        print(f"Последняя ошибка: {webhook_info.get('result', {}).get('last_error_message', 'Нет ошибок')}")
    else:
        print(f"❌ Ошибка при получении информации о вебхуке: {response.text}")

def delete_webhook():
    """Удаляет текущий вебхук"""
    api_url = f"https://api.telegram.org/bot{TOKEN}/deleteWebhook?drop_pending_updates=true"
    
    response = requests.get(api_url)
    
    if response.status_code == 200 and response.json().get("ok"):
        print("✅ Вебхук успешно удален")
    else:
        print(f"❌ Ошибка при удалении вебхука: {response.text}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Настройка вебхука для Telegram бота")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--set", type=str, help="Установить URL для вебхука")
    group.add_argument("--info", action="store_true", help="Получить информацию о текущем вебхуке")
    group.add_argument("--delete", action="store_true", help="Удалить текущий вебхук")
    
    args = parser.parse_args()
    
    if args.set:
        setup_webhook(args.set)
    elif args.info:
        get_webhook_info()
    elif args.delete:
        delete_webhook() 