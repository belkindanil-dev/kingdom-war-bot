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

def get_or_create_kingdom(user_id):
    if user_id not in kingdoms:
        kingdoms[user_id] = Kingdom()
    return kingdoms[user_id]

# --- Главное меню ---
def main_menu():
    buttons = [
        [InlineKeyboardButton("⚔️ Атаковать NPC", callback_data='attack_menu')],
        [InlineKeyboardButton("⚔️ Сразиться с игроком", callback_data='start_pvp')],
        [InlineKeyboardButton("🏰 Развитие королевства", callback_data='upgrade_menu')]
    ]
    return InlineKeyboardMarkup(buttons)

# --- Меню атак NPC ---
def attack_menu():
    buttons = [
        [InlineKeyboardButton("Слабая армия", callback_data='attack_weak')],
        [InlineKeyboardButton("Средняя армия", callback_data='attack_medium')],
        [InlineKeyboardButton("Назад", callback_data='main_menu')]
    ]
    return InlineKeyboardMarkup(buttons)

# --- Меню PvP ---
def pvp_menu(current_user_id):
    opponents = [uid for uid in kingdoms.keys() if uid != current_user_id]
    if not opponents: return None
    buttons = [[InlineKeyboardButton(f"Игрок {uid}", callback_data=f"pvp_{uid}")] for uid in opponents]
    return InlineKeyboardMarkup(buttons)

# --- Меню апгрейдов ---
def upgrade_menu():
    buttons = [
        [InlineKeyboardButton("Увеличить HP (+20) — 200 золота", callback_data='upgrade_hp')],
        [InlineKeyboardButton("Увеличить атаку (+1) — 150 золота", callback_data='upgrade_attack')],
        [InlineKeyboardButton("Увеличить защиту (+1) — 150 золота", callback_data='upgrade_defense')],
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
    await update.message.reply_text("Добро пожаловать в королевство! Выберите действие:", reply_markup=main_menu())

# --- Обработка апгрейдов ---
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

# --- Обработка кнопок ---
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    kingdom = get_or_create_kingdom(user_id)

    if query.data == "main_menu":
        await query.edit_message_text("Выберите действие:", reply_markup=main_menu())

    elif query.data == "attack_menu":
        await query.edit_message_text("Выберите тип атаки:", reply_markup=attack_menu())

    elif query.data.startswith("attack_"):
        await process_npc_attack(query, context, user_id, query.data)

    elif query.data == "start_pvp":
        markup = pvp_menu(user_id)
        if markup:
            await query.edit_message_text("Выберите игрока для атаки:", reply_markup=markup)
        else:
            await query.edit_message_text("❌ Нет доступных противников!", reply_markup=main_menu())

    elif query.data.startswith("pvp_"):
        defender_id = int(query.data.split("_")[1])
        await start_pvp(query, context, attacker_id=user_id, defender_id=defender_id)

    elif query.data == "upgrade_menu":
        await query.edit_message_text("Выберите апгрейд:", reply_markup=upgrade_menu())
    elif query.data in ['upgrade_hp','upgrade_attack','upgrade_defense']:
        await handle_upgrade(query, kingdom, query.data)
        await query.message.reply_text("Выберите действие:", reply_markup=main_menu())

# --- Атака на NPC ---
async def process_npc_attack(query, context, user_id, attack_type):
    kingdom = get_or_create_kingdom(user_id)
    rewards = {'attack_weak': {'gold': 100, 'food': 50}, 'attack_medium': {'gold': 250, 'food': 120}}
    cost = {'attack_weak': 50, 'attack_medium': 150}

    if kingdom.resources['gold'] < cost[attack_type]:
        await query.edit_message_text("❌ Недостаточно золота для атаки!", reply_markup=main_menu())
        return

    kingdom.resources['gold'] -= cost[attack_type]

    battle_gifs = {
        'attack_weak': "https://media.giphy.com/media/QBd2kLB5qDmysEXre9/giphy.gif",
        'attack_medium': "https://media.giphy.com/media/3oEjI6SIIHBdRxXI40/giphy.gif"
    }
    victory_gif = "https://media.giphy.com/media/26tOZ42Mg6pbTUPHW/giphy.gif"
    defeat_gif = "https://media.giphy.com/media/d2lcHJTG5Tscg/giphy.gif"

    battle_msg = await query.message.reply_animation(animation=battle_gifs[attack_type], caption="⚔️ Сражение началось...")
    await asyncio.sleep(3)
    try: await context.bot.delete_message(chat_id=query.message.chat_id, message_id=battle_msg.message_id)
    except: pass

    # Учитываем бонусы атакой и защитой
    attack_bonus = kingdom.attack_power
    outcome = random.choice(["win", "lose"])

    if outcome == "win":
        reward = rewards[attack_type]
        reward['gold'] += 10*attack_bonus
        reward['food'] += 5*attack_bonus
        kingdom.resources['gold'] += reward['gold']
        kingdom.resources['food'] += reward['food']
        await query.message.reply_animation(animation=victory_gif,
                                           caption=f"🏆 Победа!\n💰 +{reward['gold']} золота\n🌾 +{reward['food']} еды")
    else:
        lost_gold = min(100, kingdom.resources['gold'] // 10)
        lost_food = min(50, kingdom.resources['food'] // 10)
        kingdom.resources['gold'] -= lost_gold
        kingdom.resources['food'] -= lost_food
        await query.message.reply_animation(animation=defeat_gif,
                                           caption=f"💀 Поражение! Потери:\n💰 -{lost_gold} золота\n🌾 -{lost_food} еды")

    await query.message.reply_text("⚔️ Битва окончена! Проверь статус королевства:", reply_markup=main_menu())

# --- PvP битва ---
async def start_pvp(query, context, attacker_id, defender_id):
    attacker = get_or_create_kingdom(attacker_id)
    defender = get_or_create_kingdom(defender_id)

    try:
        await context.bot.send_message(chat_id=defender_id,
                                       text=f"⚔️ Игрок {attacker_id} вызвал вас на бой!")
    except: pass

    attacker.hp = attacker.max_hp
    defender.hp = defender.max_hp
    battle_round = 1

    battle_msg = await query.message.reply_text(
        f"Раунд {battle_round}\nВы: {hp_bar(attacker.hp)} {attacker.hp} HP\nПротивник: {hp_bar(defender.hp)} {defender.hp} HP\nБитва начинается!"
    )

    while attacker.hp > 0 and defender.hp > 0:
        await asyncio.sleep(2)
        attack_damage = random.randint(10, 25) * attacker.attack_power
        defend_damage = random.randint(8, 20) * defender.attack_power // defender.defense
        defender.hp -= attack_damage
        attacker.hp -= defend_damage
        battle_round += 1

        await battle_msg.edit_text(
            f"Раунд {battle_round}\nВы нанесли: {attack_damage} урона, получили: {defend_damage}\n"
            f"Вы: {hp_bar(attacker.hp)} {max(attacker.hp,0)} HP\nПротивник: {hp_bar(defender.hp)} {max(defender.hp,0)} HP"
        )

    if attacker.hp > 0:
        gold_stolen = defender.resources['gold']//2
        food_stolen = defender.resources['food']//2
        attacker.resources['gold'] += gold_stolen
        attacker.resources['food'] += food_stolen
        defender.resources['gold'] -= gold_stolen
        defender.resources['food'] -= food_stolen
        await battle_msg.edit_text(battle_msg.text + f"\n🏆 Вы победили!\n💰 +{gold_stolen} золота\n🌾 +{food_stolen} еды")
        try:
            await context.bot.send_message(chat_id=defender_id,
                                           text=f"💀 Вы проиграли против игрока {attacker_id}.\n💰 Потеряно: {gold_stolen} золота\n🌾 Потеряно: {food_stolen} еды")
        except: pass
    else:
        gold_stolen = attacker.resources['gold']//2
        food_stolen = attacker.resources['food']//2
        defender.resources['gold'] += gold_stolen
        defender.resources['food'] += food_stolen
        attacker.resources['gold'] -= gold_stolen
        attacker.resources['food'] -= food_stolen
        await battle_msg.edit_text(battle_msg.text + f"\n💀 Вы проиграли!\n💰 Потеряно: {gold_stolen} золота\n🌾 Потеряно: {food_stolen} еды")
        try:
            await context.bot.send_message(chat_id=defender_id,
                                           text=f"🏆 Вы выиграли битву против игрока {attacker_id}!\n💰 +{gold_stolen} золота\n🌾 +{food_stolen} еды")
        except: pass

    await query.message.reply_text("⚔️ Битва окончена!", reply_markup=main_menu())

# --- Запуск бота ---
if __name__ == "__main__":
    app = ApplicationBuilder().token("8056012397:AAG7cQuWw38ozN8hCJv8NMH0fyjpbv_zb4E").build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    print("Бот запущен...")
    app.run_polling()
