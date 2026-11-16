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
print("\nCheck 2: suspect rows (OK = 0) per category")
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