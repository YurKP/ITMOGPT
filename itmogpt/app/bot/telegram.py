import logging
from typing import Set

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from app.config import cfg

logger = logging.getLogger("itmogpt.bot")


class ITMOBot:
    def __init__(self, router):
        self.router = router
        self.application = Application.builder().token(cfg.BOT_TOKEN).build()
        self.allowed_users: Set[str] = set(cfg.ALLOWED_USERS)
        self._setup_handlers()

    def _is_allowed(self, user) -> bool:
        if not self.allowed_users:
            return True
        if not user.username:
            return False
        return user.username.lower() in self.allowed_users

    def _setup_handlers(self):
        self.application.add_handler(CommandHandler("start", self._cmd_start))
        self.application.add_handler(CommandHandler("help", self._cmd_help))
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_message)
        )

    async def _cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._is_allowed(update.effective_user):
            await update.message.reply_text("❌ Нет доступа.")
            return
        await update.message.reply_text(
            "👋 Привет! Я ИТМО GPT — твой студенческий помощник!\n\n"
            "Просто напиши вопрос, и я постараюсь помочь.\n"
            "Могу искать научные статьи (Гостомысл) и строить пути обучения (Выготский).\n\n"
            "Напиши /help для подробностей."
        )

    async def _cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._is_allowed(update.effective_user):
            await update.message.reply_text("❌ Нет доступа.")
            return
        await update.message.reply_text(
            "🤖 **ИТМО GPT — Помощь**\n\n"
            "💬 Просто напиши вопрос — отвечу про ИТМО, учёбу, общагу и т.д.\n\n"
            "📚 **Гостомысл** — поиск статей и ГОСТ-библиография:\n"
            '   Напиши что-то вроде "найди статьи про machine learning"\n\n'
            "🧠 **Выготский** — граф знаний и путь обучения:\n"
            '   Напиши "что изучить для вакансии ML Engineer"\n'
            '   Или "граф знаний: Data Science | знаю Python и статистику"\n\n'
            "🏠 **Вобщаге** — вобщаге.fun — интерактивная карта общаги!",
            parse_mode="Markdown",
        )

    async def _handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if not self._is_allowed(user):
            await update.message.reply_text("❌ Нет доступа.")
            return

        text = update.message.text
        session_id = f"tg_{user.id}"

        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

        try:
            result = await self.router.route(text, session_id=session_id)
            answer = result["answer"]
            if len(answer) > 4096:
                for i in range(0, len(answer), 4096):
                    await update.message.reply_text(answer[i : i + 4096])
            else:
                await update.message.reply_text(answer)
        except Exception as e:
            logger.error(f"Error handling message: {e}", exc_info=True)
            await update.message.reply_text("❌ Ой, что-то пошло не так. Попробуй ещё раз!")

    def run(self):
        logger.info("Starting ITMO GPT Telegram bot...")
        self.application.run_polling(drop_pending_updates=True)
