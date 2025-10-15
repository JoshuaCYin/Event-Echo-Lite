"""
Simple DB connection helper using SQLAlchemy.

- Defaults to SQLite for easy local development.
- Switch to PostgreSQL by setting the DATABASE_URL env var,
  e.g. postgres://user:pass@host:5432/dbname

SQLAlchemy gives us a standard way to define models (tables) and talk to the database in Python.
SQLite is the default because it requires zero setup: just a file eventecho.db. That keeps onboarding easy for our team members and professor.
If later we want PostgreSQL for hosting or grading, we only change one environment variable: DATABASE_URL. The rest of the code (models, queries) stays the same.
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Use environment variable if provided (useful when deploying)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///eventecho.db")

# Create SQLAlchemy engine
# For SQLite: sqlite:///eventecho.db  (a file in the project root)
# For PostgreSQL: postgres://user:pass@host:5432/dbname
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {})

# Create a configured "Session" class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models to inherit from
Base = declarative_base()


def init_db():
    """
    Create tables for all models that inherit from Base.
    Call this once at startup (or from a small setup script).
    """
    Base.metadata.create_all(bind=engine)


# Simple helper to get a DB session (we should use this in the route handlers)
def get_db():
    """
    Yields a new DB session. Caller should close the session when done.
    Example:
        db = get_db()
        try:
            # use db (db is a Session instance)
        finally:
            db.close()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
