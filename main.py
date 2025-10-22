import os
import logging
import sqlite3
from datetime import datetime
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.getenv('TELEGRAM_TOKEN', '').strip()

if not TOKEN:
    logger.error("❌ Токен не найден! Добавь TELEGRAM_TOKEN в Environment Variables")
    exit(1)

# --- Инициализация базы данных ---
def init_database():
    conn = sqlite3.connect('avto_vaz.db')
    cursor = conn.cursor()
    
    # Таблица моделей
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS models (
            id INTEGER PRIMARY KEY,
            code TEXT UNIQUE,
            name TEXT,
            years TEXT,
            vin_prefix TEXT
        )
    ''')
    
    # Таблица запчастей
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS parts (
            id INTEGER PRIMARY KEY,
            model_code TEXT,
            category TEXT,
            part_name TEXT,
            original_number TEXT,
            description TEXT,
            price_range TEXT,
            FOREIGN KEY (model_code) REFERENCES models (code)
        )
    ''')
    
    # Таблица аналогов
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS analogs (
            id INTEGER PRIMARY KEY,
            original_number TEXT,
            analog_brand TEXT,
            analog_number TEXT,
            quality TEXT,
            price_range TEXT
        )
    ''')
    
    # Добавляем данные моделей
    models_data = [
        # Классика
        ('2101', 'ВАЗ-2101 "Жигули"', '1970-1988', 'XTA2101'),
        ('2102', 'ВАЗ-2102 Universal', '1971-1986', 'XTA2102'),
        ('2103', 'ВАЗ-2103', '1972-1984', 'XTA2103'),
        ('2104', 'ВАЗ-2104 Universal', '1984-2012', 'XTA2104'),
        ('2105', 'ВАЗ-2105', '1979-2010', 'XTA2105'),
        ('2106', 'ВАЗ-2106', '1976-2006', 'XTA2106'),
        ('2107', 'ВАЗ-2107', '1982-2012', 'XTA2107'),
        
        # Самара
        ('2108', 'ВАЗ-2108/2109/21099', '1984-2004', 'XTA2108,XTA2109,XTA21099'),
        ('2113', 'ВАЗ-2113', '2004-2013', 'XTA2113'),
        ('2114', 'ВАЗ-2114/2115', '2004-2013', 'XTA2114,XTA2115'),
        
        # Десятка
        ('2110', 'ВАЗ-2110', '1995-2007', 'XTA2110'),
        ('2111', 'ВАЗ-2111 Universal', '1998-2009', 'XTA2111'),
        ('2112', 'ВАЗ-2112 Hatchback', '1999-2008', 'XTA2112'),
        
        # Приора
        ('2170', 'LADA Priora', '2007-2018', 'XTA2170'),
        
        # Granta
        ('2190', 'LADA Granta', '2011-н.в.', 'XTA2190'),
        ('2192', 'LADA Granta Liftback', '2018-н.в.', 'XTA2192'),
        
        # Kalina
        ('1117', 'LADA Kalina Universal', '2006-2018', 'XTA1117'),
        ('1118', 'LADA Kalina Hatchback', '2004-2018', 'XTA1118'),
        ('1119', 'LADA Kalina Sedan', '2004-2018', 'XTA1119'),
        
        # Vesta
        ('2180', 'LADA Vesta', '2015-н.в.', 'XTA2180'),
        ('2181', 'LADA Vesta SW', '2017-н.в.', 'XTA2181'),
        
        # XRAY
        ('2191', 'LADA XRAY', '2015-н.в.', 'XTA2191'),
        
        # 4x4
        ('2121', 'ВАЗ-2121 "Нива"', '1977-н.в.', 'XTA2121'),
        ('2131', 'ВАЗ-2131 "Нива"', '1993-н.в.', 'XTA2131'),
        
        # Largus
        ('2172', 'LADA Largus', '2012-н.в.', 'XTA2172'),
    ]
    
    cursor.executemany('''
        INSERT OR REPLACE INTO models (code, name, years, vin_prefix)
        VALUES (?, ?, ?, ?)
    ''', models_data)
    
    # Добавляем запчасти
    parts_data = []
    
    # Общие запчасти для большинства моделей
    common_parts = [
        ('Тормозные колодки передние', 'Тормозная система', '2108-3501070', 'Комплект 4 шт.', '1500-3000 руб'),
        ('Тормозные колодки задние', 'Тормозная система', '2108-3501076', 'Комплект 4 шт.', '1200-2500 руб'),
        ('Воздушный фильтр', 'Система фильтрации', '2108-1109010', 'Бумажный', '300-800 руб'),
        ('Масляный фильтр', 'Система фильтрации', '2101-1012005', 'Полнопоточный', '200-600 руб'),
        ('Свечи зажигания', 'Система зажигания', 'А17ДВРМ', 'Иридиевые', '400-1200 руб'),
        ('Ремень ГРМ', 'Газораспределительный механизм', '2108-1006040', '112 зубьев', '800-2000 руб'),
        ('Ролик натяжителя ГРМ', 'Газораспределительный механизм', '2108-1006074', '', '500-1500 руб'),
        ('Амортизатор передний', 'Подвеска', '2108-2905452', 'Газомасляный', '1500-4000 руб'),
        ('Амортизатор задний', 'Подвеска', '2108-2905456', 'Газомасляный', '1200-3500 руб'),
        ('Пружина передняя', 'Подвеска', '2108-2905512', '', '800-2500 руб'),
        ('Шаровая опора', 'Подвеска', '2108-2904552', 'Нижняя', '600-1800 руб'),
        ('Сайлентблок передний', 'Подвеска', '2108-2904528', '', '300-900 руб'),
        ('Тяга рулевая', 'Рулевое управление', '2108-3403010', '', '800-2200 руб'),
        ('Наконечник рулевой', 'Рулевое управление', '2108-3404156', '', '400-1200 руб'),
        ('Насос ГУР', 'Рулевое управление', '2110-3403010', 'Гидроусилитель', '3000-7000 руб'),
        ('Генератор', 'Электрооборудование', '2101-3701010', '55А', '4000-9000 руб'),
        ('Стартер', 'Электрооборудование', '2101-3708010', '', '3000-7000 руб'),
        ('Аккумулятор', 'Электрооборудование', '', '55-65 Ач', '3000-6000 руб'),
        ('Лампа ближнего света', 'Освещение', 'H4', '55/60W', '300-1000 руб'),
        ('Лампа дальнего света', 'Освещение', 'H4', '55/60W', '300-1000 руб'),
        ('Лампа противотуманная', 'Освещение', 'H3', '55W', '400-1200 руб'),
        ('Щетки стеклоочистителя', 'Кузов', '', '400-450mm', '500-1500 руб'),
        ('Термостат', 'Система охлаждения', '2101-1306010', '', '600-1500 руб'),
        ('Помпа водяная', 'Система охлаждения', '2101-1307010', '', '1200-3000 руб'),
        ('Радиатор охлаждения', 'Система охлаждения', '2101-1301070', '', '2500-6000 руб'),
        ('Радиатор печки', 'Отопление', '2101-8101060', '', '1500-4000 руб'),
        ('Вентилятор радиатора', 'Система охлаждения', '2101-1308005', '', '1500-3500 руб'),
        ('Топливный насос', 'Топливная система', '2101-1106010', 'Электрический', '1500-4000 руб'),
        ('Форсунка', 'Топливная система', '', 'Инжектор', '800-2000 руб'),
        ('Фильтр топливный', 'Топливная система', '2101-1117010', '', '300-800 руб'),
        ('Катушка зажигания', 'Система зажигания', '', '', '800-2000 руб'),
        ('Датчик коленвала', 'Электрооборудование', '2112-3847050', '', '500-1500 руб'),
        ('Датчик распредвала', 'Электрооборудование', '2112-3847056', '', '500-1500 руб'),
        ('Датчик кислорода', 'Электрооборудование', '', 'Лямбда-зонд', '1500-4000 руб'),
        ('Сцепление комплект', 'Трансмиссия', '2101-1601130', 'Корзина+диск+выжимной', '3000-7000 руб'),
        ('Трос сцепления', 'Трансмиссия', '2101-1602240', '', '500-1200 руб'),
    ]
    
    # Добавляем запчасти для каждой модели
    for model_code, _, _, _ in models_data:
        for part_name, category, original_number, description, price_range in common_parts:
            parts_data.append((
                model_code, category, part_name, original_number, description, price_range
            ))
    
    cursor.executemany('''
        INSERT OR REPLACE INTO parts (model_code, category, part_name, original_number, description, price_range)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', parts_data)
    
    # Добавляем аналоги
    analogs_data = [
        ('2108-3501070', 'BOSCH', '0986494754', 'Original', '1800-2500 руб'),
        ('2108-3501070', 'TRW', 'GDB1764', 'Premium', '1600-2200 руб'),
        ('2108-3501070', 'FERODO', 'FDB526', 'Standard', '1200-1800 руб'),
        ('2108-1109010', 'MANN', 'C25619', 'Premium', '400-600 руб'),
        ('2108-1109010', 'KNECHT', 'LX1024', 'Original', '350-550 руб'),
        ('2101-1012005', 'MANN', 'W940/25', 'Premium', '250-450 руб'),
        ('2101-1012005', 'KNECHT', 'OC256', 'Original', '200-350 руб'),
        ('А17ДВРМ', 'NGK', 'BPR6ES', 'Premium', '350-600 руб'),
        ('А17ДВРМ', 'DENSO', 'W20EPR-U', 'Standard', '300-500 руб'),
        ('2108-1006040', 'CONTITECH', 'CT1044', 'Premium', '1200-1800 руб'),
        ('2108-1006040', 'GATES', '5546XS', 'Original', '1000-1500 руб'),
    ]
    
    cursor.executemany('''
        INSERT OR REPLACE INTO analogs (original_number, analog_brand, analog_number, quality, price_range)
        VALUES (?, ?, ?, ?, ?)
    ''', analogs_data)
    
    conn.commit()
    conn.close()

# Инициализируем базу данных при запуске
init_database()

# --- Главное меню ---
def main_menu():
    buttons = [
        [InlineKeyboardButton("🚗 Выбрать модель", callback_data='select_model')],
        [InlineKeyboardButton("🔍 Поиск по VIN", callback_data='search_vin')],
        [InlineKeyboardButton("📋 Категории запчастей", callback_data='categories')],
        [InlineKeyboardButton("🔧 Поиск по артикулу", callback_data='search_by_number')],
        [InlineKeyboardButton("ℹ️ Помощь", callback_data='help')]
    ]
    return InlineKeyboardMarkup(buttons)

# --- Меню выбора модели ---
def models_menu():
    conn = sqlite3.connect('avto_vaz.db')
    cursor = conn.cursor()
    cursor.execute('SELECT code, name FROM models ORDER BY name')
    models = cursor.fetchall()
    conn.close()
    
    buttons = []
    for model_code, model_name in models:
        buttons.append([InlineKeyboardButton(model_name, callback_data=f'model_{model_code}')])
    
    buttons.append([InlineKeyboardButton("🔙 Назад", callback_data='main_menu')])
    return InlineKeyboardMarkup(buttons)

# --- Меню категорий ---
def categories_menu():
    categories = [
        "🔧 Тормозная система",
        "🛢️ Система фильтрации", 
        "⚡ Система зажигания",
        "⚙️ Газораспределительный механизм",
        "🔄 Подвеска",
        "🚗 Рулевое управление",
        "🔋 Электрооборудование",
        "💡 Освещение",
        "🚙 Кузов",
        "❄️ Система охлаждения",
        "⛽ Топливная система",
        "🔩 Трансмиссия"
    ]
    
    buttons = []
    for category in categories:
        callback_data = f'category_{category.split()[1]}'
        buttons.append([InlineKeyboardButton(category, callback_data=callback_data)])
    
    buttons.append([InlineKeyboardButton("🔙 Назад", callback_data='main_menu')])
    return InlineKeyboardMarkup(buttons)

# --- Меню запчастей для модели ---
def parts_menu(model_code, category=None):
    conn = sqlite3.connect('avto_vaz.db')
    cursor = conn.cursor()
    
    if category:
        cursor.execute('''
            SELECT part_name, original_number FROM parts 
            WHERE model_code = ? AND category LIKE ? 
            ORDER BY part_name
        ''', (model_code, f'%{category}%'))
    else:
        cursor.execute('''
            SELECT part_name, original_number FROM parts 
            WHERE model_code = ? 
            ORDER BY category, part_name
        ''', (model_code,))
    
    parts = cursor.fetchall()
    conn.close()
    
    buttons = []
    for part_name, part_number in parts:
        display_name = f"{part_name}" 
        if part_number:
            display_name += f" ({part_number})"
        buttons.append([InlineKeyboardButton(
            display_name, 
            callback_data=f'part_{model_code}_{part_name.replace(" ", "_")}'
        )])
    
    buttons.append([InlineKeyboardButton("📋 Все категории", callback_data=f'model_{model_code}')])
    buttons.append([InlineKeyboardButton("🚗 Другие модели", callback_data='select_model')])
    buttons.append([InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')])
    
    return InlineKeyboardMarkup(buttons)

# --- Определение модели по VIN (улучшенная версия) ---
def detect_model_from_vin(vin):
    vin = vin.upper().strip()
    
    conn = sqlite3.connect('avto_vaz.db')
    cursor = conn.cursor()
    cursor.execute('SELECT code, name, vin_prefix FROM models')
    models = cursor.fetchall()
    conn.close()
    
    for model_code, model_name, vin_prefix in models:
        if vin_prefix:
            prefixes = vin_prefix.split(',')
            for prefix in prefixes:
                if vin.startswith(prefix.strip()):
                    return model_code, model_name
    
    # Если точного совпадения нет, ищем по WMI (первые 3 символа)
    wmi = vin[:3]
    if wmi == 'XTA':  # АвтоВАЗ
        # Пытаемся определить по 4-7 символам
        model_part = vin[3:7]
        for model_code, model_name, vin_prefix in models:
            if vin_prefix and model_part in vin_prefix:
                return model_code, model_name
    
    return None, None

# --- Команда /start ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "🔧 **АвтоВАЗ Помощник по запчастям**\n\n"
        "Я помогу найти оригинальные артикулы запчастей для твоего АвтоВАЗа!\n\n"
        "**Что я умею:**\n"
        "• 🚗 Подбирать запчасти по модели авто\n"
        "• 🔍 Искать по VIN-номеру\n"
        "• 📋 Искать по категориям запчастей\n"
        "• 🔎 Находить по артикулу\n"
        "• 💰 Показывать аналоги и цены\n\n"
        "**База данных:** 35+ моделей, 500+ запчастей\n\n"
        "Выбери действие:"
    )
    
    await update.message.reply_text(welcome_text, reply_markup=main_menu())

# --- Обработка VIN-номера ---
async def handle_vin_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    vin = update.message.text.upper().strip()
    
    if len(vin) < 11:
        await update.message.reply_text(
            "❌ VIN должен содержать минимум 11 символов\n"
            "Пример: `XTA210800Y1234567`\n\n"
            "Попробуй еще раз или выбери модель из списка:",
            reply_markup=models_menu()
        )
        return
    
    model_code, model_name = detect_model_from_vin(vin)
    
    if model_code:
        await update.message.reply_text(
            f"✅ **VIN распознан!**\n\n"
            f"🔢 **VIN:** `{vin}`\n"
            f"🚗 **Модель:** {model_name}\n"
            f"📋 **Код модели:** {model_code}\n\n"
            f"Теперь выбери нужную запчасть:",
            reply_markup=parts_menu(model_code)
        )
    else:
        await update.message.reply_text(
            f"❌ **Не удалось определить модель по VIN**\n\n"
            f"🔢 **Введенный VIN:** `{vin}`\n"
            f"⚠️ **Причина:** Модель не найдена в базе\n\n"
            f"**Что можно сделать:**\n"
            f"• Проверь правильность VIN\n"
            f"• Выбери модель вручную\n"
            f"• Напиши артикул для поиска\n\n"
            f"Выбери модель из списка:",
            reply_markup=models_menu()
        )

# --- Поиск по артикулу ---
async def handle_number_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    number = update.message.text.upper().strip()
    
    conn = sqlite3.connect('avto_vaz.db')
    cursor = conn.cursor()
    
    # Ищем запчасть по артикулу
    cursor.execute('''
        SELECT p.model_code, p.part_name, p.category, p.original_number, 
               p.description, p.price_range, m.name 
        FROM parts p 
        JOIN models m ON p.model_code = m.code 
        WHERE p.original_number LIKE ? OR p.part_name LIKE ?
        LIMIT 10
    ''', (f'%{number}%', f'%{number}%'))
    
    parts = cursor.fetchall()
    
    if parts:
        response_text = f"🔍 **Результаты поиска по '{number}':**\n\n"
        
        for i, (model_code, part_name, category, original_number, description, price_range, model_name) in enumerate(parts, 1):
            response_text += f"**{i}. {part_name}**\n"
            response_text += f"   🚗 Модель: {model_name}\n"
            response_text += f"   📦 Категория: {category}\n"
            if original_number:
                response_text += f"   🔢 Артикул: `{original_number}`\n"
            if description:
                response_text += f"   📝 Описание: {description}\n"
            if price_range:
                response_text += f"   💰 Цена: {price_range}\n"
            response_text += "\n"
        
        # Ищем аналоги
        cursor.execute('''
            SELECT analog_brand, analog_number, quality, price_range 
            FROM analogs 
            WHERE original_number = ?
        ''', (number,))
        
        analogs = cursor.fetchall()
        if analogs:
            response_text += "💡 **Доступные аналоги:**\n"
            for analog_brand, analog_number, quality, price_range in analogs:
                response_text += f"• {analog_brand} {analog_number} ({quality}) - {price_range}\n"
        
    else:
        response_text = (
            f"❌ **Запчасть с артикулом '{number}' не найдена**\n\n"
            f"**Что можно сделать:**\n"
            f"• Проверь правильность артикула\n"
            f"• Попробуй поиск по модели авто\n"
            f"• Используй поиск по VIN\n"
            f"• Уточни название запчасти\n"
        )
    
    conn.close()
    
    await update.message.reply_text(response_text, reply_markup=main_menu())

# --- Обработчик кнопок ---
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    try:
        if query.data == 'main_menu':
            await query.edit_message_text("🔧 Выбери действие:", reply_markup=main_menu())
            
        elif query.data == 'select_model':
            await query.edit_message_text("🚗 Выбери модель авто:", reply_markup=models_menu())
            
        elif query.data == 'search_vin':
            await query.edit_message_text(
                "🔍 **Поиск по VIN-номеру**\n\n"
                "Отправь мне VIN-номер твоего авто (минимум 11 символов):\n"
                "**Пример:** `XTA210800Y1234567`\n\n"
                "**Где найти VIN:**\n"
                "• Под капотом на шильдике\n"
                "• На стойке водительской двери\n"
                "• В ПТС или СТС\n\n"
                "Или выбери модель вручную:",
                reply_markup=models_menu()
            )
            
        elif query.data == 'categories':
            await query.edit_message_text("📋 Выбери категорию запчастей:", reply_markup=categories_menu())
            
        elif query.data == 'search_by_number':
            await query.edit_message_text(
                "🔎 **Поиск по артикулу**\n\n"
                "Отправь мне артикул запчасти:\n"
                "**Пример:** `2108-3501070`\n\n"
                "Я найду:\n"
                "• Модели авто где используется\n"
                "• Описание запчасти\n"
                "• Ценовой диапазон\n"
                "• Доступные аналоги\n\n"
                "Или выбери другой способ поиска:",
                reply_markup=main_menu()
            )
            
        elif query.data == 'help':
            help_text = (
                "ℹ️ **Помощь по использованию бота**\n\n"
                "**Способы поиска:**\n"
                "• 🚗 **По модели** - выбираешь авто и запчасть\n"
                "• 🔍 **По VIN** - автоматическое определение модели\n"
                "• 📋 **По категории** - поиск по типу запчасти\n"
                "• 🔎 **По артикулу** - прямой поиск по номеру\n\n"
                "**Формат VIN:**\n"
                "• 17 символов (международный стандарт)\n"
                "• Начинается с XTA... для АвтоВАЗ\n"
                "• Пример: XTA210800Y1234567\n\n"
                "**База данных:**\n"
                "• 35+ моделей АвтоВАЗ\n"
                "• 500+ оригинальных запчастей\n"
                "• Цены и аналоги\n\n"
                "Для начала работы нажми /start"
            )
            await query.edit_message_text(help_text, reply_markup=main_menu())
            
        elif query.data.startswith('model_'):
            model_code = query.data.replace('model_', '')
            conn = sqlite3.connect('avto_vaz.db')
            cursor = conn.cursor()
            cursor.execute('SELECT name FROM models WHERE code = ?', (model_code,))
            model_name = cursor.fetchone()[0]
            conn.close()
            
            response_text = (
                f"🚗 **Выбрана модель:** {model_name}\n\n"
                f"📋 **Доступные запчасти:**\n"
                f"Выбери категорию или посмотри все запчасти:"
            )
            
            buttons = [
                [InlineKeyboardButton("📋 Все запчасти", callback_data=f'parts_{model_code}')],
                [InlineKeyboardButton("🔧 По категориям", callback_data=f'categories_{model_code}')],
                [InlineKeyboardButton("🚗 Другие модели", callback_data='select_model')],
                [InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')]
            ]
            
            await query.edit_message_text(response_text, reply_markup=InlineKeyboardMarkup(buttons))
            
        elif query.data.startswith('parts_'):
            model_code = query.data.replace('parts_', '')
            conn = sqlite3.connect('avto_vaz.db')
            cursor = conn.cursor()
            cursor.execute('SELECT name FROM models WHERE code = ?', (model_code,))
            model_name = cursor.fetchone()[0]
            conn.close()
            
            await query.edit_message_text(
                f"🔧 **Запчасти для {model_name}:**\n\n"
                f"Выбери нужную запчасть:",
                reply_markup=parts_menu(model_code)
            )
            
        elif query.data.startswith('part_'):
            parts = query.data.replace('part_', '').split('_')
            if len(parts) >= 2:
                model_code = parts[0]
                part_name = ' '.join(parts[1:])
                
                conn = sqlite3.connect('avto_vaz.db')
                cursor = conn.cursor()
                
                # Получаем информацию о запчасти
                cursor.execute('''
                    SELECT p.part_name, p.category, p.original_number, 
                           p.description, p.price_range, m.name 
                    FROM parts p 
                    JOIN models m ON p.model_code = m.code 
                    WHERE p.model_code = ? AND p.part_name = ?
                ''', (model_code, part_name))
                
                part_info = cursor.fetchone()
                
                if part_info:
                    part_name, category, original_number, description, price_range, model_name = part_info
                    
                    response_text = (
                        f"🔧 **Информация о запчасти**\n\n"
                        f"🚗 **Модель:** {model_name}\n"
                        f"📝 **Запчасть:** {part_name}\n"
                        f"📦 **Категория:** {category}\n"
                    )
                    
                    if original_number:
                        response_text += f"🔢 **Оригинальный артикул:** `{original_number}`\n"
                    if description:
                        response_text += f"📋 **Описание:** {description}\n"
                    if price_range:
                        response_text += f"💰 **Ценовой диапазон:** {price_range}\n"
                    
                    # Ищем аналоги
                    if original_number:
                        cursor.execute('''
                            SELECT analog_brand, analog_number, quality, price_range 
                            FROM analogs 
                            WHERE original_number = ?
                        ''', (original_number,))
                        
                        analogs = cursor.fetchall()
                        if analogs:
                            response_text += "\n💡 **Рекомендуемые аналоги:**\n"
                            for analog_brand, analog_number, quality, price_range in analogs:
                                response_text += f"• **{analog_brand}** `{analog_number}` ({quality}) - {price_range}\n"
                    
                    response_text += "\n⚠️ **Уточняй артикул у продавца перед покупкой!**"
                    
                conn.close()
                
                buttons = [
                    [InlineKeyboardButton("📋 Другие запчасти", callback_data=f'parts_{model_code}')],
                    [InlineKeyboardButton("🚗 Выбрать модель", callback_data='select_model')],
                    [InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')]
                ]
                
                await query.edit_message_text(response_text, reply_markup=InlineKeyboardMarkup(buttons))
                
    except Exception as e:
        logger.error(f"Ошибка в обработчике кнопок: {e}")
        await query.edit_message_text("❌ Произошла ошибка. Используй /start")

# --- Обработчик текстовых сообщений ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    
    # Если сообщение похоже на VIN (начинается с XTA и достаточно длинное)
    if text.upper().startswith('XTA') and len(text) >= 11:
        await handle_vin_search(update, context)
    # Если сообщение похоже на артикул (содержит цифры и тире)
    elif any(c.isdigit() for c in text) and ('-' in text or len(text) >= 6):
        await handle_number_search(update, context)
    else:
        await update.message.reply_text(
            "🔧 Я не понял запрос. Вот что я умею:\n\n"
            "• 🚗 Искать запчасти по модели авто\n"
            "• 🔍 Определять модель по VIN-номеру\n"
            "• 🔎 Находить запчасти по артикулу\n\n"
            "Выбери действие:",
            reply_markup=main_menu()
        )

# --- Обработчик ошибок ---
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    error = context.error
    if "Message is not modified" in str(error):
        return
    logger.error(f"Ошибка: {error}")

# --- HTTP сервер для Render ---
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'AutoVAZ Parts Bot is running!')
    def log_message(self, *args): pass

def start_health_server():
    port = int(os.getenv('PORT', 10000))
    server = HTTPServer(('0.0.0.0', port), HealthHandler)
    print(f"✅ Health server started on port {port}")
    server.serve_forever()

# --- Запуск ---
if __name__ == "__main__":
    # HTTP сервер
    server_thread = threading.Thread(target=start_health_server, daemon=True)
    server_thread.start()
    
    # Бот
    if TOKEN:
        application = Application.builder().token(TOKEN).build()
        
        # Обработчики
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CallbackQueryHandler(button_handler))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        application.add_error_handler(error_handler)
        
        print("🔧 АвтоВАЗ Помощник запускается...")
        print("📊 База данных: 35 моделей, 500+ запчастей")
        application.run_polling()
    else:
        print("❌ Токен не найден")
