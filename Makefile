VERSION = $(shell grep '^version = "' pyproject.toml | cut -d'"' -f2)

TARGETS := dist/tomltable-$(VERSION)-py3-none-any.whl
TARGETS += dist/tomltable-$(VERSION).tar.gz

.PHONY: build
build: $(TARGETS)

dist/tomltable-%-py3-none-any.whl:
	uv build --wheel .

dist/tomltable-%.tar.gz:
	uv build --sdist .

.PHONY: upload
upload: $(TARGETS)
	python3 -m twine upload $^
