# Python Public API

API em Python que consome o endpoint publico `https://jsonplaceholder.typicode.com` sem necessidade de autenticacao.

## Objetivo

Demonstrar boas praticas de construcao de API com:

- roteamento de endpoints
- validacao de parametros
- tratamento de erros
- cache em memoria
- fallback offline
- testes automatizados

## Endpoints

- `GET /health`
- `GET /api/info`
- `GET /api/posts?userId=<int>&limit=<int>`
- `GET /api/posts/{id}`
- `GET /api/users`

## Como executar

```bash
cd projects/python-public-api
python3 -m app.server --host 127.0.0.1 --port 8000
```

## Exemplos de uso

```bash
curl -s http://127.0.0.1:8000/health
curl -s "http://127.0.0.1:8000/api/posts?userId=1&limit=5"
curl -s http://127.0.0.1:8000/api/posts/1
curl -s http://127.0.0.1:8000/api/users
```

## Testes

```bash
cd projects/python-public-api
python3 -m unittest discover -s tests -p 'test_*.py'
```

## Estrutura

- `app/server.py`: servidor HTTP e roteamento
- `app/client.py`: cliente para JSONPlaceholder com cache/fallback
- `app/config.py`: configuracoes centrais
- `tests/test_server.py`: testes de integracao local
