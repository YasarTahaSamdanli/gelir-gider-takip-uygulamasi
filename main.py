import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sqlite3
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from tkcalendar import DateEntry
import bcrypt
import re
import time
import json  # JSON verilerini saklamak için

import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.lib import colors

# YENİ EKLENENLER: ReportLab için Türkçe font desteği
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os
import sys  # PyInstaller için

# Matplotlib için Türkçe font ayarı (isteğe bağlı, sistemde yüklü bir font olmalı)
plt.rcParams['font.sans-serif'] = ['Arial', 'DejaVu Sans']  # Matplotlib için ayrı
plt.rcParams['axes.unicode_minus'] = False

# Font dosyasının adını global olarak tanımla
# PyInstaller için doğru yolu bulma mantığı burada da uygulanır
GLOBAL_FONT_FILE_NAME = "Arial.ttf"  # Font dosyanızın adı
if hasattr(sys, '_MEIPASS'):
    GLOBAL_FONT_PATH = os.path.join(sys._MEIPASS, GLOBAL_FONT_FILE_NAME)
else:
    GLOBAL_FONT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), GLOBAL_FONT_FILE_NAME)

# ReportLab'a fontu uygulama başlamadan önce kaydet
try:
    pdfmetrics.registerFont(TTFont("Arial", GLOBAL_FONT_PATH))
    pdfmetrics.registerFont(TTFont("Arial-Bold", GLOBAL_FONT_PATH))  # Bold için de aynı fontu kullan
    pdfmetrics.registerFontFamily("Arial",
                                  normal="Arial",
                                  bold="Arial-Bold",  # Bold stilini ayarla
                                  italic="Arial",
                                  boldItalic="Arial-Bold")
    print(f"Font 'Arial' başarıyla yüklendi: {GLOBAL_FONT_PATH}")
    GLOBAL_REPORTLAB_FONT_NAME = "Arial"
except Exception as e:
    print(
        f"Hata: Font yüklenemedi. PDF'de Türkçe karakter sorunları olabilir: {e}. Lütfen '{GLOBAL_FONT_FILE_NAME}' dosyasının uygulamanızın bulunduğu dizinde olduğundan emin olun.")
    GLOBAL_REPORTLAB_FONT_NAME = "Helvetica"  # Varsayılan fonta geri dön (Türkçe karakterler için sorun devam edebilir)


# --- Şifre Hashleme Fonksiyonları ---
def hash_password_bcrypt(password):
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    return hashed.decode('utf-8')


def check_password_bcrypt(hashed_password_from_db, user_password_input):
    try:
        return bcrypt.checkpw(user_password_input.encode('utf-8'), hashed_password_from_db.encode('utf-8'))
    except ValueError:
        return False


# --- Kullanıcı Yönetimi Ekranları ---

class LoginRegisterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Giriş / Kayıt")
        self.root.geometry("400x300")
        self.root.resizable(False, False)
        self.root.configure(bg="#f5f5f5")

        self.conn = None
        self.cursor = None
        self.baglanti_olustur()

        self.current_frame = None
        self.show_login_screen()

    def baglanti_olustur(self):
        """SQLite veritabanı bağlantısını kurar ve tabloları oluşturur/günceller."""
        try:
            self.conn = sqlite3.connect("veriler.db")
            self.cursor = self.conn.cursor()

            # 1. users tablosunu oluştur
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    kullanici_adi TEXT NOT NULL UNIQUE,
                    sifre_hash TEXT NOT NULL,
                    login_attempts INTEGER DEFAULT 0,
                    lockout_until TEXT
                )
            """)

            # YENİ: categories tablosu
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS categories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    kategori_adi TEXT NOT NULL UNIQUE,
                    tur TEXT NOT NULL, 
                    kullanici_id INTEGER NOT NULL
                )
            """)

            # 2. islemler tablosunu oluştur (kullanici_id sütunuyla birlikte)
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

            # 3. tekrar_eden_islemler tablosunu oluştur (kullanici_id sütunuyla birlikte)
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

            # YENİ: fatura_teklifler tablosu
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS fatura_teklifler (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tur TEXT NOT NULL, -- 'Fatura' veya 'Teklif'
                    musteri_adi TEXT NOT NULL,
                    belge_tarihi TEXT NOT NULL,
                    son_odeme_gecerlilik_tarihi TEXT, -- Fatura için son ödeme, Teklif için geçerlilik
                    urun_hizmetler_json TEXT NOT NULL, -- JSON olarak ürün/hizmet listesi
                    toplam_tutar REAL NOT NULL,
                    notlar TEXT,
                    durum TEXT NOT NULL, -- Fatura için: 'Taslak', 'Gönderildi', 'Ödendi', 'İptal Edildi'
                    kullanici_id INTEGER NOT NULL
                )
            """)

            # 4. Mevcut tablolara yeni sütun ekleme (sadece tablo zaten VARSA ve sütun YOKSA)
            self.cursor.execute("PRAGMA table_info(islemler);")
            cols = [col[1] for col in self.cursor.fetchall()]
            if 'kullanici_id' not in cols:
                try:
                    self.cursor.execute("ALTER TABLE islemler ADD COLUMN kullanici_id INTEGER DEFAULT 0 NOT NULL")
                    print("islemler tablosuna kullanici_id sütunu eklendi (eski veritabanı için).")
                except sqlite3.Error as e:
                    if "duplicate column name: kullanici_id" not in str(e):
                        raise e

            self.cursor.execute("PRAGMA table_info(tekrar_eden_islemler);")
            cols = [col[1] for col in self.cursor.fetchall()]
            if 'kullanici_id' not in cols:
                try:
                    self.cursor.execute(
                        "ALTER TABLE tekrar_eden_islemler ADD COLUMN kullanici_id INTEGER DEFAULT 0 NOT NULL")
                    print("tekrar_eden_islemler tablosuna kullanici_id sütunu eklendi (eski veritabanı için).")
                except sqlite3.Error as e:
                    if "duplicate column name: kullanici_id" not in str(e):
                        raise e

            self.conn.commit()
        except sqlite3.Error as e:
            messagebox.showerror("Veritabanı Hatası",
                                 f"Veritabanı bağlantısı kurulamadı veya tablo oluşturulamadı: {e}\nLütfen uygulamanın bulunduğu klasördeki 'veriler.db' dosyasını silip tekrar deneyin.")
            self.root.destroy()

    def show_login_screen(self):
        if self.current_frame:
            self.current_frame.destroy()
        self.current_frame = LoginScreen(self.root, self)
        self.current_frame.pack(fill="both", expand=True, padx=20, pady=20)

    def show_register_screen(self):
        if self.current_frame:
            self.current_frame.destroy()
        self.current_frame = RegisterScreen(self.root, self)
        self.current_frame.pack(fill="both", expand=True, padx=20, pady=20)

    def start_main_app(self, user_id, username):
        if self.current_frame:
            self.current_frame.destroy()
        self.root.title("Gelişmiş Gelir Gider Takibi")
        self.root.geometry("1200x800")
        self.root.resizable(True, True)
        GelirGiderUygulamasi(self.root, self.conn, self.cursor, user_id, username)


class LoginScreen(ttk.Frame):
    MAX_LOGIN_ATTEMPTS = 3
    LOCKOUT_DURATION_MINUTES = 5

    def __init__(self, master, app_instance):
        super().__init__(master)
        self.app_instance = app_instance
        self.master = master

        stil = ttk.Style()
        stil.configure("Login.TLabel", font=("Arial", 12))
        stil.configure("Login.TEntry", font=("Arial", 12))
        stil.configure("Login.TButton", font=("Arial", 12, "bold"), padding=10)

        ttk.Label(self, text="Giriş Yap", font=("Arial", 16, "bold")).pack(pady=10)

        form_frame = ttk.Frame(self)
        form_frame.pack(pady=10)

        ttk.Label(form_frame, text="Kullanıcı Adı:", style="Login.TLabel").grid(row=0, column=0, padx=5, pady=5,
                                                                                sticky="w")
        self.username_entry = ttk.Entry(form_frame, style="Login.TEntry", width=30)
        self.username_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(form_frame, text="Şifre:", style="Login.TLabel").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.password_entry = ttk.Entry(form_frame, style="Login.TEntry", show="*", width=30)
        self.password_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        ttk.Button(self, text="Giriş", style="Login.TButton", command=self.login).pack(pady=10)
        ttk.Button(self, text="Kayıt Ol", style="Login.TButton", command=self.app_instance.show_register_screen).pack(
            pady=5)

    def login(self):
        username = self.username_entry.get()
        password = self.password_entry.get()

        if not username or not password:
            messagebox.showerror("Hata", "Kullanıcı adı ve şifre boş bırakılamaz.")
            return

        self.app_instance.cursor.execute(
            "SELECT id, sifre_hash, login_attempts, lockout_until FROM users WHERE kullanici_adi = ?", (username,))
        user_data = self.app_instance.cursor.fetchone()

        if user_data:
            user_id, stored_password_hash, login_attempts, lockout_until_str = user_data

            if lockout_until_str:
                lockout_until = datetime.strptime(lockout_until_str, "%Y-%m-%d %H:%M:%S")
                if datetime.now() < lockout_until:
                    remaining_time_seconds = (lockout_until - datetime.now()).total_seconds()
                    minutes = int(remaining_time_seconds // 60)
                    seconds = int(remaining_time_seconds % 60)
                    messagebox.showwarning("Hesap Kilitli",
                                           f"Bu hesap, çok sayıda başarısız giriş denemesi nedeniyle {minutes} dakika {seconds} saniye kilitlenmiştir.")
                    time.sleep(1)
                    return

            if check_password_bcrypt(stored_password_hash, password):
                messagebox.showinfo("Başarılı", f"Hoş geldiniz, {username}!")
                self.app_instance.cursor.execute(
                    "UPDATE users SET login_attempts = 0, lockout_until = NULL WHERE id = ?", (user_id,))
                self.app_instance.conn.commit()
                self.app_instance.start_main_app(user_id, username)
            else:
                login_attempts += 1
                self.app_instance.cursor.execute("UPDATE users SET login_attempts = ? WHERE id = ?",
                                                 (login_attempts, user_id))
                self.app_instance.conn.commit()

                if login_attempts >= self.MAX_LOGIN_ATTEMPTS:
                    lockout_time = datetime.now() + timedelta(minutes=self.LOCKOUT_DURATION_MINUTES)
                    self.app_instance.cursor.execute("UPDATE users SET lockout_until = ? WHERE id = ?",
                                                     (lockout_time.strftime("%Y-%m-%d %H:%M:%S"), user_id))
                    self.app_instance.conn.commit()
                    messagebox.showerror("Giriş Başarısız",
                                         f"Çok sayıda yanlış deneme. Hesap {self.LOCKOUT_DURATION_MINUTES} dakika kilitlenmiştir.")
                else:
                    messagebox.showerror("Giriş Başarısız", "Geçersiz kullanıcı adı veya şifre.")

                time.sleep(1)
        else:
            messagebox.showerror("Giriş Başarısız", "Geçersiz kullanıcı adı veya şifre.")
            time.sleep(1)


class RegisterScreen(ttk.Frame):
    def __init__(self, master, app_instance):
        super().__init__(master)
        self.app_instance = app_instance
        self.master = master

        stil = ttk.Style()
        stil.configure("Register.TLabel", font=("Arial", 12))
        stil.configure("Register.TEntry", font=("Arial", 12))
        stil.configure("Register.TButton", font=("Arial", 12, "bold"), padding=10)

        ttk.Label(self, text="Kayıt Ol", font=("Arial", 16, "bold")).pack(pady=10)

        form_frame = ttk.Frame(self)
        form_frame.pack(pady=10)

        ttk.Label(form_frame, text="Kullanıcı Adı:", style="Register.TLabel").grid(row=0, column=0, padx=5, pady=5,
                                                                                   sticky="w")
        self.username_entry = ttk.Entry(form_frame, style="Register.TEntry", width=30)
        self.username_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(form_frame, text="Şifre:", style="Register.TLabel").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.password_entry = ttk.Entry(form_frame, style="Register.TEntry", show="*", width=30)
        self.password_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(form_frame, text="Şifre Tekrar:", style="Register.TLabel").grid(row=2, column=0, padx=5, pady=5,
                                                                                  sticky="w")
        self.password_confirm_entry = ttk.Entry(form_frame, style="Register.TEntry", show="*", width=30)
        self.password_confirm_entry.grid(row=2, column=1, padx=5, pady=5, sticky="ew")

        ttk.Button(self, text="Kayıt Ol", style="Register.TButton", command=self.register).pack(pady=10)
        ttk.Button(self, text="Giriş Ekranına Dön", style="Register.TButton",
                   command=self.app_instance.show_login_screen).pack(pady=5)

    def register(self):
        username = self.username_entry.get()
        password = self.password_entry.get()
        password_confirm = self.password_confirm_entry.get()

        if not username or not password or not password_confirm:
            messagebox.showerror("Hata", "Tüm alanlar doldurulmalıdır.")
            return

        if password != password_confirm:
            messagebox.showerror("Hata", "Şifreler uyuşmuyor.")
            return

        if len(password) < 8:
            messagebox.showerror("Hata", "Şifre en az 8 karakter olmalıdır.")
            return
        if not re.search("[a-z]", password):
            messagebox.showerror("Hata", "Şifre küçük harf içermelidir.")
            return
        if not re.search("[A-Z]", password):
            messagebox.showerror("Hata", "Şifre büyük harf içermelidir.")
            return
        if not re.search("[0-9]", password):
            messagebox.showerror("Hata", "Şifre sayı içermelidir.")
            return
        if not re.search("[!@#$%^&*(),.?\":{}|<>]", password):
            messagebox.showerror("Hata", "Şifre en az bir özel karakter içermelidir (!@#$%^&* vb.).")
            return

        try:
            self.app_instance.cursor.execute("SELECT id FROM users WHERE kullanici_adi = ?", (username,))
            if self.app_instance.cursor.fetchone():
                messagebox.showerror("Hata", "Bu kullanıcı adı zaten mevcut.")
                return

            hashed_password = hash_password_bcrypt(password)
            self.app_instance.cursor.execute(
                "INSERT INTO users (kullanici_adi, sifre_hash, login_attempts, lockout_until) VALUES (?, ?, ?, ?)",
                (username, hashed_password, 0, None))
            self.app_instance.conn.commit()
            messagebox.showinfo("Başarılı", "Kayıt başarıyla tamamlandı. Şimdi giriş yapabilirsiniz.")
            self.app_instance.show_login_screen()
        except sqlite3.Error as e:
            messagebox.showerror("Hata", f"Kayıt işlemi sırasında hata oluştu: {e}")


class GelirGiderUygulamasi:
    def __init__(self, root, conn, cursor, kullanici_id, username):
        self.root = root
        self.conn = conn
        self.cursor = cursor
        self.kullanici_id = kullanici_id
        self.username = username

        self.selected_item_id = None
        self.selected_recurring_item_id = None
        self.selected_category_id = None
        self.selected_invoice_id = None  # Seçilen fatura/teklif id'si

        # Font Yolu ve Kaydı (GLOBAL_REPORTLAB_FONT_NAME'ı kullan)
        self.font_name = GLOBAL_REPORTLAB_FONT_NAME

        self.arayuz_olustur()

        # İlk sayfa için listelemeler
        self.listele()
        # İkinci sayfa için listelemeler ve kontroller
        self.listele_tekrar_eden_islemler()
        self.kategorileri_yukle()
        # Fatura/Teklif listeleme artık kendi metodunda çağrılacak
        self.listele_fatura_teklifler()

        self.uretim_kontrolu()

    def arayuz_olustur(self):
        stil = ttk.Style()
        stil.theme_use("clam")
        stil.configure("TFrame", background="#f5f5f5")
        stil.configure("TLabel", background="#f5f5f5", font=("Arial", 10))
        stil.configure("TButton", font=("Arial", 10, "bold"), padding=6, background="#e0e0e0")
        stil.map("TButton", background=[('active', '#c0c0c0')])
        stil.configure("Treeview", font=("Arial", 10), rowheight=25)
        stil.configure("Treeview.Heading", font=("Arial", 10, "bold"), background="#d0d0d0")
        stil.map("Treeview.Heading", background=[('active', '#b0b0b0')])
        stil.configure("TLabelframe", background="#f5f5f5", bordercolor="#d0d0d0", relief="solid")
        stil.configure("TLabelframe.Label", font=("Arial", 12, "bold"), foreground="#333333")

        # Ana çerçeve, başlık ve notebook için düzenleme
        baslik_frame = ttk.Frame(self.root, padding="10 10 10 10")
        baslik_frame.pack(pady=0, fill="x", padx=20, side="top")  # En üste sabitlenir

        ttk.Label(baslik_frame, text="Gelişmiş Gelir - Gider Takip Uygulaması",
                  font=("Arial", 18, "bold"), foreground="#0056b3").pack(side="left")
        ttk.Label(baslik_frame, text=f"Kullanıcı: {self.username}",
                  font=("Arial", 10, "italic"), foreground="#555").pack(side="right", padx=10)

        # Ana içerik frame'i (notebook'u barındıracak)
        main_content_frame = ttk.Frame(self.root)
        main_content_frame.pack(pady=10, padx=20, fill="both", expand=True, side="top")

        # Sekmeli Arayüz (Notebook) - main_content_frame içine yerleştirilir
        self.notebook = ttk.Notebook(main_content_frame)
        self.notebook.pack(fill="both", expand=True)

        # Sekme 1: Ana İşlemler
        self.tab_ana_islemler = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_ana_islemler, text="Ana İşlemler")
        self._ana_islemler_arayuzu_olustur(self.tab_ana_islemler)

        # Sekme 2: Gelişmiş Araçlar & Raporlar
        self.tab_gelismis_araclar = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_gelismis_araclar, text="Gelişmiş Araçlar & Raporlar")
        self._gelismis_araclar_arayuzu_olustur(self.tab_gelismis_araclar)

        # YENİ SEKME: Fatura & Teklifler
        self.tab_fatura_teklif = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_fatura_teklif, text="Fatura & Teklifler")
        self._fatura_teklif_arayuzu_olustur(self.tab_fatura_teklif)

    def _ana_islemler_arayuzu_olustur(self, parent_frame):
        giris_frame = ttk.LabelFrame(parent_frame, text="Yeni İşlem Ekle / Düzenle", padding=15)
        giris_frame.pack(pady=10, padx=0, fill="x", expand=False)

        input_widgets = [
            ("İşlem Türü:", "tur_var", ["Gelir", "Gider"], "Combobox"),
            ("Miktar (₺):", "miktar_entry", None, "Entry"),
            ("Kategori:", "kategori_var", [], "Combobox"),
            ("Açıklama:", "aciklama_entry", None, "Entry"),
            ("Tarih:", "tarih_entry", None, "DateEntry")
        ]

        for i, (label_text, var_name, values, widget_type) in enumerate(input_widgets):
            ttk.Label(giris_frame, text=label_text).grid(row=i, column=0, sticky="w", padx=10, pady=5)

            if widget_type == "Combobox":
                var = tk.StringVar()
                cb = ttk.Combobox(giris_frame, textvariable=var, values=values, state="readonly", width=30)
                cb.grid(row=i, column=1, padx=10, pady=5, sticky="ew")
                setattr(self, var_name, var)
                if var_name == "kategori_var":
                    self.kategori_combobox = cb
            elif widget_type == "Entry":
                entry = ttk.Entry(giris_frame, width=35)
                entry.grid(row=i, column=1, padx=10, pady=5, sticky="ew")
                setattr(self, var_name, entry)
            elif widget_type == "DateEntry":
                date_entry = DateEntry(giris_frame, selectmode='day', date_pattern='yyyy-mm-dd', width=32,
                                       background='darkblue', foreground='white', borderwidth=2)
                date_entry.grid(row=i, column=1, padx=10, pady=5, sticky="ew")
                date_entry.set_date(datetime.now().strftime("%Y-%m-%d"))
                setattr(self, var_name, date_entry)

        giris_frame.grid_columnconfigure(1, weight=1)

        buton_frame = ttk.Frame(giris_frame, padding="10 0 0 0")
        buton_frame.grid(row=len(input_widgets), column=0, columnspan=2, pady=10, sticky="ew")

        ttk.Button(buton_frame, text="Kaydet", command=self.kaydet).pack(side="left", padx=5, fill="x", expand=True)
        ttk.Button(buton_frame, text="Güncelle", command=self.guncelle).pack(side="left", padx=5, fill="x", expand=True)
        ttk.Button(buton_frame, text="Temizle", command=self.temizle).pack(side="left", padx=5, fill="x", expand=True)
        ttk.Button(buton_frame, text="Sil", command=self.sil).pack(side="left", padx=5, fill="x", expand=True)

        filtre_frame = ttk.LabelFrame(parent_frame, text="Filtreleme ve Arama", padding=15)
        filtre_frame.pack(pady=10, padx=0, fill="x", expand=False)

        ttk.Label(filtre_frame, text="Tür:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.filtre_tur_var = tk.StringVar(value="Tümü")
        ttk.Combobox(filtre_frame, textvariable=self.filtre_tur_var,
                     values=["Tümü", "Gelir", "Gider"], state="readonly", width=12).grid(row=0, column=1, padx=5,
                                                                                         pady=5, sticky="ew")

        ttk.Label(filtre_frame, text="Kategori:").grid(row=0, column=2, padx=5, pady=5, sticky="w")
        self.filtre_kategori_var = tk.StringVar(value="Tümü")
        self.filtre_kategori_combobox = ttk.Combobox(filtre_frame, textvariable=self.filtre_kategori_var,
                                                     values=["Tümü"], width=12)
        self.filtre_kategori_combobox.grid(row=0, column=3, padx=5, pady=5, sticky="ew")

        ttk.Label(filtre_frame, text="Açıklama/Arama:").grid(row=0, column=4, padx=5, pady=5, sticky="w")
        self.arama_entry = ttk.Entry(filtre_frame, width=20)
        self.arama_entry.grid(row=0, column=5, padx=5, pady=5, sticky="ew")
        self.arama_entry.bind("<KeyRelease>", self.listele)

        ttk.Label(filtre_frame, text="Tarih Aralığı:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.bas_tarih_entry = DateEntry(filtre_frame, selectmode='day', date_pattern='yyyy-mm-dd', width=12)
        self.bas_tarih_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        self.bas_tarih_entry.set_date("2023-01-01")

        ttk.Label(filtre_frame, text="-").grid(row=1, column=2, sticky="w")

        self.bit_tarih_entry = DateEntry(filtre_frame, selectmode='day', date_pattern='yyyy-mm-dd', width=12)
        self.bit_tarih_entry.grid(row=1, column=3, padx=5, pady=5, sticky="ew")
        self.bit_tarih_entry.set_date(datetime.now().strftime("%Y-%m-%d"))

        ttk.Button(filtre_frame, text="Filtrele", command=self.listele).grid(row=1, column=4, columnspan=2, padx=10,
                                                                             pady=5, sticky="ew")

        for i in range(6):
            filtre_frame.grid_columnconfigure(i, weight=1)

        liste_frame = ttk.Frame(parent_frame, padding="10 0 0 0")
        liste_frame.pack(pady=10, padx=0, fill="both", expand=True)  # Bu frame genişleyebilir

        scroll_y = ttk.Scrollbar(liste_frame, orient="vertical")
        scroll_x = ttk.Scrollbar(liste_frame, orient="horizontal")

        self.liste = ttk.Treeview(liste_frame,
                                  columns=("id", "Tür", "Miktar", "Kategori", "Açıklama", "Tarih"),
                                  show="headings",
                                  yscrollcommand=scroll_y.set,
                                  xscrollcommand=scroll_x.set)

        scroll_y.config(command=self.liste.yview)
        scroll_x.config(command=self.liste.xview)

        columns_info = {
            "id": {"text": "ID", "width": 50, "minwidth": 40},
            "Tür": {"text": "Tür", "width": 80, "minwidth": 70},
            "Miktar": {"text": "Miktar (₺)", "width": 100, "minwidth": 90},
            "Kategori": {"text": "Kategori", "width": 100, "minwidth": 90},
            "Açıklama": {"text": "Açıklama", "width": 250, "minwidth": 200},
            "Tarih": {"text": "Tarih", "width": 100, "minwidth": 90}
        }

        for col_name, info in columns_info.items():
            self.liste.heading(col_name, text=info["text"], anchor="w")
            self.liste.column(col_name, width=info["width"], minwidth=info["minwidth"], stretch=tk.NO)

        self.liste.grid(row=0, column=0, sticky="nsew")
        scroll_y.grid(row=0, column=1, sticky="ns")
        scroll_x.grid(row=1, column=0, sticky="ew")

        liste_frame.grid_rowconfigure(0, weight=1)
        liste_frame.grid_columnconfigure(0, weight=1)

        self.liste.bind("<<TreeviewSelect>>", self.liste_secildi)

        ozet_frame = ttk.LabelFrame(parent_frame, text="Özet Bilgiler", padding=15)
        ozet_frame.pack(pady=10, padx=0, fill="x", expand=False)

        self.toplam_gelir_label = ttk.Label(ozet_frame, text="Toplam Gelir: ₺0.00",
                                            font=("Arial", 11, "bold"), foreground="green")
        self.toplam_gelir_label.pack(side="left", padx=20, fill="x", expand=True)

        self.toplam_gider_label = ttk.Label(ozet_frame, text="Toplam Gider: ₺0.00",
                                            font=("Arial", 11, "bold"), foreground="red")
        self.toplam_gider_label.pack(side="left", padx=20, fill="x", expand=True)

        self.bakiye_label = ttk.Label(ozet_frame, text="Bakiye: ₺0.00",
                                      font=("Arial", 11, "bold"))
        self.bakiye_label.pack(side="left", padx=20, fill="x", expand=True)

    def _gelismis_araclar_arayuzu_olustur(self, parent_frame):
        left_panel_advanced = ttk.Frame(parent_frame)
        left_panel_advanced.pack(side="left", fill="both", expand=True, padx=(0, 10))

        right_panel_advanced = ttk.Frame(parent_frame)
        right_panel_advanced.pack(side="right", fill="both", expand=True, padx=(10, 0))

        # --- Tekrarlayan İşlemler Paneli (Sol Panelde) ---
        tekrar_eden_frame = ttk.LabelFrame(left_panel_advanced, text="Tekrarlayan İşlemler Tanımla", padding=15)
        tekrar_eden_frame.pack(pady=10, padx=0, fill="x", expand=False)  # Dikeyde sabit tutulur

        recurring_input_widgets = [
            ("İşlem Türü:", "tur_tekrar_var", ["Gelir", "Gider"], "Combobox"),
            ("Miktar (₺):", "miktar_tekrar_entry", None, "Entry"),
            ("Kategori:", "kategori_tekrar_var", [], "Combobox"),
            ("Açıklama:", "aciklama_tekrar_entry", None, "Entry"),
            ("Başlangıç Tarihi:", "baslangic_tarih_tekrar_entry", None, "DateEntry"),
            ("Sıklık:", "siklilik_var", ["Günlük", "Haftalık", "Aylık", "Yıllık"], "Combobox")
        ]

        for i, (label_text, var_name, values, widget_type) in enumerate(recurring_input_widgets):
            ttk.Label(tekrar_eden_frame, text=label_text).grid(row=i, column=0, padx=10, pady=5, sticky="w")

            if widget_type == "Combobox":
                var = tk.StringVar()
                cb = ttk.Combobox(tekrar_eden_frame, textvariable=var, values=values, state="readonly", width=30)
                cb.grid(row=i, column=1, padx=10, pady=5, sticky="ew")
                setattr(self, var_name, var)
                if var_name == "kategori_tekrar_var":
                    self.kategori_tekrar_combobox = cb
            elif widget_type == "Entry":
                entry = ttk.Entry(tekrar_eden_frame, width=35)
                entry.grid(row=i, column=1, padx=10, pady=5, sticky="ew")
                setattr(self, var_name, entry)
            elif widget_type == "DateEntry":
                date_entry = DateEntry(tekrar_eden_frame, selectmode='day', date_pattern='yyyy-mm-dd', width=32,
                                       background='darkblue', foreground='white', borderwidth=2)
                date_entry.grid(row=i, column=1, padx=10, pady=5, sticky="ew")
                date_entry.set_date(datetime.now().strftime("%Y-%m-%d"))
                setattr(self, var_name, date_entry)

        tekrar_eden_frame.grid_columnconfigure(1, weight=1)

        tekrar_eden_buton_frame = ttk.Frame(tekrar_eden_frame, padding="10 0 0 0")
        tekrar_eden_buton_frame.grid(row=len(recurring_input_widgets), column=0, columnspan=2, pady=10, sticky="ew")

        ttk.Button(tekrar_eden_buton_frame, text="Tekrarlayan Kaydet", command=self.kaydet_tekrar_eden).pack(
            side="left", padx=5, fill="x", expand=True)
        ttk.Button(tekrar_eden_buton_frame, text="Tekrarlayan Sil", command=self.sil_tekrar_eden).pack(side="left",
                                                                                                       padx=5, fill="x",
                                                                                                       expand=True)
        ttk.Button(tekrar_eden_buton_frame, text="Temizle", command=self.temizle_tekrar_eden).pack(side="left", padx=5,
                                                                                                   fill="x",
                                                                                                   expand=True)

        tekrar_eden_liste_frame = ttk.Frame(left_panel_advanced, padding="10 0 0 0")
        tekrar_eden_liste_frame.pack(pady=10, padx=0, fill="both", expand=True)  # Bu frame genişleyebilir

        tekrar_eden_scroll_y = ttk.Scrollbar(tekrar_eden_liste_frame, orient="vertical")
        tekrar_eden_scroll_x = ttk.Scrollbar(tekrar_eden_liste_frame, orient="horizontal")

        self.tekrar_eden_liste = ttk.Treeview(tekrar_eden_liste_frame,
                                              columns=("id", "Tür", "Miktar", "Kategori", "Açıklama",
                                                       "Başlangıç Tarihi", "Sıklık", "Son Üretilen"),
                                              show="headings",
                                              yscrollcommand=tekrar_eden_scroll_y.set,
                                              xscrollcommand=tekrar_eden_scroll_x.set)

        tekrar_eden_scroll_y.config(command=self.tekrar_eden_liste.yview)
        tekrar_eden_scroll_x.config(command=self.tekrar_eden_liste.xview)

        recurring_columns_info = {
            "id": {"text": "ID", "width": 40, "minwidth": 30},
            "Tür": {"text": "Tür", "width": 60, "minwidth": 50},
            "Miktar": {"text": "Miktar (₺)", "width": 90, "minwidth": 80},
            "Kategori": {"text": "Kategori", "width": 90, "minwidth": 80},
            "Açıklama": {"text": "Açıklama", "width": 180, "minwidth": 150},
            "Başlangıç Tarihi": {"text": "Başlangıç Tarihi", "width": 100, "minwidth": 90},
            "Sıklık": {"text": "Sıklık", "width": 80, "minwidth": 70},
            "Son Üretilen": {"text": "Son Üretilen", "width": 100, "minwidth": 90}
        }

        for col_name, info in recurring_columns_info.items():
            self.tekrar_eden_liste.heading(col_name, text=info["text"], anchor="w")
            self.tekrar_eden_liste.column(col_name, width=info["width"], minwidth=info["minwidth"], stretch=tk.NO)

        self.tekrar_eden_liste.grid(row=0, column=0, sticky="nsew")
        tekrar_eden_scroll_y.grid(row=0, column=1, sticky="ns")
        tekrar_eden_scroll_x.grid(row=1, column=0, sticky="ew")

        tekrar_eden_liste_frame.grid_rowconfigure(0, weight=1)
        tekrar_eden_liste_frame.grid_columnconfigure(0, weight=1)

        self.tekrar_eden_liste.bind("<<TreeviewSelect>>", self.tekrar_eden_liste_secildi)

        # --- Kategori Yönetimi Paneli (Sağ Panelde) ---
        kategori_yonetim_frame = ttk.LabelFrame(right_panel_advanced, text="Kategori Yönetimi", padding=15)
        kategori_yonetim_frame.pack(pady=10, padx=0, fill="x", expand=False)  # Dikeyde sabit tutulur

        ttk.Label(kategori_yonetim_frame, text="Kategori Adı:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.kategori_adi_entry = ttk.Entry(kategori_yonetim_frame, width=30)
        self.kategori_adi_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(kategori_yonetim_frame, text="Kategori Türü:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.kategori_tur_var = tk.StringVar()
        self.kategori_tur_combobox = ttk.Combobox(kategori_yonetim_frame, textvariable=self.kategori_tur_var,
                                                  values=["Gelir", "Gider", "Genel"], state="readonly", width=28)
        self.kategori_tur_combobox.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        self.kategori_tur_var.set("Genel")

        kategori_yonetim_frame.grid_columnconfigure(1, weight=1)

        kategori_buton_frame = ttk.Frame(kategori_yonetim_frame, padding="10 0 0 0")
        kategori_buton_frame.grid(row=2, column=0, columnspan=2, pady=10, sticky="ew")
        ttk.Button(kategori_buton_frame, text="Kategori Ekle", command=self.kategori_ekle).pack(side="left", padx=5,
                                                                                                fill="x", expand=True)
        ttk.Button(kategori_buton_frame, text="Kategori Sil", command=self.kategori_sil).pack(side="left", padx=5,
                                                                                              fill="x", expand=True)
        ttk.Button(kategori_buton_frame, text="Temizle", command=self.temizle_kategori).pack(side="left", padx=5,
                                                                                             fill="x", expand=True)

        self.kategori_liste = ttk.Treeview(kategori_yonetim_frame, columns=("id", "Kategori Adı", "Tür"),
                                           show="headings")
        self.kategori_liste.heading("id", text="ID", anchor="w")
        self.kategori_liste.column("id", width=30, minwidth=20, stretch=tk.NO)
        self.kategori_liste.heading("Kategori Adı", text="Kategori Adı", anchor="w")
        self.kategori_liste.column("Kategori Adı", width=150, minwidth=100)
        self.kategori_liste.heading("Tür", text="Tür", anchor="w")
        self.kategori_liste.column("Tür", width=80, minwidth=60, stretch=tk.NO)
        self.kategori_liste.grid(row=3, column=0, columnspan=2, sticky="nsew", padx=5, pady=5)
        self.kategori_liste.bind("<<TreeviewSelect>>", self.kategori_liste_secildi)

        kategori_yonetim_frame.grid_rowconfigure(3, weight=1)

        # --- Grafik ve Rapor Butonları (Sağ Panelde) ---
        grafik_rapor_frame = ttk.LabelFrame(right_panel_advanced, text="Grafik & Rapor İşlemleri", padding=15)
        grafik_rapor_frame.pack(pady=10, padx=0, fill="x", expand=False)  # Dikeyde sabit tutulur
        ttk.Button(grafik_rapor_frame, text="Gelir-Gider Grafikleri", command=self.grafik_goster).pack(pady=5, fill="x")
        ttk.Button(grafik_rapor_frame, text="Gelir-Gider Raporu Oluştur", command=self.rapor_olustur).pack(pady=5,
                                                                                                           fill="x")

        # Fatura/Teklif kısmı buradan KALDIRILDI, yeni sekmeye taşındı.

    def _fatura_teklif_arayuzu_olustur(self, parent_frame):
        # Bu yeni sekme için fatura/teklif yönetim arayüzünü oluşturur
        fatura_teklif_frame = ttk.LabelFrame(parent_frame, text="Fatura / Teklif Oluştur ve Yönet", padding=15)
        fatura_teklif_frame.pack(pady=10, padx=0, fill="both", expand=True)  # Bu frame tüm sekmeyi kaplar

        # Fatura/Teklif giriş alanları ve listesi için grid yapılandırması
        fatura_teklif_frame.grid_columnconfigure(1, weight=1)  # İkinci sütun (giriş alanları) yatayda genişler
        fatura_teklif_frame.grid_rowconfigure(9, weight=1)  # Fatura listesi için ayrılan satır dikeyde genişler

        # Giriş widget'ları için satırları yapılandır
        fatura_input_widgets = [
            ("Tür:", "fatura_tur_var", ["Fatura", "Teklif"], "Combobox"),
            ("Müşteri Adı:", "fatura_musteri_entry", None, "Entry"),
            ("Belge Tarihi:", "fatura_belge_tarih_entry", None, "DateEntry"),
            ("Son Ödeme/Geçerlilik Tarihi:", "fatura_son_odeme_gecerlilik_tarih_entry", None, "DateEntry"),
            ("Ürün/Hizmetler (Ad,Miktar,Fiyat | her satırda bir kalem):", "fatura_urun_hizmetler_text", None, "Text"),
            ("Toplam Tutar (₺):", "fatura_toplam_tutar_entry", None, "Entry"),
            ("Notlar:", "fatura_notlar_text", None, "Text"),
            ("Durum:", "fatura_durum_var", ["Taslak", "Gönderildi", "Ödendi", "İptal Edildi"], "Combobox"),
        ]

        for i, (label_text, var_name, values, widget_type) in enumerate(fatura_input_widgets):
            # fatura_teklif_frame.grid_rowconfigure(i, weight=0) # Giriş satırları dikeyde sabit kalır (Zaten varsayılan)
            ttk.Label(fatura_teklif_frame, text=label_text).grid(row=i, column=0, padx=5, pady=2, sticky="nw")

            if widget_type == "Combobox":
                var = tk.StringVar()
                cb = ttk.Combobox(fatura_teklif_frame, textvariable=var, values=values, state="readonly", width=30)
                cb.grid(row=i, column=1, padx=5, pady=2, sticky="ew")
                setattr(self, var_name, var)
                if var_name == "fatura_tur_var":
                    var.set("Fatura")
                    cb.bind("<<ComboboxSelected>>", self._fatura_tur_secildi)  # Tür seçildiğinde diğer alanları ayarla
                if var_name == "fatura_durum_var":
                    var.set("Taslak")
            elif widget_type == "Entry":
                entry = ttk.Entry(fatura_teklif_frame, width=35)
                entry.grid(row=i, column=1, padx=5, pady=2, sticky="ew")
                setattr(self, var_name, entry)
            elif widget_type == "DateEntry":
                date_entry = DateEntry(fatura_teklif_frame, selectmode='day', date_pattern='yyyy-mm-dd', width=32,
                                       background='darkblue', foreground='white', borderwidth=2)
                date_entry.grid(row=i, column=1, padx=5, pady=2, sticky="ew")
                date_entry.set_date(datetime.now().strftime("%Y-%m-%d"))
                setattr(self, var_name, date_entry)
            elif widget_type == "Text":
                text_widget = tk.Text(fatura_teklif_frame, height=4, width=35)  # Height ve width ayarları
                text_widget.grid(row=i, column=1, padx=5, pady=2, sticky="ew")
                setattr(self, var_name, text_widget)
                if var_name == "fatura_urun_hizmetler_text":
                    text_widget.bind("<KeyRelease>", self._fatura_tutari_hesapla)  # Ürün değiştikçe tutarı hesapla

        fatura_buton_frame = ttk.Frame(fatura_teklif_frame, padding="10 0 0 0")
        fatura_buton_frame.grid(row=len(fatura_input_widgets), column=0, columnspan=2, pady=10, sticky="ew")
        # fatura_teklif_frame.grid_rowconfigure(len(fatura_input_widgets), weight=0) # Buton satırı da sabit kalır (Zaten varsayılan)

        ttk.Button(fatura_buton_frame, text="Kaydet", command=self.fatura_kaydet).pack(side="left", padx=5, fill="x",
                                                                                       expand=True)
        ttk.Button(fatura_buton_frame, text="Güncelle", command=self.fatura_guncelle).pack(side="left", padx=5,
                                                                                           fill="x", expand=True)
        ttk.Button(fatura_buton_frame, text="PDF Oluştur", command=self.fatura_pdf_olustur).pack(side="left", padx=5,
                                                                                                 fill="x", expand=True)
        ttk.Button(fatura_buton_frame, text="Sil", command=self.fatura_sil).pack(side="left", padx=5, fill="x",
                                                                                 expand=True)
        ttk.Button(fatura_buton_frame, text="Temizle", command=self.fatura_temizle).pack(side="left", padx=5, fill="x",
                                                                                         expand=True)

        # Fatura listesi için satır yapılandırması - kalan tüm alanı kaplar
        self.fatura_liste = ttk.Treeview(fatura_teklif_frame,
                                         columns=("id", "Tür", "Müşteri", "Toplam", "Tarih", "Durum"), show="headings")
        self.fatura_liste.heading("id", text="ID", anchor="w")
        self.fatura_liste.column("id", width=30, minwidth=20, stretch=tk.NO)
        self.fatura_liste.heading("Tür", text="Tür", anchor="w")
        self.fatura_liste.column("Tür", width=60, minwidth=50, stretch=tk.NO)
        self.fatura_liste.heading("Müşteri", text="Müşteri Adı", anchor="w")
        self.fatura_liste.column("Müşteri", width=120, minwidth=100)
        self.fatura_liste.heading("Toplam", text="Toplam (₺)", anchor="e")  # Sağ Hizalama
        self.fatura_liste.column("Toplam", width=90, minwidth=80, stretch=tk.NO, anchor="e")  # Sağ Hizalama
        self.fatura_liste.heading("Tarih", text="Tarih", anchor="w")
        self.fatura_liste.column("Tarih", width=90, minwidth=80, stretch=tk.NO)
        self.fatura_liste.heading("Durum", text="Durum", anchor="w")
        self.fatura_liste.column("Durum", width=80, minwidth=70, stretch=tk.NO)

        # Fatura listesini butonların bir sonraki satırına yerleştir
        self.fatura_liste.grid(row=len(fatura_input_widgets) + 1, column=0, columnspan=2, sticky="nsew", padx=5, pady=5)
        # Fatura listesinin olduğu satırın dikeyde genişlemesini sağlar
        fatura_teklif_frame.grid_rowconfigure(len(fatura_input_widgets) + 1, weight=1)

        # Scrollbar'lar eklendi (Fatura listesi için)
        fatura_scroll_y = ttk.Scrollbar(fatura_teklif_frame, orient="vertical", command=self.fatura_liste.yview)
        fatura_scroll_x = ttk.Scrollbar(fatura_teklif_frame, orient="horizontal", command=self.fatura_liste.xview)
        self.fatura_liste.configure(yscrollcommand=fatura_scroll_y.set, xscrollcommand=fatura_scroll_x.set)

        fatura_scroll_y.grid(row=len(fatura_input_widgets) + 1, column=2, sticky="ns")
        fatura_scroll_x.grid(row=len(fatura_input_widgets) + 2, column=0, columnspan=2, sticky="ew")

        self.fatura_liste.bind("<<TreeviewSelect>>", self.fatura_liste_secildi)

    # --- Ana İşlem Fonksiyonları ---
    def kaydet(self):
        tur = self.tur_var.get()
        miktar_str = self.miktar_entry.get()
        kategori = self.kategori_var.get()
        aciklama = self.aciklama_entry.get()
        tarih = self.tarih_entry.get_date().strftime("%Y-%m-%d")

        if not tur:
            messagebox.showerror("Hata", "Lütfen işlem türünü seçiniz.")
            return

        try:
            miktar = float(miktar_str)
            if miktar <= 0:
                messagebox.showerror("Hata", "Miktar pozitif bir sayı olmalıdır.")
                return
        except ValueError:
            messagebox.showerror("Hata", "Geçersiz miktar değeri. Lütfen sayı giriniz.")
            return

        if not kategori or kategori == "Kategori Seçin":
            messagebox.showerror("Hata", "Lütfen bir kategori seçiniz.")
            return

        if not tarih:
            messagebox.showerror("Hata", "Lütfen geçerli bir tarih seçiniz.")
            return

        try:
            self.cursor.execute("""
                INSERT INTO islemler (tur, miktar, kategori, aciklama, tarih, kullanici_id)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (tur, miktar, kategori, aciklama, tarih, self.kullanici_id))
            self.conn.commit()

            messagebox.showinfo("Başarılı", "İşlem başarıyla kaydedildi.")
            self.temizle()
            self.listele()
        except sqlite3.Error as e:
            messagebox.showerror("Hata", f"Veritabanına kaydetme hatası: {e}")

    def guncelle(self):
        if self.selected_item_id is None:
            messagebox.showwarning("Uyarı", "Lütfen güncellemek istediğiniz kaydı seçiniz.")
            return

        tur = self.tur_var.get()
        miktar_str = self.miktar_entry.get()
        kategori = self.kategori_var.get()
        aciklama = self.aciklama_entry.get()
        tarih = self.tarih_entry.get_date().strftime("%Y-%m-%d")

        if not tur:
            messagebox.showerror("Hata", "Lütfen işlem türünü seçiniz.")
            return

        try:
            miktar = float(miktar_str)
            if miktar <= 0:
                messagebox.showerror("Hata", "Miktar pozitif bir sayı olmalıdır.")
                return
        except ValueError:
            messagebox.showerror("Hata", "Geçersiz miktar değeri. Lütfen sayı giriniz.")
            return

        if not kategori or kategori == "Kategori Seçin":
            messagebox.showerror("Hata", "Lütfen bir kategori seçiniz.")
            return

        if not tarih:
            messagebox.showerror("Hata", "Lütfen geçerli bir tarih seçiniz.")
            return

        try:
            self.cursor.execute("""
                UPDATE islemler SET tur = ?, miktar = ?, kategori = ?, aciklama = ?, tarih = ?
                WHERE id = ? AND kullanici_id = ?
            """, (tur, miktar, kategori, aciklama, tarih, self.selected_item_id, self.kullanici_id))
            self.conn.commit()
            messagebox.showinfo("Başarılı", "Kayıt başarıyla güncellendi.")
            self.temizle()
            self.listele()
        except sqlite3.Error as e:
            messagebox.showerror("Hata", f"Veritabanı güncelleme hatası: {e}")

    def listele(self, event=None):
        for row in self.liste.get_children():
            self.liste.delete(row)

        tur = self.filtre_tur_var.get()
        kategori = self.filtre_kategori_var.get()

        bas_tarih = self.bas_tarih_entry.get_date().strftime("%Y-%m-%d") if self.bas_tarih_entry.get() else ""
        bit_tarih = self.bit_tarih_entry.get_date().strftime("%Y-%m-%d") if self.bit_tarih_entry.get() else ""
        arama_terimi = self.arama_entry.get().strip()

        sql = "SELECT id, tur, miktar, kategori, aciklama, tarih FROM islemler WHERE kullanici_id = ?"
        params = [self.kullanici_id]

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

        try:
            self.cursor.execute(sql, params)
            veriler = self.cursor.fetchall()
        except sqlite3.Error as e:
            messagebox.showerror("Veritabanı Hatası", f"Veri çekme hatası: {e}")
            return

        toplam_gelir = 0
        toplam_gider = 0

        for veri in veriler:
            self.liste.insert("", tk.END, values=veri)

            if veri[1] == "Gelir":
                toplam_gelir += veri[2]
            else:
                toplam_gider += veri[2]

        self.toplam_gelir_label.config(text=f"Toplam Gelir: ₺{toplam_gelir:,.2f}")
        self.toplam_gider_label.config(text=f"Toplam Gider: ₺{toplam_gider:,.2f}")
        bakiye = toplam_gelir - toplam_gider
        self.bakiye_label.config(text=f"Bakiye: ₺{bakiye:,.2f}",
                                 foreground="blue" if bakiye >= 0 else "red")

    def liste_secildi(self, event):
        selected_items = self.liste.selection()
        if selected_items:
            selected_item = selected_items[0]
            values = self.liste.item(selected_item, "values")
            self.selected_item_id = values[0]

            self.tur_var.set(values[1])
            self.miktar_entry.delete(0, tk.END)
            self.miktar_entry.insert(0, values[2])
            self.kategori_var.set(values[3])
            self.aciklama_entry.delete(0, tk.END)
            self.aciklama_entry.insert(0, values[4])
            try:
                date_obj = datetime.strptime(values[5], "%Y-%m-%d").date()
                self.tarih_entry.set_date(date_obj)
            except ValueError:
                self.tarih_entry.set_date(datetime.now().date())
        else:
            self.selected_item_id = None
            self.temizle()

    def temizle(self):
        self.tur_var.set("Gelir")
        self.miktar_entry.delete(0, tk.END)
        self.kategori_var.set("Kategori Seçin")
        self.aciklama_entry.delete(0, tk.END)
        self.tarih_entry.set_date(datetime.now().date())
        self.selected_item_id = None

    def sil(self):
        selected_items = self.liste.selection()
        if not selected_items:
            messagebox.showwarning("Uyarı", "Lütfen silmek istediğiniz kaydı seçiniz.")
            return

        selected_item = selected_items[0]
        values = self.liste.item(selected_item, "values")
        record_id = values[0]

        onay = messagebox.askyesno("Onay", "Seçili kaydı silmek istediğinize emin misiniz?")
        if onay:
            try:
                self.cursor.execute("DELETE FROM islemler WHERE id = ? AND kullanici_id = ?",
                                    (record_id, self.kullanici_id))
                self.conn.commit()
                messagebox.showinfo("Başarılı", "Kayıt başarıyla silindi.")
                self.listele()
                self.temizle()
            except sqlite3.Error as e:
                messagebox.showerror("Hata", f"Kayıt silme hatası: {e}")

    def grafik_goster(self):
        self.cursor.execute("""
            SELECT tur, kategori, SUM(miktar) FROM islemler WHERE kullanici_id = ? GROUP BY tur, kategori
        """, (self.kullanici_id,))
        kategori_verileri = self.cursor.fetchall()

        self.cursor.execute("""
            SELECT tarih, tur, miktar FROM islemler WHERE kullanici_id = ? ORDER BY tarih ASC
        """, (self.kullanici_id,))
        zaman_verileri = self.cursor.fetchall()

        if not kategori_verileri and not zaman_verileri:
            messagebox.showinfo("Bilgi", "Gösterilecek veri bulunamadı.")
            return

        grafik_pencere = tk.Toplevel(self.root)
        grafik_pencere.title("Gelir-Gider Grafikleri")
        grafik_pencere.geometry("1000x700")

        fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(18, 6))
        fig.tight_layout(pad=4.0)

        gelirler = [v for v in kategori_verileri if v[0] == "Gelir"]
        if gelirler:
            gelir_miktarlari = [v[2] for v in gelirler]
            gelir_kategorileri = [f"{v[1]} ({v[2]:,.2f}₺)" for v in gelirler]
            ax1.pie(gelir_miktarlari,
                    labels=gelir_kategorileri,
                    autopct='%1.1f%%',
                    startangle=90,
                    pctdistance=0.85)
            ax1.set_title("Gelir Dağılımı", fontsize=14)
            ax1.axis('equal')
        else:
            ax1.text(0.5, 0.5, "Gelir Verisi Yok", horizontalalignment='center', verticalalignment='center',
                     transform=ax1.transAxes, fontsize=12)
            ax1.set_title("Gelir Dağılımı", fontsize=14)
            ax1.axis('off')

        giderler = [v for v in kategori_verileri if v[0] == "Gider"]
        if giderler:
            gider_miktarlari = [v[2] for v in giderler]
            gider_kategorileri = [f"{v[1]} ({v[2]:,.2f}₺)" for v in giderler]
            ax2.pie(gider_miktarlari,
                    labels=gider_kategorileri,
                    autopct='%1.1f%%',
                    startangle=90,
                    pctdistance=0.85)
            ax2.set_title("Gider Dağılımı", fontsize=14)
            ax2.axis('equal')
        else:
            ax2.text(0.5, 0.5, "Gider Verisi Yok", horizontalalignment='center', verticalalignment='center',
                     transform=ax2.transAxes, fontsize=12)
            ax2.set_title("Gider Dağılımı", fontsize=14)
            ax2.axis('off')

        if zaman_verileri:
            tarihler = sorted(list(set([v[0] for v in zaman_verileri])))
            gunluk_bakiye = {t: 0.0 for t in tarihler}

            for tarih, tur, miktar in zaman_verileri:
                if tur == "Gelir":
                    gunluk_bakiye[tarih] += miktar
                else:
                    gunluk_bakiye[tarih] -= miktar

            kumulatif_bakiye = []
            current_bakiye = 0
            for tarih in tarihler:
                current_bakiye += gunluk_bakiye[tarih]
                kumulatif_bakiye.append(current_bakiye)

            ax3.plot(tarihler, kumulatif_bakiye, marker='o', linestyle='-', color='purple')
            ax3.set_title("Zaman İçinde Kümülatif Bakiye", fontsize=14)
            ax3.set_xlabel("Tarih", fontsize=12)
            ax3.set_ylabel("Bakiye (₺)", fontsize=12)
            ax3.tick_params(axis='x', rotation=45)
            ax3.grid(True, linestyle='--', alpha=0.6)
            num_ticks = min(len(tarihler), 10)
            ax3.xaxis.set_major_locator(plt.MaxNLocator(num_ticks))
        else:
            ax3.text(0.5, 0.5, "Bakiye Verisi Yok", horizontalalignment='center', verticalalignment='center',
                     transform=ax3.transAxes, fontsize=12)
            ax3.set_title("Zaman İçinde Kümülatif Bakiye", fontsize=14)
            ax3.axis('off')

        canvas = FigureCanvasTkAgg(fig, master=grafik_pencere)
        canvas.draw()
        canvas.get_tk_widget().pack(side="top", fill="both", expand=True)

    # --- Tekrarlayan İşlem Fonksiyonları ---

    def kaydet_tekrar_eden(self):
        tur = self.tur_tekrar_var.get()
        miktar_str = self.miktar_tekrar_entry.get()
        kategori = self.kategori_tekrar_var.get()
        aciklama = self.aciklama_tekrar_entry.get()
        baslangic_tarih_degeri = self.baslangic_tarih_tekrar_entry.get_date().strftime("%Y-%m-%d")
        siklilik = self.siklilik_var.get()

        if not all([tur, miktar_str, kategori, baslangic_tarih_degeri, siklilik]):
            messagebox.showerror("Hata", "Lütfen tüm tekrarlayan işlem alanlarını doldurunuz.")
            return

        try:
            miktar = float(miktar_str)
            if miktar <= 0:
                messagebox.showerror("Hata", "Miktar pozitif bir sayı olmalıdır.")
                return
        except ValueError:
            messagebox.showerror("Hata", "Geçersiz miktar değeri. Lütfen sayı giriniz.")
            return

        if not kategori or kategori == "Kategori Seçin":
            messagebox.showerror("Hata", "Lütfen bir kategori seçiniz.")
            return

        if not baslangic_tarih_degeri:
            messagebox.showerror("Hata", "Lütfen geçerli bir başlangıç tarihi seçiniz.")
            return

        try:
            self.cursor.execute("""
                INSERT INTO tekrar_eden_islemler (tur, miktar, kategori, aciklama, baslangic_tarihi, siklilik, son_uretilen_tarih, kullanici_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (tur, miktar, kategori, aciklama, baslangic_tarih_degeri, siklilik, baslangic_tarih_degeri,
                  self.kullanici_id))
            self.conn.commit()

            messagebox.showinfo("Başarılı", "Tekrarlayan işlem başarıyla kaydedildi.")
            self.temizle_tekrar_eden()
            self.listele_tekrar_eden_islemler()
            self.uretim_kontrolu()
        except sqlite3.Error as e:
            messagebox.showerror("Hata", f"Tekrarlayan işlem kaydetme hatası: {e}")

    def sil_tekrar_eden(self):
        selected_items = self.tekrar_eden_liste.selection()
        if not selected_items:
            messagebox.showwarning("Uyarı", "Lütfen silmek istediğiniz tekrarlayan kaydı seçiniz.")
            return

        selected_item = selected_items[0]
        values = self.tekrar_eden_liste.item(selected_item, "values")
        record_id = values[0]

        onay = messagebox.askyesno("Onay", "Seçili tekrarlayan kaydı silmek istediğinize emin misiniz?")
        if onay:
            try:
                self.cursor.execute("DELETE FROM tekrar_eden_islemler WHERE id = ? AND kullanici_id = ?",
                                    (record_id, self.kullanici_id))
                self.conn.commit()
                messagebox.showinfo("Başarılı", "Tekrarlayan kayıt başarıyla silindi.")
                self.listele_tekrar_eden_islemler()
                self.temizle_tekrar_eden()
            except sqlite3.Error as e:
                messagebox.showerror("Hata", f"Tekrarlayan kayıt silme hatası: {e}")

    def listele_tekrar_eden_islemler(self):
        for row in self.tekrar_eden_liste.get_children():
            self.tekrar_eden_liste.delete(row)

        try:
            self.cursor.execute(
                "SELECT id, tur, miktar, kategori, aciklama, baslangic_tarihi, siklilik, son_uretilen_tarih FROM tekrar_eden_islemler WHERE kullanici_id = ? ORDER BY baslangic_tarihi DESC",
                (self.kullanici_id,))
            veriler = self.cursor.fetchall()
            for veri in veriler:
                self.tekrar_eden_liste.insert("", tk.END, values=veri)
        except sqlite3.Error as e:
            messagebox.showerror("Veritabanı Hatası", f"Tekrarlayan veri çekme hatası: {e}")

    def tekrar_eden_liste_secildi(self, event):
        selected_items = self.tekrar_eden_liste.selection()
        if selected_items:
            selected_item = selected_items[0]
            values = self.tekrar_eden_liste.item(selected_item, "values")
            self.selected_recurring_item_id = values[0]

            self.tur_tekrar_var.set(values[1])
            self.miktar_tekrar_entry.delete(0, tk.END)
            self.miktar_tekrar_entry.insert(0, values[2])
            self.kategori_tekrar_var.set(values[3])
            self.aciklama_tekrar_entry.delete(0, tk.END)
            self.aciklama_tekrar_entry.insert(0, values[4])
            try:
                date_obj = datetime.strptime(values[5], "%Y-%m-%d").date()
                self.baslangic_tarih_tekrar_entry.set_date(date_obj)
            except ValueError:
                self.baslangic_tarih_tekrar_entry.set_date(datetime.now().date())
            self.siklilik_var.set(values[6])
        else:
            self.selected_recurring_item_id = None
            self.temizle_tekrar_eden()

    def temizle_tekrar_eden(self):
        self.tur_tekrar_var.set("Gelir")
        self.miktar_tekrar_entry.delete(0, tk.END)
        self.kategori_tekrar_var.set("Kategori Seçin")
        self.aciklama_tekrar_entry.delete(0, tk.END)
        self.baslangic_tarih_tekrar_entry.set_date(datetime.now().date())
        self.siklilik_var.set("Aylık")
        self.selected_recurring_item_id = None

    def uretim_kontrolu(self):
        bugun = datetime.now().date()
        uretilen_islem_sayisi = 0
        uretilen_mesajlar = []

        try:
            self.cursor.execute(
                "SELECT id, tur, miktar, kategori, aciklama, baslangic_tarihi, siklilik, son_uretilen_tarih FROM tekrar_eden_islemler WHERE kullanici_id = ?",
                (self.kullanici_id,))
            tekrar_eden_kayitlar = self.cursor.fetchall()

            for kayit in tekrar_eden_kayitlar:
                (rec_id, tur, miktar, kategori, aciklama, baslangic_tarih_str, siklilik, son_uretilen_tarih_str) = kayit

                baslangic_tarih = datetime.strptime(baslangic_tarih_str, "%Y-%m-%d").date()
                son_uretilen_tarih = datetime.strptime(son_uretilen_tarih_str, "%Y-%m-%d").date()

                next_due_date = son_uretilen_tarih

                if baslangic_tarih > son_uretilen_tarih:
                    next_due_date = baslangic_tarih

                while next_due_date <= bugun:
                    if next_due_date > son_uretilen_tarih:
                        try:
                            self.cursor.execute("""
                                INSERT INTO islemler (tur, miktar, kategori, aciklama, tarih, kullanici_id)
                                VALUES (?, ?, ?, ?, ?, ?)
                            """, (tur, miktar, kategori, aciklama, next_due_date.strftime("%Y-%m-%d"),
                                  self.kullanici_id))
                            self.conn.commit()
                            uretilen_islem_sayisi += 1
                            uretilen_mesajlar.append(
                                f"{tur} - {miktar:,.2f}₺ ({kategori}) tarihinde: {next_due_date.strftime('%Y-%m-%d')}")
                        except sqlite3.Error as e:
                            print(f"Hata: Tekrarlayan işlem üretilemedi ({rec_id}): {e}")
                            break

                    self.cursor.execute("UPDATE tekrar_eden_islemler SET son_uretilen_tarih = ? WHERE id = ?",
                                        (next_due_date.strftime("%Y-%m-%d"), rec_id))
                    self.conn.commit()

                    if siklilik == "Günlük":
                        next_due_date += timedelta(days=1)
                    elif siklilik == "Haftalık":
                        next_due_date += timedelta(weeks=1)
                    elif siklilik == "Aylık":
                        gun = next_due_date.day
                        ay = next_due_date.month + 1
                        yil = next_due_date.year
                        if ay > 12:
                            ay = 1
                            yil += 1
                        try:
                            next_due_date = next_due_date.replace(year=yil, month=ay)
                        except ValueError:
                            next_due_date = datetime(yil, ay, 1).date() - timedelta(days=1)
                    elif siklilik == "Yıllık":
                        next_due_date = next_due_date.replace(year=next_due_date.year + 1)
                    else:
                        break

        except sqlite3.Error as e:
            messagebox.showerror("Veritabanı Hatası", f"Tekrarlayan işlemler kontrol edilirken hata oluştu: {e}")

        if uretilen_islem_sayisi > 0:
            mesaj = f"Bugün {uretilen_islem_sayisi} adet tekrarlayan işlem otomatik olarak oluşturuldu:\n\n"
            mesaj += "\n".join(uretilen_mesajlar[:10])
            if uretilen_islem_sayisi > 10:
                mesaj += "\n..."
            messagebox.showinfo("Tekrarlayan İşlem Bildirimi", mesaj)
            self.listele()

    def __del__(self):
        pass

        # --- Kategori Yönetimi Fonksiyonları ---

    def kategorileri_yukle(self):
        for row in self.kategori_liste.get_children():
            self.kategori_liste.delete(row)

        try:
            self.cursor.execute(
                "SELECT id, kategori_adi, tur FROM categories WHERE kullanici_id = ? ORDER BY kategori_adi ASC",
                (self.kullanici_id,))
            kategoriler = self.cursor.fetchall()

            kategori_adlari = ["Kategori Seçin"]
            filtre_kategori_adlari = ["Tümü"]

            for kategori in kategoriler:
                self.kategori_liste.insert("", tk.END, values=kategori)
                kategori_adlari.append(kategori[1])
                filtre_kategori_adlari.append(kategori[1])

            self.kategori_combobox['values'] = kategori_adlari
            self.kategori_combobox.set("Kategori Seçin")

            self.kategori_tekrar_combobox['values'] = kategori_adlari
            self.kategori_tekrar_combobox.set("Kategori Seçin")

            self.filtre_kategori_combobox['values'] = filtre_kategori_adlari
            self.filtre_kategori_combobox.set("Tümü")


        except sqlite3.Error as e:
            messagebox.showerror("Veritabanı Hatası", f"Kategoriler yüklenirken hata oluştu: {e}")

    def kategori_ekle(self):
        kategori_adi = self.kategori_adi_entry.get().strip()
        kategori_tur = self.kategori_tur_var.get()

        if not kategori_adi:
            messagebox.showerror("Hata", "Kategori adı boş bırakılamaz.")
            return
        if not kategori_tur:
            messagebox.showerror("Hata", "Kategori türü seçilmelidir.")
            return

        try:
            self.cursor.execute("INSERT INTO categories (kategori_adi, tur, kullanici_id) VALUES (?, ?, ?)",
                                (kategori_adi, kategori_tur, self.kullanici_id))
            self.conn.commit()
            messagebox.showinfo("Başarılı", "Kategori başarıyla eklendi.")
            self.temizle_kategori()
            self.kategorileri_yukle()
        except sqlite3.IntegrityError:
            messagebox.showerror("Hata", "Bu kategori adı zaten mevcut.")
        except sqlite3.Error as e:
            messagebox.showerror("Hata", f"Kategori eklenirken hata oluştu: {e}")

    def kategori_sil(self):
        selected_items = self.kategori_liste.selection()
        if not selected_items:
            messagebox.showwarning("Uyarı", "Lütfen silmek istediğiniz kategoriyi seçiniz.")
            return

        selected_item = selected_items[0]
        values = self.kategori_liste.item(selected_item, "values")
        category_id = values[0]
        kategori_adi = values[1]

        self.cursor.execute("SELECT COUNT(*) FROM islemler WHERE kategori = ? AND kullanici_id = ?",
                            (kategori_adi, self.kullanici_id))
        islem_sayisi = self.cursor.fetchone()[0]

        if islem_sayisi > 0:
            onay = messagebox.askyesno("Uyarı",
                                       f"'{kategori_adi}' kategorisi {islem_sayisi} adet işlemde kullanılmaktadır. Bu kategoriyi silerseniz, bu işlemlerin kategori bilgisi boş kalacaktır. Emin misiniz?")
        else:
            onay = messagebox.askyesno("Onay", f"'{kategori_adi}' kategorisini silmek istediğinize emin misiniz?")

        if onay:
            try:
                self.cursor.execute("UPDATE islemler SET kategori = NULL WHERE kategori = ? AND kullanici_id = ?",
                                    (kategori_adi, self.kullanici_id))
                self.cursor.execute(
                    "UPDATE tekrar_eden_islemler SET kategori = NULL WHERE kategori = ? AND kullanici_id = ?",
                    (kategori_adi, self.kullanici_id))

                self.cursor.execute("DELETE FROM categories WHERE id = ? AND kullanici_id = ?",
                                    (category_id, self.kullanici_id))
                self.conn.commit()
                messagebox.showinfo("Başarılı", "Kategori başarıyla silindi.")
                self.temizle_kategori()
                self.kategorileri_yukle()
                self.listele()
            except sqlite3.Error as e:
                messagebox.showerror("Hata", f"Kategori silinirken hata oluştu: {e}")

    def kategori_liste_secildi(self, event):
        selected_items = self.kategori_liste.selection()
        if selected_items:
            selected_item = selected_items[0]
            values = self.kategori_liste.item(selected_item, "values")
            self.selected_category_id = values[0]

            self.kategori_adi_entry.delete(0, tk.END)
            self.kategori_adi_entry.insert(0, values[1])
            self.kategori_tur_var.set(values[2])
        else:
            self.selected_category_id = None
            self.temizle_kategori()

    def temizle_kategori(self):
        self.kategori_adi_entry.delete(0, tk.END)
        self.kategori_tur_var.set("Genel")
        self.selected_category_id = None

    # --- Raporlama Fonksiyonları ---
    def rapor_olustur(self):
        tur = self.filtre_tur_var.get()
        kategori = self.filtre_kategori_var.get()
        bas_tarih = self.bas_tarih_entry.get_date().strftime("%Y-%m-%d") if self.bas_tarih_entry.get() else ""
        bit_tarih = self.bit_tarih_entry.get_date().strftime("%Y-%m-%d") if self.bit_tarih_entry.get() else ""
        arama_terimi = self.arama_entry.get().strip()

        sql = "SELECT id, tur, miktar, kategori, aciklama, tarih FROM islemler WHERE kullanici_id = ?"
        params = [self.kullanici_id]

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

        try:
            self.cursor.execute(sql, params)
            rapor_verileri = self.cursor.fetchall()
        except sqlite3.Error as e:
            messagebox.showerror("Veritabanı Hatası", f"Rapor verileri çekilirken hata oluştu: {e}")
            return

        if not rapor_verileri:
            messagebox.showinfo("Bilgi", "Seçilen kriterlere göre rapor oluşturulacak veri bulunamadı.")
            return

        rapor_secenekleri_pencere = tk.Toplevel(self.root)
        rapor_secenekleri_pencere.title("Rapor Kaydet")
        rapor_secenekleri_pencere.geometry("300x150")
        rapor_secenekleri_pencere.transient(self.root)
        rapor_secenekleri_pencere.grab_set()

        ttk.Label(rapor_secenekleri_pencere, text="Raporu hangi formatta kaydetmek istersiniz?").pack(pady=10)

        ttk.Button(rapor_secenekleri_pencere, text="Excel Olarak Kaydet",
                   command=lambda: self._excel_rapor_olustur(rapor_verileri, rapor_secenekleri_pencere)).pack(pady=5)

        ttk.Button(rapor_secenekleri_pencere, text="PDF Olarak Kaydet",
                   command=lambda: self._pdf_rapor_olustur(rapor_verileri, rapor_secenekleri_pencere)).pack(pady=5)

    def _excel_rapor_olustur(self, data, parent_window):
        parent_window.destroy()

        if not data:
            messagebox.showwarning("Uyarı", "Excel raporu oluşturulacak veri bulunamadı.")
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel Dosyaları", "*.xlsx")],
            title="Excel Raporu Kaydet"
        )
        if not file_path:
            return

        try:
            df = pd.DataFrame(data, columns=["ID", "Tür", "Miktar", "Kategori", "Açıklama", "Tarih"])
            df.to_excel(file_path, index=False)
            messagebox.showinfo("Başarılı", f"Excel raporu başarıyla kaydedildi:\n{file_path}")
        except Exception as e:
            messagebox.showerror("Hata", f"Excel raporu oluşturulurken hata oluştu: {e}")

    def _pdf_rapor_olustur(self, data, parent_window):
        parent_window.destroy()

        if not data:
            messagebox.showwarning("Uyarı", "PDF raporu oluşturulacak veri bulunamadı.")
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF Dosyaları", "*.pdf")],
            title="PDF Raporu Kaydet"
        )
        if not file_path:
            return

        try:
            doc = SimpleDocTemplate(file_path, pagesize=letter)
            styles = getSampleStyleSheet()

            # Başlık Stilleri (FontName güncellendi)
            title_style = ParagraphStyle(
                'TitleStyle',
                parent=styles['h1'],
                fontName=self.font_name,
                fontSize=20,
                spaceAfter=14,
                alignment=TA_CENTER
            )
            heading_style = ParagraphStyle(
                'HeadingStyle',
                parent=styles['h2'],
                fontName=self.font_name,
                fontSize=14,
                spaceAfter=10,
                alignment=TA_CENTER
            )
            # Normal metinler için ayrı bir ParagraphStyle oluşturup fontu belirtiyoruz
            normal_style = ParagraphStyle(
                'NormalStyle',
                parent=styles['Normal'],
                fontName=self.font_name,
                fontSize=10,
                leading=12
            )

            elements = []

            elements.append(Paragraph("Gelir-Gider Uygulaması Raporu", title_style))
            elements.append(Spacer(1, 0.2 * 10 * 6))

            # Filtre Bilgileri (normal_style kullanıldı)
            filtre_bilgisi = f"<b>Rapor Tarihi:</b> {datetime.now().strftime('%Y-%m-%d %H:%M')}<br/>" \
                             f"<b>Kullanıcı:</b> {self.username}<br/>" \
                             f"<b>Filtreler:</b> Tür: {self.filtre_tur_var.get()}, Kategori: {self.filtre_kategori_var.get()}<br/>" \
                             f"Tarih Aralığı: {self.bas_tarih_entry.get_date().strftime('%Y-%m-%d')} - {self.bit_tarih_entry.get_date().strftime('%Y-%m-%d')}<br/>" \
                             f"Arama Terimi: {self.arama_entry.get().strip() or 'Yok'}"
            elements.append(Paragraph(filtre_bilgisi, normal_style))  # Normal stili kullan
            elements.append(Spacer(1, 0.2 * 10 * 6))

            table_data = [["ID", "Tür", "Miktar (₺)", "Kategori", "Açıklama", "Tarih"]]
            total_gelir = 0
            total_gider = 0

            for row in data:
                table_data.append([
                    Paragraph(str(row[0]), normal_style),
                    Paragraph(row[1], normal_style),
                    Paragraph(f"{row[2]:,.2f}", normal_style),
                    Paragraph(row[3] if row[3] else '', normal_style),
                    Paragraph(row[4] if row[4] else '', normal_style),
                    Paragraph(row[5], normal_style)
                ])
                if row[1] == "Gelir":
                    total_gelir += row[2]
                else:
                    total_gider += row[2]

            table_style = TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#D0D0D0")),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('FONTNAME', (0, 0), (-1, 0), self.font_name),  # Başlık fontu
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor("#F5F5F5")),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('LEFTPADDING', (0, 0), (-1, -1), 4),
                ('RIGHTPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('FONTNAME', (0, 1), (-1, -1), self.font_name),  # Hücre fontu
                ('FONTSIZE', (0, 1), (-1, -1), 9),
            ])

            col_widths = [0.05 * letter[0], 0.08 * letter[0], 0.12 * letter[0], 0.15 * letter[0], 0.45 * letter[0],
                          0.15 * letter[0]]

            table_style.add('ALIGN', (2, 0), (2, -1), 'RIGHT')

            table = Table(table_data, colWidths=col_widths)
            table.setStyle(table_style)
            elements.append(table)
            elements.append(Spacer(1, 0.2 * 10 * 6))

            elements.append(
                Paragraph(f"<b>Toplam Gelir:</b> <font color='green'>₺{total_gelir:,.2f}</font>", normal_style))
            elements.append(
                Paragraph(f"<b>Toplam Gider:</b> <font color='red'>₺{total_gider:,.2f}</font>", normal_style))
            elements.append(
                Paragraph(f"<b>Bakiye:</b> <font color='blue'>₺{total_gelir - total_gider:,.2f}</font>", normal_style))

            doc.build(elements)
            messagebox.showinfo("Başarılı", f"PDF raporu başarıyla kaydedildi:\n{file_path}")
        except Exception as e:
            messagebox.showerror("Hata",
                                 f"PDF raporu oluşturulurken hata oluştu: {e}\nPDF kütüphanesi Türkçe karakter desteği için ek font ayarları gerektirebilir. Lütfen '{GLOBAL_FONT_FILE_NAME}' dosyasının uygulamanızın bulunduğu dizinde olduğundan emin olun.")

    # --- Fatura/Teklif Fonksiyonları ---
    def _fatura_tur_secildi(self, event):
        selected_type = self.fatura_tur_var.get()
        if selected_type == "Fatura":
            self.fatura_durum_var.set("Taslak")
            self.fatura_son_odeme_gecerlilik_tarih_entry.config(date_pattern='yyyy-mm-dd')
            # self.fatura_son_odeme_gecerlilik_tarih_entry.set_date(datetime.now().strftime("%Y-%m-%d")) # Otomatik tarih atama isteğe bağlı
        elif selected_type == "Teklif":
            self.fatura_durum_var.set("Taslak")  # Teklifler genellikle durum olarak taslak başlar
            self.fatura_son_odeme_gecerlilik_tarih_entry.config(date_pattern='yyyy-mm-dd')
            # self.fatura_son_odeme_gecerlilik_tarih_entry.set_date(datetime.now().strftime("%Y-%m-%d"))

    def _fatura_tutari_hesapla(self, event=None):
        items_text = self.fatura_urun_hizmetler_text.get("1.0", tk.END).strip()
        total_amount = 0.0
        if items_text:
            for line in items_text.split('\n'):
                parts = [p.strip() for p in line.split(',') if p.strip()]
                if len(parts) == 3:  # Ad, Miktar, Fiyat formatı
                    try:
                        quantity = float(parts[1].replace(",", "."))  # Virgülü noktaya çevir
                        price = float(parts[2].replace(",", "."))  # Virgülü noktaya çevir
                        total_amount += (quantity * price)
                    except ValueError:
                        pass  # Geçersiz satırları görmezden gel
        self.fatura_toplam_tutar_entry.delete(0, tk.END)
        self.fatura_toplam_tutar_entry.insert(0, f"{total_amount:,.2f}")

    def fatura_kaydet(self):
        tur = self.fatura_tur_var.get()
        musteri_adi = self.fatura_musteri_entry.get().strip()
        belge_tarihi = self.fatura_belge_tarih_entry.get_date().strftime("%Y-%m-%d")
        son_odeme_gecerlilik_tarihi = self.fatura_son_odeme_gecerlilik_tarih_entry.get_date().strftime("%Y-%m-%d")
        urun_hizmetler_text = self.fatura_urun_hizmetler_text.get("1.0", tk.END).strip()
        toplam_tutar_str = self.fatura_toplam_tutar_entry.get().replace(".", "").replace(",", ".").replace("₺",
                                                                                                           "").strip()  # Türk Lirası formatından float'a çevir
        notlar = self.fatura_notlar_text.get("1.0", tk.END).strip()
        durum = self.fatura_durum_var.get()

        if not all([tur, musteri_adi, belge_tarihi, son_odeme_gecerlilik_tarihi, urun_hizmetler_text, toplam_tutar_str,
                    durum]):
            messagebox.showerror("Hata", "Lütfen fatura/teklif için tüm gerekli alanları doldurun.")
            return

        try:
            toplam_tutar = float(toplam_tutar_str)
            if toplam_tutar < 0:
                messagebox.showerror("Hata", "Toplam tutar negatif olamaz.")
                return
        except ValueError:
            messagebox.showerror("Hata", "Geçersiz toplam tutar değeri. Lütfen sayı giriniz.")
            return

        # Ürün/Hizmetleri JSON'a dönüştür
        urun_hizmetler_list = []
        for line in urun_hizmetler_text.split('\n'):
            parts = [p.strip() for p in line.split(',') if p.strip()]
            if len(parts) == 3:  # Ad, Miktar, Fiyat formatı
                try:
                    quantity = float(parts[1].replace(",", "."))  # Virgülü noktaya çevir
                    price = float(parts[2].replace(",", "."))  # Virgülü noktaya çevir
                    urun_hizmetler_list.append({
                        "ad": parts[0],
                        "miktar": quantity,
                        "birim_fiyat": price,
                        "ara_toplam": quantity * price
                    })
                except ValueError:
                    messagebox.showwarning("Uyarı",
                                           f"Geçersiz ürün/hizmet satırı atlandı: {line}. Format 'Ad,Miktar,Fiyat' olmalı.")
                    continue

        if not urun_hizmetler_list:
            messagebox.showerror("Hata", "Lütfen geçerli ürün/hizmet bilgileri giriniz (Ad,Miktar,Fiyat).")
            return

        urun_hizmetler_json = json.dumps(urun_hizmetler_list, ensure_ascii=False)

        try:
            self.cursor.execute("""
                INSERT INTO fatura_teklifler (tur, musteri_adi, belge_tarihi, son_odeme_gecerlilik_tarihi, urun_hizmetler_json, toplam_tutar, notlar, durum, kullanici_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (tur, musteri_adi, belge_tarihi, son_odeme_gecerlilik_tarihi, urun_hizmetler_json, toplam_tutar,
                  notlar, durum, self.kullanici_id))
            self.conn.commit()
            messagebox.showinfo("Başarılı", f"{tur} başarıyla kaydedildi.")
            self.fatura_temizle()
            self.listele_fatura_teklifler()
        except sqlite3.Error as e:
            messagebox.showerror("Hata", f"{tur} kaydetme hatası: {e}")

    def fatura_guncelle(self):
        if self.selected_invoice_id is None:
            messagebox.showwarning("Uyarı", "Lütfen güncellemek istediğiniz fatura/teklifi seçiniz.")
            return

        tur = self.fatura_tur_var.get()
        musteri_adi = self.fatura_musteri_entry.get().strip()
        belge_tarihi = self.fatura_belge_tarih_entry.get_date().strftime("%Y-%m-%d")
        son_odeme_gecerlilik_tarihi = self.fatura_son_odeme_gecerlilik_tarih_entry.get_date().strftime("%Y-%m-%d")
        urun_hizmetler_text = self.fatura_urun_hizmetler_text.get("1.0", tk.END).strip()
        toplam_tutar_str = self.fatura_toplam_tutar_entry.get().replace(".", "").replace(",", ".").replace("₺",
                                                                                                           "").strip()  # Türk Lirası formatından float'a çevir
        notlar = self.fatura_notlar_text.get("1.0", tk.END).strip()
        durum = self.fatura_durum_var.get()

        if not all([tur, musteri_adi, belge_tarihi, son_odeme_gecerlilik_tarihi, urun_hizmetler_text, toplam_tutar_str,
                    durum]):
            messagebox.showerror("Hata", "Lütfen fatura/teklif için tüm gerekli alanları doldurun.")
            return

        try:
            toplam_tutar = float(toplam_tutar_str)
            if toplam_tutar < 0:
                messagebox.showerror("Hata", "Toplam tutar negatif olamaz.")
                return
        except ValueError:
            messagebox.showerror("Hata", "Geçersiz toplam tutar değeri. Lütfen sayı giriniz.")
            return

        urun_hizmetler_list = []
        for line in urun_hizmetler_text.split('\n'):
            parts = [p.strip() for p in line.split(',') if p.strip()]
            if len(parts) == 3:
                try:
                    urun_hizmetler_list.append({
                        "ad": parts[0],
                        "miktar": float(parts[1].replace(",", ".")),  # Virgülü noktaya çevir
                        "birim_fiyat": float(parts[2].replace(",", ".")),  # Virgülü noktaya çevir
                        "ara_toplam": float(parts[1].replace(",", ".")) * float(parts[2].replace(",", "."))
                    })
                except ValueError:
                    messagebox.showwarning("Uyarı",
                                           f"Geçersiz ürün/hizmet satırı atlandı: {line}. Format 'Ad,Miktar,Fiyat' olmalı.")
                    continue

        if not urun_hizmetler_list:
            messagebox.showerror("Hata", "Lütfen geçerli ürün/hizmet bilgileri giriniz (Ad,Miktar,Fiyat).")
            return

        urun_hizmetler_json = json.dumps(urun_hizmetler_list, ensure_ascii=False)

        try:
            self.cursor.execute("""
                UPDATE fatura_teklifler SET tur = ?, musteri_adi = ?, belge_tarihi = ?, son_odeme_gecerlilik_tarihi = ?, urun_hizmetler_json = ?, toplam_tutar = ?, notlar = ?, durum = ?
                WHERE id = ? AND kullanici_id = ?
            """, (tur, musteri_adi, belge_tarihi, son_odeme_gecerlilik_tarihi, urun_hizmetler_json, toplam_tutar,
                  notlar, durum, self.selected_invoice_id, self.kullanici_id))
            self.conn.commit()
            messagebox.showinfo("Başarılı", f"{tur} başarıyla güncellendi.")
            self.fatura_temizle()
            self.listele_fatura_teklifler()
        except sqlite3.Error as e:
            messagebox.showerror("Hata", f"{tur} güncelleme hatası: {e}")

    def fatura_sil(self):
        if self.selected_invoice_id is None:
            messagebox.showwarning("Uyarı", "Lütfen silmek istediğiniz fatura/teklifi seçiniz.")
            return

        onay = messagebox.askyesno("Onay", "Seçili fatura/teklifi silmek istediğinize emin misiniz?")
        if onay:
            try:
                self.cursor.execute("DELETE FROM fatura_teklifler WHERE id = ? AND kullanici_id = ?",
                                    (self.selected_invoice_id, self.kullanici_id))
                self.conn.commit()
                messagebox.showinfo("Başarılı", "Fatura/Teklif başarıyla silindi.")
                self.fatura_temizle()
                self.listele_fatura_teklifler()
            except sqlite3.Error as e:
                messagebox.showerror("Hata", f"Fatura/Teklif silme hatası: {e}")

    def fatura_temizle(self):
        self.fatura_tur_var.set("Fatura")
        self.fatura_musteri_entry.delete(0, tk.END)
        self.fatura_belge_tarih_entry.set_date(datetime.now().strftime("%Y-%m-%d"))
        self.fatura_son_odeme_gecerlilik_tarih_entry.set_date(datetime.now().strftime("%Y-%m-%d"))
        self.fatura_urun_hizmetler_text.delete("1.0", tk.END)
        self.fatura_toplam_tutar_entry.delete(0, tk.END)
        self.fatura_notlar_text.delete("1.0", tk.END)
        self.fatura_durum_var.set("Taslak")
        self.selected_invoice_id = None

    def listele_fatura_teklifler(self):
        for row in self.fatura_liste.get_children():
            self.fatura_liste.delete(row)

        try:
            self.cursor.execute(
                "SELECT id, tur, musteri_adi, toplam_tutar, belge_tarihi, durum FROM fatura_teklifler WHERE kullanici_id = ? ORDER BY belge_tarihi DESC",
                (self.kullanici_id,))
            veriler = self.cursor.fetchall()
            for veri in veriler:
                # Toplam tutarı biçimlendirerek Treeview'e ekle
                formatted_veri = list(veri)
                formatted_veri[3] = f"{veri[3]:,.2f} ₺"
                self.fatura_liste.insert("", tk.END, values=formatted_veri)
        except sqlite3.Error as e:
            messagebox.showerror("Veritabanı Hatası", f"Fatura/Teklif verileri çekilirken hata oluştu: {e}")

    def fatura_liste_secildi(self, event):
        selected_items = self.fatura_liste.selection()
        if selected_items:
            selected_item = selected_items[0]
            values = self.fatura_liste.item(selected_item, "values")
            self.selected_invoice_id = values[0]

            # Veritabanından tam kaydı çek
            self.cursor.execute(
                "SELECT tur, musteri_adi, belge_tarihi, son_odeme_gecerlilik_tarihi, urun_hizmetler_json, toplam_tutar, notlar, durum FROM fatura_teklifler WHERE id = ? AND kullanici_id = ?",
                (self.selected_invoice_id, self.kullanici_id))
            fatura_data = self.cursor.fetchone()

            if fatura_data:
                tur, musteri_adi, belge_tarihi_str, son_odeme_gecerlilik_tarihi_str, urun_hizmetler_json, toplam_tutar, notlar, durum = fatura_data

                self.fatura_tur_var.set(tur)
                self.fatura_musteri_entry.delete(0, tk.END)
                self.fatura_musteri_entry.insert(0, musteri_adi)

                try:
                    self.fatura_belge_tarih_entry.set_date(datetime.strptime(belge_tarihi_str, "%Y-%m-%d").date())
                    self.fatura_son_odeme_gecerlilik_tarih_entry.set_date(
                        datetime.strptime(son_odeme_gecerlilik_tarihi_str, "%Y-%m-%d").date())
                except ValueError:
                    self.fatura_belge_tarih_entry.set_date(datetime.now().date())
                    self.fatura_son_odeme_gecerlilik_tarih_entry.set_date(datetime.now().date())

                # Ürün/Hizmetleri JSON'dan Text Widget'a dönüştür
                urun_hizmetler_list = json.loads(urun_hizmetler_json)
                urun_hizmetler_text_content = ""
                for item in urun_hizmetler_list:
                    # miktar ve birim_fiyat'ı tam sayı veya float olarak tuttuğumuz için string'e çevirirken formatlama yapalım
                    miktar = item.get('miktar', 0)
                    birim_fiyat = item.get('birim_fiyat', 0)
                    # Float'ı string'e çevirirken virgülü noktaya çevirmiştik, burada tekrar normal okunuşuna çevirelim
                    if isinstance(miktar, (int, float)):
                        miktar = f"{miktar}".replace(".", ",")  # Ondalık kısım 0 ise gösterme (örn: 1.0 -> 1)
                    if isinstance(birim_fiyat, (int, float)):
                        birim_fiyat = f"{birim_fiyat}".replace(".", ",")

                    urun_hizmetler_text_content += f"{item.get('ad', '')},{miktar},{birim_fiyat}\n"

                self.fatura_urun_hizmetler_text.delete("1.0", tk.END)
                self.fatura_urun_hizmetler_text.insert("1.0", urun_hizmetler_text_content.strip())

                self.fatura_toplam_tutar_entry.delete(0, tk.END)
                self.fatura_toplam_tutar_entry.insert(0, f"{toplam_tutar:,.2f}")
                self.fatura_notlar_text.delete("1.0", tk.END)
                self.fatura_notlar_text.insert("1.0", notlar)
                self.fatura_durum_var.set(durum)
        else:
            self.selected_invoice_id = None
            self.fatura_temizle()

    def fatura_pdf_olustur(self):
        if self.selected_invoice_id is None:
            messagebox.showwarning("Uyarı", "Lütfen PDF'ini oluşturmak istediğiniz fatura/teklifi seçiniz.")
            return

        self.cursor.execute("SELECT * FROM fatura_teklifler WHERE id = ? AND kullanici_id = ?",
                            (self.selected_invoice_id, self.kullanici_id))
        fatura_data = self.cursor.fetchone()

        if not fatura_data:
            messagebox.showerror("Hata", "Seçilen fatura/teklif bulunamadı.")
            return

        (id, tur, musteri_adi, belge_tarihi_str, son_odeme_gecerlilik_tarihi_str, urun_hizmetler_json, toplam_tutar,
         notlar, durum, kullanici_id) = fatura_data

        file_path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF Dosyaları", "*.pdf")],
            title=f"{tur} Kaydet"
        )
        if not file_path:
            return

        try:
            doc = SimpleDocTemplate(file_path, pagesize=letter)
            styles = getSampleStyleSheet()

            # Ana Metin Stilleri (font_name kullanılarak)
            normal_style = ParagraphStyle(
                'NormalStyle',
                parent=styles['Normal'],
                fontName=self.font_name,  # GLOBAL_REPORTLAB_FONT_NAME kullanıldı
                fontSize=10,
                leading=12
            )
            bold_style = ParagraphStyle(
                'BoldStyle',
                parent=normal_style,
                fontName=self.font_name + '-Bold' if self.font_name != "Helvetica" else "Helvetica-Bold",
                # Bold font kullanmak için
                fontSize=10,
                leading=12,
            )
            heading_style = ParagraphStyle(
                'HeadingStyle',
                parent=styles['h2'],
                fontName=self.font_name,  # GLOBAL_REPORTLAB_FONT_NAME kullanıldı
                fontSize=16,
                spaceAfter=12,
                alignment=TA_CENTER
            )
            sub_heading_style = ParagraphStyle(
                'SubHeadingStyle',
                parent=styles['h3'],
                fontName=self.font_name,  # GLOBAL_REPORTLAB_FONT_NAME kullanıldı
                fontSize=12,
                spaceAfter=8,
                alignment=TA_LEFT
            )

            elements = []

            # 1. Başlık
            elements.append(Paragraph(f"{tur} / Teklif Belgesi", heading_style))
            elements.append(Spacer(1, 0.2 * 10 * 6))

            # 2. Şirket Bilgileri (Sabit Metin)
            elements.append(Paragraph("<b>Sirket Adı:</b> Fingo Finansal Hizmetler", normal_style))
            elements.append(
                Paragraph("<b>Adres:</b> TopBeyaz Mahallesi, ATATURK Caddesi No: 123, Eskisehir, Turkiye", normal_style))
            elements.append(Paragraph("<b>Telefon:</b> +90 5XX XXX XX XX", normal_style))
            elements.append(Paragraph("<b>E-posta:</b> yasarsamdanli1@gmail.com", normal_style))
            elements.append(Spacer(1, 0.2 * 10 * 6))

            # 3. Belge Bilgileri ve Müşteri Bilgileri
            belge_bilgi_data = [
                [Paragraph(f"<b>{tur} No:</b> {id}", bold_style),
                 Paragraph(f"<b>Muşteri Adı:</b> {musteri_adi}", bold_style)],
                [Paragraph(f"<b>Belge Tarihi:</b> {belge_tarihi_str}", normal_style), Paragraph("", normal_style)],
                [Paragraph(
                    f"<b>{'Son Odeme Tarihi' if tur == 'Fatura' else 'Gecerlilik Tarihi'}:</b> {son_odeme_gecerlilik_tarihi_str}",
                    normal_style), Paragraph("", normal_style)],
                [Paragraph(f"<b>Durum:</b> {durum}", normal_style), Paragraph("", normal_style)],
            ]

            belge_bilgi_table = Table(belge_bilgi_data, colWidths=[letter[0] / 2, letter[0] / 2])
            belge_bilgi_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING', (0, 0), (-1, -1), 0),
                ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ('TOPPADDING', (0, 0), (-1, -1), 0),
            ]))
            elements.append(belge_bilgi_table)
            elements.append(Spacer(1, 0.2 * 10 * 6))

            # 4. Ürün/Hizmet Tablosu
            elements.append(Paragraph("<b>Urunler / Hizmetler</b>", sub_heading_style))
            elements.append(Spacer(1, 0.1 * 10 * 6))

            urun_hizmetler_data = [
                [
                    Paragraph("<b>Acıklama</b>", bold_style),
                    Paragraph("<b>Miktar</b>", bold_style),
                    Paragraph("<b>Birim Fiyat (₺)</b>", bold_style),
                    Paragraph("<b>Ara Toplam (₺)</b>", bold_style)
                ]
            ]

            parsed_items = json.loads(urun_hizmetler_json)
            for item in parsed_items:
                urun_hizmetler_data.append([
                    Paragraph(item.get('ad', ''), normal_style),
                    Paragraph(f"{item.get('miktar', 0):g}".replace(".", ","), normal_style),
                    # Miktarı Türkçeye uygun formatla
                    Paragraph(f"{item.get('birim_fiyat', 0):,.2f}".replace(".", ","), normal_style),
                    # Birim fiyatı Türkçeye uygun formatla
                    Paragraph(f"{item.get('ara_toplam', 0):,.2f}".replace(".", ","), normal_style)
                    # Ara toplamı Türkçeye uygun formatla
                ])

            urun_hizmet_table_style = TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#D0D0D0")),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('FONTNAME', (0, 0), (-1, 0), self.font_name),  # Başlık fontu
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor("#F5F5F5")),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('LEFTPADDING', (0, 0), (-1, -1), 4),
                ('RIGHTPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('FONTNAME', (0, 1), (-1, -1), self.font_name),  # Hücre fontu
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),  # Miktar, Birim Fiyat, Ara Toplam sağa hizalı
            ])

            col_widths_urun = [0.4 * letter[0], 0.15 * letter[0], 0.2 * letter[0], 0.25 * letter[0]]

            urun_hizmet_table = Table(urun_hizmetler_data, colWidths=col_widths_urun)
            urun_hizmet_table.setStyle(urun_hizmet_table_style)
            elements.append(urun_hizmet_table)
            elements.append(Spacer(1, 0.2 * 10 * 6))

            # 5. Toplam Tutar
            elements.append(
                Paragraph(f"<b>Toplam Tutar:</b> <font color='blue'>₺{toplam_tutar:,.2f}".replace(".", ",") + "</font>",
                          bold_style))
            elements.append(Spacer(1, 0.2 * 10 * 6))

            # 6. Notlar
            if notlar:
                elements.append(Paragraph("<b>Notlar:</b>", sub_heading_style))
                elements.append(Paragraph(notlar, normal_style))

            doc.build(elements)
            messagebox.showinfo("Başarılı", f"{tur} PDF'i başarıyla kaydedildi:\n{file_path}")
        except Exception as e:
            messagebox.showerror("Hata",
                                 f"PDF raporu oluşturulurken hata oluştu: {e}\nPDF kütüphanesi Türkçe karakter desteği için ek font ayarları gerektirebilir. Lütfen '{GLOBAL_FONT_FILE_NAME}' dosyasının uygulamanızın bulunduğu dizinde olduğundan emin olun.")


# --- Ana Başlatma Bloğu ---
if __name__ == "__main__":
    root = tk.Tk()
    app = LoginRegisterApp(root)
    root.mainloop()

