apt update && apt install -y

uv sync --frozen --dev
uv tool install pre-commit --with pre-commit-uv --force-reinstall
uvx pre-commit install
