"""
Модели базы данных для ИИ-диспетчера
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()


class Client(Base):
    """Модель клиента"""
    __tablename__ = "clients"
    
    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(Integer, unique=True, index=True)
    username = Column(String(100), nullable=True)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    phone = Column(String(20), nullable=True)
    email = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # Связи
    orders = relationship("Order", back_populates="client")
    
    def __repr__(self):
        return f"<Client {self.telegram_id}: {self.first_name}>"


class Order(Base):
    """Модель заказа"""
    __tablename__ = "orders"
    
    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"))
    
    # Информация о маршруте
    from_city = Column(String(100), nullable=False)
    to_city = Column(String(100), nullable=False)
    
    # Информация о грузе
    cargo_description = Column(Text)
    weight = Column(Float)  # в кг
    volume = Column(Float)  # в м³
    cargo_type = Column(String(100))
    
    # Новые поля для улучшенной функциональности
    body_type = Column(String(50))  # тип кузова
    load_type = Column(String(50))  # ftl/dont-care
    loading_method = Column(String(50))  # способ загрузки
    unloading_method = Column(String(50))  # способ разгрузки
    pack_type = Column(String(50))  # тип упаковки
    contact_name = Column(String(100))  # имя контакта
    contact_phone = Column(String(20))  # телефон контакта
    
    # Цены
    client_price = Column(Integer)  # цена для клиента
    carrier_price = Column(Integer)  # цена для перевозчика
    our_commission = Column(Integer)  # наша комиссия
    
    # Даты
    loading_date = Column(DateTime)
    delivery_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Статус заказа
    status = Column(String(50), default="new")  # new, in_progress, completed, cancelled
    
    # Контакты
    loading_contact = Column(JSON)  # {"name": "", "phone": "", "address": ""}
    delivery_contact = Column(JSON)
    
    # Связанные данные
    ati_cargo_id = Column(String(100), nullable=True)  # ID груза в ATI.SU
    ati_order_id = Column(String(100), nullable=True)  # ID заказа в ATI.SU
    carrier_info = Column(JSON, nullable=True)  # информация о перевозчике
    owner_id = Column(Integer, nullable=True)  # Telegram ID владельца (для уведомлений)
    
    # Связи
    client = relationship("Client", back_populates="orders")
    
    def __repr__(self):
        return f"<Order {self.id}: {self.from_city} → {self.to_city}>"


# УДАЛЕНЫ МОДЕЛИ MonitoredCargo и ProcessedCargo
# Они использовались для старой логики "холодных продаж" - мониторинга чужих грузов на ATI.SU
# Новая логика: работаем только с заказами наших клиентов (модель Order)


class Conversation(Base):
    """Модель для хранения переписки с клиентами"""
    __tablename__ = "conversations"
    
    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"))
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)
    
    # Сообщение
    sender_type = Column(String(20))  # "client", "bot", "human"
    message_text = Column(Text)
    message_type = Column(String(50), default="text")  # text, image, document
    
    # Метаданные
    telegram_message_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Связи
    client = relationship("Client")
    order = relationship("Order")
    
    def __repr__(self):
        return f"<Conversation {self.id}: {self.sender_type}>"


class CarrierContact(Base):
    """Модель для хранения контактов перевозчиков"""
    __tablename__ = "carrier_contacts"
    
    id = Column(Integer, primary_key=True, index=True)
    ati_company_id = Column(String(100), unique=True)
    
    # Информация о компании
    company_name = Column(String(200))
    contact_person = Column(String(100))
    phone = Column(String(20))
    email = Column(String(100))
    
    # Рейтинг и статистика
    ati_rating = Column(Float)
    completed_orders = Column(Integer, default=0)
    our_rating = Column(Float, nullable=True)  # наша внутренняя оценка
    
    # География работы
    working_regions = Column(JSON)  # список регионов
    vehicle_types = Column(JSON)  # типы транспорта
    
    # Статус сотрудничества
    is_blacklisted = Column(Boolean, default=False)
    notes = Column(Text, nullable=True)
    
    # Даты
    first_contact = Column(DateTime, default=datetime.utcnow)
    last_contact = Column(DateTime, nullable=True)
    
    def __repr__(self):
        return f"<CarrierContact {self.company_name}>"


class SystemStats(Base):
    """Модель для хранения статистики системы"""
    __tablename__ = "system_stats"
    
    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime, default=datetime.utcnow)
    
    # Статистика мониторинга
    cargos_monitored = Column(Integer, default=0)
    cargos_processed = Column(Integer, default=0)
    offers_sent = Column(Integer, default=0)
    
    # Статистика конверсии
    clients_contacted = Column(Integer, default=0)
    orders_created = Column(Integer, default=0)
    orders_completed = Column(Integer, default=0)
    
    # Финансовая статистика
    total_revenue = Column(Integer, default=0)  # общий доход
    total_commission = Column(Integer, default=0)  # наша комиссия
    
    def __repr__(self):
        return f"<SystemStats {self.date.date()}>"


class Commission(Base):
    """Модель комиссии"""
    __tablename__ = "commissions"
    
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"))
    
    # Финансовые данные
    carrier_price = Column(Integer)  # цена перевозчика
    commission_percent = Column(Float)  # процент комиссии
    commission_amount = Column(Integer)  # сумма комиссии
    total_price = Column(Integer)  # итоговая цена для клиента
    
    # Статус
    status = Column(String(50), default="pending")  # pending, paid, cancelled
    created_at = Column(DateTime, default=datetime.utcnow)
    paid_at = Column(DateTime, nullable=True)
    
    # Связи
    order = relationship("Order")
    
    def __repr__(self):
        return f"<Commission {self.id}: {self.total_price}₽>"


class CarrierOffer(Base):
    """Таблица для хранения предложений перевозчиков с ATI.SU"""
    __tablename__ = "carrier_offers"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Связь с заказом
    order_id = Column(String, index=True)  # ID заказа в нашей системе
    ati_cargo_id = Column(String, index=True)  # ID груза на ATI.SU
    
    # Маршрут
    from_city = Column(String, nullable=False)
    to_city = Column(String, nullable=False)
    from_city_id = Column(Integer)  # ID города на ATI
    to_city_id = Column(Integer)    # ID города на ATI
    distance_km = Column(Integer)   # Расстояние в км
    
    # Данные груза
    cargo_type = Column(String)
    weight_kg = Column(Float)
    volume_m3 = Column(Float)
    
    # Данные перевозчика
    carrier_company_name = Column(String)
    carrier_contact_id = Column(Integer)  # ID контакта на ATI
    carrier_phone = Column(String)
    carrier_rating = Column(Float)        # Рейтинг перевозчика
    carrier_reviews_count = Column(Integer)
    
    # Финансовые данные
    carrier_price_rub = Column(Float, nullable=False)  # Цена перевозчика
    client_price_rub = Column(Float, nullable=False)   # Цена клиенту (с наценкой)
    markup_percent = Column(Float, default=40.0)       # Процент наценки
    profit_rub = Column(Float)                         # Прибыль
    
    # Условия перевозки
    body_type = Column(String)           # Тип кузова
    loading_method = Column(String)      # Способ загрузки
    unloading_method = Column(String)    # Способ разгрузки
    payment_type = Column(String)        # Тип оплаты (наличные/безнал)
    
    # Временные рамки
    loading_date_from = Column(DateTime)
    loading_date_to = Column(DateTime)
    delivery_days = Column(Integer)      # Срок доставки в днях
    
    # Статус предложения
    status = Column(String, default="received")  # received, sent_to_client, accepted, rejected
    is_selected = Column(Boolean, default=False) # Выбрано ли это предложение
    
    # Метаданные
    received_at = Column(DateTime, default=datetime.utcnow)  # Когда получено предложение
    sent_to_client_at = Column(DateTime)                    # Когда отправлено клиенту
    client_response_at = Column(DateTime)                   # Когда клиент ответил
    
    # Дополнительная информация
    notes = Column(Text)                 # Заметки
    ati_response_data = Column(Text)     # Полные данные ответа от ATI (JSON)
    
    def __repr__(self):
        return f"<CarrierOffer {self.id}: {self.from_city}→{self.to_city}, {self.carrier_price_rub}₽>"


# Алиас для совместимости
Carrier = CarrierContact 


class FailedDeal(Base):
    """Модель для хранения неудачных сделок"""
    __tablename__ = "failed_deals"
    
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"))
    ati_cargo_id = Column(String(100), nullable=True)
    
    # Информация о сделке
    cargo_type = Column(String(100))
    from_city = Column(String(100))
    to_city = Column(String(100))
    weight = Column(Float)
    volume = Column(Float)
    
    # Финансовые данные предложения
    carrier_price = Column(Integer)  # цена перевозчика
    client_price = Column(Integer)   # предложенная цена клиенту
    potential_profit = Column(Integer)  # потенциальная прибыль
    
    # Информация о перевозчике
    carrier_company = Column(String(200))
    carrier_rating = Column(Float)
    
    # Причина неудачи
    failure_reason = Column(String(50))  # client_rejected, no_response, ai_error, etc.
    failure_details = Column(Text)  # подробности
    
    # Данные клиента
    client_phone = Column(String(20))
    client_name = Column(String(100))
    
    # Временные метки
    offer_sent_at = Column(DateTime)  # когда отправили предложение
    failed_at = Column(DateTime, default=datetime.utcnow)  # когда признали неудачей
    
    # Связи
    order = relationship("Order")
    
    def __repr__(self):
        return f"<FailedDeal {self.id}: {self.from_city} → {self.to_city}, -{self.potential_profit}₽>"


class MonitoringSession(Base):
    """Временное хранение данных мониторинга и продаж"""
    __tablename__ = "monitoring_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    ati_cargo_id = Column(String(100), unique=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)
    
    # Данные груза
    cargo_data = Column(JSON)  # Полные данные груза с ATI
    
    # Данные предложений
    offers_data = Column(JSON)  # Все предложения от перевозчиков
    best_offer_data = Column(JSON)  # Выбранное лучшее предложение
    pricing_data = Column(JSON)  # Расчет цен и наценки
    
    # Данные ИИ-продажи
    ai_offer_message = Column(Text, nullable=True)  # Сгенерированное ИИ предложение
    
    # Клиентские данные
    client_telegram_id = Column(Integer, nullable=True)  # Telegram ID клиента для связи
    first_offer_sent_at = Column(DateTime, nullable=True)  # Когда отправили первое предложение
    client_response = Column(Text, nullable=True)  # Ответ клиента на предложение  
    deal_closed_at = Column(DateTime, nullable=True)  # Когда закрыли сделку
    human_intervention_requested_at = Column(DateTime, nullable=True)  # Когда потребовалось вмешательство
    
    # НОВЫЕ ПОЛЯ ДЛЯ ГИБРИДНОГО УПРАВЛЕНИЯ
    dialog_mode = Column(String(50), default="auto")  # auto, manual, mixed
    manual_takeover_at = Column(DateTime, nullable=True)  # Когда владелец взял управление
    owner_handling = Column(Boolean, default=False)  # Обрабатывает ли владелец сейчас
    auto_switch_reason = Column(String(100), nullable=True)  # Причина автопереключения
    owner_last_seen_at = Column(DateTime, nullable=True)  # Когда владелец последний раз смотрел диалог
    pending_owner_response = Column(Boolean, default=False)  # Ждет ли клиент ответа от владельца
    ai_analysis_data = Column(JSON, nullable=True)  # Последний анализ ИИ для владельца
    switch_triggers = Column(JSON, nullable=True)  # Триггеры для автопереключения
    
    # ПОЛЯ ДЛЯ УМНОГО ИИ-ПРОДАЖНИКА (LAER + Re-CAP)
    objection_attempts = Column(Integer, default=0)  # Количество попыток работы с возражениями
    last_price_discount = Column(Float, default=0.0)  # Последняя предложенная скидка (%)
    objection_type = Column(String(50), nullable=True)  # Тип возражения (past_cheaper, competitor_cheaper, budget_cap)
    price_negotiation_data = Column(JSON, nullable=True)  # JSON данные о ходе переговоров по цене
    margin_threshold_reached = Column(Boolean, default=False)  # Достигнут ли минимальный порог маржи
    sales_technique_used = Column(String(50), default="standard")  # Используемая техника продаж (standard, laer_recap)
    
    # Статус процесса
    status = Column(String(50), default="monitoring")  # monitoring, ready_for_sale, selling, completed, failed
    offers_count = Column(Integer, default=0)
    min_offers_threshold = Column(Integer, default=3)
    
    # Временные метки
    monitoring_started_at = Column(DateTime, default=datetime.utcnow)
    sales_started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Результат
    sale_result = Column(String(50), nullable=True)  # success, failed, timeout
    failure_reason = Column(String(100), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Связи
    order = relationship("Order")
    
    def __repr__(self):
        return f"<MonitoringSession {self.id}: {self.ati_cargo_id} ({self.status})>"