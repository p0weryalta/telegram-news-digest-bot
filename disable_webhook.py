import requests
import os
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
load_dotenv()

# Получаем токен бота из переменных окружения или задаем вручную
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "7571379091:AAGD4fEr_xxmoyse1mQxjbcradm6ChasA20")

# Функция для отключения вебхука
def disable_webhook():
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook"
    response = requests.get(url)
    result = response.json()
    
    if result.get("ok"):
        print("✅ Вебхук успешно деактивирован")
        print("Теперь ваш бот может работать в режиме long polling")
    else:
        print(f"❌ Ошибка при деактивации вебхука: {result.get('description')}")

if __name__ == "__main__":
    print(f"Деактивирую вебхук для бота с токеном: {BOT_TOKEN[:5]}...{BOT_TOKEN[-5:]}")
    disable_webhook() 