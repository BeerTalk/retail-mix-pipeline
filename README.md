# retail-mix-pipeline

Weekly scanner data from Dominick's Finer Foods (Chicago, 1989 to 1997), used to answer three questions:

1. How does product mix impact revenue and profit?
2. Do more product options affect category profitablity?
3. Which products should be pushed, kept or cut?

## Data

**Source:** Dominick's Finer Foods dataset, James M. Kilts Center for Marketing, University of Chicago Booth School of Business. Used for academic, non-commercial purposes under the Kilts Center's terms. Data courtesy of the James M. Kilts Center for Marketing, University of Chicago Booth School of Business.

**Categories:** beer, cereal and soft drinks. One row per store, product (UPC) and week.

**Get the data:** `bash scripts/download_data.sh` (files land in `data/raw/`, which is not committed).

**Explore:** `python data_explore/explore.py` runs every check; `python data_explore/explore.py 5 6` runs only checks 5 and 6. The first run loads the CSVs into `data/retail.duckdb`, so later runs are fast.

### Columns used

| Column | Meaning |
|---|---|
| STORE, UPC, WEEK | Store, product and week (week 1 starts on 14 September 1989) |
| MOVE | Units sold |
| PRICE, QTY | Shelf price for a bundle of QTY units |
| PROFIT | Gross margin %, based on the store's average acquisition cost |
| SALE | Promotion code: B bonus buy, C coupon, S simple price cut |
| OK | 1 = valid row, 0 = flagged as suspect by the source |

Sales = PRICE × MOVE / QTY. Gross profit = sales × PROFIT / 100. Margins are weighted: total gross profit / total sales.

### Data profile

| Category | Rows | Stores | Products | Weeks |
|---|---|---|---|---|
| Beer | 3,990,672 | 89 | 788 | 91 to 399 |
| Cereal | 6,602,582 | 93 | 490 | 1 to 399 |
| Soft drinks | 17,730,501 | 93 | 1,720 | 1 to 399 |

## Data issues, ranked by impact

| # | Issue | Evidence | Handling |
|---|---|---|---|
| 1 | Margins drop in 1992 to 1994 in all three categories at once | Soft drinks weighted margin falls from about 28% to -8.5% (1993); cereal to 8.3%; beer to 5.0% | Hypothesis: a change in how PROFIT was recorded, not real losses. Compare margins within the same period; investigate by store and product on Day 2 |
| 2 | Missing weeks and a changing number of stores | Weeks with data: beer 302 of 309, cereal 366 of 399, soft drinks 390 of 399. Stores per week range from 56 to 86 | Report sales per reporting store-week, not raw weekly totals. Show missing weeks as gaps, not zeros |
| 3 | Rows with no sales | MOVE = 0 on 50.45% (beer), 27.14% (cereal) and 38.54% (soft drinks) of valid rows; PRICE = 0 on exactly these rows | Analyse MOVE > 0 only |
| 4 | Extreme margins | Below -50% or above 80% is 0.01% (beer), 1.54% (cereal) and 5.18% (soft drinks) of sales. Below -50% rows are mostly promoted and high-volume (loss leaders). Above 80% rows are also promoted and high-volume, likely stock bought cheaply during a supplier deal (hypothesis) | Keep, with a `margin_group` flag; analyse margin monthly rather than weekly |
| 5 | Suspect rows | OK = 0 on 0.58% (beer), 2.14% (cereal) and 1.43% (soft drinks) of rows | Drop |
| 6 | Undocumented promotion codes | G: about 82,000 rows in cereal and soft drinks. L: 1 row | Group as `other` |
| 7 | Product file encoding | `upcsdr.csv` is Latin-1, not UTF-8, and its header is not auto-detected | Read with `encoding = 'latin-1', header = true` |

**Checked and clean:** no negative units, no zero or negative pack sizes, no margin above 100%, and 100% of sold products (and of sales) match the product file. 112 soft drinks products, 1 beer and 1 cereal product never sold a unit.

## First findings

**Assortment breadth** (products sold per store per week):

| Category | p10 | Median | p90 |
|---|---|---|---|
| Beer | 41 | 93 | 148 |
| Cereal | 142 | 160 | 173 |
| Soft drinks | 236 | 322 | 464 |

Beer and soft drinks vary enough to study whether more options pay off; cereal barely varies. This counts products that sold, not products on the shelf, so busier stores show higher counts. Day 5 controls for store traffic (customer counts) and compares each store with itself over time.

**Promotions:** 31.6% of soft drinks rows, 27.7% of beer and 7.6% of cereal are promoted. Promoted rows sell 2 to 8 times the units of non-promoted rows. This is a correlation, since stores promote products that already sell well; Day 6 compares the same product in the same store with and without a promotion.