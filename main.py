import random
import asyncio
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

# --- Хранилище игроков и их королевств ---
kingdoms = {}  # {user_id: Kingdom}

class Kingdom:
    def __init__(self):
        self.resources = {'gold': 500, 'food': 300}
        self.hp = 100
        self.max_hp = 100
        self.level = 1
        self.attack_power = 1
        self.defense = 1
        self.farms = 1
        self.cities = 1

def get_or_create_kingdom(user_id):
    if user_id not in kingdoms:
        kingdoms[user_id] = Kingdom()
    return kingdoms[user_id]

# --- Главное меню ---
def main_menu():
    buttons = [
        [InlineKeyboardButton("⚔️ Военная стратегия", callback_data='war_menu')],
        [InlineKeyboardButton("🏰 Экономическая стратегия", callback_data='economy_menu')],
        [InlineKeyboardButton("🌾 Ресурсная стратегия", callback_data='resource_menu')],
        [InlineKeyboardButton("🎯 Миссии", callback_data='missions_menu')]
    ]
    return InlineKeyboardMarkup(buttons)

# --- Военная стратегия ---
def war_menu():
    buttons = [
        [InlineKeyboardButton("Сразиться с NPC", callback_data='attack_menu')],
        [InlineKeyboardButton("Сразиться с игроком", callback_data='start_pvp')],
        [InlineKeyboardButton("Назад", callback_data='main_menu')]
    ]
    return InlineKeyboardMarkup(buttons)

# --- Экономическая стратегия ---
def economy_menu():
    buttons = [
        [InlineKeyboardButton("Улучшить город (+1 уровень) — 200 золота", callback_data='upgrade_city')],
        [InlineKeyboardButton("Назад", callback_data='main_menu')]
    ]
    return InlineKeyboardMarkup(buttons)

# --- Ресурсная стратегия ---
def resource_menu():
    buttons = [
        [InlineKeyboardButton("Построить ферму (+1) — 150 золота", callback_data='build_farm')],
        [InlineKeyboardButton("Собрать ресурсы", callback_data='collect_resources')],
        [InlineKeyboardButton("Назад", callback_data='main_menu')]
    ]
    return InlineKeyboardMarkup(buttons)

# --- Меню миссий ---
def missions_menu():
    buttons = [
        [InlineKeyboardButton("⚔️ Военная миссия", callback_data='mission_war')],
        [InlineKeyboardButton("🏰 Экономическая миссия", callback_data='mission_economy')],
        [InlineKeyboardButton("🌾 Ресурсная миссия", callback_data='mission_resource')],
        [InlineKeyboardButton("Назад", callback_data='main_menu')]
    ]
    return InlineKeyboardMarkup(buttons)

# --- HP панель для PvP ---
def hp_bar(hp):
    total = 20
    filled = int(max(hp,0) / 100 * total)
    empty = total - filled
    return "🟩" * filled + "⬛" * empty

# --- Команда /start ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    get_or_create_kingdom(user_id)
    await update.message.reply_text("Добро пожаловать в королевство! Выберите стратегию:", reply_markup=main_menu())

# --- Обработка апгрейдов и строительства ---
async def handle_upgrade(query, kingdom, upgrade_type):
    if upgrade_type == 'upgrade_hp':
        cost = 200
        if kingdom.resources['gold'] < cost:
            await query.message.reply_text("❌ Недостаточно золота!")
            return
        kingdom.resources['gold'] -= cost
        kingdom.max_hp += 20
        kingdom.hp = kingdom.max_hp
        await query.message.reply_text(f"✅ HP увеличено до {kingdom.max_hp}!")

    elif upgrade_type == 'upgrade_attack':
        cost = 150
        if kingdom.resources['gold'] < cost:
            await query.message.reply_text("❌ Недостаточно золота!")
            return
        kingdom.resources['gold'] -= cost
        kingdom.attack_power += 1
        await query.message.reply_text(f"✅ Атака увеличена до {kingdom.attack_power}!")

    elif upgrade_type == 'upgrade_defense':
        cost = 150
        if kingdom.resources['gold'] < cost:
            await query.message.reply_text("❌ Недостаточно золота!")
            return
        kingdom.resources['gold'] -= cost
        kingdom.defense += 1
        await query.message.reply_text(f"✅ Защита увеличена до {kingdom.defense}!")

    elif upgrade_type == 'upgrade_city':
        cost = 200
        if kingdom.resources['gold'] < cost:
            await query.message.reply_text("❌ Недостаточно золота!")
            return
        kingdom.resources['gold'] -= cost
        kingdom.cities += 1
        await query.message.reply_text(f"🏰 Уровень города увеличен до {kingdom.cities}!")

    elif upgrade_type == 'build_farm':
        cost = 150
        if kingdom.resources['gold'] < cost:
            await query.message.reply_text("❌ Недостаточно золота!")
            return
        kingdom.resources['gold'] -= cost
        kingdom.farms += 1
        await query.message.reply_text(f"🌾 Ферма построена! Всего ферм: {kingdom.farms}")

# --- Сбор ресурсов ---
async def collect_resources(query, kingdom):
    gold_gain = 50 * kingdom.cities
    food_gain = 30 * kingdom.farms
    kingdom.resources['gold'] += gold_gain
    kingdom.resources['food'] += food_gain
    await query.message.reply_text(f"🌾 Собраны ресурсы:\n💰 {gold_gain} золота\n🌾 {food_gain} еды")

# --- PvP приглашение на бой ---
async def start_pvp_invite(attacker_id, defender_id, context):
    attacker = get_or_create_kingdom(attacker_id)
    defender = get_or_create_kingdom(defender_id)

    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("⚔️ Принять бой", callback_data=f"accept_{attacker_id}")],
        [InlineKeyboardButton("❌ Отклонить бой", callback_data=f"decline_{attacker_id}")]
    ])
    
    try:
        await context.bot.send_message(
            chat_id=defender_id,
            text=f"⚔️ Игрок {attacker_id} приглашает вас на битву!\nПримите или отклоните бой?",
            reply_markup=buttons
        )
        await context.bot.send_message(
            chat_id=attacker_id,
            text=f"⏳ Ожидание ответа игрока {defender_id}..."
        )
    except:
        await context.bot.send_message(chat_id=attacker_id, text="❌ Не удалось отправить приглашение.")

# --- Обработка принятия/отклонения PvP ---
async def handle_pvp_response(query, context):
    user_id = query.from_user.id
    data = query.data
    if data.startswith("accept_") or data.startswith("decline_"):
        attacker_id = int(data.split("_")[1])
        attacker = get_or_create_kingdom(attacker_id)
        defender = get_or_create_kingdom(user_id)

        if data.startswith("decline_"):
            await query.edit_message_text("❌ Вы отклонили битву.")
            try:
                await context.bot.send_message(chat_id=attacker_id,
                                               text=f"❌ Игрок {user_id} отклонил ваш вызов.")
            except: pass
            return

        # Если принял бой
        await query.edit_message_text("⚔️ Вы приняли бой!")
        try:
            await context.bot.send_message(chat_id=attacker_id,
                                           text=f"✅ Игрок {user_id} принял бой! Битва начинается...")
        except: pass

        # Старт битвы
        await run_pvp_battle(attacker, defender, attacker_id, user_id, context)

# --- PvP битва с GIF и HP ---
async def run_pvp_battle(attacker, defender, attacker_id, defender_id, context):
    attacker.hp = attacker.max_hp
    defender.hp = defender.max_hp
    battle_round = 1

    battle_msg = await context.bot.send_message(
        chat_id=attacker_id,
        text=f"Раунд {battle_round}\nВы: {hp_bar(attacker.hp)} {attacker.hp} HP\nПротивник: {hp_bar(defender.hp)} {defender.hp} HP\nБитва начинается!"
    )
    # Так же для защищаемого игрока
    try:
        await context.bot.send_message(
            chat_id=defender_id,
            text=f"Раунд {battle_round}\nВы: {hp_bar(defender.hp)} {defender.hp} HP\nПротивник: {hp_bar(attacker.hp)} {attacker.hp} HP\nБитва начинается!"
        )
    except: pass

    battle_gif = "https://media.giphy.com/media/QBd2kLB5qDmysEXre9/giphy.gif"
    gif_msg = await context.bot.send_animation(chat_id=attacker_id, animation=battle_gif)
    await asyncio.sleep(3)
    try:
        await context.bot.delete_message(chat_id=attacker_id, message_id=gif_msg.message_id)
    except: pass

    while attacker.hp > 0 and defender.hp > 0:
        await asyncio.sleep(2)
        attack_damage = random.randint(10, 25) * attacker.attack_power
        defend_damage = random.randint(8, 20) * defender.attack_power // max(defender.defense,1)
        defender.hp -= attack_damage
        attacker.hp -= defend_damage
        battle_round += 1

        # Обновление HP для обоих игроков
        try:
            await context.bot.send_message(
                chat_id=attacker_id,
                text=f"Раунд {battle_round}\nВы нанесли: {attack_damage} урона, получили: {defend_damage}\n"
                     f"Вы: {hp_bar(attacker.hp)} {max(attacker.hp,0)} HP\nПротивник: {hp_bar(defender.hp)} {max(defender.hp,0)} HP"
            )
        except: pass
        try:
            await context.bot.send_message(
                chat_id=defender_id,
                text=f"Раунд {battle_round}\nВы нанесли: {defend_damage} урона, получили: {attack_damage}\n"
                     f"Вы: {hp_bar(defender.hp)} {max(defender.hp,0)} HP\nПротивник: {hp_bar(attacker.hp)} {max(attacker.hp,0)} HP"
            )
        except: pass

    # Определение победителя
    if attacker.hp > 0:
        gold_stolen = defender.resources['gold']//2
        food_stolen = defender.resources['food']//2
        attacker.resources['gold'] += gold_stolen
        attacker.resources['food'] += food_stolen
        defender.resources['gold'] -= gold_stolen
        defender.resources['food'] -= food_stolen
        await context.bot.send_message(chat_id=attacker_id, text=f"🏆 Вы победили!\n💰 +{gold_stolen} золота\n🌾 +{food_stolen} еды")
        try:
            await context.bot.send_message(chat_id=defender_id, text=f"💀 Вы проиграли!\n💰 Потеряно: {gold_stolen} золота\n🌾 Потеряно: {food_stolen} еды")
        except: pass
    else:
        gold_stolen = attacker.resources['gold']//2
        food_stolen = attacker.resources['food']//2
        defender.resources['gold'] += gold_stolen
        defender.resources['food'] += food_stolen
        attacker.resources['gold'] -= gold_stolen
        attacker.resources['food'] -= food_stolen
        await context.bot.send_message(chat_id=attacker_id, text=f"💀 Вы проиграли!\n💰 Потеряно: {gold_stolen} золота\n🌾 Потеряно: {food_stolen} еды")
        try:
            await context.bot.send_message(chat_id=defender_id, text=f"🏆 Вы победили!\n💰 +{gold_stolen} золота\n🌾 +{food_stolen} еды")
        except: pass

# --- Обработка кнопок ---
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    kingdom = get_or_create_kingdom(user_id)

    # Главное меню
    if query.data == "main_menu":
        await query.edit_message_text("Выберите стратегию:", reply_markup=main_menu())
    # Военная стратегия
    elif query.data == "war_menu":
        await query.edit_message_text("Военная стратегия:", reply_markup=war_menu())
    elif query.data == "start_pvp":
        markup = pvp_menu(user_id)
        if markup:
            await query.edit_message_text("Выберите игрока для атаки:", reply_markup=markup)
        else:
            await query.edit_message_text("❌ Нет доступных противников!", reply_markup=main_menu())
    elif query.data.startswith("pvp_"):
        defender_id = int(query.data.split("_")[1])
        await start_pvp_invite(user_id, defender_id, context)
    elif query.data.startswith("accept_") or query.data.startswith("decline_"):
        await handle_pvp_response(query, context)
    # Экономическая стратегия
    elif query.data == "economy_menu":
        await query.edit_message_text("Экономическая стратегия:", reply_markup=economy_menu())
    elif query.data == "upgrade_city":
        await handle_upgrade(query, kingdom, 'upgrade_city')
    # Ресурсная стратегия
    elif query.data == "resource_menu":
        await query.edit_message_text("Ресурсная стратегия:", reply_markup=resource_menu())
    elif query.data == "build_farm":
        await handle_upgrade(query, kingdom, 'build_farm')
    elif query.data == "collect_resources":
        await collect_resources(query, kingdom)
    # Миссии
    elif query.data == "missions_menu":
        await query.edit_message_text("Выберите миссию:", reply_markup=missions_menu())
    elif query.data == "mission_war":
        await query.message.reply_text("Миссия военной стратегии пока заглушка!")
    elif query.data == "mission_economy":
        await query.message.reply_text("Миссия экономической стратегии пока заглушка!")
    elif query.data == "mission_resource":
        await query.message.reply_text("Миссия ресурсной стратегии пока заглушка!")

# --- PvP меню выбора игрока ---
def pvp_menu(current_user_id):
    opponents = [uid for uid in kingdoms.keys() if uid != current_user_id]
    if not opponents: return None
    buttons = [[InlineKeyboardButton(f"Игрок {uid}", callback_data=f"pvp_{uid}")] for uid in opponents]
    return InlineKeyboardMarkup(buttons)

# --- Запуск бота ---
if __name__ == "__main__":
    app = ApplicationBuilder().token("8056012397:AAG7cQuWw38ozN8hCJv8NMH0fyjpbv_zb4E").build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    print("Бот запущен...")
    app.run_polling()
