""" data exploration: Dominick's beer, cereal and soft drinks.

DuckDB reads the CSVs directly, so the 1.2 GB soft drinks file never has to fit in memory.
"""
import duckdb
import sys


RAW = "data/raw"
# con = duckdb.connect()
con = duckdb.connect("data/retail.duckdb")

# one view over all three movement files, with a category col from the file name
con.execute(f"""
    create table if not exists movement as
    select
        case
            when filename like '%wber%' then 'beer'
            when filename like '%wcer%' then 'cereal'
            else 'soft_drinks'
        end as category,
        *
    from read_csv(['{RAW}/wber.csv', '{RAW}/wcer.csv', '{RAW}/wsdr.csv'],
                  filename = true, union_by_name = true)
""")


ONLY = sys.argv[1:]
def run(check_id):
    return not ONLY or check_id in ONLY

def query_df(sql: str):
    """Run a SQL query and return the result as a pandas DataFrame."""
    return con.execute(sql).df()


# check 1: size and time per category
if run("1"):
    print("\nCheck 1: rows, stores, products and weeks per category")
    print(query_df("""
    select
        category,
        count(*) as rows,
        -- dif STORE
        count (distinct store) as stores,
        -- dif PRODUCTS
        count(distinct UPC) as products,
        -- 1st and last week
        min(week) as first_week,
        max(week) as last_week
    from movement
    group by category
    order by category
""").to_string(index=False))


#2: share of rows flagged as suspect (OK = 0) 
if run("2"):
    print("\nCheck 2: suspect rows per category")
    print(query_df("""
    select
        category,
        count(*)                                   as rows,
        --  count rows where OK = 0
        cast(countif(OK = 0) as bigint) as suspect_rows,
        -- percent ok
        round(countif(OK = 0) / count(*) * 100 ,2)  as pct_suspect
    from movement
    group by category
    order by category
""").to_string(index=False))


#  check 3: impossible values and weeks with no sales 
if run("3"):
    print("\nCheck 3: impossible values check (OK = 1 only)")
    print(query_df("""
    select
        category,
        cast(countif(price <=0) as bigint) as price_le_0,
        cast(countif(move < 0) as bigint) as move_lt_0,
        cast(countif(qty<=0) as bigint) as qty_le_0,
        -- move = 0 percent
        round( countif(move = 0) / count(*) * 100, 2)as pct_zero_sales
    from movement
    where OK = 1        -- only the rows we'll keep
    group by category
    order by category
""").to_string(index=False))


# check 3b: do zero prices match  with zero sales? 
if run("3b"):
    print("\nCheck 3b: price = 0 while move = 0 (OK = 1 only)")
    print(query_df("""
    select
        category,
        PRICE <= 0 as price_zero,
        MOVE = 0   as no_sales,
        count(*)   as rows
    from movement
    where OK = 1
    group by category, price_zero, no_sales
    order by category, price_zero, no_sales
""").to_string(index=False))

#  check 4: margin check
if run("4"):
    print("\nCheck 4: PROFIT (gross margin %) distribution")
    print(query_df("""
    select
        category,
        min(profit) as min_margin,
        max(profit) as max_margin,
        round(quantile_cont(PROFIT, 0.05), 1) as p05,
        round(quantile_cont(PROFIT, 0.5), 1) as median,
        round(quantile_cont(PROFIT, .95), 1)as p95,
        round(100 * countif(profit < 0)/count(*),2) as pct_negative,
        cast(countif(profit> 100) as bigint) as rows_over_100
    from movement
    where OK = 1 and MOVE > 0
    group by category
    order by category
""").to_string(index=False))


#  check 4b: # sales  in unusual margins
if run("4b"):
    print("\nCheck 4b: sales with unusal margins -50% or > 80%)")
    print(query_df("""
    select
        category,
        round(countif(PROFIT < -50 or PROFIT > 80) / count(*) * 100, 2) as pct_rows_extreme,
        round(sum(case when PROFIT < -50 or PROFIT > 80
                             then PRICE * MOVE / QTY else 0 end)
                  / sum(PRICE * MOVE / QTY) *100, 2) as pct_sales_extreme
    from movement
    where OK = 1 and MOVE > 0
    group by category
    order by category
""").to_string(index=False))

#  check 4c: are extreme margins because of promotions
if run("4c"):
    print("\nCheck 4c: low vs high extreme margins promotions check")
    print(query_df("""
    select
        category,
        case
            when PROFIT < -50 then 'below -50%'
            when PROFIT > 80  then 'above 80%'
            else 'normal'
        end as margin_group,
        count(*) as rows,
        round(avg(MOVE), 1) as avg_units,
        round(100 * countif(SALE is not null) / count(*), 1) as pct_promo_flag
    from movement
    where OK = 1 and MOVE > 0
    group by category, margin_group
    order by category, margin_group
""").to_string(index=False))

#  check 5: sales and gross profit by category and year
if run("5"):
    print("\nCheck 5: sales, profit and margin by category and year")
    print(query_df("""
    with sales_rows as (
        select
            category,
            year(DATE '1989-09-14' + INTERVAL ((WEEK - 1) * 7) DAY) as yr,
            PRICE * MOVE / QTY  as sales,
            PROFIT
        from movement
        where OK = 1 and MOVE > 0
    )
    select
        category,
        yr,
        round(sum(sales) / 1000, 0) as sales_k,
        round(sum(sales * profit /100 )/ 1000, 0) as gross_profit_k,
        round(100* sum(sales * profit/100) / sum(sales), 1) as margin_pct
    from sales_rows
    group by category, yr
    order by category, yr
""").to_string(index=False))

#  check 6: assortment breadth (products with sales per store per week)
if run("6"):
    print("\nCheck 6: products sold per store per week")
    print(query_df("""
    with store_weeks as (
        select
            category,
            STORE,
            WEEK,
            count(distinct UPC) as n_products
        from movement
        where OK = 1 and MOVE > 0
        group by category, STORE, WEEK
    )
    select
        category,
        count(*) as store_weeks,
        round(avg(n_products), 0) as avg_products,
        round( quantile_cont(n_products, 0.1), 1) as p10,
        round( quantile_cont(n_products, 0.5), 1) as median,
        round( quantile_cont(n_products, 0.9), 1) as p90,
        max(n_products) as max_products
    from store_weeks
    group by category
    order by category
""").to_string(index=False))

#  check 7: store reporting per week
if run("7"):
    print("\nCheck 7: stores reporting each week")
    print(query_df("""
    with week_stores as (
        select
            category,
            WEEK,
            count(distinct STORE) as n_stores
        from movement
        where OK = 1 and MOVE > 0
        group by category, week
    )
    select
        category,
        count(*) as weeks,
        min(n_stores) as min_stores,
        round(quantile_cont(n_stores, 0.5), 0) as median_stores,
        max(n_stores) as max_stores,
        cast(countif(n_stores < 70 ) as bigint) as weeks_under_70
    from week_stores
    group by category
    order by category
""").to_string(index=False))


#  check 8: upc matching check
if run("8"):
    print("\nCheck 8: if products in sales are in the product file")
    print(query_df(f"""
    with upc as (
        select distinct UPC
        from read_csv(['{RAW}/upcber.csv', '{RAW}/upccer.csv', '{RAW}/upcsdr.csv'],
                      union_by_name = true, header = true, encoding = 'latin-1')
    ),

    sold as (
        select
            category,
            UPC,
            sum(PRICE * MOVE / QTY) as sales
        from movement
        where OK = 1 and MOVE > 0
        group by category, UPC
    )
    select
        s.category,
        count(*) as products_sold,
       cast(countif(u.upc is not null) as bigint) as products_matched,
       round(100* sum(case when u.UPC is not null then s.sales else 0 end)/sum(s.sales),2) as pct_sales_matched
    from sold as s
    left join upc as u
        on s.UPC = u.UPC
    group by s.category
    order by s.category
""").to_string(index=False))

#  check 9: promo check
if run("9"):
    print("\nCheck 9: promotion ")
    print(query_df("""
    select
        category,
        case when SALE is null then 'none' else SALE end as sale_code,
        count(*)                                        as rows,
        round(100 * count(*) / sum(count(*)) over (partition by category), 1)
                                                        as pct_rows,
        round(avg(MOVE), 1)                             as avg_units
    from movement
    where OK = 1 and MOVE > 0
    group by category, sale_code
    order by category, sale_code
""").to_string(index=False))