# FinDocs Copilot

![CI](https://github.com/RonaldoLopes/findocs_-_copilot/actions/workflows/ci.yml/badge.svg)

Plataforma em Python que **ingere dados financeiros públicos, organiza em SQL Server e MongoDB, e expõe uma API FastAPI com um assistente de IA** para perguntas em linguagem natural. O usuário escolhe o provedor de LLM: **Gemini** (nuvem, free tier) ou **Ollama** (local).

Este repositório é também um **treinamento avançado de Python**: cada aula constrói uma camada nova do projeto, do início ao fim, sempre terminando com o sistema funcionando.

> **Status:** em construção. O plano completo está em `Treinamento_FinDocs_Copilot.pdf`. A tabela de aulas abaixo mostra o andamento.

## O que ele faz

- **Perguntas sobre dados (text-to-SQL):** "Qual foi a variação da Selic nos últimos 12 meses?" vira um `SELECT` seguro no SQL Server.
- **Perguntas sobre documentos (RAG):** "O que a empresa X disse no último fato relevante?" é respondida com trechos e fontes dos documentos no MongoDB.
- **Resumo e extração estruturada:** resumo e JSON (tema, impacto, entidades) de fatos relevantes.
- **Provedor de IA à escolha:** padrão via `.env` e sobrescrita por requisição.

## Arquitetura

```
 BCB / CVM  -->  Ingestão (pandas)  -->  SQL Server  (séries, dimensões, fatos)
                        |
                        +------------->  MongoDB  (documentos, chunks,
                                                    embeddings, saídas do LLM)
                                                       ^
 Cliente --> FastAPI --> Services (OOP) --> LLMProvider --+--> Gemini
                                                          +--> Ollama
```

| Banco | Papel |
|---|---|
| SQL Server | Dados tabulares e consultas analíticas (séries, cadastro, demonstrações) |
| MongoDB | Dados semiestruturados e texto (documentos, chunks, embeddings, logs) |

## Fontes de dados

- **API do Banco Central (SGS):** Selic, CDI, IPCA, câmbio.
- **Dados Abertos da CVM:** cadastro de companhias, demonstrações financeiras e documentos (fatos relevantes).

## Stack

| Área | Tecnologia |
|---|---|
| Linguagem | Python 3.12, type hints, dataclasses, Pydantic v2 |
| Dados | pandas, httpx |
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

> Os comandos abaixo passam a funcionar conforme as aulas avançam. O fluxo completo com `docker compose up` fica pronto na **Aula 9**.

```bash
# 1. Configuração
cp .env.example .env        # preencha as variáveis

# 2. Subir os bancos (Aula 0 em diante)
docker compose up -d mssql mongo

# 3. Ambiente Python
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"

# 4. Sistema completo (a partir da Aula 9)
docker compose up --build
```

Com a API no ar, a documentação interativa fica em `http://localhost:8000/docs`.

## Variáveis de ambiente

| Variável | Descrição |
|---|---|
| `LLM_PROVIDER` | Provedor padrão: `gemini` ou `ollama` |
| `GEMINI_API_KEY` | Chave do Google AI Studio |
| `GEMINI_MODEL` | Modelo do Gemini |
| `OLLAMA_BASE_URL` | Endereço do Ollama |
| `OLLAMA_MODEL` | Modelo do Ollama |
| `MSSQL_SA_PASSWORD` | Senha do administrador do SQL Server |
| `MSSQL_HOST`, `MSSQL_DB` | Conexão com o SQL Server |
| `MSSQL_RO_USER`, `MSSQL_RO_PASSWORD` | Usuário somente leitura (text-to-SQL) |
| `MONGO_URI`, `MONGO_DB` | Conexão com o MongoDB |
| `EMBEDDING_MODEL` | Modelo local de embeddings |

Nunca versione o `.env`. Use apenas o `.env.example`, sem valores reais.

## Endpoints

| Método | Rota | Descrição |
|---|---|---|
| GET | `/health` | Status da API e dos bancos |
| GET | `/series` | Lista de séries |
| GET | `/series/{codigo}` | Valores da série, com filtro de período |
| GET | `/companhias` | Busca de companhias |
| GET | `/documentos/{id}` | Documento do MongoDB |
| GET | `/llm/providers` | Provedores disponíveis e estado |
| POST | `/documentos/{id}/resumir` | Resumo e extração estruturada |
| POST | `/perguntar-documentos` | RAG com fontes |
| POST | `/perguntar-dados` | Text-to-SQL seguro |

## Estrutura do projeto

```
findocs-copilot/
├── README.md
├── pyproject.toml
├── .env.example
├── .github/
│   ├── workflows/
│   │   ├── ci.yml
│   │   └── cd.yml
│   ├── dependabot.yml
│   └── pull_request_template.md
├── Dockerfile
├── docker-compose.yml
├── docker/mssql/init.sql
├── src/findocs/
│   ├── config.py
│   ├── domain/          # entidades e regras
│   ├── ingestion/       # BCB/CVM + limpeza com pandas
│   ├── repositories/    # SQL Server e MongoDB
│   ├── llm/             # base, gemini, ollama, factory, prompts
│   ├── rag/             # chunking, embeddings, busca
│   ├── services/        # casos de uso
│   └── api/             # routers, schemas, dependências
├── tests/
├── scripts/
└── docs/
```

## Segurança no text-to-SQL

O LLM nunca executa nada diretamente. Antes de qualquer consulta:

1. O SQL é analisado com `sqlglot` e só é aceito **um único `SELECT`**.
2. Apenas as **views permitidas** podem ser consultadas.
3. Há limite de linhas (`TOP`) e timeout.
4. A execução usa um **usuário do banco somente leitura**.

Textos de documentos são tratados como dados, nunca como instruções (mitigação de prompt injection).

## Plano de aulas

| # | Aula | Entrega funcional | Status |
|---|---|---|---|
| 0 | Setup | Containers de MongoDB e SQL Server no ar | [ ] |
| 1 | OOP na prática | Camada de domínio testada (Strategy, Factory, Repository) | [ ] |
| 2 | Ingestão com pandas | DataFrames limpos e validados (BCB e CVM) | [ ] |
| 3 | SQL Server | Séries e cadastro carregados com upsert | [ ] |
| 4 | MongoDB passo a passo | Fatos relevantes armazenados, com índices e agregações | [ ] |
| 5 | FastAPI | API de consulta de dados | [ ] |
| 6 | Camada de LLM | Provedor Gemini/Ollama, resumo e extração em JSON | [ ] |
| 7 | RAG | Endpoint `/perguntar-documentos` | [ ] |
| 8 | Text-to-SQL seguro | Endpoint `/perguntar-dados` | [ ] |
| 9 | Docker completo | `docker compose up` sobe tudo | [ ] |
| 10 | Qualidade | Testes unitários e de integração, cobertura, logs, falhas do LLM | [ ] |
| 11 | CI/CD com GitHub Actions | PR validada automaticamente e imagem publicada no GHCR | [ ] |

## Testes

Os testes são separados por marcadores: `unit` (sem bancos) e `integration` (com MongoDB e SQL Server no ar).


```bash
pytest -m unit
pytest -m integration   # exige os bancos no ar
ruff check .
ruff format --check .
```

Os testes da API usam um LLM simulado (mock), então rodam sem internet e sem chave.

## CI/CD (GitHub Actions)

O pipeline é construído na **Aula 11**, depois do Docker e dos testes, porque ele executa os dois.

| Workflow | Gatilho | O que faz |
|---|---|---|
| `ci.yml` | Pull request e push na `main` | `ruff`, testes unitários, testes de integração (MongoDB e SQL Server como service containers) e build da imagem com smoke test em `/health` |
| `cd.yml` | Push na `main` e tags `v*.*.*` | Publica a imagem no GHCR; nas tags, cria o GitHub Release; deploy opcional com aprovação manual |
| `dependabot.yml` | Semanal | PRs de atualização de dependências, actions e imagens base |

**Boas práticas adotadas**

- `main` protegida: sem push direto, PR obrigatória e CI verde para mesclar.
- Permissões mínimas em cada workflow; `packages: write` só no CD.
- O CI não usa Gemini nem Ollama: o LLM é simulado. Um smoke test opcional com Gemini real fica em workflow manual (`workflow_dispatch`).
- Segredos só em GitHub Secrets (por `environment` no caso do deploy). Nunca no repositório.

**Secrets e variables**

| Nome | Tipo | Uso |
|---|---|---|
| `GITHUB_TOKEN` | Automático | Publicar no GHCR e criar releases |
| `GEMINI_API_KEY` | Secret (opcional) | Smoke test manual com Gemini real |
| `DEPLOY_SSH_KEY`, `DEPLOY_HOST`, `DEPLOY_USER` | Secrets do `environment` (opcionais) | Deploy por SSH |
| `COVERAGE_MIN` | Variable | Cobertura mínima exigida |

**Versões:** tags semânticas (`v0.1.0`, `v0.2.0`...) disparam o CD e geram a imagem `ghcr.io/SEU_USUARIO/findocs-copilot:<versão>`.

Repositórios públicos têm minutos de Actions gratuitos; nos privados a cota depende do plano.

## Licença

A definir. Os dados do Banco Central e da CVM são públicos e seguem os termos de uso de cada fonte.
