"""
Упрощенная система лендингов без чата - переход сразу в Telegram
"""
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from utils.config import settings
from utils.logger import get_logger

logger = get_logger("LANDING")


class SimpleLandingSystem:
    """Упрощенная система лендингов без чата - переход сразу в Telegram"""
    
    def __init__(self, app: FastAPI):
        self.app = app
        
        # Добавляем статические файлы
        app.mount("/static", StaticFiles(directory="static"), name="static")
        
        # Регистрируем маршруты
        self._register_routes()
    
    def _register_routes(self):
        """Регистрация маршрутов лендинга"""
        
        @self.app.get("/", response_class=HTMLResponse)
        async def main_landing(request: Request):
            """Главная страница лендинга - переход в Telegram"""
            
            html_content = f"""
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ИИ-Диспетчер - Грузоперевозки по России 2025</title>
    <!-- Favicon -->
    <link rel="icon" href="/static/favicon.svg" type="image/svg+xml">
    <link rel="alternate icon" href="/static/favicon.ico" type="image/x-icon">
    <link rel="apple-touch-icon" href="/static/apple-touch-icon.png">
    <link rel="icon"              href="/static/favicon-32x32.png" sizes="32x32">
    <link rel="icon"              href="/static/favicon-16x16.png" sizes="16x16">
    <link href="/static/fontawesome/all.min.css" rel="stylesheet">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        
        body {{ 
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, system-ui, sans-serif; 
            line-height: 1.6; 
            overflow-x: hidden;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }}
        
        /* Современный градиентный фон */
        .hero {{ 
            min-height: 100vh;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            position: relative;
            display: flex;
            align-items: center;
            justify-content: center;
            text-align: center;
            color: white;
            overflow: hidden;
        }}
        
        .hero::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: url('data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 1000"><polygon fill="rgba(255,255,255,0.05)" points="0,1000 1000,800 1000,1000"/></svg>');
            z-index: 1;
        }}
        
        .hero-content {{ 
            position: relative; 
            z-index: 2; 
            max-width: 800px; 
            padding: 0 2rem;
            animation: fadeInUp 1s ease-out;
        }}
        
        @keyframes fadeInUp {{
            from {{ opacity: 0; transform: translateY(50px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
        
        .hero h1 {{ 
            font-size: clamp(3rem, 8vw, 6rem); 
            font-weight: 800; 
            margin-bottom: 1rem;
            background: linear-gradient(45deg, #fff, #e8f4fd);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            text-shadow: 0 4px 8px rgba(0,0,0,0.3);
        }}
        
        .hero-subtitle {{ 
            font-size: 1.5rem; 
            margin-bottom: 2rem; 
            opacity: 0.9;
            font-weight: 300;
        }}
        
        .hero-description {{ 
            font-size: 1.1rem; 
            margin-bottom: 3rem; 
            opacity: 0.8;
            max-width: 600px;
            margin-left: auto;
            margin-right: auto;
        }}
        
        /* Современные кнопки */
        .btn-group {{ display: flex; gap: 1rem; justify-content: center; flex-wrap: wrap; }}
        
        .btn {{ 
            padding: 1rem 2rem; 
            border: none; 
            border-radius: 12px; 
            font-size: 1.1rem; 
            font-weight: 600; 
            cursor: pointer; 
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            text-decoration: none; 
            display: inline-flex; 
            align-items: center; 
            gap: 0.5rem;
            position: relative;
            overflow: hidden;
        }}
        
        .btn::before {{
            content: '';
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 100%;
            background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
            transition: left 0.5s;
        }}
        
        .btn:hover::before {{ left: 100%; }}
        
        .btn-primary {{ 
            background: linear-gradient(135deg, #ff6b6b, #ff8e8e);
            color: white;
            box-shadow: 0 8px 25px rgba(255, 107, 107, 0.3);
        }}
        
        .btn-primary:hover {{ 
            transform: translateY(-2px);
            box-shadow: 0 12px 35px rgba(255, 107, 107, 0.4);
        }}
        
        .btn-secondary {{ 
            background: rgba(255, 255, 255, 0.15);
            color: white;
            border: 2px solid rgba(255, 255, 255, 0.3);
            backdrop-filter: blur(10px);
        }}
        
        .btn-secondary:hover {{ 
            background: rgba(255, 255, 255, 0.25);
            transform: translateY(-2px);
        }}
        
        /* Секция преимуществ */
        .benefits {{ 
            padding: 6rem 2rem; 
            background: #ffffff;
            position: relative;
        }}
        
        .container {{ max-width: 1200px; margin: 0 auto; }}
        
        .section-title {{ 
            text-align: center; 
            font-size: 3rem; 
            font-weight: 700; 
            margin-bottom: 3rem;
            background: linear-gradient(135deg, #667eea, #764ba2);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }}
        
        .benefits-grid {{ 
            display: grid; 
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr)); 
            gap: 2rem; 
            margin-top: 3rem;
        }}
        
        .benefit-card {{ 
            background: #ffffff;
            padding: 2.5rem;
            border-radius: 20px;
            text-align: center;
            transition: all 0.3s ease;
            border: 1px solid #e2e8f0;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
        }}
        
        .benefit-card:hover {{ 
            transform: translateY(-8px);
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
            border-color: #667eea;
        }}
        
        .benefit-icon {{ 
            width: 80px; 
            height: 80px; 
            background: linear-gradient(135deg, #667eea, #764ba2);
            border-radius: 50%; 
            display: flex; 
            align-items: center; 
            justify-content: center; 
            margin: 0 auto 1.5rem; 
            font-size: 2rem; 
            color: white;
        }}
        
        .benefit-card h3 {{ 
            font-size: 1.5rem; 
            font-weight: 700; 
            margin-bottom: 1rem;
            color: #2d3748;
        }}
        
        .benefit-card p {{ 
            color: #4a5568; 
            line-height: 1.6;
        }}
        
        /* Статистика */
        .stats {{ 
            padding: 4rem 2rem; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }}
        
        .stats-grid {{ 
            display: grid; 
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); 
            gap: 2rem; 
            max-width: 1000px; 
            margin: 0 auto;
        }}
        
        .stat-item {{ 
            text-align: center; 
            padding: 2rem 1rem;
        }}
        
        .stat-number {{ 
            display: block; 
            font-size: 3rem; 
            font-weight: 800; 
            margin-bottom: 0.5rem;
            color: #fff;
        }}
        
        .stat-label {{ 
            font-size: 1.1rem; 
            opacity: 0.9;
        }}
        
        /* CTA секция */
        .cta {{ 
            padding: 6rem 2rem; 
            background: #f7fafc;
            text-align: center;
        }}
        
        .cta-content {{ 
            max-width: 600px; 
            margin: 0 auto;
        }}
        
        .cta h2 {{ 
            font-size: 2.5rem; 
            font-weight: 700; 
            margin-bottom: 1.5rem;
            color: #2d3748;
        }}
        
        .cta p {{ 
            font-size: 1.2rem; 
            color: #4a5568; 
            margin-bottom: 2rem;
        }}
        
        .contact-info {{ 
            display: flex; 
            justify-content: center; 
            gap: 2rem; 
            margin-top: 2rem;
            flex-wrap: wrap;
        }}
        
        .contact-item {{ 
            display: flex; 
            align-items: center; 
            gap: 0.5rem;
            padding: 1rem 1.5rem;
            background: #f7fafc;
            border-radius: 12px;
            color: #2d3748;
            text-decoration: none;
            transition: all 0.3s ease;
        }}
        
        .contact-item:hover {{ 
            background: #e2e8f0;
            transform: translateY(-2px);
        }}
        
        /* Telegram кнопка в углу */
        .telegram-float {{ 
            position: fixed; 
            bottom: 2rem; 
            right: 2rem; 
            width: 70px; 
            height: 70px; 
            background: linear-gradient(135deg, #0088cc, #0066aa);
            color: white; 
            border: none; 
            border-radius: 50%; 
            cursor: pointer; 
            font-size: 1.5rem; 
            z-index: 999;
            box-shadow: 0 8px 25px rgba(0, 136, 204, 0.3);
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            text-decoration: none;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        
        .telegram-float:hover {{ 
            transform: scale(1.1);
            box-shadow: 0 12px 35px rgba(0, 136, 204, 0.4);
        }}
        
        /* Адаптивность */
        @media (max-width: 768px) {{
            .hero h1 {{ font-size: 3rem; }}
            .section-title {{ font-size: 2rem; }}
            .benefits-grid {{ grid-template-columns: 1fr; }}
            .stats-grid {{ grid-template-columns: repeat(2, 1fr); }}
            .contact-info {{ flex-direction: column; align-items: center; }}
            .btn-group {{ flex-direction: column; align-items: center; }}
        }}
        
        /* Плавная прокрутка */
        html {{ scroll-behavior: smooth; }}
        
        /* Кастомный скроллбар */
        ::-webkit-scrollbar {{ width: 8px; }}
        ::-webkit-scrollbar-track {{ background: #f1f1f1; }}
        ::-webkit-scrollbar-thumb {{ 
            background: linear-gradient(135deg, #667eea, #764ba2);
            border-radius: 4px;
        }}
        ::-webkit-scrollbar-thumb:hover {{ background: #555; }}
    </style>
</head>
<body>
    <!-- Hero секция -->
    <section class="hero">
        <div class="hero-content">
            <h1>🚛 ИИ-Диспетчер</h1>
            <p class="hero-subtitle">Грузоперевозки нового поколения</p>
            <p class="hero-description">
                Революционная система с искусственным интеллектом для организации грузоперевозок. 
                Мы находим лучших перевозчиков, договариваемся о цене и контролируем доставку 24/7.
            </p>
            <div class="btn-group">
                <a href="https://t.me/ai_dispatcherBot" class="btn btn-primary">
                    <i class="fab fa-telegram"></i>
                    Заказать через ИИ
                </a>
                <a href="javascript:void(0)" onclick="scrollToSection('benefits')" class="btn btn-secondary">
                    <i class="fas fa-arrow-down"></i>
                    Узнать больше
                </a>
            </div>
        </div>
    </section>
    
    <!-- Статистика -->
    <section class="stats">
        <div class="container">
            <h2 style="text-align: center; font-size: 3rem; font-weight: 700; margin-bottom: 3rem; color: white; text-shadow: 0 2px 4px rgba(0,0,0,0.3);">Наши результаты</h2>
            <div class="stats-grid">
                <div class="stat-item">
                    <span class="stat-number">1247</span>
                    <span class="stat-label">Доставленных грузов</span>
                </div>
                <div class="stat-item">
                    <span class="stat-number">99.8%</span>
                    <span class="stat-label">Успешных доставок</span>
                </div>
                <div class="stat-item">
                    <span class="stat-number">24/7</span>
                    <span class="stat-label">Работа ИИ-диспетчера</span>
                </div>
                <div class="stat-item">
                    <span class="stat-number">5 мин</span>
                    <span class="stat-label">Время расчета</span>
                </div>
            </div>
        </div>
    </section>
    
    <!-- Преимущества -->
    <section class="benefits" id="benefits">
        <div class="container">
            <h2 class="section-title">Почему выбирают нас</h2>
            <div class="benefits-grid">
                <div class="benefit-card">
                    <div class="benefit-icon"><i class="fas fa-robot"></i></div>
                    <h3>ИИ-диспетчер 24/7</h3>
                    <p>Наш искусственный интеллект непрерывно мониторит рынок перевозок, находит лучшие предложения и общается с клиентами как живой человек.</p>
                </div>
                <div class="benefit-card">
                    <div class="benefit-icon"><i class="fas fa-shield-alt"></i></div>
                    <h3>Проверенные перевозчики</h3>
                    <p>Работаем только с надежными перевозчиками. Все компании с рейтингом и проверенной репутацией.</p>
                </div>
                <div class="benefit-card">
                    <div class="benefit-icon"><i class="fas fa-chart-line"></i></div>
                    <h3>Экономия до 30%</h3>
                    <p>Благодаря ИИ-анализу рынка находим оптимальные цены. Прямые договоры с перевозчиками без посредников. Получите лучшую стоимость на рынке!</p>
                </div>
                <div class="benefit-card">
                    <div class="benefit-icon"><i class="fas fa-map-marked-alt"></i></div>
                    <h3>Вся Россия</h3>
                    <p>Работаем по всей территории РФ. От Калининграда до Владивостока, от Мурманска до Сочи.</p>
                </div>
                <div class="benefit-card">
                    <div class="benefit-icon"><i class="fas fa-mobile-alt"></i></div>
                    <h3>Связь через Telegram</h3>
                    <p>Удобное общение через Telegram бота. Получайте обновления статуса и связывайтесь с диспетчером в любое время.</p>
                </div>
                <div class="benefit-card">
                    <div class="benefit-icon"><i class="fas fa-clock"></i></div>
                    <h3>Быстрое оформление</h3>
                    <p>Оформление заказа за 5 минут. ИИ автоматически подберет оптимальный маршрут.</p>
                </div>
            </div>
        </div>
    </section>
    
    <!-- CTA -->
    <section class="cta">
        <div class="container">
            <div class="cta-content">
                <h2>Готовы доверить груз ИИ?</h2>
                <p>Оставьте заявку прямо сейчас и получите расчет стоимости за 2 минуты</p>
                <div class="contact-info">
                    <a href="https://t.me/ai_dispatcherBot" class="contact-item">
                        <i class="fab fa-telegram"></i>
                        ai_dispatcherBot
                    </a>
                </div>
            </div>
        </div>
    </section>
    
    <!-- Telegram кнопка -->
    <a href="https://t.me/ai_dispatcherBot" class="telegram-float">
        <i class="fab fa-telegram"></i>
    </a>
    
    <script>
        // Функция плавного скролла
        function scrollToSection(sectionId) {{
            const element = document.getElementById(sectionId);
            if (element) {{
                element.scrollIntoView({{ behavior: 'smooth' }});
            }}
        }}
        
        // Плавные анимации при прокрутке
        const observerOptions = {{
            threshold: 0.1,
            rootMargin: '0px 0px -50px 0px'
        }};
        
        const observer = new IntersectionObserver((entries) => {{
            entries.forEach(entry => {{
                if (entry.isIntersecting) {{
                    entry.target.style.animation = 'fadeInUp 0.6s ease-out';
                }}
            }});
        }}, observerOptions);
        
        // Наблюдаем за элементами для анимации
        document.addEventListener('DOMContentLoaded', () => {{
            const animatedElements = document.querySelectorAll('.benefit-card, .stat-item');
            animatedElements.forEach(el => observer.observe(el));
        }});
    </script>
</body>
</html>
            """
            
            return HTMLResponse(content=html_content)


def setup_simple_landing(app):
    """Настройка упрощенной системы лендинга без чата"""
    return SimpleLandingSystem(app) 