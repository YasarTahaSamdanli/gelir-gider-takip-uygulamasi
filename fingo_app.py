# fingo_app.py
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sqlite3
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from tkcalendar import DateEntry
import json
import os
import sys

# Gerekli modüllerin import edilmesi
from database_manager import DatabaseManager  # Veritabanı işlemlerini yönetir
from pdf_generator import PDFGenerator, GLOBAL_REPORTLAB_FONT_NAME  # PDF oluşturma ve global font adı
from ai_predictor import AIPredictor  # Yapay zeka kategori tahmincisini yönetir

# Matplotlib için Türkçe font ayarı
# Bu ayar, grafiklerde Türkçe karakterlerin düzgün görünmesini sağlar.
# 'Arial' fontu bulunamazsa 'DejaVu Sans' gibi genel bir fonta düşer.
plt.rcParams['font.sans-serif'] = ['Arial', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False  # Eksi işaretinin doğru görünmesi için


class GelirGiderUygulamasi:
    def __init__(self, root, db_manager, kullanici_id, username):
        """
        Gelir Gider Uygulamasının ana arayüzünü ve iş mantığını başlatır.

        Args:
            root (tk.Tk): Ana Tkinter penceresi.
            db_manager (DatabaseManager): Veritabanı yöneticisi örneği, tüm DB işlemlerini bu obje üzerinden yaparız.
            kullanici_id (int): Giriş yapan kullanıcının ID'si, verilere erişim için kullanılır.
            username (str): Giriş yapan kullanıcının adı, arayüzde gösterilir.
        """
        self.root = root
        self.db_manager = db_manager  # DatabaseManager örneğini sakla
        # Veritabanı bağlantısı ve imleç (cursor) artık db_manager üzerinden erişilebilir olacak.
        self.conn = self.db_manager.conn
        self.cursor = self.db_manager.cursor
        self.kullanici_id = kullanici_id
        self.username = username

        # Seçili öğelerin ID'lerini saklamak için değişkenler
        self.selected_item_id = None  # Ana işlemler listesinden seçilen öğe
        self.selected_recurring_item_id = None  # Tekrarlayan işlemler listesinden seçilen öğe
        self.selected_category_id = None  # Kategori listesinden seçilen öğe
        self.selected_invoice_id = None  # Fatura/Teklif listesinden seçilen öğe
        self.selected_customer_id = None  # Müşteri listesinden seçilen öğe
        self.selected_product_id = None  # Ürün listesinden seçilen öğe

        # PDF oluşturucu örneğini başlatırken global font adını ilet
        self.pdf_generator = PDFGenerator(font_name=GLOBAL_REPORTLAB_FONT_NAME)

        # Yapay zeka tahmincisini başlatırken db_manager ve user_id'yi ilet.
        # Bu sayede AI modeli kullanıcının kendi verileriyle eğitilebilir.
        self.ai_predictor = AIPredictor(db_manager=self.db_manager, user_id=self.kullanici_id)

        # Uygulamanın ana arayüzünü oluştur
        self.arayuz_olustur()

        # Uygulama başlatıldığında ilk listelemeleri ve kontrolleri yap
        self.listele()  # Ana işlemleri listele
        self.listele_tekrar_eden_islemler()  # Tekrarlayan işlemleri listele
        self.kategorileri_yukle()  # Kategorileri yükle (hem combobox'lar hem liste için)
        self.listele_musteriler()  # Müşterileri listele
        self.listele_urunler()  # Ürünleri listele
        self.listele_fatura_teklifler()  # Fatura/Teklifleri listele

        self.uretim_kontrolu()  # Tekrarlayan işlemlerin otomatik üretimini kontrol et

    def arayuz_olustur(self, parent_frame=None):
        """Uygulamanın ana arayüzünü (sekmeler, butonlar vb.) oluşturur."""
        # Tkinter stil ayarları
        stil = ttk.Style()
        stil.theme_use("clam")  # 'clam' teması daha modern bir görünüm sunar
        stil.configure("TFrame", background="#f5f5f5")
        stil.configure("TLabel", background="#f5f5f5", font=("Arial", 10))
        stil.configure("TButton", font=("Arial", 10, "bold"), padding=6, background="#e0e0e0")
        stil.map("TButton", background=[('active', '#c0c0c0')])  # Butona basıldığında renk değişimi
        stil.configure("Treeview", font=("Arial", 10), rowheight=25)
        stil.configure("Treeview.Heading", font=("Arial", 10, "bold"), background="#d0d0d0")
        stil.map("Treeview.Heading", background=[('active', '#b0b0b0')])
        stil.configure("TLabelframe", background="#f5f5f5", bordercolor="#d0d0d0", relief="solid")
        stil.configure("TLabelframe.Label", font=("Arial", 12, "bold"), foreground="#333333")

        # Ana başlık çerçevesi
        baslik_frame = ttk.Frame(self.root, padding="10 10 10 10")
        baslik_frame.pack(pady=0, fill="x", padx=20, side="top")

        # Uygulama başlığı
        ttk.Label(baslik_frame, text="Gelişmiş Gelir - Gider Takip Uygulaması (Fingo)",
                  font=("Arial", 18, "bold"), foreground="#0056b3").pack(side="left")
        # Kullanıcı adı bilgisi
        ttk.Label(baslik_frame, text=f"Kullanıcı: {self.username}",
                  font=("Arial", 10, "italic"), foreground="#555").pack(side="right", padx=10)

        # Ana içerik çerçevesi (sekmeleri barındıracak)
        main_content_frame = ttk.Frame(self.root)
        main_content_frame.pack(pady=10, padx=20, fill="both", expand=True, side="top")

        # Sekmeli Arayüz (Notebook widget'ı) - main_content_frame içine yerleştirilir
        self.notebook = ttk.Notebook(main_content_frame)
        self.notebook.pack(fill="both", expand=True)

        # Her bir sekme için ayrı bir Frame oluştur ve Notebook'a ekle
        self.tab_ana_islemler = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_ana_islemler, text="Ana İşlemler")
        self._ana_islemler_arayuzu_olustur(self.tab_ana_islemler)  # Ana işlemler sekmesinin içeriğini oluştur

        self.tab_gelismis_araclar = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_gelismis_araclar, text="Gelişmiş Araçlar & Raporlar")
        self._gelismis_araclar_arayuzu_olustur(
            self.tab_gelismis_araclar)  # Gelişmiş araçlar sekmesinin içeriğini oluştur

        self.tab_fatura_teklif = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_fatura_teklif, text="Fatura & Teklifler")
        self._fatura_teklif_arayuzu_olustur(self.tab_fatura_teklif)  # Fatura/Teklifler sekmesinin içeriğini oluştur

        self.tab_musteri_yonetimi = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_musteri_yonetimi, text="Müşteri Yönetimi")
        self._musteri_yonetimi_arayuzu_olustur(
            self.tab_musteri_yonetimi)  # Müşteri yönetimi sekmesinin içeriğini oluştur

        self.tab_envanter_yonetimi = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_envanter_yonetimi, text="Envanter Yönetimi")
        self._envanter_yonetimi_arayuzu_olustur(
            self.tab_envanter_yonetimi)  # Envanter yönetimi sekmesinin içeriğini oluştur

        self.tab_vergi_raporlari = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_vergi_raporlari, text="Vergi Raporları")
        self._vergi_raporlari_arayuzu_olustur(self.tab_vergi_raporlari)  # Vergi raporları sekmesinin içeriğini oluştur

    def _ana_islemler_arayuzu_olustur(self, parent_frame):
        """Ana işlemler sekmesinin kullanıcı arayüzünü oluşturur."""
        # İşlem giriş/düzenleme bölümü
        giris_frame = ttk.LabelFrame(parent_frame, text="Yeni İşlem Ekle / Düzenle", padding=15)
        giris_frame.pack(pady=10, padx=0, fill="x", expand=False)

        # Giriş alanları için widget tanımlamaları
        input_widgets = [
            ("İşlem Türü:", "tur_var", ["Gelir", "Gider"], "Combobox"),
            ("Miktar (₺):", "miktar_entry", None, "Entry"),
            ("Kategori:", "kategori_var", [], "Combobox"),  # Kategoriler dinamik olarak yüklenecek
            ("Açıklama:", "aciklama_entry", None, "Entry"),
            ("Tarih:", "tarih_entry", None, "DateEntry")  # Takvim widget'ı
        ]

        # Her bir giriş widget'ını döngü ile oluştur
        for i, (label_text, var_name, values, widget_type) in enumerate(input_widgets):
            ttk.Label(giris_frame, text=label_text).grid(row=i, column=0, sticky="w", padx=10, pady=5)

            if widget_type == "Combobox":
                var = tk.StringVar()
                cb = ttk.Combobox(giris_frame, textvariable=var, values=values, state="readonly", width=30)
                cb.grid(row=i, column=1, padx=10, pady=5, sticky="ew")
                setattr(self, var_name, var)  # self.tur_var, self.kategori_var gibi değişkenleri ayarla
                if var_name == "kategori_var":
                    self.kategori_combobox = cb  # Kategori combobox'ına özel referans sakla
                    # Kategori öner butonu (Yapay zeka entegrasyonu)
                    ttk.Button(giris_frame, text="Kategori Öner", command=self._kategori_oner).grid(row=i, column=2,
                                                                                                    padx=5, pady=5,
                                                                                                    sticky="w")
            elif widget_type == "Entry":
                entry = ttk.Entry(giris_frame, width=35)
                entry.grid(row=i, column=1, padx=10, pady=5, sticky="ew")
                setattr(self, var_name, entry)  # self.miktar_entry, self.aciklama_entry gibi değişkenleri ayarla
            elif widget_type == "DateEntry":
                date_entry = DateEntry(giris_frame, selectmode='day', date_pattern='yyyy-mm-dd', width=32,
                                       background='darkblue', foreground='white', borderwidth=2)
                date_entry.grid(row=i, column=1, padx=10, pady=5, sticky="ew")
                date_entry.set_date(datetime.now().strftime("%Y-%m-%d"))  # Varsayılan olarak bugünün tarihini ayarla
                setattr(self, var_name, date_entry)  # self.tarih_entry değişkenini ayarla

        giris_frame.grid_columnconfigure(1, weight=1)  # İkinci sütunu genişleyebilir yap

        # İşlem butonları çerçevesi
        buton_frame = ttk.Frame(giris_frame, padding="10 0 0 0")
        buton_frame.grid(row=len(input_widgets), column=0, columnspan=3, pady=10, sticky="ew")  # Tüm sütunları kapla

        # İşlem butonları
        ttk.Button(buton_frame, text="Kaydet", command=self.kaydet).pack(side="left", padx=5, fill="x", expand=True)
        ttk.Button(buton_frame, text="Güncelle", command=self.guncelle).pack(side="left", padx=5, fill="x", expand=True)
        ttk.Button(buton_frame, text="Temizle", command=self.temizle).pack(side="left", padx=5, fill="x", expand=True)
        ttk.Button(buton_frame, text="Sil", command=self.sil).pack(side="left", padx=5, fill="x", expand=True)

        # Filtreleme ve arama bölümü
        filtre_frame = ttk.LabelFrame(parent_frame, text="Filtreleme ve Arama", padding=15)
        filtre_frame.pack(pady=10, padx=0, fill="x", expand=False)

        # Filtreleme widget'ları
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
        self.arama_entry.bind("<KeyRelease>", self.listele)  # Yazdıkça filtreleme için

        ttk.Label(filtre_frame, text="Tarih Aralığı:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.bas_tarih_entry = DateEntry(filtre_frame, selectmode='day', date_pattern='yyyy-mm-dd', width=12)
        self.bas_tarih_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        self.bas_tarih_entry.set_date("2023-01-01")  # Başlangıç tarihini ayarla

        ttk.Label(filtre_frame, text="-").grid(row=1, column=2, sticky="w")

        self.bit_tarih_entry = DateEntry(filtre_frame, selectmode='day', date_pattern='yyyy-mm-dd', width=12)
        self.bit_tarih_entry.grid(row=1, column=3, padx=5, pady=5, sticky="ew")
        self.bit_tarih_entry.set_date(datetime.now().strftime("%Y-%m-%d"))  # Bitiş tarihini bugüne ayarla

        ttk.Button(filtre_frame, text="Filtrele", command=self.listele).grid(row=1, column=4, columnspan=2, padx=10,
                                                                             pady=5, sticky="ew")

        for i in range(6):  # Tüm sütunları genişleyebilir yap
            filtre_frame.grid_columnconfigure(i, weight=1)

        # İşlem listesi (Treeview)
        liste_frame = ttk.Frame(parent_frame, padding="10 0 0 0")
        liste_frame.pack(pady=10, padx=0, fill="both", expand=True)

        # Kaydırma çubukları
        scroll_y = ttk.Scrollbar(liste_frame, orient="vertical")
        scroll_x = ttk.Scrollbar(liste_frame, orient="horizontal")

        self.liste = ttk.Treeview(liste_frame,
                                  columns=("id", "Tür", "Miktar", "Kategori", "Açıklama", "Tarih"),
                                  show="headings",  # Sadece başlıkları göster
                                  yscrollcommand=scroll_y.set,
                                  xscrollcommand=scroll_x.set)

        scroll_y.config(command=self.liste.yview)
        scroll_x.config(command=self.liste.xview)

        # Sütun başlıkları ve genişlikleri
        columns_info = {
            "id": {"text": "ID", "width": 50, "minwidth": 40},
            "Tür": {"text": "Tür", "width": 80, "minwidth": 70},
            "Miktar": {"text": "Miktar (₺)", "width": 100, "minwidth": 90},
            "Kategori": {"text": "Kategori", "width": 100, "minwidth": 90},
            "Açıklama": {"text": "Açıklama", "width": 250, "minwidth": 200},
            "Tarih": {"text": "Tarih", "width": 100, "minwidth": 90}
        }

        for col_name, info in columns_info.items():
            self.liste.heading(col_name, text=info["text"], anchor="w")  # Başlık metni ve hizalama
            self.liste.column(col_name, width=info["width"], minwidth=info["minwidth"],
                              stretch=tk.NO)  # Sütun özellikleri

        self.liste.grid(row=0, column=0, sticky="nsew")  # Treeview'ı yerleştir
        scroll_y.grid(row=0, column=1, sticky="ns")  # Dikey kaydırma çubuğunu yerleştir
        scroll_x.grid(row=1, column=0, sticky="ew")  # Yatay kaydırma çubuğunu yerleştir

        liste_frame.grid_rowconfigure(0, weight=1)  # Treeview'ın satırını genişleyebilir yap
        liste_frame.grid_columnconfigure(0, weight=1)  # Treeview'ın sütununu genişleyebilir yap

        self.liste.bind("<<TreeviewSelect>>", self.liste_secildi)  # Satır seçildiğinde olayı bağla

        # Özet bilgiler bölümü (Toplam Gelir, Gider, Bakiye)
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
        """Gelişmiş araçlar sekmesinin arayüzünü oluşturur."""
        # Sol ve sağ panelleri oluştur
        left_panel_advanced = ttk.Frame(parent_frame)
        left_panel_advanced.pack(side="left", fill="both", expand=True, padx=(0, 10))

        right_panel_advanced = ttk.Frame(parent_frame)
        right_panel_advanced.pack(side="right", fill="both", expand=True, padx=(10, 0))

        # --- Tekrarlayan İşlemler Paneli (Sol Panelde) ---
        tekrar_eden_frame = ttk.LabelFrame(left_panel_advanced, text="Tekrarlayan İşlemler Tanımla", padding=15)
        tekrar_eden_frame.pack(pady=10, padx=0, fill="x", expand=False)

        # Tekrarlayan işlem giriş alanları
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

        # Tekrarlayan işlem butonları
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

        # Tekrarlayan işlemler listesi (Treeview)
        tekrar_eden_liste_frame = ttk.Frame(left_panel_advanced, padding="10 0 0 0")
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

        # Tekrarlayan işlemler sütun başlıkları ve genişlikleri
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
        kategori_yonetim_frame.pack(pady=10, padx=0, fill="x", expand=False)

        # Kategori giriş alanları
        ttk.Label(kategori_yonetim_frame, text="Kategori Adı:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.kategori_adi_entry = ttk.Entry(kategori_yonetim_frame, width=30)
        self.kategori_adi_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(kategori_yonetim_frame, text="Kategori Türü:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.kategori_tur_var = tk.StringVar()
        self.kategori_tur_combobox = ttk.Combobox(kategori_yonetim_frame, textvariable=self.kategori_tur_var,
                                                  values=["Gelir", "Gider", "Genel"], state="readonly", width=28)
        self.kategori_tur_combobox.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        self.kategori_tur_var.set("Genel")  # Varsayılan kategori türü

        kategori_yonetim_frame.grid_columnconfigure(1, weight=1)

        # Kategori butonları
        kategori_buton_frame = ttk.Frame(kategori_yonetim_frame, padding="10 0 0 0")
        kategori_buton_frame.grid(row=2, column=0, columnspan=2, pady=10, sticky="ew")
        ttk.Button(kategori_buton_frame, text="Kategori Ekle",
                   command=lambda: self.kategori_ekle(self.kategori_adi_entry.get(), self.kategori_tur_var.get(),
                                                      show_message=True)).pack(side="left", padx=5, fill="x",
                                                                               expand=True)  # show_message=True ekledik
        ttk.Button(kategori_buton_frame, text="Kategori Sil", command=self.kategori_sil).pack(side="left", padx=5,
                                                                                              fill="x", expand=True)
        ttk.Button(kategori_buton_frame, text="Temizle", command=self.temizle_kategori).pack(side="left", padx=5,
                                                                                             fill="x", expand=True)

        # Kategori listesi (Treeview)
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
        grafik_rapor_frame.pack(pady=10, padx=0, fill="x", expand=False)
        ttk.Button(grafik_rapor_frame, text="Gelir-Gider Grafikleri", command=self.grafik_goster).pack(pady=5, fill="x")
        ttk.Button(grafik_rapor_frame, text="Gelir-Gider Raporu Oluştur", command=self.rapor_olustur).pack(pady=5,
                                                                                                           fill="x")
        # Yapay Zekayı Yeniden Eğit Butonu
        ttk.Button(grafik_rapor_frame, text="Yapay Zekayı Yeniden Eğit", command=self._retrain_ai_model).pack(pady=5,
                                                                                                              fill="x")

    def _fatura_teklif_arayuzu_olustur(self, parent_frame):
        """Fatura/Teklif sekmesinin kullanıcı arayüzünü oluşturur."""
        fatura_teklif_frame = ttk.LabelFrame(parent_frame, text="Fatura / Teklif Oluştur ve Yönet", padding=15)
        fatura_teklif_frame.pack(pady=10, padx=0, fill="both", expand=True)

        fatura_teklif_frame.grid_columnconfigure(1, weight=1)
        fatura_teklif_frame.grid_rowconfigure(11, weight=1)

        # Fatura/Teklif giriş alanları
        fatura_input_widgets = [
            ("Tür:", "fatura_tur_var", ["Fatura", "Teklif"], "Combobox"),
            ("Belge No:", "belge_numarasi_entry", None, "Entry"),
            ("Müşteri Adı:", "fatura_musteri_var", [], "Combobox"),  # Müşteriler dinamik yüklenecek
            ("Belge Tarihi:", "fatura_belge_tarih_entry", None, "DateEntry"),
            ("Son Ödeme/Geçerlilik Tarihi:", "fatura_son_odeme_gecerlilik_tarih_entry", None, "DateEntry"),
            ("Ürün/Hizmetler (Ad,Miktar,Fiyat,KDV% | her satırda bir kalem):", "fatura_urun_hizmetler_text", None,
             "Text"),
            ("Toplam Tutar (KDV Hariç ₺):", "fatura_kdv_haric_toplam_entry", None, "Entry"),
            ("Toplam KDV (₺):", "fatura_toplam_kdv_entry", None, "Entry"),
            ("Genel Toplam (₺):", "fatura_genel_toplam_entry", None, "Entry"),
            ("Notlar:", "fatura_notlar_text", None, "Text"),
            ("Durum:", "fatura_durum_var", ["Taslak", "Gönderildi", "Ödendi", "İptal Edildi"], "Combobox"),
        ]

        current_row = 0
        for label_text, var_name, values, widget_type in fatura_input_widgets:
            ttk.Label(fatura_teklif_frame, text=label_text).grid(row=current_row, column=0, padx=5, pady=2, sticky="nw")

            if widget_type == "Combobox":
                var = tk.StringVar()
                cb = ttk.Combobox(fatura_teklif_frame, textvariable=var, values=values, state="readonly", width=30)
                cb.grid(row=current_row, column=1, padx=5, pady=2, sticky="ew")
                setattr(self, var_name, var)
                if var_name == "fatura_tur_var":
                    var.set("Fatura")
                    cb.bind("<<ComboboxSelected>>",
                            self._fatura_tur_secildi)  # Tür değiştiğinde belge numarası sıfırlama
                if var_name == "fatura_durum_var":
                    var.set("Taslak")
                if var_name == "fatura_musteri_var":
                    self.fatura_musteri_combobox = cb
            elif widget_type == "Entry":
                entry = ttk.Entry(fatura_teklif_frame, width=35)
                entry.grid(row=current_row, column=1, padx=5, pady=2, sticky="ew")
                setattr(self, var_name, entry)
                if var_name == "belge_numarasi_entry":
                    entry.config(state="readonly")  # Belge numarası manuel değiştirilemez
                elif var_name in ["fatura_kdv_haric_toplam_entry", "fatura_toplam_kdv_entry",
                                  "fatura_genel_toplam_entry"]:
                    entry.config(state="readonly")  # Toplam tutarlar manuel değiştirilemez
            elif widget_type == "DateEntry":
                date_entry = DateEntry(fatura_teklif_frame, selectmode='day', date_pattern='yyyy-mm-dd', width=32,
                                       background='darkblue', foreground='white', borderwidth=2)
                date_entry.grid(row=current_row, column=1, padx=5, pady=2, sticky="ew")
                date_entry.set_date(datetime.now().strftime("%Y-%m-%d"))
                setattr(self, var_name, date_entry)
            elif widget_type == "Text":
                text_widget = tk.Text(fatura_teklif_frame, height=4, width=35)
                text_widget.grid(row=current_row, column=1, padx=5, pady=2, sticky="ew")
                setattr(self, var_name, text_widget)
                if var_name == "fatura_urun_hizmetler_text":
                    text_widget.bind("<KeyRelease>", self._fatura_tutari_hesapla)  # Yazdıkça toplamları hesapla
            current_row += 1

        # Belge numarası oluşturma butonu
        ttk.Button(fatura_teklif_frame, text="Numara Oluştur", command=self.belge_numarasi_olustur).grid(row=1,
                                                                                                         column=2,
                                                                                                         padx=5, pady=2,
                                                                                                         sticky="w")

        # Envanterden ürün seçme alanı
        ttk.Label(fatura_teklif_frame, text="Envanterden Ürün Seç:").grid(row=current_row, column=0, padx=5, pady=2,
                                                                          sticky="w")
        self.fatura_urun_sec_var = tk.StringVar()
        self.fatura_urun_sec_combobox = ttk.Combobox(fatura_teklif_frame, textvariable=self.fatura_urun_sec_var,
                                                     values=[], state="readonly", width=30)
        self.fatura_urun_sec_combobox.grid(row=current_row, column=1, padx=5, pady=2, sticky="ew")
        ttk.Button(fatura_teklif_frame, text="Ekle", command=self.fatura_urun_ekle_envanterden).grid(row=current_row,
                                                                                                     column=2, padx=5,
                                                                                                     pady=2, sticky="w")
        current_row += 1

        # Fatura/Teklif butonları
        fatura_buton_frame = ttk.Frame(fatura_teklif_frame, padding="10 0 0 0")
        fatura_buton_frame.grid(row=current_row, column=0, columnspan=3, pady=10, sticky="ew")

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

        # Fatura/Teklif listesi (Treeview)
        self.fatura_liste = ttk.Treeview(fatura_teklif_frame,
                                         columns=("id", "Tür", "Belge No", "Müşteri", "Toplam", "KDV", "Genel Toplam",
                                                  "Tarih", "Durum"), show="headings")
        self.fatura_liste.heading("id", text="ID", anchor="w")
        self.fatura_liste.column("id", width=30, minwidth=20, stretch=tk.NO)
        self.fatura_liste.heading("Tür", text="Tür", anchor="w")
        self.fatura_liste.column("Tür", width=60, minwidth=50, stretch=tk.NO)
        self.fatura_liste.heading("Belge No", text="Belge No", anchor="w")
        self.fatura_liste.column("Belge No", width=90, minwidth=70, stretch=tk.NO)
        self.fatura_liste.heading("Müşteri", text="Müşteri Adı", anchor="w")
        self.fatura_liste.column("Müşteri", width=100, minwidth=80)
        self.fatura_liste.heading("Toplam", text="Toplam (₺)", anchor="e")  # Sağ hizalı
        self.fatura_liste.column("Toplam", width=90, minwidth=70, stretch=tk.NO, anchor="e")
        self.fatura_liste.heading("KDV", text="KDV (₺)", anchor="e")  # Sağ hizalı
        self.fatura_liste.column("KDV", width=80, minwidth=60, stretch=tk.NO, anchor="e")
        self.fatura_liste.heading("Genel Toplam", text="Genel Toplam (₺)", anchor="e")  # Sağ hizalı
        self.fatura_liste.column("Genel Toplam", width=110, minwidth=90, stretch=tk.NO, anchor="e")
        self.fatura_liste.heading("Tarih", text="Tarih", anchor="w")
        self.fatura_liste.column("Tarih", width=90, minwidth=70, stretch=tk.NO)
        self.fatura_liste.heading("Durum", text="Durum", anchor="w")
        self.fatura_liste.column("Durum", width=80, minwidth=60, stretch=tk.NO)

        self.fatura_liste.grid(row=current_row + 1, column=0, columnspan=3, sticky="nsew", padx=5, pady=5)
        fatura_teklif_frame.grid_rowconfigure(current_row + 1, weight=1)

        # Fatura/Teklif listesi için kaydırma çubukları
        fatura_scroll_y = ttk.Scrollbar(fatura_teklif_frame, orient="vertical", command=self.fatura_liste.yview)
        fatura_scroll_x = ttk.Scrollbar(fatura_teklif_frame, orient="horizontal", command=self.fatura_liste.xview)
        self.fatura_liste.configure(yscrollcommand=fatura_scroll_y.set, xscrollcommand=fatura_scroll_x.set)

        fatura_scroll_y.grid(row=current_row + 1, column=3, sticky="ns")
        fatura_scroll_x.grid(row=current_row + 2, column=0, columnspan=3, sticky="ew")

        self.fatura_liste.bind("<<TreeviewSelect>>", self.fatura_liste_secildi)

    def _musteri_yonetimi_arayuzu_olustur(self, parent_frame):
        """Müşteri yönetimi sekmesinin kullanıcı arayüzünü oluşturur."""
        musteri_giris_frame = ttk.LabelFrame(parent_frame, text="Yeni Müşteri Ekle / Düzenle", padding=15)
        musteri_giris_frame.pack(pady=10, padx=0, fill="x", expand=False)
        musteri_giris_frame.grid_columnconfigure(1, weight=1)

        # Müşteri giriş alanları
        ttk.Label(musteri_giris_frame, text="Müşteri Adı:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.musteri_adi_entry = ttk.Entry(musteri_giris_frame, width=40)
        self.musteri_adi_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(musteri_giris_frame, text="Adres:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.musteri_adres_entry = ttk.Entry(musteri_giris_frame, width=40)
        self.musteri_adres_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(musteri_giris_frame, text="Telefon:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.musteri_telefon_entry = ttk.Entry(musteri_giris_frame, width=40)
        self.musteri_telefon_entry.grid(row=2, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(musteri_giris_frame, text="E-posta:").grid(row=3, column=0, padx=5, pady=5, sticky="w")
        self.musteri_email_entry = ttk.Entry(musteri_giris_frame, width=40)
        self.musteri_email_entry.grid(row=3, column=1, padx=5, pady=5, sticky="ew")

        # Müşteri butonları
        musteri_buton_frame = ttk.Frame(musteri_giris_frame, padding="10 0 0 0")
        musteri_buton_frame.grid(row=4, column=0, columnspan=2, pady=10, sticky="ew")
        ttk.Button(musteri_buton_frame, text="Kaydet", command=self.musteri_ekle).pack(side="left", padx=5, fill="x",
                                                                                       expand=True)
        ttk.Button(musteri_buton_frame, text="Güncelle", command=self.musteri_guncelle).pack(side="left", padx=5,
                                                                                             fill="x", expand=True)
        ttk.Button(musteri_buton_frame, text="Sil", command=self.musteri_sil).pack(side="left", padx=5, fill="x",
                                                                                   expand=True)
        ttk.Button(musteri_buton_frame, text="Temizle", command=self.temizle_musteri).pack(side="left", padx=5,
                                                                                           fill="x", expand=True)

        # Müşteri listesi (Treeview)
        musteri_liste_frame = ttk.Frame(parent_frame, padding="10 0 0 0")
        musteri_liste_frame.pack(pady=10, padx=0, fill="both", expand=True)
        musteri_liste_frame.grid_rowconfigure(0, weight=1)
        musteri_liste_frame.grid_columnconfigure(0, weight=1)

        musteri_scroll_y = ttk.Scrollbar(musteri_liste_frame, orient="vertical")
        musteri_scroll_x = ttk.Scrollbar(musteri_liste_frame, orient="horizontal")

        self.musteri_liste = ttk.Treeview(musteri_liste_frame,
                                          columns=("id", "Müşteri Adı", "Adres", "Telefon", "E-posta"),
                                          show="headings",
                                          yscrollcommand=musteri_scroll_y.set,
                                          xscrollcommand=musteri_scroll_x.set)

        musteri_scroll_y.config(command=self.musteri_liste.yview)
        musteri_scroll_x.config(command=self.musteri_liste.xview)

        # Müşteri sütun başlıkları ve genişlikleri
        musteri_columns_info = {
            "id": {"text": "ID", "width": 40, "minwidth": 30},
            "Müşteri Adı": {"text": "Müşteri Adı", "width": 150, "minwidth": 120},
            "Adres": {"text": "Adres", "width": 250, "minwidth": 200},
            "Telefon": {"text": "Telefon", "width": 120, "minwidth": 100},
            "E-posta": {"text": "E-posta", "width": 200, "minwidth": 150}
        }

        for col_name, info in musteri_columns_info.items():
            self.musteri_liste.heading(col_name, text=info["text"], anchor="w")
            self.musteri_liste.column(col_name, width=info["width"], minwidth=info["minwidth"], stretch=tk.NO)

        self.musteri_liste.grid(row=0, column=0, sticky="nsew")
        musteri_scroll_y.grid(row=0, column=1, sticky="ns")
        musteri_scroll_x.grid(row=1, column=0, sticky="ew")

        self.musteri_liste.bind("<<TreeviewSelect>>", self.musteri_liste_secildi)

    def _envanter_yonetimi_arayuzu_olustur(self, parent_frame):
        """Envanter yönetimi sekmesinin kullanıcı arayüzünü oluşturur."""
        urun_giris_frame = ttk.LabelFrame(parent_frame, text="Yeni Ürün Ekle / Düzenle", padding=15)
        urun_giris_frame.pack(pady=10, padx=0, fill="x", expand=False)
        urun_giris_frame.grid_columnconfigure(1, weight=1)

        # Ürün giriş alanları
        ttk.Label(urun_giris_frame, text="Ürün Adı:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.urun_adi_entry = ttk.Entry(urun_giris_frame, width=40)
        self.urun_adi_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(urun_giris_frame, text="Stok Miktarı:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.stok_miktari_entry = ttk.Entry(urun_giris_frame, width=40)
        self.stok_miktari_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(urun_giris_frame, text="Alış Fiyatı (₺):").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.alis_fiyati_entry = ttk.Entry(urun_giris_frame, width=40)
        self.alis_fiyati_entry.grid(row=2, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(urun_giris_frame, text="Satış Fiyatı (₺):").grid(row=3, column=0, padx=5, pady=5, sticky="w")
        self.satis_fiyati_entry = ttk.Entry(urun_giris_frame, width=40)
        self.satis_fiyati_entry.grid(row=3, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(urun_giris_frame, text="KDV Oranı (%):").grid(row=4, column=0, padx=5, pady=5, sticky="w")
        self.urun_kdv_orani_var = tk.StringVar(value="18")
        self.urun_kdv_orani_combobox = ttk.Combobox(urun_giris_frame, textvariable=self.urun_kdv_orani_var,
                                                    values=["0", "1", "8", "10", "18", "20"], state="readonly",
                                                    width=38)
        self.urun_kdv_orani_combobox.grid(row=4, column=1, padx=5, pady=5, sticky="ew")

        # Ürün butonları
        urun_buton_frame = ttk.Frame(urun_giris_frame, padding="10 0 0 0")
        urun_buton_frame.grid(row=5, column=0, columnspan=2, pady=10, sticky="ew")
        ttk.Button(urun_buton_frame, text="Kaydet", command=self.urun_ekle).pack(side="left", padx=5, fill="x",
                                                                                 expand=True)
        ttk.Button(urun_buton_frame, text="Güncelle", command=self.urun_guncelle).pack(side="left", padx=5, fill="x",
                                                                                       expand=True)
        ttk.Button(urun_buton_frame, text="Sil", command=self.urun_sil).pack(side="left", padx=5, fill="x", expand=True)
        ttk.Button(urun_buton_frame, text="Temizle", command=self.temizle_urun).pack(side="left", padx=5, fill="x",
                                                                                     expand=True)

        # Ürün listesi (Treeview)
        urun_liste_frame = ttk.Frame(parent_frame, padding="10 0 0 0")
        urun_liste_frame.pack(pady=10, padx=0, fill="both", expand=True)
        urun_liste_frame.grid_rowconfigure(0, weight=1)
        urun_liste_frame.grid_columnconfigure(0, weight=1)

        urun_scroll_y = ttk.Scrollbar(urun_liste_frame, orient="vertical")
        urun_scroll_x = ttk.Scrollbar(urun_liste_frame, orient="horizontal")

        self.urun_liste = ttk.Treeview(urun_liste_frame,
                                       columns=("id", "Ürün Adı", "Stok", "Alış Fiyatı", "Satış Fiyatı", "KDV Oranı"),
                                       show="headings",
                                       yscrollcommand=urun_scroll_y.set,
                                       xscrollcommand=urun_scroll_x.set)

        urun_scroll_y.config(command=self.urun_liste.yview)
        urun_scroll_x.config(command=self.urun_liste.xview)

        # Ürün sütun başlıkları ve genişlikleri
        urun_columns_info = {
            "id": {"text": "ID", "width": 40, "minwidth": 30},
            "Ürün Adı": {"text": "Ürün Adı", "width": 150, "minwidth": 120},
            "Stok": {"text": "Stok Miktarı", "width": 100, "minwidth": 80, "anchor": "e"},
            "Alış Fiyatı": {"text": "Alış Fiyatı (₺)", "width": 120, "minwidth": 100, "anchor": "e"},
            "Satış Fiyatı": {"text": "Satış Fiyatı (₺)", "width": 120, "minwidth": 100, "anchor": "e"},
            "KDV Oranı": {"text": "KDV (%)", "width": 80, "minwidth": 60, "anchor": "e"}
        }

        for col_name, info in urun_columns_info.items():
            self.urun_liste.heading(col_name, text=info["text"], anchor=info.get("anchor", "w"))
            self.urun_liste.column(col_name, width=info["width"], minwidth=info["minwidth"], stretch=tk.NO,
                                   anchor=info.get("anchor", "w"))

        self.urun_liste.grid(row=0, column=0, sticky="nsew")
        urun_scroll_y.grid(row=0, column=1, sticky="ns")
        urun_scroll_x.grid(row=1, column=0, sticky="ew")

        self.urun_liste.bind("<<TreeviewSelect>>", self.urun_liste_secildi)

    def _vergi_raporlari_arayuzu_olustur(self, parent_frame):
        """Vergi raporları sekmesinin kullanıcı arayüzünü oluşturur."""
        vergi_rapor_frame = ttk.LabelFrame(parent_frame, text="Vergi Raporları ve KDV Özetleri", padding=15)
        vergi_rapor_frame.pack(pady=10, padx=0, fill="both", expand=True)
        vergi_rapor_frame.grid_columnconfigure(1, weight=1)

        # Tarih filtreleme alanı
        ttk.Label(vergi_rapor_frame, text="Başlangıç Tarihi:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.vergi_bas_tarih_entry = DateEntry(vergi_rapor_frame, selectmode='day', date_pattern='yyyy-mm-dd', width=20)
        self.vergi_bas_tarih_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.vergi_bas_tarih_entry.set_date(datetime.now().replace(day=1).strftime("%Y-%m-%d"))  # Ayın başına ayarla

        ttk.Label(vergi_rapor_frame, text="Bitiş Tarihi:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.vergi_bit_tarih_entry = DateEntry(vergi_rapor_frame, selectmode='day', date_pattern='yyyy-mm-dd', width=20)
        self.vergi_bit_tarih_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        self.vergi_bit_tarih_entry.set_date(datetime.now().strftime("%Y-%m-%d"))  # Bugüne ayarla

        ttk.Button(vergi_rapor_frame, text="Raporu Getir", command=self.vergi_raporu_getir).grid(row=2, column=0,
                                                                                                 columnspan=2, padx=5,
                                                                                                 pady=10, sticky="ew")

        # KDV Özetleri bölümü
        kdv_ozet_frame = ttk.LabelFrame(vergi_rapor_frame, text="KDV Özetleri", padding=10)
        kdv_ozet_frame.grid(row=3, column=0, columnspan=2, padx=5, pady=10, sticky="nsew")
        kdv_ozet_frame.grid_columnconfigure(1, weight=1)

        ttk.Label(kdv_ozet_frame, text="Toplam Satış KDV'si (Tahsil Edilen):", font=("Arial", 10, "bold")).grid(row=0,
                                                                                                                column=0,
                                                                                                                padx=5,
                                                                                                                pady=2,
                                                                                                                sticky="w")
        self.toplam_satis_kdv_label = ttk.Label(kdv_ozet_frame, text="₺0.00", font=("Arial", 10))
        self.toplam_satis_kdv_label.grid(row=0, column=1, padx=5, pady=2, sticky="e")

        ttk.Label(kdv_ozet_frame, text="Toplam Alış KDV'si (Ödenen):", font=("Arial", 10, "bold")).grid(row=1, column=0,
                                                                                                        padx=5, pady=2,
                                                                                                        sticky="w")
        self.toplam_alis_kdv_label = ttk.Label(kdv_ozet_frame, text="₺0.00",
                                               font=("Arial", 10))  # Şimdilik manuel, ileride ekleyebiliriz
        self.toplam_alis_kdv_label.grid(row=1, column=1, padx=5, pady=2, sticky="e")

        ttk.Label(kdv_ozet_frame, text="Ödenecek/İade Edilecek KDV:", font=("Arial", 11, "bold")).grid(row=2, column=0,
                                                                                                       padx=5, pady=5,
                                                                                                       sticky="w")
        self.kdv_farki_label = ttk.Label(kdv_ozet_frame, text="₺0.00", font=("Arial", 11, "bold"))
        self.kdv_farki_label.grid(row=2, column=1, padx=5, pady=5, sticky="e")

        # KDV Detay Tablosu (Oranlara göre dağılım)
        kdv_detay_frame = ttk.LabelFrame(vergi_rapor_frame, text="KDV Oranlarına Göre Dağılım", padding=10)
        kdv_detay_frame.grid(row=4, column=0, columnspan=2, padx=5, pady=10, sticky="nsew")
        kdv_detay_frame.grid_columnconfigure(0, weight=1)
        kdv_detay_frame.grid_columnconfigure(1, weight=1)

        self.kdv_detay_liste = ttk.Treeview(kdv_detay_frame, columns=("Oran", "KDV Tutarı"), show="headings")
        self.kdv_detay_liste.heading("Oran", text="KDV Oranı (%)", anchor="w")
        self.kdv_detay_liste.column("Oran", width=100, minwidth=80, stretch=tk.NO)
        self.kdv_detay_liste.heading("KDV Tutarı", text="KDV Tutarı (₺)", anchor="e")
        self.kdv_detay_liste.column("KDV Tutarı", width=150, minwidth=120, stretch=tk.NO, anchor="e")
        self.kdv_detay_liste.pack(fill="both", expand=True)

        vergi_rapor_frame.grid_rowconfigure(4, weight=1)

        # --- Ana İşlem Fonksiyonları ---

    def kaydet(self):
        """Yeni bir gelir/gider işlemi kaydeder."""
        tur = self.tur_var.get()
        miktar_str = self.miktar_entry.get()
        kategori = self.kategori_var.get()
        aciklama = self.aciklama_entry.get()
        tarih = self.tarih_entry.get_date().strftime("%Y-%m-%d")

        # Giriş kontrolleri
        if not tur:
            messagebox.showerror("Hata", "Lütfen işlem türünü seçiniz.")
            return

        try:
            miktar = float(miktar_str.replace(",", "."))  # Virgülü noktaya çevirerek ondalık sayıya dönüştür
            if miktar <= 0:
                messagebox.showerror("Hata", "Miktar pozitif bir sayı olmalıdır.")
                return
        except ValueError:
            messagebox.showerror("Hata", "Geçersiz miktar değeri. Lütfen sayı giriniz.")
            return

        if not kategori or kategori == "Kategori Seçin":  # "Kategori Seçin" varsayılan değeri de kontrol et
            messagebox.showerror("Hata", "Lütfen bir kategori seçiniz.")
            return

        if not tarih:
            messagebox.showerror("Hata", "Lütfen geçerli bir tarih seçiniz.")
            return

        try:
            # İşlemi veritabanına ekle
            self.db_manager.insert_transaction(tur, miktar, kategori, aciklama, tarih, self.kullanici_id)

            messagebox.showinfo("Başarılı", "İşlem başarıyla kaydedildi.")

            # Her işlem kaydedildiğinde AI modelini kullanıcı verileriyle yeniden eğit
            # Bu işlem büyük veri setlerinde UI'yi dondurabilir, ancak az veri varsa sorun olmaz.
            # Performans kritikse, ayrı bir thread'de çalıştırmak daha iyi olabilir.
            self._retrain_ai_model()

            self.temizle()  # Giriş alanlarını temizle
            self.listele()  # Listeyi güncelle
        except Exception as e:
            messagebox.showerror("Hata", f"Veritabanına kaydetme hatası: {e}")

    def guncelle(self):
        """Mevcut bir gelir/gider işlemini günceller."""
        if self.selected_item_id is None:
            messagebox.showwarning("Uyarı", "Lütfen güncellemek istediğiniz kaydı seçiniz.")
            return

        tur = self.tur_var.get()
        miktar_str = self.miktar_entry.get()
        kategori = self.kategori_var.get()
        aciklama = self.aciklama_entry.get()
        tarih = self.tarih_entry.get_date().strftime("%Y-%m-%d")

        # Giriş kontrolleri (kaydet fonksiyonu ile benzer)
        if not tur:
            messagebox.showerror("Hata", "Lütfen işlem türünü seçiniz.")
            return

        try:
            miktar = float(miktar_str.replace(",", "."))
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
            # İşlemi veritabanında güncelle
            self.db_manager.update_transaction(self.selected_item_id, tur, miktar, kategori, aciklama, tarih,
                                               self.kullanici_id)
            messagebox.showinfo("Başarılı", "Kayıt başarıyla güncellendi.")

            # Her işlem güncellendiğinde AI modelini yeniden eğit
            self._retrain_ai_model()

            self.temizle()
            self.listele()
        except Exception as e:
            messagebox.showerror("Hata", f"Veritabanı güncelleme hatası: {e}")

    def listele(self, event=None):
        """İşlemleri filtreleyerek listeler ve özet bilgileri günceller."""
        # Mevcut tüm satırları temizle
        for row in self.liste.get_children():
            self.liste.delete(row)

        # Filtreleme kriterlerini al
        tur = self.filtre_tur_var.get()
        kategori = self.filtre_kategori_var.get()

        bas_tarih = self.bas_tarih_entry.get_date().strftime("%Y-%m-%d") if self.bas_tarih_entry.get() else ""
        bit_tarih = self.bit_tarih_entry.get_date().strftime("%Y-%m-%d") if self.bit_tarih_entry.get() else ""
        arama_terimi = self.arama_entry.get().strip()

        try:
            # Veritabanından filtrelenmiş verileri çek
            veriler = self.db_manager.get_transactions(self.kullanici_id, tur, kategori, bas_tarih, bit_tarih,
                                                       arama_terimi)
        except Exception as e:
            messagebox.showerror("Veritabanı Hatası", f"Veri çekme hatası: {e}")
            return

        toplam_gelir = 0.0
        toplam_gider = 0.0

        # Çekilen verileri Treeview'a ekle ve toplamları hesapla
        for veri in veriler:
            self.liste.insert("", tk.END, values=veri)

            if veri[1] == "Gelir":  # veri[1] işlem türünü (Gelir/Gider) tutar
                toplam_gelir += veri[2]  # veri[2] miktarı tutar
            else:
                toplam_gider += veri[2]

        # Özet bilgilerini güncelle
        self.toplam_gelir_label.config(text=f"Toplam Gelir: ₺{toplam_gelir:,.2f}")
        self.toplam_gider_label.config(text=f"Toplam Gider: ₺{toplam_gider:,.2f}")
        bakiye = toplam_gelir - toplam_gider
        self.bakiye_label.config(text=f"Bakiye: ₺{bakiye:,.2f}",
                                 foreground="blue" if bakiye >= 0 else "red")  # Bakiyeye göre renk değişimi

    def liste_secildi(self, event):
        """İşlem listesinden bir öğe seçildiğinde giriş alanlarını doldurur."""
        selected_items = self.liste.selection()
        if selected_items:
            selected_item = selected_items[0]
            values = self.liste.item(selected_item, "values")
            self.selected_item_id = values[0]  # Seçili öğenin ID'sini sakla

            # Giriş alanlarını seçilen verilerle doldur
            self.tur_var.set(values[1])
            self.miktar_entry.delete(0, tk.END)
            self.miktar_entry.insert(0, f"{values[2]}".replace(".", ","))  # Virgül formatıyla göster
            self.kategori_var.set(values[3])
            self.aciklama_entry.delete(0, tk.END)
            self.aciklama_entry.insert(0, values[4])
            try:
                date_obj = datetime.strptime(values[5], "%Y-%m-%d").date()  # Tarihi DateEntry formatına dönüştür
                self.tarih_entry.set_date(date_obj)
            except ValueError:
                self.tarih_entry.set_date(datetime.now().date())  # Hata durumunda bugünü ayarla
        else:
            self.selected_item_id = None  # Seçim yoksa ID'yi sıfırla
            self.temizle()  # Giriş alanlarını temizle

    def temizle(self):
        """Ana işlem giriş alanlarını temizler."""
        self.tur_var.set("Gelir")  # Varsayılan değer
        self.miktar_entry.delete(0, tk.END)
        self.kategori_var.set("Kategori Seçin")  # Varsayılan değer
        self.aciklama_entry.delete(0, tk.END)
        self.tarih_entry.set_date(datetime.now().date())
        self.selected_item_id = None  # Seçili ID'yi sıfırla

    def sil(self):
        """Seçili gelir/gider işlemini siler."""
        selected_items = self.liste.selection()
        if not selected_items:
            messagebox.showwarning("Uyarı", "Lütfen silmek istediğiniz kaydı seçiniz.")
            return

        selected_item = selected_items[0]
        values = self.liste.item(selected_item, "values")
        record_id = values[0]  # Silinecek kaydın ID'si

        onay = messagebox.askyesno("Onay", "Seçili kaydı silmek istediğinize emin misiniz?")
        if onay:
            try:
                self.db_manager.delete_transaction(record_id, self.kullanici_id)
                messagebox.showinfo("Başarılı", "Kayıt başarıyla silindi.")

                # Her işlem silindiğinde AI modelini yeniden eğit
                self._retrain_ai_model()

                self.listele()  # Listeyi güncelle
                self.temizle()  # Giriş alanlarını temizle
            except Exception as e:
                messagebox.showerror("Hata", f"Kayıt silme hatası: {e}")

    def grafik_goster(self):
        """Gelir-gider grafiklerini gösterir."""
        kategori_verileri, zaman_verileri = self.db_manager.get_transaction_for_charts(self.kullanici_id)

        if not kategori_verileri and not zaman_verileri:
            messagebox.showinfo("Bilgi", "Gösterilecek veri bulunamadı.")
            return

        grafik_pencere = tk.Toplevel(self.root)  # Yeni bir pencere oluştur
        grafik_pencere.title("Gelir-Gider Grafikleri")
        grafik_pencere.geometry("1000x700")

        # Matplotlib figür ve eksenleri oluştur
        fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(18, 6))  # 1 satır, 3 sütunlu alt grafik
        fig.tight_layout(pad=4.0)  # Grafikler arası boşluk

        # --- Gelir Dağılım Grafiği (Pasta Grafik) ---
        gelirler = [v for v in kategori_verileri if v[0] == "Gelir"]  # Sadece gelir verilerini al
        if gelirler:
            gelir_miktarlari = [v[2] for v in gelirler]
            gelir_kategorileri = [f"{v[1]} ({v[2]:,.2f}₺)" for v in gelirler]  # Etiketlere miktar ekle
            ax1.pie(gelir_miktarlari,
                    labels=gelir_kategorileri,
                    autopct='%1.1f%%',  # Yüzdeleri göster
                    startangle=90,  # Başlangıç açısı
                    pctdistance=0.85)  # Yüzde etiketlerinin konumu
            ax1.set_title("Gelir Dağılımı", fontsize=14)
            ax1.axis('equal')  # Oranların eşit görünmesini sağla (daire şeklinde)
        else:
            ax1.text(0.5, 0.5, "Gelir Verisi Yok", horizontalalignment='center', verticalalignment='center',
                     transform=ax1.transAxes, fontsize=12)
            ax1.set_title("Gelir Dağılımı", fontsize=14)
            ax1.axis('off')  # Eksenleri gizle

        # --- Gider Dağılım Grafiği (Pasta Grafik) ---
        giderler = [v for v in kategori_verileri if v[0] == "Gider"]  # Sadece gider verilerini al
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

        # --- Zaman İçinde Kümülatif Bakiye Grafiği (Çizgi Grafik) ---
        if zaman_verileri:
            tarihler = sorted(list(set([v[0] for v in zaman_verileri])))  # Benzersiz tarihleri sırala
            gunluk_bakiye = {t: 0.0 for t in tarihler}  # Her gün için başlangıç bakiyesini sıfırla

            # Günlük bakiyeleri hesapla
            for tarih, tur, miktar in zaman_verileri:
                if tur == "Gelir":
                    gunluk_bakiye[tarih] += miktar
                else:
                    gunluk_bakiye[tarih] -= miktar

            # Kümülatif bakiyeyi hesapla
            kumulatif_bakiye = []
            current_bakiye = 0
            for tarih in tarihler:
                current_bakiye += gunluk_bakiye[tarih]
                kumulatif_bakiye.append(current_bakiye)

            ax3.plot(tarihler, kumulatif_bakiye, marker='o', linestyle='-', color='purple')
            ax3.set_title("Zaman İçinde Kümülatif Bakiye", fontsize=14)
            ax3.set_xlabel("Tarih", fontsize=12)
            ax3.set_ylabel("Bakiye (₺)", fontsize=12)
            ax3.tick_params(axis='x', rotation=45)  # Tarih etiketlerini döndür
            ax3.grid(True, linestyle='--', alpha=0.6)  # Izgara ekle
            num_ticks = min(len(tarihler), 10)  # Maksimum 10 etiket göster (yoğunluğu azaltmak için)
            ax3.xaxis.set_major_locator(plt.MaxNLocator(num_ticks))
        else:
            ax3.text(0.5, 0.5, "Bakiye Verisi Yok", horizontalalignment='center', verticalalignment='center',
                     transform=ax3.transAxes, fontsize=12)
            ax3.set_title("Zaman İçinde Kümülatif Bakiye", fontsize=14)
            ax3.axis('off')

        # Matplotlib grafiğini Tkinter penceresine göm
        canvas = FigureCanvasTkAgg(fig, master=grafik_pencere)
        canvas.draw()
        canvas.get_tk_widget().pack(side="top", fill="both", expand=True)

    # --- Tekrarlayan İşlem Fonksiyonları ---

    def kaydet_tekrar_eden(self):
        """Yeni bir tekrarlayan işlemi kaydeder."""
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
            miktar = float(miktar_str.replace(",", "."))
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
            # Tekrarlayan işlemi veritabanına ekle
            self.db_manager.insert_recurring_transaction(tur, miktar, kategori, aciklama, baslangic_tarih_degeri,
                                                         siklilik, baslangic_tarih_degeri, self.kullanici_id)

            messagebox.showinfo("Başarılı", "Tekrarlayan işlem başarıyla kaydedildi.")
            self.temizle_tekrar_eden()
            self.listele_tekrar_eden_islemler()
            self.uretim_kontrolu()  # Yeni tekrarlayan işlemleri kontrol et
        except Exception as e:
            messagebox.showerror("Hata", f"Tekrarlayan işlem kaydetme hatası: {e}")

    def sil_tekrar_eden(self):
        """Seçili tekrarlayan işlemi siler."""
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
                self.db_manager.delete_recurring_transaction(record_id, self.kullanici_id)
                messagebox.showinfo("Başarılı", "Tekrarlayan kayıt başarıyla silindi.")
                self.listele_tekrar_eden_islemler()
                self.temizle_tekrar_eden()
            except Exception as e:
                messagebox.showerror("Hata", f"Tekrarlayan kayıt silme hatası: {e}")

    def listele_tekrar_eden_islemler(self):
        """Tekrarlayan işlemleri listeler."""
        for row in self.tekrar_eden_liste.get_children():
            self.tekrar_eden_liste.delete(row)

        try:
            veriler = self.db_manager.get_recurring_transactions(self.kullanici_id)
            for veri in veriler:
                self.tekrar_eden_liste.insert("", tk.END, values=veri)
        except Exception as e:
            messagebox.showerror("Veritabanı Hatası", f"Tekrarlayan veri çekme hatası: {e}")

    def tekrar_eden_liste_secildi(self, event):
        """Tekrarlayan işlem listesinden bir öğe seçildiğinde giriş alanlarını doldurur."""
        selected_items = self.tekrar_eden_liste.selection()
        if selected_items:
            selected_item = selected_items[0]
            values = self.tekrar_eden_liste.item(selected_item, "values")
            self.selected_recurring_item_id = values[0]

            self.tur_tekrar_var.set(values[1])
            self.miktar_tekrar_entry.delete(0, tk.END)
            self.miktar_tekrar_entry.insert(0, f"{values[2]}".replace(".", ","))
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
        """Tekrarlayan işlem giriş alanlarını temizler."""
        self.tur_tekrar_var.set("Gelir")
        self.miktar_tekrar_entry.delete(0, tk.END)
        self.kategori_tekrar_var.set("Kategori Seçin")
        self.aciklama_tekrar_entry.delete(0, tk.END)
        self.baslangic_tarih_tekrar_entry.set_date(datetime.now().date())
        self.siklilik_var.set("Aylık")
        self.selected_recurring_item_id = None

    def uretim_kontrolu(self):
        """Tekrarlayan işlemleri kontrol eder ve otomatik olarak ana işlemlere ekler."""
        bugun = datetime.now().date()
        uretilen_islem_sayisi = 0
        uretilen_mesajlar = []

        try:
            tekrar_eden_kayitlar = self.db_manager.get_recurring_transactions(self.kullanici_id)

            for kayit in tekrar_eden_kayitlar:
                (rec_id, tur, miktar, kategori, aciklama, baslangic_tarih_str, siklilik, son_uretilen_tarih_str) = kayit

                baslangic_tarih = datetime.strptime(baslangic_tarih_str, "%Y-%m-%d").date()
                son_uretilen_tarih = datetime.strptime(son_uretilen_tarih_str, "%Y-%m-%d").date()

                next_due_date = son_uretilen_tarih  # Son üretilen tarihten devam et

                # Eğer başlangıç tarihi son üretilen tarihten daha yeniyse, başlangıç tarihini kullan
                if baslangic_tarih > son_uretilen_tarih:
                    next_due_date = baslangic_tarih

                # Bugün veya öncesi için otomatik işlem üret
                while next_due_date <= bugun:
                    if next_due_date > son_uretilen_tarih:  # Daha önce üretilmemişse
                        try:
                            self.db_manager.insert_transaction(tur, miktar, kategori, aciklama,
                                                               next_due_date.strftime("%Y-%m-%d"), self.kullanici_id)
                            uretilen_islem_sayisi += 1
                            uretilen_mesajlar.append(
                                f"{tur} - {miktar:,.2f}₺ ({kategori}) tarihinde: {next_due_date.strftime('%Y-%m-%d')}")
                        except Exception as e:
                            print(f"Hata: Tekrarlayan işlem üretilemedi ({rec_id}): {e}")
                            break  # Hata olursa döngüden çık

                    # Son üretilen tarihi güncelle
                    self.db_manager.update_recurring_transaction_last_generated_date(rec_id,
                                                                                     next_due_date.strftime("%Y-%m-%d"))

                    # Bir sonraki işlem tarihini hesapla
                    if siklilik == "Günlük":
                        next_due_date += timedelta(days=1)
                    elif siklilik == "Haftalık":
                        next_due_date += timedelta(weeks=1)
                    elif siklilik == "Aylık":
                        gun = next_due_date.day
                        ay = next_due_date.month + 1
                        yil = next_due_date.year
                        if ay > 12:  # Yıl değişimi
                            ay = 1
                            yil += 1
                        try:
                            next_due_date = next_due_date.replace(year=yil, month=ay)
                        except ValueError:
                            # Ayın son günü gibi durumlarda (örn: 31 Ocak'tan sonra 31 Şubat olmaz)
                            next_due_date = datetime(yil, ay, 1).date() - timedelta(days=1)
                    elif siklilik == "Yıllık":
                        next_due_date = next_due_date.replace(year=next_due_date.year + 1)
                    else:
                        break  # Bilinmeyen sıklıkta döngüden çık

        except Exception as e:
            messagebox.showerror("Veritabanı Hatası", f"Tekrarlayan işlemler kontrol edilirken hata oluştu: {e}")

        if uretilen_islem_sayisi > 0:
            mesaj = f"Bugün {uretilen_islem_sayisi} adet tekrarlayan işlem otomatik olarak oluşturuldu:\n\n"
            mesaj += "\n".join(uretilen_mesajlar[:10])  # İlk 10 mesajı göster
            if uretilen_islem_sayisi > 10:
                mesaj += "\n..."  # Daha fazlası varsa ... koy
            messagebox.showinfo("Tekrarlayan İşlem Bildirimi", mesaj)
            self.listele()  # Ana işlem listesini güncelle

    # --- Kategori Yönetimi Fonksiyonları ---
    def kategorileri_yukle(self):
        """Kategorileri veritabanından yükler ve ilgili combobox'ları günceller."""
        # Kategori listesini temizle
        for row in self.kategori_liste.get_children():
            self.kategori_liste.delete(row)

        try:
            kategoriler = self.db_manager.get_categories_for_user(self.kullanici_id)

            kategori_adlari = ["Kategori Seçin"]  # İşlem combobox'ı için varsayılan seçenek
            filtre_kategori_adlari = ["Tümü"]  # Filtreleme combobox'ı için varsayılan seçenek

            for kategori in kategoriler:
                self.kategori_liste.insert("", tk.END, values=kategori)  # Kategori listesine ekle
                kategori_adlari.append(kategori[1])  # Kategori adını combobox'a ekle
                filtre_kategori_adlari.append(kategori[1])

            # Combobox'ları yeni kategorilerle güncelle
            self.kategori_combobox['values'] = kategori_adlari
            self.kategori_combobox.set("Kategori Seçin")  # Varsayılan olarak "Kategori Seçin"i ayarla

            self.kategori_tekrar_combobox['values'] = kategori_adlari
            self.kategori_tekrar_combobox.set("Kategori Seçin")

            self.filtre_kategori_combobox['values'] = filtre_kategori_adlari
            self.filtre_kategori_combobox.set("Tümü")

        except Exception as e:
            messagebox.showerror("Veritabanı Hatası", f"Kategoriler yüklenirken hata oluştu: {e}")

    def kategori_ekle(self, kategori_adi, kategori_tur="Genel",
                      show_message=False):  # Varsayılan tür ve mesaj gösterme bayrağı
        """Yeni bir kategori ekler."""
        kategori_adi = kategori_adi.strip()  # Boşlukları temizle

        if not kategori_adi:
            if show_message:
                messagebox.showerror("Hata", "Kategori adı boş bırakılamaz.")
            return False
        # Kategori türü boşsa "Genel" ata
        if not kategori_tur:
            kategori_tur = "Genel"

        try:
            # Kategori zaten varsa hata ver veya işlem yapma
            if self.db_manager.get_category_by_name(kategori_adi, self.kullanici_id):
                if show_message:
                    messagebox.showerror("Hata", "Bu kategori adı zaten mevcut.")
                return False  # Kategori zaten varsa False döndür

            # Yeni kategoriyi veritabanına ekle
            self.db_manager.insert_category(kategori_adi, kategori_tur, self.kullanici_id)
            if show_message:
                messagebox.showinfo("Başarılı", "Kategori başarıyla eklendi.")
            self.temizle_kategori()  # Kategori giriş alanlarını temizle
            self.kategorileri_yukle()  # Kategori listelerini ve combobox'ları güncelle
            return True  # Başarılıysa True döndür
        except Exception as e:
            if show_message:
                messagebox.showerror("Hata", f"Kategori eklenirken hata oluştu: {e}")
            return False  # Hata durumunda False döndür

    def kategori_sil(self):
        """Seçili kategoriyi siler."""
        selected_items = self.kategori_liste.selection()
        if not selected_items:
            messagebox.showwarning("Uyarı", "Lütfen silmek istediğiniz kategoriyi seçiniz.")
            return

        selected_item = selected_items[0]
        values = self.kategori_liste.item(selected_item, "values")
        category_id = values[0]
        kategori_adi = values[1]

        # Bu kategorinin kaç işlemde kullanıldığını kontrol et
        islem_sayisi = self.db_manager.count_transactions_by_category(kategori_adi, self.kullanici_id)

        onay_mesaji = ""
        if islem_sayisi > 0:
            onay_mesaji = f"'{kategori_adi}' kategorisi {islem_sayisi} adet işlemde kullanılmaktadır. Bu kategoriyi silerseniz, bu işlemlerin kategori bilgisi boş kalacaktır. Emin misiniz?"
        else:
            onay_mesaji = f"'{kategori_adi}' kategorisini silmek istediğinize emin misiniz?"

        onay = messagebox.askyesno("Onay", onay_mesaji)

        if onay:
            try:
                # Kategorinin kullanıldığı işlemlerde kategori bilgisini NULL yap
                self.db_manager.update_transactions_category_to_null(kategori_adi, self.kullanici_id)
                # Kategoriyi veritabanından sil
                self.db_manager.delete_category(category_id, self.kullanici_id)
                messagebox.showinfo("Başarılı", "Kategori başarıyla silindi.")
                self.temizle_kategori()
                self.kategorileri_yukle()  # Kategori listelerini ve combobox'ları güncelle
                self.listele()  # Ana işlem listesini güncelle (kategori bilgisi değiştiği için)
                # Kategori silindiğinde AI modelini yeniden eğit
                self._retrain_ai_model()
            except Exception as e:
                messagebox.showerror("Hata", f"Kategori silinirken hata oluştu: {e}")

    def kategori_liste_secildi(self, event):
        """Kategori listesinden bir öğe seçildiğinde giriş alanlarını doldurur."""
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
        """Kategori giriş alanlarını temizler."""
        self.kategori_adi_entry.delete(0, tk.END)
        self.kategori_tur_var.set("Genel")
        self.selected_category_id = None

    def _kategori_oner(self):
        """Açıklama alanındaki metne göre kategori önerisi yapar.
        Önerilen kategori mevcut kategorilerde yoksa ekleme seçeneği sunar.
        """
        description = self.aciklama_entry.get().strip()
        if not description:
            messagebox.showwarning("Uyarı", "Kategori önerebilmek için lütfen bir açıklama giriniz.")
            return

        # Mevcut kategori listesini al
        current_categories = [cat_name for _, cat_name, _ in self.db_manager.get_categories_for_user(self.kullanici_id)]

        # Yapay zekadan kategori tahmini al
        suggested_category = self.ai_predictor.predict_category(description)

        if suggested_category:
            if suggested_category in current_categories:
                # Önerilen kategori mevcutsa, otomatik olarak seç
                self.kategori_var.set(suggested_category)
                messagebox.showinfo("Kategori Önerisi",
                                    f"Açıklamanıza göre önerilen kategori: '{suggested_category}'. Otomatik olarak seçildi.")
            else:
                # Önerilen kategori mevcut değilse, kullanıcıya ekleme seçeneği sun
                onay = messagebox.askyesno("Yeni Kategori Önerisi",
                                           f"Açıklamanıza göre '{suggested_category}' adında yeni bir kategori öneriliyor. Bu kategoriyi eklemek ister misiniz?")
                if onay:
                    # Yeni kategori ekle (varsayılan tür "Genel" olarak)
                    eklendi = self.kategori_ekle(suggested_category, "Genel",
                                                 show_message=False)  # Mesaj göstermeden sessiz ekle
                    if eklendi:
                        self.kategori_var.set(suggested_category)  # Eklenen kategoriyi seç
                        messagebox.showinfo("Kategori Eklendi",
                                            f"'{suggested_category}' kategorisi başarıyla eklendi ve seçildi.")
                    else:
                        messagebox.showerror("Kategori Ekleme Hatası",
                                             f"'{suggested_category}' kategorisi eklenirken bir sorun oluştu.")
                else:
                    messagebox.showinfo("Bilgi", "Yeni kategori ekleme işlemi iptal edildi.")
        else:
            messagebox.showinfo("Kategori Önerisi",
                                "Kategori önerisi yapılamadı. Lütfen manuel olarak seçiniz veya daha fazla veriyle modeli eğitin.")

    def _retrain_ai_model(self):
        """Yapay zeka modelini kullanıcının mevcut verileriyle yeniden eğitir."""
        # Veritabanından kullanıcının tüm işlem açıklamalarını ve kategorilerini çek
        user_data = self.db_manager.get_all_transaction_descriptions_and_categories(self.kullanici_id)

        # Sadece geçerli açıklama ve kategoriye sahip verileri filtrele
        descriptions = [item[0] for item in user_data if item[0] and item[1]]
        categories = [item[1] for item in user_data if item[0] and item[1]]

        # Yeterli veri olup olmadığını kontrol et (eşik değeri 10)
        if len(descriptions) < 10:
            messagebox.showwarning("Yapay Zeka Eğitimi",
                                   "Yapay zeka modelini yeniden eğitmek için yeterli sayıda işlem (en az 10 adet) bulunmamaktadır. Model sentetik verilerle desteklenecektir.")
            # Yeterli veri yoksa, AIPredictor'ın kendi sentetik verilerini kullanmasını sağlayacak şekilde tetikle
            self.ai_predictor._load_or_retrain_model_with_user_data()
        else:
            messagebox.showinfo("Yapay Zeka Eğitimi",
                                "Yapay zeka modeli kullanıcı verileriyle yeniden eğitiliyor. Bu işlem biraz zaman alabilir...")
            self.ai_predictor.retrain_model(descriptions, categories)
            messagebox.showinfo("Yapay Zeka Eğitimi", "Yapay zeka modeli başarıyla yeniden eğitildi!")
            self.kategorileri_yukle()  # Yeniden eğitimde yeni kategoriler de oluştuysa combobox'ı güncelle

    # --- Raporlama Fonksiyonları ---
    def rapor_olustur(self):
        """Kullanıcının seçtiği formatta rapor oluşturur."""
        # Filtreleme kriterlerini al
        tur = self.filtre_tur_var.get()
        kategori = self.filtre_kategori_var.get()
        bas_tarih = self.bas_tarih_entry.get_date().strftime("%Y-%m-%d") if self.bas_tarih_entry.get() else ""
        bit_tarih = self.bit_tarih_entry.get_date().strftime("%Y-%m-%d") if self.bit_tarih_entry.get() else ""
        arama_terimi = self.arama_entry.get().strip()

        try:
            # Raporlanacak verileri veritabanından çek
            rapor_verileri = self.db_manager.get_transactions(self.kullanici_id, tur, kategori, bas_tarih, bit_tarih,
                                                              arama_terimi)
        except Exception as e:
            messagebox.showerror("Veritabanı Hatası", f"Rapor verileri çekilirken hata oluştu: {e}")
            return

        if not rapor_verileri:
            messagebox.showinfo("Bilgi", "Seçilen kriterlere göre rapor oluşturulacak veri bulunamadı.")
            return

        # Rapor formatı seçim penceresi oluştur
        rapor_secenekleri_pencere = tk.Toplevel(self.root)
        rapor_secenekleri_pencere.title("Rapor Kaydet")
        rapor_secenekleri_pencere.geometry("300x150")
        rapor_secenekleri_pencere.transient(self.root)  # Ana pencereye bağlı kal
        rapor_secenekleri_pencere.grab_set()  # Pencere odaklanmış kalır

        ttk.Label(rapor_secenekleri_pencere, text="Raporu hangi formatta kaydetmek istersiniz?").pack(pady=10)

        # Filtre bilgilerini rapor başlığına eklemek için hazırla
        filter_info = {
            "tur": tur,
            "kategori": kategori,
            "bas_tarih": bas_tarih,
            "bit_tarih": bit_tarih,
            "arama_terimi": arama_terimi
        }

        # Excel ve PDF rapor butonları
        ttk.Button(rapor_secenekleri_pencere, text="Excel Olarak Kaydet",
                   command=lambda: self._excel_rapor_olustur(rapor_verileri, filter_info,
                                                             rapor_secenekleri_pencere)).pack(pady=5)

        ttk.Button(rapor_secenekleri_pencere, text="PDF Olarak Kaydet",
                   command=lambda: self._pdf_rapor_olustur(rapor_verileri, filter_info,
                                                           rapor_secenekleri_pencere)).pack(pady=5)

    def _excel_rapor_olustur(self, data, filter_info, parent_window):
        """Excel raporunu oluşturur ve kaydeder."""
        parent_window.destroy()  # Seçim penceresini kapat

        if not data:
            messagebox.showwarning("Uyarı", "Excel raporu oluşturulacak veri bulunamadı.")
            return

        # Dosya kaydetme diyaloğu
        file_path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel Dosyaları", "*.xlsx")],
            title="Excel Raporu Kaydet"
        )
        if not file_path:  # Kullanıcı iptal ettiyse
            return

        try:
            self.pdf_generator.generate_excel_report(data, file_path)  # PDFGenerator'daki metodu kullan
            messagebox.showinfo("Başarılı", f"Excel raporu başarıyla kaydedildi:\n{file_path}")
        except Exception as e:
            messagebox.showerror("Hata", f"Excel raporu oluşturulurken hata oluştu: {e}")

    def _pdf_rapor_olustur(self, data, filter_info, parent_window):
        """PDF raporunu oluşturur ve kaydeder."""
        parent_window.destroy()  # Seçim penceresini kapat

        if not data:
            messagebox.showwarning("Uyarı", "PDF raporu oluşturulacak veri bulunamadı.")
            return

        # Dosya kaydetme diyaloğu
        file_path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF Dosyaları", "*.pdf")],
            title="PDF Raporu Kaydet"
        )
        if not file_path:  # Kullanıcı iptal ettiyse
            return

        try:
            self.pdf_generator.generate_pdf_report(data, file_path, self.username,
                                                   filter_info)  # PDFGenerator'daki metodu kullan
            messagebox.showinfo("Başarılı", f"PDF raporu başarıyla kaydedildi:\n{file_path}")
        except Exception as e:
            messagebox.showerror("Hata",
                                 f"PDF raporu oluşturulurken hata oluştu: {e}\nPDF kütüphanesi Türkçe karakter desteği için ek font ayarları gerektirebilir.")

    # --- Fatura/Teklif Fonksiyonları ---

    def belge_numarasi_olustur(self):
        """Fatura veya teklif için otomatik belge numarası oluşturur."""
        tur = self.fatura_tur_var.get()
        current_year = datetime.now().year

        # Kullanıcının en son kullandığı fatura/teklif numaralarını al
        last_nums = self.db_manager.get_user_invoice_offer_nums(self.kullanici_id)
        last_invoice_num = last_nums[0] if last_nums else 0
        last_offer_num = last_nums[1] if last_nums else 0

        belge_no = ""
        if tur == "Fatura":
            new_num = last_invoice_num + 1
            belge_no = f"FTR-{current_year}-{new_num:05d}"  # Örn: FTR-2023-00001
            self.db_manager.update_user_invoice_offer_num(self.kullanici_id, invoice_num=new_num)
        elif tur == "Teklif":
            new_num = last_offer_num + 1
            belge_no = f"TKLF-{current_year}-{new_num:05d}"  # Örn: TKLF-2023-00001
            self.db_manager.update_user_invoice_offer_num(self.kullanici_id, offer_num=new_num)

        # Belge numarası giriş alanını güncelle
        self.belge_numarasi_entry.config(state="normal")  # Yazılabilir hale getir
        self.belge_numarasi_entry.delete(0, tk.END)
        self.belge_numarasi_entry.insert(0, belge_no)
        self.belge_numarasi_entry.config(state="readonly")  # Tekrar sadece okunabilir yap

    def _fatura_tur_secildi(self, event):
        """Fatura/Teklif türü seçildiğinde ilgili alanları günceller."""
        selected_type = self.fatura_tur_var.get()
        if selected_type == "Fatura":
            self.fatura_durum_var.set("Taslak")  # Fatura varsayılan durum
        elif selected_type == "Teklif":
            self.fatura_durum_var.set("Taslak")  # Teklif varsayılan durum

        # Belge numarası alanını temizle ve okunabilir yap
        self.belge_numarasi_entry.config(state="normal")
        self.belge_numarasi_entry.delete(0, tk.END)
        self.belge_numarasi_entry.config(state="readonly")

    def _fatura_tutari_hesapla(self, event=None):
        """Fatura/teklif kalemlerindeki tutarları ve KDV'yi hesaplar."""
        items_text = self.fatura_urun_hizmetler_text.get("1.0", tk.END).strip()
        total_kdv_haric = 0.0
        total_kdv = 0.0

        if items_text:
            for line in items_text.split('\n'):
                parts = [p.strip() for p in line.split(',') if p.strip()]
                # Beklenen format: Ad,Miktar,Fiyat,KDV%
                if len(parts) == 4:
                    try:
                        quantity = float(parts[1].replace(",", "."))
                        price = float(parts[2].replace(",", "."))
                        kdv_orani = float(parts[3].replace(",", "."))

                        item_subtotal = quantity * price
                        item_kdv_amount = item_subtotal * (kdv_orani / 100.0)

                        total_kdv_haric += item_subtotal
                        total_kdv += item_kdv_amount
                    except ValueError:
                        pass  # Geçersiz satırları atla
                elif len(parts) == 3:  # Eski format desteği: Ad,Miktar,Fiyat (KDV'siz)
                    try:
                        quantity = float(parts[1].replace(",", "."))
                        price = float(parts[2].replace(",", "."))
                        item_subtotal = quantity * price
                        total_kdv_haric += item_subtotal
                    except ValueError:
                        pass

        genel_toplam = total_kdv_haric + total_kdv

        # Hesaplanan değerleri giriş alanlarına yaz ve salt okunur yap
        self.fatura_kdv_haric_toplam_entry.config(state="normal")
        self.fatura_toplam_kdv_entry.config(state="normal")
        self.fatura_genel_toplam_entry.config(state="normal")

        self.fatura_kdv_haric_toplam_entry.delete(0, tk.END)
        self.fatura_kdv_haric_toplam_entry.insert(0, f"{total_kdv_haric:,.2f}".replace(".", ","))

        self.fatura_toplam_kdv_entry.delete(0, tk.END)
        self.fatura_toplam_kdv_entry.insert(0, f"{total_kdv:,.2f}".replace(".", ","))

        self.fatura_genel_toplam_entry.delete(0, tk.END)
        self.fatura_genel_toplam_entry.insert(0, f"{genel_toplam:,.2f}".replace(".", ","))

        self.fatura_kdv_haric_toplam_entry.config(state="readonly")
        self.fatura_toplam_kdv_entry.config(state="readonly")
        self.fatura_genel_toplam_entry.config(state="readonly")

    def fatura_urun_ekle_envanterden(self):
        """Envanterden seçilen ürünü fatura/teklif kalemlerine ekler."""
        selected_product_name = self.fatura_urun_sec_var.get()
        if not selected_product_name:
            messagebox.showwarning("Uyarı", "Lütfen envanterden bir ürün seçiniz.")
            return

        # Ürün verilerini veritabanından çek
        product_data = self.db_manager.get_product_by_name(selected_product_name, self.kullanici_id)

        if not product_data:
            messagebox.showerror("Hata", "Seçilen ürün envanterde bulunamadı.")
            return

        # product_data: (id, urun_adi, stok_miktari, alis_fiyati, satis_fiyati, kdv_orani)
        # Sadece satış fiyatı ve KDV oranı lazım
        _, urun_adi_db, _, _, satis_fiyati_db, kdv_orani_db = product_data

        current_text = self.fatura_urun_hizmetler_text.get("1.0", tk.END).strip()
        # Ürünü 'Ad,Miktar,Fiyat,KDV%' formatında ekle
        new_line = f"{urun_adi_db},1,{satis_fiyati_db:g},{kdv_orani_db:g}"

        if current_text:
            self.fatura_urun_hizmetler_text.insert(tk.END, "\n" + new_line)
        else:
            self.fatura_urun_hizmetler_text.insert(tk.END, new_line)

        self._fatura_tutari_hesapla()  # Toplamları yeniden hesapla

    def fatura_kaydet(self):
        """Yeni bir fatura/teklif kaydeder ve fatura ise envanter stoklarını günceller."""
        tur = self.fatura_tur_var.get()
        belge_numarasi = self.belge_numarasi_entry.get().strip()
        musteri_adi = self.fatura_musteri_var.get().strip()
        belge_tarihi = self.fatura_belge_tarih_entry.get_date().strftime("%Y-%m-%d")
        son_odeme_gecerlilik_tarihi = self.fatura_son_odeme_gecerlilik_tarih_entry.get_date().strftime("%Y-%m-%d")
        urun_hizmetler_text = self.fatura_urun_hizmetler_text.get("1.0", tk.END).strip()
        toplam_tutar_str = self.fatura_kdv_haric_toplam_entry.get().replace(".", "").replace(",", ".").replace("₺",
                                                                                                               "").strip()
        toplam_kdv_str = self.fatura_toplam_kdv_entry.get().replace(".", "").replace(",", ".").replace("₺", "").strip()
        notlar = self.fatura_notlar_text.get("1.0", tk.END).strip()
        durum = self.fatura_durum_var.get()

        if not all([tur, belge_numarasi, musteri_adi, belge_tarihi, son_odeme_gecerlilik_tarihi, urun_hizmetler_text,
                    toplam_tutar_str, durum]):
            messagebox.showerror("Hata", "Lütfen fatura/teklif için tüm gerekli alanları doldurun.")
            return

        try:
            toplam_tutar = float(toplam_tutar_str)
            toplam_kdv = float(toplam_kdv_str)
            if toplam_tutar < 0 or toplam_kdv < 0:
                messagebox.showerror("Hata", "Toplam tutarlar negatif olamaz.")
                return
        except ValueError:
            messagebox.showerror("Hata", "Geçersiz toplam tutar değeri. Lütfen sayı giriniz.")
            return

        # Belge numarasının benzersizliğini kontrol et
        if self.db_manager.check_belge_numarasi_exists(belge_numarasi, self.kullanici_id):
            messagebox.showerror("Hata",
                                 f"'{belge_numarasi}' belge numarası zaten mevcut. Lütfen yeni bir numara oluşturun veya farklı bir numara girin.")
            return

        urun_hizmetler_list = []
        for line in urun_hizmetler_text.split('\n'):
            parts = [p.strip() for p in line.split(',') if p.strip()]
            if len(parts) == 4:  # Ad, Miktar, Fiyat, KDV% formatı
                try:
                    quantity = float(parts[1].replace(",", "."))
                    price = float(parts[2].replace(",", "."))
                    kdv_orani = float(parts[3].replace(",", "."))
                    item_subtotal = quantity * price
                    item_kdv_amount = item_subtotal * (kdv_orani / 100.0)
                    urun_hizmetler_list.append({
                        "ad": parts[0],
                        "miktar": quantity,
                        "birim_fiyat": price,
                        "kdv_orani": kdv_orani,
                        "kdv_miktari": item_kdv_amount,
                        "ara_toplam": item_subtotal
                    })
                except ValueError:
                    messagebox.showwarning("Uyarı",
                                           f"Geçersiz ürün/hizmet satırı atlandı: {line}. Format 'Ad,Miktar,Fiyat,KDV%' olmalı.")
                    continue
            elif len(parts) == 3:  # Eski format desteği (KDV'siz)
                try:
                    quantity = float(parts[1].replace(",", "."))
                    price = float(parts[2].replace(",", "."))
                    item_subtotal = quantity * price
                    urun_hizmetler_list.append({
                        "ad": parts[0],
                        "miktar": quantity,
                        "birim_fiyat": price,
                        "kdv_orani": 0.0,
                        "kdv_miktari": 0.0,
                        "ara_toplam": item_subtotal
                    })
                except ValueError:
                    messagebox.showwarning("Uyarı",
                                           f"Geçersiz ürün/hizmet satırı atlandı: {line}. Format 'Ad,Miktar,Fiyat' olmalı.")
                    continue

        if not urun_hizmetler_list:
            messagebox.showerror("Hata", "Lütfen geçerli ürün/hizmet bilgileri giriniz (Ad,Miktar,Fiyat,KDV%).")
            return

        urun_hizmetler_json = json.dumps(urun_hizmetler_list, ensure_ascii=False)  # JSON formatına çevir

        try:
            # Fatura/teklifi veritabanına ekle
            self.db_manager.insert_invoice_offer(tur, belge_numarasi, musteri_adi, belge_tarihi,
                                                 son_odeme_gecerlilik_tarihi, urun_hizmetler_json, toplam_tutar,
                                                 toplam_kdv, notlar, durum, self.kullanici_id)

            # Eğer kaydedilen bir fatura ise, envanterden stok düşümü yap
            if tur == "Fatura":
                for item in urun_hizmetler_list:
                    product_data = self.db_manager.get_product_by_name(item['ad'], self.kullanici_id)
                    if product_data:
                        product_id, _, current_stock, _, _, _ = product_data  # id, urun_adi, stok_miktari, alis_fiyati, satis_fiyati, kdv_orani
                        new_stock = current_stock - item['miktar']
                        if new_stock < 0:
                            messagebox.showwarning("Stok Uyarısı",
                                                   f"'{item['ad']}' ürünü için stok miktarı eksiye düştü! Yeni stok: {new_stock}")
                        self.db_manager.update_product_stock(product_id, new_stock)

            messagebox.showinfo("Başarılı", f"{tur} başarıyla kaydedildi.")
            self.fatura_temizle()  # Fatura/Teklif alanlarını temizle
            self.listele_fatura_teklifler()  # Fatura/Teklif listesini güncelle
            self.listele_urunler()  # Ürünler listesini güncelle (stok değişimi için)
        except Exception as e:
            messagebox.showerror("Hata", f"{tur} kaydetme hatası: {e}")

    def fatura_guncelle(self):
        """Mevcut bir fatura/teklifi günceller ve envanter stoklarını ayarlar."""
        if self.selected_invoice_id is None:
            messagebox.showwarning("Uyarı", "Lütfen güncellemek istediğiniz fatura/teklifi seçiniz.")
            return

        # Eski fatura/teklif verilerini çek (stok düzeltmesi için)
        old_invoice_data = self.db_manager.get_invoice_offer_by_id(self.selected_invoice_id, self.kullanici_id)
        # old_invoice_data artık 12 elemanlı bir tuple: (id, tur, belge_numarasi, musteri_adi, belge_tarihi, son_odeme_gecerlilik_tarihi, urun_hizmetler_json, toplam_tutar, toplam_kdv, notlar, durum, kullanici_id)
        old_tur = old_invoice_data[1]  # Eski belge türü
        old_urun_hizmetler_list = json.loads(old_invoice_data[6]) if old_invoice_data[
            6] else []  # Eski ürün/hizmet listesi

        # Güncel form verilerini al
        tur = self.fatura_tur_var.get()
        belge_numarasi = self.belge_numarasi_entry.get().strip()
        musteri_adi = self.fatura_musteri_var.get().strip()
        belge_tarihi = self.fatura_belge_tarih_entry.get_date().strftime("%Y-%m-%d")
        son_odeme_gecerlilik_tarihi = self.fatura_son_odeme_gecerlilik_tarih_entry.get_date().strftime("%Y-%m-%d")
        urun_hizmetler_text = self.fatura_urun_hizmetler_text.get("1.0", tk.END).strip()
        toplam_tutar_str = self.fatura_kdv_haric_toplam_entry.get().replace(".", "").replace(",", ".").replace("₺",
                                                                                                               "").strip()
        toplam_kdv_str = self.fatura_toplam_kdv_entry.get().replace(".", "").replace(",", ".").replace("₺", "").strip()
        notlar = self.fatura_notlar_text.get("1.0", tk.END).strip()
        durum = self.fatura_durum_var.get()

        if not all([tur, belge_numarasi, musteri_adi, belge_tarihi, son_odeme_gecerlilik_tarihi, urun_hizmetler_text,
                    toplam_tutar_str, durum]):
            messagebox.showerror("Hata", "Lütfen fatura/teklif için tüm gerekli alanları doldurun.")
            return

        try:
            toplam_tutar = float(toplam_tutar_str)
            toplam_kdv = float(toplam_kdv_str)
            if toplam_tutar < 0 or toplam_kdv < 0:
                messagebox.showerror("Hata", "Toplam tutarlar negatif olamaz.")
                return
        except ValueError:
            messagebox.showerror("Hata", "Geçersiz toplam tutar değeri. Lütfen sayı giriniz.")
            return

        urun_hizmetler_list = []
        for line in urun_hizmetler_text.split('\n'):
            parts = [p.strip() for p in line.split(',') if p.strip()]
            if len(parts) == 4:  # Ad, Miktar, Fiyat, KDV% formatı
                try:
                    quantity = float(parts[1].replace(",", "."))
                    price = float(parts[2].replace(",", "."))
                    kdv_orani = float(parts[3].replace(",", "."))
                    item_subtotal = quantity * price
                    item_kdv_amount = item_subtotal * (kdv_orani / 100.0)
                    urun_hizmetler_list.append({
                        "ad": parts[0],
                        "miktar": quantity,
                        "birim_fiyat": price,
                        "kdv_orani": kdv_orani,
                        "kdv_miktari": item_kdv_amount,
                        "ara_toplam": item_subtotal
                    })
                except ValueError:
                    messagebox.showwarning("Uyarı",
                                           f"Geçersiz ürün/hizmet satırı atlandı: {line}. Format 'Ad,Miktar,Fiyat,KDV%' olmalı.")
                    continue
            elif len(parts) == 3:  # Eski formatı da destekle (KDV'siz)
                try:
                    quantity = float(parts[1].replace(",", "."))
                    price = float(parts[2].replace(",", "."))
                    item_subtotal = quantity * price
                    urun_hizmetler_list.append({
                        "ad": parts[0],
                        "miktar": quantity,
                        "birim_fiyat": price,
                        "kdv_orani": 0.0,
                        "kdv_miktari": 0.0,
                        "ara_toplam": item_subtotal
                    })
                except ValueError:
                    messagebox.showwarning("Uyarı",
                                           f"Geçersiz ürün/hizmet satırı atlandı: {line}. Format 'Ad,Miktar,Fiyat' olmalı.")
                    continue

        if not urun_hizmetler_list:
            messagebox.showerror("Hata", "Lütfen geçerli ürün/hizmet bilgileri giriniz (Ad,Miktar,Fiyat,KDV%).")
            return

        urun_hizmetler_json = json.dumps(urun_hizmetler_list, ensure_ascii=False)

        try:
            # Fatura/teklifi veritabanında güncelle
            self.db_manager.update_invoice_offer(self.selected_invoice_id, tur, belge_numarasi, musteri_adi,
                                                 belge_tarihi, son_odeme_gecerlilik_tarihi, urun_hizmetler_json,
                                                 toplam_tutar, toplam_kdv, notlar, durum, self.kullanici_id)

            # --- Stok Güncelleme Mantığı ---
            # Eğer eski belge fatura idiyse, eski ürün miktarlarını stoğa geri ekle
            if old_tur == "Fatura":
                for item in old_urun_hizmetler_list:
                    product_data = self.db_manager.get_product_by_name(item['ad'], self.kullanici_id)
                    if product_data:
                        product_id, _, current_stock, _, _, _ = product_data
                        self.db_manager.update_product_stock(product_id, current_stock + item['miktar'])

            # Eğer yeni belge fatura ise, yeni ürün miktarlarını stoktan düş
            if tur == "Fatura":
                for item in urun_hizmetler_list:
                    product_data = self.db_manager.get_product_by_name(item['ad'], self.kullanici_id)
                    if product_data:
                        product_id, _, current_stock, _, _, _ = product_data
                        new_stock = current_stock - item['miktar']
                        if new_stock < 0:
                            messagebox.showwarning("Stok Uyarısı",
                                                   f"'{item['ad']}' ürünü için stok miktarı eksiye düştü! Yeni stok: {new_stock}")
                        self.db_manager.update_product_stock(product_id, new_stock)

            messagebox.showinfo("Başarılı", f"{tur} başarıyla güncellendi.")
            self.fatura_temizle()
            self.listele_fatura_teklifler()
            self.listele_urunler()
        except Exception as e:
            messagebox.showerror("Hata", f"{tur} güncelleme hatası: {e}")

    def fatura_sil(self):
        """Seçili fatura/teklifi siler ve fatura ise envanter stoklarını geri yükler."""
        if self.selected_invoice_id is None:
            messagebox.showwarning("Uyarı", "Lütfen silmek istediğiniz fatura/teklifi seçiniz.")
            return

        # Silinecek faturanın/teklifin bilgilerini al
        invoice_to_delete_data = self.db_manager.get_invoice_offer_by_id(self.selected_invoice_id, self.kullanici_id)

        if not invoice_to_delete_data:
            messagebox.showerror("Hata", "Silinecek fatura/teklif bulunamadı.")
            return

        tur_to_delete = invoice_to_delete_data[1]  # Tür bilgisi
        urun_hizmetler_json_to_delete = invoice_to_delete_data[6]  # Ürün/hizmetler JSON bilgisi
        urun_hizmetler_list_to_delete = json.loads(
            urun_hizmetler_json_to_delete) if urun_hizmetler_json_to_delete else []

        onay = messagebox.askyesno("Onay", "Seçili fatura/teklifi silmek istediğinize emin misiniz?")
        if onay:
            try:
                self.db_manager.delete_invoice_offer(self.selected_invoice_id, self.kullanici_id)

                # Eğer silinen bir fatura ise, ürün miktarlarını envantere geri ekle
                if tur_to_delete == "Fatura":
                    for item in urun_hizmetler_list_to_delete:
                        product_data = self.db_manager.get_product_by_name(item['ad'], self.kullanici_id)
                        if product_data:
                            product_id, _, current_stock, _, _, _ = product_data
                            self.db_manager.update_product_stock(product_id, current_stock + item['miktar'])

                messagebox.showinfo("Başarılı", "Fatura/Teklif başarıyla silindi.")
                self.fatura_temizle()
                self.listele_fatura_teklifler()
                self.listele_urunler()
            except Exception as e:
                messagebox.showerror("Hata", f"Fatura/Teklif silme hatası: {e}")

    def fatura_temizle(self):
        """Fatura/teklif giriş alanlarını temizler."""
        self.fatura_tur_var.set("Fatura")
        self.belge_numarasi_entry.config(state="normal")
        self.belge_numarasi_entry.delete(0, tk.END)
        self.belge_numarasi_entry.config(state="readonly")
        self.fatura_musteri_var.set("")
        self.fatura_belge_tarih_entry.set_date(datetime.now().strftime("%Y-%m-%d"))
        self.fatura_son_odeme_gecerlilik_tarih_entry.set_date(datetime.now().strftime("%Y-%m-%d"))
        self.fatura_urun_hizmetler_text.delete("1.0", tk.END)  # Text widget'ı temizle

        # Salt okunur toplam alanlarını normal hale getirip temizle ve tekrar salt okunur yap
        self.fatura_kdv_haric_toplam_entry.config(state="normal")
        self.fatura_kdv_haric_toplam_entry.delete(0, tk.END)
        self.fatura_kdv_haric_toplam_entry.config(state="readonly")
        self.fatura_toplam_kdv_entry.config(state="normal")
        self.fatura_toplam_kdv_entry.delete(0, tk.END)
        self.fatura_toplam_kdv_entry.config(state="readonly")
        self.fatura_genel_toplam_entry.config(state="normal")
        self.fatura_genel_toplam_entry.delete(0, tk.END)
        self.fatura_genel_toplam_entry.config(state="readonly")

        self.fatura_notlar_text.delete("1.0", tk.END)
        self.fatura_durum_var.set("Taslak")
        self.selected_invoice_id = None  # Seçili ID'yi sıfırla
        self.fatura_urun_sec_var.set("")  # Ürün seçimini temizle

    def listele_fatura_teklifler(self):
        """Fatura/teklifleri listeler."""
        for row in self.fatura_liste.get_children():
            self.fatura_liste.delete(row)

        try:
            veriler = self.db_manager.get_invoice_offers(self.kullanici_id)
            for veri in veriler:
                formatted_veri = list(veri)
                # Miktar ve KDV değerlerini formatla
                formatted_veri[4] = f"{veri[4]:,.2f} ₺".replace(".", ",")
                formatted_veri[5] = f"{veri[5]:,.2f} ₺".replace(".", ",")
                formatted_veri[6] = f"{veri[6]:,.2f} ₺".replace(".", ",")
                self.fatura_liste.insert("", tk.END, values=formatted_veri)
        except Exception as e:
            messagebox.showerror("Veritabanı Hatası", f"Fatura/Teklif verileri çekilirken hata oluştu: {e}")

    def fatura_liste_secildi(self, event):
        """Fatura/teklif listesinden bir öğe seçildiğinde giriş alanlarını doldurur."""
        selected_items = self.fatura_liste.selection()
        if selected_items:
            selected_item = selected_items[0]
            values = self.fatura_liste.item(selected_item, "values")
            self.selected_invoice_id = values[0]  # Seçili fatura ID'si

            fatura_data = self.db_manager.get_invoice_offer_by_id(self.selected_invoice_id, self.kullanici_id)

            if fatura_data:
                # database_manager'daki get_invoice_offer_by_id metodundan dönen 12 değeri al
                (id, tur, belge_numarasi, musteri_adi, belge_tarihi_str, son_odeme_gecerlilik_tarihi_str,
                 urun_hizmetler_json, toplam_tutar, toplam_kdv, notlar, durum, kullanici_id) = fatura_data

                self.fatura_tur_var.set(tur)

                # Belge numarası alanını güncelle ve salt okunur yap
                self.belge_numarasi_entry.config(state="normal")
                self.belge_numarasi_entry.delete(0, tk.END)
                self.belge_numarasi_entry.insert(0, belge_numarasi)
                self.belge_numarasi_entry.config(state="readonly")

                self.fatura_musteri_var.set(musteri_adi)  # Müşteri adını ayarla

                try:
                    # Tarihleri DateEntry formatına dönüştür
                    self.fatura_belge_tarih_entry.set_date(datetime.strptime(belge_tarihi_str, "%Y-%m-%d").date())
                    self.fatura_son_odeme_gecerlilik_tarih_entry.set_date(
                        datetime.strptime(son_odeme_gecerlilik_tarihi_str, "%Y-%m-%d").date())
                except ValueError:
                    self.fatura_belge_tarih_entry.set_date(datetime.now().date())
                    self.fatura_son_odeme_gecerlilik_tarih_entry.set_date(datetime.now().date())

                # Ürün/hizmetler JSON'ını ayrıştır ve Text widget'ına yaz
                urun_hizmetler_list = json.loads(urun_hizmetler_json)
                urun_hizmetler_text_content = ""
                for item in urun_hizmetler_list:
                    # Sayısal değerleri string'e dönüştürürken virgül kullan ve ondalık basamakları koru
                    miktar = f"{item.get('miktar', 0):g}".replace(".", ",")
                    birim_fiyat = f"{item.get('birim_fiyat', 0):g}".replace(".", ",")
                    kdv_orani = f"{item.get('kdv_orani', 0):g}".replace(".", ",")

                    urun_hizmetler_text_content += f"{item.get('ad', '')},{miktar},{birim_fiyat},{kdv_orani}\n"

                self.fatura_urun_hizmetler_text.delete("1.0", tk.END)
                self.fatura_urun_hizmetler_text.insert("1.0", urun_hizmetler_text_content.strip())

                # Toplam tutar alanlarını güncelle ve salt okunur yap
                self.fatura_kdv_haric_toplam_entry.config(state="normal")
                self.fatura_kdv_haric_toplam_entry.delete(0, tk.END)
                self.fatura_kdv_haric_toplam_entry.insert(0, f"{toplam_tutar:,.2f}".replace(".", ","))
                self.fatura_kdv_haric_toplam_entry.config(state="readonly")

                self.fatura_toplam_kdv_entry.config(state="normal")
                self.fatura_toplam_kdv_entry.delete(0, tk.END)
                self.fatura_toplam_kdv_entry.insert(0, f"{toplam_kdv:,.2f}".replace(".", ","))
                self.fatura_toplam_kdv_entry.config(state="readonly")

                self.fatura_genel_toplam_entry.config(state="normal")
                self.fatura_genel_toplam_entry.delete(0, tk.END)
                self.fatura_genel_toplam_entry.insert(0, f"{(toplam_tutar + toplam_kdv):,.2f}".replace(".", ","))
                self.fatura_genel_toplam_entry.config(state="readonly")

                self.fatura_notlar_text.delete("1.0", tk.END)
                self.fatura_notlar_text.insert("1.0", notlar)
                self.fatura_durum_var.set(durum)
        else:
            self.selected_invoice_id = None
            self.fatura_temizle()

    def fatura_pdf_olustur(self):
        """Seçili fatura/teklif için PDF oluşturur ve kaydeder."""
        if self.selected_invoice_id is None:
            messagebox.showwarning("Uyarı", "Lütfen PDF'ini oluşturmak istediğiniz fatura/teklifi seçiniz.")
            return

        fatura_data = self.db_manager.get_invoice_offer_by_id(self.selected_invoice_id, self.kullanici_id)

        if not fatura_data:
            messagebox.showerror("Hata", "Seçilen fatura/teklif bulunamadı.")
            return

        # DatabaseManager'dan dönen verinin 12 elemanlı olduğundan emin ol
        if len(fatura_data) != 12:
            messagebox.showerror("Hata",
                                 f"Fatura verisi eksik veya yanlış formatta. PDF oluşturulamıyor. Beklenen 12, alınan {len(fatura_data)} değer.")
            return

        musteri_adi = fatura_data[3]  # Müşteri adını al
        customer_info_full = self.db_manager.get_customer_by_name(musteri_adi, self.kullanici_id)

        # customer_info_full (id, musteri_adi, adres, telefon, email)
        # PDFGenerator'a sadece adres, telefon, email (indeks 2, 3, 4) göndermeliyiz
        # Güvenli erişim için kontrol ekle
        customer_info_for_pdf = (
            customer_info_full[2] if customer_info_full and len(customer_info_full) > 2 else None,
            customer_info_full[3] if customer_info_full and len(customer_info_full) > 3 else None,
            customer_info_full[4] if customer_info_full and len(customer_info_full) > 4 else None
        )

        # Dosya kaydetme diyaloğu
        file_path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF Dosyaları", "*.pdf")],
            title=f"{fatura_data[1]} Kaydet",  # Başlıkta fatura/teklif türünü göster
            initialfile=f"{fatura_data[2]}_{musteri_adi}.pdf"  # Başlangıç dosya adı: BelgeNo_MüşteriAdı.pdf
        )
        if not file_path:
            return

        try:
            self.pdf_generator.generate_invoice_offer_pdf(fatura_data, customer_info_for_pdf, file_path)
            messagebox.showinfo("Başarılı", f"{fatura_data[1]} PDF'i başarıyla kaydedildi:\n{file_path}")
        except Exception as e:
            messagebox.showerror("Hata",
                                 f"PDF raporu oluşturulurken hata oluştu: {e}\nPDF kütüphanesi Türkçe karakter desteği için ek font ayarları gerektirebilir. Lütfen 'veriler.db' dosyanızı silip tekrar deneyin.")

    # --- Müşteri Yönetimi Fonksiyonları ---
    def listele_musteriler(self):
        """Müşterileri veritabanından yükler ve ilgili combobox'ları günceller."""
        for row in self.musteri_liste.get_children():
            self.musteri_liste.delete(row)

        try:
            musteriler = self.db_manager.get_customers(self.kullanici_id)

            musteri_adlari = []
            for musteri in musteriler:
                self.musteri_liste.insert("", tk.END, values=musteri)
                musteri_adlari.append(musteri[1])  # Müşteri adını fatura combobox'ı için sakla

            # Fatura/Teklif ekranındaki müşteri combobox'ını güncelle
            self.fatura_musteri_combobox['values'] = musteri_adlari
            if musteri_adlari:
                self.fatura_musteri_var.set(musteri_adlari[0])  # İlk müşteriyi varsayılan olarak seç
            else:
                self.fatura_musteri_var.set("")  # Müşteri yoksa boş bırak

        except Exception as e:
            messagebox.showerror("Veritabanı Hatası", f"Müşteriler yüklenirken hata oluştu: {e}")

    def musteri_ekle(self):
        """Yeni bir müşteri ekler."""
        musteri_adi = self.musteri_adi_entry.get().strip()
        adres = self.musteri_adres_entry.get().strip()
        telefon = self.musteri_telefon_entry.get().strip()
        email = self.musteri_email_entry.get().strip()

        if not musteri_adi:
            messagebox.showerror("Hata", "Müşteri adı boş bırakılamaz.")
            return

        try:
            # Müşteri adının benzersizliğini kontrol et
            if self.db_manager.get_customer_by_name(musteri_adi, self.kullanici_id):
                messagebox.showerror("Hata", "Bu müşteri adı zaten mevcut.")
                return

            self.db_manager.insert_customer(musteri_adi, adres, telefon, email, self.kullanici_id)
            messagebox.showinfo("Başarılı", "Müşteri başarıyla eklendi.")
            self.temizle_musteri()
            self.listele_musteriler()  # Müşteri listesini ve fatura combobox'ını güncelle
        except Exception as e:
            messagebox.showerror("Hata", f"Müşteri eklenirken hata oluştu: {e}")

    def musteri_guncelle(self):
        """Mevcut bir müşteriyi günceller."""
        if self.selected_customer_id is None:
            messagebox.showwarning("Uyarı", "Lütfen güncellemek istediğiniz müşteriyi seçiniz.")
            return

        musteri_adi = self.musteri_adi_entry.get().strip()
        adres = self.musteri_adres_entry.get().strip()
        telefon = self.musteri_telefon_entry.get().strip()
        email = self.musteri_email_entry.get().strip()

        if not musteri_adi:
            messagebox.showerror("Hata", "Müşteri adı boş bırakılamaz.")
            return

        try:
            # Mevcut müşteri adını al (güncelleme sonrası ad değişimi için)
            current_musteri_info = self.db_manager.get_customer_by_id(self.selected_customer_id)
            current_musteri_adi = current_musteri_info[0] if current_musteri_info else ""

            # Eğer müşteri adı değiştiyse ve yeni ad zaten varsa hata ver
            if musteri_adi != current_musteri_adi:
                if self.db_manager.get_customer_by_name(musteri_adi, self.kullanici_id):
                    messagebox.showerror("Hata", "Bu müşteri adı zaten mevcut.")
                    return

            self.db_manager.update_customer(self.selected_customer_id, musteri_adi, adres, telefon, email,
                                            self.kullanici_id)

            # Müşteri adı değiştiyse, faturalardaki eski müşteri adlarını yeni adla güncelle
            if musteri_adi != current_musteri_adi:
                self.db_manager.update_invoice_customer_name(current_musteri_adi, musteri_adi, self.kullanici_id)

            messagebox.showinfo("Başarılı", "Müşteri başarıyla güncellendi.")
            self.temizle_musteri()
            self.listele_musteriler()  # Müşteri listesini ve fatura combobox'ını güncelle
            self.listele_fatura_teklifler()  # Fatura/Teklif listesini güncelle (müşteri adı değişimi yansısın)

        except Exception as e:
            messagebox.showerror("Hata", f"Müşteri güncellenirken hata oluştu: {e}")

    def musteri_sil(self):
        """Seçili müşteriyi siler."""
        if self.selected_customer_id is None:
            messagebox.showwarning("Uyarı", "Lütfen silmek istediğiniz müşteriyi seçiniz.")
            return

        musteri_adi_data = self.db_manager.get_customer_by_id(self.selected_customer_id)
        musteri_adi = musteri_adi_data[0] if musteri_adi_data else ""

        # Bu müşterinin kaç fatura/teklifte kullanıldığını kontrol et
        fatura_sayisi = self.db_manager.count_invoices_by_customer(musteri_adi, self.kullanici_id)

        onay_mesaji = ""
        if fatura_sayisi > 0:
            onay_mesaji = f"'{musteri_adi}' müşterisi {fatura_sayisi} adet fatura/teklifte kullanılmaktadır. Bu müşteriyi silerseniz, bu belgelerdeki müşteri adı boş kalacaktır. Emin misiniz?"
        else:
            onay_mesaji = f"'{musteri_adi}' müşterisini silmek istediğinize emin misiniz?"

        onay = messagebox.askyesno("Onay", onay_mesaji)

        if onay:
            try:
                # Müşterinin kullanıldığı fatura/tekliflerde müşteri adını "Silinmiş Müşteri" yap
                self.db_manager.update_invoice_customer_name(musteri_adi, 'Silinmiş Müşteri', self.kullanici_id)
                self.db_manager.delete_customer(self.selected_customer_id, self.kullanici_id)
                messagebox.showinfo("Başarılı", "Müşteri başarıyla silindi.")
                self.temizle_musteri()
                self.listele_musteriler()  # Müşteri listesini ve fatura combobox'ını güncelle
                self.listele_fatura_teklifler()  # Fatura/Teklif listesini güncelle
            except Exception as e:
                messagebox.showerror("Hata", f"Müşteri silinirken hata oluştu: {e}")

    def musteri_liste_secildi(self, event):
        """Müşteri listesinden bir öğe seçildiğinde giriş alanlarını doldurur."""
        selected_items = self.musteri_liste.selection()
        if selected_items:
            selected_item = selected_items[0]
            values = self.musteri_liste.item(selected_item, "values")
            self.selected_customer_id = values[0]  # Seçili müşteri ID'si

            # Giriş alanlarını seçilen verilerle doldur
            self.musteri_adi_entry.delete(0, tk.END)
            self.musteri_adi_entry.insert(0, values[1])
            self.musteri_adres_entry.delete(0, tk.END)
            self.musteri_adres_entry.insert(0, values[2])
            self.musteri_telefon_entry.delete(0, tk.END)
            self.musteri_telefon_entry.insert(0, values[3])
            self.musteri_email_entry.delete(0, tk.END)
            self.musteri_email_entry.insert(0, values[4])
        else:
            self.selected_customer_id = None
            self.temizle_musteri()

    def temizle_musteri(self):
        """Müşteri giriş alanlarını temizler."""
        self.musteri_adi_entry.delete(0, tk.END)
        self.musteri_adres_entry.delete(0, tk.END)
        self.musteri_telefon_entry.delete(0, tk.END)
        self.musteri_email_entry.delete(0, tk.END)
        self.selected_customer_id = None

    # --- Envanter Yönetimi Fonksiyonları ---
    def listele_urunler(self):
        """Ürünleri veritabanından yükler ve ilgili combobox'ları günceller."""
        for row in self.urun_liste.get_children():
            self.urun_liste.delete(row)

        try:
            urunler = self.db_manager.get_products(self.kullanici_id)

            urun_adlari = []
            for urun in urunler:
                formatted_urun = list(urun)
                # Sayısal değerleri formatla (virgül ve ondalık basamaklar)
                formatted_urun[2] = f"{urun[2]:g}".replace(".", ",")  # Stok miktarı (tam sayı veya ondalık)
                formatted_urun[3] = f"{urun[3]:,.2f}".replace(".", ",")  # Alış fiyatı
                formatted_urun[4] = f"{urun[4]:,.2f}".replace(".", ",")  # Satış fiyatı
                formatted_urun[5] = f"{urun[5]:g}".replace(".", ",")  # KDV oranı
                self.urun_liste.insert("", tk.END, values=formatted_urun)
                urun_adlari.append(urun[1])  # Ürün adını fatura ürün seçimi için sakla

            # Fatura ekranındaki ürün seçim combobox'ını güncelle
            self.fatura_urun_sec_combobox['values'] = urun_adlari
            if urun_adlari:
                self.fatura_urun_sec_var.set(urun_adlari[0])  # İlk ürünü varsayılan olarak seç
            else:
                self.fatura_urun_sec_var.set("")


        except Exception as e:
            messagebox.showerror("Veritabanı Hatası", f"Ürünler yüklenirken hata oluştu: {e}")

    def urun_ekle(self):
        """Yeni bir ürün ekler."""
        urun_adi = self.urun_adi_entry.get().strip()
        stok_miktari_str = self.stok_miktari_entry.get().strip().replace(",", ".")
        alis_fiyati_str = self.alis_fiyati_entry.get().strip().replace(",", ".")
        satis_fiyati_str = self.satis_fiyati_entry.get().strip().replace(",", ".")
        kdv_orani_str = self.urun_kdv_orani_var.get().strip().replace(",", ".")

        if not urun_adi:
            messagebox.showerror("Hata", "Ürün adı boş bırakılamaz.")
            return

        try:
            stok_miktari = float(stok_miktari_str)
            alis_fiyati = float(alis_fiyati_str)
            satis_fiyati = float(satis_fiyati_str)
            kdv_orani = float(kdv_orani_str)

            if stok_miktari < 0 or alis_fiyati < 0 or satis_fiyati < 0 or kdv_orani < 0:
                messagebox.showerror("Hata", "Miktar ve fiyatlar negatif olamaz.")
                return
        except ValueError:
            messagebox.showerror("Hata", "Geçersiz sayısal değerler. Lütfen sayı giriniz.")
            return

        try:
            # Ürün adının benzersizliğini kontrol et
            if self.db_manager.get_product_by_name(urun_adi, self.kullanici_id):
                messagebox.showerror("Hata", "Bu ürün adı zaten mevcut.")
                return

            self.db_manager.insert_product(urun_adi, stok_miktari, alis_fiyati, satis_fiyati, kdv_orani,
                                           self.kullanici_id)
            messagebox.showinfo("Başarılı", "Ürün başarıyla eklendi.")
            self.temizle_urun()
            self.listele_urunler()  # Ürün listesini güncelle
        except Exception as e:
            messagebox.showerror("Hata", f"Ürün eklenirken hata oluştu: {e}")

    def urun_guncelle(self):
        """Mevcut bir ürünü günceller."""
        if self.selected_product_id is None:
            messagebox.showwarning("Uyarı", "Lütfen güncellemek istediğiniz ürünü seçiniz.")
            return

        urun_adi = self.urun_adi_entry.get().strip()
        stok_miktari_str = self.stok_miktari_entry.get().strip().replace(",", ".")
        alis_fiyati_str = self.alis_fiyati_entry.get().strip().replace(",", ".")
        satis_fiyati_str = self.satis_fiyati_entry.get().strip().replace(",", ".")
        kdv_orani_str = self.urun_kdv_orani_var.get().strip().replace(",", ".")

        if not urun_adi:
            messagebox.showerror("Hata", "Ürün adı boş bırakılamaz.")
            return

        try:
            stok_miktari = float(stok_miktari_str)
            alis_fiyati = float(alis_fiyati_str)
            satis_fiyati = float(satis_fiyati_str)
            kdv_orani = float(kdv_orani_str)

            if stok_miktari < 0 or alis_fiyati < 0 or satis_fiyati < 0 or kdv_orani < 0:
                messagebox.showerror("Hata", "Miktar ve fiyatlar negatif olamaz.")
                return
        except ValueError:
            messagebox.showerror("Hata", "Geçersiz sayısal değerler. Lütfen sayı giriniz.")
            return

        try:
            # Güncellenecek ürünün mevcut adını al (benzersizlik kontrolü için)
            current_urun_info = self.db_manager.get_product_by_name(
                self.urun_liste.item(self.urun_liste.selection()[0], "values")[1], self.kullanici_id)
            current_urun_adi = current_urun_info[1] if current_urun_info else ""

            # Eğer ürün adı değiştiyse ve yeni ad zaten varsa hata ver
            if urun_adi != current_urun_adi and self.db_manager.get_product_by_name(urun_adi, self.kullanici_id):
                messagebox.showerror("Hata", "Bu ürün adı zaten mevcut.")
                return

            self.db_manager.update_product(self.selected_product_id, urun_adi, stok_miktari, alis_fiyati, satis_fiyati,
                                           kdv_orani, self.kullanici_id)
            messagebox.showinfo("Başarılı", "Ürün başarıyla güncellendi.")
            self.temizle_urun()
            self.listele_urunler()
        except Exception as e:
            messagebox.showerror("Hata", f"Ürün güncellenirken hata oluştu: {e}")

    def urun_sil(self):
        """Seçili ürünü siler."""
        if self.selected_product_id is None:
            messagebox.showwarning("Uyarı", "Lütfen silmek istediğiniz ürünü seçiniz.")
            return

        # Silinecek ürünün adını al
        product_data = self.db_manager.get_product_by_name(
            self.urun_liste.item(self.urun_liste.selection()[0], "values")[1], self.kullanici_id)
        urun_adi = product_data[1] if product_data else ""

        onay = messagebox.askyesno("Onay",
                                   f"'{urun_adi}' ürününü silmek istediğinize emin misiniz? Bu ürün faturalarda yer alıyorsa, faturalardaki verilerde tutarsızlık olabilir.")
        if onay:
            try:
                self.db_manager.delete_product(self.selected_product_id, self.kullanici_id)
                messagebox.showinfo("Başarılı", "Ürün başarıyla silindi.")
                self.temizle_urun()
                self.listele_urunler()  # Ürün listesini güncelle
            except Exception as e:
                messagebox.showerror("Hata", f"Ürün silinirken hata oluştu: {e}")

    def urun_liste_secildi(self, event):
        """Ürün listesinden bir öğe seçildiğinde giriş alanlarını doldurur."""
        selected_items = self.urun_liste.selection()
        if selected_items:
            selected_item = selected_items[0]
            values = self.urun_liste.item(selected_item, "values")
            self.selected_product_id = values[0]  # Seçili ürün ID'si

            # Giriş alanlarını seçilen verilerle doldur
            self.urun_adi_entry.delete(0, tk.END)
            self.urun_adi_entry.insert(0, values[1])
            self.stok_miktari_entry.delete(0, tk.END)
            self.stok_miktari_entry.insert(0, values[2])  # Virgül formatında göster
            self.alis_fiyati_entry.delete(0, tk.END)
            self.alis_fiyati_entry.insert(0, values[3])  # Virgül formatında göster
            self.satis_fiyati_entry.delete(0, tk.END)
            self.satis_fiyati_entry.insert(0, values[4])  # Virgül formatında göster
            self.urun_kdv_orani_var.set(values[5])  # KDV oranı

        else:
            self.selected_product_id = None
            self.temizle_urun()

    def temizle_urun(self):
        """Ürün giriş alanlarını temizler."""
        self.urun_adi_entry.delete(0, tk.END)
        self.stok_miktari_entry.delete(0, tk.END)
        self.alis_fiyati_entry.delete(0, tk.END)
        self.satis_fiyati_entry.delete(0, tk.END)
        self.urun_kdv_orani_var.set("18")  # Varsayılan KDV oranı
        self.selected_product_id = None

    # --- Vergi Raporları Fonksiyonları ---
    def vergi_raporu_getir(self):
        """Belirli bir tarih aralığı için vergi raporu özetini getirir."""
        bas_tarih = self.vergi_bas_tarih_entry.get_date().strftime("%Y-%m-%d")
        bit_tarih = self.vergi_bit_tarih_entry.get_date().strftime("%Y-%m-%d")

        try:
            # Toplam satış KDV'sini veritabanından al
            toplam_satis_kdv = self.db_manager.get_total_sales_kdv(bas_tarih, bit_tarih, self.kullanici_id)

            # KDV oranlarına göre detaylı dağılım için faturaların JSON verilerini çek
            fatura_json_verileri = self.db_manager.get_invoice_jsons_for_tax_report(bas_tarih, bit_tarih,
                                                                                    self.kullanici_id)

            kdv_oran_detaylari = {}  # {KDV_Oranı: Toplam_KDV_Miktarı} sözlüğü

            for json_data_tuple in fatura_json_verileri:
                if json_data_tuple[0]:  # JSON verisi boş değilse
                    try:
                        items = json.loads(json_data_tuple[0])  # JSON'ı Python listesine dönüştür
                        for item in items:
                            kdv_orani = item.get('kdv_orani', 0.0)
                            kdv_miktari = item.get('kdv_miktari', 0.0)
                            # Her KDV oranı için toplam miktarı güncelle
                            kdv_oran_detaylari[kdv_orani] = kdv_oran_detaylari.get(kdv_orani, 0.0) + kdv_miktari
                    except json.JSONDecodeError:
                        print(f"Hata: Geçersiz JSON verisi: {json_data_tuple[0]}")
                        continue

            # Toplam Satış KDV'sini güncelle
            self.toplam_satis_kdv_label.config(text=f"₺{toplam_satis_kdv:,.2f}".replace(".", ","))

            # Toplam Alış KDV'si (şu an için manuel veya 0.0, gelecekte entegre edilebilir)
            toplam_alis_kdv = 0.0
            self.toplam_alis_kdv_label.config(text=f"₺{toplam_alis_kdv:,.2f}".replace(".", ","))

            # Ödenecek/İade Edilecek KDV farkını hesapla ve güncelle
            kdv_farki = toplam_satis_kdv - toplam_alis_kdv
            self.kdv_farki_label.config(text=f"₺{kdv_farki:,.2f}".replace(".", ","),
                                        foreground="red" if kdv_farki > 0 else "green")

            # KDV Detay Tablosunu güncelle
            for row in self.kdv_detay_liste.get_children():
                self.kdv_detay_liste.delete(row)

            # KDV detaylarını oranlara göre sırala ve tabloya ekle
            sorted_kdv_detaylari = sorted(kdv_oran_detaylari.items())
            for oran, tutar in sorted_kdv_detaylari:
                self.kdv_detay_liste.insert("", tk.END,
                                            values=(f"%{oran:g}".replace(".", ","), f"{tutar:,.2f}".replace(".", ",")))

        except Exception as e:
            messagebox.showerror("Hata", f"Vergi raporu getirilirken hata oluştu: {e}")

