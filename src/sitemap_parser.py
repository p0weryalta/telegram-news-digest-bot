import requests
import logging
from bs4 import BeautifulSoup
from datetime import datetime
import os
import json

logger = logging.getLogger(__name__)

class SitemapParser:
    def __init__(self, sitemap_url, cache_file='last_articles.json'):
        """
        Инициализация парсера sitemap
        
        :param sitemap_url: URL sitemap.xml
        :param cache_file: Файл для хранения ранее обработанных статей
        """
        self.sitemap_url = sitemap_url
        self.cache_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), cache_file)
        self.last_articles = self._load_last_articles()
    
    def _load_last_articles(self):
        """Загрузить ранее обработанные статьи из кеша"""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            logger.error(f"Ошибка загрузки кеша статей: {e}")
            return {}
    
    def _save_last_articles(self, articles):
        """Сохранить обработанные статьи в кеш"""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(articles, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Ошибка сохранения кеша статей: {e}")
    
    def parse_sitemap(self):
        """Парсинг sitemap.xml и получение новых статей"""
        try:
            response = requests.get(self.sitemap_url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'xml')
            urls = soup.find_all('url')
            
            logger.info(f"Найдено {len(urls)} URL в sitemap")
            
            articles = {}
            for url in urls:
                loc = url.find('loc')
                
                # Пытаемся найти lastmod, если его нет, то используем changefreq и priority
                lastmod = url.find('lastmod')
                changefreq = url.find('changefreq')
                priority = url.find('priority')
                
                if loc:
                    url_text = loc.text
                    
                    # Если есть lastmod, используем его
                    if lastmod:
                        modified_text = lastmod.text
                    # Если нет lastmod, но есть changefreq или priority, используем их комбинацию как идентификатор версии
                    elif changefreq or priority:
                        # Создаем уникальный идентификатор для отслеживания изменений
                        cf_text = changefreq.text if changefreq else "daily"
                        pr_text = priority.text if priority else "0.5"
                        modified_text = f"{cf_text}_{pr_text}_{datetime.now().strftime('%Y-%m-%d')}"
                    else:
                        # Если нет ни одного из указанных тегов, используем текущую дату
                        modified_text = datetime.now().strftime("%Y-%m-%d")
                    
                    # Пропускаем статьи, которые уже были в предыдущем дайджесте
                    if url_text in self.last_articles and self.last_articles[url_text] == modified_text:
                        continue
                    
                    articles[url_text] = modified_text
            
            logger.info(f"Найдено {len(articles)} новых или измененных статей")
            
            # Получаем заголовки статей
            new_articles = []
            # Ограничиваем количество статей для обработки, чтобы не перегружать ресурсы
            max_articles_to_process = 100
            for i, url in enumerate(list(articles.keys())[:max_articles_to_process]):
                try:
                    title = self._get_article_title(url)
                    if title:
                        new_articles.append({
                            'url': url,
                            'title': title,
                            'lastmod': articles[url]
                        })
                except Exception as e:
                    logger.error(f"Ошибка при получении заголовка статьи {url}: {e}")
            
            # Сортируем статьи по приоритету даты (если есть числовое значение приоритета)
            def get_priority(article):
                try:
                    if '_' in article['lastmod']:
                        # Если используем формат cf_pr_date
                        return float(article['lastmod'].split('_')[1])
                    return 0.5
                except:
                    return 0.5
                    
            new_articles.sort(key=get_priority, reverse=True)
            
            # Обновляем кеш
            self._save_last_articles(articles)
            
            return new_articles
        
        except Exception as e:
            logger.error(f"Ошибка при парсинге sitemap: {e}")
            return []
    
    def _get_article_title(self, url):
        """Получить заголовок статьи по URL"""
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            title = soup.find('title')
            
            if title:
                return title.text.strip()
            
            # Если title не найден, пробуем найти заголовок h1
            h1 = soup.find('h1')
            if h1:
                return h1.text.strip()
            
            return "Без заголовка"
        
        except Exception as e:
            logger.error(f"Ошибка при получении заголовка для {url}: {e}")
            return "Ошибка получения заголовка"
    
    def format_digest(self, articles, max_articles=10):
        """
        Форматирование дайджеста на основе новых статей
        
        :param articles: Список статей
        :param max_articles: Максимальное число статей в дайджесте
        :return: Отформатированный текст дайджеста
        """
        if not articles:
            return "Нет новых статей"
        
        articles = articles[:max_articles]  # Ограничиваем количество статей
        
        now = datetime.now().strftime("%d.%m.%Y %H:%M")
        digest = f"📰 *Дайджест новостей от {now}*\n\n"
        
        for i, article in enumerate(articles, 1):
            digest += f"*{i}. {article['title']}*\n{article['url']}\n\n"
        
        digest += "🤖 Бот автоматически собирает новости каждый час"
        
        return digest 