# Image Search Library: ddgs (NOT duckduckgo_search)

The DuckDuckGo search library was officially renamed by its author from `duckduckgo_search` to `ddgs` starting with version 8.0+.
- PyPI package: `ddgs` (e.g. `pip install ddgs`, in pyproject.toml: `ddgs>=8.0.0`)
- Import: `from ddgs import DDGS`
- NEVER use or install `duckduckgo_search`, as its legacy package deliberately calls `warnings.simplefilter("always")` and emits a noisy `RuntimeWarning: This package (duckduckgo_search) has been renamed to ddgs! Use pip install ddgs instead.` upon every `DDGS()` instantiation.
- In image_service.py, always import and use `from ddgs import DDGS`.
