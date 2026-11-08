from datetime import datetime
from telegram import Update,InlineKeyboardMarkup,InlineKeyboardButton,LabeledPrice
from telegram.ext import ContextTypes,ConversationHandler,MessageHandler,CommandHandler,filters
from bot.config import ADMIN_IDS
from bot.keyboards.inline import admin as admin_keyboard
from bot.database.db import SessionLocal
from bot.database.models import DraftQuestion,Quiz,Question,User
from bot.services.quiz_service import (
    create_quiz, add_question, stats, grant_premium, revoke_premium,
    cancel_quiz_creation,
)
from bot.services.pdf_service import extract_pdf_text,chunk_text
from bot.services.ai_service import make_questions

def allowed(uid): return uid in ADMIN_IDS
TITLE,SUBJECT,TOPIC,QTEXT,OA,OB,OC,OD,ANS,EXPL=range(10)

async def panel(update,context):
    q = update.callback_query
    user = update.effective_user
    if not allowed(user.id):
        if q:
            await q.answer("Not authorized.", show_alert=True)
        elif update.effective_message:
            await update.effective_message.reply_text("Not authorized.")
        return
    if q:
        await q.answer()
        await q.edit_message_text("PSCGram Admin Dashboard", reply_markup=admin_keyboard())
    else:
        await update.effective_message.reply_text("PSCGram Admin Dashboard", reply_markup=admin_keyboard())

async def stats_cb(update,context):
    q=update.callback_query; await q.answer()
    if not allowed(q.from_user.id): return
    s=stats(); await q.edit_message_text("\n".join(f"{k.title()}: {v}" for k,v in s.items()),reply_markup=admin_keyboard())

async def create_start(update,context):
    q=update.callback_query; await q.answer()
    if not allowed(q.from_user.id): return ConversationHandler.END
    await q.edit_message_text("Send quiz title:"); return TITLE
async def title_in(update,context):
    context.user_data["newquiz"]={"title":update.message.text.strip()}
    await update.message.reply_text("Send subject:"); return SUBJECT
async def subject_in(update,context):
    context.user_data["newquiz"]["subject"]=update.message.text.strip()
    await update.message.reply_text("Send topic:"); return TOPIC
async def topic_in(update,context):
    d=context.user_data["newquiz"]; d["topic"]=update.message.text.strip()
    d["id"]=create_quiz(d["title"],d["subject"],d["topic"])
    await update.message.reply_text(f"Quiz created (ID {d['id']}). Use /cancel to stop or send /done to finish. Send question text:")
    return QTEXT
async def qtext_in(update,context):
    context.user_data["newq"]={"prompt":update.message.text.strip()}
    await update.message.reply_text("Option A:"); return OA
async def opt_a(update,context):
    context.user_data["newq"]["opts"]=[update.message.text.strip()]
    await update.message.reply_text("Option B:"); return OB
async def opt_b(update,context):
    context.user_data["newq"]["opts"].append(update.message.text.strip())
    await update.message.reply_text("Option C:"); return OC
async def opt_c(update,context):
    context.user_data["newq"]["opts"].append(update.message.text.strip())
    await update.message.reply_text("Option D:"); return OD
async def opt_d(update,context):
    context.user_data["newq"]["opts"].append(update.message.text.strip())
    await update.message.reply_text("Correct option A/B/C/D:"); return ANS
async def answer_in(update,context):
    v=update.message.text.strip().upper()
    if v not in "ABCD" or len(v)!=1: await update.message.reply_text("Reply A, B, C or D."); return ANS
    context.user_data["newq"]["answer"]="ABCD".index(v)
    await update.message.reply_text("Explanation (or -):"); return EXPL
async def expl_in(update,context):
    d=context.user_data["newq"]; quiz=context.user_data["newquiz"]
    add_question(d["prompt"],d["opts"],d["answer"],"" if update.message.text.strip()=="-" else update.message.text.strip(),
                 subject=quiz["subject"],topic=quiz["topic"],quiz_id=quiz["id"])
    await update.message.reply_text("Question saved. Send next question, or /done.")
    return QTEXT
async def done(update,context):
    context.user_data.pop("newquiz", None)
    context.user_data.pop("newq", None)
    await update.message.reply_text("Finished.")
    return ConversationHandler.END

async def cancel(update,context):
    # A quiz row is created before its questions; remove the empty/incomplete
    # quiz on cancellation so it does not remain in the catalogue.
    draft = context.user_data.pop("newquiz", None)
    context.user_data.pop("newq", None)
    context.user_data.pop("waiting_pdf", None)
    context.user_data.pop("premium_action", None)
    context.user_data.pop("broadcast_wait", None)
    if draft and draft.get("id"):
        cancel_quiz_creation(draft["id"])
    await update.effective_message.reply_text("Cancelled. Temporary quiz-creation data was cleared.")
    return ConversationHandler.END

async def pdf_prompt(update,context):
    q=update.callback_query; await q.answer()
    if not allowed(q.from_user.id): return
    context.user_data["waiting_pdf"]=True
    await q.edit_message_text("Upload a PDF file here. Extracted MCQs will be drafts for admin review.")
async def process_pdf(bot,chat_id,file_id,filename):
    tgfile=await bot.get_file(file_id); data=bytes(await tgfile.download_as_bytearray())
    text=extract_pdf_text(data); count=0
    for chunk in chunk_text(text):
        for item in make_questions(chunk,8):
            with SessionLocal() as db:
                db.add(DraftQuestion(title=filename[:250],subject=item["subject"],topic=item["topic"],
                  question_text=item["question"],option_a=item["options"][0],option_b=item["options"][1],
                  option_c=item["options"][2],option_d=item["options"][3],correct_option=item["answer"],
                  explanation=item["explanation"],source_reference=item["source"]))
                db.commit()
            count+=1
    await bot.send_message(chat_id,f"PDF processed. {count} draft questions created. Review them in Admin Dashboard.")
async def pdf_upload(update,context):
    if not allowed(update.effective_user.id) or not context.user_data.get("waiting_pdf"): return
    context.user_data["waiting_pdf"]=False
    doc=update.message.document
    if not doc or not (doc.file_name or "").lower().endswith(".pdf"):
        await update.message.reply_text("Please send a PDF document."); return
    if doc.file_size and doc.file_size>20*1024*1024:
        await update.message.reply_text("PDF must be 20 MB or smaller."); return
    try: await process_pdf(context.bot,update.effective_chat.id,doc.file_id,doc.file_name or "PDF Import")
    except Exception as e: await update.message.reply_text(f"PDF processing failed: {e}")

async def channel_pdf(update,context):
    doc=update.channel_post.document if update.channel_post else None
    if not doc or not (doc.file_name or "").lower().endswith(".pdf"): return
    configured=__import__("bot.config",fromlist=["PDF_CHANNEL_ID"]).PDF_CHANNEL_ID
    if configured and str(update.channel_post.chat_id)!=configured: return
    try:
        await process_pdf(context.bot,update.channel_post.chat_id,doc.file_id,doc.file_name or "Channel PDF")
    except Exception as e:
        await context.bot.send_message(chat_id=update.channel_post.chat_id,text=f"PSCGram PDF ingestion failed: {e}")

async def drafts_cb(update,context):
    q=update.callback_query; await q.answer()
    if not allowed(q.from_user.id): return
    with SessionLocal() as db:
        d=db.query(DraftQuestion).order_by(DraftQuestion.id).first()
        if not d: await q.edit_message_text("No pending drafts.",reply_markup=admin_keyboard()); return
        did=d.id
        text=f"Draft #{d.id}\n{d.question_text}\n\nA. {d.option_a}\nB. {d.option_b}\nC. {d.option_c}\nD. {d.option_d}\nCorrect: {'ABCD'[d.correct_option]}\nExplanation: {d.explanation}\nSource: {d.source_reference}"
    kb=InlineKeyboardMarkup([[InlineKeyboardButton("Approve",callback_data=f"draft:yes:{did}"),
       InlineKeyboardButton("Reject",callback_data=f"draft:no:{did}")],
       [InlineKeyboardButton("Next draft",callback_data="ad:drafts")]])
    await q.edit_message_text(text,reply_markup=kb)
async def draft_action(update,context):
    q=update.callback_query; await q.answer()
    if not allowed(q.from_user.id): return
    _,action,raw=q.data.split(":"); did=int(raw)
    with SessionLocal() as db:
        d=db.get(DraftQuestion,did)
        if not d: await q.edit_message_text("Draft not found."); return
        if action=="yes":
            add_question(d.question_text,[d.option_a,d.option_b,d.option_c,d.option_d],d.correct_option,
              d.explanation,subject=d.subject,topic=d.topic,source=d.source_reference)
        db.delete(d); db.commit()
    await q.edit_message_text("Draft "+("approved." if action=="yes" else "rejected."),reply_markup=admin_keyboard())

async def broadcast_prompt(update,context):
    q=update.callback_query; await q.answer()
    if not allowed(q.from_user.id): return
    context.user_data["broadcast_wait"]=True
    await q.edit_message_text("Send the broadcast message. It will be sent to all registered users.")
async def broadcast_message(update,context):
    if not allowed(update.effective_user.id) or not context.user_data.get("broadcast_wait"): return
    context.user_data["broadcast_wait"]=False
    with SessionLocal() as db: ids=[x[0] for x in db.query(User.telegram_id).all()]
    sent=0
    for uid in ids:
        try: await context.bot.send_message(uid,update.message.text); sent+=1
        except Exception: pass
    await update.message.reply_text(f"Broadcast delivered to {sent}/{len(ids)} users.")

async def premium_prompt(update,context):
    q=update.callback_query; await q.answer()
    if not allowed(q.from_user.id): return
    context.user_data["premium_action"]="grant" if "grant" in q.data else "revoke"
    prompt = ("Send: TELEGRAM_USER_ID DAYS" if context.user_data["premium_action"] == "grant"
              else "Send: TELEGRAM_USER_ID")
    await q.edit_message_text(prompt + ". Use /cancel to stop.")
    return 1
async def premium_command(update, context):
    if not allowed(update.effective_user.id):
        await update.effective_message.reply_text("Not authorized.")
        return
    args = context.args or []
    try:
        if len(args) == 3 and args[0].lower() == "grant":
            uid, days = int(args[1]), int(args[2])
            if uid <= 0 or days <= 0:
                raise ValueError
            grant_premium(uid, days)
        elif len(args) == 2 and args[0].lower() == "revoke":
            uid = int(args[1])
            if uid <= 0:
                raise ValueError
            revoke_premium(uid)
        else:
            await update.effective_message.reply_text(
                "Usage: /premium grant USER_ID DAYS or /premium revoke USER_ID"
            )
            return
        await update.effective_message.reply_text("Premium access updated.")
    except (ValueError, TypeError):
        await update.effective_message.reply_text(
            "Invalid user ID or duration. Use a positive numeric ID and days."
        )


async def premium_input(update, context):
    if not allowed(update.effective_user.id):
        return ConversationHandler.END
    action = context.user_data.get("premium_action")
    parts = (update.effective_message.text or "").split()
    try:
        expected = 2 if action == "grant" else 1
        if action not in ("grant", "revoke") or len(parts) != expected:
            raise ValueError
        uid = int(parts[0])
        if uid <= 0:
            raise ValueError
        if action == "grant":
            days = int(parts[1])
            if days <= 0:
                raise ValueError
            grant_premium(uid, days)
        else:
            revoke_premium(uid)
        await update.effective_message.reply_text("Premium access updated.")
        context.user_data.pop("premium_action", None)
        return ConversationHandler.END
    except (ValueError, TypeError):
        await update.effective_message.reply_text(
            "Invalid format. Send USER_ID DAYS for grant, or USER_ID for revoke. "
            "Use /cancel to stop."
        )
        return 1
