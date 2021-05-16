#!/usr/bin/python

import bs4
import requests
import re
import logging
import csv
import argparse
import sqlite3
import time
from random import random, seed, randint, gauss, sample
from datetime import date, timedelta

from states import abbrev_us_state

class BookTemplate:
    def __init__ (self, title, pubdate, rating):
        self.title = title
        parts = pubdate.split('/')
        self.pubdate = date(int(parts[2]), int(parts[0]), int(parts[1]))
        self.rating = rating

    def __repr__ (self):
        return f'{self.title} ({self.pubdate.isoformat()})'

class Book:
    def __init__ (self, template, acdate):
        self.template = template
        self.acdate = acdate
        self.checkouts = []

    def checkout (self, when):
        if len(self.checkouts):
            last_checkout = self.checkouts[-1]
            if when <= last_checkout[1]:
                return False
        duration = max(1, round(gauss(14, 6)))
        self.checkouts.append((when, when + timedelta(days=duration)))
        return True

    def __repr__ (self):
        return f'{self.template.title} ({self.template.pubdate.isoformat()}) [{self.aqdate.isoformat()}]'

class Library:
    def __init__ (self, state, city, name):
        self.state = state
        self.city = city
        self.name = name
        self.collection = []

    def __repr__ (self):
        return f"[State] {self.state} [City] {self.city} [Name] {self.name}"

    def gen_collection (self, templates, err_pct):
        for template in templates:
            p = min(template.rating / 5.0, 0.9)
            while random() < p:
                # Generate acquisition date
                if random() < err_pct:
                    # Bad date
                    acdate = template.pubdate - timedelta(days=randint(1, 30))
                else:
                    # Good date
                    acdate = template.pubdate + timedelta(days=randint(0,60))
                self.collection.append(Book(template, acdate))
                # Possibly generate another copy with exponentially decreasing probability
                p = p ** 4

    def gen_checkouts (self, ndays, checkout_pct):
        today = date.today()
        checkouts_per_day = round(len(self.collection) * checkout_pct / 100.0)
        for i in range(ndays, 0, -1):
            when = today - timedelta(days=i)
            for book in sample(self.collection, checkouts_per_day):
                book.checkout(when)

def gen_libraries_for_state (abbrev, p):
    state = abbrev_us_state[abbrev]
    statekebab = '-'.join(state.lower().split(' '))
    url = f'https://publiclibraries.com/state/{statekebab}/'
    resp = requests.get(url)
    soup = bs4.BeautifulSoup(resp.text, 'html.parser')
    table = soup.find(id='libraries')
    trs = table.find_all('tr')
    libraries = []
    for tr in trs[1:]:
        if random() > p:
            continue
        tds = tr.find_all('td')
        city = tds[0].string
        rawlibname = tds[1].string
        # Sanitize and shorten library names
        parts = rawlibname.split('-')
        if (len(parts) == 1):
            libname = rawlibname
        else:
            libname = parts[1].strip()
        libraries.append(Library(abbrev, city, libname))
    return libraries

def gen_book_templates (books, p):
    templates = []
    booksfile = open(books)
    reader = csv.DictReader(booksfile)
    for book in reader:
        title = book['title']
        pubdate = book['publication_date']
        lang = book['language_code']
        try:
            rating = float(book['average_rating'])
        except ValueError:
            continue
        if title.find('The Great Gatsby') == -1 and (random() > p or lang != 'eng'):
            continue
        try:
            template = BookTemplate(title, pubdate, rating)
        except ValueError:
            continue
        templates.append(template)
    return templates

def gen_db (dbname, libraries):
    today = date.today()
    conn = sqlite3.connect(dbname)
    conn.execute("""
        create table LIBRARY (
            LIBRARY_KEY integer primary key,
            LIBRARY_NAME varchar(50),
            CITY varchar(50),
            STATE varchar(2)
        )""")
    conn.execute("""
        create table BOOK (
            BOOK_KEY integer primary key,
            LIBRARY_KEY integer,
            TITLE varchar(50),
            ACQUISITION_DATE datetime,
            PUBLICATION_DATE datetime
        )""")
    conn.execute("""
        create table BOOK_HISTORY (
            BOOK_HISTORY_KEY integer primary key,
            BOOK_KEY integer,
            CHECK_OUT_DATE datetime,
            CHECK_IN_DATE datetime
        )""")
    lib_key = 1
    book_key = 1
    book_history_key = 1
    for lib in libraries:
        conn.execute("insert into LIBRARY (LIBRARY_KEY, LIBRARY_NAME, CITY, STATE) values (?, ?, ?, ?)",
                     (lib_key, lib.name[:50], lib.city[:50], lib.state))
        for book in lib.collection:
            conn.execute("insert into BOOK (BOOK_KEY, LIBRARY_KEY, TITLE, ACQUISITION_DATE, PUBLICATION_DATE) values (?, ?, ?, ?, ?)",
                         (book_key, lib_key, book.template.title[:50], book.acdate, book.template.pubdate))
            for co in book.checkouts:
                if co[1] <= today:
                    conn.execute("insert into BOOK_HISTORY (BOOK_HISTORY_KEY, BOOK_KEY, CHECK_OUT_DATE, CHECK_IN_DATE) values (?, ?, ?, ?)",
                                 (book_history_key, book_key, co[0], co[1]))
                else:
                    conn.execute("insert into BOOK_HISTORY (BOOK_HISTORY_KEY, BOOK_KEY, CHECK_OUT_DATE) values (?, ?, ?)",
                                 (book_history_key, book_key, co[0]))
                book_history_key += 1
            book_key += 1
        conn.commit()
        lib_key += 1
    conn.close()

parser = argparse.ArgumentParser(description='Generate sample library database')
parser.add_argument('--db', type=str, default='library.db', help='Path for target DB')
parser.add_argument('--book_pct', type=float, default=20, help='Approximate percent of books in source CSV to include')
parser.add_argument('--checkout_days', type=int, default=50, help='Number of days of circulation to simulate')
parser.add_argument('--checkout_pct', type=float, default=2, help='Approximate percent of library holdings checked out each day')
parser.add_argument('--lib_pct', type=float, default=10, help='Percent of libraries from each state to include')
parser.add_argument('--err_pct', type=float, default=0.1, help='Percent of books with acquisition date error')
parser.add_argument('--states', nargs='+', default=['SC', 'NC', 'GA'], help='Postal abbreviations of states to include')
parser.add_argument('--seed', type=str, default='', help='Extra degree of freedom for seeing RNG')
parser.add_argument('--books', type=str, default='books.csv', help='Path to source CSV for book data')
parser.add_argument('--truerand', action='store_true', help="Don't use reproducible random numbers")

if __name__ == '__main__':
    logging.basicConfig(level=logging.WARN)
    args = parser.parse_args()
    if args.truerand:
        seed()
    else:
        seed(f'{args.seed}{str(args)}')
        #seed(f'{args.seed}{args.lib_pct}{args.book_pct}{"".join(args.states)}')
    # Get library data
    logging.info('Getting library data')
    libraries = []
    for abbrev in args.states:
        libraries += gen_libraries_for_state(abbrev, args.lib_pct / 100.0)
    logging.info('Parsing book data')
    templates = gen_book_templates(args.books, args.book_pct / 100.0)
    for lib in libraries:
        logging.info(f'Generating collection for {lib.name}')
        lib.gen_collection(templates, args.err_pct / 100.0)
        logging.info(f'Generating checkouts for {lib.name}')
        lib.gen_checkouts(args.checkout_days, args.checkout_pct)
    gen_db(args.db, libraries)

