
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

from bot.config import DATABASE_URL


# Fix PostgreSQL URL for SQLAlchemy 2.x
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace(
        "postgres://",
        "postgresql+psycopg://",
        1,
    )

elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace(
        "postgresql://",
        "postgresql+psycopg://",
        1,
    )


# Database connection
connect_args = (
    {"check_same_thread": False}
    if DATABASE_URL.startswith("sqlite")
    else {}
)

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)

Base = declarative_base()


# Initialize database and migrate Telegram IDs
def init_db():

    from bot.database import models

    # Create missing tables
    Base.metadata.create_all(bind=engine)

    # PostgreSQL migration
    if engine.dialect.name == "postgresql":

        tables = [
            "users",
            "attempts",
            "user_answers",
            "bookmarks",
            "quiz_sessions",
            "payments",
        ]

        with engine.begin() as connection:

            for table in tables:

                connection.execute(
                    text(
                        f"""
                        ALTER TABLE {table}
                        ALTER COLUMN telegram_id
                        TYPE BIGINT
                        USING telegram_id::BIGINT
                        """
                    )
                )

        print(
            "PSCGram database migration completed successfully."
        )


# Database session
def get_db():

    db = SessionLocal()

    try:
        yield db

    finally:
        db.close()
