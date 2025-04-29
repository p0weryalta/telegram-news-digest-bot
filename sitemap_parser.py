#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

logger = logging.getLogger(__name__)

def parse_sitemap(url, recursive=True):
    """
    Парсит sitemap.xml файл и возвращает список URL.
    
    Args:
        url (str): URL-адрес sitemap.xml файла
        recursive (bool): Если True, рекурсивно обрабатывает вложенные sitemaps
        
    Returns:
        list: Список URL-адресов, найденных в sitemap.xml
        
    Raises:
        requests.RequestException: Если возникла ошибка при запросе
        ValueError: Если не удалось парсить файл
    """
    logger.info(f"Начинаю парсинг sitemap: {url}")
    
    try:
        # Отправляем запрос на получение sitemap
        response = requests.get(url, timeout=30, 
                              headers={"User-Agent": "SitemapParserBot/1.0"})
        response.raise_for_status()  # Проверка на HTTP-ошибки
        
        # Парсим содержимое
        soup = BeautifulSoup(response.content, "xml")
        
        # Инициализируем список для хранения URL
        urls = []
        
        # Проверяем, является ли это sitemap index файлом
        sitemap_tags = soup.find_all("sitemap")
        if sitemap_tags and recursive:
            logger.info(f"Найден sitemap index с {len(sitemap_tags)} вложенными sitemaps")
            
            # Обрабатываем каждый вложенный sitemap
            for sitemap in sitemap_tags:
                loc_tag = sitemap.find("loc")
                if loc_tag and loc_tag.text:
                    nested_sitemap_url = loc_tag.text.strip()
                    logger.info(f"Парсинг вложенного sitemap: {nested_sitemap_url}")
                    # Рекурсивно парсим вложенный sitemap
                    nested_urls = parse_sitemap(nested_sitemap_url, recursive=True)
                    urls.extend(nested_urls)
        else:
            # Это обычный sitemap файл, извлекаем URL
            url_tags = soup.find_all("url")
            
            if url_tags:
                logger.info(f"Найдено {len(url_tags)} URL тегов")
                
                for url_tag in url_tags:
                    loc_tag = url_tag.find("loc")
                    if loc_tag and loc_tag.text:
                        page_url = loc_tag.text.strip()
                        urls.append(page_url)
            else:
                # Альтернативная проверка для случаев, когда структура отличается
                loc_tags = soup.find_all("loc")
                logger.info(f"Найдено {len(loc_tags)} loc тегов")
                
                for loc_tag in loc_tags:
                    if loc_tag.parent.name != "sitemap":  # Исключаем теги loc внутри sitemap (для sitemap index)
                        page_url = loc_tag.text.strip()
                        urls.append(page_url)
        
        logger.info(f"Парсинг завершен. Найдено {len(urls)} URL.")
        return urls
    
    except requests.RequestException as e:
        logger.error(f"Ошибка HTTP-запроса: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Ошибка парсинга sitemap: {str(e)}")
        raise ValueError(f"Не удалось разобрать sitemap.xml: {str(e)}")

if __name__ == "__main__":
    # Для тестирования функции напрямую
    import sys
    
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    
    if len(sys.argv) > 1:
        test_url = sys.argv[1]
        try:
            result = parse_sitemap(test_url)
            print(f"Найдено {len(result)} URL:")
            for i, url in enumerate(result[:10], 1):
                print(f"{i}. {url}")
            
            if len(result) > 10:
                print(f"... и еще {len(result) - 10} URL.")
        except Exception as e:
            print(f"Ошибка: {e}")
    else:
        print("Использование: python sitemap_parser.py <url>") 