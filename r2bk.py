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
DATE, AMOUNT, CATEGORY, ACCOUNT, PROJECT, NOTE = range(6)

logging.basicConfig(level=logging.INFO)

CATEGORIES = [
    ["Оплата труда", "Расходы на самовыкупы"],
    ["Хозрасходы офис/склад", "Аренда офис+склад"],
    ["Сервисы ИТ, подписки и т.п.", "Юридические услуги"],
    ["Связь, Интернет", "Дивиденды", "Прочие административные расходы"],
    ["Командировочные (билеты, суточные, проживание)"],
    ["Поступления - взносы учредителя"]
]

ACCOUNTS = [
    ["Касса"],
    ["Карта"]
]

PROJECTS = [
    ["UNIVELES", "GRAFFIX"]
]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Я помогу записать расход.\n\nВведи дату операции в формате ДД.ММ.ГГГГ:",
        reply_markup=ReplyKeyboardRemove()
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
    await update.message.reply_text(
        "Выбери проект:",
        reply_markup=ReplyKeyboardMarkup(PROJECTS, one_time_keyboard=True, resize_keyboard=True)
    )
    return PROJECT

async def get_project(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["project"] = update.message.text
    keyboard = [["Пропустить"]]
    await update.message.reply_text(
        "Введи примечание или нажми кнопку Пропустить:",
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    )
    return NOTE

async def get_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    context.user_data["note"] = "" if text == "Пропустить" else text
    await save_and_respond(update, context)
    return ConversationHandler.END

async def skip_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["note"] = ""
    await save_and_respond(update, context)
    return ConversationHandler.END

async def save_and_respond(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = {
        "date":     context.user_data["date"],
        "amount":   context.user_data["amount"],
        "category": context.user_data["category"],
        "account":  context.user_data["account"],
        "project":  context.user_data["project"],
        "note":     context.user_data["note"],
    }

    try:
        requests.post(APPS_SCRIPT_URL, json=data)
        keyboard = [["💸 Внести расход"]]
        note_line = f"\n📝 Примечание: {data['note']}" if data["note"] else ""
        await update.message.reply_text(
            f"✅ Записано!\n\n"
            f"📅 Дата: {data['date']}\n"
            f"💰 Сумма: {data['amount']}\n"
            f"📂 Статья: {data['category']}\n"
            f"🏦 Счёт: {data['account']}\n"
            f"🏢 Проект: {data['project']}"
            f"{note_line}",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )
    except Exception as e:
        await update.message.reply_text("❌ Ошибка при записи. Попробуй ещё раз.")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Отменено.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            MessageHandler(filters.Regex("^💸 Внести расход$"), start)
        ],
        states={
            DATE:     [MessageHandler(filters.TEXT & ~filters.COMMAND, get_date)],
            AMOUNT:   [MessageHandler(filters.TEXT & ~filters.COMMAND, get_amount)],
            CATEGORY: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_category)],
            ACCOUNT:  [MessageHandler(filters.TEXT & ~filters.COMMAND, get_account)],
            PROJECT:  [MessageHandler(filters.TEXT & ~filters.COMMAND, get_project)],
            NOTE:     [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_note),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    app.add_handler(conv_handler)
    print("Бот запущен...")
    app.run_polling()

if __name__ == "__main__":
    main()