import uuid
from typing import Optional
from fastapi import Depends, Request
from fastapi_users import BaseUserManager, FastAPIUsers, UUIDIDMixin, models
from fastapi_users.authentication import AuthenticationBackend, BearerTransport, JWTStrategy
from fastapi_users.db import SQLAlchemyUserDatabase
from app.db import User, get_users_db
import os
from dotenv import load_dotenv

load_dotenv()

class UserManager(UUIDIDMixin, BaseUserManager[User, uuid.UUID]):
  secret = os.getenv("USERS_SECRET")
  reset_password_token_secret= secret
  verification_token_secret= secret
  async def on_after_register(self, user: User, request: Optional[Request] = None):
    print(f" User {user.id} has registered")
    
  async def on_after_forgot_password(self, user: User, token: str, request = None):
    print(f" User {user.id} has forgotten their password. Reset token: {token}")
    
  async def on_after_request_verify(self, user, token, request = None):
    print(f"Verification Requested for user {user.id}. Verification Token: {token}")
  
async def get_user_manager(user_db: SQLAlchemyUserDatabase = Depends(get_users_db)):
  yield UserManager(user_db)
  
bearer_transport = BearerTransport(tokenUrl="auth/jwt/login")

def get_jwt_strategy():
  secret = os.getenv("USERS_SECRET")
  return JWTStrategy(secret=secret, lifetime_seconds=3600)

auth_backend = AuthenticationBackend(
  name="jwt",
  transport=bearer_transport,
  get_strategy=get_jwt_strategy
)

fastapi_users = FastAPIUsers[User, uuid.UUID](get_user_manager, auth_backends=[auth_backend])

current_active_user = fastapi_users.current_user(active=True)