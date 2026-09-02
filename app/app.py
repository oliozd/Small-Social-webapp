from fastapi import FastAPI, File, UploadFile, Form, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from contextlib import asynccontextmanager
from sqlalchemy import select
import shutil
import os
import uuid
import tempfile

# Our dependencies
from app.users import auth_backend, current_active_user, fastapi_users
from app.schemas import UserCreate, UserRead, UserUpdate
from app.db import Post, User, create_db_and_tables, get_async_session
from app.images import imagekit


@asynccontextmanager
async def lifespan(app: FastAPI):
  await create_db_and_tables()
  yield
  
#---Initialising the applicaiton---
app = FastAPI(lifespan=lifespan)

app.include_router(fastapi_users.get_auth_router(auth_backend), prefix='/auth/jwt', tags=["auth"] )
app.include_router(fastapi_users.get_register_router(UserRead, UserCreate), prefix='/auth', tags=["auth"] )
app.include_router(fastapi_users.get_reset_password_router(), prefix='/auth', tags=["auth"] )
app.include_router(fastapi_users.get_verify_router(UserRead), prefix='/auth', tags=["auth"] )
app.include_router(fastapi_users.get_users_router(UserRead, UserUpdate), prefix='/auth', tags=["auth"] )

#---Application API methods---
#Create Post method
@app.post("/upload")
async def upload_file(
  file: UploadFile = File(...),
  caption: str = Form(""),
  user: User = Depends(current_active_user),
  session: AsyncSession = Depends(get_async_session) # This triggers get_async_session as it the current function depends on it(dependency injection)
):
  temp_file_path = None
  try:
    with tempfile.NamedTemporaryFile(delete=False, suffix= os.path.splitext(file.filename)[1]) as temp_file:
      temp_file_path = temp_file.name 
      shutil.copyfileobj(file.file, temp_file)
      
    upload_result = imagekit.files.upload(
      file=open(temp_file_path, "rb"),
      file_name=file.filename,
      use_unique_file_name= True,
      tags=["backend-upload"],
      )
    # 1. Initialise a post
    post = Post(
      user_id= user.id,
      owner_email= user.email,
      caption = caption,
      url= upload_result.url,
      imagekit_id = upload_result.file_id,
      file_type= "video" if file.content_type.startswith("video/") else "image",
      file_name= upload_result.name,
    )
    # 2. Add post to db(stage)
    session.add(post) 
    # 3. Commit the session(save)
    await session.commit()
    # 4. Refresh object(Fills the remaining attributes: id, created_at)
    await session.refresh(post)
    return post
    
  except Exception as e:
    raise HTTPException(status_code=500, detail= f"Failed to Upload Post{str(e)}")
  
  finally:
    if temp_file_path and os.path.exists(temp_file_path):
      os.unlink(temp_file_path)
    file.file.close()
    


#Looking at the post 'feed'
@app.get("/feed")
async def get_feed(user: User = Depends(current_active_user), session: AsyncSession = Depends(get_async_session)):
  result = await session.execute(select(Post).order_by(Post.created_at.desc()))
  posts = [row[0] for row in result.all()]

  posts_data = []
  for post in posts:
    posts_data.append(
      {
        "post_id": str(post.post_id),
        "email": str(post.owner_email),
        "user_id": str(post.user_id),
        "caption": post.caption,
        "url": post.url,
        "imagekit_id": post.imagekit_id,
        "file_name": post.file_name,
        "file_type": post.file_type,
        "created_at": post.created_at.isoformat(),
        "is_owner": post.user_id == user.id
      }
    )
  return {"posts": posts_data}

# Deleting the post
@app.delete("/feed/{post_id}")
async def delete_post(post_id: str, user: User = Depends(current_active_user), session: AsyncSession = Depends(get_async_session)):
  
  try:
    # Database removal
    post_uuid = uuid.UUID(post_id)
    result = await session.execute(select(Post).where(Post.post_id == post_uuid))
    post = result.scalars().first()
    # Handling wrong IDs
    if not post:
      raise HTTPException(status_code=404, detail= "Post not found")
    
  
    # Handling photo removal from imagekit
    imagekit.files.delete(post.imagekit_id)
    
    await session.delete(post)
    await session.commit()
    # Sending message back to user
    return {"success": True, "message": "Post deleted successfully"}
  
  except Exception as e:
    raise HTTPException(status_code=500, detail="Server Error")