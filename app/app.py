from fastapi import FastAPI, File, UploadFile, Form, Depends, HTTPException
from sqlalchemy import select
from app.db import Post, create_db_and_tables, get_async_session
from sqlalchemy.ext.asyncio import AsyncSession
from contextlib import asynccontextmanager
from sqlalchemy import select
from app.images import imagekit
import shutil
import os
import uuid
import tempfile


@asynccontextmanager
async def lifespan(app: FastAPI):
  await create_db_and_tables()
  yield
  
app = FastAPI(lifespan=lifespan)

#Uploading posts
@app.post("/upload")
async def upload_file(
  file: UploadFile = File(...),
  caption: str = Form(""),
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
      caption = caption,
      url= upload_result.url,
      file_type= "video" if file.content_type.startswith("video/") else "image",
      file_name= upload_result.name
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
    


#Looking at the posts
@app.get("/feed")
async def get_feed(
  session: AsyncSession = Depends(get_async_session)
):
  result = await session.execute(select(Post).order_by(Post.created_at.desc()))
  posts = [row[0] for row in result.all()]

  posts_data = []
  for post in posts:
    posts_data.append(
      {
        "id": str(post.id),
        "caption": post.caption,
        "url": post.url,
        "file_name": post.file_name,
        "file_type": post.file_type,
        "created_at": post.created_at.isoformat()
      }
    )
  return {"posts": posts_data}
  