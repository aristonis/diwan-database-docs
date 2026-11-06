# diwan-database-docs

Documentation for [Diwan Database](https://github.com/aristonis/diwan-database), a Java port of
Laravel's database layer (connections, query builder, schema, migrations, Eloquent models).

The pages live under `docs/en` (English) and `docs/ar` (Arabic). They are built with MkDocs and the
Material theme. This repo is only the source; the published site pulls from it.

## Branches

`main` follows the latest release line. Each later major version gets its own branch.

## Local preview

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
mkdocs serve   # http://127.0.0.1:8000
mkdocs build --strict
```

## Translation

The Arabic pages under `docs/ar` are copies of the English pages with a note at the top. Translate one
by replacing its body and deleting that note.

## License

MIT. See [LICENSE](LICENSE).
