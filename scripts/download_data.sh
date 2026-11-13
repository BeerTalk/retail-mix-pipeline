#!/usr/bin/env bash
# Download Dominick's data (Kilts Center, Chicago Booth) for 3 categories.
# Academic use; credit the James M. Kilts Center, University of Chicago Booth School of Business.
set -e
BASE="https://www.chicagobooth.edu/research/kilts/research-data/-/media/enterprise/centers/kilts/datasets/dominicks-dataset"
DEMO="https://www.chicagobooth.edu/boothsitecore/docs/dff/store-demos-customer-count"
mkdir -p data/raw && cd data/raw

for cat in ber cer sdr; do
  wget -nc "$BASE/movement_csv-files/w$cat.zip" && unzip -n "w$cat.zip"
  wget -nc "$BASE/upc_csv-files/upc$cat.csv"
done

wget -nc "$DEMO/demo_stata.zip"   && unzip -n demo_stata.zip
wget -nc "$DEMO/ccount_stata.zip" && unzip -n ccount_stata.zip
ls -lh
