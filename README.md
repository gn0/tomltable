
# `tomltable`: generate LaTeX tables from TOML specifications and JSON data

This Python package provides a command-line utility called `tomltable`.
This utility generates a LaTeX table from a TOML formatted table specification (read from stdin) and a set of JSON files (specified as arguments).

`tomltable` can accommodate JSON files regardless of how they are structured.
However, its specification language also provides a convenience shortcut for regression tables.
There are two related packages that save regression results in a structure that is compatible with `tomltable`:

1. [`jsonwriter`](https://codeberg.org/gnyeki/jsonwriter) for R and
2. [`json_this`](https://github.com/gn0/json-this) for Stata.

The spiritual ancestor of this package is [`coeftable`](https://github.com/gn0/coeftable) which performed a similar task but without the TOML-based specification language.

## Installation

To install this package using pip, type either

```
$ python3 -m pip install --user git+https://codeberg.org/gnyeki/tomltable
```

or

```
$ git clone https://codeberg.org/gnyeki/tomltable
$ python3 -m pip install --user ./tomltable
```

## Usage

### Generating a regression table

We will generate the following table:

<img src="https://codeberg.org/gnyeki/tomltable/raw/branch/main/example/preview_mag.png" alt="Preview of example_mag.tex" width="500" height="253" />

To start with, it is convenient to save regression results with [`jsonwriter`](https://codeberg.org/gnyeki/jsonwriter) or [`json_this`](https://github.com/gn0/json-this).
An example that uses the former in R:

```r
# example_mag.R

install.packages("devtools")
devtools::install_git(url = "https://codeberg.org/gnyeki/jsonwriter")

library(fixest)
library(jsonwriter)

data(quakes)

# Regression on all earthquakes.
#
write_json(
    feols(depth ~ mag, quakes),
    "example_model_1.json")

# Regression on earthquakes that were reported by a below-median number
# of stations.
#
write_json(
    feols(depth ~ mag, quakes[quakes$stations <= 27, ]),
    "example_model_2.json")

# Regression on earthquakes that were reported by an above-median number
# of stations.
#
write_json(
    feols(depth ~ mag, quakes[quakes$stations > 27, ]),
    "example_model_3.json")
```

Let's specify a table with three columns, one for each JSON file that is generated by the R script above.
We add column numbers and the name of the outcome variable to the header, and the R-squared along with the number of observations to the footer:

```toml
# example_mag.toml

[header]
add-column-numbers = true

[[header.row]]
cell = ["Depth", "Depth", "Depth"]

[[body.cell]]
label = "Magnitude"
coef = "mag"

[[footer.cell]]
label = "Observations"
cell = "%(n::nobs)d"

[[footer.cell]]
label = "$R^2$"
cell = "%(n::r_squared).03f"

[[footer.row]]
label = "Sample"
cell = ["full", 'stations $\leq 27$', "stations $> 27$"]
```

Now we can run the R script and generate the regression table with `tomltable`:

```
$ Rscript example_mag.R
$ cat example_mag.toml \
    | tomltable \
        -j example_model_1.json \
        -j example_model_2.json \
        -j example_model_3.json \
        --title "Earthquake depth and magnitude" \
        --label tab:quakes \
        --human-readable-numbers \
    > example_mag.tex
```

### Only generating a template

Use the `--only-table` option if you only want to generate the template, not the final table:

```
$ cat example_mag.toml \
    | tomltable \
        -j example_model_1.json \
        -j example_model_2.json \
        --title "Earthquake depth and magnitude" \
        --label tab:quakes \
        --only-template \
    > example_mag.tmpl
```

Note that the `--human-readable-numbers` option is dropped.
This option is only used for generating the final table.

### Using a template to generate a table

Use the `--from-template` option if you want to use a pre-specified template instead of generating the template from a TOML specification:

```
$ cat example_mag.tmpl \
    | tomltable \
        -j example_model_1.json \
        -j example_model_2.json \
        --from-template \
        --human-readable-numbers \
    > example_mag.tex
```

Note that the `--title` and the `--label` options are dropped.
These options are only used for template generation.

### Generating a regression table with column-specific coefficients

We will generate the following table:

<img src="https://codeberg.org/gnyeki/tomltable/raw/branch/main/example/preview_mag_squared.png" alt="Preview of example_mag_squared.tex" width="450" height="292" />

In the above table, the coefficient for _Magnitude squared_ is only present in column (2).
Because it is missing in the JSON file for column (1), we will need to call `tomltable` with the `--ignore-missing-keys` option.

To make the example complete, the following R script generates the results for column (2):

```r
# example_mag_squared.R

library(fixest)
library(jsonwriter)

data(quakes)

write_json(
    feols(depth ~ mag + mag^2, quakes),
    "example_model_4.json")
```

The TOML specification for the table is similar to before.
The most notable difference is in the new `[[body.cell]]` block for _Magnitude squared:_

```toml
# example_mag_squared.toml

[header]
add-column-numbers = true

[[header.row]]
cell = ["Depth", "Depth"]

[[body.cell]]
label = "Magnitude"
coef = "mag"

[[body.cell]]
label = "Magnitude squared"
coef = "I(mag^2)"

[[footer.cell]]
label = "$R^2$"
cell = "%(n::r_squared).03f"

[[footer.cell]]
label = "Observations"
cell = "%(n::nobs)d"
```

Running the R script and generating the table, `tomltable` gives us warning messages because _Magnitude squared_ is missing for column (1).
The missing elements in the table are simply omitted in the output, leaving some dangling text in the affected cells.
To remove these, we use `sed`:

```
$ Rscript example_mag_squared.R
$ cat example_mag_sqaured.toml \
    | tomltable \
        -j example_model_1.json \
        -j example_model_4.json \
        --title "Earthquake depth and magnitude" \
        --label tab:quakes \
        --human-readable-numbers \
        --ignore-missing-keys \
    | sed \
        -e "s/ & \$\$/ \& /" \
        -e "s/ & ()/ \& /" \
    > example_mag_squared.tex
warning: Specifier '%(1::coef::I(mag^2)::est).03f' refers to key '1::coef::I(mag^2)::est' but this key is not in the JSON object.
warning: Specifier '%(1::coef::I(mag^2)::stars)s' refers to key '1::coef::I(mag^2)::stars' but this key is not in the JSON object.
warning: Specifier '%(1::coef::I(mag^2)::se).04f' refers to key '1::coef::I(mag^2)::se' but this key is not in the JSON object.
```

## Author

Gabor Nyeki.  Contact information is on https://www.gabornyeki.com/.

