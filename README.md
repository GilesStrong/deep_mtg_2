# my_package

## Installation

For development usage, we use [`uv`](https://docs.astral.sh/uv/) to handle dependency installation.
uv can be installed via, e.g.

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

and ensuring that `uv` is available in your `$PATH`

Install the dependencies:

```bash
uv lock
uv sync
uv tool install pre-commit --with pre-commit-uv --force-reinstall
uvx pre-commit install
```
