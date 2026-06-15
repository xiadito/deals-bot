# CLAUDE.md

Arquivo de contexto pra qualquer sessão do Claude (Code, web ou app) que trabalhar nesse projeto. Atualize sempre que uma decisão importante for tomada ou um módulo for concluído.

---

## Visão geral

Bot em Python que coleta promoções de produtos de **beleza e cuidado pessoal** na Amazon Brasil, gera copy persuasiva via API do Claude, e envia em grupo(s) de WhatsApp via Evolution API self-hosted. Modelo de monetização: programa **Amazon Associates** (afiliados).

O envio tem **curadoria manual** nos primeiros tempos: cada mensagem cai no privado do dono pra aprovação antes de ir pro grupo. Há uma feature flag pra migrar pra envio automático quando o pipeline amadurecer.

Pipeline a cada N horas:

```
Scrape Amazon (Playwright) → Upsert SQLite → Filtrar por regras de negócio
    → Gerar copy (Claude API) → Enviar pendente no privado
    → Aguardar aprovação via webhook → Enviar no grupo
```

---

## Status do projeto

> **Atualize esta seção a cada módulo concluído.** Marque o status atual e qualquer dívida técnica aceita.

- [ ] Módulo 1 — Setup do ambiente
- [ ] Módulo 2 — Scraper Amazon (Playwright)
- [ ] Módulo 3 — Persistência SQLite
- [ ] Módulo 4 — Filtros combinados + link de afiliado
- [ ] Módulo 5 — Geração de copy com Claude
- [ ] Módulo 6 — Evolution API (Docker + WhatsApp)
- [ ] Módulo 7 — Fluxo de aprovação manual
- [ ] Módulo 8 — Orquestrador + APScheduler
- [ ] Módulo 9 — Deploy na VPS Hostinger

**Módulo atual:** _(preencher)_
**Última atualização:** _(preencher data)_

---

## Stack

| Camada | Tecnologia | Por quê |
|---|---|---|
| Linguagem | Python 3.11+ | Stack do programador; melhor ecossistema pra scraping e SDK do Claude. |
| Dependências | `venv` + `requirements.txt` | Simplicidade; Poetry seria overhead. |
| Scraping | Playwright (chromium, sync API) | Amazon usa renderização JS pesada; `requests` puro não dá conta. |
| Persistência | SQLite via `sqlite3` (stdlib) | Volume baixo, single-writer, zero config. Suficiente. |
| IA / Copy | `anthropic` SDK, modelo `claude-sonnet-4-6` | Sweet spot de custo/qualidade pro nicho. |
| WhatsApp | Evolution API self-hosted (Docker) | API oficial da Meta **não permite envio em grupo**; Evolution roda Baileys e é open source. |
| Agendamento | APScheduler | Suficiente pra cron de poucos jobs; sem precisar de Celery. |
| HTTP servidor | FastAPI + Uvicorn | Receber webhooks da Evolution. |
| HTTP cliente | httpx | Síncrono ou assíncrono dependendo do contexto. |
| Config | `python-dotenv` + `.env` | Padrão; nunca commitar segredos. |
| Logs | `logging` stdlib + `RotatingFileHandler` | Estruturado em JSON lines pra grep/jq. |
| Deploy | VPS Hostinger KVM 2 + Docker Compose | Plano contratado pelo dono. |

---

## Fluxo de dados (alto nível)

1. **APScheduler** dispara o pipeline em horários configurados (ex: 8h/14h/20h).
2. **Scraper** acessa Amazon BR, busca "beleza", extrai N produtos.
3. **Upsert** no SQLite (tabela `produtos`); `primeiro_visto` preservado em updates.
4. Cada produto novo passa por **`avaliar_produto`** (filtros combinados):
   - Desconto mínimo (% configurável)
   - Rating mínimo
   - Número mínimo de avaliações
   - Fora do cooldown de reenvio
5. Aprovados ganham **URL de afiliado** (`amazon.com.br/dp/ASIN/?tag=TAG-20`).
6. **Claude API** gera copy persuasiva pro WhatsApp, com tom de canal de beleza.
7. Mensagem (copy + link) vira registro `envios` com status `pendente` e é enviada pro **privado do dono**.
8. Dono responde `ok #ID` ou `não #ID`.
9. **Webhook FastAPI** recebe a resposta, valida remetente, atualiza status:
   - `ok` → envia no grupo de destino, marca `enviado`
   - `não` → marca `rejeitado`
   - Timeout (X horas) → job de limpeza marca `expirado`

---

## Estrutura de pastas (alvo)

```
amazon-wpp-bot/
├── src/
│   ├── __init__.py
│   ├── main.py              # Entry point: sobe FastAPI + APScheduler
│   ├── config.py            # Carrega .env, valida vars obrigatórias
│   ├── scraper/             # Módulo 2
│   ├── repository/          # Módulo 3 (acesso SQLite)
│   ├── filters/             # Módulo 4 (regras de negócio + URL afiliado)
│   ├── claude_copy/         # Módulo 5 (geração de copy)
│   ├── whatsapp/            # Módulo 6 (cliente Evolution)
│   ├── approval/            # Módulo 7 (fluxo + webhook)
│   └── scheduler/           # Módulo 8 (jobs APScheduler)
├── tests/
├── data/                    # SQLite, cache, snapshots (volume Docker em prod)
├── logs/                    # JSON lines rotacionados (volume Docker em prod)
├── migrations/              # Scripts SQL versionados
├── docker/                  # docker-compose + Dockerfile
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

---

## Convenções

- **Idioma**: Inglês em comentários, docstrings, mensagens de log, UI e identificadores de código.
- **Estilo**: PEP 8. Se for adotar formatter, usar **`ruff format`** (substituto moderno de black).
- **Linting**: `ruff check`.
- **Tipagem**: type hints em todas as funções públicas. `Decimal` pra dinheiro, nunca `float`.
- **Datetimes**: sempre timezone-aware em `America/Sao_Paulo`. SQLite armazena em ISO 8601 UTC, converte na borda.
- **Dataclasses** pra modelos simples (Produto, Avaliacao, Envio); evitar dict pra dados estruturados.
- **Erros**: nunca silenciar `except Exception: pass`. Sempre log + decisão explícita (retry, skip, abort).
- **Imports**: stdlib → terceiros → locais, separados por linha em branco.
- **Commits**: mensagens em português, no presente, ação clara. Ex: "adiciona scraper de busca por categoria".

---

## Variáveis de ambiente

Documentadas em `.env.example`. Não commitar `.env` real.

```env
# Claude
ANTHROPIC_API_KEY=

# Amazon Associates
AMAZON_AFFILIATE_TAG=          # ex: meucanal-20

# Evolution API
EVOLUTION_BASE_URL=            # http://evolution:8080 em compose, http://localhost:8080 em dev
EVOLUTION_API_KEY=
EVOLUTION_INSTANCE_NAME=
WHATSAPP_NUMERO_DONO=          # JID privado pra aprovações (5511999999999@s.whatsapp.net)
WHATSAPP_GRUPO_DESTINO=        # JID do grupo (xxxxx@g.us)

# Filtros de negócio
DESCONTO_MIN_PCT=30
RATING_MIN=4.0
REVIEWS_MIN=50
COOLDOWN_SEMANAS=4

# Pipeline
MODO_APROVACAO=manual          # manual | automatico
PENDENCIA_TIMEOUT_HORAS=6
CRON_PIPELINE=0 8,14,20 * * *  # horários do scrape + envio

# Infra
TZ=America/Sao_Paulo
LOG_LEVEL=INFO
WEBHOOK_PORT=8000
```

---

## Decisões importantes (com motivo)

Cada decisão aqui foi tomada deliberadamente. Antes de revertê-las, entenda o porquê.

1. **WhatsApp via Evolution (não API oficial da Meta).** A Cloud API da Meta não permite envio em grupos e exige templates pré-aprovados. Evolution roda Baileys e contorna a limitação, com o trade-off de risco de banimento do número (mitigado usando chip descartável).
2. **Scraping da Amazon (não Product Advertising API).** A API oficial exige conta de afiliado já qualificada com vendas registradas, o que bloqueia quem está começando. Scraping é a forma viável até a conta amadurecer.
3. **Curadoria manual antes de envio automático.** Reduz risco de ban do número (ritmo humano), permite captar copies ruins do Claude antes de virar print, e migrar pra automático depois é só trocar flag.
4. **SQLite e não Postgres.** Volume baixo, single-writer, sem precisar de servidor separado. Migração pra Postgres é viável se o projeto crescer.
5. **APScheduler e não Celery.** Poucos jobs, sem necessidade de worker distribuído. Celery seria overhead.
6. **VPS Hostinger KVM 2.** Plano contratado pelo dono. Hospedagem compartilhada da Hostinger **não serve** (sem Docker, sem processo contínuo).
7. **Nicho fixo em beleza/cuidado pessoal.** System prompt do Claude é tunado pra esse tom. Mudar de nicho exige revisar prompt e potencialmente os filtros.

---

## Restrições e regras invioláveis

- **NUNCA usar o número WhatsApp pessoal do dono.** Sempre chip descartável.
- **NUNCA commitar `.env` ou chaves de API.** `.gitignore` é configurado antes do primeiro commit.
- **NUNCA enviar a mensagem de aprovação ("Aprovar? ok/não") pro grupo.** Sempre pro privado do dono. Validar JID antes do envio.
- **NUNCA processar webhook de remetente não autorizado.** Whitelist do JID do dono no `.env`; mensagens de outros números são logadas e descartadas.
- **NUNCA aceitar resposta de aprovação que não venha do JID privado configurado.** Defesa contra spoofing.
- **Custo do Claude**: monitorar tokens por chamada e logar custo estimado. `max_tokens` sempre setado.
- **Rate limit do scraping**: nunca rodar em loop apertado. Mínimo de horas entre runs do mesmo endpoint da Amazon, com jitter.
- **Cooldown de reenvio**: o mesmo ASIN não pode ser enviado mais de 1x dentro de `COOLDOWN_SEMANAS`. Verificar no banco antes de gerar copy (economiza chamada de Claude).
- **Idempotência do webhook**: mensagem do Evolution pode chegar 2x. Sempre validar por ID antes de processar.

---

## Como rodar localmente

```bash
# Setup inicial
python -m venv venv
source venv/bin/activate      # Linux/Mac
venv\Scripts\activate         # Windows
pip install -r requirements.txt
cp .env.example .env          # preencher com valores reais

# Smoke test (valida que .env está carregado corretamente)
python -m src.main

# Lint e formatação
ruff check src/
ruff format src/

# Testes
python -m pytest src/tests/

# Subir Evolution local (módulo 6+)
docker compose -f docker/docker-compose.dev.yml up -d
```

---

## Deploy (Hostinger VPS KVM)

Detalhes completos no módulo 9 da spec. Resumo:

- **Plano**: VPS Hostinger KVM 2 ou superior (KVM 1 fica no limite com Evolution + Playwright + Python rodando juntos).
- **SO**: Ubuntu 24.04 LTS (imagem oferecida pelo hPanel).
- **Hardening obrigatório no primeiro acesso**: trocar senha root, criar usuário não-root, SSH key only, `ufw` permitindo só 22/80/443, `fail2ban`.
- **Snapshot no hPanel** antes de parear WhatsApp e depois do estado bom conhecido. Hostinger oferece isso nativo, usar.
- **Backup do SQLite** sai pra fora da Hostinger (Backblaze B2 ou Cloudflare R2 via rclone) — não confiar só no backup nativo do provedor.
- **Sessão WhatsApp NÃO migra entre máquinas**. Repareamento é necessário em qualquer reprovisionamento.
- **Healthcheck**: cron na VPS faz `curl localhost:8000/healthz` a cada 5min; falha 3x seguidas → alerta no WhatsApp do dono via Evolution.
- **TZ=America/Sao_Paulo** obrigatório no compose (Hostinger sobe VPS em UTC).
- **Webhook entre containers** usa nome do serviço (`http://bot:8000/webhook`), não localhost nem IP público.

---

## Como pedir ajuda ao Claude neste projeto

1. **Leia este arquivo e o `HANDOFF.md` (se existir) antes de qualquer mudança.**
2. **Use a spec do módulo atual** (`spec-modulos-bot-amazon-whatsapp.md`) como referência canônica. As decisões dela já passaram por revisão.
3. **Antes de propor mudança numa decisão da seção "Decisões importantes", entenda o motivo registrado.** Se a mudança for válida, atualize esta seção junto.
4. **Pergunte antes de avançar** quando um conceito for novo pro dono. Ele é intermediário e quer aprender, não só ver código pronto.
5. **Comente código em português.** Logs e mensagens de erro também em português.
6. **Custo da API do Claude importa.** Não chamar o Claude pra coisas que regra simples resolve (filtros, deduplicação, parsing de respostas binárias do dono).
7. **Quando o chat ficar longo**, escreva um `HANDOFF.md` resumindo: o que ficou pronto, decisões novas, dívidas técnicas aceitas, próximos passos. Próxima sessão começa lendo o handoff.

---

## Referências externas relevantes

- Documentação Anthropic: https://docs.claude.com
- Evolution API: https://doc.evolution-api.com
- Playwright Python: https://playwright.dev/python
- Amazon Associates Brasil: https://associados.amazon.com.br
- Hostinger VPS: https://www.hostinger.com.br/vps
- APScheduler: https://apscheduler.readthedocs.io
