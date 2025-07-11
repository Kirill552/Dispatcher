"""
Инициализация и настройка базы данных
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from database.models import Base
from utils.config import settings
from utils.logger import db_logger as logger


# Создание движка базы данных
if settings.database_url.startswith("sqlite"):
    # Для SQLite нужна специальная строка подключения для async
    database_url = settings.database_url.replace("sqlite:///", "sqlite+aiosqlite:///")
else:
    database_url = settings.database_url

# Асинхронный движок
async_engine = create_async_engine(
    database_url,
    echo=settings.database_echo,
    future=True
)

# Фабрика сессий
AsyncSessionLocal = sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=True
)


async def init_database():
    """Инициализация базы данных и создание таблиц"""
    
    try:
        logger.info("📊 Инициализация базы данных...")
        
        # Создание всех таблиц
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        logger.info("✅ База данных инициализирована успешно")
        
    except Exception as e:
        logger.error(f"❌ Ошибка инициализации базы данных: {str(e)}")
        raise


async def get_db_session():
    """Получить сессию базы данных"""
    
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Ошибка в сессии БД: {str(e)}")
            raise
        finally:
            await session.close()


async def close_database():
    """Закрытие соединения с базой данных"""
    
    try:
        await async_engine.dispose()
        logger.info("✅ Соединение с базой данных закрыто")
    except Exception as e:
        logger.error(f"❌ Ошибка закрытия БД: {str(e)}") 