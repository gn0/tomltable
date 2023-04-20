#install.packages("devtools")
#devtools::install_git(url = "https://codeberg.org/gnyeki/jsonwriter")

library(fixest)
library(jsonwriter)

data(quakes)

write_json(
    feols(depth ~ mag, quakes),
    "example_model_1.json")

write_json(
    feols(depth ~ mag, quakes[quakes$stations <= 27, ]),
    "example_model_2.json")

write_json(
    feols(depth ~ mag, quakes[quakes$stations > 27, ]),
    "example_model_3.json")
