
import logging
import os

from aiohttp import web

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    PreCheckoutQueryHandler,
    filters,
)

from bot.config import BOT_TOKEN
from bot.database.db import init_db

from bot.handlers.user import *

from bot.handlers.admin import (
    panel,
    stats_cb,
    create_start,
    title_in,
    subject_in,
    topic_in,
    qtext_in,
    opt_a,
    opt_b,
    opt_c,
    opt_d,
    answer_in,
    expl_in,
    done,
    cancel,
    pdf_prompt,
    pdf_upload,
    channel_pdf,
    drafts_cb,
    draft_action,
    broadcast_prompt,
    broadcast_message,
    premium_prompt,
    premium_command,
    premium_input,
    TITLE,
    SUBJECT,
    TOPIC,
    QTEXT,
    OA,
    OB,
    OC,
    OD,
    ANS,
    EXPL,
)

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

logger = logging.getLogger(__name__)

BOT = None
WEBHOOK_PATH = "/telegram"


# Error handler
async def error_handler(update, context):
    logger.error(
        "Update failed",
        exc_info=context.error,
    )


# Build Telegram application
def build_app():

    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN is not configured.")

    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .concurrent_updates(False)
        .build()
    )

    # Quiz creation conversation
    conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(
                create_start,
                pattern=r"^ad:createquiz$",
            )
        ],
        states={
            TITLE: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    title_in,
                )
            ],
            SUBJECT: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    subject_in,
                )
            ],
            TOPIC: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    topic_in,
                )
            ],
            QTEXT: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    qtext_in,
                )
            ],
            OA: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    opt_a,
                )
            ],
            OB: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    opt_b,
                )
            ],
            OC: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    opt_c,
                )
            ],
            OD: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    opt_d,
                )
            ],
            ANS: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    answer_in,
                )
            ],
            EXPL: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    expl_in,
                )
            ],
        },
        fallbacks=[
            CommandHandler("done", done),
            CommandHandler("cancel", cancel),
        ],
        allow_reentry=True,
    )

    # Main commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", panel))
    app.add_handler(CommandHandler("premium", premium_command))

    app.add_handler(conv)

    # Premium management conversation
    premium_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(
                premium_prompt,
                pattern=r"^ad:(grant|revoke)$",
            )
        ],
        states={
            1: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    premium_input,
                )
            ]
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
        ],
        allow_reentry=True,
    )

    app.add_handler(premium_conv)

    # Channel PDF uploads
    app.add_handler(
        MessageHandler(
            filters.ChatType.CHANNEL & filters.Document.PDF,
            channel_pdf,
        )
    )

    # Private PDF uploads
    app.add_handler(
        MessageHandler(
            filters.ChatType.PRIVATE & filters.Document.PDF,
            pdf_upload,
        )
    )

    # Payments
    app.add_handler(
        PreCheckoutQueryHandler(precheckout)
    )

    app.add_handler(
        MessageHandler(
            filters.SUCCESSFUL_PAYMENT,
            successful_payment,
        )
    )

    # General text messages
    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            broadcast_message,
        )
    )

    # User navigation
    app.add_handler(
        CallbackQueryHandler(home_cb, pattern=r"^home$")
    )

    app.add_handler(
        CallbackQueryHandler(modes_cb, pattern=r"^modes$")
    )

    app.add_handler(
        CallbackQueryHandler(subjects_cb, pattern=r"^subjects$")
    )

    app.add_handler(
        CallbackQueryHandler(topics_cb, pattern=r"^topics$")
    )

    app.add_handler(
        CallbackQueryHandler(
            select_mode,
            pattern=r"^mode:[a-z_]+$",
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            select_subject,
            pattern=r"^subject:.+$",
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            select_topic,
            pattern=r"^topic:.+$",
        )
    )

    app.add_handler(
        CallbackQueryHandler(resume_cb, pattern=r"^resume$")
    )

    app.add_handler(
        CallbackQueryHandler(
            answer_cb,
            pattern=r"^ans:\d+:[0-3]$",
        )
    )

    app.add_handler(
        CallbackQueryHandler(next_cb, pattern=r"^next$")
    )

    app.add_handler(
        CallbackQueryHandler(finish_cb, pattern=r"^finish$")
    )

    app.add_handler(
        CallbackQueryHandler(
            bookmark_cb,
            pattern=r"^bm:\d+$",
        )
    )

    app.add_handler(
        CallbackQueryHandler(history_cb, pattern=r"^history$")
    )

    app.add_handler(
        CallbackQueryHandler(
            leaderboard_cb,
            pattern=r"^lb:(daily|weekly|monthly|all)$",
        )
    )

    app.add_handler(
        CallbackQueryHandler(language_cb, pattern=r"^language$")
    )

    app.add_handler(
        CallbackQueryHandler(
            set_language_cb,
            pattern=r"^lang:(en|ml)$",
        )
    )

    app.add_handler(
        CallbackQueryHandler(help_cb, pattern=r"^help$")
    )

    app.add_handler(
        CallbackQueryHandler(premium_cb, pattern=r"^premium$")
    )

    # Admin navigation
    app.add_handler(
        CallbackQueryHandler(panel, pattern=r"^admin$")
    )

    app.add_handler(
        CallbackQueryHandler(stats_cb, pattern=r"^ad:stats$")
    )

    app.add_handler(
        CallbackQueryHandler(pdf_prompt, pattern=r"^ad:pdf$")
    )

    app.add_handler(
        CallbackQueryHandler(drafts_cb, pattern=r"^ad:drafts$")
    )

    app.add_handler(
        CallbackQueryHandler(
            draft_action,
            pattern=r"^draft:(yes|no):\d+$",
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            broadcast_prompt,
            pattern=r"^ad:broadcast$",
        )
    )

    # Error handler
    app.add_error_handler(error_handler)

    return app


# Health check
async def health(request):
    return web.json_response({
        "status": "ok",
        "service": "PSCGram QuizBot",
    })


# Telegram webhook endpoint
async def telegram_webhook(request):

    if BOT is None:
        raise web.HTTPServiceUnavailable(
            text="Telegram application is not ready"
        )

    secret = os.getenv("WEBHOOK_SECRET", "")

    if not secret:
        raise web.HTTPServiceUnavailable(
            text="Webhook secret not configured"
        )

    if request.headers.get(
        "X-Telegram-Bot-Api-Secret-Token"
    ) != secret:
        raise web.HTTPForbidden(
            text="Invalid secret"
        )

    try:
        data = await request.json()

        update = Update.de_json(
            data,
            BOT.bot,
        )

        await BOT.update_queue.put(update)

        return web.Response(text="OK")

    except Exception:
        logger.exception(
            "Webhook processing failed"
        )

        raise web.HTTPBadRequest(
            text="Invalid update"
        )


# Startup
async def on_startup(server):

    global BOT

    hostname = os.getenv(
        "RENDER_EXTERNAL_HOSTNAME"
    )

    secret = os.getenv(
        "WEBHOOK_SECRET",
        "",
    )

    if not hostname:
        raise RuntimeError(
            "RENDER_EXTERNAL_HOSTNAME is missing."
        )

    if not secret:
        raise RuntimeError(
            "WEBHOOK_SECRET is missing."
        )

    init_db()

    BOT = build_app()

    await BOT.initialize()

    await BOT.start()

    webhook_url = (
        f"https://{hostname}{WEBHOOK_PATH}"
    )

    await BOT.bot.set_webhook(
        url=webhook_url,
        secret_token=secret,
        allowed_updates=Update.ALL_TYPES,
    )

    logger.info(
        "PSCGram webhook started: %s",
        webhook_url,
    )


# Shutdown
async def on_shutdown(server):

    global BOT

    if BOT is not None:

        app = BOT
        BOT = None

        try:
            await app.stop()

        finally:
            await app.shutdown()

        logger.info(
            "Telegram application stopped safely."
        )


# Create web application
def create_web_app():

    server = web.Application(
        client_max_size=20 * 1024 * 1024
    )

    server.router.add_get("/", health)

    server.router.add_get(
        "/health",
        health,
    )

    server.router.add_post(
        WEBHOOK_PATH,
        telegram_webhook,
    )

    server.on_startup.append(on_startup)

    server.on_shutdown.append(on_shutdown)

    return server
