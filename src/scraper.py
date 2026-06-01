"""
Scrapper Amazon    
"""

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright

#paths for logs and data
logs_dir = Path("logs")
data_dir = Path("data")

logs_dir.mkdir(exist_ok=True)
data_dir.mkdir(exist_ok=True)

# user agent for the scraper
user_agent = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

#logger configuration
logger = logging.getLogger("AmazonScraper")
logger.setLevel(logging.INFO)

_fmt = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s, datefmt='%Y-%m-%d %H:%M:%S'")

_stream = logging.StreamHandler(sys.stdout)
_stream.setFormatter(_fmt)
logger.addHandler(_stream)

def parse_args() -> argparse.Namespace:
    """Settings of the Amazon Scraper parser.

    Returns:
        argparse.Namespace: Namespace with the arguments for the scrapping
    """
    
    parser = argparse.ArgumentParser(description="Amazon Scraper")
    parser.add_argument("--query", default="beleza", help="Termo de busca")
    parser.add_argument("--limit", type=int, default=20, help="Máximo de produtos")
    
    # BooleanOptionalAction gera --headless e --no-headless automaticamente
    parser.add_argument(
        "--headless",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Executar o navegador em modo headless (sem interface gráfica)",
    )
    
    parser.add_argument("--debug", action="store_true", help="Salva print ao final")
    
    return parser.parse_args()

def _timestamp() -> str:
    """Format YYYYMMDD_HHMMSS for JSON file name and screenshot name.

    Returns:
        str: Current timestamp in the format YYYYMMDD_HHMMSS
    """
    return datetime.now().strftime("%Y_%m_%d_%H_%M")

def run(query: str, limit: int, headless: bool, debug: bool) -> None:
    """Do the scraping of Amazon products based on the args from the Amazon Scraper parser.

    Args:
        query (str): Namespace param search term for Amazon.
        limit (int): Namespace param maximum number of products to scrape.
        headless (bool): Namespace param whether to run the browser in headless mode.
        debug (bool): Namespace param whether to save a screenshot at the end of the scraping process.
    """
    logger.info(
        "Starting Amazon Scraper with query = '%s' | limit = %d | headless = %s | debug = %s",
        query, limit, headless, debug
    )
    
    with sync_playwright() as s_playwright:
        # opening the playwright browser
        browser = s_playwright.chromium.launch(
            headless=headless,
            args=["--disable-blink-features=AutomationControlled"],
        )
        
        # setting the context window
        context = browser.new_context(
            user_agent=user_agent,
            viewport={"width": 1920, "height": 1080},
            locale="pt-BR"
        )

        # opening a new page in the context
        page = context.new_page()
        
        # setting the navigation url with the search query
        url = f"https://www.amazon.com.br/s?k={query}"
        logger.info("Navigating to %s", url)
        
        # wait_until="domcontentloaded" wait until the basic DOM
        # without waiting for all the other resourcers to load (images, ads) it's faster
        page.goto(url, wait_until="domcontentloaded", timeout=30_000)
        
        # if in debug mode, save a screenshot of the page after loading
        if debug:
            screenshot_path = logs_dir / f"amazon_scraper_{_timestamp()}.png"
            page.screenshot(path=str(screenshot_path), full_page=True)
            logger.info("Screenshot saved to %s", screenshot_path)
            
        context.close()
        browser.close()


def main() -> None:
    """Main function to execute the Amazon Scraper."""
    
    args = parse_args()

    try: 
        run(args.query, args.limit, args.headless, args.debug)
    except Exception:
        logger.exception("An error occurred during scraping.")
        raise
    
if __name__ == "__main__":
    main()