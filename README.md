# deals-bot

Bot de deals para WhatsApp com Amazon Affiliate.

## setup

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # edite com seus valores
```

## Scrapper variables
```
--query
--limit
--headless or --no-headless
--debug
```


## smoke test

```bash
python -m src.main
```