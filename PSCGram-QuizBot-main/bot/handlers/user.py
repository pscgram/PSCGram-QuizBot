import time
from datetime import datetime
from telegram import Update,InlineKeyboardMarkup,InlineKeyboardButton,LabeledPrice
from telegram.ext import ContextTypes
from bot.config import ADMIN_IDS,DEFAULT_QUIZ_QUESTIONS,DEFAULT_TEST_MINUTES,PREMIUM_CURRENCY,PREMIUM_PRICE_STARS
from bot.keyboards.inline import home,modes,list_buttons,answer_buttons,next_button
from bot.services import quiz_service as svc

LANG={"en":{"welcome":"Welcome to PSCGram QuizBot!","choose":"Choose a quiz mode:"},
      "ml":{"welcome":"PSCGram QuizBot-ലേക്ക് സ്വാഗതം!","choose":"ക്വിസ് മോഡ് തിരഞ്ഞെടുക്കുക:"}}

def is_admin(uid): return uid in ADMIN_IDS
def getrun(ctx): return ctx.user_data.setdefault("run",{})

async def start(update:Update,context:ContextTypes.DEFAULT_TYPE):
    svc.register_user(update.effective_user)
    await update.message.reply_text(LANG[svc.get_language(update.effective_user.id)]["welcome"],
      reply_markup=home(is_admin(update.effective_user.id),svc.is_premium(update.effective_user.id)))

async def home_cb(update,context):
    q=update.callback_query; await q.answer()
    await q.edit_message_text("PSCGram QuizBot",reply_markup=home(is_admin(q.from_user.id),svc.is_premium(q.from_user.id)))

async def modes_cb(update,context):
    q=update.callback_query; await q.answer()
    await q.edit_message_text(LANG[svc.get_language(q.from_user.id)]["choose"],reply_markup=modes())

async def subjects_cb(update,context):
    q=update.callback_query; await q.answer()
    subs,_=svc.subjects_topics()
    await q.edit_message_text("Choose a subject:",reply_markup=list_buttons(subs,"subject"))

async def topics_cb(update,context):
    q=update.callback_query; await q.answer()
    _,topics=svc.subjects_topics()
    await q.edit_message_text("Choose a topic:",reply_markup=list_buttons(topics,"topic"))

async def select_mode(update,context):
    q=update.callback_query; await q.answer()
    mode=q.data.split(":",1)[1]
    if mode in ("mock","timed") and not svc.is_premium(q.from_user.id) and mode=="mock":
        await q.edit_message_text("Full Mock Test is a Premium feature. Tap Premium on the main menu."); return
    ids=svc.question_ids(mode,count=DEFAULT_QUIZ_QUESTIONS,uid=q.from_user.id)
    if not ids: await q.edit_message_text("No questions found for this mode yet."); return
    minutes=DEFAULT_TEST_MINUTES if mode=="timed" else (60 if mode=="mock" else None)
    sid=svc.save_session(q.from_user.id,mode,ids,minutes=minutes)
    getrun(context).update({"sid":sid,"mode":mode,"ids":ids,"answers":{},"index":0,
                            "started":time.time(),"deadline":time.time()+minutes*60 if minutes else None})
    await show_question(q,context)

async def select_subject(update,context):
    q=update.callback_query; await q.answer(); subject=q.data.split(":",1)[1]
    ids=svc.question_ids("subject",subject=subject,count=DEFAULT_QUIZ_QUESTIONS,uid=q.from_user.id)
    if not ids: await q.edit_message_text("No questions in this subject."); return
    sid=svc.save_session(q.from_user.id,"subject",ids)
    getrun(context).update({"sid":sid,"mode":"subject","ids":ids,"answers":{},"index":0,"started":time.time()})
    await show_question(q,context)

async def select_topic(update,context):
    q=update.callback_query; await q.answer(); topic=q.data.split(":",1)[1]
    ids=svc.question_ids("topic",topic=topic,count=DEFAULT_QUIZ_QUESTIONS,uid=q.from_user.id)
    if not ids: await q.edit_message_text("No questions in this topic."); return
    sid=svc.save_session(q.from_user.id,"topic",ids)
    getrun(context).update({"sid":sid,"mode":"topic","ids":ids,"answers":{},"index":0,"started":time.time()})
    await show_question(q,context)

async def resume_cb(update,context):
    q=update.callback_query; await q.answer(); data=svc.active_session(q.from_user.id)
    if not data: await q.edit_message_text("No active quiz to resume."); return
    getrun(context).update({"sid":data["id"],"mode":data["mode"],"ids":data["ids"],"answers":data["answers"],
                            "index":data["index"],
                            "started":data["started"].timestamp() if data.get("started") else time.time(),
                            "deadline":data.get("deadline").timestamp() if data.get("deadline") else None})
    await show_question(q,context)

async def show_question(q,context):
    r=getrun(context); idx=r["index"]
    if r.get("deadline") and time.time() >= r["deadline"]:
        await finish_quiz(q,context)
        return
    if idx>=len(r["ids"]): await finish_quiz(q,context); return
    item=svc.get_question(r["ids"][idx])
    if not item: r["index"]+=1; await show_question(q,context); return
    opts=[item.option_a,item.option_b,item.option_c,item.option_d]
    deadline=""
    if r["mode"]=="timed":
        deadline="\n⏱ Timed test: 15-minute limit."
    saved=svc.is_bookmarked(q.from_user.id,item.id)
    await q.edit_message_text(f"{r['mode'].replace('_',' ').title()} · {idx+1}/{len(r['ids'])}"+
       f"\n\n{item.question_text}"+deadline,reply_markup=answer_buttons(item.id,opts,saved))

async def answer_cb(update,context):
    q=update.callback_query; r=getrun(context)
    if not r or not r.get("sid"):
        await q.answer("No active quiz. Start a new quiz.", show_alert=True)
        return
    if r.get("deadline") and time.time() >= r["deadline"]:
        await q.answer("Time is over.", show_alert=True)
        await finish_quiz(q,context)
        return
    _,qid,choice=q.data.split(":"); qid=int(qid); choice=int(choice)
    key=str(qid)
    if key in r.get("answers",{}): await q.answer("Already answered."); return
    item=svc.get_question(qid)
    if not item: await q.answer("Question unavailable."); return
    correct=svc.save_answer(q.from_user.id,qid,choice)
    r["answers"][key]={"choice":choice,"correct":bool(correct)}
    svc.update_session(q.from_user.id,r["sid"],r["answers"],r["index"])
    await q.answer("Answer recorded.")
    opts=[item.option_a,item.option_b,item.option_c,item.option_d]
    lines=[f"{'🟢' if i==item.correct_option else ('🔴' if i==choice else '⚪')} {'ABCD'[i]}. {v}" for i,v in enumerate(opts)]
    text = (("✅ Correct!" if correct else f"❌ Incorrect. Correct answer: {'ABCD'[item.correct_option]}")
            + "\n\n" + "\n".join(lines) + "\n\n" + (item.explanation or "Explanation not provided."))
    await q.edit_message_text(text,reply_markup=next_button())

async def next_cb(update,context):
    q=update.callback_query; r=getrun(context)
    if not r or not r.get("sid"):
        await q.answer("No active quiz.", show_alert=True)
        return
    await q.answer()
    r["index"]+=1; svc.update_session(q.from_user.id,r["sid"],r["answers"],r["index"])
    await show_question(q,context)

async def bookmark_cb(update,context):
    q=update.callback_query; await q.answer()
    saved=svc.toggle_bookmark(q.from_user.id,int(q.data.split(":")[1]))
    await q.answer("Bookmark saved." if saved else "Bookmark removed.")

async def finish_quiz(q,context):
    r=getrun(context); total=len(r["ids"]); correct=sum(1 for a in r["answers"].values() if a["correct"])
    incorrect=sum(1 for a in r["answers"].values() if not a["correct"])
    duration=max(0,int(time.time()-r.get("started",time.time())))
    svc.save_attempt(q.from_user.id,r["mode"],correct,total,duration)
    svc.close_session(q.from_user.id,r["sid"])
    accuracy=correct/total*100 if total else 0
    await q.edit_message_text(f"🏁 Quiz completed!\nCorrect: {correct}\nIncorrect: {incorrect}"+
       f"\nUnanswered: {total-correct-incorrect}\nAccuracy: {accuracy:.1f}%\nTime: {duration//60}m {duration%60}s",
       reply_markup=home(is_admin(q.from_user.id),svc.is_premium(q.from_user.id)))
    context.user_data.pop("run", None)

async def finish_cb(update,context):
    q=update.callback_query
    if not getrun(context).get("sid"):
        await q.answer("No active quiz.", show_alert=True)
        return
    await q.answer()
    await finish_quiz(q,context)

async def history_cb(update,context):
    q=update.callback_query; await q.answer(); rows=svc.user_history(q.from_user.id)
    text="📊 Recent results\n\n"+("\n".join(f"{x.mode}: {x.score}/{x.total} · {x.accuracy:.0f}% · {x.created_at:%d %b}" for x in rows) or "No quiz history yet.")
    await q.edit_message_text(text,reply_markup=home(is_admin(q.from_user.id)))

async def leaderboard_cb(update,context):
    q=update.callback_query; await q.answer(); period=q.data.split(":")[1]
    rows=svc.leaderboard(period)
    text=f"🏆 {period.title()} leaderboard\n\n"+("\n".join(f"{i}. User {uid}: {int(points or 0)}" for i,(uid,points) in enumerate(rows,1)) or "No scores yet.")
    kb=InlineKeyboardMarkup([[InlineKeyboardButton("Daily",callback_data="lb:daily"),InlineKeyboardButton("Weekly",callback_data="lb:weekly")],
       [InlineKeyboardButton("Monthly",callback_data="lb:monthly"),InlineKeyboardButton("All time",callback_data="lb:all")]])
    await q.edit_message_text(text,reply_markup=kb)

async def language_cb(update,context):
    q=update.callback_query; await q.answer()
    kb=InlineKeyboardMarkup([[InlineKeyboardButton("English",callback_data="lang:en"),
       InlineKeyboardButton("മലയാളം",callback_data="lang:ml")]])
    await q.edit_message_text("Choose language / ഭാഷ തിരഞ്ഞെടുക്കുക",reply_markup=kb)

async def set_language_cb(update,context):
    q=update.callback_query; await q.answer(); lang=q.data.split(":")[1]
    svc.set_language(q.from_user.id,lang); await q.edit_message_text("Language updated.",reply_markup=home(is_admin(q.from_user.id)))

async def premium_cb(update,context):
    q=update.callback_query; await q.answer()
    await context.bot.send_invoice(chat_id=q.from_user.id,title="PSCGram Premium",description="30 days of PSCGram Premium access",
       payload=f"pscgram-premium:{q.from_user.id}",currency=PREMIUM_CURRENCY,
       prices=[LabeledPrice("30 days Premium", PREMIUM_PRICE_STARS)],provider_token="")
    await q.edit_message_text("Premium payment invoice sent in the chat.")

async def precheckout(update,context):
    query = update.pre_checkout_query
    expected_payload = f"pscgram-premium:{query.from_user.id}"
    if (query.invoice_payload != expected_payload
            or query.currency != PREMIUM_CURRENCY
            or query.total_amount != PREMIUM_PRICE_STARS):
        await query.answer(ok=False, error_message="Payment details could not be verified.")
        return
    await query.answer(ok=True)


async def successful_payment(update,context):
    from bot.database.db import SessionLocal
    from bot.database.models import Payment
    p = update.effective_message.successful_payment
    uid = update.effective_user.id
    expected_payload = f"pscgram-premium:{uid}"
    if (p.invoice_payload != expected_payload
            or p.currency != PREMIUM_CURRENCY
            or p.total_amount != PREMIUM_PRICE_STARS):
        await update.effective_message.reply_text(
            "Payment received, but its details could not be verified. Please contact an administrator."
        )
        return

    with SessionLocal() as db:
        existing = db.query(Payment).filter_by(
            charge_id=p.telegram_payment_charge_id
        ).first()
        if existing:
            await update.effective_message.reply_text("This payment has already been processed.")
            return
        db.add(Payment(
            telegram_id=uid,
            charge_id=p.telegram_payment_charge_id,
            currency=p.currency,
            amount=p.total_amount
        ))
        db.commit()

    svc.grant_premium(uid, 30)
    await update.effective_message.reply_text("⭐ Premium activated for 30 days!")


async def help_cb(update,context):
    q=update.callback_query; await q.answer()
    await q.edit_message_text("Select a quiz mode. Choose one of four answers; it locks immediately. Use bookmarks to save questions and My Progress to see history.")
