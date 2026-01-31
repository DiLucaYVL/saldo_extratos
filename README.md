# Automação de Extratos Bancários

Este projeto automatiza o processo de conciliação bancária, extraindo saldos de extratos em PDF (Banco do Brasil, Caixa, Santander, Bradesco) e consolidando as informações em uma planilha do Google Sheets.

## Funcionalidades

-   **Download Automático**: Baixa extratos do dia atual do Google Drive.
-   **Extração Inteligente**: Suporta múltiplos formatos de extrato (PDF) e bancos.
    -   *Banco do Brasil*: Extração estrita da linha "SALDO".
    -   *Caixa, Santander, Bradesco*: Parsers dedicados.
-   **Tratamento de Datas**: Calcula automaticamente o dia útil anterior para registro.
-   **Upload Google Sheets**: Envia os dados consolidados para uma planilha, verificando duplicatas e formatando datas corretamente (dd/mm/yyyy).

## Pré-requisitos

-   Python 3.8+
-   Conta de Serviço do Google (para Drive e Sheets API).

## Instalação

1.  **Clone o repositório:**
    ```bash
    git clone https://github.com/DiLucaYVL/saldo_extratos.git
    cd saldo_extratos
    ```

2.  **Crie e ative um ambiente virtual:**
    ```bash
    # Windows
    python -m venv .venv
    .venv\Scripts\Activate.ps1
    ```

3.  **Instale as dependências:**
    ```bash
    pip install -r requirements.txt
    ```

## Configuração

1.  **Variáveis de Ambiente (.env):**
    Crie um arquivo `.env` na raiz do projeto com as seguintes variáveis:
    ```env
    GOOGLE_SHEETS_ID=seu_id_da_planilha
    GOOGLE_CREDENTIALS_PATH=secrets/saldo_extratos.json
    DRIVE_ROOT_ID=seu_id_da_pasta_raiz_do_drive
    DRIVE_SA_CREDENTIALS_PATH=secrets/drive-sa.json
    BRASIL_API_URL=https://brasilapi.com.br/api/feriados/v1
    ```

2.  **Credenciais do Google:**
    Crie uma pasta chamada `secrets/` na raiz e adicione seus arquivos JSON de credenciais:
    -   `secrets/drive-sa.json`: Credenciais para acesso ao Google Drive.
    -   `secrets/saldo_extratos.json`: Credenciais para acesso ao Google Sheets.

    > **Nota:** A pasta `secrets/` e o arquivo `.env` são ignorados pelo git por segurança.

## Uso

Para executar a automação manualmente:

```bash
python main.py
```

O script irá:
1.  Verificar a data de hoje e calcular o dia útil anterior.
2.  Buscar arquivos na pasta correspondente do Google Drive.
3.  Baixar e extrair os saldos.
4.  Enviar os dados para o Google Sheets (evitando duplicatas).
5.  Limpar arquivos temporários.

## Estrutura do Projeto

-   `main.py`: Ponto de entrada da automação.
-   `server/app/ingestao/`: Módulos de extração e parsers de PDF.
-   `server/utils.py`: Utilitários de data e feriados.
-   `tests/`: Arquivos de teste (ignorados no git).
