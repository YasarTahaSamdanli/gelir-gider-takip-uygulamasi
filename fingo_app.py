# fingo_app.py
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog  # simpledialog eklendi
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
# Bu ayar, grafiklarda Türkçe karakterlerin düzgün görünmesini sağlar.
# 'Arial' fontu bulunamazsa 'DejaVu Sans' gibi genel bir fonta düşer.
plt.rcParams['font.sans-serif'] = [GLOBAL_REPORTLAB_FONT_NAME, 'DejaVu Sans']  # GLOBAL_REPORTLAB_FONT_NAME kullanıldı
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
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)  # Pencere kapatma olayını yakala

        # Seçili öğelerin ID'lerini saklamak için değişkenler
        self.selected_item_id = None  # Ana işlemler listesinden seçilen öğe
        self.selected_recurring_item_id = None  # Tekrarlayan işlemler listesinden seçilen öğe
        self.selected_category_id = None  # Kategori listesinden seçilen öğe
        self.selected_invoice_id = None  # Fatura/Teklif listesinden seçilen öğe
        self.selected_customer_id = None  # Müşteri listesinden seçilen öğe
        self.selected_product_id = None  # Ürün listesinden seçilen öğe
        self.selected_savings_goal_id = None  # YENİ: Tasarruf hedefi listesinden seçilen öğe

        # PDF oluşturucu örneğini başlatırken global font adını ilet
        # PDFGenerator init metodunun signature'ı güncellendiği için db_manager ve user_id de ekleniyor.
        self.pdf_generator = PDFGenerator(db_manager=self.db_manager, user_id=self.kullanici_id,
                                          font_name=GLOBAL_REPORTLAB_FONT_NAME)

        # Yapay zeka tahmincisini başlatırken db_manager ve user_id'yi ilet.
        # Bu sayede AI modeli kullanıcının kendi verileriyle eğitilebilir.
        self.ai_predictor = AIPredictor(db_manager=self.db_manager, user_id=self.kullanici_id)
        # Model yüklenemezse veya eğitilemezse hata mesajı vermesin, sonraki bir işlemde tekrar denenir
        try:
            self.ai_predictor.load_or_train_model()
        except Exception as e:
            print(f"AI modeli yüklenirken veya eğitilirken hata oluştu: {e}. Fonksiyonel olmayabilir.")

        # Uygulamanın ana arayüzünü oluştur
        self.arayuz_olustur()

        # Uygulama başlatıldığında ilk listelemeleri ve kontrolleri yap
        self.listele()  # Ana işlemleri listele
        self.listele_tekrar_eden_islemler()  # Tekrarlayan işlemleri listele
        self.kategorileri_yukle()  # Kategorileri yükle (hem combobox'lar hem liste için)
        self.listele_musteriler()  # Müşterileri listele
        self.listele_urunler()  # Ürünleri listele
        self.listele_fatura_teklifler()  # Fatura/Teklifleri listele
        self.listele_tasarruf_hedefleri()  # YENİ: Tasarruf hedeflerini listele

        self.uretim_kontrolu()  # Tekrarlayan işlemlerin otomatik üretimini kontrol et

    def on_closing(self):
        """Uygulama kapatılırken veritabanı bağlantısını kapatır."""
        if messagebox.askokcancel("Çıkış", "Uygulamadan çıkmak istediğinize emin misiniz?"):
            self.db_manager.close()
            self.root.destroy()

    def show_message(self, title, message):
        """Genel mesaj kutusu gösterir."""
        messagebox.showinfo(title, message)

    def show_error(self, title, message):
        """Genel hata mesajı kutusu gösterir."""
        messagebox.showerror(title, message)

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

        # YENİ SEKME: Tasarruf Hedefleri
        self.tab_tasarruf_hedefleri = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_tasarruf_hedefleri, text="Tasarruf Hedefleri")
        self._tasarruf_hedefleri_arayuzu_olustur(self.tab_tasarruf_hedefleri)

    # --- Ana Ekran (Gelir/Gider Girişi) Fonksiyonları ---
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
        self.filtre_tur_combobox = ttk.Combobox(filtre_frame, textvariable=self.filtre_tur_var,
                                                values=["Tümü", "Gelir", "Gider"], state="readonly", width=12)
        self.filtre_tur_combobox.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.filtre_tur_combobox.bind("<<ComboboxSelected>>", lambda e: self.listele())

        ttk.Label(filtre_frame, text="Kategori:").grid(row=0, column=2, padx=5, pady=5, sticky="w")
        self.filtre_kategori_var = tk.StringVar(value="Tümü")
        self.filtre_kategori_combobox = ttk.Combobox(filtre_frame, textvariable=self.filtre_kategori_var,
                                                     values=["Tümü"], width=12)
        self.filtre_kategori_combobox.grid(row=0, column=3, padx=5, pady=5, sticky="ew")
        self.filtre_kategori_combobox.bind("<<ComboboxSelected>>", lambda e: self.listele())
        self.filtre_kategori_combobox.bind("<Button-1>",
                                           lambda e: self.kategorileri_yukle(self.filtre_kategori_combobox,
                                                                             include_all=True))

        ttk.Label(filtre_frame, text="Açıklama/Arama:").grid(row=0, column=4, padx=5, pady=5, sticky="w")
        self.arama_entry = ttk.Entry(filtre_frame, width=20)
        self.arama_entry.grid(row=0, column=5, padx=5, pady=5, sticky="ew")
        self.arama_entry.bind("<KeyRelease>", self.listele)  # Yazdıkça filtreleme için

        ttk.Label(filtre_frame, text="Tarih Aralığı:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.bas_tarih_entry = DateEntry(filtre_frame, selectmode='day', date_pattern='yyyy-mm-dd', width=12)
        self.bas_tarih_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        self.bas_tarih_entry.set_date(
            (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d"))  # Varsayılan 1 yıl önce

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

    def kaydet(self):
        """Yeni bir gelir/gider işlemini veritabanına kaydeder."""
        tur = self.tur_var.get()
        miktar_str = self.miktar_entry.get()
        kategori = self.kategori_var.get()
        aciklama = self.aciklama_entry.get()
        tarih = self.tarih_entry.get()

        if not tur or not miktar_str or not kategori or not tarih:
            messagebox.showerror("Hata", "Lütfen tüm gerekli alanları doldurun.")
            return

        try:
            miktar = float(miktar_str)
            if miktar <= 0:
                messagebox.showerror("Hata", "Miktar pozitif bir sayı olmalıdır.")
                return
        except ValueError:
            messagebox.showerror("Hata", "Miktar geçerli bir sayı olmalıdır.")
            return

        self.db_manager.insert_transaction(tur, miktar, kategori, aciklama, tarih, self.kullanici_id)
        messagebox.showinfo("Başarılı", "İşlem başarıyla kaydedildi.")
        self.listele()  # Listeyi güncelle
        self.temizle()  # Giriş alanlarını temizle
        self.ai_predictor.load_or_train_model()  # Yeni veri eklendiği için AI modelini yeniden eğit

    def guncelle(self):
        """Seçili gelir/gider işlemini günceller."""
        if not self.selected_item_id:
            messagebox.showwarning("Uyarı", "Lütfen güncellemek için bir işlem seçin.")
            return

        tur = self.tur_var.get()
        miktar_str = self.miktar_entry.get()
        kategori = self.kategori_var.get()
        aciklama = self.aciklama_entry.get()
        tarih = self.tarih_entry.get()

        if not tur or not miktar_str or not kategori or not tarih:
            messagebox.showerror("Hata", "Lütfen tüm gerekli alanları doldurun.")
            return

        try:
            miktar = float(miktar_str)
            if miktar <= 0:
                messagebox.showerror("Hata", "Miktar pozitif bir sayı olmalıdır.")
                return
        except ValueError:
            messagebox.showerror("Hata", "Miktar geçerli bir sayı olmalıdır.")
            return

        self.db_manager.update_transaction(self.selected_item_id, tur, miktar, kategori, aciklama, tarih,
                                           self.kullanici_id)
        messagebox.showinfo("Başarılı", "İşlem başarıyla güncellendi.")
        self.listele()  # Listeyi güncelle
        self.temizle()  # Giriş alanlarını temizle
        self.selected_item_id = None
        self.ai_predictor.load_or_train_model()  # Veri güncellendiği için AI modelini yeniden eğit

    def sil(self):
        """Seçili gelir/gider işlemini siler."""
        if not self.selected_item_id:
            messagebox.showwarning("Uyarı", "Lütfen silmek için bir işlem seçin.")
            return

        if messagebox.askyesno("Onay", "Seçili işlemi silmek istediğinizden emin misiniz?"):
            self.db_manager.delete_transaction(self.selected_item_id, self.kullanici_id)
            messagebox.showinfo("Başarılı", "İşlem başarıyla silindi.")
            self.listele()  # Listeyi güncelle
            self.temizle()  # Giriş alanlarını temizle
            self.selected_item_id = None
            self.ai_predictor.load_or_train_model()  # Veri silindiği için AI modelini yeniden eğit

    def temizle(self):
        """Giriş alanlarını temizler ve seçimi sıfırlar."""
        self.tur_var.set("Gider")
        self.miktar_entry.delete(0, tk.END)
        self.kategori_var.set("")
        self.aciklama_entry.delete(0, tk.END)
        self.tarih_entry.set_date(datetime.now().strftime("%Y-%m-%d"))
        self.selected_item_id = None
        self.liste.selection_remove(self.liste.selection())  # Treeview'daki seçimi kaldır

    def listele(self):
        """Belirli filtrelerle işlemleri veritabanından çeker ve Treeview'da listeler."""
        for i in self.liste.get_children():
            self.liste.delete(i)

        filtre_tur = self.filtre_tur_var.get()
        filtre_kategori = self.filtre_kategori_var.get()
        arama_terimi = self.arama_entry.get().strip()
        baslangic_tarih = self.bas_tarih_entry.get()
        bitis_tarih = self.bit_tarih_entry.get()

        transactions = self.db_manager.get_transactions(self.kullanici_id, filtre_tur, filtre_kategori, baslangic_tarih,
                                                        bitis_tarih, arama_terimi)

        toplam_gelir = 0
        toplam_gider = 0

        for row in transactions:
            self.liste.insert("", "end", values=row)
            if row[1] == "Gelir":
                toplam_gelir += row[2]
            else:
                toplam_gider += row[2]

        self.toplam_gelir_label.config(text=f"Toplam Gelir: ₺{toplam_gelir:.2f}")
        self.toplam_gider_label.config(text=f"Toplam Gider: ₺{toplam_gider:.2f}")
        self.bakiye_label.config(text=f"Bakiye: ₺{toplam_gelir - toplam_gider:.2f}")

    def liste_secildi(self, event):
        """Treeview'da bir satır seçildiğinde giriş alanlarını doldurur."""
        selected_item = self.liste.focus()
        if selected_item:
            values = self.liste.item(selected_item, "values")
            self.selected_item_id = values[0]  # ID'yi sakla

            self.tur_var.set(values[1])
            self.miktar_entry.delete(0, tk.END)
            self.miktar_entry.insert(0, str(values[2]))
            self.kategori_var.set(values[3])
            self.aciklama_entry.delete(0, tk.END)
            self.aciklama_entry.insert(0, values[4])
            self.tarih_entry.set_date(values[5])
        else:
            self.temizle()  # Seçim kalkarsa alanları temizle

    def _kategori_oner(self):
        """Açıklama alanına göre AI kullanarak kategori önerir."""
        aciklama = self.aciklama_entry.get().strip()
        if not aciklama:
            messagebox.showwarning("Uyarı", "Lütfen kategori tahmini için bir açıklama girin.")
            return

        # AI modelinin eğitilip eğitilmediğini kontrol et
        if not hasattr(self.ai_predictor, 'model') or self.ai_predictor.model is None:
            messagebox.showinfo("Bilgi",
                                "AI modeli henüz eğitilmemiş veya yüklenmemiş. Lütfen birkaç işlem girdikten sonra tekrar deneyin.")
            try:
                self.ai_predictor.load_or_train_model()  # Tekrar eğitim denemesi
            except Exception as e:
                self.show_error("AI Hatası", f"AI modeli yüklenirken/eğitilirken hata oluştu: {e}")
                return

        predicted_category = self.ai_predictor.predict(aciklama)
        if predicted_category:
            self.kategori_var.set(predicted_category)
            messagebox.showinfo("Kategori Tahmini", f"Tahmin edilen kategori: {predicted_category}")
        else:
            messagebox.showinfo("Kategori Tahmini",
                                "Kategori tahmin edilemedi. Lütfen daha fazla veri girişi yapın veya manuel seçin.")

    def _retrain_ai_model(self):
        """Yapay zeka modelini manuel olarak yeniden eğitir."""
        try:
            self.ai_predictor.load_or_train_model(force_retrain=True)
            messagebox.showinfo("Başarılı", "Yapay zeka modeli başarıyla yeniden eğitildi.")
        except Exception as e:
            messagebox.showerror("Hata", f"Yapay zeka modeli yeniden eğitilirken bir hata oluştu: {e}")

    # --- Gelişmiş Araçlar & Raporlar Sekmesi Fonksiyonları ---
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
                    cb.bind("<Button-1>",
                            lambda e: self.kategorileri_yukle(self.kategori_tekrar_combobox))  # Tıklayınca güncelle
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
        ttk.Button(tekrar_eden_buton_frame, text="Manuel Üret", command=self.manuel_uret_tekrar_eden).pack(side="left",
                                                                                                           padx=5,
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

    # Tekrarlayan İşlem Fonksiyonları
    def kaydet_tekrar_eden(self):
        """Yeni bir tekrarlayan işlem kaydeder."""
        tur = self.tur_tekrar_var.get()
        miktar_str = self.miktar_tekrar_entry.get()
        kategori = self.kategori_tekrar_var.get()
        aciklama = self.aciklama_tekrar_entry.get()
        baslangic_tarihi = self.baslangic_tarih_tekrar_entry.get()
        siklilik = self.siklilik_var.get()

        if not tur or not miktar_str or not kategori or not baslangic_tarihi or not siklilik:
            self.show_error("Hata", "Lütfen tüm gerekli alanları doldurun.")
            return

        try:
            miktar = float(miktar_str)
            if miktar <= 0:
                self.show_error("Hata", "Miktar pozitif bir sayı olmalıdır.")
                return
        except ValueError:
            self.show_error("Hata", "Miktar geçerli bir sayı olmalıdır.")
            return

        self.db_manager.insert_recurring_transaction(tur, miktar, kategori, aciklama, baslangic_tarihi, siklilik,
                                                     baslangic_tarihi, self.kullanici_id)
        self.show_message("Başarılı", "Tekrarlayan işlem başarıyla kaydedildi.")
        self.listele_tekrar_eden_islemler()
        self.temizle_tekrar_eden()

    def sil_tekrar_eden(self):
        """Seçili tekrarlayan işlemi siler."""
        if not self.selected_recurring_item_id:
            self.show_warning("Uyarı", "Lütfen silmek için bir tekrarlayan işlem seçin.")
            return

        if messagebox.askyesno("Onay", "Seçili tekrarlayan işlemi silmek istediğinizden emin misiniz?"):
            self.db_manager.delete_recurring_transaction(self.selected_recurring_item_id, self.kullanici_id)
            self.show_message("Başarılı", "Tekrarlayan işlem başarıyla silindi.")
            self.listele_tekrar_eden_islemler()
            self.temizle_tekrar_eden()
            self.selected_recurring_item_id = None

    def temizle_tekrar_eden(self):
        """Tekrarlayan işlem giriş alanlarını temizler."""
        self.tur_tekrar_var.set("Gider")
        self.miktar_tekrar_entry.delete(0, tk.END)
        self.kategori_tekrar_var.set("")
        self.aciklama_tekrar_entry.delete(0, tk.END)
        self.baslangic_tarih_tekrar_entry.set_date(datetime.now().strftime("%Y-%m-%d"))
        self.siklilik_var.set("Aylık")
        self.selected_recurring_item_id = None
        self.tekrar_eden_liste.selection_remove(self.tekrar_eden_liste.selection())

    def listele_tekrar_eden_islemler(self):
        """Tekrarlayan işlemleri veritabanından çeker ve Treeview'da listeler."""
        for i in self.tekrar_eden_liste.get_children():
            self.tekrar_eden_liste.delete(i)

        recurring_transactions = self.db_manager.get_recurring_transactions(self.kullanici_id)
        for row in recurring_transactions:
            self.tekrar_eden_liste.insert("", "end", values=row)

    def tekrar_eden_liste_secildi(self, event):
        """Tekrarlayan işlemler Treeview'ında bir satır seçildiğinde giriş alanlarını doldurur."""
        selected_item = self.tekrar_eden_liste.focus()
        if selected_item:
            values = self.tekrar_eden_liste.item(selected_item, "values")
            self.selected_recurring_item_id = values[0]

            self.tur_tekrar_var.set(values[1])
            self.miktar_tekrar_entry.delete(0, tk.END)
            self.miktar_tekrar_entry.insert(0, str(values[2]))
            self.kategori_tekrar_var.set(values[3])
            self.aciklama_tekrar_entry.delete(0, tk.END)
            self.aciklama_tekrar_entry.insert(0, values[4])
            self.baslangic_tarih_tekrar_entry.set_date(values[5])
            self.siklilik_var.set(values[6])
        else:
            self.temizle_tekrar_eden()

    def uretim_kontrolu(self):
        """Tekrarlayan işlemlerin otomatik üretimini kontrol eder ve yapar."""
        recurring_transactions = self.db_manager.get_recurring_transactions(self.kullanici_id)
        today = datetime.now().date()
        uretilen_sayi = 0

        for rec_t in recurring_transactions:
            rec_id, tur, miktar, kategori, aciklama, baslangic_tarih_str, siklilik, son_uretilen_tarih_str = rec_t

            last_generated_date = datetime.strptime(son_uretilen_tarih_str, '%Y-%m-%d').date()

            # sonraki_uretim_tarihi'ni son_uretilen_tarih'ten başlat
            sonraki_uretim_tarihi = last_generated_date

            while sonraki_uretim_tarihi < today:
                if siklilik == "Günlük":
                    sonraki_uretim_tarihi += timedelta(days=1)
                elif siklilik == "Haftalık":
                    sonraki_uretim_tarihi += timedelta(weeks=1)
                elif siklilik == "Aylık":
                    # Ay atlamayı daha düzgün yönet
                    year = sonraki_uretim_tarihi.year
                    month = sonraki_uretim_tarihi.month + 1
                    if month > 12:
                        month = 1
                        year += 1
                    # Ayın son gününü aşmamak için min fonksiyonu
                    day = min(sonraki_uretim_tarihi.day,
                              (datetime(year, month + 1, 1) - timedelta(days=1)).day if month < 12 else 31)
                    sonraki_uretim_tarihi = datetime(year, month, day).date()
                elif siklilik == "Yıllık":
                    year = sonraki_uretim_tarihi.year + 1
                    day = min(sonraki_uretim_tarihi.day,
                              (datetime(year, 1, 1) + timedelta(days=364 if year % 4 != 0 else 365)).day)
                    sonraki_uretim_tarihi = datetime(year, sonraki_uretim_tarihi.month, day).date()
                else:  # Tanımsız sıklık
                    break

                # Eğer yeni üretim tarihi bugüne kadar gelmişse ve zaten üretilmemişse
                if sonraki_uretim_tarihi <= today:
                    self.db_manager.insert_transaction(tur, miktar, kategori, aciklama,
                                                       sonraki_uretim_tarihi.strftime('%Y-%m-%d'), self.kullanici_id)
                    self.db_manager.update_recurring_transaction_last_generated_date(rec_id,
                                                                                     sonraki_uretim_tarihi.strftime(
                                                                                         '%Y-%m-%d'))
                    uretilen_sayi += 1
                else:
                    break  # Bugün veya geçmişteki tüm tekrarlar üretildi

        if uretilen_sayi > 0:
            self.show_message("Tekrarlayan İşlemler",
                              f"{uretilen_sayi} adet tekrarlayan işlem otomatik olarak oluşturuldu.")
            self.listele()  # Ana ekranı da güncelle
            self.ai_predictor.load_or_train_model()  # Yeni verilerle AI'ı eğit

        self.listele_tekrar_eden_islemler()  # Tekrarlayanlar listesini güncelle

    def manuel_uret_tekrar_eden(self):
        """Seçilen tekrarlayan işlemi manuel olarak üretir ve son üretilen tarihi bugüne günceller."""
        if not self.selected_recurring_item_id:
            self.show_warning("Uyarı", "Lütfen manuel olarak üretilecek bir tekrarlayan işlem seçin.")
            return

        selected_item_values = self.tekrar_eden_liste.item(self.selected_recurring_item_id, "values")
        rec_id = selected_item_values[0]
        tur = selected_item_values[1]
        miktar = selected_item_values[2]
        kategori = selected_item_values[3]
        aciklama = selected_item_values[4]

        today_str = datetime.now().strftime('%Y-%m-%d')

        try:
            self.db_manager.insert_transaction(tur, miktar, kategori, aciklama, today_str, self.kullanici_id)
            self.db_manager.update_recurring_transaction_last_generated_date(rec_id, today_str)
            self.show_message("Başarılı", f"'{aciklama}' açıklamalı işlem bugün için manuel olarak üretildi.")
            self.listele()  # Ana ekranı güncelle
            self.listele_tekrar_eden_islemler()  # Tekrarlayanlar ekranını güncelle
            self.ai_predictor.load_or_train_model()  # Yeni veri eklendiği için AI'ı eğit
        except Exception as e:
            self.show_error("Hata", f"Manuel üretim sırasında bir hata oluştu: {e}")

    # Kategori Yönetimi Fonksiyonları
    def kategorileri_yukle(self, combobox_widget=None, include_all=False):
        """Kategori combobox'larını ve kategori listesini günceller."""
        kategoriler = self.db_manager.get_categories_for_user(self.kullanici_id)
        kategori_adlari = [k[1] for k in kategoriler]  # k[1] kategori adıdır

        if include_all:
            kategori_adlari.insert(0, "Tümü")  # "Tümü" seçeneğini en başa ekle

        # Ana ekrandaki kategori combobox'ını güncelle
        if hasattr(self, 'kategori_combobox') and not combobox_widget:
            self.kategori_combobox['values'] = kategori_adlari
            if not self.kategori_var.get() in kategori_adlari and not include_all:  # Seçili kategori yoksa veya kaldırıldıysa
                self.kategori_var.set("")  # Temizle

        # Tekrarlayan işlemlerdeki kategori combobox'ını güncelle
        if hasattr(self, 'kategori_tekrar_combobox') and not combobox_widget:
            self.kategori_tekrar_combobox['values'] = kategori_adlari
            if not self.kategori_tekrar_var.get() in kategori_adlari and not include_all:
                self.kategori_tekrar_var.set("")

        # Filtreleme combobox'ını güncelle
        if hasattr(self, 'filtre_kategori_combobox') and not combobox_widget:
            self.filtre_kategori_combobox['values'] = kategori_adlari
            if not self.filtre_kategori_var.get() in kategori_adlari:
                self.filtre_kategori_var.set("Tümü")  # Filtreyi sıfırla

        # Eğer belirli bir combobox widget'ı belirtildiyse sadece onu güncelle
        if combobox_widget:
            combobox_widget['values'] = kategori_adlari
            if not combobox_widget.get() in kategori_adlari and not include_all:
                combobox_widget.set("")  # Temizle

        # Kategori yönetim ekranındaki Treeview'ı güncelle
        if hasattr(self, 'kategori_liste'):
            for i in self.kategori_liste.get_children():
                self.kategori_liste.delete(i)
            for kategori in kategoriler:
                self.kategori_liste.insert("", "end", values=kategori)

    def kategori_ekle(self, kategori_adi, kategori_turu, show_message=True):
        """Yeni bir kategori ekler."""
        kategori_adi = kategori_adi.strip()
        if not kategori_adi or not kategori_turu:
            if show_message:
                self.show_error("Hata", "Lütfen kategori adı ve türünü girin.")
            return False

        if self.db_manager.get_category_by_name(kategori_adi, self.kullanici_id):
            if show_message:
                self.show_error("Hata", f"'{kategori_adi}' adında bir kategori zaten mevcut.")
            return False

        if self.db_manager.insert_category(kategori_adi, kategori_turu, self.kullanici_id):
            if show_message:
                self.show_message("Başarılı", f"'{kategori_adi}' kategorisi başarıyla eklendi.")
            self.kategorileri_yukle()
            self.temizle_kategori()
            return True
        else:
            if show_message:
                self.show_error("Hata", "Kategori eklenirken bir sorun oluştu.")
            return False

    def kategori_sil(self):
        """Seçili kategoriyi siler."""
        if not self.selected_category_id:
            self.show_warning("Uyarı", "Lütfen silmek için bir kategori seçin.")
            return

        selected_values = self.kategori_liste.item(self.selected_category_id, "values")
        category_name = selected_values[1]  # Kategori adı

        # Bu kategorinin kullanıldığı işlem var mı kontrol et
        transaction_count = self.db_manager.count_transactions_by_category(category_name, self.kullanici_id)
        if transaction_count > 0:
            if not messagebox.askyesno("Uyarı",
                                       f"'{category_name}' kategorisi {transaction_count} işlemde kullanılıyor. Silerseniz bu işlemlerin kategori bilgisi kaldırılacaktır. Devam etmek istiyor musunuz?"):
                return
            # İşlemlerdeki kategori bilgisini NULL yap
            self.db_manager.update_transactions_category_to_null(category_name, self.kullanici_id)

        if messagebox.askyesno("Onay", f"Seçili kategoriyi ('{category_name}') silmek istediğinizden emin misiniz?"):
            self.db_manager.delete_category(self.selected_category_id, self.kullanici_id)
            self.show_message("Başarılı", "Kategori başarıyla silindi.")
            self.kategorileri_yukle()
            self.temizle_kategori()
            self.listele()  # Ana işlem listesini güncelle
            self.ai_predictor.load_or_train_model()  # AI modelini yeniden eğit (veri değiştiği için)
            self.selected_category_id = None

    def temizle_kategori(self):
        """Kategori giriş alanlarını temizler ve seçimi sıfırlar."""
        self.kategori_adi_entry.delete(0, tk.END)
        self.kategori_tur_var.set("Genel")
        self.selected_category_id = None
        self.kategori_liste.selection_remove(self.kategori_liste.selection())

    def kategori_liste_secildi(self, event):
        """Kategori Treeview'da bir satır seçildiğinde giriş alanlarını doldurur."""
        selected_item = self.kategori_liste.focus()
        if selected_item:
            values = self.kategori_liste.item(selected_item, "values")
            self.selected_category_id = values[0]

            self.kategori_adi_entry.delete(0, tk.END)
            self.kategori_adi_entry.insert(0, values[1])
            self.kategori_tur_var.set(values[2])
        else:
            self.temizle_kategori()

    # Grafik ve Raporlama Fonksiyonları
    def grafik_goster(self):
        """Gelir-Gider grafiklerini Matplotlib ile gösterir."""
        kategori_verileri, zaman_verileri = self.db_manager.get_transaction_for_charts(self.kullanici_id)

        # Matplotlib grafiklerini temizle
        plt.close('all')  # Önceki tüm figürleri kapat
        self.fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 6))  # 1 satır, 2 sütunlu subplot

        # Kategori Bazında Pasta Grafiği
        income_categories = {}
        expense_categories = {}

        for _type, category, amount in kategori_verileri:
            if category:  # Kategori boş olmayanları al
                if _type == "Gelir":
                    income_categories[category] = income_categories.get(category, 0) + amount
                elif _type == "Gider":
                    expense_categories[category] = expense_categories.get(category, 0) + amount

        if income_categories:
            ax1.pie(income_categories.values(), labels=income_categories.keys(), autopct='%1.1f%%', startangle=90)
            ax1.set_title('Gelir Kategorileri Dağılımı', fontsize=10)
            ax1.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.
        else:
            ax1.text(0.5, 0.5, "Gelir Verisi Yok", horizontalalignment='center', verticalalignment='center',
                     transform=ax1.transAxes)
            ax1.set_title('Gelir Kategorileri Dağılımı (Veri Yok)', fontsize=10)

        if expense_categories:
            ax2.pie(expense_categories.values(), labels=expense_categories.keys(), autopct='%1.1f%%', startangle=90)
            ax2.set_title('Gider Kategorileri Dağılımı', fontsize=10)
            ax2.axis('equal')
        else:
            ax2.text(0.5, 0.5, "Gider Verisi Yok", horizontalalignment='center', verticalalignment='center',
                     transform=ax2.transAxes)
            ax2.set_title('Gider Kategorileri Dağılımı (Veri Yok)', fontsize=10)

        plt.tight_layout()  # Grafikler arasındaki boşlukları ayarla
        plt.show()  # Grafiği göster

        # Kümülatif Bakiye Grafiği (Ayrı bir pencerede gösterilebilir)
        fig_balance, ax_balance = plt.subplots(figsize=(10, 6))
        dates = []
        balances = []
        current_balance = 0.0

        # Tarih ve miktarları alıp sırala
        sorted_transactions = sorted(zaman_verileri, key=lambda x: datetime.strptime(x[0], '%Y-%m-%d'))

        for date_str, _type, amount in sorted_transactions:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            if _type == "Gelir":
                current_balance += amount
            elif _type == "Gider":
                current_balance -= amount
            dates.append(date_obj)
            balances.append(current_balance)

        if dates:
            ax_balance.plot(dates, balances, marker='o', linestyle='-', color='blue')
            ax_balance.set_title('Zamanla Kümülatif Bakiye', fontsize=12)
            ax_balance.set_xlabel('Tarih', fontsize=10)
            ax_balance.set_ylabel('Bakiye (TL)', fontsize=10)
            ax_balance.grid(True)
            fig_balance.autofmt_xdate()  # Tarih etiketlerini eğ
        else:
            ax_balance.text(0.5, 0.5, "Bakiye Verisi Yok", horizontalalignment='center', verticalalignment='center',
                            transform=ax_balance.transAxes)
            ax_balance.set_title('Zamanla Kümülatif Bakiye (Veri Yok)', fontsize=12)

        plt.tight_layout()
        plt.show()

    def rapor_olustur(self):
        """Gelir-Gider Raporunu PDF olarak oluşturur."""
        # Burada raporun içeriğini oluşturup PDFGenerator'a göndereceğiz
        # Basit bir örnek rapor oluşturalım:
        transactions = self.db_manager.get_transactions(self.kullanici_id)

        report_data = {
            "title": f"{self.username} Kullanıcısı İçin Gelir-Gider Raporu",
            "sections": [
                {"heading": "Tüm İşlemler", "data": [["ID", "Tür", "Miktar", "Kategori", "Açıklama", "Tarih"]]}
            ]
        }

        for t in transactions:
            report_data["sections"][0]["data"].append([str(x) for x in t])  # Tüm verileri stringe çevir

        # Toplam gelir, gider, bakiye hesapla
        toplam_gelir = sum(t[2] for t in transactions if t[1] == "Gelir")
        toplam_gider = sum(t[2] for t in transactions if t[1] == "Gider")
        bakiye = toplam_gelir - toplam_gider

        report_data["sections"].append({
            "heading": "Özet Bilgiler",
            "data": [
                ["Toplam Gelir:", f"₺{toplam_gelir:.2f}"],
                ["Toplam Gider:", f"₺{toplam_gider:.2f}"],
                ["Bakiye:", f"₺{bakiye:.2f}"]
            ]
        })

        try:
            # PDFGenerator'ı burada kullanıyoruz
            pdf_path = self.pdf_generator.generate_general_report_pdf(report_data,
                                                                      f"{self.username}_GelirGider_Raporu_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf")
            messagebox.showinfo("Rapor Oluşturuldu", f"Gelir-Gider Raporu başarıyla oluşturuldu:\n{pdf_path}")
            os.startfile(pdf_path)  # Oluşturulan PDF'i aç
        except Exception as e:
            messagebox.showerror("Hata", f"Rapor oluşturulurken bir hata oluştu: {e}")

    # --- Fatura / Teklifler Sekmesi Fonksiyonları ---
    def _fatura_teklif_arayuzu_olustur(self, parent_frame):
        """Fatura/Teklif sekmesinin kullanıcı arayüzünü oluşturur."""
        fatura_teklif_frame = ttk.LabelFrame(parent_frame, text="Fatura / Teklif Oluştur ve Yönet", padding=15)
        fatura_teklif_frame.pack(pady=10, padx=0, fill="both", expand=True)

        fatura_teklif_frame.grid_columnconfigure(1, weight=1)
        # item_list_frame için expand vereceğiz, bu yüzden fatura_teklif_frame'in satırını genişletelim
        fatura_teklif_frame.grid_rowconfigure(9,
                                              weight=1)  # Ürün/Hizmetler listesinin olduğu satır. (Güncellenmiş index)

        # Fatura/Teklif giriş alanları (Güncellenmiş input_widgets listesi)
        input_rows = [
            ("Tür:", "fatura_tur_var", ["Fatura", "Teklif"], "Combobox"),
            ("Belge No:", "belge_numarasi_entry", None, "Entry"),
            ("Müşteri Adı:", "fatura_musteri_var", [], "Combobox"),
            ("Belge Tarihi:", "fatura_belge_tarih_entry", None, "DateEntry"),
            ("Son Ödeme/Geçerlilik Tarihi:", "fatura_son_odeme_gecerlilik_tarih_entry", None, "DateEntry"),
            ("Durum:", "fatura_durum_var", ["Taslak", "Gönderildi", "Ödendi", "İptal Edildi"], "Combobox"),
        ]

        current_row = 0
        for label_text, var_name, values, widget_type in input_rows:
            ttk.Label(fatura_teklif_frame, text=label_text).grid(row=current_row, column=0, padx=5, pady=2, sticky="nw")

            if widget_type == "Combobox":
                var = tk.StringVar()
                cb = ttk.Combobox(fatura_teklif_frame, textvariable=var, values=values, state="readonly", width=30)
                cb.grid(row=current_row, column=1, padx=5, pady=2, sticky="ew")
                setattr(self, var_name, var)
                if var_name == "fatura_tur_var":
                    var.set("Fatura")
                    cb.bind("<<ComboboxSelected>>", self._fatura_tur_secildi)
                if var_name == "fatura_durum_var":
                    var.set("Taslak")
                if var_name == "fatura_musteri_var":
                    self.fatura_musteri_combobox = cb
                    self.fatura_musteri_combobox.bind("<Button-1>",
                                                      lambda e: self.listele_musteriler(self.fatura_musteri_combobox))
            elif widget_type == "Entry":
                entry = ttk.Entry(fatura_teklif_frame, width=35)
                entry.grid(row=current_row, column=1, padx=5, pady=2, sticky="ew")
                setattr(self, var_name, entry)
                if var_name == "belge_numarasi_entry":
                    entry.config(state="readonly")
            elif widget_type == "DateEntry":
                date_entry = DateEntry(fatura_teklif_frame, selectmode='day', date_pattern='yyyy-mm-dd', width=32,
                                       background='darkblue', foreground='white', borderwidth=2)
                date_entry.grid(row=current_row, column=1, padx=5, pady=2, sticky="ew")
                date_entry.set_date(datetime.now().strftime("%Y-%m-%d"))
                setattr(self, var_name, date_entry)
            current_row += 1

        # Belge numarası oluşturma butonu
        ttk.Button(fatura_teklif_frame, text="Numara Oluştur", command=self.belge_numarasi_olustur).grid(row=1,
                                                                                                         column=2,
                                                                                                         padx=5, pady=2,
                                                                                                         sticky="w")
        # --- Ürün/Hizmet Ekleme Bölümü ---
        ttk.Label(fatura_teklif_frame, text="Ürün/Hizmet Seç:").grid(row=current_row, column=0, padx=5, pady=2,
                                                                     sticky="w")
        self.fatura_urun_sec_var = tk.StringVar()
        self.fatura_urun_sec_combobox = ttk.Combobox(fatura_teklif_frame, textvariable=self.fatura_urun_sec_var,
                                                     values=[], state="readonly", width=30)
        self.fatura_urun_sec_combobox.grid(row=current_row, column=1, padx=5, pady=2, sticky="ew")
        self.fatura_urun_sec_combobox.bind("<Button-1>", lambda e: self.listele_urunler(self.fatura_urun_sec_combobox))
        self.fatura_urun_sec_combobox.bind("<<ComboboxSelected>>", self._fatura_urun_secildi)

        ttk.Label(fatura_teklif_frame, text="Miktar:").grid(row=current_row, column=2, padx=5, pady=2, sticky="w")
        self.fatura_urun_miktar_entry = ttk.Entry(fatura_teklif_frame, width=10)
        self.fatura_urun_miktar_entry.grid(row=current_row, column=3, padx=5, pady=2, sticky="ew")
        self.fatura_urun_miktar_entry.bind("<KeyRelease>", self._fatura_urun_tutari_hesapla)
        current_row += 1

        ttk.Label(fatura_teklif_frame, text="Birim Fiyat:").grid(row=current_row, column=0, padx=5, pady=2, sticky="w")
        self.fatura_urun_birim_fiyat_entry = ttk.Entry(fatura_teklif_frame, width=10)
        self.fatura_urun_birim_fiyat_entry.grid(row=current_row, column=1, padx=5, pady=2, sticky="ew")
        self.fatura_urun_birim_fiyat_entry.bind("<KeyRelease>", self._fatura_urun_tutari_hesapla)

        ttk.Label(fatura_teklif_frame, text="KDV Oranı (%):").grid(row=current_row, column=2, padx=5, pady=2,
                                                                   sticky="w")
        self.fatura_urun_kdv_oran_entry = ttk.Entry(fatura_teklif_frame, width=10)
        self.fatura_urun_kdv_oran_entry.grid(row=current_row, column=3, padx=5, pady=2, sticky="ew")
        self.fatura_urun_kdv_oran_entry.bind("<KeyRelease>", self._fatura_urun_tutari_hesapla)
        current_row += 1

        ttk.Label(fatura_teklif_frame, text="KDV Miktarı:").grid(row=current_row, column=0, padx=5, pady=2, sticky="w")
        self.fatura_urun_kdv_miktar_label = ttk.Label(fatura_teklif_frame, text="0.00 ₺")
        self.fatura_urun_kdv_miktar_label.grid(row=current_row, column=1, padx=5, pady=2, sticky="ew")

        ttk.Label(fatura_teklif_frame, text="Ara Toplam:").grid(row=current_row, column=2, padx=5, pady=2, sticky="w")
        self.fatura_urun_ara_toplam_label = ttk.Label(fatura_teklif_frame, text="0.00 ₺")
        self.fatura_urun_ara_toplam_label.grid(row=current_row, column=3, padx=5, pady=2, sticky="ew")
        current_row += 1

        ttk.Button(fatura_teklif_frame, text="Kalemi Ekle", command=self.fatura_kalem_ekle).grid(row=current_row,
                                                                                                 column=0, columnspan=4,
                                                                                                 pady=5, sticky="ew")
        current_row += 1

        # Ürün/Hizmetler listesi (Treeview)
        item_list_frame = ttk.Frame(fatura_teklif_frame, padding="5 0 0 0")
        item_list_frame.grid(row=current_row, column=0, columnspan=4, sticky="nsew")  # Tüm sütunları kapla
        current_row += 1

        self.fatura_kalem_liste = ttk.Treeview(item_list_frame,
                                               columns=("Ad", "Miktar", "Birim Fiyat", "KDV Oranı", "KDV Miktarı",
                                                        "Ara Toplam"),
                                               show="headings")
        self.fatura_kalem_liste.heading("Ad", text="Ürün/Hizmet", anchor="w")
        self.fatura_kalem_liste.column("Ad", width=150)
        self.fatura_kalem_liste.heading("Miktar", text="Miktar", anchor="w")
        self.fatura_kalem_liste.column("Miktar", width=70)
        self.fatura_kalem_liste.heading("Birim Fiyat", text="Birim Fiyat (₺)", anchor="e")
        self.fatura_kalem_liste.column("Birim Fiyat", width=100)
        self.fatura_kalem_liste.heading("KDV Oranı", text="KDV %", anchor="e")
        self.fatura_kalem_liste.column("KDV Oranı", width=70)
        self.fatura_kalem_liste.heading("KDV Miktarı", text="KDV Miktar (₺)", anchor="e")
        self.fatura_kalem_liste.column("KDV Miktarı", width=100)
        self.fatura_kalem_liste.heading("Ara Toplam", text="Ara Toplam (₺)", anchor="e")
        self.fatura_kalem_liste.column("Ara Toplam", width=120)
        self.fatura_kalem_liste.pack(fill="both", expand=True)

        kalem_scroll_y = ttk.Scrollbar(item_list_frame, orient="vertical", command=self.fatura_kalem_liste.yview)
        self.fatura_kalem_liste.configure(yscrollcommand=kalem_scroll_y.set)
        kalem_scroll_y.pack(side="right", fill="y")

        ttk.Button(item_list_frame, text="Kalemi Çıkar", command=self.fatura_kalem_cikar).pack(pady=5)
        self.current_invoice_items = []  # Fatura/Teklife eklenecek geçici kalemler listesi

        # --- Toplamlar ve Notlar Bölümü ---
        ttk.Label(fatura_teklif_frame, text="KDV Hariç Toplam (₺):").grid(row=current_row, column=0, padx=5, pady=2,
                                                                          sticky="w")
        self.fatura_kdv_haric_toplam_label = ttk.Label(fatura_teklif_frame, text="0.00", font=("Arial", 11, "bold"))
        self.fatura_kdv_haric_toplam_label.grid(row=current_row, column=1, padx=5, pady=2, sticky="ew")
        current_row += 1

        ttk.Label(fatura_teklif_frame, text="Toplam KDV (₺):").grid(row=current_row, column=0, padx=5, pady=2,
                                                                    sticky="w")
        self.fatura_toplam_kdv_label = ttk.Label(fatura_teklif_frame, text="0.00", font=("Arial", 11, "bold"))
        self.fatura_toplam_kdv_label.grid(row=current_row, column=1, padx=5, pady=2, sticky="ew")
        current_row += 1

        ttk.Label(fatura_teklif_frame, text="Genel Toplam (₺):").grid(row=current_row, column=0, padx=5, pady=2,
                                                                      sticky="w")
        self.fatura_genel_toplam_label = ttk.Label(fatura_teklif_frame, text="0.00", font=("Arial", 12, "bold"),
                                                   foreground="blue")
        self.fatura_genel_toplam_label.grid(row=current_row, column=1, padx=5, pady=2, sticky="ew")
        current_row += 1

        ttk.Label(fatura_teklif_frame, text="Notlar:").grid(row=current_row, column=0, padx=5, pady=2, sticky="nw")
        self.fatura_notlar_text = tk.Text(fatura_teklif_frame, height=3, width=30)
        self.fatura_notlar_text.grid(row=current_row, column=1, padx=5, pady=2, sticky="ew")
        current_row += 1

        # Fatura/Teklif butonları
        fatura_buton_frame = ttk.Frame(fatura_teklif_frame, padding="10 0 0 0")
        fatura_buton_frame.grid(row=current_row, column=0, columnspan=4, pady=10, sticky="ew")
        ttk.Button(fatura_buton_frame, text="Kaydet", command=self.kaydet_fatura_teklif).pack(side="left", padx=5,
                                                                                              fill="x", expand=True)
        ttk.Button(fatura_buton_frame, text="Güncelle", command=self.guncelle_fatura_teklif).pack(side="left", padx=5,
                                                                                                  fill="x", expand=True)
        ttk.Button(fatura_buton_frame, text="Sil", command=self.sil_fatura_teklif).pack(side="left", padx=5, fill="x",
                                                                                        expand=True)
        ttk.Button(fatura_buton_frame, text="Temizle", command=self.temizle_fatura_teklif).pack(side="left", padx=5,
                                                                                                fill="x", expand=True)
        ttk.Button(fatura_buton_frame, text="PDF Oluştur", command=self.pdf_olustur_fatura_teklif).pack(side="left",
                                                                                                        padx=5,
                                                                                                        fill="x",
                                                                                                        expand=True)
        current_row += 1

        # Fatura/Teklif listesi (Treeview)
        fatura_liste_frame = ttk.Frame(parent_frame, padding="10 0 0 0")
        fatura_liste_frame.pack(pady=10, padx=0, fill="both", expand=True)

        fatura_scroll_y = ttk.Scrollbar(fatura_liste_frame, orient="vertical")
        fatura_scroll_x = ttk.Scrollbar(fatura_liste_frame, orient="horizontal")

        self.fatura_teklif_liste = ttk.Treeview(fatura_liste_frame,
                                                columns=("id", "Tip", "Belge No", "Müşteri", "KDV Hariç", "Toplam KDV",
                                                         "Genel Toplam", "Tarih", "Durum"),
                                                show="headings",
                                                yscrollcommand=fatura_scroll_y.set,
                                                xscrollcommand=fatura_scroll_x.set)

        fatura_scroll_y.config(command=self.fatura_teklif_liste.yview)
        fatura_scroll_x.config(command=self.fatura_teklif_liste.xview)

        fatura_columns_info = {
            "id": {"text": "ID", "width": 40},
            "Tip": {"text": "Tip", "width": 60},
            "Belge No": {"text": "Belge No", "width": 120},
            "Müşteri": {"text": "Müşteri", "width": 150},
            "KDV Hariç": {"text": "KDV Hariç (₺)", "width": 100},
            "Toplam KDV": {"text": "Toplam KDV (₺)", "width": 100},
            "Genel Toplam": {"text": "Genel Toplam (₺)", "width": 120},
            "Tarih": {"text": "Tarih", "width": 90},
            "Durum": {"text": "Durum", "width": 90}
        }

        for col_name, info in fatura_columns_info.items():
            self.fatura_teklif_liste.heading(col_name, text=info["text"], anchor="w")
            self.fatura_teklif_liste.column(col_name, width=info["width"], stretch=tk.NO)

        self.fatura_teklif_liste.grid(row=0, column=0, sticky="nsew")
        fatura_scroll_y.grid(row=0, column=1, sticky="ns")
        fatura_scroll_x.grid(row=1, column=0, sticky="ew")

        fatura_liste_frame.grid_rowconfigure(0, weight=1)
        fatura_liste_frame.grid_columnconfigure(0, weight=1)

        self.fatura_teklif_liste.bind("<<TreeviewSelect>>", self.fatura_teklif_liste_secildi)

    # Fatura/Teklif Fonksiyonları
    def _fatura_tur_secildi(self, event=None):
        """Fatura/Teklif türü değiştiğinde belge numarasını günceller."""
        self.belge_numarasi_olustur()  # Yeni numara oluştur

    def belge_numarasi_olustur(self):
        """Yeni belge numarası oluşturur."""
        doc_type = self.fatura_tur_var.get()
        current_invoice_num, current_offer_num = self.db_manager.get_user_invoice_offer_nums(self.kullanici_id)

        prefix = ""
        num = 0
        if doc_type == "Fatura":
            prefix = "FTR-"
            num = current_invoice_num + 1
        elif doc_type == "Teklif":
            prefix = "TKLF-"
            num = current_offer_num + 1

        year = datetime.now().year
        self.belge_numarasi_entry.config(state="normal")  # Yazılabilir yap
        self.belge_numarasi_entry.delete(0, tk.END)
        self.belge_numarasi_entry.insert(0, f"{prefix}{year}-{num:05d}")
        self.belge_numarasi_entry.config(state="readonly")  # Tekrar sadece okunabilir yap

    def _fatura_urun_secildi(self, event=None):
        """Envanterden ürün seçildiğinde birim fiyat ve KDV oranını doldurur."""
        selected_product_name = self.fatura_urun_sec_var.get()
        product_info = self.db_manager.get_product_by_name(selected_product_name, self.kullanici_id)

        if product_info:
            # product_info formatı: (id, name, stock_quantity, purchase_price, selling_price, kdv_rate)
            selling_price = product_info[4]
            kdv_rate = product_info[5]

            self.fatura_urun_birim_fiyat_entry.delete(0, tk.END)
            self.fatura_urun_birim_fiyat_entry.insert(0, f"{selling_price:.2f}")

            self.fatura_urun_kdv_oran_entry.delete(0, tk.END)
            self.fatura_urun_kdv_oran_entry.insert(0, f"{kdv_rate:.2f}")

            self._fatura_urun_tutari_hesapla()  # Miktar boş olsa da sıfır olarak hesaplar

    def _fatura_urun_tutari_hesapla(self, event=None):
        """Ürün miktarı/fiyatı/KDV oranı değiştiğinde ara toplam ve KDV miktarını hesaplar."""
        try:
            miktar = float(self.fatura_urun_miktar_entry.get() or 0)
            birim_fiyat = float(self.fatura_urun_birim_fiyat_entry.get() or 0)
            kdv_oran = float(self.fatura_urun_kdv_oran_entry.get() or 0)

            ara_toplam_kdv_haric = miktar * birim_fiyat
            kdv_miktar = ara_toplam_kdv_haric * (kdv_oran / 100)

            self.fatura_urun_kdv_miktar_label.config(text=f"{kdv_miktar:.2f} ₺")
            self.fatura_urun_ara_toplam_label.config(text=f"{ara_toplam_kdv_haric:.2f} ₺")

        except ValueError:
            self.fatura_urun_kdv_miktar_label.config(text="Hata")
            self.fatura_urun_ara_toplam_label.config(text="Hata")

    def fatura_kalem_ekle(self):
        """Fatura/Teklife yeni kalem ekler."""
        urun_adi = self.fatura_urun_sec_var.get()
        miktar_str = self.fatura_urun_miktar_entry.get()
        birim_fiyat_str = self.fatura_urun_birim_fiyat_entry.get()
        kdv_oran_str = self.fatura_urun_kdv_oran_entry.get()

        if not urun_adi or not miktar_str or not birim_fiyat_str or not kdv_oran_str:
            self.show_error("Hata", "Lütfen tüm kalem alanlarını doldurun.")
            return

        try:
            miktar = float(miktar_str)
            birim_fiyat = float(birim_fiyat_str)
            kdv_oran = float(kdv_oran_str)
            if miktar <= 0 or birim_fiyat <= 0 or kdv_oran < 0:
                self.show_error("Hata", "Miktar ve birim fiyat pozitif, KDV oranı negatif olamaz.")
                return
        except ValueError:
            self.show_error("Hata", "Miktar, birim fiyat ve KDV oranı geçerli sayılar olmalıdır.")
            return

        # Ürünün stok miktarını kontrol et (Sadece faturalar için)
        if self.fatura_tur_var.get() == "Fatura":
            product_info = self.db_manager.get_product_by_name(urun_adi, self.kullanici_id)
            if product_info:
                current_stock = product_info[2]
                if miktar > current_stock:
                    messagebox.showwarning("Stok Uyarısı",
                                           f"'{urun_adi}' için yeterli stok yok. Mevcut stok: {current_stock}. Yine de ekleniyor.")

        kdv_miktar = birim_fiyat * miktar * (kdv_oran / 100)
        ara_toplam = birim_fiyat * miktar

        item_data = {
            "ad": urun_adi,
            "miktar": miktar,
            "birim_fiyat": birim_fiyat,
            "kdv_orani": kdv_oran,
            "kdv_miktari": kdv_miktar,
            "ara_toplam": ara_toplam
        }
        self.current_invoice_items.append(item_data)
        self.update_fatura_kalem_liste()
        self.temizle_fatura_kalemleri()
        self.fatura_toplamlari_hesapla()

    def fatura_kalem_cikar(self):
        """Fatura/Tekliften seçili kalemi çıkarır."""
        selected_item = self.fatura_kalem_liste.focus()
        if not selected_item:
            self.show_error("Hata", "Lütfen çıkarılacak bir kalem seçin.")
            return

        item_index = self.fatura_kalem_liste.index(selected_item)
        if messagebox.askyesno("Kalem Çıkar", "Seçili kalemi çıkarmak istediğinize emin misiniz?"):
            del self.current_invoice_items[item_index]
            self.update_fatura_kalem_liste()
            self.fatura_toplamlari_hesapla()

    def update_fatura_kalem_liste(self):
        """Fatura/Teklif kalem listesini günceller."""
        for i in self.fatura_kalem_liste.get_children():
            self.fatura_kalem_liste.delete(i)

        for item in self.current_invoice_items:
            self.fatura_kalem_liste.insert("", "end", values=(
                item["ad"],
                item["miktar"],
                f"{item['birim_fiyat']:.2f}",
                f"{item['kdv_orani']:.2f}",
                f"{item['kdv_miktari']:.2f}",
                f"{item['ara_toplam']:.2f}"
            ))

    def temizle_fatura_kalemleri(self):
        """Fatura/Teklif kalem giriş alanlarını temizler."""
        self.fatura_urun_sec_var.set("")
        self.fatura_urun_miktar_entry.delete(0, tk.END)
        self.fatura_urun_birim_fiyat_entry.delete(0, tk.END)
        self.fatura_urun_kdv_oran_entry.delete(0, tk.END)
        self.fatura_urun_kdv_miktar_label.config(text="0.00 ₺")
        self.fatura_urun_ara_toplam_label.config(text="0.00 ₺")

    def fatura_toplamlari_hesapla(self):
        """Fatura/Teklifin genel toplamlarını hesaplar ve günceller."""
        toplam_kdv_haric = sum(item["ara_toplam"] for item in self.current_invoice_items)
        toplam_kdv = sum(item["kdv_miktari"] for item in self.current_invoice_items)
        genel_toplam = toplam_kdv_haric + toplam_kdv

        self.fatura_kdv_haric_toplam_label.config(text=f"{toplam_kdv_haric:.2f} ₺")
        self.fatura_toplam_kdv_label.config(text=f"{toplam_kdv:.2f} ₺")
        self.fatura_genel_toplam_label.config(text=f"{genel_toplam:.2f} ₺")

    def kaydet_fatura_teklif(self):
        """Yeni bir fatura veya teklif kaydeder."""
        tur = self.fatura_tur_var.get()
        belge_numarasi = self.belge_numarasi_entry.get()
        musteri_adi = self.fatura_musteri_var.get()
        belge_tarihi = self.fatura_belge_tarih_entry.get()
        son_odeme_gecerlilik_tarihi = self.fatura_son_odeme_gecerlilik_tarih_entry.get()
        notlar = self.fatura_notlar_text.get("1.0", tk.END).strip()
        durum = self.fatura_durum_var.get()

        if not tur or not belge_numarasi or not musteri_adi or not belge_tarihi or not son_odeme_gecerlilik_tarihi or not durum:
            self.show_error("Hata", "Lütfen tüm belge bilgilerini doldurun.")
            return

        if not self.current_invoice_items:
            self.show_error("Hata", "Lütfen belgeye en az bir kalem ekleyin.")
            return

        if self.db_manager.check_belge_numarasi_exists(belge_numarasi, self.kullanici_id):
            self.show_error("Hata", f"'{belge_numarasi}' numaralı belge zaten mevcut. Lütfen başka bir numara girin.")
            return

        toplam_kdv_haric = sum(item["ara_toplam"] for item in self.current_invoice_items)
        toplam_kdv = sum(item["kdv_miktari"] for item in self.current_invoice_items)
        urun_hizmetler_json = json.dumps(self.current_invoice_items)

        self.db_manager.insert_invoice_offer(tur, belge_numarasi, musteri_adi, belge_tarihi,
                                             son_odeme_gecerlilik_tarihi,
                                             urun_hizmetler_json, toplam_kdv_haric, toplam_kdv, notlar, durum,
                                             self.kullanici_id)

        # Belge numaralarını güncelle
        if tur == "Fatura":
            current_invoice_num, _ = self.db_manager.get_user_invoice_offer_nums(self.kullanici_id)
            self.db_manager.update_user_invoice_offer_num(self.kullanici_id, invoice_num=current_invoice_num + 1)
        elif tur == "Teklif":
            _, current_offer_num = self.db_manager.get_user_invoice_offer_nums(self.kullanici_id)
            self.db_manager.update_user_invoice_offer_num(self.kullanici_id, offer_num=current_offer_num + 1)

        # Stokları güncelle (sadece fatura eklendiğinde ve ürünler envanterden düşüldüğünde)
        if tur == "Fatura":
            for item in self.current_invoice_items:
                product_name = item["ad"]
                quantity = item["miktar"]
                product_info = self.db_manager.get_product_by_name(product_name, self.kullanici_id)
                if product_info:
                    product_id = product_info[0]
                    current_stock = product_info[2]
                    new_stock = current_stock - quantity
                    self.db_manager.update_product_stock(product_id, new_stock)
            self.listele_urunler()  # Ürün listesini güncelle

        self.show_message("Başarılı", f"{tur} başarıyla eklendi.")
        self.listele_fatura_teklifler()
        self.temizle_fatura_teklif()
        self.belge_numarasi_olustur()  # Yeni belge numarası için önek ve sayı

    def guncelle_fatura_teklif(self):
        """Mevcut bir fatura veya teklifi günceller."""
        if not self.selected_invoice_id:
            self.show_warning("Uyarı", "Lütfen güncellemek için bir belge seçin.")
            return

        tur = self.fatura_tur_var.get()
        belge_numarasi = self.belge_numarasi_entry.get()
        musteri_adi = self.fatura_musteri_var.get()
        belge_tarihi = self.fatura_belge_tarih_entry.get()
        son_odeme_gecerlilik_tarihi = self.fatura_son_odeme_gecerlilik_tarih_entry.get()
        notlar = self.fatura_notlar_text.get("1.0", tk.END).strip()
        durum = self.fatura_durum_var.get()

        if not tur or not belge_numarasi or not musteri_adi or not belge_tarihi or not son_odeme_gecerlilik_tarihi or not durum:
            self.show_error("Hata", "Lütfen tüm belge bilgilerini doldurun.")
            return

        if not self.current_invoice_items:
            self.show_error("Hata", "Lütfen belgeye en az bir kalem ekleyin.")
            return

        # Belge numarasının kendisi hariç başka bir belgede kullanılıp kullanılmadığını kontrol et
        existing_doc = self.db_manager.get_invoice_offer_by_id(self.selected_invoice_id, self.kullanici_id)
        if existing_doc and existing_doc[2] != belge_numarasi:  # Eğer belge numarası değiştiyse
            if self.db_manager.check_belge_numarasi_exists(belge_numarasi, self.kullanici_id):
                self.show_error("Hata",
                                f"'{belge_numarasi}' numaralı belge başka bir belgede zaten mevcut. Lütfen başka bir numara girin.")
                return

        toplam_kdv_haric = sum(item["ara_toplam"] for item in self.current_invoice_items)
        toplam_kdv = sum(item["kdv_miktari"] for item in self.current_invoice_items)
        urun_hizmetler_json = json.dumps(self.current_invoice_items)

        self.db_manager.update_invoice_offer(self.selected_invoice_id, tur, belge_numarasi, musteri_adi, belge_tarihi,
                                             son_odeme_gecerlilik_tarihi,
                                             urun_hizmetler_json, toplam_kdv_haric, toplam_kdv, notlar, durum,
                                             self.kullanici_id)

        # Stokları güncelleme mantığı burada daha karmaşık olabilir (eski ve yeni kalemleri karşılaştırma)
        # Basit bir yaklaşım olarak, fatura güncellendiğinde stokları manuel olarak düzeltmek gerekebilir.
        # Bu kısım daha gelişmiş bir envanter yönetimi gerektirir.

        self.show_message("Başarılı", f"{tur} başarıyla güncellendi.")
        self.listele_fatura_teklifler()
        self.temizle_fatura_teklif()
        self.selected_invoice_id = None

    def sil_fatura_teklif(self):
        """Seçili fatura veya teklifi siler."""
        if not self.selected_invoice_id:
            self.show_warning("Uyarı", "Lütfen silmek için bir belge seçin.")
            return

        item_values = self.fatura_teklif_liste.item(self.selected_invoice_id, "values")
        doc_id = item_values[0]
        doc_type = item_values[1]
        doc_number = item_values[2]

        if messagebox.askyesno("Onay",
                               f"'{doc_number}' numaralı {doc_type} belgesini silmek istediğinizden emin misiniz?"):
            # Fatura silindiğinde stokları geri ekle (sadece Fatura ise)
            if doc_type == "Fatura":
                doc_detail = self.db_manager.get_invoice_offer_by_id(doc_id, self.kullanici_id)
                if doc_detail:
                    items = json.loads(doc_detail[6])  # items_json sütunu 6. indekste
                    for item in items:
                        product_name = item["ad"]
                        quantity = item["miktar"]
                        product_info = self.db_manager.get_product_by_name(product_name, self.kullanici_id)
                        if product_info:
                            product_id = product_info[0]
                            current_stock = product_info[2]
                            new_stock = current_stock + quantity  # Stokları geri ekle
                            self.db_manager.update_product_stock(product_id, new_stock)
                    self.listele_urunler()  # Ürün listesini güncelle

            self.db_manager.delete_invoice_offer(doc_id, self.kullanici_id)
            self.show_message("Başarılı", "Belge başarıyla silindi.")
            self.listele_fatura_teklifler()
            self.temizle_fatura_teklif()
            self.belge_numarasi_olustur()  # Belge numaralarını yeniden oluştur
            self.selected_invoice_id = None

    def temizle_fatura_teklif(self):
        """Fatura/Teklif giriş alanlarını ve kalemleri temizler."""
        self.fatura_tur_var.set("Fatura")
        self.belge_numarasi_olustur()  # Varsayılan belge numarasını getir
        self.fatura_musteri_var.set("")
        self.fatura_belge_tarih_entry.set_date(datetime.now())
        self.fatura_son_odeme_gecerlilik_tarih_entry.set_date(
            datetime.now() + timedelta(days=30))  # Varsayılan 30 gün sonra
        self.fatura_notlar_text.delete("1.0", tk.END)
        self.fatura_durum_var.set("Taslak")

        self.temizle_fatura_kalemleri()
        self.current_invoice_items = []
        self.update_fatura_kalem_liste()
        self.fatura_toplamlari_hesapla()
        self.selected_invoice_id = None
        self.fatura_teklif_liste.selection_remove(self.fatura_teklif_liste.selection())

    def listele_fatura_teklifler(self):
        """Tüm fatura ve teklifleri veritabanından çeker ve Treeview'da listeler."""
        for i in self.fatura_teklif_liste.get_children():
            self.fatura_teklif_liste.delete(i)

        invoice_offers = self.db_manager.get_invoice_offers(self.kullanici_id)
        for doc in invoice_offers:
            # doc formatı: (id, type, document_number, customer_name, total_amount_excluding_kdv, total_kdv_amount, general_total, document_date, status)
            self.fatura_teklif_liste.insert("", "end", values=(
                doc[0], doc[1], doc[2], doc[3], f"{doc[4]:.2f}", f"{doc[5]:.2f}", f"{doc[6]:.2f}", doc[7], doc[8]
            ))

    def fatura_teklif_liste_secildi(self, event):
        """Fatura/Teklif Treeview'da bir satır seçildiğinde giriş alanlarını doldurur."""
        selected_item = self.fatura_teklif_liste.focus()
        if selected_item:
            self.selected_invoice_id = self.fatura_teklif_liste.item(selected_item, "values")[0]
            doc_detail = self.db_manager.get_invoice_offer_by_id(self.selected_invoice_id, self.kullanici_id)

            if doc_detail:
                # doc_detail formatı: (id, type, document_number, customer_name, document_date, due_validity_date, items_json, total_amount_excluding_kdv, total_kdv_amount, notes, status, user_id)
                self.temizle_fatura_teklif()  # Önce temizle

                self.fatura_tur_var.set(doc_detail[1])
                self.belge_numarasi_entry.config(state="normal")
                self.belge_numarasi_entry.insert(0, doc_detail[2])
                self.belge_numarasi_entry.config(state="readonly")
                self.fatura_musteri_var.set(doc_detail[3])
                self.fatura_belge_tarih_entry.set_date(doc_detail[4])
                self.fatura_son_odeme_gecerlilik_tarih_entry.set_date(doc_detail[5])
                self.fatura_notlar_text.insert("1.0", doc_detail[9] or "")
                self.fatura_durum_var.set(doc_detail[10])

                self.current_invoice_items = json.loads(doc_detail[6])  # JSON'ı tekrar listeye çevir
                self.update_fatura_kalem_liste()
                self.fatura_toplamlari_hesapla()
        else:
            self.temizle_fatura_teklif()

    def pdf_olustur_fatura_teklif(self):
        """Seçili fatura veya teklifin PDF'ini oluşturur."""
        if not self.selected_invoice_id:
            self.show_error("Hata", "Lütfen PDF oluşturulacak bir belge seçin.")
            return

        doc_detail = self.db_manager.get_invoice_offer_by_id(self.selected_invoice_id, self.kullanici_id)

        if doc_detail:
            try:
                file_path = self.pdf_generator.generate_document_pdf(doc_detail)
                self.show_message("PDF Oluşturuldu", f"PDF başarıyla oluşturuldu:\n{file_path}")
                os.startfile(file_path)  # PDF'i otomatik aç
            except Exception as e:
                self.show_error("PDF Hatası", f"PDF oluşturulurken bir hata oluştu: {e}")
        else:
            self.show_error("Hata", "Belge detayları bulunamadı.")

    # --- Müşteri Yönetimi Sekmesi Fonksiyonları ---
    def _musteri_yonetimi_arayuzu_olustur(self, parent_frame):
        """Müşteri yönetimi sekmesinin arayüzünü oluşturur."""
        musteri_frame = ttk.LabelFrame(parent_frame, text="Müşteri Ekle / Düzenle / Sil", padding=15)
        musteri_frame.pack(pady=10, padx=0, fill="x", expand=False)

        musteri_frame.grid_columnconfigure(1, weight=1)

        input_widgets = [
            ("Ad/Unvan:", "musteri_ad_entry", None, "Entry"),
            ("Adres:", "musteri_adres_entry", None, "Entry"),
            ("Telefon:", "musteri_telefon_entry", None, "Entry"),
            ("E-posta:", "musteri_eposta_entry", None, "Entry"),
        ]

        for i, (label_text, var_name, values, widget_type) in enumerate(input_widgets):
            ttk.Label(musteri_frame, text=label_text).grid(row=i, column=0, padx=10, pady=5, sticky="w")
            entry = ttk.Entry(musteri_frame, width=40)
            entry.grid(row=i, column=1, padx=10, pady=5, sticky="ew")
            setattr(self, var_name, entry)

        # Müşteri butonları
        musteri_buton_frame = ttk.Frame(musteri_frame, padding="10 0 0 0")
        musteri_buton_frame.grid(row=len(input_widgets), column=0, columnspan=2, pady=10, sticky="ew")

        ttk.Button(musteri_buton_frame, text="Müşteri Ekle", command=self.musteri_ekle).pack(side="left", padx=5,
                                                                                             fill="x", expand=True)
        ttk.Button(musteri_buton_frame, text="Müşteri Güncelle", command=self.musteri_guncelle).pack(side="left",
                                                                                                     padx=5, fill="x",
                                                                                                     expand=True)
        ttk.Button(musteri_buton_frame, text="Müşteri Sil", command=self.musteri_sil).pack(side="left", padx=5,
                                                                                           fill="x", expand=True)
        ttk.Button(musteri_buton_frame, text="Temizle", command=self.temizle_musteri).pack(side="left", padx=5,
                                                                                           fill="x", expand=True)

        # Müşteri listesi (Treeview)
        musteri_liste_frame = ttk.Frame(parent_frame, padding="10 0 0 0")
        musteri_liste_frame.pack(pady=10, padx=0, fill="both", expand=True)

        musteri_scroll_y = ttk.Scrollbar(musteri_liste_frame, orient="vertical")
        musteri_scroll_x = ttk.Scrollbar(musteri_liste_frame, orient="horizontal")

        self.musteri_liste = ttk.Treeview(musteri_liste_frame,
                                          columns=("id", "Ad/Unvan", "Adres", "Telefon", "E-posta"),
                                          show="headings",
                                          yscrollcommand=musteri_scroll_y.set,
                                          xscrollcommand=musteri_scroll_x.set)

        musteri_scroll_y.config(command=self.musteri_liste.yview)
        musteri_scroll_x.config(command=self.musteri_liste.xview)

        musteri_columns_info = {
            "id": {"text": "ID", "width": 50, "minwidth": 40},
            "Ad/Unvan": {"text": "Ad/Unvan", "width": 150, "minwidth": 100},
            "Adres": {"text": "Adres", "width": 200, "minwidth": 150},
            "Telefon": {"text": "Telefon", "width": 100, "minwidth": 90},
            "E-posta": {"text": "E-posta", "width": 150, "minwidth": 120}
        }

        for col_name, info in musteri_columns_info.items():
            self.musteri_liste.heading(col_name, text=info["text"], anchor="w")
            self.musteri_liste.column(col_name, width=info["width"], minwidth=info["minwidth"], stretch=tk.NO)

        self.musteri_liste.grid(row=0, column=0, sticky="nsew")
        musteri_scroll_y.grid(row=0, column=1, sticky="ns")
        musteri_scroll_x.grid(row=1, column=0, sticky="ew")

        musteri_liste_frame.grid_rowconfigure(0, weight=1)
        musteri_liste_frame.grid_columnconfigure(0, weight=1)

        self.musteri_liste.bind("<<TreeviewSelect>>", self.musteri_liste_secildi)

    def musteri_ekle(self):
        ad = self.musteri_ad_entry.get().strip()
        adres = self.musteri_adres_entry.get()
        telefon = self.musteri_telefon_entry.get()
        eposta = self.musteri_eposta_entry.get()

        if not ad:
            self.show_error("Hata", "Lütfen müşteri adı/unvanı girin.")
            return

        if self.db_manager.get_customer_by_name(ad, self.kullanici_id):
            self.show_error("Hata", f"'{ad}' adında bir müşteri zaten mevcut.")
            return

        self.db_manager.insert_customer(ad, adres, telefon, eposta, self.kullanici_id)
        self.show_message("Başarılı", f"'{ad}' müşterisi başarıyla eklendi.")
        self.listele_musteriler()
        self.temizle_musteri()

    def musteri_guncelle(self):
        if not self.selected_customer_id:
            self.show_warning("Uyarı", "Lütfen güncellemek için bir müşteri seçin.")
            return

        ad = self.musteri_ad_entry.get().strip()
        adres = self.musteri_adres_entry.get()
        telefon = self.musteri_telefon_entry.get()
        eposta = self.musteri_eposta_entry.get()

        if not ad:
            self.show_error("Hata", "Lütfen müşteri adı/unvanı girin.")
            return

        # Eğer ad değiştiyse ve yeni ad zaten varsa hata ver
        old_name = self.musteri_liste.item(self.selected_customer_id, "values")[1]
        if ad != old_name and self.db_manager.get_customer_by_name(ad, self.kullanici_id):
            self.show_error("Hata", f"'{ad}' adında başka bir müşteri zaten mevcut.")
            return

        self.db_manager.update_customer(self.selected_customer_id, ad, adres, telefon, eposta, self.kullanici_id)
        self.show_message("Başarılı", f"'{ad}' müşterisi başarıyla güncellendi.")
        self.listele_musteriler()
        self.temizle_musteri()
        self.selected_customer_id = None

        # Fatura/tekliflerdeki müşteri adını güncelle (eğer müşteri adı değiştiyse)
        if ad != old_name:
            self.db_manager.update_invoice_customer_name(old_name, ad, self.kullanici_id)
            self.listele_fatura_teklifler()

    def musteri_sil(self):
        if not self.selected_customer_id:
            self.show_warning("Uyarı", "Lütfen silmek için bir müşteri seçin.")
            return

        item_values = self.musteri_liste.item(self.selected_customer_id, "values")
        customer_name = item_values[1]

        # Bu müşterinin kullanıldığı fatura/teklif var mı kontrol et
        invoice_count = self.db_manager.count_invoices_by_customer(customer_name, self.kullanici_id)
        if invoice_count > 0:
            self.show_error("Hata",
                            f"Bu müşteriye ait {invoice_count} adet fatura/teklif mevcut. Önce bunları silmelisiniz.")
            return

        if messagebox.askyesno("Onay", f"Seçili müşteriyi ('{customer_name}') silmek istediğinizden emin misiniz?"):
            self.db_manager.delete_customer(self.selected_customer_id, self.kullanici_id)
            self.show_message("Başarılı", "Müşteri başarıyla silindi.")
            self.listele_musteriler()
            self.temizle_musteri()
            self.selected_customer_id = None

    def temizle_musteri(self):
        self.musteri_ad_entry.delete(0, tk.END)
        self.musteri_adres_entry.delete(0, tk.END)
        self.musteri_telefon_entry.delete(0, tk.END)
        self.musteri_eposta_entry.delete(0, tk.END)
        self.selected_customer_id = None
        self.musteri_liste.selection_remove(self.musteri_liste.selection())

    def listele_musteriler(self, combobox_widget=None):
        """Müşterileri veritabanından çeker ve Treeview'da/Combobox'ta listeler."""
        musteriler = self.db_manager.get_customers(self.kullanici_id)

        if combobox_widget:  # Eğer bir combobox widget'ı belirtildiyse sadece onu güncelle
            musteri_adlari = [m[1] for m in musteriler]
            combobox_widget['values'] = musteri_adlari
            if not combobox_widget.get() in musteri_adlari:
                combobox_widget.set("")  # Eğer seçili müşteri yoksa veya kaldırıldıysa temizle
            return

        # Treeview'ı güncelle
        for i in self.musteri_liste.get_children():
            self.musteri_liste.delete(i)
        for row in musteriler:
            self.musteri_liste.insert("", "end", values=row)

        # Fatura/Teklif ekranındaki müşteri combobox'ını da güncelle
        if hasattr(self, 'fatura_musteri_combobox'):
            musteri_adlari = [m[1] for m in musteriler]
            self.fatura_musteri_combobox['values'] = musteri_adlari
            if not self.fatura_musteri_var.get() in musteri_adlari:
                self.fatura_musteri_var.set("")  # Eğer seçili müşteri yoksa veya kaldırıldıysa temizle

    def musteri_liste_secildi(self, event):
        """Müşteri Treeview'ında bir satır seçildiğinde giriş alanlarını doldurur."""
        selected_item = self.musteri_liste.focus()
        if selected_item:
            values = self.musteri_liste.item(selected_item, "values")
            self.selected_customer_id = values[0]

            self.musteri_ad_entry.delete(0, tk.END)
            self.musteri_ad_entry.insert(0, values[1])
            self.musteri_adres_entry.delete(0, tk.END)
            self.musteri_adres_entry.insert(0, values[2])
            self.musteri_telefon_entry.delete(0, tk.END)
            self.musteri_telefon_entry.insert(0, values[3])
            self.musteri_eposta_entry.delete(0, tk.END)
            self.musteri_eposta_entry.insert(0, values[4])
        else:
            self.temizle_musteri()

    # --- Envanter Yönetimi Sekmesi Fonksiyonları ---
    def _envanter_yonetimi_arayuzu_olustur(self, parent_frame):
        """Envanter yönetimi sekmesinin arayüzünü oluşturur."""
        urun_frame = ttk.LabelFrame(parent_frame, text="Ürün / Hizmet Ekle / Düzenle / Sil", padding=15)
        urun_frame.pack(pady=10, padx=0, fill="x", expand=False)

        urun_frame.grid_columnconfigure(1, weight=1)

        input_widgets = [
            ("Ad:", "urun_ad_entry", None, "Entry"),
            ("Stok Miktarı:", "urun_stok_entry", None, "Entry"),
            ("Alış Fiyatı (₺):", "urun_alis_fiyat_entry", None, "Entry"),
            ("Satış Fiyatı (₺):", "urun_satis_fiyat_entry", None, "Entry"),
            ("KDV Oranı (%):", "urun_kdv_oran_entry", None, "Entry"),
        ]

        for i, (label_text, var_name, values, widget_type) in enumerate(input_widgets):
            ttk.Label(urun_frame, text=label_text).grid(row=i, column=0, padx=10, pady=5, sticky="w")
            entry = ttk.Entry(urun_frame, width=40)
            entry.grid(row=i, column=1, padx=10, pady=5, sticky="ew")
            setattr(self, var_name, entry)
            if var_name == "urun_kdv_oran_entry":
                entry.insert(0, "18.0")  # Varsayılan KDV oranı

        # Ürün butonları
        urun_buton_frame = ttk.Frame(urun_frame, padding="10 0 0 0")
        urun_buton_frame.grid(row=len(input_widgets), column=0, columnspan=2, pady=10, sticky="ew")

        ttk.Button(urun_buton_frame, text="Ürün Ekle", command=self.urun_ekle).pack(side="left", padx=5, fill="x",
                                                                                    expand=True)
        ttk.Button(urun_buton_frame, text="Ürün Güncelle", command=self.urun_guncelle).pack(side="left", padx=5,
                                                                                            fill="x", expand=True)
        ttk.Button(urun_buton_frame, text="Ürün Sil", command=self.urun_sil).pack(side="left", padx=5, fill="x",
                                                                                  expand=True)
        ttk.Button(urun_buton_frame, text="Temizle", command=self.temizle_urun).pack(side="left", padx=5, fill="x",
                                                                                     expand=True)

        # Ürün listesi (Treeview)
        urun_liste_frame = ttk.Frame(parent_frame, padding="10 0 0 0")
        urun_liste_frame.pack(pady=10, padx=0, fill="both", expand=True)

        urun_scroll_y = ttk.Scrollbar(urun_liste_frame, orient="vertical")
        urun_scroll_x = ttk.Scrollbar(urun_liste_frame, orient="horizontal")

        self.urun_liste = ttk.Treeview(urun_liste_frame,
                                       columns=("id", "Ad", "Stok", "Alış Fiyatı", "Satış Fiyatı", "KDV Oranı"),
                                       show="headings",
                                       yscrollcommand=urun_scroll_y.set,
                                       xscrollcommand=urun_scroll_x.set)

        urun_scroll_y.config(command=self.urun_liste.yview)
        urun_scroll_x.config(command=self.urun_liste.xview)

        urun_columns_info = {
            "id": {"text": "ID", "width": 50},
            "Ad": {"text": "Ad", "width": 150},
            "Stok": {"text": "Stok", "width": 80},
            "Alış Fiyatı": {"text": "Alış Fiyatı (₺)", "width": 100},
            "Satış Fiyatı": {"text": "Satış Fiyatı (₺)", "width": 100},
            "KDV Oranı": {"text": "KDV Oranı (%)", "width": 90}
        }

        for col_name, info in urun_columns_info.items():
            self.urun_liste.heading(col_name, text=info["text"], anchor="w")
            self.urun_liste.column(col_name, width=info["width"], stretch=tk.NO)

        self.urun_liste.grid(row=0, column=0, sticky="nsew")
        urun_scroll_y.grid(row=0, column=1, sticky="ns")
        urun_scroll_x.grid(row=1, column=0, sticky="ew")

        urun_liste_frame.grid_rowconfigure(0, weight=1)
        urun_liste_frame.grid_columnconfigure(0, weight=1)

        self.urun_liste.bind("<<TreeviewSelect>>", self.urun_liste_secildi)

    def urun_ekle(self):
        ad = self.urun_ad_entry.get().strip()
        stok_str = self.urun_stok_entry.get()
        alis_fiyat_str = self.urun_alis_fiyat_entry.get()
        satis_fiyat_str = self.urun_satis_fiyat_entry.get()
        kdv_oran_str = self.urun_kdv_oran_entry.get()

        if not ad or not stok_str or not satis_fiyat_str:
            self.show_error("Hata", "Lütfen ürün adı, stok ve satış fiyatını girin.")
            return

        try:
            stok = float(stok_str)
            satis_fiyat = float(satis_fiyat_str)
            alis_fiyat = float(alis_fiyat_str) if alis_fiyat_str else 0.0  # Opsiyonel
            kdv_oran = float(kdv_oran_str) if kdv_oran_str else 0.0

            if stok < 0 or satis_fiyat <= 0 or alis_fiyat < 0 or kdv_oran < 0:
                self.show_error("Hata",
                                "Miktar, fiyat ve KDV oranları pozitif veya sıfır olmalıdır (satış fiyatı pozitif).")
                return

        except ValueError:
            self.show_error("Hata", "Miktar, fiyat ve KDV oranları geçerli sayılar olmalıdır.")
            return

        if self.db_manager.get_product_by_name(ad, self.kullanici_id):
            self.show_error("Hata", f"'{ad}' adında bir ürün/hizmet zaten mevcut.")
            return

        self.db_manager.insert_product(ad, stok, alis_fiyat, satis_fiyat, kdv_oran, self.kullanici_id)
        self.show_message("Başarılı", f"'{ad}' ürünü başarıyla eklendi.")
        self.listele_urunler()
        self.temizle_urun()

    def urun_guncelle(self):
        if not self.selected_product_id:
            self.show_warning("Uyarı", "Lütfen güncellemek için bir ürün seçin.")
            return

        ad = self.urun_ad_entry.get().strip()
        stok_str = self.urun_stok_entry.get()
        alis_fiyat_str = self.urun_alis_fiyat_entry.get()
        satis_fiyat_str = self.urun_satis_fiyat_entry.get()
        kdv_oran_str = self.urun_kdv_oran_entry.get()

        if not ad or not stok_str or not satis_fiyat_str:
            self.show_error("Hata", "Lütfen ürün adı, stok ve satış fiyatını girin.")
            return

        try:
            stok = float(stok_str)
            satis_fiyat = float(satis_fiyat_str)
            alis_fiyat = float(alis_fiyat_str) if alis_fiyat_str else 0.0
            kdv_oran = float(kdv_oran_str) if kdv_oran_str else 0.0

            if stok < 0 or satis_fiyat <= 0 or alis_fiyat < 0 or kdv_oran < 0:
                self.show_error("Hata",
                                "Miktar, fiyat ve KDV oranları pozitif veya sıfır olmalıdır (satış fiyatı pozitif).")
                return

        except ValueError:
            self.show_error("Hata", "Miktar, fiyat ve KDV oranları geçerli sayılar olmalıdır.")
            return

        old_name = self.urun_liste.item(self.selected_product_id, "values")[1]
        if ad != old_name and self.db_manager.get_product_by_name(ad, self.kullanici_id):
            self.show_error("Hata", f"'{ad}' adında başka bir ürün/hizmet zaten mevcut.")
            return

        self.db_manager.update_product(self.selected_product_id, ad, stok, alis_fiyat, satis_fiyat, kdv_oran,
                                       self.kullanici_id)
        self.show_message("Başarılı", f"'{ad}' ürünü başarıyla güncellendi.")
        self.listele_urunler()
        self.temizle_urun()
        self.selected_product_id = None

    def urun_sil(self):
        if not self.selected_product_id:
            self.show_warning("Uyarı", "Lütfen silmek için bir ürün seçin.")
            return

        item_values = self.urun_liste.item(self.selected_product_id, "values")
        product_name = item_values[1]

        # Ürünün fatura/tekliflerde kullanılıp kullanılmadığını kontrol etmek daha karmaşık
        # Şimdilik, fatura/tekliflerdeki ürünler JSON içinde olduğu için doğrudan kontrol edemiyoruz.
        # Bu yüzden burada bir uyarı vermiyoruz, doğrudan siliyoruz. Ancak gerçek bir uygulamada bu kontrol edilmeli.

        if messagebox.askyesno("Onay", f"Seçili ürünü ('{product_name}') silmek istediğinizden emin misiniz?"):
            self.db_manager.delete_product(self.selected_product_id, self.kullanici_id)
            self.show_message("Başarılı", "Ürün başarıyla silindi.")
            self.listele_urunler()
            self.temizle_urun()
            self.selected_product_id = None

    def temizle_urun(self):
        self.urun_ad_entry.delete(0, tk.END)
        self.urun_stok_entry.delete(0, tk.END)
        self.urun_alis_fiyat_entry.delete(0, tk.END)
        self.urun_satis_fiyat_entry.delete(0, tk.END)
        self.urun_kdv_oran_entry.delete(0, tk.END)
        self.urun_kdv_oran_entry.insert(0, "18.0")  # Varsayılan KDV oranı
        self.selected_product_id = None
        self.urun_liste.selection_remove(self.urun_liste.selection())

    def listele_urunler(self, combobox_widget=None):
        """Ürünleri veritabanından çeker ve Treeview'da/Combobox'ta listeler."""
        urunler = self.db_manager.get_products(self.kullanici_id)

        if combobox_widget:  # Eğer bir combobox widget'ı belirtildiyse sadece onu güncelle
            urun_adlari = [u[1] for u in urunler]
            combobox_widget['values'] = urun_adlari
            if not combobox_widget.get() in urun_adlari:
                combobox_widget.set("")  # Eğer seçili ürün yoksa veya kaldırıldıysa temizle
            return

        # Treeview'ı güncelle
        for i in self.urun_liste.get_children():
            self.urun_liste.delete(i)
        for row in urunler:
            self.urun_liste.insert("", "end", values=row)

        # Fatura/Teklif ekranındaki ürün combobox'ını da güncelle
        if hasattr(self, 'fatura_urun_sec_combobox'):
            urun_adlari = [u[1] for u in urunler]
            self.fatura_urun_sec_combobox['values'] = urun_adlari
            if not self.fatura_urun_sec_var.get() in urun_adlari:
                self.fatura_urun_sec_var.set("")  # Eğer seçili ürün yoksa veya kaldırıldıysa temizle

    def urun_liste_secildi(self, event):
        """Ürün Treeview'ında bir satır seçildiğinde giriş alanlarını doldurur."""
        selected_item = self.urun_liste.focus()
        if selected_item:
            values = self.urun_liste.item(selected_item, "values")
            self.selected_product_id = values[0]

            self.urun_ad_entry.delete(0, tk.END)
            self.urun_ad_entry.insert(0, values[1])
            self.urun_stok_entry.delete(0, tk.END)
            self.urun_stok_entry.insert(0, str(values[2]))
            self.urun_alis_fiyat_entry.delete(0, tk.END)
            self.urun_alis_fiyat_entry.insert(0, str(values[3]))
            self.urun_satis_fiyat_entry.delete(0, tk.END)
            self.urun_satis_fiyat_entry.insert(0, str(values[4]))
            self.urun_kdv_oran_entry.delete(0, tk.END)
            self.urun_kdv_oran_entry.insert(0, str(values[5]))
        else:
            self.temizle_urun()

    # --- Vergi Raporları Sekmesi Fonksiyonları ---
    def _vergi_raporlari_arayuzu_olustur(self, parent_frame):
        """Vergi raporları sekmesinin arayüzünü oluşturur."""
        tax_report_frame = ttk.LabelFrame(parent_frame, text="KDV Raporu Oluştur", padding=15)
        tax_report_frame.pack(padx=10, pady=10, fill="x", expand=False)

        ttk.Label(tax_report_frame, text="Başlangıç Tarihi:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.tax_start_date_entry = DateEntry(tax_report_frame, width=12, background='darkblue', foreground='white',
                                              borderwidth=2, date_pattern='yyyy-mm-dd')
        self.tax_start_date_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.tax_start_date_entry.set_date((datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"))

        ttk.Label(tax_report_frame, text="Bitiş Tarihi:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.tax_end_date_entry = DateEntry(tax_report_frame, width=12, background='darkblue', foreground='white',
                                            borderwidth=2, date_pattern='yyyy-mm-dd')
        self.tax_end_date_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        self.tax_end_date_entry.set_date(datetime.now().strftime("%Y-%m-%d"))

        generate_report_button = ttk.Button(tax_report_frame, text="Rapor Oluştur", command=self.vergi_raporu_olustur)
        generate_report_button.grid(row=2, column=0, columnspan=2, pady=10, sticky="ew")

        # Rapor Sonuç Çerçevesi
        report_results_frame = ttk.LabelFrame(parent_frame, text="KDV Rapor Sonuçları", padding=15)
        report_results_frame.pack(padx=10, pady=10, fill="both", expand=True)

        self.kdv_report_text = tk.Text(report_results_frame, height=15, wrap="word", state="disabled")
        self.kdv_report_text.pack(fill="both", expand=True, padx=5, pady=5)

        kdv_report_scrollbar = ttk.Scrollbar(report_results_frame, orient="vertical",
                                             command=self.kdv_report_text.yview)
        self.kdv_report_text.configure(yscrollcommand=kdv_report_scrollbar.set)
        kdv_report_scrollbar.pack(side="right", fill="y")

    def vergi_raporu_olustur(self):
        """Belirli bir tarih aralığı için KDV raporunu oluşturur."""
        start_date = self.tax_start_date_entry.get()
        end_date = self.tax_end_date_entry.get()

        if not start_date or not end_date:
            self.show_error("Hata", "Lütfen başlangıç ve bitiş tarihini girin.")
            return

        try:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
            if start_dt > end_dt:
                self.show_error("Hata", "Başlangıç tarihi bitiş tarihinden sonra olamaz.")
                return
        except ValueError:
            self.show_error("Hata", "Geçersiz tarih formatı. LütfenYYYY-MM-DD formatını kullanın.")
            return

        total_sales_kdv = self.db_manager.get_total_sales_kdv(start_date, end_date, self.kullanici_id)
        invoice_items_jsons = self.db_manager.get_invoice_jsons_for_tax_report(start_date, end_date, self.kullanici_id)

        kdv_by_rate = {}
        for item_json_tuple in invoice_items_jsons:
            if item_json_tuple and item_json_tuple[0]:
                items = json.loads(item_json_tuple[0])
                for item in items:
                    rate = item.get("kdv_orani", 0.0)
                    amount = item.get("kdv_miktari", 0.0)
                    kdv_by_rate[rate] = kdv_by_rate.get(rate, 0.0) + amount

        report_content = f"--- KDV Raporu ({start_date} - {end_date}) ---\n\n"
        report_content += f"Toplam Satış KDV'si: {total_sales_kdv:.2f} TL\n\n"
        report_content += "KDV Oranlarına Göre Dağılım:\n"

        if not kdv_by_rate:
            report_content += "   Belirtilen tarih aralığında KDV bilgisi bulunan satış işlemi yok.\n"
        else:
            for rate, amount in sorted(kdv_by_rate.items()):
                report_content += f"   KDV %{rate:.2f}: {amount:.2f} TL\n"

        self.kdv_report_text.config(state="normal")
        self.kdv_report_text.delete("1.0", tk.END)
        self.kdv_report_text.insert("1.0", report_content)
        self.kdv_report_text.config(state="disabled")

    # --- YENİ EKLENEN: Tasarruf Hedefleri Sekmesi Fonksiyonları ---
    def _tasarruf_hedefleri_arayuzu_olustur(self, parent_frame):
        """Tasarruf hedefleri sekmesinin arayüzünü oluşturur."""
        input_frame = ttk.LabelFrame(parent_frame, text="Tasarruf Hedefi Ekle/Güncelle", padding=15)
        input_frame.pack(padx=10, pady=10, fill="x")

        input_frame.grid_columnconfigure(1, weight=1)

        ttk.Label(input_frame, text="Hedef Adı:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.goal_name_entry = ttk.Entry(input_frame)
        self.goal_name_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(input_frame, text="Hedef Miktar (TL):").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.goal_target_amount_entry = ttk.Entry(input_frame)
        self.goal_target_amount_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(input_frame, text="Mevcut Birikmiş Miktar (TL):").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.goal_current_amount_entry = ttk.Entry(input_frame)
        self.goal_current_amount_entry.grid(row=2, column=1, padx=5, pady=5, sticky="ew")
        self.goal_current_amount_entry.insert(0, "0.00")  # Varsayılan olarak 0

        ttk.Label(input_frame, text="Hedef Tarihi:").grid(row=3, column=0, padx=5, pady=5, sticky="w")
        self.goal_target_date_entry = DateEntry(input_frame, width=12, background='darkblue', foreground='white',
                                                borderwidth=2, date_pattern='yyyy-mm-dd')
        self.goal_target_date_entry.grid(row=3, column=1, padx=5, pady=5, sticky="ew")
        self.goal_target_date_entry.set_date(datetime.now().strftime("%Y-%m-%d"))  # Varsayılan bugünün tarihi

        ttk.Label(input_frame, text="Açıklama/Notlar:").grid(row=4, column=0, padx=5, pady=5, sticky="w")
        self.goal_notes_text = tk.Text(input_frame, height=3, width=30)
        self.goal_notes_text.grid(row=4, column=1, padx=5, pady=5, sticky="ew")

        action_buttons_frame = ttk.Frame(input_frame)
        action_buttons_frame.grid(row=5, column=0, columnspan=2, pady=10)
        ttk.Button(action_buttons_frame, text="Hedef Ekle", command=self.kaydet_tasarruf_hedefi).pack(side="left",
                                                                                                      padx=5)
        ttk.Button(action_buttons_frame, text="Hedefi Güncelle", command=self.guncelle_tasarruf_hedefi).pack(
            side="left", padx=5)
        ttk.Button(action_buttons_frame, text="Temizle", command=self.temizle_tasarruf_hedefi).pack(side="left", padx=5)

        list_frame = ttk.LabelFrame(parent_frame, text="Mevcut Tasarruf Hedefleri")  # parent_frame kullanıldı
        list_frame.pack(padx=10, pady=10, fill="both", expand=True)

        self.savings_goal_tree = ttk.Treeview(list_frame, columns=("ID", "Hedef Adı", "Hedef Miktar", "Biriken Miktar",
                                                                   "Kalan Miktar", "Hedef Tarihi", "Durum"),
                                              show="headings")
        self.savings_goal_tree.heading("ID", text="ID")
        self.savings_goal_tree.heading("Hedef Adı", text="Hedef Adı")
        self.savings_goal_tree.heading("Hedef Miktar", text="Hedef Miktar (₺)")
        self.savings_goal_tree.heading("Biriken Miktar", text="Biriken Miktar (₺)")
        self.savings_goal_tree.heading("Kalan Miktar", text="Kalan Miktar (₺)")
        self.savings_goal_tree.heading("Hedef Tarihi", text="Hedef Tarihi")
        self.savings_goal_tree.heading("Durum", text="Durum")

        self.savings_goal_tree.column("ID", width=50, anchor="center")
        self.savings_goal_tree.column("Hedef Adı", width=150, anchor="w")
        self.savings_goal_tree.column("Hedef Miktar", width=100, anchor="e")
        self.savings_goal_tree.column("Biriken Miktar", width=100, anchor="e")
        self.savings_goal_tree.column("Kalan Miktar", width=100, anchor="e")
        self.savings_goal_tree.column("Hedef Tarihi", width=100, anchor="center")
        self.savings_goal_tree.column("Durum", width=100, anchor="center")

        self.savings_goal_tree.pack(fill="both", expand=True)
        self.savings_goal_tree.bind("<<TreeviewSelect>>", self.tasarruf_hedefi_liste_secildi)

        goal_scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.savings_goal_tree.yview)
        self.savings_goal_tree.configure(yscrollcommand=goal_scrollbar.set)
        goal_scrollbar.pack(side="right", fill="y")

        goal_action_buttons_bottom = ttk.Frame(list_frame)
        goal_action_buttons_bottom.pack(pady=5)
        ttk.Button(goal_action_buttons_bottom, text="Hedefi Sil", command=self.sil_tasarruf_hedefi).pack(side="left",
                                                                                                         padx=5)
        ttk.Button(goal_action_buttons_bottom, text="Miktar Ekle", command=self.miktar_ekle_tasarruf_hedefi).pack(
            side="left", padx=5)
        ttk.Button(goal_action_buttons_bottom, text="Durumu Güncelle",
                   command=self.durum_guncelle_tasarruf_hedefi).pack(side="left", padx=5)

    def kaydet_tasarruf_hedefi(self):
        name = self.goal_name_entry.get().strip()
        target_amount_str = self.goal_target_amount_entry.get()
        current_amount_str = self.goal_current_amount_entry.get()
        target_date = self.goal_target_date_entry.get()
        description = self.goal_notes_text.get("1.0", tk.END).strip()

        if not name or not target_amount_str or not target_date:
            self.show_error("Hata", "Lütfen hedef adı, hedef miktar ve hedef tarihini girin.")
            return

        try:
            target_amount = float(target_amount_str)
            current_amount = float(current_amount_str)
            if target_amount <= 0 or current_amount < 0:
                self.show_error("Hata", "Hedef miktar pozitif, mevcut miktar sıfır veya pozitif olmalıdır.")
                return
            # Hedef tarihi geçmiş mi kontrolü (Opsiyonel, duruma göre esnetilebilir)
            if datetime.strptime(target_date, '%Y-%m-%d').date() < datetime.now().date():
                messagebox.showwarning("Uyarı", "Hedef tarihi geçmiş bir tarih olamaz. Gelecek bir tarih seçin.")
                return
        except ValueError:
            self.show_error("Hata", "Miktar geçerli bir sayı olmalı, tarih formatıYYYY-MM-DD olmalıdır.")
            return

        # Hedef adı benzersiz mi kontrol et
        existing_goals = self.db_manager.get_savings_goals(self.kullanici_id)
        for goal in existing_goals:
            if goal[1] == name:  # goal[1] hedefin adıdır
                self.show_error("Hata", f"'{name}' adında bir tasarruf hedefi zaten mevcut.")
                return

        if self.db_manager.insert_savings_goal(name, target_amount, current_amount, target_date, description,
                                               self.kullanici_id):
            self.show_message("Başarılı", f"'{name}' tasarruf hedefi başarıyla eklendi.")
            self.listele_tasarruf_hedefleri()
            self.temizle_tasarruf_hedefi()
        else:
            self.show_error("Hata", "Tasarruf hedefi eklenirken bir sorun oluştu.")

    def guncelle_tasarruf_hedefi(self):
        if not self.selected_savings_goal_id:
            self.show_warning("Uyarı", "Lütfen güncellemek için bir tasarruf hedefi seçin.")
            return

        name = self.goal_name_entry.get().strip()
        target_amount_str = self.goal_target_amount_entry.get()
        current_amount_str = self.goal_current_amount_entry.get()
        target_date = self.goal_target_date_entry.get()
        description = self.goal_notes_text.get("1.0", tk.END).strip()

        if not name or not target_amount_str or not target_date:
            self.show_error("Hata", "Lütfen hedef adı, hedef miktar ve hedef tarihini girin.")
            return

        try:
            target_amount = float(target_amount_str)
            current_amount = float(current_amount_str)
            if target_amount <= 0 or current_amount < 0:
                self.show_error("Hata", "Hedef miktar pozitif, mevcut miktar sıfır veya pozitif olmalıdır.")
                return
            if datetime.strptime(target_date, '%Y-%m-%d').date() < datetime.now().date():
                messagebox.showwarning("Uyarı", "Hedef tarihi geçmiş bir tarih olamaz. Gelecek bir tarih seçin.")
                return
        except ValueError:
            self.show_error("Hata", "Miktar geçerli bir sayı olmalı, tarih formatıYYYY-MM-DD olmalıdır.")
            return

        # Hedef adı benzersiz mi kontrol et (güncellenen hedef hariç)
        existing_goals = self.db_manager.get_savings_goals(self.kullanici_id)
        for goal in existing_goals:
            if goal[0] != self.selected_savings_goal_id and goal[1] == name:
                self.show_error("Hata", f"'{name}' adında başka bir tasarruf hedefi zaten mevcut.")
                return

        if self.db_manager.update_savings_goal(self.selected_savings_goal_id, name, target_amount, current_amount,
                                               target_date, description, self.kullanici_id):
            self.show_message("Başarılı", f"'{name}' tasarruf hedefi başarıyla güncellendi.")
            self.listele_tasarruf_hedefleri()
            self.temizle_tasarruf_hedefi()
            self.selected_savings_goal_id = None
        else:
            self.show_error("Hata", "Tasarruf hedefi güncellenirken bir sorun oluştu.")

    def sil_tasarruf_hedefi(self):
        if not self.selected_savings_goal_id:
            self.show_warning("Uyarı", "Lütfen silmek için bir tasarruf hedefi seçin.")
            return

        item_values = self.savings_goal_tree.item(self.selected_savings_goal_id, "values")
        goal_name = item_values[1]

        if messagebox.askyesno("Onay", f"Seçili tasarruf hedefini ('{goal_name}') silmek istediğinizden emin misiniz?"):
            if self.db_manager.delete_savings_goal(self.selected_savings_goal_id, self.kullanici_id):
                self.show_message("Başarılı", "Tasarruf hedefi başarıyla silindi.")
                self.listele_tasarruf_hedefleri()
                self.temizle_tasarruf_hedefi()
                self.selected_savings_goal_id = None
            else:
                self.show_error("Hata", "Tasarruf hedefi silinirken bir sorun oluştu.")

    def temizle_tasarruf_hedefi(self):
        self.goal_name_entry.delete(0, tk.END)
        self.goal_target_amount_entry.delete(0, tk.END)
        self.goal_current_amount_entry.delete(0, tk.END)
        self.goal_target_amount_entry.insert(0, "0.00")  # Varsayılan olarak 0
        self.goal_current_amount_entry.insert(0, "0.00")  # Varsayılan olarak 0
        self.goal_target_date_entry.set_date(datetime.now().strftime("%Y-%m-%d"))  # Varsayılan bugünün tarihi
        self.goal_notes_text.delete("1.0", tk.END)
        self.selected_savings_goal_id = None
        self.savings_goal_tree.selection_remove(self.savings_goal_tree.selection())

    def listele_tasarruf_hedefleri(self):
        """Tasarruf hedeflerini veritabanından çeker ve Treeview'da listeler."""
        for i in self.savings_goal_tree.get_children():
            self.savings_goal_tree.delete(i)

        goals = self.db_manager.get_savings_goals(self.kullanici_id)
        for goal in goals:
            # goal formatı: (id, name, target_amount, current_amount, target_date, description, status)
            goal_id, name, target_amount, current_amount, target_date, description, status = goal

            remaining_amount = target_amount - current_amount
            if remaining_amount < 0:  # Eğer hedef aşıldıysa
                remaining_amount = 0

            # Durumu otomatik güncelle (sadece eğer zaten tamamlanmadıysa ve miktar hedefe ulaştıysa)
            if current_amount >= target_amount and status != "Tamamlandı":
                status = "Tamamlandı"
                self.db_manager.update_savings_goal_status(goal_id, "Tamamlandı",
                                                           self.kullanici_id)  # DB'yi de güncelle

            self.savings_goal_tree.insert("", "end", values=(
                goal_id, name, f"{target_amount:.2f}", f"{current_amount:.2f}", f"{remaining_amount:.2f}", target_date,
                status
            ))

    def tasarruf_hedefi_liste_secildi(self, event):
        """Tasarruf Hedefi Treeview'da bir satır seçildiğinde giriş alanlarını doldurur."""
        selected_item = self.savings_goal_tree.focus()
        if selected_item:
            self.selected_savings_goal_id = self.savings_goal_tree.item(selected_item, "values")[0]
            goal_detail = self.db_manager.get_savings_goal_by_id(self.selected_savings_goal_id, self.kullanici_id)

            if goal_detail:
                # goal_detail formatı: (id, name, target_amount, current_amount, target_date, description, status)
                self.temizle_tasarruf_hedefi()  # Önce temizle

                self.goal_name_entry.insert(0, goal_detail[1])
                self.goal_target_amount_entry.insert(0, f"{goal_detail[2]:.2f}")
                self.goal_current_amount_entry.insert(0, f"{goal_detail[3]:.2f}")
                self.goal_target_date_entry.set_date(
                    goal_detail[4])  # Tarih str olarak gelebilir, DateEntry otomatik dönüştürür
                self.goal_notes_text.insert("1.0", goal_detail[5] or "")  # None ise boş string ekle
        else:
            self.temizle_tasarruf_hedefi()

    def miktar_ekle_tasarruf_hedefi(self):
        selected_item = self.savings_goal_tree.focus()
        if not selected_item:
            self.show_error("Hata", "Lütfen miktar eklenecek bir tasarruf hedefi seçin.")
            return

        goal_id = self.savings_goal_tree.item(selected_item, "values")[0]
        goal_name = self.savings_goal_tree.item(selected_item, "values")[1]  # Sadece ismini al

        goal_detail = self.db_manager.get_savings_goal_by_id(goal_id, self.kullanici_id)
        if not goal_detail:
            self.show_error("Hata", "Hedef detayları bulunamadı.")
            return

        current_status = goal_detail[6]
        if current_status == "Tamamlandı" or current_status == "İptal Edildi":
            self.show_error("Hata", f"Bu hedef ({current_status}) durumunda. Miktar ekleyemezsiniz.")
            return

        amount_to_add_str = simpledialog.askstring("Miktar Ekle",
                                                   f"'{goal_name}' hedefine ne kadar miktar eklemek istersiniz?",
                                                   parent=self.root)

        if amount_to_add_str is None:  # Kullanıcı iptal etti
            return

        try:
            amount_to_add = float(amount_to_add_str)
            if amount_to_add <= 0:
                self.show_error("Hata", "Eklenecek miktar pozitif bir sayı olmalıdır.")
                return
        except ValueError:
            self.show_error("Hata", "Geçersiz miktar. Lütfen sayı girin.")
            return

        # goal_detail formatı: (id, name, target_amount, current_amount, target_date, description, status)
        current_amount = goal_detail[3]
        new_total_amount = current_amount + amount_to_add

        if self.db_manager.update_savings_goal_current_amount(goal_id, new_total_amount, self.kullanici_id):
            self.show_message("Başarılı", f"'{goal_name}' hedefine {amount_to_add:.2f} TL eklendi.")
            self.listele_tasarruf_hedefleri()  # Listeyi güncelleyerek durum kontrolünü de tetikler
        else:
            self.show_error("Hata", "Tasarruf hedefine miktar eklenirken bir sorun oluştu.")

    def durum_guncelle_tasarruf_hedefi(self):
        selected_item = self.savings_goal_tree.focus()
        if not selected_item:
            self.show_error("Hata", "Lütfen durumu güncellenecek bir tasarruf hedefi seçin.")
            return

        goal_id = self.savings_goal_tree.item(selected_item, "values")[0]
        goal_name = self.savings_goal_tree.item(selected_item, "values")[1]

        new_status = simpledialog.askstring("Durum Güncelle",
                                            f"'{goal_name}' hedefinin yeni durumunu girin (Devam Ediyor, Tamamlandı, İptal Edildi):",
                                            parent=self.root)

        if new_status is None:  # Kullanıcı iptal etti
            return

        valid_statuses = ["Devam Ediyor", "Tamamlandı", "İptal Edildi"]
        if new_status not in valid_statuses:
            self.show_error("Hata", "Geçersiz durum. Lütfen 'Devam Ediyor', 'Tamamlandı' veya 'İptal Edildi' girin.")
            return

        if self.db_manager.update_savings_goal_status(goal_id, new_status, self.kullanici_id):
            self.show_message("Başarılı", f"'{goal_name}' hedefinin durumu '{new_status}' olarak güncellendi.")
            self.listele_tasarruf_hedefleri()
        else:
            self.show_error("Hata", "Tasarruf hedefi durumu güncellenirken bir sorun oluştu.")

