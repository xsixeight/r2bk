import logging
import requests
import os
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes, ConversationHandler
)

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
APPS_SCRIPT_URL = os.getenv("APPS_SCRIPT_URL")

# Этапы диалога
DATE, AMOUNT, CATEGORY, ACCOUNT = range(4)

logging.basicConfig(level=logging.INFO)

# Статьи расходов — можешь изменить под себя
CATEGORIES = [
    ["Зарплата", "Аренда"],
    ["Маркетинг", "Транспорт"],
    ["Прочее", "Закупка товара"]
]

# Счета списания — можешь изменить под себя
ACCOUNTS = [
    ["Касса"],
    ["Карта"]
]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Я помогу записать расход.\n\nВведи дату операции в формате ДД.ММ.ГГГГ:"
    )
    return DATE

async def get_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["date"] = update.message.text
    await update.message.reply_text("Введи сумму операции:")
    return AMOUNT

async def get_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["amount"] = update.message.text
    await update.message.reply_text(
        "Выбери статью расхода:",
        reply_markup=ReplyKeyboardMarkup(CATEGORIES, one_time_keyboard=True, resize_keyboard=True)
    )
    return CATEGORY

async def get_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["category"] = update.message.text
    await update.message.reply_text(
        "Выбери счёт списания:",
        reply_markup=ReplyKeyboardMarkup(ACCOUNTS, one_time_keyboard=True, resize_keyboard=True)
    )
    return ACCOUNT

async def get_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["account"] = update.message.text

    data = {
        "date":     context.user_data["date"],
        "amount":   context.user_data["amount"],
        "category": context.user_data["category"],
        "account":  context.user_data["account"],
    }

    try:
        requests.post(APPS_SCRIPT_URL, json=data)
        keyboard = [["💸 Внести расход"]]
        await update.message.reply_text(
            f"✅ Записано!\n\n"
            f"📅 Дата: {data['date']}\n"
            f"💰 Сумма: {data['amount']}\n"
            f"📂 Статья: {data['category']}\n"
            f"🏦 Счёт: {data['account']}",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )
    except Exception as e:
        await update.message.reply_text("❌ Ошибка при записи. Попробуй ещё раз.")

    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Отменено.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            DATE:     [MessageHandler(filters.TEXT & ~filters.COMMAND, get_date)],
            AMOUNT:   [MessageHandler(filters.TEXT & ~filters.COMMAND, get_amount)],
            CATEGORY: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_category)],
            ACCOUNT:  [MessageHandler(filters.TEXT & ~filters.COMMAND, get_account)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    app.add_handler(conv_handler)
    app.add_handler(MessageHandler(filters.Regex("^💸 Внести расход$"), start))
    print("Бот запущен...")
    app.run_polling()

if __name__ == "__main__":
    main()