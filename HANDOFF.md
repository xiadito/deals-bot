# HANDOFF — deals-bot

**Data:** 2026-06-14  
**Sessão encerrada em:** Módulo 2 (Scraper Amazon) — parcialmente concluído.

---

## O que está pronto

### Módulo 1 — Setup do ambiente ✅
- `venv` criado, `requirements.txt` com Playwright, dotenv.
- `src/config.py`: dataclass `Config` (frozen) carregando `.env` via `python-dotenv`.
- `src/main.py`: entry point mínimo — loga `APP_ENV` e encerra. Ainda não sobe FastAPI nem APScheduler.
- `.env` real está em `src/.env` (fora do `.gitignore`? confirmar — deve estar em raiz, não em `src/`).

### Módulo 2 — Scraper Amazon ⚠️ (WIP)
- `src/scraper.py` implementado com:
  - Dataclass `Product` com todos os campos do spec.
  - `parse_price_br`, `parse_rating`, `parse_num_avalues` — parsers com tratamento de erro.
  - `safe_extract` — extrai texto ou atributo de um Locator Playwright com try/except.
  - `extract_products` — monta um `Product` a partir de um card da busca Amazon.
  - `run` — sobe Playwright, navega para busca, espera os cards, itera e salva JSON em `src/data/`.
  - `parse_args` — CLI com `--query`, `--limit`, `--headless/--no-headless`, `--debug`.
  - `save_json` — persiste lista de `Product` em JSON com `default=str` (serializa `Decimal`).

---

## Dívidas técnicas e pontos pendentes

### Críticos (bloqueiam Módulo 3)

1. **Scraper retornando lista vazia.** Os arquivos `src/data/products_*.json` gerados nas últimas execuções estão todos vazios (`[]`). Causa provável: Amazon detectou o scraper e retornou CAPTCHA ou página diferente, ou o seletor CSS `[data-component-type='s-search-result']` foi alterado. Próximo passo: rodar com `--no-headless --debug` e inspecionar o screenshot + título da página para diagnosticar.

2. **`scroll_page` definida mas nunca chamada.** A função existe em `scraper.py` mas não é invocada dentro de `run()`. Produtos abaixo da dobra nunca são carregados. Adicionar `scroll_page(page)` após o `wait_for_selector` antes de chamar `.all()`.

3. **Scraper não integrado ao `main.py`.** Hoje o scraper só roda como script standalone (`python src/scraper.py`). `main.py` não chama o scraper. A integração vai acontecer no Módulo 8 (Orquestrador), mas vale registrar.

### Menores

4. **Comentários e docstrings em inglês.** `scraper.py` está com tudo em inglês. CLAUDE.md exige português. Pode refatorar no começo da próxima sessão ou deixar pra refactor final.

5. **Estrutura de pastas diverge do spec.** O spec define `src/scraper/` (subpacote) mas o arquivo está em `src/scraper.py`. Refatorar pra subpacote quando integrar com `main.py` (Módulo 8).

6. **`anthropic` SDK não está no `requirements.txt`.** Vai ser necessário no Módulo 5. Adicionar antes de começar o módulo de copy.

7. **`.env` em `src/.env` em vez de raiz.** `config.py` chama `load_dotenv()` sem path — vai pegar o `.env` da raiz quando rodar via `python -m src.main`. Conferir se o `.gitignore` cobre `src/.env` também.

8. **Seletor de avaliações frágil.** `"[aria-label*='classificações']"` com `attr="aria-label"` extrai o texto do aria-label inteiro (ex: `"1.234 classificações"`) e `parse_num_avalues` remove os não-dígitos. Funciona, mas Amazon pode mudar o atributo. Documentar o seletor como potencial ponto de quebra.

---

## Próximos passos (Módulo 2 → concluir e Módulo 3)

### Para fechar o Módulo 2

1. Rodar `python src/scraper.py --no-headless --debug --query beleza --limit 5` e ver o screenshot.
2. Se for CAPTCHA/bloqueio: investigar adição de `time.sleep` maior no início, cookies, ou usar proxy.
3. Se for seletor quebrado: abrir a página no browser e inspecionar o DOM atual.
4. Adicionar `scroll_page(page)` logo após o `wait_for_selector` em `run()`.
5. Ajustar retorno mínimo: garantir que ao menos 1 produto seja salvo antes de marcar módulo como pronto.

### Módulo 3 — Persistência SQLite

- Criar `src/repository/` com:
  - `schema.sql` — DDL das tabelas `produtos` e `envios`.
  - `db.py` — conexão singleton + `upsert_produto` + `buscar_pendentes`.
- Campo `primeiro_visto` deve ser preservado no upsert (só inserir se não existir).
- Testar com os JSONs de `src/data/` como entrada manual.

---

## Decisões novas (nenhuma nesta sessão)

Todas as decisões desta sessão seguiram o spec. Nenhuma reversão ou nova decisão foi necessária.

---

## Como retomar

```bash
# Ativar ambiente
venv\Scripts\activate   # Windows

# Testar scraper com browser visível
python src/scraper.py --no-headless --debug --query beleza --limit 5

# Smoke test do config
python -m src.main
```

Leia este arquivo e o `CLAUDE.md` antes de qualquer mudança. O ponto de entrada para diagnóstico é o screenshot gerado pelo `--debug`.
