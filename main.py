"""
Главный файл ИИ-диспетчера логистики
Запуск всех компонентов системы
"""
import asyncio
import signal
import sys
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI
from uvicorn import run

# Импорты наших модулей
from utils.config import settings
from utils.logger import get_logger
from ati_integration.cargo_monitor import cargo_monitor
from ati_integration.business_logic_new import ati_business
from ai_services.ai_dispatcher_logic import AIDispatcherLogic
from ai_services.sales_agent import sales_agent
# from ai_services.advertising_campaigns_agent import advertising_campaigns_agent  # ОТКЛЮЧЕНО - перенесено в отдельный проект
from bot.client_bot import client_bot
from database.database import init_database
from parsers.logistics_platforms import platform_aggregator
from social_monitoring.telegram_monitor import telegram_monitor
from advertising.simple_landing import setup_simple_landing  # Упрощенный лендинг без чата
from ati_integration.cargo_renewal_manager import cargo_renewal_manager
from ati_integration.offers_monitor import offers_monitor

logger = get_logger("MAIN")

# Инициализация ИИ-диспетчера
ai_dispatcher = AIDispatcherLogic()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом приложения"""
    
    logger.info("🚀 Запуск ИИ-диспетчера логистики")
    
    # Инициализация базы данных
    await init_database()
    logger.info("✅ База данных инициализирована")
    
    # Запуск фоновых задач
    tasks = []
    
    try:
        # Запуск мониторинга грузов ATI.SU
        monitor_task = asyncio.create_task(cargo_monitor.start_monitoring())
        tasks.append(monitor_task)
        logger.info("✅ Мониторинг грузов ATI.SU запущен")
        
        # Запуск системы автоматического обновления грузов
        renewal_task = asyncio.create_task(cargo_renewal_manager.start_monitoring())
        tasks.append(renewal_task)
        logger.info("✅ Система автоматического обновления грузов запущена")
        
        # Запуск мониторинга встречных предложений с ИИ-продажником
        offers_task = asyncio.create_task(offers_monitor.start_monitoring())
        tasks.append(offers_task)
        logger.info("✅ Мониторинг встречных предложений с ИИ-продажником запущен")
        
        # Запуск Telegram бота отключён в режиме лендинга
        bot_task = asyncio.create_task(client_bot.start_bot())
        tasks.append(bot_task)
        logger.info("✅ Telegram бот запущен")
        
        # Запуск парсинга других площадок (в отдельном таске)
        # parser_task = asyncio.create_task(platform_aggregator.start_monitoring())
        # tasks.append(parser_task)
        # logger.info("✅ Парсинг площадок запущен")
        
        # Запуск мониторинга Telegram каналов (опционально)
        # if hasattr(settings, 'telegram_api_id'):
        #     telegram_task = asyncio.create_task(telegram_monitor.start_monitoring())
        #     tasks.append(telegram_task)
        #     logger.info("✅ Мониторинг Telegram каналов запущен")
        
        logger.info("🎯 Все сервисы запущены успешно!")
        logger.info(f"📊 Мониторинг: каждые {settings.monitoring_interval_seconds} секунд")
        logger.info(f"💰 Наценка к перевозчикам: {settings.default_commission_percent}%")
        logger.info(f"📞 Контакт: {settings.dispatcher_phone}")
        
        yield
        
    except Exception as e:
        logger.error(f"❌ Ошибка при запуске сервисов: {str(e)}")
        raise
    finally:
        # Остановка всех задач
        logger.info("🛑 Остановка сервисов...")
        
        await cargo_monitor.stop_monitoring()
        await cargo_renewal_manager.stop_monitoring()
        await offers_monitor.stop_monitoring()
        await client_bot.stop_bot()
        
        # Отменяем все задачи
        for task in tasks:
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        logger.info("✅ Все сервисы остановлены")


# Создание FastAPI приложения
app = FastAPI(
    title="ИИ-Диспетчер Логистики",
    description="Автоматизированная система поиска и обработки заказов на перевозку грузов",
    version="1.0.0",
    lifespan=lifespan
)

# Настройка лендинга - остается в проекте
landing_system = setup_simple_landing(app)


@app.get("/")
async def root():
    """Главная страница API"""
    return {
        "message": "ИИ-Диспетчер Логистики",
        "version": "1.0.0",
        "status": "running",
        "services": {
            "ati_monitor": cargo_monitor.is_running,
            "offers_monitor": offers_monitor.is_running,
            "telegram_bot": client_bot.app is not None
        }
    }


@app.get("/health")
async def health_check():
    """Проверка здоровья системы"""
    
    stats = await cargo_monitor.get_monitoring_stats()
    
    return {
        "status": "healthy",
        "timestamp": asyncio.get_event_loop().time(),
        "monitoring": stats,
        "config": {
            "service_markup": settings.default_commission_percent,
            "min_order_amount": settings.min_order_amount,
            "max_order_amount": settings.max_order_amount
        }
    }


@app.get("/stats")
async def get_stats():
    """Получить статистику работы системы"""
    
    monitoring_stats = await cargo_monitor.get_monitoring_stats()
    offers_stats = await offers_monitor.get_monitoring_stats()
    
    return {
        "monitoring": monitoring_stats,
        "offers_monitoring": offers_stats,
        "system": {
            "debug_mode": settings.debug,
            "log_level": settings.log_level,
            "database_url": settings.database_url.split("://")[0] + "://***"  # скрываем детали
        }
    }


@app.post("/webhook/ati")
async def ati_webhook(payload: dict):
    """Вебхук для получения уведомлений от ATI.SU"""
    
    logger.info(f"📬 Получен вебхук от ATI.SU: {payload}")
    
    # TODO: Обработка уведомлений от ATI.SU
    # - Новые отклики на наши грузы
    # - Изменения статуса заказов
    # - Сообщения в мессенджере
    
    return {"status": "received"}


@app.post("/webhook/telegram")
async def telegram_webhook(payload: dict):
    """Вебхук для Telegram (альтернатива polling)"""
    
    # Если используем webhook вместо polling
    if settings.telegram_webhook_url:
        logger.info("📬 Получен вебхук от Telegram")
        # TODO: Обработка через webhook
    
    return {"status": "received"}


@app.get("/api/leads")
async def get_leads_stats():
    """Получить статистику лидов"""
    
    # TODO: Реализовать получение статистики из БД
    return {
        "total_leads": 245,
        "today_leads": 12,
        "conversion_rate": 23.5,
        "sources": {
            "ati.su": 65,
            "telegram": 43,
            "landing": 78,
            "dellin": 32,
            "avito": 27
        }
    }


@app.get("/api/platforms")
async def get_platforms_status():
    """Статус мониторинга площадок"""
    
    return {
        "ati_monitor": cargo_monitor.is_running,
        "telegram_monitor": False,  # telegram_monitor.is_running if hasattr else False
        "parsers_status": {
            "dellin": "active",
            "perevozka24": "inactive", 
            "cargo_alliance": "inactive",
            "avito": "inactive"
        },
        "last_update": "2024-01-15T10:30:00Z"
    }


@app.post("/api/external-order")
async def process_external_order(order_data: dict):
    """Обработка заказа через ИИ-диспетчера с интеграцией ATI.SU"""
    
    logger.info(f"📥 Получен внешний заказ: {order_data}")
    
    try:
        # Используем новую логику ИИ-диспетчера
        result = await ai_dispatcher.process_client_order(order_data)
        return result
    except Exception as e:
        logger.error(f"❌ Ошибка обработки внешнего заказа: {str(e)}")
        return {"status": "error", "error": str(e)}


@app.get("/api/business-stats")
async def get_business_stats():
    """Статистика работы ИИ-диспетчера"""
    
    try:
        stats = await ai_dispatcher.get_statistics()
        return stats
    except Exception as e:
        logger.error(f"❌ Ошибка получения статистики: {str(e)}")
        return {"status": "error", "error": str(e)}


@app.get("/api/order-status/{order_id}")
async def get_order_status(order_id: str):
    """Получить статус заказа"""
    
    try:
        status = await ai_dispatcher.get_order_status(order_id)
        return status
    except Exception as e:
        logger.error(f"❌ Ошибка получения статуса заказа: {str(e)}")
        return {"status": "error", "error": str(e)}


@app.post("/api/ai-clarify-order")
async def clarify_order_details(clarification_data: dict):
    """ИИ уточняет детали заказа у клиента"""
    
    try:
        client_data = clarification_data.get("client_data", {})
        additional_info = clarification_data.get("additional_info", {})
        
        # Объединяем данные
        updated_data = {**client_data, **additional_info}
        
        # Повторно обрабатываем с дополнительной информацией
        result = await ai_dispatcher.process_client_order(updated_data)
        return result
        
    except Exception as e:
        logger.error(f"❌ Ошибка уточнения заказа: {str(e)}")
        return {"status": "error", "error": str(e)}


@app.post("/api/parse-platforms")
async def trigger_platforms_parsing():
    """Запуск парсинга всех площадок"""
    
    try:
        # Запускаем парсинг в фоне
        asyncio.create_task(platform_aggregator.collect_all_cargos())
        
        return {"status": "started", "message": "Парсинг площадок запущен"}
        
    except Exception as e:
        logger.error(f"Ошибка запуска парсинга: {str(e)}")
        return {"status": "error", "message": str(e)}


@app.get("/api/ai-agent/conversation/{client_id}")
async def get_conversation_history(client_id: int):
    """Получить историю разговора с клиентом"""
    
    try:
        # TODO: Получить из БД
        return {
            "client_id": client_id,
            "messages": [
                {"sender": "client", "text": "Нужно перевезти груз", "timestamp": "2024-01-15T10:00:00Z"},
                {"sender": "bot", "text": "Расскажите подробнее о грузе", "timestamp": "2024-01-15T10:00:30Z"}
            ]
        }
        
    except Exception as e:
        return {"error": str(e)}


@app.post("/api/ai-agent/analyze-lead")
async def analyze_lead_quality(lead_data: dict):
    """Анализ качества лида через ИИ"""
    
    try:
        analysis = await sales_agent.analyze_lead_quality(lead_data)
        return {"success": True, "analysis": analysis}
        
    except Exception as e:
        logger.error(f"Ошибка анализа лида: {str(e)}")
        return {"success": False, "error": str(e)}


# РЕКЛАМНЫЕ API ОТКЛЮЧЕНЫ - ПЕРЕНЕСЕНЫ В ОТДЕЛЬНЫЙ ПРОЕКТ

# @app.post("/api/advertising/create-campaign-plan")
# async def create_campaign_plan(request_data: dict):
#     """Создание комплексного плана рекламной кампании"""
#     
#     try:
#         business_request = request_data.get("business_request", "")
#         
#         if not business_request:
#             return {"success": False, "error": "Не указан запрос о бизнесе"}
#         
#         # Создаем комплексный план кампании
#         campaign_plan = await advertising_campaigns_agent.create_comprehensive_campaign_plan(business_request)
#         
#         return {
#             "success": True,
#             "campaign_plan": campaign_plan,
#             "message": "Комплексный план рекламной кампании создан"
#         }
#         
#     except Exception as e:
#         logger.error(f"Ошибка создания плана кампании: {str(e)}")
#         return {"success": False, "error": str(e)}


# @app.post("/api/advertising/analyze-business")
# async def analyze_business_context(business_data: dict):
#     """Анализ бизнес-контекста для рекламной стратегии"""
#     
#     try:
#         context = await advertising_campaigns_agent.analyze_business_context(business_data)
#         
#         return {
#             "success": True,
#             "business_context": context.__dict__,
#             "message": "Анализ бизнес-контекста завершен"
#         }
#         
#     except Exception as e:
#         logger.error(f"Ошибка анализа бизнеса: {str(e)}")
#         return {"success": False, "error": str(e)}


# @app.post("/api/advertising/optimize-campaign")
# async def optimize_campaign(optimization_data: dict):
#     """Оптимизация существующей рекламной кампании"""
#     
#     try:
#         campaign_data = optimization_data.get("campaign_data", {})
#         performance_metrics = optimization_data.get("performance_metrics", {})
#         
#         optimization_plan = await advertising_campaigns_agent.optimize_campaign_performance(
#             campaign_data, performance_metrics
#         )
#         
#         return {
#             "success": True,
#             "optimization_plan": optimization_plan,
#             "message": "План оптимизации кампании создан"
#         }
#         
#     except Exception as e:
#         logger.error(f"Ошибка оптимизации кампании: {str(e)}")
#         return {"success": False, "error": str(e)}


# @app.post("/api/advertising/generate-creatives")
# async def generate_ad_creatives(creative_data: dict):
#     """Генерация креативных вариантов объявлений"""
#     
#     try:
#         product_info = creative_data.get("product_info", {})
#         target_audience = creative_data.get("target_audience", {})
#         competitor_analysis = creative_data.get("competitor_analysis")
#         
#         creative_variants = await advertising_campaigns_agent.generate_creative_variants(
#             product_info, target_audience, competitor_analysis
#         )
#         
#         return {
#             "success": True,
#             "creative_variants": creative_variants,
#             "total_variants": len(creative_variants),
#             "message": f"Создано {len(creative_variants)} вариантов объявлений"
#         }
#         
#     except Exception as e:
#         logger.error(f"Ошибка генерации креативов: {str(e)}")
#         return {"success": False, "error": str(e)}


# @app.get("/api/advertising/campaign-templates")
# async def get_campaign_templates():
#     """Получение шаблонов кампаний для разных отраслей"""
#     
#     templates = {
#         "logistics": {
#             "name": "Грузоперевозки",
#             "campaign_types": ["TEXT_CAMPAIGN", "DYNAMIC_TEXT_CAMPAIGN"],
#             "typical_keywords": [
#                 "грузоперевозки", "доставка грузов", "перевозка", "транспортная компания",
#                 "логистические услуги", "грузовое такси", "переезд офиса"
#             ],
#             "target_audience": {
#                 "age": "25-65",
#                 "interests": ["business", "logistics", "transport"],
#                 "behavior": "business_owners, managers"
#             },
#             "average_cpc": "150-300 руб",
#             "conversion_rate": "3-8%"
#         },
#         "ecommerce": {
#             "name": "Интернет-магазины",
#             "campaign_types": ["TEXT_CAMPAIGN", "SMART_CAMPAIGN", "DYNAMIC_TEXT_CAMPAIGN"],
#             "typical_keywords": [
#                 "купить", "заказать", "интернет-магазин", "доставка", "скидки"
#             ],
#             "target_audience": {
#                 "age": "18-55",
#                 "interests": ["shopping", "online_purchases"],
#                 "behavior": "online_shoppers"
#             },
#             "average_cpc": "50-200 руб",
#             "conversion_rate": "2-5%"
#         },
#         "services": {
#             "name": "Услуги для бизнеса",
#             "campaign_types": ["TEXT_CAMPAIGN"],
#             "typical_keywords": [
#                 "услуги", "консультации", "аутсорсинг", "бизнес решения"
#             ],
#             "target_audience": {
#                 "age": "30-60",
#                 "interests": ["business", "professional_services"],
#                 "behavior": "decision_makers"
#             },
#             "average_cpc": "200-500 руб",
#             "conversion_rate": "5-15%"
#         }
#     }
#     
#     return {
#         "success": True,
#         "templates": templates,
#         "message": "Шаблоны кампаний загружены"
#     }


# @app.get("/api/advertising/market-insights")
# async def get_market_insights():
#     """Аналитические данные о рекламном рынке"""
#     
#     insights = {
#         "yandex_direct_trends": {
#             "growing_industries": [
#                 "e-commerce", "delivery", "digital_services", "healthcare", "education"
#             ],
#             "declining_cpc": ["travel", "entertainment", "offline_retail"],
#             "rising_cpc": ["finance", "insurance", "real_estate", "legal_services"],
#             "seasonal_peaks": {
#                 "november": ["black_friday", "winter_goods"],
#                 "december": ["new_year", "gifts"],
#                 "january": ["fitness", "education", "business_services"],
#                 "march": ["spring_goods", "construction", "auto"]
#             }
#         },
#         "best_practices": {
#             "ad_text_optimization": [
#                 "Используйте числа в заголовках",
#                 "Добавляйте призывы к действию",
#                 "Указывайте конкретные выгоды",
#                 "Тестируйте эмоциональные триггеры"
#             ],
#             "keyword_strategy": [
#                 "Собирайте семантику из нескольких источников",
#                 "Используйте разные типы соответствия",
#                 "Регулярно анализируйте поисковые запросы",
#                 "Добавляйте минус-слова еженедельно"
#             ],
#             "bidding_optimization": [
#                 "Начинайте с автоматических стратегий",
#                 "Переходите на ручное управление при достаточных данных",
#                 "Учитывайте конкурентную ситуацию",
#                 "Корректируйте ставки по времени суток"
#             ]
#         },
#         "performance_benchmarks": {
#             "ctr_by_industry": {
#                 "logistics": "4-8%",
#                 "ecommerce": "3-6%",
#                 "services": "5-10%",
#                 "finance": "2-4%"
#             },
#             "conversion_rates": {
#                 "logistics": "3-8%",
#                 "ecommerce": "2-5%",
#                 "services": "5-15%",
#                 "finance": "1-3%"
#             }
#         }
#     }
#     
#     return {
#         "success": True,
#         "insights": insights,
#         "updated_at": datetime.now().isoformat()
#     }


@app.get("/api/cargo-renewal/status")
async def get_cargo_renewal_status():
    """Получить статус системы автоматического обновления грузов"""
    try:
        status = await cargo_renewal_manager.get_renewal_status()
        return {"success": True, "status": status}
    except Exception as e:
        logger.error(f"❌ Ошибка получения статуса обновления грузов: {str(e)}")
        return {"success": False, "error": str(e)}


@app.post("/api/cargo-renewal/add-cargo")
async def add_cargo_for_renewal(request_data: dict):
    """Добавить груз в систему автоматического обновления"""
    try:
        cargo_id = request_data.get("cargo_id")
        delay_minutes = request_data.get("delay_minutes", 0)
        
        if not cargo_id:
            return {"success": False, "error": "Не указан cargo_id"}
        
        await cargo_renewal_manager.add_cargo_for_renewal(cargo_id, delay_minutes)
        
        return {
            "success": True,
            "message": f"Груз {cargo_id} добавлен в систему обновления"
        }
        
    except Exception as e:
        logger.error(f"❌ Ошибка добавления груза в систему обновления: {str(e)}")
        return {"success": False, "error": str(e)}


@app.post("/api/cargo-renewal/remove-cargo")
async def remove_cargo_from_renewal(request_data: dict):
    """Удалить груз из системы автоматического обновления"""
    try:
        cargo_id = request_data.get("cargo_id")
        
        if not cargo_id:
            return {"success": False, "error": "Не указан cargo_id"}
        
        await cargo_renewal_manager.remove_cargo_from_renewal(cargo_id)
        
        return {
            "success": True,
            "message": f"Груз {cargo_id} удален из системы обновления"
        }
        
    except Exception as e:
        logger.error(f"❌ Ошибка удаления груза из системы обновления: {str(e)}")
        return {"success": False, "error": str(e)}


@app.post("/api/cargo-renewal/manual-renewal")
async def manual_cargo_renewal(request_data: dict):
    """Ручное обновление указанных грузов"""
    try:
        cargo_ids = request_data.get("cargo_ids", [])
        
        if not cargo_ids:
            return {"success": False, "error": "Не указаны cargo_ids"}
        
        results = await cargo_renewal_manager.ati_client.renew_multiple_cargos(cargo_ids)
        
        return {
            "success": True,
            "results": results,
            "message": f"Обновление {len(cargo_ids)} грузов завершено"
        }
        
    except Exception as e:
        logger.error(f"❌ Ошибка ручного обновления грузов: {str(e)}")
        return {"success": False, "error": str(e)}


@app.get("/api/cargo-renewal/renewable-loads")
async def get_renewable_loads():
    """Получить список грузов готовых к обновлению"""
    try:
        renewable_loads = await cargo_renewal_manager.ati_client.get_renewable_loads()
        
        return {
            "success": True,
            "renewable_loads": renewable_loads,
            "total_count": len(renewable_loads)
        }
        
    except Exception as e:
        logger.error(f"❌ Ошибка получения обновляемых грузов: {str(e)}")
        return {"success": False, "error": str(e)}


@app.get("/api/cargo-renewal/company-loads")
async def get_company_loads():
    """Получить все грузы фирмы с информацией об обновлении"""
    try:
        company_loads = await cargo_renewal_manager.ati_client.get_all_company_loads()
        
        return {
            "success": True,
            "company_loads": company_loads,
            "total_count": len(company_loads)
        }
        
    except Exception as e:
        logger.error(f"❌ Ошибка получения грузов фирмы: {str(e)}")
        return {"success": False, "error": str(e)}


@app.get("/api/offers-monitor/status")
async def get_offers_monitor_status():
    """Получить статус мониторинга встречных предложений"""
    try:
        stats = await offers_monitor.get_monitoring_stats()
        
        return {
            "status": "success",
            "data": stats
        }
        
    except Exception as e:
        logger.error(f"❌ Ошибка получения статуса мониторинга предложений: {e}")
        return {"status": "error", "message": str(e)}


@app.post("/api/offers-monitor/start")
async def start_offers_monitor():
    """Запустить мониторинг встречных предложений"""
    try:
        if offers_monitor.is_running:
            return {"status": "already_running", "message": "Мониторинг уже запущен"}
        
        # Запускаем в фоновой задаче
        asyncio.create_task(offers_monitor.start_monitoring())
        
        return {"status": "success", "message": "Мониторинг встречных предложений запущен"}
        
    except Exception as e:
        logger.error(f"❌ Ошибка запуска мониторинга предложений: {e}")
        return {"status": "error", "message": str(e)}


@app.post("/api/offers-monitor/stop")
async def stop_offers_monitor():
    """Остановить мониторинг встречных предложений"""
    try:
        await offers_monitor.stop_monitoring()
        
        return {"status": "success", "message": "Мониторинг встречных предложений остановлен"}
        
    except Exception as e:
        logger.error(f"❌ Ошибка остановки мониторинга предложений: {e}")
        return {"status": "error", "message": str(e)}


@app.get("/api/offers-monitor/active-cargos")
async def get_active_monitored_cargos():
    """Получить активные грузы в мониторинге"""
    try:
        # Получаем данные из кэша мониторинга
        active_cargos = []
        for cargo_id, cargo_offers in offers_monitor.monitored_cargos.items():
            active_cargos.append({
                "cargo_id": cargo_id,
                "cargo_number": cargo_offers.cargo_number,
                "cargo_name": cargo_offers.cargo_name,
                "route": cargo_offers.route,
                "offers_count": cargo_offers.offers_count,
                "best_offer_price": cargo_offers.best_offer_price,
                "last_check": cargo_offers.last_check.isoformat(),
                "ready_for_sale": cargo_offers.offers_count >= offers_monitor.min_offers_for_sale
            })
        
        return {
            "status": "success",
            "total_active_cargos": len(active_cargos),
            "ready_for_sale": len([c for c in active_cargos if c["ready_for_sale"]]),
            "cargos": active_cargos
        }
        
    except Exception as e:
        logger.error(f"❌ Ошибка получения активных грузов: {e}")
        return {"status": "error", "message": str(e)}


@app.post("/api/test-ai-sales/{cargo_id}")
async def test_ai_sales_for_cargo(cargo_id: str):
    """
    Тестирование ИИ-продажника для конкретного груза
    Добавляет груз в БД и запускает анализ предложений
    """
    try:
        from database.crud import create_order, get_order_by_ati_cargo_id
        from ati_integration.ati_client_v2 import ATIClientV2
        
        # Создаем экземпляр клиента
        ati_client = ATIClientV2()
        
        # Получаем данные о грузе
        logger.info(f"🔍 Получение данных о грузе {cargo_id}")
        cargo = await ati_client.get_cargo_by_id(cargo_id)
        
        if not cargo:
            return {
                "error": f"Груз {cargo_id} не найден или недоступен",
                "status": "error"
            }
        
        # Извлекаем основные данные
        cargo_name = "Тестовый груз"
        from_city = "Неизвестно"
        to_city = "Неизвестно"
        weight = 0
        volume = 0
        
        # Получаем название груза
        if cargo.get('Cargo'):
            if cargo['Cargo'].get('CargoType'):
                cargo_name = cargo['Cargo']['CargoType']
            weight = cargo['Cargo'].get('Weight', 0)
            volume = cargo['Cargo'].get('Volume', 0)
        
        # Получаем города
        if cargo.get('Loading'):
            loading_city_id = cargo['Loading'].get('CityId')
            if loading_city_id:
                from_city_data = await ati_client.get_city_by_id(loading_city_id)
                if from_city_data:
                    from_city = from_city_data.get('Name', f'ID:{loading_city_id}')
                    
        if cargo.get('Unloading'):
            unloading_city_id = cargo['Unloading'].get('CityId')
            if unloading_city_id:
                to_city_data = await ati_client.get_city_by_id(unloading_city_id)
                if to_city_data:
                    to_city = to_city_data.get('Name', f'ID:{unloading_city_id}')
        
        # Проверяем не существует ли уже заказ с таким ati_cargo_id
        existing_order = await get_order_by_ati_cargo_id(cargo_id)
        
        if existing_order:
            logger.info(f"✅ Заказ с ati_cargo_id {cargo_id} уже существует (ID: {existing_order.id})")
            order_id = existing_order.id
        else:
            # Создаем новый заказ в базе данных
            order_data = {
                'ati_cargo_id': cargo_id,
                'contact_phone': '+79000000000',  # Тестовый номер
                'contact_name': 'Тестовый клиент',
                'cargo_type': cargo_name,
                'from_city': from_city,
                'to_city': to_city,
                'weight': weight,
                'volume': volume,
                'loading_date': datetime.now(),
                'status': 'searching_offers',
                'owner_id': 408001372,  # Telegram ID владельца для уведомлений
                'created_at': datetime.now()
            }
            
            new_order = await create_order(order_data)
            order_id = new_order.id
            logger.info(f"✅ Создан новый заказ с ID: {order_id}")
        
        # Получаем встречные предложения
        logger.info(f"🔍 Получение встречных предложений для груза {cargo_id}")
        offers = await ati_client.get_cargo_responses(cargo_id)
        
        if not offers:
            return {
                "error": f"Встречные предложения для груза {cargo_id} не найдены",
                "status": "no_offers",
                "order_id": order_id,
                "cargo_info": {
                    "name": cargo_name,
                    "route": f"{from_city} → {to_city}",
                    "weight": weight,
                    "volume": volume
                }
            }
        
        # Запускаем анализ предложений
        logger.info(f"🤖 Запуск анализа {len(offers)} предложений")
        
        # Добавляем груз в мониторинг если его там нет
        if not offers_monitor.is_running:
            await offers_monitor.start_monitoring()
        
        # Принудительно обрабатываем предложения
        if len(offers) >= 3:  # Минимум 3 предложения для запуска ИИ
            logger.info(f"✅ Найдено {len(offers)} предложений - запускаем ИИ-продажника")
            
            # Создаем объект CargoOffers и добавляем в кэш мониторинга
            from ati_integration.offers_monitor import CargoOffers
            
            cargo_offers = CargoOffers(
                cargo_id=cargo_id,
                cargo_number=cargo.get('Number', ''),
                cargo_name=cargo_name,
                route=f"{from_city} → {to_city}",
                offers=offers,
                external_id=cargo.get('ExternalId', ''),
                created_at=datetime.now(),
                last_check=datetime.now(),
                offers_count=len(offers),
                best_offer_price=min(offer.get("Price", float('inf')) for offer in offers) if offers else 0
            )
            
            # Добавляем в кэш мониторинга
            offers_monitor.monitored_cargos[cargo_id] = cargo_offers
            
            # Вызываем обработку готовых предложений (без аргументов)
            result = await offers_monitor._process_ready_offers()
            
            return {
                "status": "success",
                "message": f"ИИ-продажник запущен для груза {cargo_id}",
                "order_id": order_id,
                "offers_count": len(offers),
                "cargo_info": {
                    "name": cargo_name,
                    "route": f"{from_city} → {to_city}",
                    "weight": weight,
                    "volume": volume
                },
                "processing_result": result
            }
        else:
            return {
                "status": "waiting",
                "message": f"Недостаточно предложений ({len(offers)}/3). Груз добавлен в мониторинг",
                "order_id": order_id,
                "offers_count": len(offers),
                "cargo_info": {
                    "name": cargo_name,
                    "route": f"{from_city} → {to_city}",
                    "weight": weight,
                    "volume": volume
                }
            }
        
    except Exception as e:
        logger.error(f"❌ Ошибка тестирования ИИ-продажника: {e}")
        import traceback
        traceback.print_exc()
        return {
            "error": f"Ошибка тестирования ИИ-продажника: {str(e)}",
            "status": "error"
        }


@app.get("/api/failed-deals/stats")
async def get_failed_deals_stats(days: int = 30):
    """Получение статистики неудачных сделок"""
    try:
        from database.crud import get_failed_deals_stats
        
        stats = await get_failed_deals_stats(days)
        
        logger.info(f"📊 Запрошена статистика неудачных сделок за {days} дней")
        
        return {
            "status": "success",
            "data": stats
        }
        
    except Exception as e:
        logger.error(f"❌ Ошибка получения статистики неудачных сделок: {e}")
        return {
            "status": "error",
            "message": str(e)
        }


def handle_shutdown(signum, frame):
    """Обработка сигналов завершения"""
    logger.info(f"🛑 Получен сигнал {signum}, завершение работы...")
    sys.exit(0)


async def main():
    """Главная функция запуска"""
    
    # Регистрируем обработчики сигналов
    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)
    
    try:
        # Проверяем аргументы командной строки для быстрого тестирования
        import sys
        if len(sys.argv) > 1 and sys.argv[1] == "test-ai-sales":
            # Быстрое тестирование ИИ-продажника
            if len(sys.argv) > 2:
                cargo_id = sys.argv[2]
                logger.info(f"🧪 Запуск тестирования ИИ-продажника для груза {cargo_id}")
                
                # Инициализируем базу данных
                await init_database()
                
                # Запускаем тест
                await test_ai_sales_quick(cargo_id)
                return
            else:
                logger.error("❌ Укажите cargo_id: python main.py test-ai-sales <cargo_id>")
                return
        
        # Запуск FastAPI сервера
        config = {
            "app": "main:app",
            "host": "0.0.0.0",
            "port": 8000,
            "reload": settings.debug,
            "log_level": settings.log_level.lower()
        }
        
        logger.info("🌐 Запуск FastAPI сервера...")
        run(**config)
        
    except KeyboardInterrupt:
        logger.info("🛑 Получен сигнал завершения")
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {str(e)}")
        raise
    finally:
        logger.info("👋 Завершение работы ИИ-диспетчера")


async def test_ai_sales_quick(cargo_id: str):
    """Быстрое тестирование ИИ-продажника для груза"""
    try:
        from database.crud import create_order, get_order_by_ati_cargo_id
        from ati_integration.ati_client_v2 import ATIClientV2
        from ati_integration.offers_monitor import CargoOffers
        from datetime import datetime
        
        logger.info(f"🔍 Тестирование ИИ-продажника для груза {cargo_id}")
        
        # Создаем экземпляр клиента
        ati_client = ATIClientV2()
        
        # Получаем данные о грузе
        cargo = await ati_client.get_cargo_by_id(cargo_id)
        if not cargo:
            logger.error(f"❌ Груз {cargo_id} не найден")
            return
        
        # Извлекаем данные
        cargo_name = cargo.get('Cargo', {}).get('CargoType', 'Тестовый груз')
        weight = cargo.get('Cargo', {}).get('Weight', 0)
        volume = cargo.get('Cargo', {}).get('Volume', 0)
        
        # Получаем города
        from_city = "Неизвестно"
        to_city = "Неизвестно"
        
        if cargo.get('Loading', {}).get('CityId'):
            city_data = await ati_client.get_city_by_id(cargo['Loading']['CityId'])
            if city_data:
                from_city = city_data.get('Name', from_city)
                
        if cargo.get('Unloading', {}).get('CityId'):
            city_data = await ati_client.get_city_by_id(cargo['Unloading']['CityId'])
            if city_data:
                to_city = city_data.get('Name', to_city)
        
        # Проверяем существующий заказ
        existing_order = await get_order_by_ati_cargo_id(cargo_id)
        
        if not existing_order:
            # Создаем тестовый заказ
            order_data = {
                'ati_cargo_id': cargo_id,
                'contact_phone': '+79000000000',
                'contact_name': 'Тестовый клиент',
                'cargo_type': cargo_name,
                'from_city': from_city,
                'to_city': to_city,
                'weight': weight,
                'volume': volume,
                'loading_date': datetime.now(),
                'status': 'searching_offers',
                'owner_id': 408001372,  # Telegram ID владельца
                'created_at': datetime.now()
            }
            
            new_order = await create_order(order_data)
            logger.info(f"✅ Создан тестовый заказ: {new_order.id}")
        
        # Получаем предложения
        offers = await ati_client.get_cargo_responses(cargo_id)
        if not offers:
            logger.error(f"❌ Нет предложений для груза {cargo_id}")
            return
        
        if len(offers) < 3:
            logger.warning(f"⚠️ Недостаточно предложений ({len(offers)}/3)")
            return
        
        # Запускаем мониторинг
        if not offers_monitor.is_running:
            await offers_monitor.start_monitoring()
        
        # Создаем объект для обработки
        cargo_offers = CargoOffers(
            cargo_id=cargo_id,
            cargo_number=cargo.get('Number', ''),
            cargo_name=cargo_name,
            route=f"{from_city} → {to_city}",
            offers=offers,
            external_id=cargo.get('ExternalId', ''),
            created_at=datetime.now(),
            last_check=datetime.now(),
            offers_count=len(offers),
            best_offer_price=min(offer.get("Price", float('inf')) for offer in offers)
        )
        
        # Добавляем в кэш и обрабатываем
        offers_monitor.monitored_cargos[cargo_id] = cargo_offers
        
        # Запускаем обработку
        await offers_monitor._process_ready_offers()
        
        logger.info(f"✅ Тестирование завершено для груза {cargo_id}")
        
    except Exception as e:
        logger.error(f"❌ Ошибка тестирования: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Проверяем наличие необходимых токенов
    if not settings.ati_api_token or settings.ati_api_token == "your_ati_api_token_here":
        logger.error("❌ Не указан ATI_API_TOKEN в конфигурации")
        logger.info("📝 Скопируйте config.env.example в .env и заполните токены")
        sys.exit(1)
    
    if not settings.telegram_bot_token or settings.telegram_bot_token == "your_telegram_bot_token_here":
        logger.error("❌ Не указан TELEGRAM_BOT_TOKEN в конфигурации")
        logger.info("📝 Скопируйте config.env.example в .env и заполните токены")
        sys.exit(1)
    
    if not settings.openai_api_key or settings.openai_api_key == "your_openai_api_key_here":
        logger.error("❌ Не указан OPENAI_API_KEY в конфигурации")
        logger.info("📝 Скопируйте config.env.example в .env и заполните токены")
        sys.exit(1)
    
    # Запуск приложения
    asyncio.run(main()) 