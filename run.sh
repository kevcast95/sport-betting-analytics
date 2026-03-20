#!/bin/bash
# Ejecuta el scraper usando el entorno virtual
cd "$(dirname "$0")"
export PLAYWRIGHT_BROWSERS_PATH="${PLAYWRIGHT_BROWSERS_PATH:-$(pwd)/playwright-browsers}"

if [ ! -d ".venv" ]; then
  echo "Creando entorno virtual..."
  python3 -m venv .venv
fi

source .venv/bin/activate

if ! python -c "import playwright" 2>/dev/null; then
  echo "Instalando dependencias..."
  pip install -r requirements.txt -q
  echo "Instalando Chromium..."
  playwright install chromium
fi

# Chromium se instala con las deps; si falla al ejecutar, ejecuta: playwright install chromium

python event_bundle_scraper.py "$@"
