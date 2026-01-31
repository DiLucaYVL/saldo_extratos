"""FastAPI bootstrap for the TopFama reconciliation webapp."""
from pathlib import Path
import sys

# Permite execução direta (python server/main.py) adicionando a raiz ao PYTHONPATH
file_path = Path(__file__).resolve()
root_path = file_path.parents[1]
if str(root_path) not in sys.path:
    sys.path.append(str(root_path))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from server.app.api.routes import api_router
from server.app.config import get_settings

settings = get_settings()
PROJECT_ROOT = Path(__file__).resolve().parents[1]


app = FastAPI(
    title="TopFama - Conciliacao Bancaria",
    description="Backend FastAPI que orquestra ingestao, motor de conciliacao e relatorios.",
    version="0.1.0",
    contact={"name": "TopFama TI", "email": "ti@topfama.com"},
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Expoe os arquivos gerados (CSV, XLSX, logs) para download no frontend.
settings.reports_dir.mkdir(parents=True, exist_ok=True)
app.mount("/dados", StaticFiles(directory=str(settings.reports_dir)), name="relatorios")



app.include_router(api_router)



@app.get("/")
def read_root():
    """Retorna status da API."""
    return {
        "status": "ok",
        "message": "TopFama Conciliacao Bancaria API is running",
        "docs": "/docs"
    }





if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "server.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
    )
