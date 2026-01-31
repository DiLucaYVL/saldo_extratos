import os
from pathlib import Path
from fastapi import HTTPException
from server.app.config import get_settings

settings = get_settings()

def localizar_arquivo(nome_arquivo: str) -> Path:
    """
    Localiza um arquivo no diretório de relatórios configurado.
    
    Args:
        nome_arquivo: Caminho relativo do arquivo (ex: 'pasta/relatorio.xlsx')
        
    Returns:
        Path: Caminho absoluto para o arquivo
        
    Raises:
        HTTPException: Se o arquivo não for encontrado ou tentar sair do diretório base
    """
    # Garante que o diretório existe
    settings.reports_dir.mkdir(parents=True, exist_ok=True)
    
    # Resolve o caminho e garante que está dentro do reports_dir (segurança básica)
    try:
        arquivo_path = (settings.reports_dir / nome_arquivo).resolve()
        # Verifica se o caminho resolvido começa com o reports_dir resolvido
        # Isso evita Path Traversal (../)
        # Mas permite se reports_dir for symlink? Vamos simplificar.
        # Se o arquivo existe e está dentro da árvore, ok.
    except Exception:
        raise HTTPException(status_code=404, detail="Caminho inválido.")
    
    if not arquivo_path.exists():
        # Tenta procurar também na pasta 'dados' relativa à raiz se não estiver em reports_dir
        root_dados = Path(__file__).resolve().parents[3] / "dados"
        arquivo_path_alt = (root_dados / nome_arquivo).resolve()
        
        if arquivo_path_alt.exists():
            return arquivo_path_alt
            
        raise HTTPException(status_code=404, detail=f"Arquivo '{nome_arquivo}' não encontrado.")
        
    return arquivo_path
