
from datetime import datetime

from sqlalchemy import (
    Column,
    Integer,
    BigInteger,
    String,
    Text,
    Boolean,
    DateTime,
    ForeignKey,
    Float,
    UniqueConstraint,
)

from bot.database.db import Base


class User(Base):
    __tablename__ = "users"

    telegram_id = Column(BigInteger, primary_key=True)
    username = Column(String(255))
    first_name = Column(String(255))
    language = Column(String(8), default="en")
    is_premium = Column(Boolean, default=False)
    premium_until = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Quiz(Base):
    __tablename__ = "quizzes"

    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    subject = Column(String(150), default="General")
    topic = Column(String(150), default="General")
    description = Column(Text, default="")
    mode_tag = Column(String(50), default="practice")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True)
    quiz_id = Column(Integer, ForeignKey("quizzes.id"), nullable=True)
    subject = Column(String(150), default="General")
    topic = Column(String(150), default="General")
    difficulty = Column(String(30), default="medium")
    year = Column(Integer, nullable=True)
    question_text = Column(Text, nullable=False)
    option_a = Column(Text, nullable=False)
    option_b = Column(Text, nullable=False)
    option_c = Column(Text, nullable=False)
    option_d = Column(Text, nullable=False)
    correct_option = Column(Integer, nullable=False)
    explanation = Column(Text, default="")
    source_reference = Column(Text, default="")
    fingerprint = Column(String(64), unique=True, nullable=True)
    is_approved = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Attempt(Base):
    __tablename__ = "attempts"

    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, nullable=False)
    quiz_id = Column(Integer, nullable=True)
    mode = Column(String(40), default="practice")
    score = Column(Integer, default=0)
    total = Column(Integer, default=0)
    correct = Column(Integer, default=0)
    incorrect = Column(Integer, default=0)
    accuracy = Column(Float, default=0)
    duration_seconds = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)


class UserAnswer(Base):
    __tablename__ = "user_answers"

    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, nullable=False)
    question_id = Column(
        Integer,
        ForeignKey("questions.id"),
        nullable=False,
    )
    selected_option = Column(Integer, nullable=False)
    is_correct = Column(Boolean, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint(
            "telegram_id",
            "question_id",
            "created_at",
            name="uq_answer_event",
        ),
    )


class Bookmark(Base):
    __tablename__ = "bookmarks"

    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, nullable=False)
    question_id = Column(
        Integer,
        ForeignKey("questions.id"),
        nullable=False,
    )
    created_at = Column(DateTime, default=datetime.utcnow)


class QuizSession(Base):
    __tablename__ = "quiz_sessions"

    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, nullable=False)
    quiz_id = Column(Integer, nullable=True)
    mode = Column(String(40), default="practice")
    question_ids = Column(Text, nullable=False)
    answers_json = Column(Text, default="{}")
    current_index = Column(Integer, default=0)
    started_at = Column(DateTime, default=datetime.utcnow)
    deadline_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)


class DraftQuestion(Base):
    __tablename__ = "draft_questions"

    id = Column(Integer, primary_key=True)
    title = Column(String(255), default="PDF Import")
    subject = Column(String(150), default="General")
    topic = Column(String(150), default="PDF Import")
    question_text = Column(Text, nullable=False)
    option_a = Column(Text, nullable=False)
    option_b = Column(Text, nullable=False)
    option_c = Column(Text, nullable=False)
    option_d = Column(Text, nullable=False)
    correct_option = Column(Integer, nullable=False)
    explanation = Column(Text, default="")
    source_reference = Column(Text, default="")
    fingerprint = Column(String(64))
    created_at = Column(DateTime, default=datetime.utcnow)


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, nullable=False)
    charge_id = Column(String(255), unique=True)
    currency = Column(String(10))
    amount = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
