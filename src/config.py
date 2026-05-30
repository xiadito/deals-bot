import os
from dotenv import load_dotenv
from dataclasses import dataclass

load_dotenv()

@dataclass(frozen=True)
class Config:
    APP_ENV = os.getenv('APP_ENV', 'development')
    
    # API Keys
    ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')

    EVOLUTION_API_KEY = os.getenv('EVOLUTION_API_KEY')
    EVOLUTION_API_URL = os.getenv('EVOLUTION_API_URL')

    AMAZON_AFFILIATE_TAG = os.getenv('AMAZON_AFFILIATE_TAG')
    WHATSAPP_GROUP_ID = os.getenv('WHATSAPP_GROUP_ID')

