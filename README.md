# librarydb

This is is just a quick hack to generate a sample SQL database representing libraries, their holdings, and their circulation. It has no general utility for anybody; I just put it on github so I could share it with a couple specific people.

## gendb.py

```
usage: gendb.py [-h] [--db DB] [--book_pct BOOK_PCT]
                [--checkout_days CHECKOUT_DAYS] [--checkout_pct CHECKOUT_PCT]
                [--lib_pct LIB_PCT] [--err_pct ERR_PCT]
                [--states STATES [STATES ...]] [--seed SEED] [--books BOOKS]
                [--truerand]

Generate sample library database

optional arguments:
  -h, --help            show this help message and exit
  --db DB               Path for target DB
  --book_pct BOOK_PCT   Approximate percent of books in source CSV to include
  --checkout_days CHECKOUT_DAYS
                        Number of days of circulation to simulate
  --checkout_pct CHECKOUT_PCT
                        Approximate percent of library holdings checked out
                        each day
  --lib_pct LIB_PCT     Percent of libraries from each state to include
  --err_pct ERR_PCT     Percent of books with acquisition date error
  --states STATES [STATES ...]
                        Postal abbreviations of states to include
  --seed SEED           Extra degree of freedom for seeing RNG
  --books BOOKS         Path to source CSV for book data
  --truerand            Don't use reproducible random numbers
```

## Data Sources

**Libraries**: Dynamically loaded from [publiclibraries.com](https://publiclibraries.com).

**Books**: `dataset.csv` from [https://www.kaggle.com/sp1thas/book-depository-dataset](), extracted and renamed to `books.csv`.