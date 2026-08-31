from pydantic import BaseModel

class PostCreate(BaseModel): # Inheriting from Basemodel 
  title: str
  content: str

class PostResponse(BaseModel): # Inheriting from Basemodel 
  title: str
  content: str