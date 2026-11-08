import json, hashlib, random
from datetime import datetime, timedelta
from sqlalchemy import func, desc
from bot.database.db import SessionLocal
from bot.database.models import User, Quiz, Question, Attempt, UserAnswer, Bookmark, QuizSession

def fingerprint(prompt, options):
    raw = " ".join([prompt or "", *(options or [])]).casefold()
    return hashlib.sha256(" ".join(raw.split()).encode()).hexdigest()

def register_user(tg):
    with SessionLocal() as db:
        u=db.get(User,tg.id)
        if u is None: u=User(telegram_id=tg.id,username=tg.username,first_name=tg.first_name); db.add(u)
        else: u.username=tg.username; u.first_name=tg.first_name
        db.commit()

def set_language(uid, lang):
    with SessionLocal() as db:
        u=db.get(User,uid)
        if u: u.language=lang; db.commit()

def get_language(uid):
    with SessionLocal() as db:
        u=db.get(User,uid); return u.language if u else "en"

def is_premium(uid):
    with SessionLocal() as db:
        u=db.get(User,uid)
        if not u: return False
        if u.is_premium and u.premium_until and u.premium_until < datetime.utcnow():
            u.is_premium=False; db.commit()
        return bool(u.is_premium)

def grant_premium(uid, days):
    if isinstance(days, bool) or not isinstance(days, int) or days <= 0:
        raise ValueError("Premium duration must be a positive whole number of days.")
    if isinstance(uid, bool) or not isinstance(uid, int) or uid <= 0:
        raise ValueError("Telegram user ID must be a positive integer.")
    with SessionLocal() as db:
        u=db.get(User,uid)
        if not u: u=User(telegram_id=uid); db.add(u)
        start=max(datetime.utcnow(),u.premium_until or datetime.utcnow())
        u.is_premium=True; u.premium_until=start+timedelta(days=days); db.commit()

def revoke_premium(uid):
    with SessionLocal() as db:
        u=db.get(User,uid)
        if u: u.is_premium=False; u.premium_until=None; db.commit()

def create_quiz(title, subject="General", topic="General", mode_tag="practice"):
    with SessionLocal() as db:
        q=Quiz(title=title,subject=subject,topic=topic,mode_tag=mode_tag); db.add(q); db.commit(); db.refresh(q); return q.id



def cancel_quiz_creation(quiz_id):
    """Remove an empty quiz or deactivate it if questions were already saved."""
    if not quiz_id:
        return
    with SessionLocal() as db:
        quiz = db.get(Quiz, quiz_id)
        if not quiz:
            return
        has_questions = db.query(Question.id).filter_by(quiz_id=quiz_id).first()
        if has_questions:
            quiz.is_active = False
        else:
            db.delete(quiz)
        db.commit()

def add_question(prompt, options, correct, explanation="", subject="General", topic="General",
                 quiz_id=None, difficulty="medium", year=None, source="", approved=True):
    if len(options)!=4 or correct not in range(4): raise ValueError("Need four options and correct index 0-3.")
    fp=fingerprint(prompt,options)
    with SessionLocal() as db:
        if db.query(Question).filter_by(fingerprint=fp).first(): return False
        db.add(Question(quiz_id=quiz_id,question_text=prompt,option_a=options[0],option_b=options[1],
            option_c=options[2],option_d=options[3],correct_option=correct,explanation=explanation,
            subject=subject,topic=topic,difficulty=difficulty,year=year,source_reference=source,
            fingerprint=fp,is_approved=approved))
        db.commit(); return True

def get_question(qid):
    with SessionLocal() as db: return db.get(Question,qid)

def list_quizzes():
    with SessionLocal() as db:
        qs=db.query(Quiz).filter_by(is_active=True).order_by(Quiz.id.desc()).all()
        return [{"id":q.id,"title":q.title,"subject":q.subject,"topic":q.topic,
                 "count":db.query(Question).filter_by(quiz_id=q.id,is_approved=True).count()} for q in qs]

def question_ids(mode="random", subject=None, topic=None, count=10, uid=None, quiz_id=None):
    with SessionLocal() as db:
        query=db.query(Question.id).filter_by(is_approved=True)
        if quiz_id: query=query.filter(Question.quiz_id==quiz_id)
        if subject: query=query.filter(func.lower(Question.subject)==subject.lower())
        if topic: query=query.filter(func.lower(Question.topic)==topic.lower())
        if mode=="wrong" and uid:
            wrong=[x[0] for x in db.query(UserAnswer.question_id).filter_by(telegram_id=uid,is_correct=False).all()]
            query=query.filter(Question.id.in_(wrong or [-1]))
        if mode=="bookmarks" and uid:
            saved=[x[0] for x in db.query(Bookmark.question_id).filter_by(telegram_id=uid).all()]
            query=query.filter(Question.id.in_(saved or [-1]))
        ids=[x[0] for x in query.all()]
        if mode in ("random","daily","practice","timed","mock","previous_year"): random.Random(datetime.utcnow().date().isoformat() if mode=="daily" else None).shuffle(ids)
        return ids[:count]

def save_answer(uid,qid,choice):
    q=get_question(qid)
    if not q: return None
    correct=(choice==q.correct_option)
    with SessionLocal() as db:
        db.add(UserAnswer(telegram_id=uid,question_id=qid,selected_option=choice,is_correct=correct)); db.commit()
    return correct

def toggle_bookmark(uid,qid):
    with SessionLocal() as db:
        b=db.query(Bookmark).filter_by(telegram_id=uid,question_id=qid).first()
        if b: db.delete(b); saved=False
        else: db.add(Bookmark(telegram_id=uid,question_id=qid)); saved=True
        db.commit(); return saved

def is_bookmarked(uid,qid):
    with SessionLocal() as db: return db.query(Bookmark).filter_by(telegram_id=uid,question_id=qid).first() is not None

def save_attempt(uid,mode,score,total,duration,quiz_id=None):
    with SessionLocal() as db:
        db.add(Attempt(telegram_id=uid,quiz_id=quiz_id,mode=mode,score=score,total=total,
            correct=score,incorrect=total-score,accuracy=(score/total*100 if total else 0),duration_seconds=duration)); db.commit()

def leaderboard(period="all"):
    with SessionLocal() as db:
        q=db.query(Attempt.telegram_id,func.sum(Attempt.score).label("points"))
        if period=="daily": q=q.filter(Attempt.created_at>=datetime.utcnow()-timedelta(days=1))
        elif period=="weekly": q=q.filter(Attempt.created_at>=datetime.utcnow()-timedelta(days=7))
        elif period=="monthly": q=q.filter(Attempt.created_at>=datetime.utcnow()-timedelta(days=30))
        return q.group_by(Attempt.telegram_id).order_by(desc("points")).limit(10).all()

def stats():
    with SessionLocal() as db:
        return {"users":db.query(User).count(),"quizzes":db.query(Quiz).count(),
                "questions":db.query(Question).count(),"attempts":db.query(Attempt).count(),
                "drafts":db.query(__import__("bot.database.models",fromlist=["DraftQuestion"]).DraftQuestion).count()}

def user_history(uid):
    with SessionLocal() as db:
        return db.query(Attempt).filter_by(telegram_id=uid).order_by(Attempt.created_at.desc()).limit(10).all()

def save_session(uid,mode,ids,quiz_id=None,minutes=None):
    with SessionLocal() as db:
        s=db.query(QuizSession).filter_by(telegram_id=uid,is_active=True).first()
        if s: s.is_active=False
        deadline=datetime.utcnow()+timedelta(minutes=minutes) if minutes else None
        s=QuizSession(telegram_id=uid,mode=mode,quiz_id=quiz_id,question_ids=json.dumps(ids),
                      answers_json="{}",current_index=0,deadline_at=deadline)
        db.add(s); db.commit(); db.refresh(s); return s.id

def active_session(uid):
    with SessionLocal() as db:
        s=db.query(QuizSession).filter_by(telegram_id=uid,is_active=True).order_by(QuizSession.id.desc()).first()
        if not s: return None
        return {"id":s.id,"mode":s.mode,"quiz_id":s.quiz_id,"ids":json.loads(s.question_ids),
                "answers":json.loads(s.answers_json or "{}"),"index":s.current_index,
                "started":s.started_at,"deadline":s.deadline_at}

def update_session(uid, sid, answers, index):
    with SessionLocal() as db:
        s=db.get(QuizSession,sid)
        if s and s.telegram_id==uid and s.is_active:
            s.answers_json=json.dumps(answers); s.current_index=index; db.commit()

def close_session(uid,sid):
    with SessionLocal() as db:
        s=db.get(QuizSession,sid)
        if s and s.telegram_id==uid: s.is_active=False; db.commit()

def subjects_topics():
    with SessionLocal() as db:
        subjects=[x[0] for x in db.query(Question.subject).filter_by(is_approved=True).distinct().all()]
        topics=[x[0] for x in db.query(Question.topic).filter_by(is_approved=True).distinct().all()]
        return sorted(set(subjects)),sorted(set(topics))
