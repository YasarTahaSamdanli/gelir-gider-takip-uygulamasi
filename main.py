import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from tkcalendar import DateEntry

# Matplotlib için Türkçe font ayarı (isteğe bağlı, sistemde yüklü bir font olmalı)
plt.rcParams['font.sans-serif'] = ['Arial', 'DejaVu Sans']  # İlk yüklü olanı kullanır
plt.rcParams['axes.unicode_minus'] = False  # Eksi işaretinin doğru görünmesi için


class GelirGiderUygulamasi:
    def __init__(self, root):
        self.root = root
        self.root.title("Gelişmiş Gelir Gider Takibi")
        self.root.geometry("1200x800")  # Pencere boyutunu tekrarlayan işlemler için büyüttük
        self.root.configure(bg="#f5f5f5")

        # Seçili öğenin ID'sini tutmak için değişkenler
        self.selected_item_id = None  # Ana işlemler listesi için
        self.selected_recurring_item_id = None  # Tekrarlayan işlemler listesi için

        # Veritabanı bağlantısı ve tablo oluşturma
        self.baglanti_olustur()

        # Arayüz bileşenleri
        self.arayuz_olustur()

        # Başlangıç verilerini yükle
        self.listele()
        self.listele_tekrar_eden_islemler()  # Tekrarlayan işlemleri listele

        # Uygulama başladığında tekrarlayan işlemleri kontrol et ve oluştur
        self.uretim_kontrolu()

    def baglanti_olustur(self):
        """SQLite veritabanı bağlantısını kurar ve 'islemler' ile 'tekrar_eden_islemler' tablolarını oluşturur."""
        try:
            self.conn = sqlite3.connect("veriler.db")
            self.cursor = self.conn.cursor()

            # Ana işlemler tablosu
            self.cursor.execute("""
                                CREATE TABLE IF NOT EXISTS islemler
                                (
                                    id
                                    INTEGER
                                    PRIMARY
                                    KEY
                                    AUTOINCREMENT,
                                    tur
                                    TEXT
                                    NOT
                                    NULL,
                                    miktar
                                    REAL
                                    NOT
                                    NULL,
                                    kategori
                                    TEXT,
                                    aciklama
                                    TEXT,
                                    tarih
                                    TEXT
                                    NOT
                                    NULL
                                )
                                """)

            # Tekrarlayan işlemler tablosu
            # DİKKAT: 'baslangic_tarihi' ve 'son_uretilen_tarih' sütun adları tutarlı olmalı!
            self.cursor.execute("""
                                CREATE TABLE IF NOT EXISTS tekrar_eden_islemler
                                (
                                    id
                                    INTEGER
                                    PRIMARY
                                    KEY
                                    AUTOINCREMENT,
                                    tur
                                    TEXT
                                    NOT
                                    NULL,
                                    miktar
                                    REAL
                                    NOT
                                    NULL,
                                    kategori
                                    TEXT,
                                    aciklama
                                    TEXT,
                                    baslangic_tarihi
                                    TEXT
                                    NOT
                                    NULL, -- Bu isim tablodaki sütun adıdır
                                    siklilik
                                    TEXT
                                    NOT
                                    NULL, -- Günlük, Haftalık, Aylık, Yıllık
                                    son_uretilen_tarih
                                    TEXT  -- Son olarak üretilen işlemin tarihi
                                )
                                """)
            self.conn.commit()
        except sqlite3.Error as e:
            messagebox.showerror("Veritabanı Hatası",
                                 f"Veritabanı bağlantısı kurulamadı veya tablo oluşturulamadı: {e}")
            self.root.destroy()  # Uygulamayı kapat

    def arayuz_olustur(self):
        """Uygulamanın kullanıcı arayüzünü (UI) oluşturur."""
        # Stil ayarları
        stil = ttk.Style()
        stil.theme_use("clam")  # Daha modern bir tema
        stil.configure("TFrame", background="#f5f5f5")
        stil.configure("TLabel", background="#f5f5f5", font=("Arial", 10))
        stil.configure("TButton", font=("Arial", 10, "bold"), padding=6, background="#e0e0e0")
        stil.map("TButton", background=[('active', '#c0c0c0')])
        stil.configure("Treeview", font=("Arial", 10), rowheight=25)
        stil.configure("Treeview.Heading", font=("Arial", 10, "bold"), background="#d0d0d0")
        stil.map("Treeview.Heading", background=[('active', '#b0b0b0')])
        stil.configure("TLabelframe", background="#f5f5f5", bordercolor="#d0d0d0", relief="solid")
        stil.configure("TLabelframe.Label", font=("Arial", 12, "bold"), foreground="#333333")

        # Ana içerik frame'i (sol ve sağ panelleri ayırmak için)
        main_frame = ttk.Frame(self.root)
        main_frame.pack(pady=10, padx=20, fill="both", expand=True)

        # Sol Panel (Giriş, Filtreleme, Özet)
        left_panel = ttk.Frame(main_frame)
        left_panel.pack(side="left", fill="both", expand=True, padx=(0, 10))

        # Sağ Panel (Tekrarlayan İşlemler)
        right_panel = ttk.Frame(main_frame)
        right_panel.pack(side="right", fill="both", expand=True, padx=(10, 0))

        # Başlık
        baslik_frame = ttk.Frame(left_panel, padding="10 10 10 10")
        baslik_frame.pack(pady=10, fill="x", padx=0)  # Sol panele göre ayarladık
        ttk.Label(baslik_frame, text="Gelişmiş Gelir - Gider Takip Uygulaması",
                  font=("Arial", 18, "bold"), foreground="#0056b3").pack()

        # Giriş Paneli (Sol Panelde)
        giris_frame = ttk.LabelFrame(left_panel, text="Yeni İşlem Ekle / Düzenle", padding=15)
        giris_frame.pack(pady=10, padx=0, fill="x")

        # Giriş bileşenleri ve etiketleri
        input_widgets = [
            ("İşlem Türü:", "tur_var", ["Gelir", "Gider"], "Combobox"),
            ("Miktar (₺):", "miktar_entry", None, "Entry"),
            ("Kategori:", "kategori_var", ["Maaş", "Yatırım", "Hediye", "Diğer",
                                           "Fatura", "Gıda", "Ulaşım", "Eğlence", "Sağlık", "Eğitim", "Giyim"],
             "Combobox"),
            ("Açıklama:", "aciklama_entry", None, "Entry"),
            ("Tarih:", "tarih_entry", None, "DateEntry")
        ]

        for i, (label_text, var_name, values, widget_type) in enumerate(input_widgets):
            ttk.Label(giris_frame, text=label_text).grid(row=i, column=0, sticky="w", padx=10, pady=5)

            if widget_type == "Combobox":
                var = tk.StringVar()
                cb = ttk.Combobox(giris_frame, textvariable=var, values=values, state="readonly", width=30)
                cb.grid(row=i, column=1, padx=10, pady=5, sticky="ew")
                cb.set(values[0] if values else "")
                setattr(self, var_name, var)
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

        # Butonlar
        buton_frame = ttk.Frame(giris_frame, padding="10 0 0 0")
        buton_frame.grid(row=len(input_widgets), column=0, columnspan=2, pady=10, sticky="ew")

        ttk.Button(buton_frame, text="Kaydet", command=self.kaydet).pack(side="left", padx=5, fill="x", expand=True)
        ttk.Button(buton_frame, text="Güncelle", command=self.guncelle).pack(side="left", padx=5, fill="x", expand=True)
        ttk.Button(buton_frame, text="Temizle", command=self.temizle).pack(side="left", padx=5, fill="x", expand=True)
        ttk.Button(buton_frame, text="Sil", command=self.sil).pack(side="left", padx=5, fill="x", expand=True)
        ttk.Button(buton_frame, text="Grafik Göster", command=self.grafik_goster).pack(side="left", padx=5, fill="x",
                                                                                       expand=True)

        # Filtreleme Paneli (Sol Panelde)
        filtre_frame = ttk.LabelFrame(left_panel, text="Filtreleme ve Arama", padding=15)
        filtre_frame.pack(pady=10, padx=0, fill="x")

        ttk.Label(filtre_frame, text="Tür:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.filtre_tur_var = tk.StringVar(value="Tümü")
        ttk.Combobox(filtre_frame, textvariable=self.filtre_tur_var,
                     values=["Tümü", "Gelir", "Gider"], state="readonly", width=12).grid(row=0, column=1, padx=5,
                                                                                         pady=5, sticky="ew")

        ttk.Label(filtre_frame, text="Kategori:").grid(row=0, column=2, padx=5, pady=5, sticky="w")
        self.filtre_kategori_var = tk.StringVar(value="Tümü")
        ttk.Combobox(filtre_frame, textvariable=self.filtre_kategori_var,
                     values=["Tümü", "Maaş", "Yatırım", "Hediye", "Diğer",
                             "Fatura", "Gıda", "Ulaşım", "Eğlence", "Sağlık", "Eğitim", "Giyim"], width=12).grid(row=0,
                                                                                                                 column=3,
                                                                                                                 padx=5,
                                                                                                                 pady=5,
                                                                                                                 sticky="ew")

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

        # Liste Paneli (Ana İşlemler - Sol Panelde)
        liste_frame = ttk.Frame(left_panel, padding="10 0 0 0")
        liste_frame.pack(pady=10, padx=0, fill="both", expand=True)

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

        # Özet Paneli (Sol Panelde)
        ozet_frame = ttk.LabelFrame(left_panel, text="Özet Bilgiler", padding=15)
        ozet_frame.pack(pady=10, padx=0, fill="x")

        self.toplam_gelir_label = ttk.Label(ozet_frame, text="Toplam Gelir: ₺0.00",
                                            font=("Arial", 11, "bold"), foreground="green")
        self.toplam_gelir_label.pack(side="left", padx=20, fill="x", expand=True)

        self.toplam_gider_label = ttk.Label(ozet_frame, text="Toplam Gider: ₺0.00",
                                            font=("Arial", 11, "bold"), foreground="red")
        self.toplam_gider_label.pack(side="left", padx=20, fill="x", expand=True)

        self.bakiye_label = ttk.Label(ozet_frame, text="Bakiye: ₺0.00",
                                      font=("Arial", 11, "bold"))
        self.bakiye_label.pack(side="left", padx=20, fill="x", expand=True)

        # --- Tekrarlayan İşlemler Paneli (Sağ Panelde) ---
        tekrar_eden_frame = ttk.LabelFrame(right_panel, text="Tekrarlayan İşlemler Tanımla", padding=15)
        tekrar_eden_frame.pack(pady=10, padx=0, fill="x")

        # Tekrarlayan İşlem Giriş Alanları
        recurring_input_widgets = [
            ("İşlem Türü:", "tur_tekrar_var", ["Gelir", "Gider"], "Combobox"),
            ("Miktar (₺):", "miktar_tekrar_entry", None, "Entry"),
            ("Kategori:", "kategori_tekrar_var", ["Maaş", "Yatırım", "Hediye", "Diğer",
                                                  "Fatura", "Gıda", "Ulaşım", "Eğlence", "Sağlık", "Eğitim", "Giyim"],
             "Combobox"),
            ("Açıklama:", "aciklama_tekrar_entry", None, "Entry"),
            ("Başlangıç Tarihi:", "baslangic_tarih_tekrar_entry", None, "DateEntry"),
            ("Sıklık:", "siklilik_var", ["Günlük", "Haftalık", "Aylık", "Yıllık"], "Combobox")
        ]

        for i, (label_text, var_name, values, widget_type) in enumerate(recurring_input_widgets):
            ttk.Label(tekrar_eden_frame, text=label_text).grid(row=i, column=0, sticky="w", padx=10, pady=5)

            if widget_type == "Combobox":
                var = tk.StringVar()
                cb = ttk.Combobox(tekrar_eden_frame, textvariable=var, values=values, state="readonly", width=30)
                cb.grid(row=i, column=1, padx=10, pady=5, sticky="ew")
                cb.set(values[0] if values else "")
                setattr(self, var_name, var)
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

        # Tekrarlayan İşlem Butonları
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

        # Tekrarlayan İşlemler Listesi (Sağ Panelde)
        tekrar_eden_liste_frame = ttk.Frame(right_panel, padding="10 0 0 0")
        tekrar_eden_liste_frame.pack(pady=10, padx=0, fill="both", expand=True)

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

    # --- Ana İşlem Fonksiyonları ---
    def kaydet(self):
        """Yeni bir gelir veya gider işlemini veritabanına kaydeder."""
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

        if not tarih:
            messagebox.showerror("Hata", "Lütfen geçerli bir tarih seçiniz.")
            return

        try:
            self.cursor.execute("""
                                INSERT INTO islemler (tur, miktar, kategori, aciklama, tarih)
                                VALUES (?, ?, ?, ?, ?)
                                """, (tur, miktar, kategori, aciklama, tarih))
            self.conn.commit()

            messagebox.showinfo("Başarılı", "İşlem başarıyla kaydedildi.")
            self.temizle()
            self.listele()
        except sqlite3.Error as e:
            messagebox.showerror("Hata", f"Veritabanına kaydetme hatası: {e}")

    def guncelle(self):
        """Seçili gelir veya gider işlemini veritabanında günceller."""
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

        if not tarih:
            messagebox.showerror("Hata", "Lütfen geçerli bir tarih seçiniz.")
            return

        try:
            self.cursor.execute("""
                                UPDATE islemler
                                SET tur      = ?,
                                    miktar   = ?,
                                    kategori = ?,
                                    aciklama = ?,
                                    tarih    = ?
                                WHERE id = ?
                                """, (tur, miktar, kategori, aciklama, tarih, self.selected_item_id))
            self.conn.commit()
            messagebox.showinfo("Başarılı", "Kayıt başarıyla güncellendi.")
            self.temizle()
            self.listele()
        except sqlite3.Error as e:
            messagebox.showerror("Hata", f"Veritabanı güncelleme hatası: {e}")

    def listele(self, event=None):
        """Veritabanındaki işlemleri filtreleyerek Treeview'da listeler ve özeti günceller."""
        for row in self.liste.get_children():
            self.liste.delete(row)

        tur = self.filtre_tur_var.get()
        kategori = self.filtre_kategori_var.get()

        # Tarih alanlarının boş olup olmadığını kontrol et ve DateEntry'den doğru tarih formatını al
        bas_tarih = self.bas_tarih_entry.get_date().strftime("%Y-%m-%d") if self.bas_tarih_entry.get() else ""
        bit_tarih = self.bit_tarih_entry.get_date().strftime("%Y-%m-%d") if self.bit_tarih_entry.get() else ""
        arama_terimi = self.arama_entry.get().strip()

        sql = "SELECT id, tur, miktar, kategori, aciklama, tarih FROM islemler WHERE 1=1"
        params = []

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
        """Ana işlem Treeview'da bir öğe seçildiğinde giriş alanlarını doldurur."""
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
        """Ana işlem giriş alanlarını varsayılan değerlere sıfırlar."""
        self.tur_var.set("Gelir")
        self.miktar_entry.delete(0, tk.END)
        self.kategori_var.set("Diğer")
        self.aciklama_entry.delete(0, tk.END)
        self.tarih_entry.set_date(datetime.now().date())
        self.selected_item_id = None

    def sil(self):
        """Seçili ana kaydı veritabanından siler."""
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
                self.cursor.execute("DELETE FROM islemler WHERE id = ?", (record_id,))
                self.conn.commit()
                messagebox.showinfo("Başarılı", "Kayıt başarıyla silindi.")
                self.listele()
                self.temizle()
            except sqlite3.Error as e:
                messagebox.showerror("Hata", f"Kayıt silme hatası: {e}")

    def grafik_goster(self):
        """Kategorilere göre gelir/gider dağılımını ve zaman içindeki bakiye değişimini gösterir."""
        self.cursor.execute("""
                            SELECT tur, kategori, SUM(miktar)
                            FROM islemler
                            GROUP BY tur, kategori
                            """)
        kategori_verileri = self.cursor.fetchall()

        self.cursor.execute("""
                            SELECT tarih, tur, miktar
                            FROM islemler
                            ORDER BY tarih ASC
                            """)
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
        """Yeni bir tekrarlayan işlemi veritabanına kaydeder."""
        tur = self.tur_tekrar_var.get()
        miktar_str = self.miktar_tekrar_entry.get()
        kategori = self.kategori_tekrar_var.get()
        aciklama = self.aciklama_tekrar_entry.get()
        # DEĞİŞİKLİK: DateEntry'den gelen tarih değişkeni 'baslangic_tarih_degeri' olarak adlandırıldı
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

        if not baslangic_tarih_degeri:  # Tarih boş kontrolü
            messagebox.showerror("Hata", "Lütfen geçerli bir başlangıç tarihi seçiniz.")
            return

        try:
            self.cursor.execute("""
                                INSERT INTO tekrar_eden_islemler (tur, miktar, kategori, aciklama, baslangic_tarihi,
                                                                  siklilik, son_uretilen_tarih)
                                VALUES (?, ?, ?, ?, ?, ?, ?)
                                """, (tur, miktar, kategori, aciklama, baslangic_tarih_degeri, siklilik,
                                      baslangic_tarih_degeri))
            self.conn.commit()

            messagebox.showinfo("Başarılı", "Tekrarlayan işlem başarıyla kaydedildi.")
            self.temizle_tekrar_eden()
            self.listele_tekrar_eden_islemler()
            self.uretim_kontrolu()
        except sqlite3.Error as e:
            messagebox.showerror("Hata", f"Tekrarlayan işlem kaydetme hatası: {e}")

    def sil_tekrar_eden(self):
        """Seçili tekrarlayan işlemi veritabanından siler."""
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
                self.cursor.execute("DELETE FROM tekrar_eden_islemler WHERE id = ?", (record_id,))
                self.conn.commit()
                messagebox.showinfo("Başarılı", "Tekrarlayan kayıt başarıyla silindi.")
                self.listele_tekrar_eden_islemler()
                self.temizle_tekrar_eden()
            except sqlite3.Error as e:
                messagebox.showerror("Hata", f"Tekrarlayan kayıt silme hatası: {e}")

    def listele_tekrar_eden_islemler(self):
        """Veritabanındaki tekrarlayan işlemleri Treeview'da listeler."""
        for row in self.tekrar_eden_liste.get_children():
            self.tekrar_eden_liste.delete(row)

        try:
            self.cursor.execute(
                "SELECT id, tur, miktar, kategori, aciklama, baslangic_tarihi, siklilik, son_uretilen_tarih FROM tekrar_eden_islemler ORDER BY baslangic_tarihi DESC")
            veriler = self.cursor.fetchall()
            for veri in veriler:
                self.tekrar_eden_liste.insert("", tk.END, values=veri)
        except sqlite3.Error as e:
            messagebox.showerror("Veritabanı Hatası", f"Tekrarlayan veri çekme hatası: {e}")

    def tekrar_eden_liste_secildi(self, event):
        """Tekrarlayan işlemler Treeview'da bir öğe seçildiğinde giriş alanlarını doldurur."""
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
                # DEĞİŞİKLİK: baslangic_tarihi sütunundan gelen değer kullanılacak
                date_obj = datetime.strptime(values[5], "%Y-%m-%d").date()
                self.baslangic_tarih_tekrar_entry.set_date(date_obj)
            except ValueError:
                self.baslangic_tarih_tekrar_entry.set_date(datetime.now().date())
            self.siklilik_var.set(values[6])
        else:
            self.selected_recurring_item_id = None
            self.temizle_tekrar_eden()

    def temizle_tekrar_eden(self):
        """Tekrarlayan işlem giriş alanlarını varsayılan değerlere sıfırlar."""
        self.tur_tekrar_var.set("Gelir")
        self.miktar_tekrar_entry.delete(0, tk.END)
        self.kategori_tekrar_var.set("Diğer")
        self.aciklama_tekrar_entry.delete(0, tk.END)
        self.baslangic_tarih_tekrar_entry.set_date(datetime.now().date())
        self.siklilik_var.set("Aylık")  # Varsayılan olarak aylık
        self.selected_recurring_item_id = None

    def uretim_kontrolu(self):
        """
        Tekrarlayan işlemleri kontrol eder ve vadesi gelenleri ana işlemlere ekler.
        Uygulama başlatıldığında veya tekrarlayan işlem eklendiğinde/silindiğinde çağrılır.
        """
        bugun = datetime.now().date()
        uretilen_islem_sayisi = 0
        uretilen_mesajlar = []

        try:
            self.cursor.execute(
                "SELECT id, tur, miktar, kategori, aciklama, baslangic_tarihi, siklilik, son_uretilen_tarih FROM tekrar_eden_islemler")
            tekrar_eden_kayitlar = self.cursor.fetchall()

            for kayit in tekrar_eden_kayitlar:
                (rec_id, tur, miktar, kategori, aciklama, baslangic_tarih_str, siklilik, son_uretilen_tarih_str) = kayit

                baslangic_tarih = datetime.strptime(baslangic_tarih_str, "%Y-%m-%d").date()
                son_uretilen_tarih = datetime.strptime(son_uretilen_tarih_str, "%Y-%m-%d").date()

                next_due_date = son_uretilen_tarih  # Başlangıçta son üretilen tarih

                # Eğer başlangıç tarihi son üretilen tarihten daha yeniyse, başlangıç tarihinden itibaren kontrol et
                # Veya hiç üretilmemişse (son_uretilen_tarih başlangıç tarihi olarak ayarlanmışsa) başlangıç tarihinden başla
                if baslangic_tarih > son_uretilen_tarih:
                    next_due_date = baslangic_tarih

                # Tekrarlayan döngü: Bugün veya geçmişte kalan tüm vadesi gelen işlemleri üret
                while next_due_date <= bugun:
                    if next_due_date > son_uretilen_tarih:  # Sadece yeni üretilecekleri ele al
                        try:
                            self.cursor.execute("""
                                                INSERT INTO islemler (tur, miktar, kategori, aciklama, tarih)
                                                VALUES (?, ?, ?, ?, ?)
                                                """,
                                                (tur, miktar, kategori, aciklama, next_due_date.strftime("%Y-%m-%d")))
                            self.conn.commit()
                            uretilen_islem_sayisi += 1
                            uretilen_mesajlar.append(
                                f"{tur} - {miktar:,.2f}₺ ({kategori}) tarihinde: {next_due_date.strftime('%Y-%m-%d')}")
                        except sqlite3.Error as e:
                            print(f"Hata: Tekrarlayan işlem üretilemedi ({rec_id}): {e}")  # Konsola hata bas
                            break  # Hata olursa bu kaydın döngüsünü durdur

                    # Son üretilen tarihi güncelle
                    # Her döngüde son_uretilen_tarih'i güncelleyerek bir sonraki kontrol noktasını belirliyoruz
                    self.cursor.execute("UPDATE tekrar_eden_islemler SET son_uretilen_tarih = ? WHERE id = ?",
                                        (next_due_date.strftime("%Y-%m-%d"), rec_id))
                    self.conn.commit()

                    # Bir sonraki vade tarihini hesapla
                    if siklilik == "Günlük":
                        next_due_date += timedelta(days=1)
                    elif siklilik == "Haftalık":
                        next_due_date += timedelta(weeks=1)
                    elif siklilik == "Aylık":
                        # Ay sonunu doğru işlemek için özel mantık
                        gun = next_due_date.day
                        ay = next_due_date.month + 1
                        yil = next_due_date.year
                        if ay > 12:
                            ay = 1
                            yil += 1
                        try:
                            next_due_date = next_due_date.replace(year=yil, month=ay)
                        except ValueError:
                            # Ayın son günü yoksa (örn. 31 Şubat veya 31 Nisan)
                            # Bir sonraki ayın ilk gününe git ve bir gün çıkar (o ayın son günü)
                            next_due_date = datetime(yil, ay, 1).date() - timedelta(days=1)
                    elif siklilik == "Yıllık":
                        next_due_date = next_due_date.replace(year=next_due_date.year + 1)
                    else:
                        break  # Bilinmeyen sıklık, döngüyü kır

        except sqlite3.Error as e:
            messagebox.showerror("Veritabanı Hatası", f"Tekrarlayan işlemler kontrol edilirken hata oluştu: {e}")

        if uretilen_islem_sayisi > 0:
            mesaj = f"Bugün {uretilen_islem_sayisi} adet tekrarlayan işlem otomatik olarak oluşturuldu:\n\n"
            mesaj += "\n".join(uretilen_mesajlar[:10])  # İlk 10 işlemi göster
            if uretilen_islem_sayisi > 10:
                mesaj += "\n..."
            messagebox.showinfo("Tekrarlayan İşlem Bildirimi", mesaj)
            self.listele()  # Ana listeyi güncelle

    def __del__(self):
        """Uygulama kapatıldığında veritabanı bağlantısını kapatır."""
        if hasattr(self, 'conn') and self.conn:
            self.conn.close()


if __name__ == "__main__":
    root = tk.Tk()
    app = GelirGiderUygulamasi(root)
    root.mainloop()
