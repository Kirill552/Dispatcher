# -*- coding: utf-8 -*-
"""
Синтетические данные встречных предложений от перевозчиков
Реалистичные предложения с разными ценами для проверки ИИ-продажника
"""

from datetime import datetime, timedelta
from typing import List, Dict
import random

# Базовые данные перевозчиков
SYNTHETIC_CARRIERS = [
    {
        "FirmId": 10001,
        "FirmName": "ТК ЭКСПРЕСС-ЛОГИСТИК",
        "ContactId": 50001,
        "Rating": 4.8,
        "CompletedOrders": 1250,
        "Equipment": ["Тент", "Рефрижератор"],
        "PriceMultiplier": 0.95  # На 5% дешевле рынка
    },
    {
        "FirmId": 10002, 
        "FirmName": "МЕГАПЕРЕВОЗКИ",
        "ContactId": 50002,
        "Rating": 4.5,
        "CompletedOrders": 800,
        "Equipment": ["Тент", "Открытая платформа"],
        "PriceMultiplier": 1.02  # На 2% дороже рынка
    },
    {
        "FirmId": 10003,
        "FirmName": "СИБИРЬ-ТРАНС",
        "ContactId": 50003, 
        "Rating": 4.9,
        "CompletedOrders": 2100,
        "Equipment": ["Тент", "Рефрижератор", "Автовоз"],
        "PriceMultiplier": 0.98  # На 2% дешевле рынка
    },
    {
        "FirmId": 10004,
        "FirmName": "БЫСТРЫЙ ГРУЗОВИК",
        "ContactId": 50004,
        "Rating": 4.2,
        "CompletedOrders": 450,
        "Equipment": ["Тент"],
        "PriceMultiplier": 1.08  # На 8% дороже рынка (новичок)
    },
    {
        "FirmId": 10005,
        "FirmName": "ПРОФИ-ЛОГИСТИК",
        "ContactId": 50005,
        "Rating": 4.7,
        "CompletedOrders": 1500,
        "Equipment": ["Тент", "Рефрижератор", "Открытая платформа"],
        "PriceMultiplier": 0.92  # На 8% дешевле рынка (лучшая цена)
    },
    {
        "FirmId": 10006,
        "FirmName": "АЛЬФА-ТРАНСПОРТ",
        "ContactId": 50006,
        "Rating": 4.6,
        "CompletedOrders": 950,
        "Equipment": ["Тент", "Изотерм"],
        "PriceMultiplier": 1.05  # На 5% дороже рынка
    }
]

# Базовые расценки по маршрутам (руб)
BASE_ROUTE_PRICES = {
    "Москва → Санкт-Петербург": 35000,
    "Екатеринбург → Новосибирск": 45000,
    "Казань → Ростов-на-Дону": 55000,
    "Челябинск → Воронеж": 48000,
    "Нижний Новгород → Краснодар": 52000,
    "Москва → Казань": 30000
}

def generate_synthetic_offers(cargo_id: str, cargo_data: Dict) -> List[Dict]:
    """Генерация синтетических предложений для груза"""
    route = f"{cargo_data['FromCityName']} → {cargo_data['ToCityName']}"
    base_price = BASE_ROUTE_PRICES.get(route, 40000)  # Дефолт 40к
    
    # Корректировка цены по весу и объему
    weight = cargo_data.get('Weight', 10000)
    volume = cargo_data.get('Volume', 30)
    
    # Увеличиваем цену для тяжелых и объемных грузов
    if weight > 15000:  # Больше 15 тонн
        base_price *= 1.15
    elif weight < 5000:  # Меньше 5 тонн
        base_price *= 0.85
        
    if volume > 50:  # Больше 50 м³
        base_price *= 1.1
    elif volume < 20:  # Меньше 20 м³  
        base_price *= 0.9
    
    # Корректировка по типу груза
    cargo_name = cargo_data.get('CargoName', '').lower()
    if 'замороженные' in cargo_name or 'рефрижератор' in cargo_name:
        base_price *= 1.2  # Рефрижератор дороже на 20%
    elif 'металл' in cargo_name:
        base_price *= 1.1  # Металл дороже на 10%
    elif 'текстиль' in cargo_name or 'одежда' in cargo_name:
        base_price *= 0.95  # Легкие грузы дешевле на 5%
    
    offers = []
    
    # Генерируем 3-7 предложений от разных перевозчиков
    num_offers = random.randint(3, 7)
    selected_carriers = random.sample(SYNTHETIC_CARRIERS, min(num_offers, len(SYNTHETIC_CARRIERS)))
    
    for i, carrier in enumerate(selected_carriers):
        # Рассчитываем цену с учетом мультипликатора перевозчика
        offer_price = base_price * carrier['PriceMultiplier']
        
        # Добавляем небольшую случайную вариацию (±3%)
        price_variation = random.uniform(0.97, 1.03)
        final_price = int(offer_price * price_variation)
        
        # Генерируем время отклика (от 10 минут до 3 часов назад)
        response_time = datetime.now() - timedelta(
            minutes=random.randint(10, 180)
        )
        
        offer = {
            "ResponseId": f"resp-{cargo_id}-{i+1:03d}",
            "LoadId": cargo_id,
            "LoadNumber": cargo_data.get('Number', f'T{i+1:03d}'),
            "LoadFirmId": 408001372,  # ID нашей фирмы
            "FirmId": carrier['FirmId'],
            "FirmName": carrier['FirmName'],
            "ContactId": carrier['ContactId'],
            "AddedAt": response_time.isoformat() + "Z",
            "UpdatedAt": response_time.isoformat() + "Z",
            "Price": final_price,
            "CurrencyId": 1,  # Рубли
            "NdsPrice": int(final_price * 1.2),  # С НДС +20%
            "NdsCurrencyId": 1,
            "NotNdsPrice": final_price,  # Без НДС
            "NotNdsCurrencyId": 1,
            "CounterOfferSource": random.choice([1, 2, 4]),  # Мобильное приложение, интегратор, страница поиска
            "Note": _generate_carrier_note(carrier, final_price),
            "PayAttributes": _generate_payment_attributes(),
            # Дополнительные поля для анализа
            "CarrierRating": carrier['Rating'],
            "CompletedOrders": carrier['CompletedOrders'],
            "Equipment": carrier['Equipment']
        }
        
        offers.append(offer)
    
    # Сортируем по цене (от дешевых к дорогим)
    offers.sort(key=lambda x: x['Price'])
    
    return offers

def _generate_carrier_note(carrier: Dict, price: float) -> str:
    """Генерация заметки от перевозчика"""
    notes = [
        f"Готовы выполнить перевозку за {price:,.0f} руб. Машина чистая, водитель опытный.",
        f"Предлагаем качественную перевозку. Цена {price:,.0f} руб. включает все расходы.",
        f"Профессиональная перевозка {price:,.0f} руб. Собственный автопарк, быстрая подача.",
        f"Выполним перевозку за {price:,.0f} руб. Страховка груза включена.",
        f"Надежная компания. Цена {price:,.0f} руб. фиксированная, без доплат."
    ]
    
    base_note = random.choice(notes)
    
    # Добавляем особенности для высокорейтинговых перевозчиков
    if carrier['Rating'] >= 4.7:
        extras = [
            " GPS-контроль маршрута.",
            " Сопровождение груза 24/7.",
            " Премиум-сервис."
        ]
        base_note += random.choice(extras)
    
    return base_note

def _generate_payment_attributes() -> int:
    """Генерация атрибутов оплаты"""
    # Битовая сумма:
    # 1 - наличные, 2 - безнал, 4 - блиц, 8 - НДС, 16 - предоплата
    payment_options = [
        3,   # наличные + безнал
        10,  # безнал + НДС
        11,  # наличные + безнал + НДС  
        18,  # безнал + НДС + предоплата
        6,   # безнал + блиц
        14   # безнал + блиц + НДС
    ]
    return random.choice(payment_options)

# Предзаготовленные предложения для конкретных грузов
PREDEFINED_OFFERS = {
    "test-cargo-001": [  # Стройматериалы Москва-СПб
        {
            "ResponseId": "resp-001-001",
            "LoadId": "test-cargo-001",
            "FirmName": "ПРОФИ-ЛОГИСТИК",
            "Price": 32200,
            "NdsPrice": 38640,
            "NotNdsPrice": 32200,
            "CarrierRating": 4.7,
            "Note": "Готовы выполнить перевозку стройматериалов за 32,200 руб. Большой опыт работы со стройкой."
        },
        {
            "ResponseId": "resp-001-002", 
            "LoadId": "test-cargo-001",
            "FirmName": "ТК ЭКСПРЕСС-ЛОГИСТИК",
            "Price": 33500,
            "NdsPrice": 40200,
            "NotNdsPrice": 33500,
            "CarrierRating": 4.8,
            "Note": "Профессиональная перевозка 33,500 руб. Собственный автопарк, быстрая подача."
        },
        {
            "ResponseId": "resp-001-003",
            "LoadId": "test-cargo-001", 
            "FirmName": "МЕГАПЕРЕВОЗКИ",
            "Price": 35700,
            "NdsPrice": 42840,
            "NotNdsPrice": 35700,
            "CarrierRating": 4.5,
            "Note": "Выполним перевозку за 35,700 руб. Страховка груза включена."
        },
        {
            "ResponseId": "resp-001-004",
            "LoadId": "test-cargo-001",
            "FirmName": "БЫСТРЫЙ ГРУЗОВИК", 
            "Price": 37800,
            "NdsPrice": 45360,
            "NotNdsPrice": 37800,
            "CarrierRating": 4.2,
            "Note": "Готовы выполнить перевозку за 37,800 руб. Машина чистая, водитель опытный."
        }
    ],
    "test-cargo-002": [  # Рефрижератор Екатеринбург-Новосибирск
        {
            "ResponseId": "resp-002-001",
            "LoadId": "test-cargo-002",
            "FirmName": "СИБИРЬ-ТРАНС",
            "Price": 49900,
            "NdsPrice": 59880,
            "NotNdsPrice": 49900,
            "CarrierRating": 4.9,
            "Note": "Рефрижераторная перевозка 49,900 руб. Собственный парк рефов, контроль температуры."
        },
        {
            "ResponseId": "resp-002-002",
            "LoadId": "test-cargo-002",
            "FirmName": "ТК ЭКСПРЕСС-ЛОГИСТИК", 
            "Price": 52100,
            "NdsPrice": 62520,
            "NotNdsPrice": 52100,
            "CarrierRating": 4.8,
            "Note": "Замороженные продукты 52,100 руб. GPS-контроль маршрута и температуры."
        },
        {
            "ResponseId": "resp-002-003",
            "LoadId": "test-cargo-002",
            "FirmName": "ПРОФИ-ЛОГИСТИК",
            "Price": 54300,
            "NdsPrice": 65160,
            "NotNdsPrice": 54300, 
            "CarrierRating": 4.7,
            "Note": "Рефрижератор 54,300 руб. Премиум-сервис, сопровождение груза 24/7."
        }
    ]
}

def get_offers_for_cargo(cargo_id: str, cargo_data: Dict = None) -> List[Dict]:
    """Получить предложения для груза (предзаготовленные или сгенерированные)"""
    
    # Если есть предзаготовленные предложения - используем их
    if cargo_id in PREDEFINED_OFFERS:
        return PREDEFINED_OFFERS[cargo_id]
    
    # Иначе генерируем синтетические
    if cargo_data:
        return generate_synthetic_offers(cargo_id, cargo_data)
    
    return []

def get_best_offer(offers: List[Dict]) -> Dict:
    """Получить лучшее предложение (минимальная цена)"""
    if not offers:
        return None
    
    return min(offers, key=lambda x: x.get('Price', float('inf')))

def get_carrier_by_firm_id(firm_id: int) -> Dict:
    """Получить данные перевозчика по FirmId"""
    for carrier in SYNTHETIC_CARRIERS:
        if carrier['FirmId'] == firm_id:
            return carrier
    return None 