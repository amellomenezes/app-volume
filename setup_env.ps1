# Cria a virtualenv se não existir
if (!(Test-Path ".venv")) {
    python -m venv .venv
}

# Ativa o ambiente virtual
. .\.venv\Scripts\Activate.ps1

# Atualiza pip com segurança
python -m pip install --upgrade pip

# Instala dependências (se houver arquivo requirements.txt)
if (Test-Path "requirements.txt") {
    pip install -r requirements.txt
}
