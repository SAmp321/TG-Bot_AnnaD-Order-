В разработке

# TG-Bot_AnnaD-Order-Public

🤖 Telegram бот для продажи курсов и проведения трансляций | Многоуровневая система продуктов

## 📋 Описание проекта

Многофункциональный Telegram бот для продажи различных цифровых продуктов а также проведения платных прямых трансляций. Бот включает систему промокодов и напоминаний.

## ✨ Основные функции

- **🎯 Продажа различных продуктов
- **📹 Прямые трансляции** - платный доступ к live-трансляциям
- **🎁 Система промокодов** - скидки и специальные предложения
- **⏰ Напоминания** - автоматические уведомления пользователям
- **👨‍💼 Админ-панель** - полное управление контентом и пользователями
- **💾 База данных** - хранение всех данных на базе aiosqlite 

## 🛠 Технологический стек

- **Python 3.8+**
- **Aiogram 3.20.0** 
- **SQLite3**
- **aiosqlite 0.21.0** 
- **SQLAlchemy 2.0.41** 
- **APScheduler 3.11.0** 
- **YooKassa 3.5.0** 
- **Redis 6.2.0** 

## 📦 Зависимости проекта

```txt
aiofiles==24.1.0
aiogram==3.20.0.post0
aiohappyeyeballs==2.6.1
aiohttp==3.11.18
aiosignal==1.3.2
aiosqlite==0.21.0
alembic==1.16.2
annotated-types==0.7.0
APScheduler==3.11.0
attrs==25.3.0
certifi==2025.6.15
charset-normalizer==3.4.2
colorama==0.4.6
Deprecated==1.2.18
distro==1.9.0
frozenlist==1.7.0
greenlet==3.2.3
idna==3.10
loguru==0.7.3
magic-filter==1.0.12
Mako==1.3.10
MarkupSafe==3.0.2
multidict==6.6.0
netaddr==1.3.0
propcache==0.3.2
pydantic==2.11.7
pydantic_core==2.33.2
pydantic-settings==2.10.1
python-dotenv==1.1.1
redis==6.2.0
requests==2.32.4
SQLAlchemy==2.0.41
typing_extensions==4.14.0
typing-inspection==0.4.1
tzdata==2025.2
tzlocal==5.3.1
urllib3==2.5.0
uuid==1.30
win32_setctime==1.2.0
wrapt==1.17.2
yarl==1.20.1
yookassa==3.5.0
```
```txt
## 📦 Структура проекта
TG-Bot_AnnaD-Order-Public/
├── run.py # Основной файл запуска бота (мозг проекта)
├── scheduler.py # Система отправки напоминаний через время
├── config.py # Конфигурационные параметры
├── requirements.txt # Зависимости проекта
├── .env.example # Пример файла окружения
├── database/ # Главная база данных проекта
│ ├── init_db.py # Инициализация базы данных
│ ├── migrate_db.py # Миграции базы данных
│ └── models.py # Модели данных
├── reg/ # Хранит ID всех видео, аудио, фото и текста для продажи
├── handlers/ # Обработчики (handlers)
│ ├── init.py
│ ├── admin_handlers.py # Админ команды и управление
│ ├── body_handlers.py # Обработка продуктов категории "Тело"
│ ├── rela_handlers.py # Обработка продуктов категории "Отношения"
│ ├── sex_handlers.py # Обработка продуктов категории "Секс"
│ ├── want_talk_handlers.py # Обработка продуктов "Хочу говорить"
│ ├── stream_handlers.py # Система платных трансляций
│ └── promokode_handlers.py # Система промокодов для покупки
├── keyboards/ # Все кейборды и немного сортировки
│ ├── init.py
│ ├── keyboards_admin.py # Клавиатуры для админ-панели
│ ├── keyboards_main.py # Основные клавиатуры
│ └── keyboards_shop.py # Клавиатуры для магазина
├── utils/ # Вспомогательные утилиты
│ ├── init.py
│ ├── states.py # Состояния FSM
│ └── helpers.py # Вспомогательные функции
└── data/ # Данные курсов и медиафайлы
├── info_baza.db # Основная база данных
├── promokode.db # База промокодов
└── streams.db # База трансляций
'''
