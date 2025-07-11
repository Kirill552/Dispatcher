"""
Парсеры для различных логистических площадок
"""
import asyncio
import aiohttp
from bs4 import BeautifulSoup
from typing import Dict, List, Optional
from datetime import datetime
from utils.config import settings
from utils.logger import get_logger

logger = get_logger("PARSERS")


class LogisticsPlatformParser:
    """Базовый класс для парсинга логистических площадок"""
    
    def __init__(self):
        self.session = None
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(headers=self.headers)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()


class DellinParser(LogisticsPlatformParser):
    """Парсер для Dellin.ru"""
    
    BASE_URL = "https://www.dellin.ru"
    
    async def get_cargo_orders(self, city_from: str = "", city_to: str = "") -> List[Dict]:
        """Получение грузов с Dellin.ru"""
        
        try:
            # Поиск по грузам (обратное направление)
            search_url = f"{self.BASE_URL}/find/cargo"
            params = {
                'from': city_from,
                'to': city_to,
                'weight_from': settings.min_order_amount // 50,  # примерный вес
                'page': 1
            }
            
            async with self.session.get(search_url, params=params) as response:
                html = await response.text()
                
            soup = BeautifulSoup(html, 'html.parser')
            cargo_items = soup.find_all('div', class_='cargo-item')
            
            cargos = []
            for item in cargo_items:
                try:
                    cargo_data = self._parse_dellin_cargo(item)
                    if cargo_data:
                        cargos.append(cargo_data)
                except Exception as e:
                    logger.error(f"Ошибка парсинга груза Dellin: {str(e)}")
                    continue
            
            logger.info(f"Найдено {len(cargos)} грузов на Dellin.ru")
            return cargos
            
        except Exception as e:
            logger.error(f"Ошибка парсинга Dellin.ru: {str(e)}")
            return []
    
    def _parse_dellin_cargo(self, item) -> Optional[Dict]:
        """Парсинг отдельного груза с Dellin"""
        
        try:
            # Извлекаем данные из HTML
            route_elem = item.find('div', class_='route')
            price_elem = item.find('div', class_='price')
            weight_elem = item.find('div', class_='weight')
            contact_elem = item.find('div', class_='contact')
            
            if not route_elem or not price_elem:
                return None
            
            route = route_elem.get_text(strip=True)
            price_text = price_elem.get_text(strip=True)
            weight_text = weight_elem.get_text(strip=True) if weight_elem else "н/д"
            
            # Извлекаем цену
            price = self._extract_price(price_text)
            
            return {
                'source': 'dellin.ru',
                'route': route,
                'price': price,
                'weight': self._extract_weight(weight_text),
                'description': item.get_text(strip=True),
                'contact_info': self._extract_contact(contact_elem),
                'url': self.BASE_URL + item.find('a')['href'] if item.find('a') else '',
                'found_at': datetime.now()
            }
            
        except Exception as e:
            logger.error(f"Ошибка парсинга груза: {str(e)}")
            return None
    
    def _extract_price(self, price_text: str) -> int:
        """Извлечение цены из текста"""
        import re
        price_match = re.search(r'(\d+(?:\s*\d+)*)', price_text.replace(' ', ''))
        return int(price_match.group(1)) if price_match else 0
    
    def _extract_weight(self, weight_text: str) -> float:
        """Извлечение веса из текста"""
        import re
        weight_match = re.search(r'(\d+(?:\.\d+)?)', weight_text)
        return float(weight_match.group(1)) if weight_match else 0.0
    
    def _extract_contact(self, contact_elem) -> Dict:
        """Извлечение контактной информации"""
        if not contact_elem:
            return {}
        
        contact_text = contact_elem.get_text(strip=True)
        
        # Ищем телефон
        import re
        phone_match = re.search(r'[\+]?[7-8][\s\-]?\(?(\d{3})\)?[\s\-]?(\d{3})[\s\-]?(\d{2})[\s\-]?(\d{2})', contact_text)
        
        return {
            'phone': phone_match.group(0) if phone_match else '',
            'raw_text': contact_text
        }


class PlatformAggregator:
    """Агрегатор для сбора данных со всех площадок"""
    
    def __init__(self):
        self.parsers = {
            'dellin': DellinParser(),
        }
    
    async def collect_all_cargos(self, regions: List[str] = None) -> List[Dict]:
        """Сбор грузов со всех площадок"""
        
        if not regions:
            regions = ["москва", "санкт-петербург", "екатеринбург", "новосибирск"]
        
        all_cargos = []
        
        for platform_name, parser in self.parsers.items():
            try:
                logger.info(f"🔍 Парсинг площадки {platform_name}")
                
                async with parser:
                    # Парсим по городам
                    for i, city_from in enumerate(regions):
                        for city_to in regions[i+1:]:
                            cargos = await parser.get_cargo_orders(city_from, city_to)
                            all_cargos.extend(cargos)
                            
                            # Пауза между запросами
                            await asyncio.sleep(2)
                
                logger.info(f"✅ {platform_name}: найдено {len([c for c in all_cargos if c['source'] == platform_name])} грузов")
                
            except Exception as e:
                logger.error(f"❌ Ошибка парсинга {platform_name}: {str(e)}")
                
        # Удаляем дубликаты
        unique_cargos = self._remove_duplicates(all_cargos)
        
        logger.info(f"🎯 Итого найдено {len(unique_cargos)} уникальных грузов")
        
        return unique_cargos
    
    def _remove_duplicates(self, cargos: List[Dict]) -> List[Dict]:
        """Удаление дубликатов грузов"""
        
        seen = set()
        unique_cargos = []
        
        for cargo in cargos:
            # Создаем ключ для дедупликации
            key = f"{cargo['route']}_{cargo['price']}_{cargo.get('weight', 0)}"
            
            if key not in seen:
                seen.add(key)
                unique_cargos.append(cargo)
        
        return unique_cargos


# Глобальный экземпляр агрегатора
platform_aggregator = PlatformAggregator() 