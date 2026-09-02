import uuid
from collections.abc import AsyncGenerator
from sqlalchemy import create_engine, Column, String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, relationship
from datetime import datetime
from fastapi_users.db import SQLAlchemyBaseUserTableUUID, SQLAlchemyUserDatabase
from fastapi import Depends
DATABASE_URL = "sqlite+aiosqlite:///./test.db"

class Base(DeclarativeBase): # Cannot inherit directly
  pass

# Here SQL alchemy is used to build the database. Two tables User & Posts. Relationship: 1:Many
# SQLalchemy has its own variables and primary key instantiated already. e.g. email, id
class User(SQLAlchemyBaseUserTableUUID, Base):
  posts= relationship(argument="Post", back_populates="user")
  
class Post(Base):
  __tablename__ = "posts"
  
  post_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
  owner_email = Column(String, nullable=False)
  user_id = Column(UUID(as_uuid=True), ForeignKey("user.id"), nullable=False)
  caption = Column(Text)
  url = Column(String, nullable= False)
  imagekit_id = Column(String, nullable = False)
  file_type = Column(String, nullable= False)
  file_name = Column(String, nullable= False)
  created_at = Column(DateTime, default= datetime.now)
  
  user = relationship(argument="User", back_populates="posts")

engine = create_async_engine(DATABASE_URL)
async_session_maker = async_sessionmaker(engine, expire_on_commit=False)

async def create_db_and_tables():
  async with engine.begin() as conn:
    await conn.run_sync(Base.metadata.create_all)

async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
  async with async_session_maker() as session:
    yield session

async def get_users_db(session: AsyncSession= Depends(get_async_session)):
  yield SQLAlchemyUserDatabase(session, User)