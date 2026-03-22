call .venv\Scripts\activate.bat
pip install poetry
cd frontend || exit /b
call npm install
call npm run lint
cd .. || exit /b
poetry run ruff check src/
poetry run mypy src/
python scripts/verify_z3_install.py
