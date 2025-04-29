import os
import json
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Проверяем, находимся ли мы на платформе Vercel
IS_VERCEL = os.environ.get('VERCEL', '0') == '1'

# Кеш в памяти для локальной разработки
_memory_cache = {}

def _get_vercel_kv_api():
    """
    Получает API для Vercel KV Storage
    
    Требуются переменные окружения:
    - VERCEL_KV_URL
    - VERCEL_KV_REST_API_TOKEN
    - VERCEL_KV_REST_API_READ_ONLY_TOKEN
    """
    try:
        from vercel_kv import VercelKV
        
        kv_url = os.environ.get('VERCEL_KV_URL')
        kv_token = os.environ.get('VERCEL_KV_REST_API_TOKEN')
        
        if not kv_url or not kv_token:
            logger.warning("Не настроены переменные окружения VERCEL_KV_URL или VERCEL_KV_REST_API_TOKEN")
            return None
        
        return VercelKV(kv_url, kv_token)
    except ImportError:
        logger.warning("Библиотека vercel_kv не установлена")
        return None
    except Exception as e:
        logger.error(f"Ошибка при инициализации Vercel KV: {e}")
        return None

async def set_value(key: str, value: Any) -> bool:
    """
    Сохраняет значение в хранилище
    
    :param key: Ключ
    :param value: Значение (будет преобразовано в JSON)
    :return: True если успешно, иначе False
    """
    try:
        json_value = json.dumps(value)
        
        if IS_VERCEL:
            kv = _get_vercel_kv_api()
            if kv:
                await kv.set(key, json_value)
                return True
        
        # Если не на Vercel или не удалось инициализировать KV, используем кеш в памяти
        _memory_cache[key] = json_value
        return True
    except Exception as e:
        logger.error(f"Ошибка при сохранении значения для ключа {key}: {e}")
        return False

async def get_value(key: str, default: Any = None) -> Any:
    """
    Получает значение из хранилища
    
    :param key: Ключ
    :param default: Значение по умолчанию, если ключ не найден
    :return: Значение или default, если ключ не найден
    """
    try:
        if IS_VERCEL:
            kv = _get_vercel_kv_api()
            if kv:
                value = await kv.get(key)
                if value is not None:
                    return json.loads(value)
                return default
        
        # Если не на Vercel или не удалось инициализировать KV, используем кеш в памяти
        if key in _memory_cache:
            return json.loads(_memory_cache[key])
        
        return default
    except Exception as e:
        logger.error(f"Ошибка при получении значения для ключа {key}: {e}")
        return default

async def delete_value(key: str) -> bool:
    """
    Удаляет значение из хранилища
    
    :param key: Ключ
    :return: True если успешно, иначе False
    """
    try:
        if IS_VERCEL:
            kv = _get_vercel_kv_api()
            if kv:
                await kv.delete(key)
                return True
        
        # Если не на Vercel или не удалось инициализировать KV, используем кеш в памяти
        if key in _memory_cache:
            del _memory_cache[key]
        
        return True
    except Exception as e:
        logger.error(f"Ошибка при удалении значения для ключа {key}: {e}")
        return False 