import os
import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.getenv('TELEGRAM_TOKEN')

# Игровые данные пользователей
user_data = {}

class Kingdom:
    def __init__(self):
        self.resources = {'gold': 1000, 'food': 500, 'wood': 300, 'iron': 200}
        self.army = {'infantry': 10, 'archers': 5, 'knights': 2}
        self.buildings = {'farms': 1, 'mines': 1, 'barracks': 1}
        self.level = 1

def get_or_create_kingdom(user_id):
    """Создает новое королевство если его нет"""
    if user_id not in user_data:
        user_data[user_id] = Kingdom()
        logger.info(f"Создано новое королевство для пользователя {user_id}")
    return user_data[user_id]

async def safe_user_action(update: Update, context: ContextTypes.DEFAULT_TYPE, action_func):
    """Безопасно выполняет действие с пользователем"""
    try:
        user_id = update.effective_user.id
        kingdom = get_or_create_kingdom(user_id)
        await action_func(update, context, kingdom)
    except KeyError as e:
        logger.error(f"KeyError для пользователя {update.effective_user.id}: {e}")
        # Пересоздаем королевство и пробуем снова
        user_id = update.effective_user.id
        user_data[user_id] = Kingdom()
        kingdom = user_data[user_id]
        await action_func(update, context, kingdom)
    except Exception as e:
        logger.error(f"Ошибка в safe_user_action: {e}")
        if update.callback_query:
            await update.callback_query.message.reply_text("❌ Произошла ошибка. Попробуй /start")
        elif update.message:
            await update.message.reply_text("❌ Произошла ошибка. Попробуй /start")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await safe_user_action(update, context, start_action)

async def start_action(update: Update, context: ContextTypes.DEFAULT_TYPE, kingdom):
    keyboard = [
        [InlineKeyboardButton("📊 Статус", callback_data="status")],
        [InlineKeyboardButton("⚔️ Атаковать", callback_data="attack")],
        [InlineKeyboardButton("🏗 Строить", callback_data="build")],
        [InlineKeyboardButton("🌾 Собрать ресурсы", callback_data="collect")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "👑 Добро пожаловать в королевство, Властелин!\nВыбери действие:",
        reply_markup=reply_markup
    )

async def show_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await safe_user_action(update, context, show_status_action)

async def show_status_action(update: Update, context: ContextTypes.DEFAULT_TYPE, kingdom):
    query = update.callback_query
    await query.answer()
    
    status_text = f"""
🏰 Твое королевство (Уровень {kingdom.level})

💎 Ресурсы:
- Золото: {kingdom.resources['gold']}
- Еда: {kingdom.resources['food']}
- Дерево: {kingdom.resources['wood']}
- Железо: {kingdom.resources['iron']}

⚔️ Армия:
- Пехота: {kingdom.army['infantry']}
- Лучники: {kingdom.army['archers']}
- Рыцари: {kingdom.army['knights']}

🏗 Здания:
- Фермы: {kingdom.buildings['farms']}
- Шахты: {kingdom.buildings['mines']}
- Казармы: {kingdom.buildings['barracks']}
"""
    await query.edit_message_text(
        text=status_text,
        reply_markup=main_menu()
    )

async def attack_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await safe_user_action(update, context, attack_menu_action)

async def attack_menu_action(update: Update, context: ContextTypes.DEFAULT_TYPE, kingdom):
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("🛡 Слабая армия (50 золота)", callback_data="attack_weak")],
        [InlineKeyboardButton("⚔️ Средняя армия (150 золота)", callback_data="attack_medium")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back")]
    ]
    await query.edit_message_text(
        text="⚔️ Выбери цель для атаки:\nЗа победу получишь ресурсы и золото!",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def process_attack(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await safe_user_action(update, context, process_attack_action)

async def process_attack_action(update: Update, context: ContextTypes.DEFAULT_TYPE, kingdom):
    query = update.callback_query
    await query.answer()
    attack_type = query.data
    
    rewards = {'attack_weak': {'gold': 100, 'food': 50}, 'attack_medium': {'gold': 250, 'food': 120}}
    cost = {'attack_weak': 50, 'attack_medium': 150}
    
    if kingdom.resources['gold'] >= cost[attack_type]:
        kingdom.resources['gold'] -= cost[attack_type]
        reward = rewards[attack_type]
        kingdom.resources['gold'] += reward['gold']
        kingdom.resources['food'] += reward['food']
        
        await query.edit_message_text(
            text=f"🎉 Победа!\n\nТы победил вражескую армию и получил:\n💰 +{reward['gold']} золота\n🌾 +{reward['food']} еды",
            reply_markup=main_menu()
        )
    else:
        await query.edit_message_text(
            text="❌ Недостаточно золота для атаки!",
            reply_markup=main_menu()
        )

async def build_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await safe_user_action(update, context, build_menu_action)

async def build_menu_action(update: Update, context: ContextTypes.DEFAULT_TYPE, kingdom):
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("🌾 Ферма (100 дерева)", callback_data="build_farm")],
        [InlineKeyboardButton("⛏ Шахта (150 дерева)", callback_data="build_mine")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back")]
    ]
    await query.edit_message_text(
        text="🏗 Выбери здание для постройки:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def process_build(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await safe_user_action(update, context, process_build_action)

async def process_build_action(update: Update, context: ContextTypes.DEFAULT_TYPE, kingdom):
    query = update.callback_query
    await query.answer()
    build_type = query.data
    
    costs = {'build_farm': {'wood': 100}, 'build_mine': {'wood': 150}}
    building_names = {'build_farm': 'ферму', 'build_mine': 'шахту'}
    
    if kingdom.resources['wood'] >= costs[build_type]['wood']:
        kingdom.resources['wood'] -= costs[build_type]['wood']
        building_key = build_type.replace('build_', '') + 's'
        kingdom.buildings[building_key] += 1
        
        await query.edit_message_text(
            text=f"🏗 Ты построил {building_names[build_type]}!",
            reply_markup=main_menu()
        )
    else:
        await query.edit_message_text(
            text="❌ Недостаточно дерева для строительства!",
            reply_markup=main_menu()
        )

async def collect_resources(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await safe_user_action(update, context, collect_resources_action)

async def collect_resources_action(update: Update, context: ContextTypes.DEFAULT_TYPE, kingdom):
    query = update.callback_query
    await query.answer()
    
    food_collected = kingdom.buildings['farms'] * 50
    gold_collected = kingdom.buildings['mines'] * 30
    
    kingdom.resources['food'] += food_collected
    kingdom.resources['gold'] += gold_collected
    
    await query.edit_message_text(
        text=f"🌾 Ресурсы собраны!\n\nС ферм: +{food_collected} еды\nС шахт: +{gold_collected} золота",
        reply_markup=main_menu()
    )

async def back_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await safe_user_action(update, context, back_to_main_action)

async def back_to_main_action(update: Update, context: ContextTypes.DEFAULT_TYPE, kingdom):
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        text="👑 Выбери действие:",
        reply_markup=main_menu()
    )

def main_menu():
    keyboard = [
        [InlineKeyboardButton("📊 Статус", callback_data="status")],
        [InlineKeyboardButton("⚔️ Атаковать", callback_data="attack")],
        [InlineKeyboardButton("🏗 Строить", callback_data="build")],
        [InlineKeyboardButton("🌾 Собрать ресурсы", callback_data="collect")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ошибок"""
    logger.error(f"Ошибка: {context.error}")
    try:
        if update and update.effective_user:
            await update.effective_user.send_message(
                "❌ Произошла ошибка. Попробуй начать заново с /start"
            )
    except Exception as e:
        logger.error(f"Ошибка в error_handler: {e}")

async def run_bot():
    """Запуск бота"""
    if not TOKEN:
        logger.error("Токен не найден! Проверь переменную TELEGRAM_TOKEN")
        return
    
    try:
        application = Application.builder().token(TOKEN).build()
        
        # Обработчики команд
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CallbackQueryHandler(show_status, pattern="^status$"))
        application.add_handler(CallbackQueryHandler(attack_menu, pattern="^attack$"))
        application.add_handler(CallbackQueryHandler(build_menu, pattern="^build$"))
        application.add_handler(CallbackQueryHandler(collect_resources, pattern="^collect$"))
        application.add_handler(CallbackQueryHandler(process_attack, pattern="^attack_"))
        application.add_handler(CallbackQueryHandler(process_build, pattern="^build_"))
        application.add_handler(CallbackQueryHandler(back_to_main, pattern="^back$"))
        
        # Обработчик ошибок
        application.add_error_handler(error_handler)
        
        logger.info("Бот запускается... 🎮")
        await application.run_polling()
        
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")

def start_simple_server():
    """Простой HTTP сервер для Render"""
    from http.server import HTTPServer, BaseHTTPRequestHandler
    import threading
    
    class SimpleHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'Bot is running!')
        
        def log_message(self, format, *args):
            pass  # Отключаем логирование запросов
    
    def run_server():
        server = HTTPServer(('0.0.0.0', 8080), SimpleHandler)
        logger.info("HTTP сервер запущен на порту 8080")
        server.serve_forever()
    
    # Запускаем сервер в отдельном потоке
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()

def main():
    # Запускаем простой HTTP сервер для Render
    start_simple_server()
    
    # Запускаем бота
    asyncio.run(run_bot())

if __name__ == "__main__":
    main()
