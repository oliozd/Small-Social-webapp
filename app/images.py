from dotenv import load_dotenv
from imagekitio import ImageKit
import os

load_dotenv() # Looks for .env file and loads the variables

imagekit = ImageKit(
  private_key= os.getenv("IMAGEKIT_PRIVATE_KEY"),
)

URL_ENDPOINT = os.getenv("IMAGEKIT_URL_ENDPOINT")