import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

TOKEN = os.getenv('TELEGRAM_TOKEN')

user_data = {}

class Kingdom:
    def __init__(self):
        self.resources = {'gold': 1000, 'food': 500, 'wood': 300, 'iron': 200}
        self.army = {'infantry': 10, 'archers': 5, 'knights': 2}
        self.buildings = {'farms': 1, 'mines': 1, 'barracks': 1}
        self.level = 1

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_data:
        user_data[user_id] = Kingdom()
    
    keyboard = [
        [InlineKeyboardButton("📊 Статус", callback_data="status")],
        [InlineKeyboardButton("⚔️ Атаковать", callback_data="attack")],
        [InlineKeyboardButton("🏗 Строить", callback_data="build")],
        [InlineKeyboardButton("🌾 Собрать ресурсы", callback_data="collect")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text("👑 Добро пожаловать в королевство!", reply_markup=reply_markup)

async def show_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    kingdom = user_data[user_id]
    
    status_text = f"""
🏰 **Твое королевство** (Уровень {kingdom.level})

💎 **Ресурсы:**
- Золото: {kingdom.resources['gold']}
- Еда: {kingdom.resources['food']}
- Дерево: {kingdom.resources['wood']}
- Железо: {kingdom.resources['iron']}

⚔️ **Армия:**
- Пехота: {kingdom.army['infantry']}
- Лучники: {kingdom.army['archers']}
- Рыцари: {kingdom.army['knights']}

🏗 **Здания:**
- Фермы: {kingdom.buildings['farms']}
- Шахты: {kingdom.buildings['mines']}
- Казармы: {kingdom.buildings['barracks']}
"""
    await query.edit_message_text(status_text, reply_markup=main_menu())

async def attack_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("🛡 Слабая армия (50 золота)", callback_data="attack_weak")],
        [InlineKeyboardButton("⚔️ Средняя армия (150 золота)", callback_data="attack_medium")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back")]
    ]
    await query.edit_message_text("⚔️ Выбери цель для атаки:", reply_markup=InlineKeyboardMarkup(keyboard))

async def process_attack(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    kingdom = user_data[user_id]
    attack_type = query.data
    
    rewards = {'attack_weak': {'gold': 100, 'food': 50}, 'attack_medium': {'gold': 250, 'food': 120}}
    cost = {'attack_weak': 50, 'attack_medium': 150}
    
    if kingdom.resources['gold'] >= cost[attack_type]:
        kingdom.resources['gold'] -= cost[attack_type]
        reward = rewards[attack_type]
        kingdom.resources['gold'] += reward['gold']
        kingdom.resources['food'] += reward['food']
        await query.edit_message_text(f"🎉 Победа! Получил: 💰+{reward['gold']} золота, 🌾+{reward['food']} еды", reply_markup=main_menu())
    else:
        await query.edit_message_text("❌ Недостаточно золота!", reply_markup=main_menu())

async def build_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("🌾 Ферма (100 дерева)", callback_data="build_farm")],
        [InlineKeyboardButton("⛏ Шахта (150 дерева)", callback_data="build_mine")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back")]
    ]
    await query.edit_message_text("🏗 Выбери здание:", reply_markup=InlineKeyboardMarkup(keyboard))

async def process_build(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    kingdom = user_data[user_id]
    build_type = query.data
    
    costs = {'build_farm': {'wood': 100}, 'build_mine': {'wood': 150}}
    building_names = {'build_farm': 'ферму', 'build_mine': 'шахту'}
    
    if kingdom.resources['wood'] >= costs[build_type]['wood']:
        kingdom.resources['wood'] -= costs[build_type]['wood']
        building_key = build_type.replace('build_', '') + 's'
        kingdom.buildings[building_key] += 1
        await query.edit_message_text(f"🏗 Построил {building_names[build_type]}!", reply_markup=main_menu())
    else:
        await query.edit_message_text("❌ Недостаточно дерева!", reply_markup=main_menu())

async def collect_resources(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    kingdom = user_data[user_id]
    
    food_collected = kingdom.buildings['farms'] * 50
    gold_collected = kingdom.buildings['mines'] * 30
    kingdom.resources['food'] += food_collected
    kingdom.resources['gold'] += gold_collected
    
    await query.edit_message_text(f"🌾 Собрано: +{food_collected} еды, +{gold_collected} золота", reply_markup=main_menu())

def main_menu():
    keyboard = [
        [InlineKeyboardButton("📊 Статус", callback_data="status")],
        [InlineKeyboardButton("⚔️ Атаковать", callback_data="attack")],
        [InlineKeyboardButton("🏗 Строить", callback_data="build")],
        [InlineKeyboardButton("🌾 Собрать ресурсы", callback_data="collect")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def back_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("👑 Выбери действие:", reply_markup=main_menu())

def main():
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(show_status, pattern="^status$"))
    application.add_handler(CallbackQueryHandler(attack_menu, pattern="^attack$"))
    application.add_handler(CallbackQueryHandler(build_menu, pattern="^build$"))
    application.add_handler(CallbackQueryHandler(collect_resources, pattern="^collect$"))
    application.add_handler(CallbackQueryHandler(process_attack, pattern="^attack_"))
    application.add_handler(CallbackQueryHandler(process_build, pattern="^build_"))
    application.add_handler(CallbackQueryHandler(back_to_main, pattern="^back$"))
    
    print("Бот запущен! 🎮")
    application.run_polling()

if __name__ == "__main__":
    main()
