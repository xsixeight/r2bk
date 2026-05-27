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
MONEY_SELLERS_API_KEY = os.getenv("MONEY_SELLERS_API_KEY")

# Этапы диалога
DATE, AMOUNT, CATEGORY, ACCOUNT = range(4)

logging.basicConfig(level=logging.INFO)

# Статьи расходов с ID потока
STREAMS_MAP = {
    "Закупка товара":   2334170,
    "Аренда офиса":     2327766,
    "Аренда склада":    2327767,
    "Реклама":          2327725,
    "Оплата труда":     2327704,
    "Логистика":        2327628,
    "Сервисы ИТ":       2327737,
    "Прочие расходы":   2327765,
}

CATEGORIES = [[name] for name in STREAMS_MAP.keys()]

# Счета списания
ACCOUNTS_MAP = {
    "Наличные":                  {"accountId": 584954, "organisationId": 151207},
    "Карта физ лица":            {"accountId": 584964, "organisationId": 151207},
}

ACCOUNTS = [[name] for name in ACCOUNTS_MAP.keys()]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Я помогу записать расход.\n\nВведи дату операции в формате ДД.ММ.ГГГГ:",
        reply_markup=ReplyKeyboardRemove()
    )
    return DATE


async def get_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Конвертируем дату из ДД.ММ.ГГГГ в ГГГГ-ММ-ДД для API
    try:
        parts = update.message.text.strip().split(".")
        date_formatted = f"{parts[2]}-{parts[1]}-{parts[0]}"
        context.user_data["date"] = date_formatted
        context.user_data["date_display"] = update.message.text.strip()
    except:
        await update.message.reply_text("❌ Неверный формат даты. Введи в формате ДД.ММ.ГГГГ, например 26.05.2026:")
        return DATE

    await update.message.reply_text("Введи сумму операции:")
    return AMOUNT


async def get_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amount = float(update.message.text.strip().replace(",", "."))
        context.user_data["amount"] = amount
    except:
        await update.message.reply_text("❌ Неверный формат суммы. Введи число, например 5000 или 1500.50:")
        return AMOUNT

    await update.message.reply_text(
        "Выбери статью расхода:",
        reply_markup=ReplyKeyboardMarkup(CATEGORIES, one_time_keyboard=True, resize_keyboard=True)
    )
    return CATEGORY


async def get_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text not in STREAMS_MAP:
        await update.message.reply_text(
            "❌ Выбери статью из списка:",
            reply_markup=ReplyKeyboardMarkup(CATEGORIES, one_time_keyboard=True, resize_keyboard=True)
        )
        return CATEGORY

    context.user_data["category"] = update.message.text
    await update.message.reply_text(
        "Выбери счёт списания:",
        reply_markup=ReplyKeyboardMarkup(ACCOUNTS, one_time_keyboard=True, resize_keyboard=True)
    )
    return ACCOUNT


async def get_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text not in ACCOUNTS_MAP:
        await update.message.reply_text(
            "❌ Выбери счёт из списка:",
            reply_markup=ReplyKeyboardMarkup(ACCOUNTS, one_time_keyboard=True, resize_keyboard=True)
        )
        return ACCOUNT

    context.user_data["account"] = update.message.text

    account_info = ACCOUNTS_MAP[context.user_data["account"]]

    payload = [{
        "paymentDate":         context.user_data["date"],
        "internalPaymentDate": context.user_data["date"],
        "paymentSum":          context.user_data["amount"],
        "paymentPurpose":      context.user_data["category"],
        "accountId":           account_info["accountId"],
        "organisationId":      account_info["organisationId"],
        "operationTypeId":     411,
        "directionId":         510,
        "sourceCurrencyId":    "RUB",
        "sourcePaymentSum":    context.user_data["amount"],
        "paymentStatusId":     531,
        "priorityId":          532,
    }]

    headers = {
        "X-API-KEY": MONEY_SELLERS_API_KEY,
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(
            "https://rest.api.report.finance/api/Payments",
            json=payload,
            headers=headers
        )
        if response.status_code == 200:
            keyboard = [["💸 Внести расход"]]
            await update.message.reply_text(
                f"✅ Записано в Money Sellers!\n\n"
                f"📅 Дата: {context.user_data['date_display']}\n"
                f"💰 Сумма: {context.user_data['amount']}\n"
                f"📂 Статья: {context.user_data['category']}\n"
                f"🏦 Счёт: {context.user_data['account']}",
                reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            )
        else:
            await update.message.reply_text(
                f"❌ Ошибка API: {response.status_code}\n{response.text}"
            )
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")

    return ConversationHandler.END


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
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    app.add_handler(conv_handler)
    print("Бот запущен...")
    app.run_polling()


if __name__ == "__main__":
    main()