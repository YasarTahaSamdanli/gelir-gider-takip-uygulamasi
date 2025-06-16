# database_manager.py

import sqlite3
import hashlib  # Şifreleri güvenli saklamak için
import json  # Fatura/tekliflerdeki ürün/hizmetleri JSON olarak saklamak için


class DatabaseManager:
    def __init__(self, db_name="veriler.db"):
        self.db_name = db_name
        self.conn = None
        self.cursor = None
        self._connect()
        self._create_tables()

    def _connect(self):
        """Veritabanına bağlanır."""
        try:
            self.conn = sqlite3.connect(self.db_name)
            self.cursor = self.conn.cursor()
            print(f"Veritabanı bağlantısı '{self.db_name}' başarıyla kuruldu.")
        except sqlite3.Error as e:
            print(f"Veritabanı bağlantı hatası: {e}")
            raise ConnectionError(f"Veritabanı bağlantı hatası: {e}")  # Hata daha üst seviyeye fırlatıldı

    def _create_tables(self):
        """Uygulama için gerekli tabloları oluşturur (eğer yoksa)."""
        # Kullanıcılar tablosu (AUTOINCREMENT hatası düzeltildi: INTEGER INTEGER -> INTEGER)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                invoice_num INTEGER DEFAULT 0,
                offer_num INTEGER DEFAULT 0
            )
        """)
        # İşlemler (gelir/gider) tablosu
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL,
                amount REAL NOT NULL,
                category TEXT,
                description TEXT,
                date TEXT NOT NULL,
                user_id INTEGER NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)
        # Tekrarlayan işlemler tablosu
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS recurring_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL,
                amount REAL NOT NULL,
                category TEXT,
                description TEXT,
                start_date TEXT NOT NULL,
                frequency TEXT NOT NULL,
                last_generated_date TEXT NOT NULL,
                user_id INTEGER NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)
        # Kategoriler tablosu
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                type TEXT NOT NULL, -- 'Gelir', 'Gider', 'Genel'
                user_id INTEGER NOT NULL,
                UNIQUE(name, user_id), -- Her kullanıcı için kategori adı benzersiz olmalı
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)
        # Müşteriler tablosu
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                address TEXT,
                phone TEXT,
                email TEXT,
                user_id INTEGER NOT NULL,
                UNIQUE(name, user_id),
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)
        # Ürünler/Hizmetler tablosu (Envanter)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                stock_quantity REAL NOT NULL,
                purchase_price REAL,
                selling_price REAL NOT NULL,
                kdv_rate REAL DEFAULT 18.0, -- KDV oranı, örn: 0, 1, 8, 18, 20
                user_id INTEGER NOT NULL,
                UNIQUE(name, user_id),
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)
        # Fatura/Teklifler tablosu
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS invoices_offers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL, -- 'Fatura' veya 'Teklif'
                document_number TEXT UNIQUE NOT NULL, -- Belge numarası (FTR-2023-00001, TKLF-2023-00001)
                customer_name TEXT NOT NULL,
                document_date TEXT NOT NULL,
                due_validity_date TEXT NOT NULL,
                items_json TEXT, -- Ürün/hizmet detayları JSON formatında [{"ad": "Ürün1", "miktar": 2, "birim_fiyat": 50, "kdv_orani": 18, "kdv_miktari": 18, "ara_toplam": 100}]
                total_amount_excluding_kdv REAL NOT NULL, -- KDV hariç toplam tutar
                total_kdv_amount REAL NOT NULL, -- Toplam KDV tutarı
                notes TEXT,
                status TEXT NOT NULL, -- 'Taslak', 'Gönderildi', 'Ödendi', 'İptal Edildi'
                user_id INTEGER NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users (id),
                UNIQUE(document_number, user_id) -- Her kullanıcı için belge numarası benzersiz olmalı
            )
        """)

        # YENİ EKLENEN: Tasarruf Hedefleri tablosu
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS savings_goals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                target_amount REAL NOT NULL,
                current_amount REAL DEFAULT 0.0,
                target_date TEXT, -- Hedeflenen tamamlama tarihi (YYYY-MM-DD)
                description TEXT,
                user_id INTEGER NOT NULL,
                status TEXT DEFAULT 'Devam Ediyor', -- 'Devam Ediyor', 'Tamamlandı', 'İptal Edildi'
                UNIQUE(name, user_id),
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)

        self.conn.commit()
        print("Veritabanı tabloları başarıyla oluşturuldu/kontrol edildi.")

    def close(self):
        """Veritabanı bağlantısını kapatır."""
        if self.conn:
            self.conn.close()
            print("Veritabanı bağlantısı kapatıldı.")

    def register_user(self, username, password):
        """Yeni bir kullanıcı kaydeder."""
        try:
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            self.cursor.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)",
                                (username, password_hash))
            self.conn.commit()
            print(f"Kullanıcı '{username}' başarıyla kaydedildi.")
            return True
        except sqlite3.IntegrityError:
            print(f"Hata: Kullanıcı adı '{username}' zaten mevcut.")
            return False
        except sqlite3.Error as e:
            print(f"Kullanıcı kaydı hatası: {e}")
            return False

    def verify_user(self, username, password):
        """Kullanıcı adı ve şifreyi doğrular."""
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        self.cursor.execute("SELECT id FROM users WHERE username = ? AND password_hash = ?",
                            (username, password_hash))
        result = self.cursor.fetchone()
        if result:
            print(f"Kullanıcı '{username}' doğrulandı. ID: {result[0]}")
            return result[0]  # Kullanıcı ID'sini döndür
        else:
            print("Kullanıcı adı veya şifre hatalı.")
            return None

    def get_username_by_id(self, user_id):
        """Kullanıcı ID'sine göre kullanıcı adını döndürür."""
        self.cursor.execute("SELECT username FROM users WHERE id = ?", (user_id,))
        result = self.cursor.fetchone()
        return result[0] if result else None

    def get_user_by_username(self, username):
        """Kullanıcı adına göre kullanıcı ID'si ve şifre hash'ini döndürür."""
        self.cursor.execute("SELECT id, password_hash FROM users WHERE username = ?", (username,))
        return self.cursor.fetchone()

    def get_user_invoice_offer_nums(self, user_id):
        """Kullanıcının fatura ve teklif numaralarını döndürür."""
        self.cursor.execute("SELECT invoice_num, offer_num FROM users WHERE id = ?", (user_id,))
        result = self.cursor.fetchone()
        return result if result else (0, 0)  # Yoksa 0,0 döndür

    def update_user_invoice_offer_num(self, user_id, invoice_num=None, offer_num=None):
        """Kullanıcının fatura veya teklif numarasını günceller."""
        try:
            if invoice_num is not None:
                self.cursor.execute("UPDATE users SET invoice_num = ? WHERE id = ?, (invoice_num, user_id)")
            if offer_num is not None:
                self.cursor.execute("UPDATE users SET offer_num = ? WHERE id = ?, (offer_num, user_id)")
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Kullanıcı fatura/teklif numarası güncelleme hatası: {e}")
            return False

    # --- İşlem (Gelir/Gider) Metotları ---
    def insert_transaction(self, type, amount, category, description, date, user_id):
        """Yeni bir gelir/gider işlemi ekler."""
        self.cursor.execute(
            "INSERT INTO transactions (type, amount, category, description, date, user_id) VALUES (?, ?, ?, ?, ?, ?)",
            (type, amount, category, description, date, user_id))
        self.conn.commit()

    def update_transaction(self, id, type, amount, category, description, date, user_id):
        """Mevcut bir gelir/gider işlemini günceller."""
        self.cursor.execute(
            "UPDATE transactions SET type = ?, amount = ?, category = ?, description = ?, date = ? WHERE id = ? AND user_id = ?",
            (type, amount, category, description, date, id, user_id))
        self.conn.commit()

    def delete_transaction(self, id, user_id):
        """Bir gelir/gider işlemini siler."""
        self.cursor.execute("DELETE FROM transactions WHERE id = ? AND user_id = ?", (id, user_id))
        self.conn.commit()

    def get_transactions(self, user_id, type_filter="Tümü", category_filter="Tümü", start_date="", end_date="",
                         search_term=""):
        """Belirli filtrelerle işlemleri getirir."""
        query = "SELECT id, type, amount, category, description, date FROM transactions WHERE user_id = ?"
        params = [user_id]

        if type_filter != "Tümü":
            query += " AND type = ?"
            params.append(type_filter)
        if category_filter != "Tümü":
            query += " AND category = ?"
            params.append(category_filter)
        if start_date:
            query += " AND date >= ?"
            params.append(start_date)
        if end_date:
            query += " AND date <= ?"
            params.append(end_date)
        if search_term:
            search_pattern = f"%{search_term}%"
            query += " AND (description LIKE ? OR category LIKE ?)"
            params.extend([search_pattern, search_pattern])

        query += " ORDER BY date DESC"  # Tarihe göre tersten sırala

        self.cursor.execute(query, params)
        return self.cursor.fetchall()

    def get_all_transaction_descriptions_and_categories(self, user_id):
        """
        AI modeli eğitimi için tüm işlem açıklamalarını ve kategorilerini getirir.
        Boş (NULL) değerler de döndürülebilir, çağıran metodun bunları filtrelemesi gerekir.
        """
        self.cursor.execute("SELECT description, category FROM transactions WHERE user_id = ?", (user_id,))
        return self.cursor.fetchall()

    def get_transaction_for_charts(self, user_id):
        """Grafikler için gerekli gelir/gider verilerini kategori ve zaman bazında getirir."""
        # Kategori bazında gelir/gider toplamları
        self.cursor.execute("""
            SELECT type, category, SUM(amount) 
            FROM transactions 
            WHERE user_id = ?
            GROUP BY type, category
        """, (user_id,))
        kategori_verileri = self.cursor.fetchall()

        # Zaman bazında gelir/gider verileri (kümülatif bakiye için)
        self.cursor.execute("""
            SELECT date, type, amount 
            FROM transactions 
            WHERE user_id = ?
            ORDER BY date ASC
        """, (user_id,))
        zaman_verileri = self.cursor.fetchall()

        return kategori_verileri, zaman_verileri

    # --- Tekrarlayan İşlem Metotları ---
    def insert_recurring_transaction(self, type, amount, category, description, start_date, frequency,
                                     last_generated_date, user_id):
        """Yeni bir tekrarlayan işlem ekler."""
        self.cursor.execute(
            "INSERT INTO recurring_transactions (type, amount, category, description, start_date, frequency, last_generated_date, user_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (type, amount, category, description, start_date, frequency, last_generated_date, user_id))
        self.conn.commit()

    def update_recurring_transaction_last_generated_date(self, id, last_generated_date):
        """Tekrarlayan işlemin son üretildiği tarihi günceller."""
        self.cursor.execute("UPDATE recurring_transactions SET last_generated_date = ? WHERE id = ?",
                            (last_generated_date, id))
        self.conn.commit()

    def delete_recurring_transaction(self, id, user_id):
        """Bir tekrarlayan işlemi siler."""
        self.cursor.execute("DELETE FROM recurring_transactions WHERE id = ? AND user_id = ?", (id, user_id))
        self.conn.commit()

    def get_recurring_transactions(self, user_id):
        """Tüm tekrarlayan işlemleri getirir."""
        self.cursor.execute(
            "SELECT id, type, amount, category, description, start_date, frequency, last_generated_date FROM recurring_transactions WHERE user_id = ?",
            (user_id,))
        return self.cursor.fetchall()

    # --- Kategori Metotları ---
    def insert_category(self, name, type, user_id):
        """Yeni bir kategori ekler."""
        self.cursor.execute("INSERT INTO categories (name, type, user_id) VALUES (?, ?, ?)",
                            (name, type, user_id))
        self.conn.commit()

    def delete_category(self, id, user_id):
        """Bir kategoriyi siler."""
        self.cursor.execute("DELETE FROM categories WHERE id = ? AND user_id = ?", (id, user_id))
        self.conn.commit()

    def get_categories_for_user(self, user_id):
        """Belirli bir kullanıcıya ait tüm kategorileri getirir."""
        self.cursor.execute("SELECT id, name, type FROM categories WHERE user_id = ?", (user_id,))
        return self.cursor.fetchall()

    def get_category_by_name(self, name, user_id):
        """Kategori adına göre kategoriyi getirir."""
        self.cursor.execute("SELECT id, name, type FROM categories WHERE name = ? AND user_id = ?", (name, user_id))
        return self.cursor.fetchone()

    def count_transactions_by_category(self, category_name, user_id):
        """Belirli bir kategorinin kaç işlemde kullanıldığını sayar."""
        self.cursor.execute("SELECT COUNT(*) FROM transactions WHERE category = ? AND user_id = ?",
                            (category_name, user_id))
        result = self.cursor.fetchone()
        return result[0] if result else 0

    def update_transactions_category_to_null(self, old_category_name, user_id):
        """Belirli bir kategorinin kullanıldığı işlemlerde kategori bilgisini NULL yapar."""
        self.cursor.execute("UPDATE transactions SET category = NULL WHERE category = ? AND user_id = ?",
                            (old_category_name, user_id))
        self.conn.commit()

    # --- Müşteri Metotları ---
    def insert_customer(self, name, address, phone, email, user_id):
        """Yeni bir müşteri ekler."""
        self.cursor.execute("INSERT INTO customers (name, address, phone, email, user_id) VALUES (?, ?, ?, ?, ?)",
                            (name, address, phone, email, user_id))
        self.conn.commit()

    def update_customer(self, id, name, address, phone, email, user_id):
        """Mevcut bir müşteriyi günceller."""
        self.cursor.execute(
            "UPDATE customers SET name = ?, address = ?, phone = ?, email = ? WHERE id = ? AND user_id = ?",
            (name, address, phone, email, id, user_id))
        self.conn.commit()

    def delete_customer(self, id, user_id):
        """Bir müşteriyi siler."""
        self.cursor.execute("DELETE FROM customers WHERE id = ? AND user_id = ?", (id, user_id))
        self.conn.commit()

    def get_customers(self, user_id):
        """Tüm müşterileri getirir."""
        self.cursor.execute("SELECT id, name, address, phone, email FROM customers WHERE user_id = ?", (user_id,))
        return self.cursor.fetchall()

    def get_customer_by_name(self, name, user_id):
        """Müşteri adına göre müşteriyi getirir."""
        self.cursor.execute("SELECT id, name, address, phone, email FROM customers WHERE name = ? AND user_id = ?",
                            (name, user_id))
        return self.cursor.fetchone()

    def get_customer_by_id(self, customer_id):
        """Müşteri ID'sine göre müşteriyi getirir."""
        self.cursor.execute("SELECT name, address, phone, email FROM customers WHERE id = ?", (customer_id,))
        return self.cursor.fetchone()  # Sadece müşteri bilgilerini döndür (ID hariç)

    def count_invoices_by_customer(self, customer_name, user_id):
        """Belirli bir müşterinin kaç fatura/teklifte kullanıldığını sayar."""
        self.cursor.execute("SELECT COUNT(*) FROM invoices_offers WHERE customer_name = ? AND user_id = ?",
                            (customer_name, user_id))
        result = self.cursor.fetchone()
        return result[0] if result else 0

    def update_invoice_customer_name(self, old_customer_name, new_customer_name, user_id):
        """Faturalardaki müşteri adını günceller."""
        self.cursor.execute("UPDATE invoices_offers SET customer_name = ? WHERE customer_name = ? AND user_id = ?",
                            (new_customer_name, old_customer_name, user_id))
        self.conn.commit()

    # --- Ürün Metotları ---
    def insert_product(self, name, stock_quantity, purchase_price, selling_price, kdv_rate, user_id):
        """Yeni bir ürün ekler."""
        self.cursor.execute(
            "INSERT INTO products (name, stock_quantity, purchase_price, selling_price, kdv_rate, user_id) VALUES (?, ?, ?, ?, ?, ?)",
            (name, stock_quantity, purchase_price, selling_price, kdv_rate, user_id))
        self.conn.commit()

    def update_product(self, id, name, stock_quantity, purchase_price, selling_price, kdv_rate, user_id):
        """Mevcut bir ürünü günceller."""
        self.cursor.execute(
            "UPDATE products SET name = ?, stock_quantity = ?, purchase_price = ?, selling_price = ?, kdv_rate = ? WHERE id = ? AND user_id = ?",
            (name, stock_quantity, purchase_price, selling_price, kdv_rate, id, user_id))
        self.conn.commit()

    def update_product_stock(self, product_id, new_stock_quantity):
        """Bir ürünün stok miktarını günceller."""
        self.cursor.execute("UPDATE products SET stock_quantity = ? WHERE id = ?", (new_stock_quantity, product_id))
        self.conn.commit()

    def delete_product(self, id, user_id):
        """Bir ürünü siler."""
        self.cursor.execute("DELETE FROM products WHERE id = ? AND user_id = ?", (id, user_id))
        self.conn.commit()

    def get_products(self, user_id):
        """Tüm ürünleri getirir."""
        self.cursor.execute(
            "SELECT id, name, stock_quantity, purchase_price, selling_price, kdv_rate FROM products WHERE user_id = ?",
            (user_id,))
        return self.cursor.fetchall()

    def get_product_by_name(self, name, user_id):
        """Ürün adına göre ürünü getirir."""
        self.cursor.execute(
            "SELECT id, name, stock_quantity, purchase_price, selling_price, kdv_rate FROM products WHERE name = ? AND user_id = ?",
            (name, user_id))
        return self.cursor.fetchone()

    # --- Fatura/Teklif Metotları ---
    def insert_invoice_offer(self, type, document_number, customer_name, document_date, due_validity_date, items_json,
                             total_amount_excluding_kdv, total_kdv_amount, notes, status, user_id):
        """Yeni bir fatura veya teklif kaydeder."""
        self.cursor.execute("""
            INSERT INTO invoices_offers 
            (type, document_number, customer_name, document_date, due_validity_date, items_json, total_amount_excluding_kdv, total_kdv_amount, notes, status, user_id) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (type, document_number, customer_name, document_date, due_validity_date, items_json,
              total_amount_excluding_kdv, total_kdv_amount, notes, status, user_id))
        self.conn.commit()

    def update_invoice_offer(self, id, type, document_number, customer_name, document_date, due_validity_date,
                             items_json, total_amount_excluding_kdv, total_kdv_amount, notes, status, user_id):
        """Mevcut bir fatura veya teklifi günceller."""
        self.cursor.execute("""
            UPDATE invoices_offers 
            SET type = ?, document_number = ?, customer_name = ?, document_date = ?, due_validity_date = ?, items_json = ?, total_amount_excluding_kdv = ?, total_kdv_amount = ?, notes = ?, status = ? 
            WHERE id = ? AND user_id = ?
        """, (type, document_number, customer_name, document_date, due_validity_date, items_json,
              total_amount_excluding_kdv, total_kdv_amount, notes, status, id, user_id))
        self.conn.commit()

    def delete_invoice_offer(self, id, user_id):
        """Bir fatura veya teklifi siler."""
        self.cursor.execute("DELETE FROM invoices_offers WHERE id = ? AND user_id = ?", (id, user_id))
        self.conn.commit()

    def get_invoice_offers(self, user_id):
        """Tüm fatura ve teklifleri getirir."""
        self.cursor.execute(
            "SELECT id, type, document_number, customer_name, total_amount_excluding_kdv, total_kdv_amount, (total_amount_excluding_kdv + total_kdv_amount) AS general_total, document_date, status FROM invoices_offers WHERE user_id = ? ORDER BY document_date DESC",
            (user_id,))
        return self.cursor.fetchall()

    def get_invoice_offer_by_id(self, invoice_id, user_id):
        """ID'ye göre fatura veya teklifi getirir."""
        self.cursor.execute(
            "SELECT id, type, document_number, customer_name, document_date, due_validity_date, items_json, total_amount_excluding_kdv, total_kdv_amount, notes, status, user_id FROM invoices_offers WHERE id = ? AND user_id = ?",
            (invoice_id, user_id))
        return self.cursor.fetchone()

    def check_belge_numarasi_exists(self, document_number, user_id):
        """Belge numarasının o kullanıcı için zaten var olup olmadığını kontrol eder."""
        self.cursor.execute("SELECT COUNT(*) FROM invoices_offers WHERE document_number = ? AND user_id = ?",
                            (document_number, user_id))
        result = self.cursor.fetchone()
        return result[0] > 0

    def get_total_sales_kdv(self, start_date, end_date, user_id):
        """Belirli bir tarih aralığındaki satış faturalarının toplam KDV'sini getirir."""
        self.cursor.execute("""
            SELECT SUM(total_kdv_amount) 
            FROM invoices_offers 
            WHERE type = 'Fatura' AND status = 'Ödendi' AND user_id = ? AND document_date BETWEEN ? AND ?
        """, (user_id, start_date, end_date))
        result = self.cursor.fetchone()
        return result[0] if result[0] else 0.0

    def get_invoice_jsons_for_tax_report(self, start_date, end_date, user_id):
        """Belirli bir tarih aralığındaki satış faturalarının (ödendi olarak) items_json verilerini getirir."""
        self.cursor.execute("""
            SELECT items_json 
            FROM invoices_offers 
            WHERE type = 'Fatura' AND status = 'Ödendi' AND user_id = ? AND document_date BETWEEN ? AND ?
        """, (user_id, start_date, end_date))
        return self.cursor.fetchall()

    # YENİ EKLENEN: Tasarruf Hedefi Metotları
    def insert_savings_goal(self, name, target_amount, current_amount, target_date, description, user_id):
        """Yeni bir tasarruf hedefi ekler."""
        try:
            self.cursor.execute("""
                INSERT INTO savings_goals (name, target_amount, current_amount, target_date, description, user_id) 
                VALUES (?, ?, ?, ?, ?, ?)
            """, (name, target_amount, current_amount, target_date, description, user_id))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            print(f"Hata: Tasarruf hedefi adı '{name}' zaten mevcut.")
            return False
        except sqlite3.Error as e:
            print(f"Tasarruf hedefi ekleme hatası: {e}")
            return False

    def get_savings_goals(self, user_id):
        """Belirli bir kullanıcıya ait tüm tasarruf hedeflerini getirir."""
        self.cursor.execute("""
            SELECT id, name, target_amount, current_amount, target_date, description, status 
            FROM savings_goals 
            WHERE user_id = ?
            ORDER BY status ASC, target_date ASC
        """, (user_id,))
        return self.cursor.fetchall()

    def update_savings_goal_current_amount(self, goal_id, new_current_amount, user_id):
        """Bir tasarruf hedefinin mevcut birikmiş miktarını günceller."""
        try:
            self.cursor.execute("""
                UPDATE savings_goals 
                SET current_amount = ? 
                WHERE id = ? AND user_id = ?
            """, (new_current_amount, goal_id, user_id))
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Tasarruf hedefi miktar güncelleme hatası: {e}")
            return False

    def update_savings_goal_status(self, goal_id, new_status, user_id):
        """Bir tasarruf hedefinin durumunu günceller."""
        try:
            self.cursor.execute("""
                UPDATE savings_goals 
                SET status = ? 
                WHERE id = ? AND user_id = ?
            """, (new_status, goal_id, user_id))
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Tasarruf hedefi durum güncelleme hatası: {e}")
            return False

    def delete_savings_goal(self, goal_id, user_id):
        """Bir tasarruf hedefini siler."""
        try:
            self.cursor.execute("DELETE FROM savings_goals WHERE id = ? AND user_id = ?", (goal_id, user_id))
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            print(f"Tasarruf hedefi silme hatası: {e}")
            return False

    def get_savings_goal_by_id(self, goal_id, user_id):
        """ID'ye göre tek bir tasarruf hedefi getirir."""
        self.cursor.execute("""
            SELECT id, name, target_amount, current_amount, target_date, description, status 
            FROM savings_goals 
            WHERE id = ? AND user_id = ?
        """, (goal_id, user_id))
        return self.cursor.fetchone()

