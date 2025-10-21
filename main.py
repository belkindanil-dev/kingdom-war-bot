import random
import asyncio
from telegram import InlineKeyboardMarkup, InlineKeyboardButton

async def process_attack(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    kingdom = get_or_create_kingdom(user_id)
    attack_type = query.data

    # Стоимость и награды
    rewards = {
        'attack_weak': {'gold': 100, 'food': 50},
        'attack_medium': {'gold': 250, 'food': 120}
    }
    cost = {'attack_weak': 50, 'attack_medium': 150}

    # Проверяем золото
    if kingdom.resources['gold'] < cost[attack_type]:
        await query.edit_message_text(
            text="❌ Недостаточно золота для атаки!",
            reply_markup=main_menu()
        )
        return

    # Списываем стоимость
    kingdom.resources['gold'] -= cost[attack_type]

    # 🎞 Гифки с рыцарями
    battle_gifs = {
        'attack_weak': "https://media.giphy.com/media/QBd2kLB5qDmysEXre9/giphy.gif",   # Бой рыцарей
        'attack_medium': "https://media.giphy.com/media/3oEjI6SIIHBdRxXI40/giphy.gif"   # Эпичная битва
    }
    victory_gif = "https://media.giphy.com/media/26tOZ42Mg6pbTUPHW/giphy.gif"
    defeat_gif = "https://media.giphy.com/media/d2lcHJTG5Tscg/giphy.gif"

    # Отправляем гифку битвы
    battle_msg = await query.message.reply_animation(
        animation=battle_gifs[attack_type],
        caption="⚔️ Сражение началось..."
    )

    # Задержка (имитация битвы)
    await asyncio.sleep(3)

    # Удаляем гифку битвы
    try:
        await context.bot.delete_message(chat_id=query.message.chat_id, message_id=battle_msg.message_id)
    except Exception:
        pass  # Если уже удалено или ошибка Telegram

    # Определяем исход битвы
    outcome = random.choice(["win", "lose"])

    if outcome == "win":
        reward = rewards[attack_type]
        kingdom.resources['gold'] += reward['gold']
        kingdom.resources['food'] += reward['food']

        # Гифка победы
        victory_msg = await query.message.reply_animation(
            animation=victory_gif,
            caption=f"🏆 Победа!\n\n💰 +{reward['gold']} золота\n🌾 +{reward['food']} еды"
        )
        await asyncio.sleep(3)
        # Удаляем гифку победы
        try:
            await context.bot.delete_message(chat_id=query.message.chat_id, message_id=victory_msg.message_id)
        except Exception:
            pass

        await query.message.reply_text(
            "⚔️ Битва окончена! Проверь статус королевства:",
            reply_markup=main_menu()
        )

    else:
        # Гифка поражения
        defeat_msg = await query.message.reply_animation(
            animation=defeat_gif,
            caption="💀 Поражение... Ты потерял немного ресурсов."
        )
        await asyncio.sleep(3)
        try:
            await context.bot.delete_message(chat_id=query.message.chat_id, message_id=defeat_msg.message_id)
        except Exception:
            pass

        # Наказание за поражение
        lost_gold = min(100, kingdom.resources['gold'] // 10)
        lost_food = min(50, kingdom.resources['food'] // 10)
        kingdom.resources['gold'] -= lost_gold
        kingdom.resources['food'] -= lost_food

        await query.message.reply_text(
            f"😢 Потери:\n💰 -{lost_gold} золота\n🌾 -{lost_food} еды",
            reply_markup=main_menu()
        )
