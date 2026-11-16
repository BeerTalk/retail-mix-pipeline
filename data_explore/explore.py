""" data exploration: Dominick's beer, cereal and soft drinks.

DuckDB reads the CSVs directly, so the 1.2 GB soft drinks file never has to fit in memory.
"""
import duckdb

RAW = "data/raw"
con = duckdb.connect()

# one view over all three movement files, with a category col from the file name
con.execute(f"""
    create view movement as
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


def query_df(sql: str):
    """Run a SQL query and return the result as a pandas DataFrame."""
    return con.execute(sql).df()


# check 1: size and time per category
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