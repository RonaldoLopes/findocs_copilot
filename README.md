# FinDocs Copilot

![CI](https://github.com/RonaldoLopes/findocs_copilot/actions/workflows/ci.yml/badge.svg)

Plataforma em Python que **ingere dados financeiros públicos, organiza em SQL Server e MongoDB, e expõe uma API FastAPI com um assistente de IA** para perguntas em linguagem natural. O usuário escolhe o provedor de LLM: **Gemini** (nuvem, free tier) ou **Ollama** (local).

Os dados que vão para o SQL Server passam por um **processo de ETL** com regras de qualidade, staging, `MERGE` idempotente e auditoria de cada execução.

Este repositório é também um **treinamento avançado de Python**: cada aula constrói uma camada nova do projeto, do início ao fim, sempre terminando com o sistema funcionando. O passo a passo completo, com todo o código, está em `Treinamento_FinDocs_Copilot.pdf` (e em `TREINAMENTO.md`).

> Troque `SEU_USUARIO` pelo seu usuário do GitHub (no selo acima e nos comandos deste arquivo).

## O que ele faz

- **Perguntas sobre dados (text-to-SQL):** "Qual foi a variação da Selic nos últimos 12 meses?" vira um `SELECT` seguro no SQL Server.
- **Perguntas sobre documentos (RAG):** "O que a empresa X disse no último fato relevante?" é respondida com trechos e fontes dos documentos no MongoDB.
- **Resumo e extração estruturada:** resumo e JSON (tema, impacto, entidades) de fatos relevantes.
- **Provedor de IA à escolha:** padrão via `.env` e sobrescrita por requisição.

## Arquitetura

```
 BCB / CVM  -->  Ingestão (pandas)  -->  ETL  -->  SQL Server  (séries, dimensões, fatos)
                        |                (regras, staging,        + auditoria da carga
                        |                 MERGE, auditoria)
                        +-------------->  MongoDB  (documentos, chunks,
                                                     embeddings, saídas do LLM)
                                                        ^
 Cliente --> FastAPI --> Services (OOP) --> LLMProvider --+--> Gemini
                                                           +--> Ollama
```

| Banco | Papel |
|---|---|
| SQL Server | Dados tabulares e consultas analíticas (séries, cadastro, demonstrações), mais o staging e a auditoria do ETL |
| MongoDB | Dados semiestruturados e texto (documentos, chunks, embeddings, logs) |

## ETL para o SQL Server

Séries do BCB, cadastro da CVM e DRE **não são gravados direto** nas tabelas finais. Cada execução percorre as etapas abaixo e deixa um registro do que aconteceu.

```
 BCB / CVM ─► EXTRAÇÃO ─► TRANSFORMAÇÃO ─┬─► etl.rejeitado   linhas recusadas + motivo
              (clientes)   regras de      │
                           qualidade      └─► válidas ─► stg.* ─► MERGE ─► dbo.*
                                                          │                  │
                                          etl.execucao ◄──┴──────────────────┘
                                          (status e contagens de cada execução)
```

| Etapa | O que faz |
|---|---|
| **Extração** | Os clientes do BCB e da CVM baixam e tipam os dados |
| **Transformação** | Regras de qualidade linha a linha: CNPJ com dígito verificador (numérico e **alfanumérico**), datas, faixas de valor, tamanho dos textos, duplicatas. Cada rejeição guarda o **motivo** |
| **Staging** | As linhas válidas entram em `stg.*`. Se o `MERGE` falhar, ficam lá para investigação |
| **`MERGE`** | Insere o que é novo e atualiza **só o que mudou** (`EXCEPT`, que trata `NULL` como valor). Rodar duas vezes deixa o banco igual |
| **Auditoria** | `etl.execucao`: status, extraídos, rejeitados, inseridos, atualizados, inalterados, motivos e erro. `etl.rejeitado`: amostra das linhas recusadas |
| **Disjuntor** | Se mais de 20% das linhas forem rejeitadas (configurável), a fonte provavelmente mudou: **nada é carregado** |

```bash
python scripts/init_db.py                                  # cria dbo, stg e etl (idempotente)
python scripts/carregar_dados.py                           # todas as cargas
python scripts/carregar_dados.py --series --desde 2020-01-01
python scripts/carregar_dados.py --companhias
python scripts/carregar_dados.py --dre 2024 --max-rejeicao 0.05
python scripts/carregar_dados.py --historico               # últimas execuções e motivos
```

O script imprime uma tabela-resumo e **termina com código 1 se algum pipeline falhar**, para agendadores e CI perceberem. Para ver o que foi recusado:

```sql
SELECT TOP 10 id, pipeline, status, extraidos, rejeitados, inseridos, atualizados, inalterados, erro
FROM etl.execucao ORDER BY id DESC;

SELECT motivo, COUNT(*) AS n FROM etl.rejeitado
WHERE execucao_id = <id> GROUP BY motivo ORDER BY n DESC;
```

**Limites conhecidos:** linhas que o pandas não consegue nem converter já são descartadas na extração (Aula 2) e não passam pela tabela de rejeitados; o `EXCEPT` usa a *collation* do banco, então uma mudança só de maiúsculas não é vista como alteração; execuções do mesmo pipeline não devem rodar em paralelo (compartilham o staging); os dados não são versionados (o `MERGE` sobrescreve). O usuário somente leitura do text-to-SQL **não** tem acesso a `stg` nem a `etl`.

## Fontes de dados

- **API do Banco Central (SGS):** Selic, CDI, IPCA, câmbio.
- **Dados Abertos da CVM:** cadastro de companhias, demonstrações financeiras e documentos (fatos relevantes).

## Stack

| Área | Tecnologia |
|---|---|
| Linguagem | Python 3.12, type hints, dataclasses, Pydantic v2 |
| Dados | pandas, httpx |
| ETL | Regras puras em Python, staging e `MERGE` em T-SQL, auditoria no banco |
| SQL Server | SQLAlchemy 2, pyodbc (ODBC Driver 18) |
| MongoDB | PyMongo |
| API | FastAPI, Uvicorn |
| LLM | Gemini (`google-genai`), Ollama (API HTTP) |
| Embeddings | sentence-transformers (modelo multilíngue, local) |
| Validação de SQL | sqlglot (T-SQL) |
| Infra | Docker, docker-compose |
| Qualidade | pytest, pytest-cov, ruff |
| CI/CD | GitHub Actions, GitHub Container Registry (GHCR), Dependabot |

## Escolhendo o provedor de LLM

| | Gemini | Ollama |
|---|---|---|
| Onde roda | Nuvem (Google) | Sua máquina |
| Chave de API | Sim (Google AI Studio) | Não |
| Custo | Free tier com limites | Grátis |
| Privacidade | Texto enviado à nuvem | Tudo local |
| Desempenho | Independe do seu hardware | Depende do seu hardware |

**Padrão global** no `.env`:

```env
LLM_PROVIDER=gemini   # ou: ollama
```

**Por requisição** (sobrescreve o padrão):

```json
{
  "pergunta": "Qual foi a variação da Selic nos últimos 12 meses?",
  "provider": "ollama"
}
```

Os embeddings do RAG são sempre gerados por um modelo local, então **trocar de provedor não exige reindexar** os documentos.

### Configurar o Gemini

1. Gere uma chave no Google AI Studio.
2. Defina `GEMINI_API_KEY` e `GEMINI_MODEL` no `.env`.

Modelos e limites do free tier mudam com o tempo. Confira o modelo gratuito vigente no Google AI Studio antes de definir `GEMINI_MODEL`.

### Configurar o Ollama

1. Instale o Ollama e baixe um modelo: `ollama pull <modelo>`.
2. Defina `OLLAMA_MODEL` e `OLLAMA_BASE_URL` no `.env`.
3. Com a API rodando em Docker e o Ollama no host, use `OLLAMA_BASE_URL=http://host.docker.internal:11434`.

## Pré-requisitos

- Python 3.12
- Docker com Compose v2
- Git e uma conta no GitHub
- Pelo menos 2 GB de RAM livres para o container do SQL Server
- Chave do Google AI Studio (Gemini) e/ou Ollama instalado

## Como rodar

> Os comandos passam a funcionar conforme as aulas avançam. O fluxo completo com `docker compose up` fica pronto na **Aula 10**.

```bash
# 1. Configuração
cp .env.example .env        # preencha as senhas e a chave

# 2. Ambiente Python
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"

# 3. Bancos e schemas (dbo, stg e etl)
docker compose up -d mssql mongo
python scripts/init_db.py

# 4. Dados (ETL)
python scripts/carregar_dados.py
python scripts/carregar_documentos.py --amostra

# 5. Ou tudo em containers (a partir da Aula 10)
docker compose up --build
```

Com a API no ar, a documentação interativa fica em `http://localhost:8000/docs`.

## Variáveis de ambiente

| Variável | Descrição |
|---|---|
| `LLM_PROVIDER` | Provedor padrão: `gemini` ou `ollama` |
| `GEMINI_API_KEY`, `GEMINI_MODEL` | Chave e modelo do Gemini |
| `OLLAMA_BASE_URL`, `OLLAMA_MODEL` | Endereço e modelo do Ollama |
| `MSSQL_SA_PASSWORD` | Senha do administrador (só para criar banco e schemas) |
| `MSSQL_HOST`, `MSSQL_PORT`, `MSSQL_DB` | Conexão com o SQL Server |
| `MSSQL_APP_USER`, `MSSQL_APP_PASSWORD` | Usuário da aplicação e do ETL (lê e grava em `dbo`, `stg` e `etl`) |
| `MSSQL_RO_USER`, `MSSQL_RO_PASSWORD` | Usuário somente leitura (text-to-SQL, só as 3 views) |
| `MONGO_URI`, `MONGO_DB` | Conexão com o MongoDB |
| `EMBEDDING_MODEL` | Modelo local de embeddings |
| `LOG_LEVEL`, `LOG_JSON` | Nível e formato dos logs |

Nunca versione o `.env`. Use apenas o `.env.example`, sem valores reais.

## Endpoints

| Método | Rota | Descrição |
|---|---|---|
| GET | `/health` | Status da API e dos bancos |
| GET | `/series`, `/series/{codigo}`, `/series/{codigo}/variacao` | Séries, valores e variação |
| GET | `/companhias`, `/companhias/{cnpj}`, `/companhias/{cnpj}/demonstracoes` | Companhias e demonstrações (CNPJ com 14 caracteres, sem pontuação) |
| GET | `/documentos`, `/documentos/{id_origem}` | Documentos do MongoDB |
| GET | `/llm/providers` | Provedores disponíveis e estado |
| POST | `/documentos/{id_origem}/resumir` | Resumo e extração estruturada |
| GET | `/documentos/{id_origem}/extracoes` | Extrações já feitas |
| POST | `/documentos/{id_origem}/indexar` | Cria chunks e embeddings |
| POST | `/perguntar-documentos` | RAG com fontes |
| POST | `/perguntar-dados` | Text-to-SQL seguro |
| GET | `/perguntar-dados/historico`, `/dados/esquema` | Log das perguntas e esquema visível ao assistente |

## Estrutura do projeto

```
findocs-copilot/
├── README.md
├── pyproject.toml
├── .env.example
├── Dockerfile
├── docker-compose.yml
├── .github/
│   ├── workflows/            # ci.yml, cd.yml, gemini-smoke.yml
│   ├── dependabot.yml
│   └── pull_request_template.md
├── docker/mssql/
│   ├── 01_database.sql       # banco e usuários
│   ├── 02_schema.sql         # tabelas, views e permissões (dbo)
│   └── 03_etl.sql            # schemas stg e etl (staging e auditoria)
├── src/findocs/
│   ├── config.py
│   ├── domain/               # entidades e regras
│   ├── ingestion/            # BCB/CVM + limpeza com pandas
│   ├── etl/                  # regras, sql, carregador, auditoria, pipeline
│   ├── repositories/         # SQL Server, MongoDB e memória
│   ├── llm/                  # base, gemini, ollama, factory, prompts
│   ├── rag/                  # chunking, embeddings, busca
│   ├── text2sql/             # esquema, validador, executor
│   ├── services/             # casos de uso
│   └── api/                  # routers, schemas, dependências
├── tests/
├── scripts/                  # init_db, carregar_dados (ETL), ...
└── data/
```

## Segurança

- **Text-to-SQL:** o LLM nunca executa nada diretamente. O SQL é analisado com `sqlglot` (um único `SELECT`), só as **views permitidas** são consultáveis, há `TOP` e timeout, e a execução usa um **usuário somente leitura** que não enxerga `stg` nem `etl`.
- **ETL:** nenhum dado é descartado em silêncio (rejeições com motivo em `etl.rejeitado`) e acima de 20% de rejeição nada é carregado.
- **Prompt injection:** textos de documentos são tratados como dados, nunca como instruções.
- **CNPJ:** validado com dígito verificador, nos formatos numérico e alfanumérico (emitido pela Receita Federal desde julho de 2026).

## Plano de aulas

| # | Aula | Entrega funcional | Status |
|---|---|---|---|
| 0 | Setup | Containers de MongoDB e SQL Server no ar | [ ] |
| 1 | OOP na prática | Camada de domínio testada (Strategy, Factory, Repository) | [ ] |
| 2 | Ingestão com pandas | DataFrames limpos e validados (BCB e CVM) | [ ] |
| 3 | SQL Server | Schema, repositórios e carga incremental com `MERGE` | [ ] |
| 4 | **ETL para o SQL Server** | Regras de qualidade, staging, `MERGE` com contagem, auditoria e disjuntor | [ ] |
| 5 | MongoDB passo a passo | Fatos relevantes armazenados, com índices e agregações | [ ] |
| 6 | FastAPI | API de consulta de dados | [ ] |
| 7 | Camada de LLM | Provedor Gemini/Ollama, resumo e extração em JSON | [ ] |
| 8 | RAG | Endpoint `/perguntar-documentos` | [ ] |
| 9 | Text-to-SQL seguro | Endpoint `/perguntar-dados` | [ ] |
| 10 | Docker | `docker compose up` sobe tudo | [ ] |
| 11 | Qualidade e observabilidade | Cobertura, logs, falhas do LLM, comparação de provedores | [ ] |
| 12 | CI/CD com GitHub Actions | PR validada automaticamente e imagem publicada no GHCR | [ ] |

## Testes

Os testes são separados por marcadores: `unit` (sem bancos, sem rede) e `integration` (SQL Server e MongoDB no ar).

```bash
pytest -m unit --cov=findocs            # piso de cobertura no pyproject.toml
pytest -m integration -v                # exige os bancos no ar (docker compose up -d)
ruff check . && ruff format --check .
```

Os testes da API e do ETL usam dublês (LLM simulado, clientes BCB/CVM falsos), então rodam sem internet e sem chave. Localmente, os de integração **pulam** se o banco não responder; com `CI=true` (como no GitHub Actions) eles **falham**.

## CI/CD (GitHub Actions)

O pipeline é construído na **Aula 12**, depois do Docker e dos testes, porque ele executa os dois.

| Workflow | Gatilho | O que faz |
|---|---|---|
| `ci.yml` | Pull request e push na `main` | `ruff`; testes unitários com cobertura; integração com SQL Server e MongoDB como *service containers* (inclui o ETL); build da imagem com smoke test em `/health` |
| `cd.yml` | Tags `v*.*.*` | Verifica (`ruff` e testes), publica a imagem no GHCR e cria o GitHub Release |
| `gemini-smoke.yml` | Manual | Testa o Gemini real (secret `GEMINI_API_KEY`) |
| `dependabot.yml` | Semanal | PRs de atualização de dependências, actions e imagem base |

**Boas práticas adotadas**

- `main` protegida: PR obrigatória e os quatro checks verdes para mesclar.
- Permissões mínimas em cada workflow; `packages: write` só no CD; `pull_request_target` proibido.
- O CI não usa Gemini nem Ollama. As senhas dos bancos do CI são descartáveis.
- Segredos só em GitHub Secrets. Nunca no repositório.
- O deploy (levar a imagem a um servidor) **não** faz parte do projeto.

**Versões:** tags semânticas (`v0.1.0`, `v0.2.0`...) disparam o CD e geram a imagem `ghcr.io/SEU_USUARIO/findocs-copilot:<versão>`. Repositórios públicos têm minutos de Actions gratuitos; nos privados a cota depende do plano.

## Licença

A definir. Os dados do Banco Central e da CVM são públicos e seguem os termos de uso de cada fonte.
