VERSION = $(shell cat setup.py | grep '^ *version="' | cut -d'"' -f2)

TARGETS := dist/tomltable-$(VERSION)-py3-none-any.whl
TARGETS += dist/tomltable-$(VERSION).tar.gz

.PHONY: build
build: $(TARGETS)

dist/tomltable-%-py3-none-any.whl:
	python3 -m build .

dist/tomltable-%.tar.gz:
	python3 -m build --wheel .

.PHONY: upload
upload: $(TARGETS)
	python3 -m twine upload $^
