
# `tomltable`: generate LaTeX tables from TOML specifications and JSON data

This Python package provides a command-line utility called `tomltable`.
This utility generates a LaTeX table from a TOML formatted table specification (read from stdin) and a set of JSON files (specified as arguments).

`tomltable` can accommodate JSON files regardless of how they are structured.
However, its specification language also provides a convenience shortcut for regression tables.
There are two related packages that save regression results in a structure that is compatible with `tomltable`:

1. [`jsonwriter`](https://codeberg.org/gnyeki/jsonwriter) for R and
2. [`json_this`](https://github.com/gn0/json-thus) for Stata.

The spiritual ancestor of this package is [`coeftable`](https://github.com/gn0/coeftable) which performed a similar task but without the TOML-based specification language.

## Installation

To install this package using pip, type either

```
python3 -m pip install git+https://codeberg.org/gnyeki/tomltable
```

or

```
git clone https://codeberg.org/gnyeki/tomltable
python3 -m pip install ./tomltable
```

## Usage

## Author

Gabor Nyeki.  Contact information is on https://www.gabornyeki.com/.

