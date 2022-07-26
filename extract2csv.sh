#!/usr/bin/env bash

echo "Protein;key;dG_protein;dG_water;SD_protein;SD_water" > $1/results.csv
cat $1/result_*.csv >> $1/results.csv
