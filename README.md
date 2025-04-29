# Telegram News Digest Bot

Телеграм бот для автоматического мониторинга sitemap.xml новостных сайтов и отправки дайджестов.

## Возможности

- Периодический парсинг sitemap.xml для поиска новых статей
- Извлечение заголовков статей
- Формирование компактных дайджестов с заголовками и ссылками
- Отправка дайджестов в указанный Telegram чат
- Интерактивные кнопки для управления ботом
- Логирование всех операций
- Работа через Vercel с использованием webhook API

## Установка

### Локальная разработка

1. Клонировать репозиторий:
   ```
   git clone <URL репозитория>
   cd <директория проекта>
   ```

2. Установить зависимости:
   ```
   pip install -r requirements.txt
   ```

3. Создать файл `.env` в корневой директории и добавить:
   ```
   TELEGRAM_BOT_TOKEN=ваш_токен_бота
   SITEMAP_URL=https://example.com/sitemap.xml
   DIGEST_CHAT_ID=  # ID чата для отправки дайджеста (опционально)
   MAX_ARTICLES_IN_DIGEST=10
   DIGEST_INTERVAL_HOURS=1
   ADMIN_ID=  # ID администратора (опционально)
   ```

4. Запустить бота:
   ```
   python -m src.bot
   ```

### Развертывание на Vercel

1. Установить Vercel CLI (если еще не установлен):
   ```
   npm install -g vercel
   ```

2. Авторизоваться в Vercel:
   ```
   vercel login
   ```

3. Настроить переменные окружения в Vercel:
   ```
   vercel env add TELEGRAM_BOT_TOKEN
   vercel env add SITEMAP_URL
   vercel env add DIGEST_CHAT_ID  # опционально
   vercel env add MAX_ARTICLES_IN_DIGEST
   vercel env add DIGEST_INTERVAL_HOURS
   vercel env add ADMIN_ID  # опционально
   ```

4. Развернуть приложение:
   ```
   vercel --prod
   ```

5. Настроить вебхук Telegram на URL вашего приложения:
   ```
   python setup_webhook.py --set https://your-vercel-app.vercel.app/api/webhook
   ```

## Использование

### Команды бота

- `/start` - Начать работу с ботом
- `/help` - Показать справку по командам
- `/digest` - Запросить дайджест прямо сейчас
- `/status` - Проверить статус планировщика (только в режиме long polling)
- `/setchat` - Установить текущий чат для отправки дайджеста (только для админа)

### Управление через Vercel

- Проверить статус вебхука:
  ```
  npm run webhook-info
  ```

- Удалить вебхук:
  ```
  npm run delete-webhook
  ```

- Локальная разработка с Vercel:
  ```
  npm run dev
  ```

## Особенности работы с Vercel

- В режиме Vercel бот работает через веб-хуки, а не через long polling
- Дайджесты отправляются по расписанию с помощью Vercel Cron Jobs
- Настройки чата для отправки сохраняются в переменных окружения
- Для хранения состояния рекомендуется использовать Vercel KV Storage

## Требования

- Python 3.9+
- python-telegram-bot
- requests
- beautifulsoup4
- python-dotenv
- lxml
- Node.js и npm (для работы с Vercel)

## Лицензия

MIT 