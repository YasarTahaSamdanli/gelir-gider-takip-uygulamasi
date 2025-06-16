# database_manager.py
import sqlite3
import json
from datetime import datetime


class DatabaseManager:
    def __init__(self, db_name="veriler.db"):
        """
        Veritabanı bağlantısını ve yönetimini başlatır.
        Args:
            db_name (str): Kullanılacak SQLite veritabanı dosyasının adı.
        """
        self.db_name = db_name
        self.conn = None
        self.cursor = None
        self.connect()
        self.create_tables()

    def connect(self):
        """SQLite veritabanına bağlanır."""
        try:
            self.conn = sqlite3.connect(self.db_name)
            self.cursor = self.conn.cursor()
        except sqlite3.Error as e:
            raise ConnectionError(f"Veritabanı bağlantısı kurulamadı: {e}")

    def create_tables(self):
        """Uygulama için gerekli tüm tabloları oluşturur veya günceller."""
        # 1. users tablosu
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kullanici_adi TEXT NOT NULL UNIQUE,
                sifre_hash TEXT NOT NULL,
                login_attempts INTEGER DEFAULT 0,
                lockout_until TEXT,
                last_invoice_num INTEGER DEFAULT 0,
                last_offer_num INTEGER DEFAULT 0
            )
        """)
        self._add_column_if_not_exists('users', 'last_invoice_num', 'INTEGER DEFAULT 0')
        self._add_column_if_not_exists('users', 'last_offer_num', 'INTEGER DEFAULT 0')

        # 2. categories tablosu
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kategori_adi TEXT NOT NULL UNIQUE,
                tur TEXT NOT NULL, 
                kullanici_id INTEGER NOT NULL
            )
        """)

        # 3. islemler tablosu
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS islemler (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tur TEXT NOT NULL,
                miktar REAL NOT NULL,
                kategori TEXT,
                aciklama TEXT,
                tarih TEXT NOT NULL,
                kullanici_id INTEGER NOT NULL
            )
        """)

        # 4. tekrar_eden_islemler tablosu
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS tekrar_eden_islemler (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tur TEXT NOT NULL,
                miktar REAL NOT NULL,
                kategori TEXT,
                aciklama TEXT,
                baslangic_tarihi TEXT NOT NULL,
                siklilik TEXT NOT NULL,
                son_uretilen_tarih TEXT,
                kullanici_id INTEGER NOT NULL
            )
        """)

        # 5. fatura_teklifler tablosu
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS fatura_teklifler (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tur TEXT NOT NULL, 
                belge_numarasi TEXT UNIQUE, 
                musteri_adi TEXT NOT NULL,
                belge_tarihi TEXT NOT NULL,
                son_odeme_gecerlilik_tarihi TEXT, 
                urun_hizmetler_json TEXT NOT NULL, 
                toplam_tutar REAL NOT NULL,
                toplam_kdv REAL DEFAULT 0.0, 
                notlar TEXT,
                durum TEXT NOT NULL, 
                kullanici_id INTEGER NOT NULL
            )
        """)
        self._add_column_if_not_exists('fatura_teklifler', 'belge_numarasi', 'TEXT UNIQUE')
        self._add_column_if_not_exists('fatura_teklifler', 'toplam_kdv', 'REAL DEFAULT 0.0')

        # 6. customers tablosu
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                musteri_adi TEXT NOT NULL UNIQUE,
                adres TEXT,
                telefon TEXT,
                email TEXT,
                kullanici_id INTEGER NOT NULL
            )
        """)

        # 7. products tablosu (Envanter için)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                urun_adi TEXT NOT NULL UNIQUE,
                stok_miktari REAL DEFAULT 0.0,
                alis_fiyati REAL DEFAULT 0.0,
                satis_fiyati REAL DEFAULT 0.0,
                kdv_orani REAL DEFAULT 0.0,
                kullanici_id INTEGER NOT NULL
            )
        """)
        self._add_column_if_not_exists('products', 'kdv_orani', 'REAL DEFAULT 0.0')

        self.conn.commit()

    def _add_column_if_not_exists(self, table_name, column_name, column_type):
        """Bir tabloya sütun ekler, eğer henüz yoksa."""
        self.cursor.execute(f"PRAGMA table_info({table_name});")
        cols = [col[1] for col in self.cursor.fetchall()]
        if column_name not in cols:
            self.cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")
            self.conn.commit()

    def close(self):
        """Veritabanı bağlantısını kapatır."""
        if self.conn:
            self.conn.close()

    # --- User (Kullanıcı) Metodları ---
    def get_user_by_username(self, username):
        """Kullanıcı adına göre kullanıcı verilerini getirir."""
        self.cursor.execute("SELECT id, sifre_hash, login_attempts, lockout_until FROM users WHERE kullanici_adi = ?",
                            (username,))
        return self.cursor.fetchone()

    def update_user_login_attempts(self, user_id, attempts, lockout_until=None):
        """Kullanıcının giriş denemelerini ve kilitlenme zamanını günceller."""
        self.cursor.execute("UPDATE users SET login_attempts = ?, lockout_until = ? WHERE id = ?",
                            (attempts, lockout_until, user_id))
        self.conn.commit()

    def insert_user(self, username, hashed_password):
        """Yeni bir kullanıcı ekler."""
        self.cursor.execute(
            "INSERT INTO users (kullanici_adi, sifre_hash, login_attempts, lockout_until) VALUES (?, ?, ?, ?)",
            (username, hashed_password, 0, None))
        self.conn.commit()
        return self.cursor.lastrowid  # Yeni eklenen kullanıcının ID'sini döndür

    def get_user_invoice_offer_nums(self, user_id):
        """Kullanıcının son fatura ve teklif numaralarını getirir."""
        self.cursor.execute("SELECT last_invoice_num, last_offer_num FROM users WHERE id = ?", (user_id,))
        return self.cursor.fetchone()

    def update_user_invoice_offer_num(self, user_id, invoice_num=None, offer_num=None):
        """Kullanıcının son fatura veya teklif numarasını günceller."""
        if invoice_num is not None:
            self.cursor.execute("UPDATE users SET last_invoice_num = ? WHERE id = ?", (invoice_num, user_id))
        if offer_num is not None:
            self.cursor.execute("UPDATE users SET last_offer_num = ? WHERE id = ?", (offer_num, user_id))
        self.conn.commit()

    # --- Transaction (İşlem) Metodları ---
    def insert_transaction(self, tur, miktar, kategori, aciklama, tarih, kullanici_id):
        """Yeni bir gelir/gider işlemi ekler."""
        self.cursor.execute("""
            INSERT INTO islemler (tur, miktar, kategori, aciklama, tarih, kullanici_id)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (tur, miktar, kategori, aciklama, tarih, kullanici_id))
        self.conn.commit()

    def update_transaction(self, id, tur, miktar, kategori, aciklama, tarih, kullanici_id):
        """Mevcut bir işlemi günceller."""
        self.cursor.execute("""
            UPDATE islemler SET tur = ?, miktar = ?, kategori = ?, aciklama = ?, tarih = ?
            WHERE id = ? AND kullanici_id = ?
        """, (tur, miktar, kategori, aciklama, tarih, id, kullanici_id))
        self.conn.commit()

    def delete_transaction(self, id, kullanici_id):
        """Bir işlemi siler."""
        self.cursor.execute("DELETE FROM islemler WHERE id = ? AND kullanici_id = ?", (id, kullanici_id))
        self.conn.commit()

    def get_transactions(self, kullanici_id, tur="Tümü", kategori="Tümü", bas_tarih="", bit_tarih="", arama_terimi=""):
        """Filtrelenmiş işlemleri getirir."""
        sql = "SELECT id, tur, miktar, kategori, aciklama, tarih FROM islemler WHERE kullanici_id = ?"
        params = [kullanici_id]

        if tur != "Tümü":
            sql += " AND tur = ?"
            params.append(tur)

        if kategori != "Tümü":
            sql += " AND kategori = ?"
            params.append(kategori)

        if bas_tarih:
            sql += " AND tarih >= ?"
            params.append(bas_tarih)

        if bit_tarih:
            sql += " AND tarih <= ?"
            params.append(bit_tarih)

        if arama_terimi:
            sql += " AND (aciklama LIKE ? OR kategori LIKE ?)"
            params.append(f"%{arama_terimi}%")
            params.append(f"%{arama_terimi}%")

        sql += " ORDER BY tarih DESC, id DESC"

        self.cursor.execute(sql, params)
        return self.cursor.fetchall()

    def get_transaction_for_charts(self, kullanici_id):
        """Grafikler için işlem verilerini getirir."""
        self.cursor.execute("""
            SELECT tur, kategori, SUM(miktar) FROM islemler WHERE kullanici_id = ? GROUP BY tur, kategori
        """, (kullanici_id,))
        kategori_verileri = self.cursor.fetchall()

        self.cursor.execute("""
            SELECT tarih, tur, miktar FROM islemler WHERE kullanici_id = ? ORDER BY tarih ASC
        """, (kullanici_id,))
        zaman_verileri = self.cursor.fetchall()
        return kategori_verileri, zaman_verileri

    # --- Recurring Transaction (Tekrarlayan İşlem) Metodları ---
    def insert_recurring_transaction(self, tur, miktar, kategori, aciklama, baslangic_tarihi, siklilik,
                                     son_uretilen_tarih, kullanici_id):
        """Yeni bir tekrarlayan işlem ekler."""
        self.cursor.execute("""
            INSERT INTO tekrar_eden_islemler (tur, miktar, kategori, aciklama, baslangic_tarihi, siklilik, son_uretilen_tarih, kullanici_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (tur, miktar, kategori, aciklama, baslangic_tarihi, siklilik, son_uretilen_tarih, kullanici_id))
        self.conn.commit()

    def delete_recurring_transaction(self, id, kullanici_id):
        """Bir tekrarlayan işlemi siler."""
        self.cursor.execute("DELETE FROM tekrar_eden_islemler WHERE id = ? AND kullanici_id = ?", (id, kullanici_id))
        self.conn.commit()

    def get_recurring_transactions(self, kullanici_id):
        """Tekrarlayan işlemleri getirir."""
        self.cursor.execute(
            "SELECT id, tur, miktar, kategori, aciklama, baslangic_tarihi, siklilik, son_uretilen_tarih FROM tekrar_eden_islemler WHERE kullanici_id = ? ORDER BY baslangic_tarihi DESC",
            (kullanici_id,))
        return self.cursor.fetchall()

    def update_recurring_transaction_last_generated_date(self, id, son_uretilen_tarih):
        """Tekrarlayan işlemin son üretildiği tarihi günceller."""
        self.cursor.execute("UPDATE tekrar_eden_islemler SET son_uretilen_tarih = ? WHERE id = ?",
                            (son_uretilen_tarih, id))
        self.conn.commit()

    # --- Category (Kategori) Metodları ---
    def get_categories_for_user(self, kullanici_id):
        """Belirli bir kullanıcıya ait kategorileri getirir."""
        self.cursor.execute(
            "SELECT id, kategori_adi, tur FROM categories WHERE kullanici_id = ? ORDER BY kategori_adi ASC",
            (kullanici_id,))
        return self.cursor.fetchall()

    def insert_category(self, kategori_adi, tur, kullanici_id):
        """Yeni bir kategori ekler."""
        self.cursor.execute("INSERT INTO categories (kategori_adi, tur, kullanici_id) VALUES (?, ?, ?)",
                            (kategori_adi, tur, kullanici_id))
        self.conn.commit()

    def delete_category(self, id, kullanici_id):
        """Bir kategoriyi siler."""
        self.cursor.execute("DELETE FROM categories WHERE id = ? AND kullanici_id = ?", (id, kullanici_id))
        self.conn.commit()

    def update_transactions_category_to_null(self, kategori_adi, kullanici_id):
        """Silinen kategorinin kullanıldığı işlemlerde kategori bilgisini NULL yapar."""
        self.cursor.execute("UPDATE islemler SET kategori = NULL WHERE kategori = ? AND kullanici_id = ?",
                            (kategori_adi, kullanici_id))
        self.cursor.execute("UPDATE tekrar_eden_islemler SET kategori = NULL WHERE kategori = ? AND kullanici_id = ?",
                            (kategori_adi, kullanici_id))
        self.conn.commit()

    def get_category_by_name(self, kategori_adi, kullanici_id):
        """Kategori adına göre kategori getirir."""
        self.cursor.execute("SELECT id FROM categories WHERE kategori_adi = ? AND kullanici_id = ?",
                            (kategori_adi, kullanici_id))
        return self.cursor.fetchone()

    def count_transactions_by_category(self, kategori_adi, kullanici_id):
        """Belirli bir kategorinin kaç işlemde kullanıldığını sayar."""
        self.cursor.execute("SELECT COUNT(*) FROM islemler WHERE kategori = ? AND kullanici_id = ?",
                            (kategori_adi, kullanici_id))
        return self.cursor.fetchone()[0]

    # --- Invoice/Offer (Fatura/Teklif) Metodları ---
    def insert_invoice_offer(self, tur, belge_numarasi, musteri_adi, belge_tarihi, son_odeme_gecerlilik_tarihi,
                             urun_hizmetler_json, toplam_tutar, toplam_kdv, notlar, durum, kullanici_id):
        """Yeni bir fatura veya teklif ekler."""
        self.cursor.execute("""
            INSERT INTO fatura_teklifler (tur, belge_numarasi, musteri_adi, belge_tarihi, son_odeme_gecerlilik_tarihi, urun_hizmetler_json, toplam_tutar, toplam_kdv, notlar, durum, kullanici_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (tur, belge_numarasi, musteri_adi, belge_tarihi, son_odeme_gecerlilik_tarihi, urun_hizmetler_json,
              toplam_tutar, toplam_kdv, notlar, durum, kullanici_id))
        self.conn.commit()

    def update_invoice_offer(self, id, tur, belge_numarasi, musteri_adi, belge_tarihi, son_odeme_gecerlilik_tarihi,
                             urun_hizmetler_json, toplam_tutar, toplam_kdv, notlar, durum, kullanici_id):
        """Mevcut bir fatura veya teklifi günceller."""
        self.cursor.execute("""
            UPDATE fatura_teklifler SET tur = ?, belge_numarasi = ?, musteri_adi = ?, belge_tarihi = ?, son_odeme_gecerlilik_tarihi = ?, urun_hizmetler_json = ?, toplam_tutar = ?, toplam_kdv = ?, notlar = ?, durum = ?
            WHERE id = ? AND kullanici_id = ?
        """, (tur, belge_numarasi, musteri_adi, belge_tarihi, son_odeme_gecerlilik_tarihi, urun_hizmetler_json,
              toplam_tutar, toplam_kdv, notlar, durum, id, kullanici_id))
        self.conn.commit()

    def delete_invoice_offer(self, id, kullanici_id):
        """Bir fatura veya teklifi siler."""
        self.cursor.execute("DELETE FROM fatura_teklifler WHERE id = ? AND kullanici_id = ?", (id, kullanici_id))
        self.conn.commit()

    def get_invoice_offers(self, kullanici_id):
        """Tüm fatura ve teklifleri getirir."""
        self.cursor.execute(
            "SELECT id, tur, belge_numarasi, musteri_adi, toplam_tutar, toplam_kdv, (toplam_tutar + toplam_kdv), belge_tarihi, durum FROM fatura_teklifler WHERE kullanici_id = ? ORDER BY belge_tarihi DESC",
            (kullanici_id,))
        return self.cursor.fetchall()

    def get_invoice_offer_by_id(self, id, kullanici_id):
        """ID'ye göre fatura veya teklif getirir."""
        self.cursor.execute(
            "SELECT tur, belge_numarasi, musteri_adi, belge_tarihi, son_odeme_gecerlilik_tarihi, urun_hizmetler_json, toplam_tutar, toplam_kdv, notlar, durum FROM fatura_teklifler WHERE id = ? AND kullanici_id = ?",
            (id, kullanici_id))
        return self.cursor.fetchone()

    def check_belge_numarasi_exists(self, belge_numarasi, kullanici_id):
        """Belge numarasının veritabanında mevcut olup olmadığını kontrol eder."""
        self.cursor.execute("SELECT id FROM fatura_teklifler WHERE belge_numarasi = ? AND kullanici_id = ?",
                            (belge_numarasi, kullanici_id))
        return self.cursor.fetchone() is not None

    def get_invoice_offer_by_belge_numarasi(self, belge_numarasi, kullanici_id):
        """Belge numarasına göre fatura veya teklif getirir."""
        self.cursor.execute("SELECT id FROM fatura_teklifler WHERE belge_numarasi = ? AND kullanici_id = ?",
                            (belge_numarasi, kullanici_id))
        return self.cursor.fetchone()

    # --- Customer (Müşteri) Metodları ---
    def get_customers(self, kullanici_id):
        """Tüm müşterileri getirir."""
        self.cursor.execute(
            "SELECT id, musteri_adi, adres, telefon, email FROM customers WHERE kullanici_id = ? ORDER BY musteri_adi ASC",
            (kullanici_id,))
        return self.cursor.fetchall()

    def insert_customer(self, musteri_adi, adres, telefon, email, kullanici_id):
        """Yeni bir müşteri ekler."""
        self.cursor.execute(
            "INSERT INTO customers (musteri_adi, adres, telefon, email, kullanici_id) VALUES (?, ?, ?, ?, ?)",
            (musteri_adi, adres, telefon, email, kullanici_id))
        self.conn.commit()

    def update_customer(self, id, musteri_adi, adres, telefon, email, kullanici_id):
        """Mevcut bir müşteriyi günceller."""
        self.cursor.execute("""
            UPDATE customers SET musteri_adi = ?, adres = ?, telefon = ?, email = ?
            WHERE id = ? AND kullanici_id = ?
        """, (musteri_adi, adres, telefon, email, id, kullanici_id))
        self.conn.commit()

    def delete_customer(self, id, kullanici_id):
        """Bir müşteriyi siler."""
        self.cursor.execute("DELETE FROM customers WHERE id = ? AND kullanici_id = ?", (id, kullanici_id))
        self.conn.commit()

    def get_customer_by_id(self, id):
        """ID'ye göre müşteri getirir."""
        self.cursor.execute("SELECT musteri_adi FROM customers WHERE id = ?", (id,))
        return self.cursor.fetchone()

    def get_customer_by_name(self, musteri_adi, kullanici_id):
        """Müşteri adına göre müşteri getirir."""
        self.cursor.execute(
            "SELECT id, adres, telefon, email FROM customers WHERE musteri_adi = ? AND kullanici_id = ?",
            (musteri_adi, kullanici_id))
        return self.cursor.fetchone()

    def count_invoices_by_customer(self, musteri_adi, kullanici_id):
        """Belirli bir müşterinin kaç fatura/teklifte kullanıldığını sayar."""
        self.cursor.execute("SELECT COUNT(*) FROM fatura_teklifler WHERE musteri_adi = ? AND kullanici_id = ?",
                            (musteri_adi, kullanici_id))
        return self.cursor.fetchone()[0]

    def update_invoice_customer_name(self, old_musteri_adi, new_musteri_adi, kullanici_id):
        """Müşteri adı değiştiğinde fatura/tekliflerdeki müşteri adını günceller."""
        self.cursor.execute("UPDATE fatura_teklifler SET musteri_adi = ? WHERE musteri_adi = ? AND kullanici_id = ?",
                            (new_musteri_adi, old_musteri_adi, kullanici_id))
        self.conn.commit()

    # --- Product (Ürün) Metodları (Envanter) ---
    def get_products(self, kullanici_id):
        """Tüm ürünleri getirir."""
        self.cursor.execute(
            "SELECT id, urun_adi, stok_miktari, alis_fiyati, satis_fiyati, kdv_orani FROM products WHERE kullanici_id = ? ORDER BY urun_adi ASC",
            (kullanici_id,))
        return self.cursor.fetchall()

    def insert_product(self, urun_adi, stok_miktari, alis_fiyati, satis_fiyati, kdv_orani, kullanici_id):
        """Yeni bir ürün ekler."""
        self.cursor.execute(
            "INSERT INTO products (urun_adi, stok_miktari, alis_fiyati, satis_fiyati, kdv_orani, kullanici_id) VALUES (?, ?, ?, ?, ?, ?)",
            (urun_adi, stok_miktari, alis_fiyati, satis_fiyati, kdv_orani, kullanici_id))
        self.conn.commit()

    def update_product(self, id, urun_adi, stok_miktari, alis_fiyati, satis_fiyati, kdv_orani, kullanici_id):
        """Mevcut bir ürünü günceller."""
        self.cursor.execute("""
            UPDATE products SET urun_adi = ?, stok_miktari = ?, alis_fiyati = ?, satis_fiyati = ?, kdv_orani = ?
            WHERE id = ? AND kullanici_id = ?
        """, (urun_adi, stok_miktari, alis_fiyati, satis_fiyati, kdv_orani, id, kullanici_id))
        self.conn.commit()

    def delete_product(self, id, kullanici_id):
        """Bir ürünü siler."""
        self.cursor.execute("DELETE FROM products WHERE id = ? AND kullanici_id = ?", (id, kullanici_id))
        self.conn.commit()

    def get_product_by_name(self, urun_adi, kullanici_id):
        """Ürün adına göre ürün getirir."""
        self.cursor.execute(
            "SELECT id, stok_miktari, alis_fiyati, satis_fiyati, kdv_orani FROM products WHERE urun_adi = ? AND kullanici_id = ?",
            (urun_adi, kullanici_id))
        return self.cursor.fetchone()

    def update_product_stock(self, product_id, new_stock):
        """Ürün stok miktarını günceller."""
        self.cursor.execute("UPDATE products SET stok_miktari = ? WHERE id = ?", (new_stock, product_id))
        self.conn.commit()

    # --- Tax (Vergi) Metodları ---
    def get_total_sales_kdv(self, bas_tarih, bit_tarih, kullanici_id):
        """Belirli bir tarih aralığındaki toplam satış KDV'sini getirir."""
        self.cursor.execute("""
            SELECT SUM(toplam_kdv) FROM fatura_teklifler 
            WHERE tur = 'Fatura' AND belge_tarihi >= ? AND belge_tarihi <= ? AND kullanici_id = ?
        """, (bas_tarih, bit_tarih, kullanici_id))
        return self.cursor.fetchone()[0] or 0.0

    def get_invoice_jsons_for_tax_report(self, bas_tarih, bit_tarih, kullanici_id):
        """Vergi raporu için faturaların JSON verilerini getirir."""
        self.cursor.execute("""
            SELECT urun_hizmetler_json FROM fatura_teklifler 
            WHERE tur = 'Fatura' AND belge_tarihi >= ? AND belge_tarihi <= ? AND kullanici_id = ?
        """, (bas_tarih, bit_tarih, kullanici_id))
        return self.cursor.fetchall()

