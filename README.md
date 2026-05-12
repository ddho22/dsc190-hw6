# nldate

Natural language date parsing for Python — no LLMs required.

```python
from datetime import date
from nldate import parse

today = date(2025, 6, 15)

parse("next Tuesday",                       today=today)  # date(2025, 6, 17)
parse("5 days before December 1st, 2025",   today=today)  # date(2025, 11, 26)
parse("1 year and 2 months after yesterday",today=today)  # date(2026, 8, 14)
parse("two weeks from tomorrow",            today=today)  # date(2025, 6, 30)
parse("in 3 months",                        today=today)  # date(2025, 9, 15)
```

## Installation

```bash
pip install nldate          # once published to PyPI
# or directly from source:
uv add git+https://github.com/YOUR_USERNAME/nldate
```

## Usage

```python
from nldate import parse

# today defaults to datetime.date.today() if omitted
result = parse("next Friday")
```

### Supported expressions

| Category | Examples |
|---|---|
| Named anchors | `today`, `tomorrow`, `yesterday` |
| Absolute dates | `December 1st, 2025` · `2025-12-01` · `12/01/2025` · `1 January 2026` |
| Weekdays | `next Tuesday` · `last Monday` · `this Friday` · `Wednesday` |
| Next/last period | `next week` · `last month` · `next year` |
| Offset (future) | `in 3 days` · `in 2 weeks` · `in 1 year` · `in five days` |
| Offset (past) | `3 days ago` · `2 weeks ago` · `3 months ago` |
| From/later | `10 days from now` · `10 days from today` · `7 days later` |
| Compound offsets | `2 weeks and 3 days from now` · `1 year and 2 months after yesterday` |
| Before/after anchor | `5 days before December 1st` · `10 days after January 1, 2026` |
| Prior to / following | `1 week prior to July 4 2025` · `3 days following December 25 2025` |
| Word numbers | `two weeks from tomorrow` · `in five days` |
| Case-insensitive | `NEXT TUESDAY` · `5 Days Before December 1St, 2025` |

## Development

This project uses [uv](https://github.com/astral-sh/uv).

```bash
git clone https://github.com/YOUR_USERNAME/nldate
cd nldate
uv sync
uv run pytest          # run tests
uv run mypy src/       # type check
uv run ruff check      # lint
```

## License

MIT
