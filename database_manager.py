import sqlite3
import bcrypt  # bcrypt kütüphanesini import ediyoruz
from datetime import datetime, timedelta
import pandas as pd


class DatabaseManager:
    def __init__(self, db_name="veriler.db"):
        self.db_name = db_name
        self.conn = None
        self.cursor = None
        self.connect()
        self.create_tables()

    def connect(self):
        """Veritabanına bağlanır."""
        try:
            self.conn = sqlite3.connect(self.db_name)
            self.cursor = self.conn.cursor()
            print(f"Veritabanı bağlantısı '{self.db_name}' başarıyla kuruldu.")
        except sqlite3.Error as e:
            print(f"Veritabanı bağlantı hatası: {e}")

    def close(self):
        """Veritabanı bağlantısını kapatır."""
        if self.conn:
            self.conn.close()
            print("Veritabanı bağlantısı kapatıldı.")

    def create_tables(self):
        """Gerekli tabloları oluşturur veya kontrol eder."""
        try:
            # Kullanıcılar tablosu
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    last_invoice_num INTEGER DEFAULT 0,
                    last_offer_num INTEGER DEFAULT 0
                )
            """)
            # İşlemler tablosu (gelir/gider)
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    type TEXT NOT NULL, -- 'Gelir' veya 'Gider'
                    amount REAL NOT NULL,
                    category TEXT,
                    description TEXT,
                    date TEXT NOT NULL, -- YYYY-MM-DD formatında sakla
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)
            # Tekrarlayan İşlemler Tablosu
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS recurring_transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    description TEXT NOT NULL,
                    amount REAL NOT NULL,
                    type TEXT NOT NULL,
                    category TEXT,
                    start_date TEXT NOT NULL, -- YYYY-MM-DD
                    frequency TEXT NOT NULL, -- 'Günlük', 'Haftalık', 'Aylık', 'Yıllık'
                    last_generated_date TEXT, -- Son otomatik oluşturulma tarihi
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)
            # Tasarruf Hedefleri Tablosu
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS savings_goals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    goal_name TEXT NOT NULL,
                    target_amount REAL NOT NULL,
                    current_amount REAL DEFAULT 0.0,
                    target_date TEXT, -- YYYY-MM-DD
                    description TEXT,
                    status TEXT DEFAULT 'Devam Ediyor', -- 'Devam Ediyor', 'Tamamlandı', 'İptal Edildi'
                    FOREIGN KEY (user_id) REFERENCES users(id),
                    UNIQUE(user_id, goal_name) -- Her kullanıcının aynı isimde iki hedefi olamaz
                )
            """)
            # Müşteriler Tablosu
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS customers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    address TEXT,
                    phone TEXT,
                    email TEXT,
                    FOREIGN KEY (user_id) REFERENCES users(id),
                    UNIQUE(user_id, name)
                )
            """)
            # Ürünler/Hizmetler Tablosu
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    stock REAL DEFAULT 0.0,
                    purchase_price REAL DEFAULT 0.0,
                    selling_price REAL DEFAULT 0.0,
                    kdv_rate REAL DEFAULT 0.0, -- KDV oranı yüzde olarak (örn: 18.0)
                    FOREIGN KEY (user_id) REFERENCES users(id),
                    UNIQUE(user_id, name)
                )
            """)
            # Fatura/Teklifler Tablosu
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS invoices_offers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    type TEXT NOT NULL, -- 'Fatura' veya 'Teklif'
                    document_number TEXT UNIQUE NOT NULL,
                    customer_name TEXT NOT NULL,
                    document_date TEXT NOT NULL, -- YYYY-MM-DD
                    due_validity_date TEXT, -- Vade veya geçerlilik tarihi YYYY-MM-DD
                    items_json TEXT NOT NULL, -- JSON formatında ürün/hizmet kalemleri listesi
                    total_amount_excluding_kdv REAL NOT NULL,
                    total_kdv_amount REAL NOT NULL,
                    total_amount_with_kdv REAL NOT NULL,
                    notes TEXT,
                    status TEXT DEFAULT 'Taslak', -- 'Taslak', 'Gönderildi', 'Ödendi', 'İptal Edildi'
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)
            # Kategoriler Tablosu
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS categories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    type TEXT NOT NULL, -- 'Gelir', 'Gider' veya 'Genel'
                    FOREIGN KEY (user_id) REFERENCES users(id),
                    UNIQUE(user_id, name)
                )
            """)

            # users tablosuna 'last_invoice_num' ve 'last_offer_num' sütunlarını ekle (eğer yoksa)
            self._add_column_if_not_exists('users', 'last_invoice_num', 'INTEGER DEFAULT 0')
            self._add_column_if_not_exists('users', 'last_offer_num', 'INTEGER DEFAULT 0')

            # invoices_offers tablosuna 'total_amount_with_kdv' sütununu ekle (eğer yoksa)
            self._add_column_if_not_exists('invoices_offers', 'total_amount_with_kdv', 'REAL')

            # recurring_transactions tablosuna 'category' sütununu ekle (eğer yoksa)
            self._add_column_if_not_exists('recurring_transactions', 'category', 'TEXT')

            self.conn.commit()
            print("Tablolar başarıyla kontrol edildi/oluşturuldu.")
        except sqlite3.Error as e:
            print(f"Tablo oluşturma hatası: {e}")

    def _add_column_if_not_exists(self, table_name, column_name, column_definition):
        """Belirtilen tabloya sütun ekler, eğer sütun yoksa."""
        self.cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [column[1] for column in self.cursor.fetchall()]
        if column_name not in columns:
            try:
                self.cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}")
                self.conn.commit()
                print(f"'{table_name}' tablosuna '{column_name}' sütunu eklendi.")
            except sqlite3.Error as e:
                print(f"'{table_name}' tablosuna '{column_name}' sütunu eklenirken hata: {e}")

    # --- Kullanıcı Yönetimi ---
    def add_user(self, username, password):
        """Yeni bir kullanıcı ekler."""
        from utils import hash_password_bcrypt
        hashed_password = hash_password_bcrypt(password)
        try:
            self.cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed_password))
            self.conn.commit()
            print(f"Kullanıcı '{username}' başarıyla eklendi.")
            return True
        except sqlite3.IntegrityError:
            print(f"Hata: '{username}' kullanıcı adı zaten mevcut.")
            return False
        except sqlite3.Error as e:
            print(f"Kullanıcı ekleme hatası: {e}")
            return False

    def check_user(self, username, password):
        """Kullanıcı adı ve şifreyi kontrol eder, başarılıysa kullanıcı ID'sini döner."""
        from utils import check_password_bcrypt
        self.cursor.execute("SELECT id, password FROM users WHERE username = ?", (username,))
        result = self.cursor.fetchone()
        if result:
            user_id, hashed_password = result
            if check_password_bcrypt(hashed_password, password):
                return user_id
        return None

    def get_user_invoice_offer_nums(self, user_id):
        """Belirli bir kullanıcı için son fatura ve teklif numaralarını alır."""
        self.cursor.execute("SELECT last_invoice_num, last_offer_num FROM users WHERE id = ?", (user_id,))
        result = self.cursor.fetchone()
        if result:
            return result
        return 0, 0  # Varsayılan değerler

    def update_user_invoice_offer_num(self, user_id, invoice_num=None, offer_num=None):
        """Belirli bir kullanıcı için fatura veya teklif numarasını günceller."""
        if invoice_num is not None:
            self.cursor.execute("UPDATE users SET last_invoice_num = ? WHERE id = ?", (invoice_num, user_id))
        if offer_num is not None:
            self.cursor.execute("UPDATE users SET last_offer_num = ? WHERE id = ?", (offer_num, user_id))
        self.conn.commit()

    # --- İşlem Yönetimi (Gelir/Gider) ---
    def insert_transaction(self, type, amount, category, description, date, user_id):
        """Yeni bir gelir veya gider işlemi ekler."""
        try:
            self.cursor.execute(
                "INSERT INTO transactions (user_id, type, amount, category, description, date) VALUES (?, ?, ?, ?, ?, ?)",
                (user_id, type, amount, category, description, date))
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"İşlem ekleme hatası: {e}")
            return False

    def get_transactions(self, user_id, type_filter=None, category_filter=None, start_date=None, end_date=None,
                         search_term=None):
        """Belirli kriterlere göre işlemleri getirir."""
        query = "SELECT id, date, type, amount, category, description FROM transactions WHERE user_id = ?"
        params = [user_id]

        if type_filter:
            query += " AND type = ?"
            params.append(type_filter)
        if category_filter:
            query += " AND category = ?"
            params.append(category_filter)
        if start_date:
            query += " AND date >= ?"
            params.append(start_date)
        if end_date:
            query += " AND date <= ?"
            params.append(end_date)
        if search_term:
            query += " AND (description LIKE ? OR category LIKE ?)"
            params.append(f"%{search_term}%")
            params.append(f"%{search_term}%")

        query += " ORDER BY date DESC"

        self.cursor.execute(query, params)
        return self.cursor.fetchall()

    def update_transaction(self, transaction_id, type, amount, category, description, date, user_id):
        """Mevcut bir işlemi günceller."""
        try:
            self.cursor.execute(
                "UPDATE transactions SET type = ?, amount = ?, category = ?, description = ?, date = ? WHERE id = ? AND user_id = ?",
                (type, amount, category, description, date, transaction_id, user_id))
            self.conn.commit()
            return self.cursor.rowcount > 0
        except sqlite3.Error as e:
            print(f"İşlem güncelleme hatası: {e}")
            return False

    def delete_transaction(self, transaction_id, user_id):
        """Bir işlemi siler."""
        try:
            self.cursor.execute("DELETE FROM transactions WHERE id = ? AND user_id = ?", (transaction_id, user_id))
            self.conn.commit()
            return self.cursor.rowcount > 0
        except sqlite3.Error as e:
            print(f"İşlem silme hatası: {e}")
            return False

    def get_balance(self, user_id):
        """Kullanıcının mevcut bakiyesini hesaplar."""
        self.cursor.execute(
            "SELECT SUM(CASE WHEN type = 'Gelir' THEN amount ELSE -amount END) FROM transactions WHERE user_id = ?",
            (user_id,))
        balance = self.cursor.fetchone()[0]
        return balance if balance is not None else 0.0

    # --- Kategori Yönetimi ---
    def insert_category(self, name, type, user_id):
        """Yeni bir kategori ekler."""
        try:
            self.cursor.execute("INSERT INTO categories (user_id, name, type) VALUES (?, ?, ?)", (user_id, name, type))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            print(f"Hata: '{name}' kategorisi zaten mevcut.")
            return False
        except sqlite3.Error as e:
            print(f"Kategori ekleme hatası: {e}")
            return False

    def get_categories_for_user(self, user_id):
        """Belirli bir kullanıcıya ait tüm kategorileri getirir."""
        self.cursor.execute("SELECT id, name, type FROM categories WHERE user_id = ? ORDER BY name", (user_id,))
        return self.cursor.fetchall()

    def get_all_categories(self, user_id):
        """Combobox için tüm kategori isimlerini döndürür."""
        self.cursor.execute("SELECT name FROM categories WHERE user_id = ? ORDER BY name", (user_id,))
        return [row[0] for row in self.cursor.fetchall()]

    def delete_category(self, category_id, user_id):
        """Bir kategoriyi siler."""
        try:
            self.cursor.execute("DELETE FROM categories WHERE id = ? AND user_id = ?", (category_id, user_id))
            self.conn.commit()
            return self.cursor.rowcount > 0
        except sqlite3.Error as e:
            print(f"Kategori silme hatası: {e}")
            return False

    def count_transactions_by_category(self, category_name, user_id):
        """Belirli bir kategoriye ait işlem sayısını döner."""
        self.cursor.execute("SELECT COUNT(*) FROM transactions WHERE category = ? AND user_id = ?",
                            (category_name, user_id))
        return self.cursor.fetchone()[0]

    def update_transactions_category_to_null(self, category_name, user_id):
        """Belirli bir kategoriye sahip tüm işlemlerin kategorisini NULL olarak günceller."""
        try:
            self.cursor.execute("UPDATE transactions SET category = NULL WHERE category = ? AND user_id = ?",
                                (category_name, user_id))
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"İşlemlerin kategorisi NULL olarak güncellenirken hata: {e}")
            return False

    # --- Tekrarlayan İşlemler Yönetimi ---
    def insert_recurring_transaction(self, type, amount, category, description, start_date, last_generated_date,
                                     user_id):
        """Yeni bir tekrarlayan işlem ekler."""
        try:
            self.cursor.execute(
                "INSERT INTO recurring_transactions (user_id, description, amount, type, category, start_date, last_generated_date) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (user_id, description, amount, type, category, start_date, last_generated_date))
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Tekrarlayan işlem ekleme hatası: {e}")
            return False

    def get_recurring_transactions(self, user_id):
        """Belirli bir kullanıcıya ait tüm tekrarlayan işlemleri getirir."""
        self.cursor.execute(
            "SELECT id, type, amount, category, description, start_date, frequency, last_generated_date FROM recurring_transactions WHERE user_id = ?",
            (user_id,))
        return self.cursor.fetchall()

    def update_recurring_transaction(self, rec_id, type, amount, category, description, start_date, frequency, user_id):
        """Mevcut bir tekrarlayan işlemi günceller."""
        try:
            self.cursor.execute(
                "UPDATE recurring_transactions SET type = ?, amount = ?, category = ?, description = ?, start_date = ?, frequency = ? WHERE id = ? AND user_id = ?",
                (type, amount, category, description, start_date, frequency, rec_id, user_id))
            self.conn.commit()
            return self.cursor.rowcount > 0
        except sqlite3.Error as e:
            print(f"Tekrarlayan işlem güncelleme hatası: {e}")
            return False

    def update_recurring_transaction_last_generated_date(self, rec_id, new_last_generated_date):
        """Tekrarlayan işlemin son üretildiği tarihi günceller."""
        try:
            self.cursor.execute("UPDATE recurring_transactions SET last_generated_date = ? WHERE id = ?",
                                (new_last_generated_date, rec_id))
            self.conn.commit()
            return self.cursor.rowcount > 0
        except sqlite3.Error as e:
            print(f"Tekrarlayan işlem son üretilme tarihi güncelleme hatası: {e}")
            return False

    def delete_recurring_transaction(self, rec_id, user_id):
        """Bir tekrarlayan işlemi siler."""
        try:
            self.cursor.execute("DELETE FROM recurring_transactions WHERE id = ? AND user_id = ?", (rec_id, user_id))
            self.conn.commit()
            return self.cursor.rowcount > 0
        except sqlite3.Error as e:
            print(f"Tekrarlayan işlem silme hatası: {e}")
            return False

    # --- Tasarruf Hedefleri Yönetimi ---
    def insert_savings_goal(self, goal_name, target_amount, current_amount, target_date, description, user_id):
        """Yeni bir tasarruf hedefi ekler."""
        try:
            self.cursor.execute(
                "INSERT INTO savings_goals (user_id, goal_name, target_amount, current_amount, target_date, description) VALUES (?, ?, ?, ?, ?, ?)",
                (user_id, goal_name, target_amount, current_amount, target_date, description))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            print(f"Hata: '{goal_name}' adında bir hedef zaten mevcut.")
            return False
        except sqlite3.Error as e:
            print(f"Tasarruf hedefi ekleme hatası: {e}")
            return False

    def get_savings_goals(self, user_id):
        """Belirli bir kullanıcıya ait tüm tasarruf hedeflerini getirir."""
        self.cursor.execute(
            "SELECT id, goal_name, target_amount, current_amount, target_date, description, status FROM savings_goals WHERE user_id = ?",
            (user_id,))
        return self.cursor.fetchall()

    def update_savings_goal(self, goal_id, goal_name, target_amount, current_amount, target_date, description, user_id):
        """Mevcut bir tasarruf hedefini günceller."""
        try:
            self.cursor.execute(
                "UPDATE savings_goals SET goal_name = ?, target_amount = ?, current_amount = ?, target_date = ?, description = ? WHERE id = ? AND user_id = ?",
                (goal_name, target_amount, current_amount, target_date, description, goal_id, user_id))
            self.conn.commit()
            return self.cursor.rowcount > 0
        except sqlite3.Error as e:
            print(f"Tasarruf hedefi güncelleme hatası: {e}")
            return False

    def update_savings_goal_status(self, goal_id, new_status, user_id):
        """Tasarruf hedefinin durumunu günceller."""
        try:
            self.cursor.execute("UPDATE savings_goals SET status = ? WHERE id = ? AND user_id = ?",
                                (new_status, goal_id, user_id))
            self.conn.commit()
            return self.cursor.rowcount > 0
        except sqlite3.Error as e:
            print(f"Tasarruf hedefi durumu güncelleme hatası: {e}")
            return False

    def delete_savings_goal(self, goal_id, user_id):
        """Bir tasarruf hedefini siler."""
        try:
            self.cursor.execute("DELETE FROM savings_goals WHERE id = ? AND user_id = ?", (goal_id, user_id))
            self.conn.commit()
            return self.cursor.rowcount > 0
        except sqlite3.Error as e:
            print(f"Tasarruf hedefi silme hatası: {e}")
            return False

    # --- Müşteri Yönetimi ---
    def insert_customer(self, name, address, phone, email, user_id):
        """Yeni bir müşteri ekler."""
        try:
            self.cursor.execute("INSERT INTO customers (user_id, name, address, phone, email) VALUES (?, ?, ?, ?, ?)",
                                (user_id, name, address, phone, email))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            print(f"Hata: '{name}' adında bir müşteri zaten mevcut.")
            return False
        except sqlite3.Error as e:
            print(f"Müşteri ekleme hatası: {e}")
            return False

    def get_customers(self, user_id):
        """Belirli bir kullanıcıya ait tüm müşterileri getirir."""
        self.cursor.execute("SELECT id, name, address, phone, email FROM customers WHERE user_id = ? ORDER BY name",
                            (user_id,))
        return self.cursor.fetchall()

    def get_customer_by_name(self, name, user_id):
        """İsimle müşteri bilgilerini getirir."""
        self.cursor.execute("SELECT id, name, address, phone, email FROM customers WHERE name = ? AND user_id = ?",
                            (name, user_id))
        return self.cursor.fetchone()

    def update_customer(self, customer_id, name, address, phone, email, user_id):
        """Mevcut bir müşteriyi günceller."""
        try:
            self.cursor.execute(
                "UPDATE customers SET name = ?, address = ?, phone = ?, email = ? WHERE id = ? AND user_id = ?",
                (name, address, phone, email, customer_id, user_id))
            self.conn.commit()
            return self.cursor.rowcount > 0
        except sqlite3.Error as e:
            print(f"Müşteri güncelleme hatası: {e}")
            return False

    def delete_customer(self, customer_id, user_id):
        """Bir müşteriyi siler."""
        try:
            self.cursor.execute("DELETE FROM customers WHERE id = ? AND user_id = ?", (customer_id, user_id))
            self.conn.commit()
            return self.cursor.rowcount > 0
        except sqlite3.Error as e:
            print(f"Müşteri silme hatası: {e}")
            return False

    def count_invoices_by_customer(self, customer_name, user_id):
        """Belirli bir müşteriye ait fatura/teklif sayısını döner."""
        self.cursor.execute("SELECT COUNT(*) FROM invoices_offers WHERE customer_name = ? AND user_id = ?",
                            (customer_name, user_id))
        return self.cursor.fetchone()[0]

    def update_invoice_customer_name(self, old_customer_name, new_customer_name, user_id):
        """Müşteri adı değiştiğinde ilgili fatura/teklifleri günceller."""
        try:
            self.cursor.execute("UPDATE invoices_offers SET customer_name = ? WHERE customer_name = ? AND user_id = ?",
                                (new_customer_name, old_customer_name, user_id))
            self.conn.commit()
            return self.cursor.rowcount > 0
        except sqlite3.Error as e:
            print(f"Fatura müşteri adı güncelleme hatası: {e}")
            return False

    # --- Ürün/Hizmet Yönetimi ---
    def insert_product(self, name, stock, purchase_price, selling_price, kdv_rate, user_id):
        """Yeni bir ürün/hizmet ekler."""
        try:
            self.cursor.execute(
                "INSERT INTO products (user_id, name, stock, purchase_price, selling_price, kdv_rate) VALUES (?, ?, ?, ?, ?, ?)",
                (user_id, name, stock, purchase_price, selling_price, kdv_rate))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            print(f"Hata: '{name}' adında bir ürün/hizmet zaten mevcut.")
            return False
        except sqlite3.Error as e:
            print(f"Ürün/hizmet ekleme hatası: {e}")
            return False

    def get_products(self, user_id):
        """Belirli bir kullanıcıya ait tüm ürünleri/hizmetleri getirir."""
        self.cursor.execute(
            "SELECT id, name, stock, purchase_price, selling_price, kdv_rate FROM products WHERE user_id = ? ORDER BY name",
            (user_id,))
        return self.cursor.fetchall()

    def get_product_by_name(self, name, user_id):
        """İsimle ürün/hizmet bilgilerini getirir."""
        self.cursor.execute(
            "SELECT id, name, stock, purchase_price, selling_price, kdv_rate FROM products WHERE name = ? AND user_id = ?",
            (name, user_id))
        return self.cursor.fetchone()

    def update_product(self, product_id, name, stock, purchase_price, selling_price, kdv_rate, user_id):
        """Mevcut bir ürün/hizmeti günceller."""
        try:
            self.cursor.execute(
                "UPDATE products SET name = ?, stock = ?, purchase_price = ?, selling_price = ?, kdv_rate = ? WHERE id = ? AND user_id = ?",
                (name, stock, purchase_price, selling_price, kdv_rate, product_id, user_id))
            self.conn.commit()
            return self.cursor.rowcount > 0
        except sqlite3.Error as e:
            print(f"Ürün/hizmet güncelleme hatası: {e}")
            return False

    def update_product_stock(self, product_id, new_stock):
        """Bir ürünün stok miktarını günceller."""
        try:
            self.cursor.execute("UPDATE products SET stock = ? WHERE id = ?", (new_stock, product_id))
            self.conn.commit()
            return self.cursor.rowcount > 0
        except sqlite3.Error as e:
            print(f"Ürün stok güncelleme hatası: {e}")
            return False

    def delete_product(self, product_id, user_id):
        """Bir ürün/hizmeti siler."""
        try:
            self.cursor.execute("DELETE FROM products WHERE id = ? AND user_id = ?", (product_id, user_id))
            self.conn.commit()
            return self.cursor.rowcount > 0
        except sqlite3.Error as e:
            print(f"Ürün/hizmet silme hatası: {e}")
            return False

    # --- Fatura/Teklif Yönetimi ---
    def insert_invoice_offer(self, type, document_number, customer_name, document_date, due_validity_date,
                             items_json, total_excl_kdv, total_kdv_amount, notes, status, user_id):
        """Yeni bir fatura veya teklif ekler."""
        try:
            total_with_kdv = total_excl_kdv + total_kdv_amount
            self.cursor.execute("""
                INSERT INTO invoices_offers (user_id, type, document_number, customer_name, document_date, 
                                            due_validity_date, items_json, total_amount_excluding_kdv, 
                                            total_kdv_amount, total_amount_with_kdv, notes, status) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                                (user_id, type, document_number, customer_name, document_date, due_validity_date,
                                 items_json, total_excl_kdv, total_kdv_amount, total_with_kdv, notes, status))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            print(f"Hata: '{document_number}' belge numarası zaten mevcut.")
            return False
        except sqlite3.Error as e:
            print(f"Fatura/Teklif ekleme hatası: {e}")
            return False

    def get_invoice_offers(self, user_id):
        """Belirli bir kullanıcıya ait tüm fatura/teklifleri getirir."""
        self.cursor.execute("""
            SELECT id, type, document_number, customer_name, total_amount_excluding_kdv, 
                   total_amount_with_kdv, document_date, status, notes
            FROM invoices_offers 
            WHERE user_id = ? ORDER BY document_date DESC, document_number DESC
        """, (user_id,))
        return self.cursor.fetchall()

    def get_invoice_offer_by_id(self, invoice_offer_id, user_id):
        """Belge ID'sine göre fatura/teklif detaylarını getirir."""
        self.cursor.execute("""
            SELECT id, type, document_number, customer_name, document_date, due_validity_date, 
                   items_json, total_amount_excluding_kdv, total_kdv_amount, total_amount_with_kdv, notes, status
            FROM invoices_offers 
            WHERE id = ? AND user_id = ?
        """, (invoice_offer_id, user_id))
        return self.cursor.fetchone()

    def update_invoice_offer(self, invoice_offer_id, type, document_number, customer_name, document_date,
                             due_validity_date, items_json, total_excl_kdv, total_kdv_amount, notes, status, user_id):
        """Mevcut bir fatura veya teklifi günceller."""
        try:
            total_with_kdv = total_excl_kdv + total_kdv_amount
            self.cursor.execute("""
                UPDATE invoices_offers SET type = ?, document_number = ?, customer_name = ?, document_date = ?, 
                                         due_validity_date = ?, items_json = ?, total_amount_excluding_kdv = ?, 
                                         total_kdv_amount = ?, total_amount_with_kdv = ?, notes = ?, status = ? 
                WHERE id = ? AND user_id = ?""",
                                (type, document_number, customer_name, document_date, due_validity_date,
                                 items_json, total_excl_kdv, total_kdv_amount, total_with_kdv, notes, status,
                                 invoice_offer_id, user_id))
            self.conn.commit()
            return self.cursor.rowcount > 0
        except sqlite3.Error as e:
            print(f"Fatura/Teklif güncelleme hatası: {e}")
            return False

    def delete_invoice_offer(self, invoice_offer_id, user_id):
        """Bir fatura veya teklifi siler."""
        try:
            self.cursor.execute("DELETE FROM invoices_offers WHERE id = ? AND user_id = ?", (invoice_offer_id, user_id))
            self.conn.commit()
            return self.cursor.rowcount > 0
        except sqlite3.Error as e:
            print(f"Fatura/Teklif silme hatası: {e}")
            return False

    def get_total_sales_kdv(self, start_date, end_date, user_id):
        """Belirli bir tarih aralığındaki toplam satış KDV'sini hesaplar."""
        query = """
            SELECT SUM(total_kdv_amount) FROM invoices_offers 
            WHERE user_id = ? AND type = 'Fatura' AND document_date BETWEEN ? AND ?
        """
        self.cursor.execute(query, (user_id, start_date, end_date))
        result = self.cursor.fetchone()[0]
        return result if result is not None else 0.0

    def get_invoice_jsons_for_tax_report(self, start_date, end_date, user_id):
        """Vergi raporu için faturalardaki kalem JSON'larını getirir."""
        query = """
            SELECT items_json FROM invoices_offers
            WHERE user_id = ? AND type = 'Fatura' AND document_date BETWEEN ? AND ?
        """
        self.cursor.execute(query, (user_id, start_date, end_date))
        return self.cursor.fetchall()

    # --- Raporlama ve AI için Yeni Metotlar ---
    def get_all_transactions_for_ai_training(self, user_id):
        """AI modeli eğitimi için tüm gelir ve gider işlemlerini kategori ve açıklama ile birlikte getirir."""
        # Kategori NULL olmayan ve geçerli açıklama olanları al
        self.cursor.execute("""
            SELECT description, category, type FROM transactions 
            WHERE user_id = ? AND category IS NOT NULL AND description IS NOT NULL AND description != ''
        """, (user_id,))
        return self.cursor.fetchall()

    def get_monthly_balance_trend(self, user_id, num_months=12):
        """Son N aydaki aylık kümülatif bakiye trendini getirir."""
        today = datetime.now().date()
        start_date_limit = (today - timedelta(days=num_months * 30)).strftime('%Y-%m-%d')  # Yaklaşık N ay öncesi

        self.cursor.execute(
            "SELECT date, type, amount FROM transactions WHERE user_id = ? AND date >= ? ORDER BY date ASC",
            (user_id, start_date_limit))
        transactions = self.cursor.fetchall()
        return transactions  # Dataframe'e çevrilmesi ve hesaplama fingo_app.py'de yapılmalı

    def get_income_expenses_by_month_and_category(self, user_id, num_months=12):
        """
        Son N aydaki gelir ve giderleri kategori bazında getirir.
        AI analizinde ve grafiklerde kullanılabilir.
        """
        today = datetime.now().date()
        start_date_limit = (today - timedelta(days=num_months * 30)).strftime('%Y-%m-%d')

        self.cursor.execute("""
            SELECT type, category, SUM(amount) as total_amount
            FROM transactions
            WHERE user_id = ? AND date >= ?
            GROUP BY type, category
            ORDER BY type, total_amount DESC
        """, (user_id, start_date_limit))
        return self.cursor.fetchall()

    def get_all_transaction_data_for_analysis(self, user_id):
        """
        AI tahmincisi için tüm işlem verilerini çeker.
        (id, type, amount, category, description, date)
        """
        self.cursor.execute("SELECT id, type, amount, category, description, date FROM transactions WHERE user_id = ?",
                            (user_id,))
        return self.cursor.fetchall()

