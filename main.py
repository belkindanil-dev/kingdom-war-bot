import os
import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.getenv('TELEGRAM_TOKEN', '').strip()

if not TOKEN:
    logger.error("❌ Токен не найден! Добавь TELEGRAM_TOKEN в Environment Variables")
    exit(1)

# --- База данных запчастей (упрощенная версия) ---
PARTS_DATABASE = {
    "2108": {  # ВАЗ 2108/2109/21099
        "тормозные колодки": "2108-3501070",
        "воздушный фильтр": "2108-1109010",
        "масляный фильтр": "2108-1012005",
        "свечи зажигания": "2108-3701000",
        "ремень ГРМ": "2108-1006040",
        "амортизатор передний": "2108-2905452",
        "лампа ближнего света": "2108-3747010",
        "генератор": "2108-3701010",
        "стартер": "2108-3708010"
    },
    "2110": {  # ВАЗ 2110/2111/2112
        "тормозные колодки": "2110-3501070",
        "воздушный фильтр": "2110-1109010",
        "масляный фильтр": "2110-1012005",
        "свечи зажигания": "2110-3701000",
        "ремень ГРМ": "2110-1006040",
        "амортизатор передний": "2110-2905452",
        "лампа ближнего света": "2110-3747010",
        "генератор": "2110-3701010",
        "стартер": "2110-3708010"
    },
    "2114": {  # ВАЗ 2114/2115
        "тормозные колодки": "2114-3501070",
        "воздушный фильтр": "2114-1109010",
        "масляный фильтр": "2114-1012005",
        "свечи зажигания": "2114-3701000",
        "ремень ГРМ": "2114-1006040",
        "амортизатор передний": "2114-2905452",
        "лампа ближнего света": "2114-3747010"
    },
    "2121": {  # ВАЗ 2121 Нива
        "тормозные колодки": "2121-3501070",
        "воздушный фильтр": "2121-1109010",
        "масляный фильтр": "2121-1012005",
        "свечи зажигания": "2121-3701000",
        "ремень ГРМ": "2121-1006040",
        "амортизатор передний": "2121-2905452"
    },
    "2190": {  # LADA Granta
        "тормозные колодки": "2190-3501070",
        "воздушный фильтр": "2190-1109010",
        "масляный фильтр": "2190-1012005",
        "свечи зажигания": "2190-3701000",
        "ремень ГРМ": "2190-1006040",
        "лампа ближнего света": "2190-3747010"
    },
    "2170": {  # LADA Priora
        "тормозные колодки": "2170-3501070",
        "воздушный фильтр": "2170-1109010",
        "масляный фильтр": "2170-1012005",
        "свечи зажигания": "2170-3701000",
        "ремень ГРМ": "2170-1006040",
        "лампа ближнего света": "2170-3747010"
    }
}

# --- Популярные модели для быстрого выбора ---
POPULAR_MODELS = {
    "2108": "ВАЗ 2108/2109/21099 (Самара)",
    "2110": "ВАЗ 2110/2111/2112",
    "2114": "ВАЗ 2114/2115",
    "2121": "ВАЗ 2121 (Нива)",
    "2190": "LADA Granta",
    "2170": "LADA Priora"
}

# --- Главное меню ---
def main_menu():
    buttons = [
        [InlineKeyboardButton("🚗 Выбрать модель", callback_data='select_model')],
        [InlineKeyboardButton("🔍 Поиск по VIN", callback_data='search_vin')],
        [InlineKeyboardButton("📋 Список запчастей", callback_data='parts_list')],
        [InlineKeyboardButton("ℹ️ Помощь", callback_data='help')]
    ]
    return InlineKeyboardMarkup(buttons)

# --- Меню выбора модели ---
def models_menu():
    buttons = []
    for model_code, model_name in POPULAR_MODELS.items():
        buttons.append([InlineKeyboardButton(model_name, callback_data=f'model_{model_code}')])
    buttons.append([InlineKeyboardButton("🔙 Назад", callback_data='main_menu')])
    return InlineKeyboardMarkup(buttons)

# --- Меню запчастей для выбранной модели ---
def parts_menu(model_code):
    buttons = []
    parts = PARTS_DATABASE.get(model_code, {})
    
    for part_name, part_number in parts.items():
        buttons.append([InlineKeyboardButton(
            f"🔧 {part_name.title()}", 
            callback_data=f'part_{model_code}_{part_name}'
        )])
    
    buttons.append([InlineKeyboardButton("🔙 Назад к моделям", callback_data='select_model')])
    buttons.append([InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')])
    
    return InlineKeyboardMarkup(buttons)

# --- Команда /start ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "🔧 **АвтоВАЗ Помощник по запчастям**\n\n"
        "Я помогу найти оригинальные артикулы запчастей для твоего АвтоВАЗа!\n\n"
        "**Что я умею:**\n"
        "• 🚗 Подбирать запчасти по модели авто\n"
        "• 🔍 Искать по VIN-номеру\n"
        "• 📋 Показывать оригинальные артикулы\n"
        "• 💰 Рекомендовать аналоги\n\n"
        "Выбери действие:"
    )
    
    await update.message.reply_text(welcome_text, reply_markup=main_menu())

# --- Обработка выбора модели ---
async def handle_model_selection(query, model_code):
    model_name = POPULAR_MODELS.get(model_code, "Неизвестная модель")
    
    response_text = (
        f"🚗 **Выбрана модель:** {model_name}\n\n"
        f"📋 **Доступные запчасти:**\n"
    )
    
    parts = PARTS_DATABASE.get(model_code, {})
    if parts:
        for part_name, part_number in parts.items():
            response_text += f"• {part_name.title()}: `{part_number}`\n"
    else:
        response_text += "❌ Запчасти для этой модели не найдены\n"
    
    response_text += "\n🔧 Выбери нужную запчасть:"
    
    await query.edit_message_text(response_text, reply_markup=parts_menu(model_code))

# --- Обработка выбора запчасти ---
async def handle_part_selection(query, model_code, part_name):
    model_name = POPULAR_MODELS.get(model_code, "Неизвестная модель")
    part_number = PARTS_DATABASE.get(model_code, {}).get(part_name, "Не найден")
    
    response_text = (
        f"🔧 **Информация о запчасти**\n\n"
        f"🚗 Модель: {model_name}\n"
        f"📝 Запчасть: {part_name.title()}\n"
        f"🔢 **Оригинальный артикул:** `{part_number}`\n\n"
    )
    
    # Добавляем рекомендации по аналогам
    analogs = get_analogs(part_number)
    if analogs:
        response_text += "💡 **Рекомендуемые аналоги:**\n"
        for analog in analogs:
            response_text += f"• {analog}\n"
    
    response_text += "\n⚠️ **Важно:** Уточняй артикул у продавца!"
    
    buttons = [
        [InlineKeyboardButton("📋 Другие запчасти", callback_data=f'model_{model_code}')],
        [InlineKeyboardButton("🚗 Выбрать другую модель", callback_data='select_model')],
        [InlineKeyboardButton("🏠 Главное меню", callback_data='main_menu')]
    ]
    
    await query.edit_message_text(response_text, reply_markup=InlineKeyboardMarkup(buttons))

# --- Поиск аналогов (упрощенная версия) ---
def get_analogs(original_number):
    analogs_db = {
        "2108-3501070": ["BOSCH 0986494754", "TRW GDB1764", "FERODO FDB526"],
        "2108-1109010": ["MANN C25619", "KNECHT LX1024", "SACHS 320021"],
        "2108-1012005": ["MANN W940/25", "KNECHT OC256", "BOSCH 0451103319"],
        "2110-3501070": ["BOSCH 0986494755", "TRW GDB1765", "FERODO FDB527"],
        "2110-1109010": ["MANN C25620", "KNECHT LX1025", "SACHS 320022"],
        "2190-3501070": ["BOSCH 0986494756", "TRW GDB1766", "FERODO FDB528"]
    }
    return analogs_db.get(original_number, [])

# --- Обработка VIN-номера ---
async def handle_vin_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    vin = update.message.text.upper().strip()
    
    # Простая валидация VIN (17 символов)
    if len(vin) != 17:
        await update.message.reply_text(
            "❌ Неверный формат VIN! Должно быть 17 символов.\n"
            "Попробуй еще раз или выбери модель из списка:",
            reply_markup=main_menu()
        )
        return
    
    # Определяем модель по VIN (упрощенно)
    model_code = detect_model_from_vin(vin)
    
    if model_code:
        model_name = POPULAR_MODELS.get(model_code, "Неизвестная модель")
        await update.message.reply_text(
            f"✅ VIN распознан!\n"
            f"🚗 Модель: {model_name}\n\n"
            f"Теперь выбери нужную запчасть:",
            reply_markup=parts_menu(model_code)
        )
    else:
        await update.message.reply_text(
            "❌ Не удалось определить модель по VIN.\n"
            "Попробуй выбрать модель вручную:",
            reply_markup=models_menu()
        )

# --- Определение модели по VIN (упрощенное) ---
def detect_model_from_vin(vin):
    vin_prefixes = {
        "XTA2108": "2108",
        "XTA2109": "2108", 
        "XTA2110": "2110",
        "XTA2111": "2110",
        "XTA2112": "2110",
        "XTA2114": "2114",
        "XTA2121": "2121",
        "XTA2190": "2190",
        "XTA2170": "2170"
    }
    
    for prefix, model in vin_prefixes.items():
        if vin.startswith(prefix):
            return model
    return None

# --- Список всех запчастей ---
async def show_parts_list(query):
    response_text = "📋 **База запчастей АвтоВАЗ**\n\n"
    
    for model_code, parts in PARTS_DATABASE.items():
        model_name = POPULAR_MODELS.get(model_code, "Неизвестная модель")
        response_text += f"🚗 **{model_name}**\n"
        
        for part_name, part_number in parts.items():
            response_text += f"• {part_name.title()}: `{part_number}`\n"
        response_text += "\n"
    
    await query.edit_message_text(response_text, reply_markup=main_menu())

# --- Помощь ---
async def show_help(query):
    help_text = (
        "ℹ️ **Помощь по использованию бота**\n\n"
        "**Как найти запчасть:**\n"
        "1. 🚗 Выбери модель авто\n"
        "2. 🔧 Выбери нужную запчасть\n"
        "3. 📝 Получи оригинальный артикул\n\n"
        "**VIN-номер:**\n"
        "• Должен содержать 17 символов\n"
        "• Начинается с XTA...\n"
        "• Пример: XTA21080012345678\n\n"
        "**Важно:**\n"
        "• Артикулы могут обновляться\n"
        "• Уточняй у продавца перед покупкой\n"
        "• Сохраняй артикулы для быстрого поиска\n\n"
        "Для начала работы нажми /start"
    )
    
    await query.edit_message_text(help_text, reply_markup=main_menu())

# --- Обработчик кнопок ---
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == 'main_menu':
        await query.edit_message_text("🔧 Выбери действие:", reply_markup=main_menu())
        
    elif query.data == 'select_model':
        await query.edit_message_text("🚗 Выбери модель авто:", reply_markup=models_menu())
        
    elif query.data == 'search_vin':
        await query.edit_message_text(
            "🔍 **Поиск по VIN-номеру**\n\n"
            "Отправь мне VIN-номер твоего авто (17 символов):\n"
            "Пример: `XTA21080012345678`\n\n"
            "Или выбери модель вручную:",
            reply_markup=models_menu()
        )
        
    elif query.data == 'parts_list':
        await show_parts_list(query)
        
    elif query.data == 'help':
        await show_help(query)
        
    elif query.data.startswith('model_'):
        model_code = query.data.replace('model_', '')
        await handle_model_selection(query, model_code)
        
    elif query.data.startswith('part_'):
        parts = query.data.replace('part_', '').split('_')
        if len(parts) >= 2:
            model_code = parts[0]
            part_name = '_'.join(parts[1:])
            await handle_part_selection(query, model_code, part_name)

# --- Обработчик текстовых сообщений ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    
    # Если сообщение похоже на VIN
    if len(text) == 17 and text.upper().startswith('XTA'):
        await handle_vin_search(update, context)
    else:
        await update.message.reply_text(
            "🔧 Отправь VIN-номер или выбери действие:",
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
        application.run_polling()
    else:
        print("❌ Токен не найден")
