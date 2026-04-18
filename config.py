import os
import urllib.parse
from dotenv import load_dotenv

# Load .env file automatically
load_dotenv()

class Config:
    # MySQL Configuration
    MYSQL_HOST = os.getenv('MYSQL_HOST', 'localhost')
    MYSQL_USER = os.getenv('MYSQL_USER', 'root')
    
    raw_password = os.getenv('MYSQL_PASSWORD', '')
    MYSQL_PASSWORD = urllib.parse.quote_plus(raw_password)
    
    MYSQL_DB = os.getenv('MYSQL_DB', 'sfras_db')
    
    SQLALCHEMY_DATABASE_URI = f"mysql+mysqlconnector://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}/{MYSQL_DB}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    SECRET_KEY = os.urandom(24)
    
    # Email Service Configuration
    MAIL_SERVER = 'smtp.gmail.com'
    MAIL_PORT = 465
    MAIL_USERNAME = os.getenv('MAIL_USERNAME', '')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD', '')
