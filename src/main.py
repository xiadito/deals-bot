from .config import Config
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

def main():
    logger.info("Starting the application...")
    
    logger.info("Ambiente OK | APP_ENV: %s", Config.APP_ENV)
    # Your application logic here

if __name__ == "__main__":
    main()
