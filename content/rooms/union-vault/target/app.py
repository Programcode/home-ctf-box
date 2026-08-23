"""GadgetHub: catalog search glued into a two-column SQL query. Room target only."""

import os
import sqlite3

from flask import Flask, request
from markupsafe import escape

app = Flask(__name__)
FLAG = os.environ["ROOM_FLAG"]
DB = "/tmp/shop.db"

PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>GadgetHub</title>
<style>
body { background:#F7F6F3; font-family:'Helvetica Neue',Helvetica,Arial,sans-serif; display:flex; justify-content:center; padding-top:12vh; }
.box { background:#fff; border:1px solid #EAEAEA; border-radius:8px; padding:2.5rem; width:26rem; }
h1 { font-family:Georgia,serif; letter-spacing:-0.02em; font-size:1.4rem; margin-bottom:1rem; }
p { color:#787774; font-size:.88rem; }
li { margin:.35rem 0; font-size:.92rem; color:#111; }
pre { font-family:ui-monospace,Menlo,monospace; font-size:.8rem; background:#F7F6F3; border:1px solid #EAEAEA; border-radius:4px; padding:.7rem; overflow:auto; white-space:pre-wrap; word-break:break-all; }
code { font-family:ui-monospace,Menlo,monospace; font-size:.85rem; background:#F7F6F3; border:1px solid #EAEAEA; border-radius:4px; padding:.1rem .4rem; }
</style></head><body>{BODY}</body></html>"""


def page(body):
    return PAGE.replace("{BODY}", body)


def init():
    con = sqlite3.connect(DB)
    con.execute("CREATE TABLE IF NOT EXISTS products(id INTEGER, name TEXT, price REAL)")
    if con.execute("SELECT COUNT(*) FROM products").fetchone()[0] == 0:
        con.executemany(
            "INSERT INTO products VALUES(?,?,?)",
            [(1, "USB-C Cable", 9.99), (2, "Desk Mat", 24.5), (3, "Webcam Cover", 3.5)],
        )
    con.execute("CREATE TABLE IF NOT EXISTS vault(secret TEXT)")
    if con.execute("SELECT COUNT(*) FROM vault").fetchone()[0] == 0:
        con.execute("INSERT INTO vault VALUES(?)", (FLAG,))
    con.commit()
    con.close()


@app.get("/healthz")
def healthz():
    return "ok"


@app.get("/")
@app.get("/products")
def products():
    q = request.args.get("q", "")
    # The intern's query: the search term is glued straight into the SQL string.
    sql = f"SELECT name, price FROM products WHERE name LIKE '%{q}%'"
    con = sqlite3.connect(DB)
    try:
        rows = con.execute(sql).fetchall()
    except sqlite3.Error as exc:
        con.close()
        return page(f'<div class="box"><h1>Search error</h1><pre>{escape(str(exc))}</pre></div>')
    con.close()
    items = "".join(f"<li>{escape(str(name))} - {escape(str(price))}</li>" for name, price in rows)
    return page(
        '<div class="box"><h1>GadgetHub</h1>'
        f"<ul>{items}</ul>"
        "<p>Search the catalog: <code>/products?q=cable</code></p></div>"
    )


init()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
