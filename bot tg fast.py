import logging
import sqlite3
import aiogram
from aiogram import types, Dispatcher
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils import executor

from data import FOODLIST
from gigachat import get_chat_completion, get_token, auth

conn = sqlite3.connect("database.db")
cursor = conn.cursor()

logging.basicConfig(level=logging.INFO)

bot = aiogram.Bot(token="")
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

btnlist = [KeyboardButton(i) for i in FOODLIST]
foodlistmenu = ReplyKeyboardMarkup(resize_keyboard=True).add(*btnlist)
sogl_keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)


@dp.message_handler(commands=["start", "get_a_recipe"])
async def start(message: types.Message):
    user_id = message.from_user.id
    result = cursor.execute(f"SELECT * FROM user WHERE user_id={user_id}").fetchall()
    if not result:
        res = "INSERT INTO user (user_id) VALUES (" + str(user_id) + ")"
        cursor.execute(res)
        conn.commit()

    if message.text == "/start":
        await bot.send_message(message.from_user.id, "Это бот для генерации рецептов из предложенных продуктов."
                                                     "\nВыбери продукты из предложенного списка "
                                                     "или введи самостоятельно:",
                               reply_markup=foodlistmenu)
        MESS = bot.send_message(message.from_user.id,
                                f"Список пустой\n\n/get_a_recipe - получить рецепт\n"
                                f"/start - перейти в начало и очистить список".replace('🍔', "\n"))
        MESS = await MESS
        res = "UPDATE user SET mes_list_id= " + str(MESS.message_id) + " WHERE user_id = " + str(message.from_user.id)
        t = "DELETE FROM lists_of_food WHERE user_id=" + str(message.from_user.id)
        cursor.execute(t)
        cursor.execute(res)
        conn.commit()
    elif message.text == "/help":
        pass
    elif message.text == "/get_a_recipe":
        res = cursor.execute(f"SELECT list_of_food FROM lists_of_food "
                             f"WHERE user_id={str(message.from_user.id)}").fetchall()
        tempmass = [i[0] for i in res]
        if tempmass:
            TOKEN = get_token(auth)["access_token"]
            ans = get_chat_completion(TOKEN, f"Придумай или найди рецепт ОДИН РЕЦЕПТ, причем только"
                                             f" с использованием в ингридиентах ТОЛЬКО СЛЕДУЮЩИХ "
                                             f"продуктов: {', '.join(tempmass)}. Не используй другие продукты. "
                                             f"Пиши короче").json()[
                'choices'][0]['message']['content']
            t = "DELETE FROM lists_of_food WHERE user_id=" + str(message.from_user.id)
            cursor.execute(t)
            conn.commit()
            await bot.send_message(message.from_user.id, ans)
            await bot.send_message(message.from_user.id,
                                   "/start - перейти в начало",
                                   reply_markup=types.ReplyKeyboardRemove())
        else:
            MESS = bot.send_message(message.from_user.id,
                                    f"Список пустой\n\n/get_a_recipe - получить рецепт\n"
                                    f"/start - перейти в начало и очистить список".replace('🍔', "\n"))
            MESS = await MESS
            res = "UPDATE user SET mes_list_id= " + str(MESS.message_id) + " WHERE user_id = " + str(
                message.from_user.id)
            t = "DELETE FROM lists_of_food WHERE user_id=" + str(message.from_user.id)
            cursor.execute(t)
            cursor.execute(res)
            conn.commit()



@dp.message_handler(lambda message: message.text in FOODLIST)
async def foodlist(message: types.Message):
    res = cursor.execute(f"SELECT list_of_food FROM lists_of_food "
                         f"WHERE user_id={str(message.from_user.id)}").fetchall()
    tempmass = [i[0] for i in res]
    if message.text.lower() in tempmass:
        t = "DELETE FROM lists_of_food WHERE user_id=" + str(message.from_user.id) \
            + " AND list_of_food='" + message.text + "'"
        cursor.execute(t)
        conn.commit()
    else:
        remp = "INSERT INTO lists_of_food (user_id, list_of_food) VALUES ('" + \
               str(message.from_user.id) + "', '" + message.text.lower() + "')"
        cursor.execute(remp)
        conn.commit()
    res = cursor.execute(f"SELECT list_of_food FROM lists_of_food WHERE user_id="
                         f"{str(message.from_user.id)}").fetchall()
    tempmass = [i[0].capitalize() for i in res]
    user_id = message.from_user.id
    message_ids = cursor.execute(f"SELECT mes_list_id FROM user WHERE user_id={user_id}").fetchone()
    message_ids = message_ids[0]
    if tempmass:
        await bot.edit_message_text(f"Список выбранных продуктов:\n{'🍔'.join(tempmass)}"
                                    f"\n\nДля удаления из "
                                    f"списка введи продукт заново\n\n"
                                    f"/get_a_recipe - получить рецепт\n"
                                    f"/start - перейти в начало и очистить список".replace('🍔', "\n"),
                                    message_id=message_ids,
                                    chat_id=message.from_user.id)

    else:
        await bot.edit_message_text(f"Список пуст, выбери хотя бы один продукт\n\n"
                                    f"/get_a_recipe - получить рецепт\n"
                                    f"/start - перейти в начало и очистить список".replace('🍔', "\n"),
                                    message_id=message_ids,
                                    chat_id=message.from_user.id)

    await message.delete()


@dp.message_handler(lambda message: message.text not in FOODLIST)
async def nofoodlist(message: types.Message):
    TOKEN = get_token(auth)["access_token"]
    ans = get_chat_completion(TOKEN, f"Является ли {message.text} съедобным продуктом? Напиши да или нет.").json()[
        'choices'][0]['message']['content']
    res = cursor.execute(f"SELECT list_of_food FROM lists_of_food WHERE "
                         f"user_id={str(message.from_user.id)}").fetchall()
    tempmass = [i[0].lower() for i in res]
    if "да" in ans.lower():
        if message.text.lower() in tempmass:
            t = "DELETE FROM lists_of_food WHERE user_id=" + str(message.from_user.id) \
                + " AND list_of_food='" + message.text + "'"
            cursor.execute(t)
            conn.commit()
        else:
            remp = "INSERT INTO lists_of_food (user_id, list_of_food) VALUES ('" + \
                   str(message.from_user.id) + "', '" + message.text.lower() + "')"
            cursor.execute(remp)
            conn.commit()
        res = cursor.execute(f"SELECT list_of_food FROM lists_of_food WHERE user_id="
                             f"{str(message.from_user.id)}").fetchall()
        tempmass = [i[0].capitalize() for i in res]
        user_id = message.from_user.id
        message_ids = cursor.execute(f"SELECT mes_list_id FROM user WHERE user_id={user_id}").fetchone()
        message_ids = message_ids[0]
        if tempmass:
            await bot.edit_message_text(f"Список выбранных продуктов:\n{'🍔'.join(tempmass)}"
                                        f"\n\nДля удаления из "
                                        f"списка введи продукт заново\n\n"
                                        f"/get_a_recipe - получить рецепт\n"
                                        f"/start - перейти в начало и очистить список".replace('🍔', "\n"),
                                        message_id=message_ids,
                                        chat_id=message.from_user.id)

        else:
            await bot.edit_message_text(f"Список пуст, выбери хотя бы один продукт\n\n"
                                        f"/get_a_recipe - получить рецепт\n"
                                        f"/start - перейти в начало и очистить список".replace('🍔', "\n"),
                                        message_id=message_ids,
                                        chat_id=message.from_user.id)
        await message.delete()
    else:
        await bot.send_message(message.from_user.id, "Такого продукта не существует")
        res = cursor.execute(f"SELECT list_of_food FROM lists_of_food WHERE user_id="
                             f"{str(message.from_user.id)}").fetchall()
        tempmass = [i[0].capitalize() for i in res]

        if tempmass:
            MESS = bot.send_message(message.from_user.id, f"Список выбранных продуктов:\n{'🍔'.join(tempmass)}"
                                                          f"\n\nДля удаления из "
                                                          f"списка введи продукт заново\n\n"
                                                          f"/get_a_recipe - получить рецепт\n"
                                                          f"/start - перейти в начало и очистить "
                                                          f"список".replace('🍔', "\n"))
        else:
            MESS = bot.send_message(message.from_user.id, f"Список пуст, выбери хотя бы один продукт\n\n"
                                                          f"/get_a_recipe - получить рецепт\n"
                                                          f"/start - перейти в начало и очистить "
                                                          f"список".replace('🍔', "\n"))
        user_id = message.from_user.id
        MESS = await MESS
        res = "UPDATE user SET mes_list_id= " + str(MESS.message_id) + \
              " WHERE user_id = " + str(message.from_user.id)
        cursor.execute(res)
        conn.commit()
        await message.delete()


if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=False)
