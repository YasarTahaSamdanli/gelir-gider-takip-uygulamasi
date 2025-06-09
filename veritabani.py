import sqlite3

def veritabani_olustur():
    con = sqlite3.connect("veriler.db")
    cursor = con.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS islemler (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tur TEXT,
            miktar REAL,
            kategori TEXT,
            aciklama TEXT,
            tarih TEXT
        )
    """)
    con.commit()
    con.close()

veritabani_olustur()
