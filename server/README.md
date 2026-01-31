# Backend (server)

Camada FastAPI responsável pela ingestão de extratos, consulta SETA, motor de conciliação e geração de relatórios.

## Estrutura
- `app/`: domínios (ingestao, conciliacao, relatorios, services).
- `main.py`: bootstrap FastAPI (API REST).
- `tests/`: suíte pytest.
- `Dockerfile` / `docker-compose.yml`: artefatos de deploy.

## Setup local

Certifique-se de usar o ambiente virtual para evitar conflitos de pacotes.

```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -r server/requirements.txt
cp server/.env.example server/.env  # ajuste credenciais e diretórios
```

### Executar API (Server)

Diretamente pelo Python:
```bash
python -m server.main
```
Ou via Uvicorn (dev):
```bash
uvicorn server.main:app --host 0.0.0.0 --port 55000 --reload
```

### Executar Frontend (Tauri)

O frontend agora é uma aplicação desktop gerenciada pelo Tauri.

```bash
cd client
npm install
npm run tauri dev
```

### Docker

Para subir apenas o backend via Docker:

```bash
docker compose -f server/docker-compose.yml up --build
```

### Testes

```bash
pytest server/tests -q
```

A API publica `/api/*` e expõe `/dados` com os arquivos gerados durante a conciliação. A documentação interativa (Swagger UI) está disponível em `/docs`.
