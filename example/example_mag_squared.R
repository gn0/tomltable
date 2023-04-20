library(fixest)
library(jsonwriter)

data(quakes)

write_json(
    feols(depth ~ mag + mag^2, quakes),
    "example_model_4.json")
