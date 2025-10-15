# """
# User model for the authentication service.

# This defines what a "user" looks like in the database.
# Each attribute becomes a column in the 'users' table.

# This file defines what data we store for each user.

# SQLAlchemy uses it to create a table called users in the database.
# Later, the auth routes can:
#     + Add users (register),
#     + Look them up (login),
#     + Delete them if needed.
# """

# from sqlalchemy import Column, Integer, String, Boolean
# from database.db_connection import Base


# class User(Base):
#     __tablename__ = "users"  # table name in the database

#     id = Column(Integer, primary_key=True, index=True)
#     full_name = Column(String, nullable=False)
#     email = Column(String, unique=True, nullable=False, index=True)
#     password = Column(String, nullable=False)  # hashed password
#     is_organizer = Column(Boolean, default=False)
#     is_admin = Column(Boolean, default=False)
