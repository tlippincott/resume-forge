import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("API_KEY")
if API_KEY is None:
    raise ValueError("API_KEY not found in environment. Please check your .env file.")
MODEL_NAME = "gpt-4o-mini"
