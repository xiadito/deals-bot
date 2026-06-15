"""
Scrapper Amazon    
"""

#stdlib
import argparse
import json
import logging
import random
import re
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

#third party
from playwright.sync_api import Locator, TimeoutError as PlaywrightTimeoutError, sync_playwright

#local
#from .models import Product

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

card_selector = "[data-component-type='s-search-result']"
# Dentro de cada card:
# ASIN     → card.get_attribute("data-asin")           (atributo do próprio card)
# Título   → "h2 [aria-label] span"                                (h2 é único, span pega o texto)
# URL      → "h2 a"                                     (href do link)
# Preço    → ".a-price[data-a-color='base'] .a-offscreen"     (R$ 29,90 inteiro)
# Preço de → ".a-price[data-a-strike='true'] .a-offscreen"    (riscado, opcional)
# Rating   → "[aria-label*='estrelas']"                       (aria-label tem "4,5 de 5 estrelas")
# Avaliações → "[aria-label*='estrelas'] + span"             (irmão imediato do rating)


#logger configuration
logger = logging.getLogger("AmazonScraper")
logger.setLevel(logging.INFO)

_fmt = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s", datefmt='%Y-%m-%d %H:%M:%S')

_stream = logging.StreamHandler(sys.stdout)
_stream.setFormatter(_fmt)
logger.addHandler(_stream)

@dataclass
class Product:
    """Data class to represent a product scraped from Amazon."""
    
    asin: str
    title: str
    price: Decimal | None
    url: str
    old_price: Decimal | None = None    
    rating: float | None = None 
    num_reviews: int | None = None  
    
def parse_price_br(price_str: str | None) -> Decimal | None:
    """Parse the scrapped price string.

    Args:
        price_str (str | None): the scrapped price string from amazon.

    Returns:
        Decimal | None: the price as a Decimal object, or None if the input was None or could not be parsed.
    """
    
    if not price_str:
        return None
    
    clear_price: str = re.sub(r"[R$\s\xa0]", "", price_str)  # Remove 'R$', spaces, and non-breaking spaces
    clear_price = clear_price.replace(".", "").replace(",", ".")  # Replace comma with dot for decimal separator
    
    try:
        return Decimal(clear_price) # transform the clear price string into a Decimal object
    except InvalidOperation:
        logger.error("Error parsing price: %s", price_str)
        return None # if the conversion to Decimal fails

def parse_rating(rating_str: str | None) -> float | None:
    """Parse the scrapped rating string.

    Args:
        rating_str (str | None): the scrapped rating string from amazon.

    Returns:
        float | None: the rating as a float, or None if the input was None or could not be parsed.
    """
    
    if not rating_str:
        return None
    
    match = re.match(r"(\d+[,\.]\d+)", rating_str.strip()) # remove the blank spaces and match the pattern of the rating (e.g., "4,5" or "4.5")
    
    if not match:
        logger.info("No rating found in string: %s", rating_str)
        return None # if found nothing
    
    try:
        return float(match.group(1).replace(",", ".")) # replace the comma of the rating with a dot for the decimal separator and convert to float
    except ValueError:
        logger.info("Error parsing rating: %s", rating_str)
        return None # if the conversion to float fails

def parse_num_avalues(num_str: str | None) -> int | None:
    """Parse the scrapped number of reviews string.

    Args:
        num_str (str | None): the scrapped number of reviews string from amazon.

    Returns:
        int | None: the number of reviews as an integer, or None if the input was None or could not be parsed.
    """
    
    if not num_str:
        return None
    
    clear_num = re.sub(r"[\D]", "", num_str) # Remove all non-digit characters
    
    if not clear_num:
        logger.info("No number of reviews found in string: %s", num_str)
        return None # if found nothing
    
    try:
        return int(clear_num) # Convert the cleaned string to an integer
    except ValueError:
        logger.info("Error parsing number of reviews: %s", num_str)
        return None # if the conversion to int fails

def safe_extract(card: Locator, selector: str, attr: str | None = None) -> str | None:
    """Extract text or attribute from the DOM, returns None if was not found.
   E 
    - If: attr is None -> returns text_content()
    - If attr = "href" / "data-asin" / etc, returns the attr.
    Args:
        card (Locator): Playwright Locator for the product card.
        selector (str): CSS selector to find the element within the card.
        attr (str | None, optional): The attribute to extract. If None, extracts text. Defaults to None.

    Returns:
        str | None: The extracted text or attribute, or None if not found.
    """
    
    try:
        card_locator = card.locator(selector).first #return locator to the first matching element
        
        if card_locator.count() == 0:
            return None
        
        attr_value = card_locator.get_attribute(attr) if attr else card_locator.text_content()
        
        return attr_value.strip() if attr_value else None
    
    except PlaywrightTimeoutError:
        logger.debug("safe_extract timeout in %r", selector)
        return None

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

def scroll_page(page) -> None:
    """Scroll the page with random delays to prevent from being blocked by Amazon's anti-scraping measures.

    Args:
        page: Playwright page object.
    """

    num_scroll = random.randint(2, 3) # number of scrolls to do
    logger.info("Scrolling the page %d times to load more products.", num_scroll)
    
    for i in range(num_scroll):
        page.evaluate("window.scrollBy(0, window.innerHeight * 0.8)") # scroll down by 80% of the viewport height
        pause = random.uniform(1, 3) # random pause between 1 and 3 seconds
        time.sleep(pause)
    
    page.evaluate("window.scrollTo(0, 0)") # scroll back to the top of the page
    time.sleep(random.uniform(0.5, 1.0)) # random pause after scrolling back to the top

def _timestamp() -> str:
    
    """Format YYYYMMDD_HHMMSS for JSON file name and screenshot name.

    Returns:
        str: Current timestamp in the format YYYYMMDD_HHMMSS
    """
    return datetime.now().strftime("%Y_%m_%d_%H_%M") 

    
def save_json(products: list[Product], path: Path) -> None:
    """Save the list of products in json form

    Args:
        products (list[Product]): List of Product objects to be saved.
        path (Path): path they're going to be saved in.
    """
    
    data = [asdict(product) for product in products] # convert each Product object to a dictionary
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8"
    )
    
def extract_products(card: Locator) -> Product | None:
    """Scrape a single product from a Playwright Locator for the product card.

    Args:
        card (Locator): Playwright Locator for the product card.

    Returns:
        Product | None: A Product object with the scraped data, or None if the ASIN was not found.
    """
    
    asin = card.get_attribute("data-asin")
    if not asin:
        href = safe_extract(card, "h2 a", attr="href") or ""
        match = re.search(r"/dp/([A-Z0-9]{10})", href)
        asin = match.group(1) if match else None
    
    title = safe_extract(card, "h2[aria-label] span")
    if not title:
        logger.warning("Title not found for ASIN %s, skipping.", asin)
        return None
    
    current_price = parse_price_br(safe_extract(card, ".a-price[data-a-color='base'] .a-offscreen"))
    if current_price is None:
        logger.warning("Current price not found for ASIN %s, skipping.", asin)
        return None
    
    return Product(
        asin=asin,
        title=title,
        price=current_price,
        url=f"https://www.amazon.com.br/dp/{asin}",
        
        old_price = parse_price_br(safe_extract(card, ".a-price[data-a-strike='true'] .a-offscreen")),
        
        rating = parse_rating(safe_extract(card, ".a-icon-alt")),
        
        num_reviews = parse_num_avalues(safe_extract(card, "[aria-label*='classificações']", attr="aria-label"))
    )
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
        logger.info("Page loaded successfully | title: %s", page.title())
        
        #early exit if the page title indicates a captcha or block
        try:
            # wait for the product cards to be visible
            page.wait_for_selector(card_selector, timeout=30_000)
            scroll_page(page) # scroll the page to load more products
            logger.info("Product cards are visible on the page.")
        except PlaywrightTimeoutError:
            logger.error("Timeout while waiting for product cards to load. Didn't load in 15s")
            
            shot_path = data_dir / f"timeout_{_timestamp()}.png"
            page.screenshot(path=shot_path)
            
            logger.info("Saved screenshot of the timeout at %s", shot_path)
            
            context.close()
            browser.close()
            return
        
        # scrapping the products
        
        try:
            ##.all() returns a list of locators for all the matching elements
            cards = page.locator(card_selector).all() # here we have the cards to use in safe_extract
            logger.info("Found %d product cards on the page.", len(cards))
            
            
            #extract the products
            products: list[Product] = []
            descarted = 0
            for card in cards:
                if len(products) >= limit:
                    logger.info("Reached the limit of %d products, stopping.", limit)
                    break
                
                product = extract_products(card)
                
                if product:
                    products.append(product)
                else:
                    descarted += 1
            
            logger.info("Scraped %d products | descarted %d", len(products), descarted)
            
            # save the products in a json file
            json_path = data_dir / f"products_{_timestamp()}.json"
            save_json(products, json_path)
            logger.info("Saved scraped products to %s", json_path)
            
            # screenshot debug
            if debug:
                shot_path = data_dir / f"debug_{_timestamp()}.png"
                page.screenshot(path=shot_path)
                logger.info("Saved debug screenshot at %s", shot_path)
                logger.info("Pausing for inspection.")
                page.pause() # pause the browser for inspection
                
            context.close()
            browser.close()
        except Exception:
            logger.exception("An error occurred during scraping.")
            
            shot_path = data_dir / f"debug_{_timestamp()}.png"
            page.screenshot(path=shot_path)
            logger.info("Saved debug screenshot at %s", shot_path)
            
            context.close()
            browser.close()
            raise
        
  

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