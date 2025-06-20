# fingo_app.py
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import sqlite3
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from tkcalendar import DateEntry
import json
import os
import sys
import pandas as pd

# Gerekli modüllerin import edilmesi
from database_manager import DatabaseManager
# pdf_generator'dan hem sınıfı hem de font adını ve register fonksiyonunu import et
from pdf_generator import PDFGenerator, GLOBAL_REPORTLAB_FONT_NAME, _register_pdf_font
from ai_predictor import AIPredictor
from utils import validate_numeric_input  # utils'den fonksiyonu doğrudan import et

# Matplotlib için Türkçe font ayarı
# Bu ayar, `_register_pdf_font` içindeki GLOBAL_REPORTLAB_FONT_NAME'i kullanır.
plt.rcParams['font.sans-serif'] = [GLOBAL_REPORTLAB_FONT_NAME, 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# Uygulama başlatıldığında fontu ReportLab'a kaydet
# Font dosyasının uygulama ile aynı dizinde olduğundan emin olun (örn: ArialCustom.ttf).
_register_pdf_font(f"{GLOBAL_REPORTLAB_FONT_NAME}.ttf")


class GelirGiderUygulamasi:
    def __init__(self, root, db_manager, kullanici_id, username):
        """
        Gelir Gider Uygulamasının ana arayüzünü ve iş mantığını başlatır.
        """
        self.root = root
        self.db_manager = db_manager
        self.conn = self.db_manager.conn
        self.cursor = self.db_manager.cursor
        self.kullanici_id = kullanici_id
        self.username = username
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.selected_item_id = None
        self.selected_recurring_item_id = None
        self.selected_savings_goal_id = None
        self.selected_customer_id = None
        self.selected_product_id = None
        self.selected_invoice_offer_id = None
        self.selected_category_id = None

        # Grafik değişkenlerini başlangıçta None olarak ayarla
        self.fig_category = None
        self.canvas_category = None
        self.fig_balance = None
        self.canvas_balance = None

        # PDFGenerator'ı db_manager ve user_id ile başlat
        self.pdf_generator = PDFGenerator(db_manager=self.db_manager, user_id=self.kullanici_id)
        self.ai_predictor = AIPredictor(db_manager=self.db_manager, user_id=self.kullanici_id)

        # validate_numeric_input fonksiyonunu bir kere kaydet
        self.validate_numeric_cmd = self.root.register(self._validate_numeric_input_wrapper)

        self._create_main_ui()  # Yeni ana UI oluşturma metodunu çağırıyoruz

        # AI modelini UI oluşturulduktan sonra yükle/eğit
        self.ai_predictor.load_or_train_model()

        # İlk sekmelerin yüklenmesi ve veri çekimi notebook sekme değişim olayına bağlandı
        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_change)

        # Uygulama açılışında ilk sekmenin içeriğini yükle
        self._load_current_tab_content()

        print(
            f"DEBUG: GelirGiderUygulamasi başlatıldı. Kullanıcı ID: {self.kullanici_id}, Kullanıcı Adı: {self.username}")

    def _validate_numeric_input_wrapper(self, P):
        """utils.py'deki validate_numeric_input fonksiyonunu sarmalayan wrapper."""
        return validate_numeric_input(P)

    def on_closing(self):
        """Uygulama kapatılırken veritabanı bağlantısını kapatır."""
        if messagebox.askokcancel("Çıkış", "Uygulamadan çıkmak istediğinizden emin misiniz?"):
            self.db_manager.close()
            self.root.destroy()

    def _create_main_ui(self):
        """Ana kullanıcı arayüzünü sekmeli bir yapıya göre oluşturur."""
        self.main_frame = ttk.Frame(self.root, padding="10")
        self.main_frame.pack(expand=True, fill="both")

        # Üst kısım: Başlık ve Kullanıcı Bilgisi
        top_bar_frame = ttk.Frame(self.main_frame)
        top_bar_frame.pack(fill="x", pady=5)

        ttk.Label(top_bar_frame, text="Gelişmiş Gelir - Gider Takip Uygulaması", font=("Arial", 16, "bold"),
                  foreground="#0056b3").pack(side="left", padx=10)
        self.user_label = ttk.Label(top_bar_frame, text=f"Kullanıcı: {self.username}", font=("Arial", 10))
        self.user_label.pack(side="right", padx=10)

        # Sekmeli Notebook Oluşturma
        self.notebook = ttk.Notebook(self.main_frame)
        self.notebook.pack(expand=True, fill="both", padx=10, pady=5)

        # Sekme Çerçeveleri (self. ile erişilebilir olmalı)
        self.transactions_tab_frame = ttk.Frame(self.notebook)
        self.reports_analysis_tab_frame = ttk.Frame(self.notebook)
        self.invoice_offer_tab_frame = ttk.Frame(self.notebook)
        self.recurring_transactions_tab_frame = ttk.Frame(self.notebook)
        self.savings_goals_tab_frame = ttk.Frame(self.notebook)
        self.customer_management_tab_frame = ttk.Frame(self.notebook)
        self.product_management_tab_frame = ttk.Frame(self.notebook)
        self.category_management_tab_frame = ttk.Frame(self.notebook)
        # self.tax_report_tab_frame = ttk.Frame(self.notebook) # Kaldırıldı, entegre edildi

        self.notebook.add(self.transactions_tab_frame, text="Ana İşlemler")
        self.notebook.add(self.reports_analysis_tab_frame, text="Gelişmiş Araçlar & Raporlar")
        self.notebook.add(self.invoice_offer_tab_frame, text="Fatura & Teklifler")
        self.notebook.add(self.recurring_transactions_tab_frame, text="Tekrarlayan İşlemler")
        self.notebook.add(self.savings_goals_tab_frame, text="Tasarruf Hedefleri")
        self.notebook.add(self.customer_management_tab_frame, text="Müşteri Yönetimi")
        self.notebook.add(self.product_management_tab_frame, text="Ürün/Hizmet Yönetimi")
        self.notebook.add(self.category_management_tab_frame, text="Kategori Yönetimi")
        # self.notebook.add(self.tax_report_tab_frame, text="Vergi Raporu") # Kaldırıldı

        # Her sekmeye ilgili UI'ları oluştur
        self._create_transactions_ui(self.transactions_tab_frame)
        self._create_reports_analysis_ui(self.reports_analysis_tab_frame)
        self._create_invoice_offer_ui(self.invoice_offer_tab_frame)
        self._create_recurring_transactions_ui(self.recurring_transactions_tab_frame)
        self._create_savings_goals_ui(self.savings_goals_tab_frame)
        self._create_customer_management_ui(self.customer_management_tab_frame)
        self._create_product_management_ui(self.product_management_tab_frame)
        self._create_category_management_ui(self.category_management_tab_frame)
        # self._create_tax_report_ui(self.tax_report_tab_frame) # Kaldırıldı

        self.guncelle_bakiye()  # Bakiye bilgisini güncelle (istersen bu bilgiyi de ana ekrana veya bir sekmeye taşıyabilirsin)

        # Varsayılan olarak ilk sekmeyi göster
        self.notebook.select(self.transactions_tab_frame)

    def _clear_content_frame(self):
        """Bu metod artık kullanılmayacak, sekmeler arası geçiş notebook tarafından yönetiliyor."""
        pass

    def _create_widgets(self):
        """Bu metodun içeriği artık sekmelerin içine taşındığı için boş kalacak."""
        pass

    def _on_tab_change(self, event):
        """Sekme değiştiğinde ilgili içeriği yükler."""
        selected_tab = self.notebook.tab(self.notebook.select(), "text")
        print(f"DEBUG: Selected tab changed to: {selected_tab}")

        # Her sekmeye özel yükleme/listeleme fonksiyonlarını çağır
        if selected_tab == "Ana İşlemler":
            self.listele_islemler()
            self.guncelle_kategori_listesi()  # İşlem ekranı için kategori listesini güncelle
            self.on_transaction_type_selected()  # Varsayılan işlem tipi seçildiğinde kategorileri yükle
        elif selected_tab == "Gelişmiş Araçlar & Raporlar":
            # Grafikler artık butonlarla ayrı pencerelerde açılacak, vergi raporu da butonla tetiklenecek
            pass
        elif selected_tab == "Fatura & Teklifler":
            self.listele_faturalar_teklifler()
            self.update_customer_combobox()  # Müşteri listesini güncelle
            self.update_product_combobox_for_invoice_items()  # Ürün listesini güncelle
            self.generate_document_number()  # Yeni belge numarası oluştur
        elif selected_tab == "Tekrarlayan İşlemler":
            self.listele_tekrarlayan_islemler()
            self.guncelle_kategori_listesi()  # Tekrarlayan işlem ekranı için kategori listesini güncelle
            self.on_recurring_type_selected()  # Varsayılan işlem tipi seçildiğinde kategorileri yükle
        elif selected_tab == "Tasarruf Hedefleri":
            self.listele_tasarruf_hedefleri()
        elif selected_tab == "Müşteri Yönetimi":
            self.listele_musteriler()
        elif selected_tab == "Ürün/Hizmet Yönetimi":
            self.listele_urunler()
        elif selected_tab == "Kategori Yönetimi":
            self.listele_kategoriler()

        self.guncelle_bakiye()  # Bakiye bilgisini her sekme değişiminde güncelle

    # --- Genel Yardımcı Fonksiyonlar ---
    def show_message(self, title, message):
        """Bilgi mesajı gösterir."""
        messagebox.showinfo(title, message)

    def show_error(self, title, message):
        """Hata mesajı gösterir."""
        messagebox.showerror(title, message)

    def _parse_date_input(self, date_str):
        """
        Farklı tarih formatlarını (MM/DD/YY, YYYY-MM-DD, DD.MM.YYYY) ayrıştırır ve
        YYYY-MM-DD string formatında döner. Hata durumunda ValueError yükseltir.
        """
        if not date_str:
            raise ValueError("Tarih alanı boş olamaz.")

        # tkcalendar varsayılan MM/DD/YY
        try:
            return datetime.strptime(date_str, '%m/%d/%y').strftime('%Y-%m-%d')
        except ValueError:
            pass

        # ISO formatı YYYY-MM-DD
        try:
            return datetime.strptime(date_str, '%Y-%m-%d').strftime('%Y-%m-%d')
        except ValueError:
            pass

        # DD.MM.YYYY formatı
        try:
            return datetime.strptime(date_str, '%d.%m.%Y').strftime('%Y-%m-%d')
        except ValueError:
            pass

        # Eğer hiçbiri eşleşmezse hata fırlat
        raise ValueError("Geçersiz tarih formatı. Lütfen GG.AA.YYYY, AA/GG/YY veya YYYY-AA-GG formatlarını kullanın.")

    def guncelle_bakiye(self):
        """Mevcut bakiyeyi veritabanından alıp günceller."""
        bakiye = self.db_manager.get_balance(self.kullanici_id)
        # Bakiye artık sol menüde değil, uygun bir yere yerleştirilebilir (örn: üst bar)
        # self.balance_label.config(text=f"Bakiye: {bakiye:.2f} TL")
        # if bakiye < 0:
        #     self.balance_label.config(foreground="red")
        # else:
        #     self.balance_label.config(foreground="green")

    # --- Ekran Geçiş Fonksiyonları (Artık sekme seçimi yapacak) ---
    def show_transactions_screen(self):
        self.notebook.select(self.transactions_tab_frame)
        self.listele_islemler()

    def show_recurring_transactions_screen(self):
        self.notebook.select(self.recurring_transactions_tab_frame)
        self.listele_tekrarlayan_islemler()

    def show_savings_goals_screen(self):
        self.notebook.select(self.savings_goals_tab_frame)
        self.listele_tasarruf_hedefleri()

    def show_customer_management_screen(self):
        self.notebook.select(self.customer_management_tab_frame)
        self.listele_musteriler()

    def show_product_management_screen(self):
        self.notebook.select(self.product_management_tab_frame)
        self.listele_urunler()

    def show_invoice_offer_screen(self):
        self.notebook.select(self.invoice_offer_tab_frame)
        self.listele_faturalar_teklifler()

    def show_reports_analysis_screen(self):
        self.notebook.select(self.reports_analysis_tab_frame)

    def show_category_management_screen(self):
        self.notebook.select(self.category_management_tab_frame)
        self.listele_kategoriler()

    # --- Kategori Yönetimi UI ve Fonksiyonları ---
    def _create_category_management_ui(self, parent_frame):
        """Kategori yönetimi arayüzünü oluşturur."""
        category_frame = ttk.LabelFrame(parent_frame, text="Kategori Yönetimi", padding="15")
        category_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Giriş Alanları
        input_frame = ttk.Frame(category_frame)
        input_frame.pack(pady=10)

        ttk.Label(input_frame, text="Kategori Adı:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.category_name_entry = ttk.Entry(input_frame, width=30)
        self.category_name_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(input_frame, text="Kategori Tipi:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.category_type_combobox = ttk.Combobox(input_frame, values=["Gelir", "Gider", "Genel"], state="readonly",
                                                   width=27)
        self.category_type_combobox.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        self.category_type_combobox.set("Gider")  # Varsayılan değer

        # Butonlar
        button_frame = ttk.Frame(category_frame)
        button_frame.pack(pady=10)

        ttk.Button(button_frame, text="Kategori Ekle", command=self.kategori_ekle).grid(row=0, column=0, padx=5, pady=5)
        ttk.Button(button_frame, text="Kategori Sil", command=self.kategori_sil).grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(button_frame, text="Temizle", command=self.temizle_kategori_formu).grid(row=0, column=2, padx=5,
                                                                                           pady=5)

        # Kategori Listesi (Treeview)
        self.category_tree = ttk.Treeview(category_frame, columns=("ID", "Adı", "Tipi"), show="headings")
        self.category_tree.heading("ID", text="ID")
        self.category_tree.heading("Adı", text="Kategori Adı")
        self.category_tree.heading("Tipi", text="Tipi")

        self.category_tree.column("ID", width=50, stretch=tk.NO)
        self.category_tree.column("Adı", width=200, stretch=tk.YES)
        self.category_tree.column("Tipi", width=100, stretch=tk.NO)

        self.category_tree.pack(fill="both", expand=True, pady=10)
        self.category_tree.bind("<ButtonRelease-1>", self.kategori_sec)

    def kategori_ekle(self):
        category_name = self.category_name_entry.get().strip()
        category_type = self.category_type_combobox.get()

        if not category_name:
            self.show_error("Hata", "Kategori adı boş olamaz.")
            return
        if not category_type:
            self.show_error("Hata", "Lütfen kategori tipini seçin.")
            return

        if self.db_manager.insert_category(category_name, category_type, self.kullanici_id):
            self.show_message("Başarılı", "Kategori başarıyla eklendi.")
            self.temizle_kategori_formu()
            self.listele_kategoriler()
            self.guncelle_kategori_listesi()
            self.ai_predictor.load_or_train_model(force_retrain=True)
        else:
            self.show_error("Hata", "Kategori eklenirken bir sorun oluştu veya bu kategori adı zaten mevcut.")

    def kategori_sil(self):
        if not self.selected_category_id:
            self.show_error("Hata", "Lütfen silmek istediğiniz kategoriyi seçin.")
            return

        selected_item = self.category_tree.selection()
        if not selected_item:
            self.show_error("Hata", "Lütfen silmek istediğiniz kategoriyi seçin.")
            return
        category_name_to_delete = self.category_tree.item(selected_item, 'values')[1]

        transaction_count = self.db_manager.count_transactions_by_category(category_name_to_delete, self.kullanici_id)

        if transaction_count > 0:
            confirm = messagebox.askyesno(
                "Onay",
                f"'{category_name_to_delete}' kategorisine ait {transaction_count} adet işlem bulunmaktadır. "
                "Bu kategoriyi silerseniz, ilgili işlemlerin kategorisi 'NULL' olarak ayarlanacaktır. Devam etmek istiyor musunuz?"
            )
            if not confirm:
                return

            if not self.db_manager.update_transactions_category_to_null(category_name_to_delete, self.kullanici_id):
                self.show_error("Hata", "İşlemlerin kategorisi güncellenirken bir sorun oluştu.")
                return

        if self.db_manager.delete_category(self.selected_category_id, self.kullanici_id):
            self.show_message("Başarılı", "Kategori başarıyla silindi.")
            self.selected_category_id = None
            self.temizle_kategori_formu()
            self.listele_kategoriler()
            self.guncelle_kategori_listesi()
            self.listele_islemler()
            self.ai_predictor.load_or_train_model(force_retrain=True)
        else:
            self.show_error("Hata", "Kategori silinirken bir sorun oluştu.")

    def kategori_sec(self, event):
        selected_item = self.category_tree.selection()
        if selected_item:
            values = self.category_tree.item(selected_item, 'values')
            self.selected_category_id = values[0]
            if hasattr(self, 'category_name_entry') and self.category_name_entry.winfo_exists():
                self.category_name_entry.delete(0, tk.END)
                self.category_name_entry.insert(0, values[1])
            if hasattr(self, 'category_type_combobox') and self.category_type_combobox.winfo_exists():
                self.category_type_combobox.set(values[2])
        else:
            self.temizle_kategori_formu()

    def listele_kategoriler(self):
        """Kategorileri Treeview'de listeler."""
        if not (hasattr(self, 'category_tree') and self.category_tree.winfo_exists()):
            return

        for item in self.category_tree.get_children():
            self.category_tree.delete(item)

        categories = self.db_manager.get_categories_for_user(self.kullanici_id)
        for cat_id, cat_name, cat_type in categories:
            self.category_tree.insert("", "end", values=(cat_id, cat_name, cat_type))

    def temizle_kategori_formu(self):
        """Kategori ekleme/güncelleme formunu temizler."""
        if hasattr(self, 'category_name_entry') and self.category_name_entry.winfo_exists():
            self.category_name_entry.delete(0, tk.END)
        if hasattr(self, 'category_type_combobox') and self.category_type_combobox.winfo_exists():
            self.category_type_combobox.set("Gider")
        self.selected_category_id = None

    def guncelle_kategori_listesi(self):
        """İşlem ekleme/düzenleme ekranındaki kategori combobox'ını günceller."""
        categories = self.db_manager.get_all_categories(self.kullanici_id)
        if hasattr(self, 'transaction_category_combobox') and self.transaction_category_combobox.winfo_exists():
            self.transaction_category_combobox['values'] = categories
        if hasattr(self, 'recurring_category_combobox') and self.recurring_category_combobox.winfo_exists():
            self.recurring_category_combobox['values'] = categories
        if hasattr(self, 'filter_category_combobox') and self.filter_category_combobox.winfo_exists():
            self.filter_category_combobox['values'] = ["Tümü"] + categories

    # --- İşlem UI ve Fonksiyonları (Gelir/Gider) ---
    def _create_transactions_ui(self, parent_frame):
        """Gelir/Gider İşlemleri arayüzünü oluşturur (Ana İşlemler sekmesi)."""
        transactions_frame = ttk.LabelFrame(parent_frame, text="Yeni İşlem Ekle / Düzenle", padding="15")
        transactions_frame.pack(fill="x", pady=10)

        # Giriş Alanları
        input_grid_frame = ttk.Frame(transactions_frame)
        input_grid_frame.pack(pady=10, fill="x", padx=5)

        # İşlem Türü
        ttk.Label(input_grid_frame, text="İşlem Türü:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.transaction_type_combobox = ttk.Combobox(input_grid_frame, values=["Gelir", "Gider"], state="readonly",
                                                      width=20)
        self.transaction_type_combobox.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.transaction_type_combobox.set("Gider")
        self.transaction_type_combobox.bind("<<ComboboxSelected>>", self.on_transaction_type_selected)

        # Miktar
        ttk.Label(input_grid_frame, text="Miktar (₺):").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.transaction_amount_entry = ttk.Entry(input_grid_frame, validate="key",
                                                  validatecommand=(self.validate_numeric_cmd, '%P'), width=20)
        self.transaction_amount_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        # Kategori
        ttk.Label(input_grid_frame, text="Kategori:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.transaction_category_combobox = ttk.Combobox(input_grid_frame, state="readonly", width=20)
        self.transaction_category_combobox.grid(row=2, column=1, padx=5, pady=5, sticky="ew")
        self.guncelle_kategori_listesi()

        # Açıklama
        ttk.Label(input_grid_frame, text="Açıklama:").grid(row=3, column=0, padx=5, pady=5, sticky="w")
        self.transaction_description_entry = ttk.Entry(input_grid_frame, width=40)
        self.transaction_description_entry.grid(row=3, column=1, padx=5, pady=5, sticky="ew", columnspan=2)

        # Tarih
        ttk.Label(input_grid_frame, text="Tarih:").grid(row=4, column=0, padx=5, pady=5, sticky="w")
        self.transaction_date_entry = DateEntry(input_grid_frame, width=12, background='darkblue',
                                                foreground='white', borderwidth=2, locale='tr_TR')
        self.transaction_date_entry.grid(row=4, column=1, padx=5, pady=5, sticky="ew")

        input_grid_frame.grid_columnconfigure(1, weight=1)
        input_grid_frame.grid_columnconfigure(2, weight=1)

        # Butonlar (Kaydet, Güncelle, Temizle, Sil)
        button_frame = ttk.Frame(transactions_frame)
        button_frame.pack(pady=10, padx=5)

        ttk.Button(button_frame, text="Kaydet", command=self.islem_ekle).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Güncelle", command=self.islem_guncelle).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Temizle", command=self.temizle_islem_formu).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Sil", command=self.islem_sil).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Otomatik Kategori Belirle (AI)", command=self.otomatik_kategori_belirle).pack(
            side="left", padx=5)

        # Filtreleme ve Arama Çerçevesi
        filter_frame = ttk.LabelFrame(parent_frame, text="Filtreleme ve Arama", padding="15")
        filter_frame.pack(fill="x", pady=10)

        filter_grid_frame = ttk.Frame(filter_frame)
        filter_grid_frame.pack(pady=10, fill="x", padx=5)

        # Tür Filtre
        ttk.Label(filter_grid_frame, text="Tür:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.filter_type_combobox = ttk.Combobox(filter_grid_frame, values=["Tümü", "Gelir", "Gider"], state="readonly",
                                                 width=15)
        self.filter_type_combobox.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.filter_type_combobox.set("Tümü")
        self.filter_type_combobox.bind("<<ComboboxSelected>>", self.listele_islemler)

        # Kategori Filtre
        ttk.Label(filter_grid_frame, text="Kategori:").grid(row=0, column=2, padx=5, pady=5, sticky="w")
        self.filter_category_combobox = ttk.Combobox(filter_grid_frame, state="readonly", width=15)
        self.filter_category_combobox['values'] = ["Tümü"] + self.db_manager.get_all_categories(self.kullanici_id)
        self.filter_category_combobox.grid(row=0, column=3, padx=5, pady=5, sticky="ew")
        self.filter_category_combobox.set("Tümü")
        self.filter_category_combobox.bind("<<ComboboxSelected>>", self.listele_islemler)

        # Açıklama/Arama
        ttk.Label(filter_grid_frame, text="Açıklama/Arama:").grid(row=0, column=4, padx=5, pady=5, sticky="w")
        self.search_term_entry = ttk.Entry(filter_grid_frame, width=25)
        self.search_term_entry.grid(row=0, column=5, padx=5, pady=5, sticky="ew")

        # Tarih Aralığı
        ttk.Label(filter_grid_frame, text="Tarih Aralığı:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.filter_start_date_entry = DateEntry(filter_grid_frame, width=12, background='darkblue', foreground='white',
                                                 borderwidth=2, locale='tr_TR')
        self.filter_start_date_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        ttk.Label(filter_grid_frame, text="-").grid(row=1, column=2, padx=2, pady=5)
        self.filter_end_date_entry = DateEntry(filter_grid_frame, width=12, background='darkblue', foreground='white',
                                               borderwidth=2, locale='tr_TR')
        self.filter_end_date_entry.grid(row=1, column=3, padx=5, pady=5, sticky="ew")

        # Filtrele Butonu
        ttk.Button(filter_grid_frame, text="Filtrele", command=self.listele_islemler).grid(row=1, column=4,
                                                                                           columnspan=2, padx=5, pady=5,
                                                                                           sticky="ew")

        filter_grid_frame.grid_columnconfigure(1, weight=1)
        filter_grid_frame.grid_columnconfigure(3, weight=1)
        filter_grid_frame.grid_columnconfigure(5, weight=1)

        # İşlem Listesi (Treeview)
        # Note: self.tree yerine self.transactions_tree kullanılıyor
        self.transactions_tree = ttk.Treeview(parent_frame,
                                              columns=("ID", "Tarih", "Tip", "Miktar", "Kategori", "Açıklama"),
                                              show="headings")
        self.transactions_tree.heading("ID", text="ID")
        self.transactions_tree.heading("Tarih", text="Tarih")
        self.transactions_tree.heading("Tip", text="Tür")
        self.transactions_tree.heading("Miktar", text="Miktar (₺)")
        self.transactions_tree.heading("Kategori", text="Kategori")
        self.transactions_tree.heading("Açıklama", text="Açıklama")

        self.transactions_tree.column("ID", width=50, stretch=tk.NO)
        self.transactions_tree.column("Tarih", width=100, stretch=tk.NO)
        self.transactions_tree.column("Tip", width=70, stretch=tk.NO)
        self.transactions_tree.column("Miktar", width=100, stretch=tk.NO)
        self.transactions_tree.column("Kategori", width=150, stretch=tk.YES)
        self.transactions_tree.column("Açıklama", width=250, stretch=tk.YES)

        self.transactions_tree.pack(fill="both", expand=True, pady=10, padx=10)
        self.transactions_tree.bind("<ButtonRelease-1>", self.islem_sec)

        # Export Buttons Frame
        export_buttons_frame = ttk.Frame(parent_frame)
        export_buttons_frame.pack(pady=10)

        ttk.Button(export_buttons_frame, text="PDF Olarak Dışa Aktar", command=self.export_transactions_to_pdf).pack(
            side="left", padx=5)
        ttk.Button(export_buttons_frame, text="Excel Olarak Dışa Aktar",
                   command=self.export_transactions_to_excel).pack(side="left", padx=5)

    def on_transaction_type_selected(self, event=None):
        """İşlem tipi değiştiğinde kategori seçeneklerini günceller."""
        selected_type = self.transaction_type_combobox.get()
        categories = self.db_manager.get_categories_for_user(self.kullanici_id)

        filtered_categories = []
        for cat_id, cat_name, cat_type in categories:
            if cat_type == selected_type or cat_type == "Genel":
                filtered_categories.append(cat_name)

        if hasattr(self, 'transaction_category_combobox') and self.transaction_category_combobox.winfo_exists():
            self.transaction_category_combobox['values'] = filtered_categories
            if filtered_categories:
                self.transaction_category_combobox.set(filtered_categories[0])
            else:
                self.transaction_category_combobox.set("")

    def islem_ekle(self):
        date_str = self.transaction_date_entry.get()
        type = self.transaction_type_combobox.get()
        amount_str = self.transaction_amount_entry.get()
        category = self.transaction_category_combobox.get()
        description = self.transaction_description_entry.get()

        if not type or not amount_str:
            self.show_error("Hata", "Tip ve Miktar alanları boş bırakılamaz.")
            return

        try:
            amount = float(amount_str)
            if amount <= 0:
                self.show_error("Hata", "Miktar pozitif bir sayı olmalıdır.")
                return
        except ValueError:
            self.show_error("Hata", "Geçersiz miktar formatı.")
            return

        try:
            date_obj_str = self._parse_date_input(date_str)
        except ValueError as e:
            self.show_error("Hata", str(e))
            return

        if self.db_manager.insert_transaction(type, amount, category if category else None,
                                              description if description else None, date_obj_str, self.kullanici_id):
            self.show_message("Başarılı", "İşlem başarıyla eklendi.")
            self.temizle_islem_formu()
            self.listele_islemler()
            self.guncelle_bakiye()
            self.ai_predictor.load_or_train_model(force_retrain=True)
        else:
            self.show_error("Hata", "İşlem eklenirken bir sorun oluştu.")

    def islem_guncelle(self):
        if not self.selected_item_id:
            self.show_error("Hata", "Lütfen güncellemek istediğiniz bir işlem seçin.")
            return

        date_str = self.transaction_date_entry.get()
        type = self.transaction_type_combobox.get()
        amount_str = self.transaction_amount_entry.get()
        category = self.transaction_category_combobox.get()
        description = self.transaction_description_entry.get()

        if not type or not amount_str:
            self.show_error("Hata", "Tip ve Miktar alanları boş bırakılamaz.")
            return

        try:
            amount = float(amount_str)
            if amount <= 0:
                self.show_error("Hata", "Miktar pozitif bir sayı olmalıdır.")
                return
        except ValueError:
            self.show_error("Hata", "Geçersiz miktar formatı.")
            return

        try:
            date_obj_str = self._parse_date_input(date_str)
        except ValueError as e:
            self.show_error("Hata", str(e))
            return

        if self.db_manager.update_transaction(self.selected_item_id, type, amount, category if category else None,
                                              description if description else None, date_obj_str, self.kullanici_id):
            self.show_message("Başarılı", "İşlem başarıyla güncellendi.")
            self.temizle_islem_formu()
            self.listele_islemler()
            self.guncelle_bakiye()
            self.ai_predictor.load_or_train_model(force_retrain=True)
        else:
            self.show_error("Hata", "İşlem güncellenirken bir sorun oluştu.")

    def islem_sil(self):
        if not self.selected_item_id:
            self.show_error("Hata", "Lütfen silmek istediğiniz bir işlem seçin.")
            return

        if messagebox.askyesno("Onay", "Seçili işlemi silmek istediğinizden emin misiniz?"):
            if self.db_manager.delete_transaction(self.selected_item_id, self.kullanici_id):
                self.show_message("Başarılı", "İşlem başarıyla silindi.")
                self.temizle_islem_formu()
                self.listele_islemler()
                self.guncelle_bakiye()
                self.ai_predictor.load_or_train_model(force_retrain=True)
            else:
                self.show_error("Hata", "İşlem silinirken bir sorun oluştu.")

    def islem_sec(self, event):
        selected_item = self.transactions_tree.selection()
        if selected_item:
            values = self.transactions_tree.item(selected_item, 'values')
            self.selected_item_id = values[0]
            if hasattr(self, 'transaction_date_entry') and self.transaction_date_entry.winfo_exists():
                try:
                    self.transaction_date_entry.set_date(datetime.strptime(values[1], '%Y-%m-%d'))
                except ValueError:
                    self.show_error("Hata", "Veritabanından okunan tarih formatı geçersiz.")
                    self.transaction_date_entry.set_date(datetime.now())
            if hasattr(self, 'transaction_type_combobox') and self.transaction_type_combobox.winfo_exists():
                self.transaction_type_combobox.set(values[2])
            if hasattr(self, 'transaction_amount_entry') and self.transaction_amount_entry.winfo_exists():
                self.transaction_amount_entry.delete(0, tk.END)
                self.transaction_amount_entry.insert(0, values[3])
            if hasattr(self, 'transaction_category_combobox') and self.transaction_category_combobox.winfo_exists():
                self.transaction_category_combobox.set(values[4])
            if hasattr(self, 'transaction_description_entry') and self.transaction_description_entry.winfo_exists():
                self.transaction_description_entry.delete(0, tk.END)
                self.transaction_description_entry.insert(0, values[5])
        else:
            self.temizle_islem_formu()

    def listele_islemler(self, event=None):
        if not (hasattr(self, 'transactions_tree') and self.transactions_tree.winfo_exists()):
            return

        for item in self.transactions_tree.get_children():
            self.transactions_tree.delete(item)

        type_filter = self.filter_type_combobox.get()
        category_filter = self.filter_category_combobox.get()

        start_date_str = self.filter_start_date_entry.get()
        end_date_str = self.filter_end_date_entry.get()

        start_date_db_format = None
        end_date_db_format = None

        try:
            start_date_db_format = self._parse_date_input(start_date_str) if start_date_str else None
            end_date_db_format = self._parse_date_input(end_date_str) if end_date_str else None
        except ValueError as e:
            self.show_error("Hata", f"Filtre tarih formatı geçersiz: {e}")
            return

        search_term = self.search_term_entry.get().strip()

        transactions = self.db_manager.get_transactions(
            self.kullanici_id,
            type_filter if type_filter != "Tümü" else None,
            category_filter if category_filter != "Tümü" else None,
            start_date_db_format,
            end_date_db_format,
            search_term
        )

        for row in transactions:
            self.transactions_tree.insert("", "end", values=row)

    def temizle_islem_formu(self):
        if hasattr(self, 'transaction_date_entry') and self.transaction_date_entry.winfo_exists():
            self.transaction_date_entry.set_date(datetime.now())
        if hasattr(self, 'transaction_type_combobox') and self.transaction_type_combobox.winfo_exists():
            self.transaction_type_combobox.set("Gider")
            self.on_transaction_type_selected()
        if hasattr(self, 'transaction_amount_entry') and self.transaction_amount_entry.winfo_exists():
            self.transaction_amount_entry.delete(0, tk.END)
        if hasattr(self, 'transaction_category_combobox') and self.transaction_category_combobox.winfo_exists():
            self.transaction_category_combobox.set("")
        if hasattr(self, 'transaction_description_entry') and self.transaction_description_entry.winfo_exists():
            self.transaction_description_entry.delete(0, tk.END)
        self.selected_item_id = None

        if hasattr(self, 'filter_type_combobox') and self.filter_type_combobox.winfo_exists():
            self.filter_type_combobox.set("Tümü")
        if hasattr(self, 'filter_category_combobox') and self.filter_category_combobox.winfo_exists():
            self.filter_category_combobox.set("Tümü")
        if hasattr(self, 'filter_start_date_entry') and self.filter_start_date_entry.winfo_exists():
            self.filter_start_date_entry.set_date(datetime.now() - timedelta(days=30))
        if hasattr(self, 'filter_end_date_entry') and self.filter_end_date_entry.winfo_exists():
            self.filter_end_date_entry.set_date(datetime.now())
        if hasattr(self, 'search_term_entry') and self.search_term_entry.winfo_exists():
            self.search_term_entry.delete(0, tk.END)

    def otomatik_kategori_belirle(self):
        description = self.transaction_description_entry.get().strip()
        if not description:
            self.show_error("Hata", "Lütfen bir açıklama girin.")
            return

        predicted_category = self.ai_predictor.predict_category(description)
        if predicted_category:
            self.transaction_category_combobox.set(predicted_category)
            self.show_message("Tahmin", f"Otomatik Belirlenen Kategori: {predicted_category}")
        else:
            self.show_error("Tahmin Hatası", "Kategori belirlenemedi. Yeterli eğitim verisi olmayabilir.")

    def train_ai_model_manually(self):
        """Kullanıcının AI modelini manuel olarak yeniden eğitmesini sağlar."""
        if messagebox.askyesno("AI Modelini Eğit",
                               "Yapay zeka modelini yeniden eğitmek istediğinizden emin misiniz? Bu işlem biraz zaman alabilir."):
            self.ai_predictor.load_or_train_model(force_retrain=True)
            self.show_message("Eğitim Tamamlandı", "Yapay zeka modeli başarıyla yeniden eğitildi!")
            self.guncelle_kategori_listesi()

    # --- Tekrarlayan İşlemler UI ve Fonksiyonları ---
    def _create_recurring_transactions_ui(self, parent_frame):
        """Tekrarlayan İşlemler arayüzünü oluşturur."""
        recurring_frame = ttk.LabelFrame(parent_frame, text="Tekrarlayan İşlemler", padding="15")
        recurring_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Giriş Alanları
        input_frame = ttk.Frame(recurring_frame)
        input_frame.pack(pady=10)

        ttk.Label(input_frame, text="Açıklama:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.recurring_description_entry = ttk.Entry(input_frame, width=40)
        self.recurring_description_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(input_frame, text="Miktar:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.recurring_amount_entry = ttk.Entry(input_frame, validate="key",
                                                validatecommand=(self.validate_numeric_cmd, '%P'))
        self.recurring_amount_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(input_frame, text="Tip:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.recurring_type_combobox = ttk.Combobox(input_frame, values=["Gelir", "Gider"], state="readonly")
        self.recurring_type_combobox.grid(row=2, column=1, padx=5, pady=5, sticky="ew")
        self.recurring_type_combobox.set("Gider")
        self.recurring_type_combobox.bind("<<ComboboxSelected>>", self.on_recurring_type_selected)

        ttk.Label(input_frame, text="Kategori:").grid(row=3, column=0, padx=5, pady=5, sticky="w")
        self.recurring_category_combobox = ttk.Combobox(input_frame, state="readonly")
        self.recurring_category_combobox.grid(row=3, column=1, padx=5, pady=5, sticky="ew")
        self.guncelle_kategori_listesi()

        ttk.Label(input_frame, text="Başlangıç Tarihi:").grid(row=4, column=0, padx=5, pady=5, sticky="w")
        self.recurring_start_date_entry = DateEntry(input_frame, width=12, background='darkblue', foreground='white',
                                                    borderwidth=2, locale='tr_TR')
        self.recurring_start_date_entry.grid(row=4, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(input_frame, text="Sıklık:").grid(row=5, column=0, padx=5, pady=5, sticky="w")
        self.recurring_frequency_combobox = ttk.Combobox(input_frame, values=["Günlük", "Haftalık", "Aylık", "Yıllık"],
                                                         state="readonly")
        self.recurring_frequency_combobox.grid(row=5, column=1, padx=5, pady=5, sticky="ew")
        self.recurring_frequency_combobox.set("Aylık")

        # Butonlar
        button_frame = ttk.Frame(recurring_frame)
        button_frame.pack(pady=10)

        ttk.Button(button_frame, text="Tekrarlayan İşlem Ekle", command=self.tekrarlayan_islem_ekle).grid(row=0,
                                                                                                          column=0,
                                                                                                          padx=5,
                                                                                                          pady=5)
        ttk.Button(button_frame, text="Tekrarlayan İşlem Güncelle", command=self.tekrarlayan_islem_guncelle).grid(row=0,
                                                                                                                  column=1,
                                                                                                                  padx=5,
                                                                                                                  pady=5)
        ttk.Button(button_frame, text="Tekrarlayan İşlem Sil", command=self.tekrarlayan_islem_sil).grid(row=0, column=2,
                                                                                                        padx=5, pady=5)
        ttk.Button(button_frame, text="Formu Temizle", command=self.temizle_tekrarlayan_islem_formu).grid(row=0,
                                                                                                          column=3,
                                                                                                          padx=5,
                                                                                                          pady=5)
        ttk.Button(button_frame, text="Tekrarlayanları Şimdi Üret", command=self.otomatik_tekrarlayan_islem_uret).grid(
            row=0, column=4, padx=5, pady=5)

        # Tekrarlayan İşlemler Listesi (Treeview)
        self.recurring_tree = ttk.Treeview(recurring_frame,
                                           columns=("ID", "Açıklama", "Miktar", "Tip", "Kategori", "Başlangıç Tarihi",
                                                    "Sıklık", "Son Üretilen Tarih"), show="headings")
        self.recurring_tree.heading("ID", text="ID")
        self.recurring_tree.heading("Açıklama", text="Açıklama")
        self.recurring_tree.heading("Miktar", text="Miktar (TL)")
        self.recurring_tree.heading("Tip", text="Tip")
        self.recurring_tree.heading("Kategori", text="Kategori")
        self.recurring_tree.heading("Başlangıç Tarihi", text="Başlangıç Tarihi")
        self.recurring_tree.heading("Sıklık", text="Sıklık")
        self.recurring_tree.heading("Son Üretilen Tarih", text="Son Üretilen Tarih")

        self.recurring_tree.column("ID", width=50, stretch=tk.NO)
        self.recurring_tree.column("Açıklama", width=150, stretch=tk.YES)
        self.recurring_tree.column("Miktar", width=100, stretch=tk.NO)
        self.recurring_tree.column("Tip", width=70, stretch=tk.NO)
        self.recurring_tree.column("Kategori", width=100, stretch=tk.YES)
        self.recurring_tree.column("Başlangıç Tarihi", width=120, stretch=tk.NO)
        self.recurring_tree.column("Sıklık", width=80, stretch=tk.NO)
        self.recurring_tree.column("Son Üretilen Tarih", width=120, stretch=tk.NO)

        self.recurring_tree.pack(fill="both", expand=True, pady=10)
        self.recurring_tree.bind("<ButtonRelease-1>", self.tekrarlayan_islem_sec)

    def on_recurring_type_selected(self, event=None):
        """Tekrarlayan işlem tipi değiştiğinde kategori seçeneklerini günceller."""
        selected_type = self.recurring_type_combobox.get()
        categories = self.db_manager.get_categories_for_user(self.kullanici_id)

        filtered_categories = []
        for cat_id, cat_name, cat_type in categories:
            if cat_type == selected_type or cat_type == "Genel":
                filtered_categories.append(cat_name)

        if hasattr(self, 'recurring_category_combobox') and self.recurring_category_combobox.winfo_exists():
            self.recurring_category_combobox['values'] = filtered_categories
            if filtered_categories:
                self.recurring_category_combobox.set(filtered_categories[0])
            else:
                self.recurring_category_combobox.set("")

    def tekrarlayan_islem_ekle(self):
        description = self.recurring_description_entry.get().strip()
        amount_str = self.recurring_amount_entry.get()
        type = self.recurring_type_combobox.get()
        category = self.recurring_category_combobox.get()
        start_date_str = self.recurring_start_date_entry.get()
        frequency = self.recurring_frequency_combobox.get()

        if not description or not amount_str or not type or not start_date_str or not frequency:
            self.show_error("Hata", "Tüm alanlar doldurulmalıdır.")
            return

        try:
            amount = float(amount_str)
            if amount <= 0:
                self.show_error("Hata", "Miktar pozitif bir sayı olmalıdır.")
                return
        except ValueError:
            self.show_error("Hata", "Geçersiz miktar formatı.")
            return

        try:
            start_date_db_format = self._parse_date_input(start_date_str)
        except ValueError as e:
            self.show_error("Hata", str(e))
            return

        last_generated_date_db_format = start_date_db_format

        if self.db_manager.insert_recurring_transaction(type, amount, category if category else None, description,
                                                        start_date_db_format, last_generated_date_db_format,
                                                        self.kullanici_id):
            self.show_message("Başarılı", "Tekrarlayan işlem başarıyla eklendi.")
            self.temizle_tekrarlayan_islem_formu()
            self.listele_tekrarlayan_islemler()
        else:
            self.show_error("Hata", "Tekrarlayan işlem eklenirken bir sorun oluştu.")

    def tekrarlayan_islem_guncelle(self):
        if not self.selected_recurring_item_id:
            self.show_error("Hata", "Lütfen güncellemek istediğiniz bir tekrarlayan işlem seçin.")
            return

        description = self.recurring_description_entry.get().strip()
        amount_str = self.recurring_amount_entry.get()
        type = self.recurring_type_combobox.get()
        category = self.recurring_category_combobox.get()
        start_date_str = self.recurring_start_date_entry.get()
        frequency = self.recurring_frequency_combobox.get()

        if not description or not amount_str or not type or not start_date_str or not frequency:
            self.show_error("Hata", "Tüm alanlar doldurulmalıdır.")
            return

        try:
            amount = float(amount_str)
            if amount <= 0:
                self.show_error("Hata", "Miktar pozitif bir sayı olmalıdır.")
                return
        except ValueError:
            self.show_error("Hata", "Geçersiz miktar formatı.")
            return

        try:
            start_date_db_format = self._parse_date_input(start_date_str)
        except ValueError as e:
            self.show_error("Hata", str(e))
            return

        if self.db_manager.update_recurring_transaction(self.selected_recurring_item_id, type, amount,
                                                        category if category else None, description,
                                                        start_date_db_format, frequency, self.kullanici_id):
            self.show_message("Başarılı", "Tekrarlayan işlem başarıyla güncellendi.")
            self.temizle_tekrarlayan_islem_formu()
            self.listele_tekrarlayan_islemler()
        else:
            self.show_error("Hata", "Tekrarlayan işlem güncellenirken bir sorun oluştu.")

    def tekrarlayan_islem_sil(self):
        if not self.selected_recurring_item_id:
            self.show_error("Hata", "Lütfen silmek istediğiniz bir tekrarlayan işlem seçin.")
            return

        if messagebox.askyesno("Onay", "Seçili tekrarlayan işlemi silmek istediğinizden emin misiniz?"):
            if self.db_manager.delete_recurring_transaction(self.selected_recurring_item_id, self.kullanici_id):
                self.show_message("Başarılı", "Tekrarlayan işlem başarıyla silindi.")
                self.temizle_tekrarlayan_islem_formu()
                self.listele_tekrarlayan_islemler()
            else:
                self.show_error("Hata", "Tekrarlayan işlem silinirken bir sorun oluştu.")

    def tekrarlayan_islem_sec(self, event):
        selected_item = self.recurring_tree.selection()
        if selected_item:
            values = self.recurring_tree.item(selected_item, 'values')
            self.selected_recurring_item_id = values[0]
            if hasattr(self, 'recurring_description_entry') and self.recurring_description_entry.winfo_exists():
                self.recurring_description_entry.delete(0, tk.END)
                self.recurring_description_entry.insert(0, values[1])
            if hasattr(self, 'recurring_amount_entry') and self.recurring_amount_entry.winfo_exists():
                self.recurring_amount_entry.delete(0, tk.END)
                self.recurring_amount_entry.insert(0, values[2])
            if hasattr(self, 'recurring_type_combobox') and self.recurring_type_combobox.winfo_exists():
                self.recurring_type_combobox.set(values[3])
            if hasattr(self, 'recurring_category_combobox') and self.recurring_category_combobox.winfo_exists():
                self.recurring_category_combobox.set(values[4])
            if hasattr(self, 'recurring_start_date_entry') and self.recurring_start_date_entry.winfo_exists():
                try:
                    self.recurring_start_date_entry.set_date(datetime.strptime(values[5], '%Y-%m-%d'))
                except ValueError:
                    self.show_error("Hata", "Veritabanından okunan başlangıç tarih formatı geçersiz.")
                    self.recurring_start_date_entry.set_date(datetime.now())
            if hasattr(self, 'recurring_frequency_combobox') and self.recurring_frequency_combobox.winfo_exists():
                if values[6]:
                    self.recurring_frequency_combobox.set(values[6])
                else:
                    self.recurring_frequency_combobox.set("Aylık")
        else:
            self.temizle_tekrarlayan_islem_formu()

    def listele_tekrarlayan_islemler(self):
        if not (hasattr(self, 'recurring_tree') and self.recurring_tree.winfo_exists()):
            return

        for item in self.recurring_tree.get_children():
            self.recurring_tree.delete(item)

        recurring_transactions = self.db_manager.get_recurring_transactions(self.kullanici_id)
        for rec_id, type, amount, category, description, start_date, frequency, last_generated_date in recurring_transactions:
            self.recurring_tree.insert("", "end",
                                       values=(rec_id, description, amount, type, category, start_date, frequency,
                                               last_generated_date))

    def temizle_tekrarlayan_islem_formu(self):
        if hasattr(self, 'recurring_description_entry') and self.recurring_description_entry.winfo_exists():
            self.recurring_description_entry.delete(0, tk.END)
        if hasattr(self, 'recurring_amount_entry') and self.recurring_amount_entry.winfo_exists():
            self.recurring_amount_entry.delete(0, tk.END)
        if hasattr(self, 'recurring_type_combobox') and self.recurring_type_combobox.winfo_exists():
            self.recurring_type_combobox.set("Gider")
            self.on_recurring_type_selected()
        if hasattr(self, 'recurring_category_combobox') and self.recurring_category_combobox.winfo_exists():
            self.recurring_category_combobox.set("")
        if hasattr(self, 'recurring_start_date_entry') and self.recurring_start_date_entry.winfo_exists():
            self.recurring_start_date_entry.set_date(datetime.now())
        if hasattr(self, 'recurring_frequency_combobox') and self.recurring_frequency_combobox.winfo_exists():
            self.recurring_frequency_combobox.set("Aylık")
        self.selected_recurring_item_id = None

    def otomatik_tekrarlayan_islem_uret(self):
        """
        Tekrarlayan işlemleri kontrol eder ve zamanı gelmişse ana işlemlere ekler.
        Uygulama başladığında ve manuel olarak çağrılabilir.
        """
        print("Otomatik tekrarlayan işlem kontrolü başlatıldı.")
        recurring_transactions = self.db_manager.get_recurring_transactions(self.kullanici_id)
        today = datetime.now().date()
        generated_count = 0

        for rec_id, type, amount, category, description, start_date_str, frequency, last_generated_date_str in recurring_transactions:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            last_generated_date = datetime.strptime(last_generated_date_str,
                                                    '%Y-%m-%d').date() if last_generated_date_str else start_date

            next_due_date = last_generated_date

            if last_generated_date < start_date:
                next_due_date = start_date

            while next_due_date <= today:
                if next_due_date > last_generated_date:
                    if self.db_manager.insert_transaction(type, amount, category, description,
                                                          next_due_date.strftime('%Y-%m-%d'), self.kullanici_id):
                        generated_count += 1
                        print(f"Tekrarlayan işlem '{description}' ({next_due_date.strftime('%Y-%m-%d')}) oluşturuldu.")
                    else:
                        print(
                            f"Hata: Tekrarlayan işlem '{description}' ({next_due_date.strftime('%Y-%m-%d')}) eklenirken sorun oluştu.")

                    self.db_manager.update_recurring_transaction_last_generated_date(rec_id,
                                                                                     next_due_date.strftime('%Y-%m-%d'))
                    self.guncelle_bakiye()
                    self.listele_islemler()
                    self.ai_predictor.load_or_train_model(force_retrain=True)

                if frequency == "Günlük":
                    next_due_date += timedelta(days=1)
                elif frequency == "Haftalık":
                    next_due_date += timedelta(weeks=1)
                elif frequency == "Aylık":
                    current_month = next_due_date.month
                    current_year = next_due_date.year
                    next_month = current_month + 1
                    next_year = current_year
                    if next_month > 12:
                        next_month = 1
                        next_year += 1

                    try:
                        next_due_date = next_due_date.replace(year=next_year, month=next_month)
                    except ValueError:
                        last_day_of_next_month = (datetime(next_year, next_month + 1, 1) - timedelta(
                            days=1)).date() if next_month < 12 else (
                                    datetime(next_year + 1, 1, 1) - timedelta(days=1)).date()
                        next_due_date = last_day_of_next_month

                elif frequency == "Yıllık":
                    next_due_date = next_due_date.replace(year=next_due_date.year + 1)
                else:
                    break

        if generated_count > 0:
            self.show_message("Tekrarlayan İşlemler",
                              f"{generated_count} adet tekrarlayan işlem başarıyla oluşturuldu.")
            self.listele_tekrarlayan_islemler()
        else:
            print("Kontrol tamamlandı. Yeni tekrarlayan işlem oluşturulmadı.")

    # --- Tasarruf Hedefleri UI ve Fonksiyonları ---
    def _create_savings_goals_ui(self, parent_frame):
        """Tasarruf Hedefleri arayüzünü oluşturur."""
        goals_frame = ttk.LabelFrame(parent_frame, text="Tasarruf Hedefleri", padding="15")
        goals_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Giriş Alanları
        input_frame = ttk.Frame(goals_frame)
        input_frame.pack(pady=10)

        ttk.Label(input_frame, text="Hedef Adı:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.goal_name_entry = ttk.Entry(input_frame, width=30)
        self.goal_name_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(input_frame, text="Hedef Miktar (TL):").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.goal_target_amount_entry = ttk.Entry(input_frame, validate="key",
                                                  validatecommand=(self.validate_numeric_cmd, '%P'))
        self.goal_target_amount_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(input_frame, text="Mevcut Birikim (TL):").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.goal_current_amount_entry = ttk.Entry(input_frame, validate="key",
                                                   validatecommand=(self.validate_numeric_cmd, '%P'))
        self.goal_current_amount_entry.grid(row=2, column=1, padx=5, pady=5, sticky="ew")
        self.goal_current_amount_entry.insert(0, "0.0")

        ttk.Label(input_frame, text="Hedef Tarihi:").grid(row=3, column=0, padx=5, pady=5, sticky="w")
        self.goal_target_date_entry = DateEntry(input_frame, width=12, background='darkblue', foreground='white',
                                                borderwidth=2, locale='tr_TR')
        self.goal_target_date_entry.grid(row=3, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(input_frame, text="Açıklama:").grid(row=4, column=0, padx=5, pady=5, sticky="w")
        self.goal_description_entry = ttk.Entry(input_frame, width=30)
        self.goal_description_entry.grid(row=4, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(input_frame, text="Durum:").grid(row=5, column=0, padx=5, pady=5, sticky="w")
        self.goal_status_combobox = ttk.Combobox(input_frame, values=["Devam Ediyor", "Tamamlandı", "İptal Edildi"],
                                                 state="readonly")
        self.goal_status_combobox.grid(row=5, column=1, padx=5, pady=5, sticky="ew")
        self.goal_status_combobox.set("Devam Ediyor")

        # Butonlar
        button_frame = ttk.Frame(goals_frame)
        button_frame.pack(pady=10)

        ttk.Button(button_frame, text="Hedef Ekle", command=self.tasarruf_hedefi_ekle).grid(row=0, column=0, padx=5,
                                                                                            pady=5)
        ttk.Button(button_frame, text="Hedef Güncelle", command=self.tasarruf_hedefi_guncelle).grid(row=0, column=1,
                                                                                                    padx=5, pady=5)
        ttk.Button(button_frame, text="Hedef Sil", command=self.tasarruf_hedefi_sil).grid(row=0, column=2, padx=5,
                                                                                          pady=5)
        ttk.Button(button_frame, text="Formu Temizle", command=self.temizle_tasarruf_hedefi_formu).grid(row=0, column=3,
                                                                                                        padx=5, pady=5)
        ttk.Button(button_frame, text="Durum Güncelle", command=self.tasarruf_hedefi_durum_guncelle).grid(row=0,
                                                                                                          column=4,
                                                                                                          padx=5,
                                                                                                          pady=5)

        # Tasarruf Hedefleri Listesi (Treeview)
        self.savings_goals_tree = ttk.Treeview(goals_frame,
                                               columns=("ID", "Adı", "Hedef Miktar", "Biriken", "Hedef Tarihi",
                                                        "Açıklama", "Durum"), show="headings")
        self.savings_goals_tree.heading("ID", text="ID")
        self.savings_goals_tree.heading("Adı", text="Hedef Adı")
        self.savings_goals_tree.heading("Hedef Miktar", text="Hedef Miktar (TL)")
        self.savings_goals_tree.heading("Biriken", text="Biriken (TL)")
        self.savings_goals_tree.heading("Hedef Tarihi", text="Hedef Tarihi")
        self.savings_goals_tree.heading("Açıklama", text="Açıklama")
        self.savings_goals_tree.heading("Durum", text="Durum")

        self.savings_goals_tree.column("ID", width=50, stretch=tk.NO)
        self.savings_goals_tree.column("Adı", width=150, stretch=tk.YES)
        self.savings_goals_tree.column("Hedef Miktar", width=100, stretch=tk.NO)
        self.savings_goals_tree.column("Biriken", width=100, stretch=tk.NO)
        self.savings_goals_tree.column("Hedef Tarihi", width=100, stretch=tk.NO)
        self.savings_goals_tree.column("Açıklama", width=200, stretch=tk.YES)
        self.savings_goals_tree.column("Durum", width=100, stretch=tk.NO)

        self.savings_goals_tree.pack(fill="both", expand=True, pady=10)
        self.savings_goals_tree.bind("<ButtonRelease-1>", self.tasarruf_hedefi_sec)

    def tasarruf_hedefi_ekle(self):
        goal_name = self.goal_name_entry.get().strip()
        target_amount_str = self.goal_target_amount_entry.get()
        current_amount_str = self.goal_current_amount_entry.get()
        target_date_str = self.goal_target_date_entry.get()
        description = self.goal_description_entry.get().strip()

        if not goal_name or not target_amount_str or not current_amount_str or not target_date_str:
            self.show_error("Hata", "Hedef Adı, Hedef Miktar, Mevcut Birikim ve Hedef Tarihi alanları boş olamaz.")
            return

        try:
            target_amount = float(target_amount_str)
            current_amount = float(current_amount_str)
            if target_amount <= 0 or current_amount < 0:
                self.show_error("Hata", "Miktar alanları pozitif sayılar olmalıdır. Biriken miktar sıfır olabilir.")
                return
        except ValueError:
            self.show_error("Hata", "Geçersiz miktar formatı.")
            return

        try:
            target_date_db_format = self._parse_date_input(target_date_str)
        except ValueError as e:
            self.show_error("Hata", str(e))
            return

        if self.db_manager.insert_savings_goal(goal_name, target_amount, current_amount, target_date_db_format,
                                               description if description else None, self.kullanici_id):
            self.show_message("Başarılı", "Tasarruf hedefi başarıyla eklendi.")
            self.temizle_tasarruf_hedefi_formu()
            self.listele_tasarruf_hedefleri()
        else:
            self.show_error("Hata", "Tasarruf hedefi eklenirken bir sorun oluştu.")

    def tasarruf_hedefi_guncelle(self):
        if not self.selected_savings_goal_id:
            self.show_error("Hata", "Lütfen güncellemek istediğiniz bir tasarruf hedefi seçin.")
            return

        goal_name = self.goal_name_entry.get().strip()
        target_amount_str = self.goal_target_amount_entry.get()
        current_amount_str = self.goal_current_amount_entry.get()
        target_date_str = self.goal_target_date_entry.get()
        description = self.goal_description_entry.get().strip()

        if not goal_name or not target_amount_str or not current_amount_str or not target_date_str:
            self.show_error("Hata", "Tüm gerekli alanlar doldurulmalıdır.")
            return

        try:
            target_amount = float(target_amount_str)
            current_amount = float(current_amount_str)
            if target_amount <= 0 or current_amount < 0:
                self.show_error("Hata", "Miktar alanları pozitif sayılar olmalıdır. Biriken miktar sıfır olabilir.")
                return
        except ValueError:
            self.show_error("Hata", "Geçersiz miktar formatı.")
            return

        try:
            target_date_db_format = self._parse_date_input(target_date_str)
        except ValueError as e:
            self.show_error("Hata", str(e))
            return

        if self.db_manager.update_savings_goal(self.selected_savings_goal_id, goal_name, target_amount, current_amount,
                                               target_date_db_format, description if description else None,
                                               self.kullanici_id):
            self.show_message("Başarılı", "Tasarruf hedefi başarıyla güncellendi.")
            self.temizle_tasarruf_hedefi_formu()
            self.listele_tasarruf_hedefleri()
        else:
            self.show_error("Hata", "Tasarruf hedefi güncellenirken bir sorun oluştu.")

    def tasarruf_hedefi_sil(self):
        if not self.selected_savings_goal_id:
            self.show_error("Hata", "Lütfen silmek istediğiniz bir tasarruf hedefi seçin.")
            return

        if messagebox.askyesno("Onay", "Seçili tasarruf hedefini silmek istediğinizden emin misiniz?"):
            if self.db_manager.delete_savings_goal(self.selected_savings_goal_id, self.kullanici_id):
                self.show_message("Başarılı", "Tasarruf hedefi başarıyla silindi.")
                self.temizle_tasarruf_hedefi_formu()
                self.listele_tasarruf_hedefleri()
            else:
                self.show_error("Hata", "Tasarruf hedefi silinirken bir sorun oluştu.")

    def tasarruf_hedefi_sec(self, event):
        selected_item = self.savings_goals_tree.selection()
        if selected_item:
            values = self.savings_goals_tree.item(selected_item, 'values')
            self.selected_savings_goal_id = values[0]
            if hasattr(self, 'goal_name_entry') and self.goal_name_entry.winfo_exists():
                self.goal_name_entry.delete(0, tk.END)
                self.goal_name_entry.insert(0, values[1])
            if hasattr(self, 'goal_target_amount_entry') and self.goal_target_amount_entry.winfo_exists():
                self.goal_target_amount_entry.delete(0, tk.END)
                self.goal_target_amount_entry.insert(0, values[2])
            if hasattr(self, 'goal_current_amount_entry') and self.goal_current_amount_entry.winfo_exists():
                self.goal_current_amount_entry.delete(0, tk.END)
                self.goal_current_amount_entry.insert(0, values[3])
            if hasattr(self, 'goal_target_date_entry') and self.goal_target_date_entry.winfo_exists():
                try:
                    self.goal_target_date_entry.set_date(datetime.strptime(values[4], '%Y-%m-%d'))
                except ValueError:
                    self.show_error("Hata", "Veritabanından okunan hedef tarih formatı geçersiz.")
                    self.goal_target_date_entry.set_date(datetime.now())
            if hasattr(self, 'goal_description_entry') and self.goal_description_entry.winfo_exists():
                self.goal_description_entry.delete(0, tk.END)
                self.goal_description_entry.insert(0, values[5])
            if hasattr(self, 'goal_status_combobox') and self.goal_status_combobox.winfo_exists():
                self.goal_status_combobox.set(values[6])
        else:
            self.temizle_tasarruf_hedefi_formu()

    def listele_tasarruf_hedefleri(self):
        if not (hasattr(self, 'savings_goals_tree') and self.savings_goals_tree.winfo_exists()):
            return

        for item in self.savings_goals_tree.get_children():
            self.savings_goals_tree.delete(item)

        goals = self.db_manager.get_savings_goals(self.kullanici_id)
        for goal_id, name, target, current, target_date, description, status in goals:
            self.savings_goals_tree.insert("", "end",
                                           values=(goal_id, name, f"{target:.2f}", f"{current:.2f}", target_date,
                                                   description, status))

    def temizle_tasarruf_hedefi_formu(self):
        if hasattr(self, 'goal_name_entry') and self.goal_name_entry.winfo_exists():
            self.goal_name_entry.delete(0, tk.END)
        if hasattr(self, 'goal_target_amount_entry') and self.goal_target_amount_entry.winfo_exists():
            self.goal_target_amount_entry.delete(0, tk.END)
        if hasattr(self, 'goal_current_amount_entry') and self.goal_current_amount_entry.winfo_exists():
            self.goal_current_amount_entry.delete(0, tk.END)
            self.goal_current_amount_entry.insert(0, "0.0")
        if hasattr(self, 'goal_target_date_entry') and self.goal_target_date_entry.winfo_exists():
            self.goal_target_date_entry.set_date(datetime.now())
        if hasattr(self, 'goal_description_entry') and self.goal_description_entry.winfo_exists():
            self.goal_description_entry.delete(0, tk.END)
        if hasattr(self, 'goal_status_combobox') and self.goal_status_combobox.winfo_exists():
            self.goal_status_combobox.set("Devam Ediyor")
        self.selected_savings_goal_id = None

    def tasarruf_hedefi_durum_guncelle(self):
        if not self.selected_savings_goal_id:
            self.show_error("Hata", "Lütfen durumunu güncellemek istediğiniz bir tasarruf hedefi seçin.")
            return

        goal_name = self.goal_name_entry.get().strip()
        new_status = self.goal_status_combobox.get()

        if not new_status:
            self.show_error("Hata", "Lütfen yeni bir durum seçin.")
            return

        if self.db_manager.update_savings_goal_status(self.selected_savings_goal_id, new_status, self.kullanici_id):
            self.show_message("Başarılı", f"'{goal_name}' hedefinin durumu '{new_status}' olarak güncellendi.")
            self.listele_tasarruf_hedefleri()
        else:
            self.show_error("Hata", "Tasarruf hedefi durumu güncellenirken bir sorun oluştu.")

    def tasarruf_analizi_yap(self):
        """AI kullanarak tasarruf hedeflerini analiz eder ve sonuçları gösterir."""
        print("fingo_app: Tasarruf Analizi Yap butonu tıklandı.")
        try:
            analysis_report = self.ai_predictor.analyze_and_suggest_savings()

            if hasattr(self, 'savings_analysis_text') and self.savings_analysis_text.winfo_exists():
                self.savings_analysis_text.config(state="normal")
                self.savings_analysis_text.delete("1.0", tk.END)
                self.savings_analysis_text.insert("1.0", analysis_report)
                self.savings_analysis_text.config(state="disabled")
                print("fingo_app: Tasarruf analizi başarıyla tamamlandı ve gösterildi.")
            else:
                print("fingo_app: savings_analysis_text widget'ı henüz oluşturulmamış veya mevcut değil.")


        except Exception as e:
            self.show_error("Hata", f"Tasarruf analizi yapılırken bir hata oluştu: {e}")
            print(f"fingo_app: Tasarruf analizi sırasında hata: {e}")
            if hasattr(self, 'savings_analysis_text') and self.savings_analysis_text.winfo_exists():
                self.savings_analysis_text.config(state="normal")
                self.savings_analysis_text.delete("1.0", tk.END)
                self.savings_analysis_text.insert("1.0", f"Analiz raporu oluşturulamadı: {e}")
                self.savings_analysis_text.config(state="disabled")

    # --- Müşteri Yönetimi UI ve Fonksiyonları ---
    def _create_customer_management_ui(self, parent_frame):
        """Müşteri Yönetimi arayüzünü oluşturur."""
        customer_frame = ttk.LabelFrame(parent_frame, text="Müşteri Yönetimi", padding="15")
        customer_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Giriş Alanları
        input_frame = ttk.Frame(customer_frame)
        input_frame.pack(pady=10)

        ttk.Label(input_frame, text="Adı:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.customer_name_entry = ttk.Entry(input_frame, width=30)
        self.customer_name_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(input_frame, text="Adres:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.customer_address_entry = ttk.Entry(input_frame, width=30)
        self.customer_address_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(input_frame, text="Telefon:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.customer_phone_entry = ttk.Entry(input_frame, width=30)
        self.customer_phone_entry.grid(row=2, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(input_frame, text="E-posta:").grid(row=3, column=0, padx=5, pady=5, sticky="w")
        self.customer_email_entry = ttk.Entry(input_frame, width=30)
        self.customer_email_entry.grid(row=3, column=1, padx=5, pady=5, sticky="ew")

        # Butonlar
        button_frame = ttk.Frame(customer_frame)
        button_frame.pack(pady=10)

        ttk.Button(button_frame, text="Müşteri Ekle", command=self.musteri_ekle).grid(row=0, column=0, padx=5, pady=5)
        ttk.Button(button_frame, text="Müşteri Güncelle", command=self.musteri_guncelle).grid(row=0, column=1, padx=5,
                                                                                              pady=5)
        ttk.Button(button_frame, text="Müşteri Sil", command=self.musteri_sil).grid(row=0, column=2, padx=5, pady=5)
        ttk.Button(button_frame, text="Temizle", command=self.temizle_musteri_formu).grid(row=0, column=3, padx=5,
                                                                                          pady=5)

        # Müşteri Listesi (Treeview)
        self.customer_tree = ttk.Treeview(customer_frame, columns=("ID", "Adı", "Adres", "Telefon", "E-posta"),
                                          show="headings")
        self.customer_tree.heading("ID", text="ID")
        self.customer_tree.heading("Adı", text="Adı")
        self.customer_tree.heading("Adres", text="Adres")
        self.customer_tree.heading("Telefon", text="Telefon")
        self.customer_tree.heading("E-posta", text="E-posta")

        self.customer_tree.column("ID", width=50, stretch=tk.NO)
        self.customer_tree.column("Adı", width=150, stretch=tk.YES)
        self.customer_tree.column("Adres", width=200, stretch=tk.YES)
        self.customer_tree.column("Telefon", width=100, stretch=tk.NO)
        self.customer_tree.column("E-posta", width=150, stretch=tk.YES)

        self.customer_tree.pack(fill="both", expand=True, pady=10)
        self.customer_tree.bind("<ButtonRelease-1>", self.musteri_sec)

    def musteri_ekle(self):
        name = self.customer_name_entry.get().strip()
        address = self.customer_address_entry.get().strip()
        phone = self.customer_phone_entry.get().strip()
        email = self.customer_email_entry.get().strip()

        if not name:
            self.show_error("Hata", "Müşteri adı boş olamaz.")
            return

        if self.db_manager.insert_customer(name, address if address else None, phone if phone else None,
                                           email if email else None, self.kullanici_id):
            self.show_message("Başarılı", "Müşteri başarıyla eklendi.")
            self.temizle_musteri_formu()
            self.listele_musteriler()
        else:
            self.show_error("Hata", "Müşteri eklenirken bir sorun oluştu veya bu müşteri adı zaten mevcut.")

    def musteri_guncelle(self):
        if not self.selected_customer_id:
            self.show_error("Hata", "Lütfen güncellemek istediğiniz bir müşteri seçin.")
            return

        name = self.customer_name_entry.get().strip()
        address = self.customer_address_entry.get().strip()
        phone = self.customer_phone_entry.get().strip()
        email = self.customer_email_entry.get().strip()

        selected_item = self.customer_tree.selection()
        current_customer_name = self.customer_tree.item(selected_item[0], 'values')[1] if selected_item else None

        if not name:
            self.show_error("Hata", "Müşteri adı boş olamaz.")
            return

        if name != current_customer_name and self.db_manager.get_customer_by_name(name, self.kullanici_id):
            self.show_error("Hata", f"'{name}' isimli bir müşteri zaten mevcut.")
            return

        if self.db_manager.update_customer(self.selected_customer_id, name, address if address else None,
                                           phone if phone else None, email if email else None, self.kullanici_id):
            if name != current_customer_name:
                self.db_manager.update_invoice_customer_name(current_customer_name, name, self.kullanici_id)

            self.show_message("Başarılı", "Müşteri başarıyla güncellendi.")
            self.temizle_musteri_formu()
            self.listele_musteriler()
            self.listele_faturalar_teklifler()
        else:
            self.show_error("Hata", "Müşteri güncellenirken bir sorun oluştu.")

    def musteri_sil(self):
        if not self.selected_customer_id:
            self.show_error("Hata", "Lütfen silmek istediğiniz bir müşteri seçin.")
            return

        selected_item = self.customer_tree.selection()
        customer_name_to_delete = self.customer_tree.item(selected_item[0], 'values')[1] if selected_item else None

        invoice_count = self.db_manager.count_invoices_by_customer(customer_name_to_delete, self.kullanici_id)
        if invoice_count > 0:
            self.show_error("Hata",
                            f"Bu müşteriye ait {invoice_count} adet fatura/teklif bulunmaktadır. Lütfen önce bu fatura/teklifleri silin.")
            return

        if messagebox.askyesno("Onay", "Seçili müşteriyi silmek istediğinizden emin misiniz?"):
            if self.db_manager.delete_customer(self.selected_customer_id, self.kullanici_id):
                self.show_message("Başarılı", "Müşteri başarıyla silindi.")
                self.temizle_musteri_formu()
                self.listele_musteriler()
            else:
                self.show_error("Hata", "Müşteri silinirken bir sorun oluştu.")

    def musteri_sec(self, event):
        selected_item = self.customer_tree.selection()
        if selected_item:
            values = self.customer_tree.item(selected_item, 'values')
            self.selected_customer_id = values[0]
            if hasattr(self, 'customer_name_entry') and self.customer_name_entry.winfo_exists():
                self.customer_name_entry.delete(0, tk.END)
                self.customer_name_entry.insert(0, values[1])
            if hasattr(self, 'customer_address_entry') and self.customer_address_entry.winfo_exists():
                self.customer_address_entry.delete(0, tk.END)
                self.customer_address_entry.insert(0, values[2])
            if hasattr(self, 'customer_phone_entry') and self.customer_phone_entry.winfo_exists():
                self.customer_phone_entry.delete(0, tk.END)
                self.customer_phone_entry.insert(0, values[3])
            if hasattr(self, 'customer_email_entry') and self.customer_email_entry.winfo_exists():
                self.customer_email_entry.delete(0, tk.END)
                self.customer_email_entry.insert(0, values[4])
        else:
            self.temizle_musteri_formu()

    def listele_musteriler(self):
        if not (hasattr(self, 'customer_tree') and self.customer_tree.winfo_exists()):
            return

        for item in self.customer_tree.get_children():
            self.customer_tree.delete(item)

        customers = self.db_manager.get_customers(self.kullanici_id)
        for cust_id, name, address, phone, email in customers:
            self.customer_tree.insert("", "end", values=(cust_id, name, address, phone, email))

    def temizle_musteri_formu(self):
        if hasattr(self, 'customer_name_entry') and self.customer_name_entry.winfo_exists():
            self.customer_name_entry.delete(0, tk.END)
        if hasattr(self, 'customer_address_entry') and self.customer_address_entry.winfo_exists():
            self.customer_address_entry.delete(0, tk.END)
        if hasattr(self, 'customer_phone_entry') and self.customer_phone_entry.winfo_exists():
            self.customer_phone_entry.delete(0, tk.END)
        if hasattr(self, 'customer_email_entry') and self.customer_email_entry.winfo_exists():
            self.customer_email_entry.delete(0, tk.END)
        self.selected_customer_id = None

    # --- Ürün/Hizmet Yönetimi ---
    def _create_product_management_ui(self, parent_frame):
        """Ürün/Hizmet Yönetimi arayüzünü oluşturur."""
        product_frame = ttk.LabelFrame(parent_frame, text="Ürün / Hizmet Yönetimi", padding="15")
        product_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Giriş Alanları
        input_frame = ttk.Frame(product_frame)
        input_frame.pack(pady=10)

        ttk.Label(input_frame, text="Ürün Adı:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.product_name_entry = ttk.Entry(input_frame, width=30)
        self.product_name_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(input_frame, text="Stok Miktarı:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.product_stock_entry = ttk.Entry(input_frame, validate="key",
                                             validatecommand=(self.validate_numeric_cmd, '%P'))
        self.product_stock_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        self.product_stock_entry.insert(0, "0.0")

        ttk.Label(input_frame, text="Alış Fiyatı (TL):").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.product_purchase_price_entry = ttk.Entry(input_frame, validate="key",
                                                      validatecommand=(self.validate_numeric_cmd, '%P'))
        self.product_purchase_price_entry.grid(row=2, column=1, padx=5, pady=5, sticky="ew")
        self.product_purchase_price_entry.insert(0, "0.0")

        ttk.Label(input_frame, text="Satış Fiyatı (TL):").grid(row=3, column=0, padx=5, pady=5, sticky="w")
        self.product_selling_price_entry = ttk.Entry(input_frame, validate="key",
                                                     validatecommand=(self.validate_numeric_cmd, '%P'))
        self.product_selling_price_entry.grid(row=3, column=1, padx=5, pady=5, sticky="ew")
        self.product_selling_price_entry.insert(0, "0.0")

        ttk.Label(input_frame, text="KDV Oranı (%):").grid(row=4, column=0, padx=5, pady=5, sticky="w")
        self.product_kdv_rate_entry = ttk.Entry(input_frame, validate="key",
                                                validatecommand=(self.validate_numeric_cmd, '%P'))
        self.product_kdv_rate_entry.grid(row=4, column=1, padx=5, pady=5, sticky="ew")
        self.product_kdv_rate_entry.insert(0, "18.0")

        # Butonlar
        button_frame = ttk.Frame(product_frame)
        button_frame.pack(pady=10)

        ttk.Button(button_frame, text="Ürün Ekle", command=self.urun_ekle).grid(row=0, column=0, padx=5, pady=5)
        ttk.Button(button_frame, text="Ürün Güncelle", command=self.urun_guncelle).grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(button_frame, text="Ürün Sil", command=self.urun_sil).grid(row=0, column=2, padx=5, pady=5)
        ttk.Button(button_frame, text="Temizle", command=self.temizle_urun_formu).grid(row=0, column=3, padx=5, pady=5)

        # Ürün Listesi (Treeview)
        self.product_tree = ttk.Treeview(product_frame,
                                         columns=("ID", "Adı", "Stok", "Alış Fiyatı", "Satış Fiyatı", "KDV Oranı"),
                                         show="headings")
        self.product_tree.heading("ID", text="ID")
        self.product_tree.heading("Adı", text="Ürün Adı")
        self.product_tree.heading("Stok", text="Stok")
        self.product_tree.heading("Alış Fiyatı", text="Alış Fiyatı (TL)")
        self.product_tree.heading("Satış Fiyatı", text="Satış Fiyatı (TL)")
        self.product_tree.heading("KDV Oranı", text="KDV Oranı (%)")

        self.product_tree.column("ID", width=50, stretch=tk.NO)
        self.product_tree.column("Adı", width=150, stretch=tk.YES)
        self.product_tree.column("Stok", width=70, stretch=tk.NO)
        self.product_tree.column("Alış Fiyatı", width=100, stretch=tk.NO)
        self.product_tree.column("Satış Fiyatı", width=100, stretch=tk.NO)
        self.product_tree.column("KDV Oranı", width=80, stretch=tk.NO)

        self.product_tree.pack(fill="both", expand=True, pady=10)
        self.product_tree.bind("<ButtonRelease-1>", self.urun_sec)

    def urun_ekle(self):
        name = self.product_name_entry.get().strip()
        stock_str = self.product_stock_entry.get()
        purchase_price_str = self.product_purchase_price_entry.get()
        selling_price_str = self.product_selling_price_entry.get()
        kdv_rate_str = self.product_kdv_rate_entry.get()

        if not name or not stock_str or not purchase_price_str or not selling_price_str or not kdv_rate_str:
            self.show_error("Hata", "Tüm alanlar doldurulmalıdır.")
            return

        try:
            stock = float(stock_str)
            purchase_price = float(purchase_price_str)
            selling_price = float(selling_price_str)
            kdv_rate = float(kdv_rate_str)
            if stock < 0 or purchase_price < 0 or selling_price < 0 or kdv_rate < 0:
                self.show_error("Hata", "Miktar ve fiyat alanları negatif olamaz.")
                return
        except ValueError:
            self.show_error("Hata", "Geçersiz sayısal format.")
            return

        if self.db_manager.insert_product(name, stock, purchase_price, selling_price, kdv_rate, self.kullanici_id):
            self.show_message("Başarılı", "Ürün/Hizmet başarıyla eklendi.")
            self.temizle_urun_formu()
            self.listele_urunler()
        else:
            self.show_error("Hata", "Ürün/Hizmet eklenirken bir sorun oluştu veya bu isimde bir ürün zaten mevcut.")

    def urun_guncelle(self):
        if not self.selected_product_id:
            self.show_error("Hata", "Lütfen güncellemek istediğiniz bir ürün/hizmet seçin.")
            return

        name = self.product_name_entry.get().strip()
        stock_str = self.product_stock_entry.get()
        purchase_price_str = self.product_purchase_price_entry.get()
        selling_price_str = self.product_selling_price_entry.get()
        kdv_rate_str = self.product_kdv_rate_entry.get()

        selected_item = self.product_tree.selection()
        current_product_name = self.product_tree.item(selected_item[0], 'values')[1] if selected_item else None

        if not name or not stock_str or not purchase_price_str or not selling_price_str or not kdv_rate_str:
            self.show_error("Hata", "Tüm alanlar doldurulmalıdır.")
            return

        if name != current_product_name and self.db_manager.get_product_by_name(name, self.kullanici_id):
            self.show_error("Hata", f"'{name}' isimli bir ürün/hizmet zaten mevcut.")
            return

        try:
            stock = float(stock_str)
            purchase_price = float(purchase_price_str)
            selling_price = float(selling_price_str)
            kdv_rate = float(kdv_rate_str)
            if stock < 0 or purchase_price < 0 or selling_price < 0 or kdv_rate < 0:
                self.show_error("Hata", "Miktar ve fiyat alanları negatif olamaz.")
                return
        except ValueError:
            self.show_error("Hata", "Geçersiz sayısal format.")
            return

        if self.db_manager.update_product(self.selected_product_id, name, stock, purchase_price, selling_price,
                                          kdv_rate, self.kullanici_id):
            self.show_message("Başarılı", "Ürün/Hizmet başarıyla güncellendi.")
            self.temizle_urun_formu()
            self.listele_urunler()
            self.listele_faturalar_teklifler()
        else:
            self.show_error("Hata", "Ürün/Hizmet güncellenirken bir sorun oluştu.")

    def urun_sil(self):
        if not self.selected_product_id:
            self.show_error("Hata", "Lütfen silmek istediğiniz bir ürün/hizmet seçin.")
            return

        if messagebox.askyesno("Onay",
                               "Seçili ürün/hizmeti silmek istediğinizden emin misiniz? Bu işlem envanter ve fatura kayıtlarını etkileyebilir."):
            if self.db_manager.delete_product(self.selected_product_id, self.kullanici_id):
                self.show_message("Başarılı", "Ürün/Hizmet başarıyla silindi.")
                self.temizle_urun_formu()
                self.listele_urunler()
            else:
                self.show_error("Hata", "Ürün/Hizmet silinirken bir sorun oluştu.")

    def urun_sec(self, event):
        selected_item = self.product_tree.selection()
        if selected_item:
            values = self.product_tree.item(selected_item, 'values')
            self.selected_product_id = values[0]
            if hasattr(self, 'product_name_entry') and self.product_name_entry.winfo_exists():
                self.product_name_entry.delete(0, tk.END)
                self.product_name_entry.insert(0, values[1])
            if hasattr(self, 'product_stock_entry') and self.product_stock_entry.winfo_exists():
                self.product_stock_entry.delete(0, tk.END)
                self.product_stock_entry.insert(0, values[2])
            if hasattr(self, 'product_purchase_price_entry') and self.product_purchase_price_entry.winfo_exists():
                self.product_purchase_price_entry.delete(0, tk.END)
                self.product_purchase_price_entry.insert(0, values[3])
            if hasattr(self, 'product_selling_price_entry') and self.product_selling_price_entry.winfo_exists():
                self.product_selling_price_entry.delete(0, tk.END)
                self.product_selling_price_entry.insert(0, values[4])
            if hasattr(self, 'product_kdv_rate_entry') and self.product_kdv_rate_entry.winfo_exists():
                self.product_kdv_rate_entry.delete(0, tk.END)
                self.product_kdv_rate_entry.insert(0, values[5])
        else:
            self.temizle_urun_formu()

    def listele_urunler(self):
        if not (hasattr(self, 'product_tree') and self.product_tree.winfo_exists()):
            return

        for item in self.product_tree.get_children():
            self.product_tree.delete(item)

        products = self.db_manager.get_products(self.kullanici_id)
        for prod_id, name, stock, purchase_price, selling_price, kdv_rate in products:
            self.product_tree.insert("", "end", values=(prod_id, name, f"{stock:.2f}", f"{purchase_price:.2f}",
                                                        f"{selling_price:.2f}", f"{kdv_rate:.2f}"))

    def temizle_urun_formu(self):
        if hasattr(self, 'product_name_entry') and self.product_name_entry.winfo_exists():
            self.product_name_entry.delete(0, tk.END)
        if hasattr(self, 'product_stock_entry') and self.product_stock_entry.winfo_exists():
            self.product_stock_entry.delete(0, tk.END)
            self.product_stock_entry.insert(0, "0.0")
        if hasattr(self, 'product_purchase_price_entry') and self.product_purchase_price_entry.winfo_exists():
            self.product_purchase_price_entry.delete(0, tk.END)
            self.product_purchase_price_entry.insert(0, "0.0")
        if hasattr(self, 'product_selling_price_entry') and self.product_selling_price_entry.winfo_exists():
            self.product_selling_price_entry.delete(0, tk.END)
            self.product_selling_price_entry.insert(0, "0.0")
        if hasattr(self, 'product_kdv_rate_entry') and self.product_kdv_rate_entry.winfo_exists():
            self.product_kdv_rate_entry.delete(0, tk.END)
            self.product_kdv_rate_entry.insert(0, "18.0")
        self.selected_product_id = None

    # --- Fatura/Teklif Oluşturma UI ve Fonksiyonları ---
    def _create_invoice_offer_ui(self, parent_frame):
        """Fatura/Teklif Oluşturma arayüzünü oluşturur."""
        invoice_offer_frame = ttk.LabelFrame(parent_frame, text="Fatura / Teklif Oluşturma", padding="15")
        invoice_offer_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Üst Kısım: Belge Bilgileri ve Müşteri Seçimi
        header_frame = ttk.Frame(invoice_offer_frame)
        header_frame.pack(fill="x", pady=10)

        ttk.Label(header_frame, text="Belge Tipi:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.doc_type_combobox = ttk.Combobox(header_frame, values=["Fatura", "Teklif"], state="readonly")
        self.doc_type_combobox.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.doc_type_combobox.set("Fatura")
        self.doc_type_combobox.bind("<<ComboboxSelected>>", self.generate_document_number)

        ttk.Label(header_frame, text="Belge Numarası:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.doc_number_entry = ttk.Entry(header_frame, state="readonly")
        self.doc_number_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        ttk.Button(header_frame, text="Numara Oluştur", command=self.generate_document_number).grid(row=1, column=2,
                                                                                                    padx=5, pady=5)

        ttk.Label(header_frame, text="Müşteri:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.invoice_customer_combobox = ttk.Combobox(header_frame, state="readonly")
        self.invoice_customer_combobox.grid(row=2, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(header_frame, text="Belge Tarihi:").grid(row=3, column=0, padx=5, pady=5, sticky="w")
        self.invoice_date_entry = DateEntry(header_frame, width=12, background='darkblue', foreground='white',
                                            borderwidth=2, locale='tr_TR')
        self.invoice_date_entry.grid(row=3, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(header_frame, text="Vade/Geçerlilik Tarihi:").grid(row=4, column=0, padx=5, pady=5, sticky="w")
        self.invoice_due_valid_date_entry = DateEntry(header_frame, width=12, background='darkblue', foreground='white',
                                                      borderwidth=2, locale='tr_TR')
        self.invoice_due_valid_date_entry.grid(row=4, column=1, padx=5, pady=5, sticky="ew")

        # Ara Çizgi
        ttk.Separator(invoice_offer_frame, orient="horizontal").pack(fill="x", pady=10)

        # Kalem Ekleme Bölümü
        items_frame = ttk.LabelFrame(invoice_offer_frame, text="Kalemler", padding="10")
        items_frame.pack(fill="both", expand=True, pady=10)

        item_input_frame = ttk.Frame(items_frame)
        item_input_frame.pack(fill="x", pady=5)

        ttk.Label(item_input_frame, text="Ürün/Hizmet:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.item_product_combobox = ttk.Combobox(item_input_frame, state="readonly")
        self.item_product_combobox.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.item_product_combobox.bind("<<ComboboxSelected>>", self.on_product_selected_for_item)

        ttk.Label(item_input_frame, text="Miktar:").grid(row=0, column=2, padx=5, pady=5, sticky="w")
        self.item_quantity_entry = ttk.Entry(item_input_frame, validate="key",
                                             validatecommand=(self.validate_numeric_cmd, '%P'), width=10)
        self.item_quantity_entry.grid(row=0, column=3, padx=5, pady=5, sticky="ew")
        self.item_quantity_entry.insert(0, "1.0")
        self.item_quantity_entry.bind("<KeyRelease>", self.calculate_item_totals_on_change)

        ttk.Label(item_input_frame, text="Birim Fiyat:").grid(row=0, column=4, padx=5, pady=5, sticky="w")
        self.item_unit_price_label = ttk.Label(item_input_frame, text="0.00 TL", width=10)
        self.item_unit_price_label.grid(row=0, column=5, padx=5, pady=5, sticky="w")

        ttk.Label(item_input_frame, text="KDV Oranı:").grid(row=0, column=6, padx=5, pady=5, sticky="w")
        self.item_kdv_rate_label = ttk.Label(item_input_frame, text="0.00%", width=10)
        self.item_kdv_rate_label.grid(row=0, column=7, padx=5, pady=5, sticky="w")

        ttk.Label(item_input_frame, text="KDV Miktar:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.item_kdv_amount_label = ttk.Label(item_input_frame, text="0.00 TL", width=10)
        self.item_kdv_amount_label.grid(row=1, column=1, padx=5, pady=5, sticky="w")

        ttk.Label(item_input_frame, text="Ara Toplam:").grid(row=1, column=2, padx=5, pady=5, sticky="w")
        self.item_subtotal_label = ttk.Label(item_input_frame, text="0.00 TL", width=10)
        self.item_subtotal_label.grid(row=1, column=3, padx=5, pady=5, sticky="w")

        ttk.Button(item_input_frame, text="Kalem Ekle", command=self.add_invoice_item).grid(row=1, column=4, padx=5,
                                                                                            pady=5)
        ttk.Button(item_input_frame, text="Kalem Sil", command=self.remove_invoice_item).grid(row=1, column=5, padx=5,
                                                                                              pady=5)

        # Kalemler Treeview
        self.invoice_items_tree = ttk.Treeview(items_frame,
                                               columns=("Ürün/Hizmet", "Miktar", "Birim Fiyat", "KDV Oranı",
                                                        "KDV Miktar", "Ara Toplam"), show="headings")
        self.invoice_items_tree.heading("Ürün/Hizmet", text="Ürün/Hizmet")
        self.invoice_items_tree.heading("Miktar", text="Miktar")
        self.invoice_items_tree.heading("Birim Fiyat", text="Birim Fiyat")
        self.invoice_items_tree.heading("KDV Oranı", text="KDV %")
        self.invoice_items_tree.heading("KDV Miktar", text="KDV Tutarı")
        self.invoice_items_tree.heading("Ara Toplam", text="Ara Toplam")

        self.invoice_items_tree.column("Miktar", width=70, stretch=tk.NO)
        self.invoice_items_tree.column("Birim Fiyat", width=100, stretch=tk.NO)
        self.invoice_items_tree.column("KDV Oranı", width=70, stretch=tk.NO)
        self.invoice_items_tree.column("KDV Miktar", width=100, stretch=tk.NO)
        self.invoice_items_tree.column("Ara Toplam", width=100, stretch=tk.NO)

        self.invoice_items_tree.pack(fill="both", expand=True, pady=10)
        self.invoice_items_tree.bind("<ButtonRelease-1>", self.select_invoice_item_for_edit)

        # Toplamlar
        totals_frame = ttk.Frame(invoice_offer_frame)
        totals_frame.pack(fill="x", pady=10)

        self.total_excl_kdv_label = ttk.Label(totals_frame, text="KDV Hariç Toplam: 0.00 TL",
                                              font=("Arial", 10, "bold"))
        self.total_excl_kdv_label.pack(side="left", padx=5)

        self.total_kdv_label = ttk.Label(totals_frame, text="Toplam KDV: 0.00 TL", font=("Arial", 10, "bold"))
        self.total_kdv_label.pack(side="left", padx=5)

        self.grand_total_label = ttk.Label(totals_frame, text="GENEL TOPLAM: 0.00 TL", font=("Arial", 12, "bold"),
                                           foreground="blue")
        self.grand_total_label.pack(side="right", padx=5)

        # Notlar ve Durum
        notes_status_frame = ttk.Frame(invoice_offer_frame)
        notes_status_frame.pack(fill="x", pady=10)

        ttk.Label(notes_status_frame, text="Notlar:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.invoice_notes_text = tk.Text(notes_status_frame, height=3, width=40, font=("Arial", 10))
        self.invoice_notes_text.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(notes_status_frame, text="Durum:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.invoice_status_combobox = ttk.Combobox(notes_status_frame,
                                                    values=["Taslak", "Gönderildi", "Ödendi", "İptal Edildi"],
                                                    state="readonly")
        self.invoice_status_combobox.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        self.invoice_status_combobox.set("Taslak")

        notes_status_frame.grid_columnconfigure(1, weight=1)

        # Ana Butonlar
        main_buttons_frame = ttk.Frame(invoice_offer_frame)
        main_buttons_frame.pack(pady=10)

        ttk.Button(main_buttons_frame, text="Kaydet", command=self.save_invoice_offer).grid(row=0, column=0, padx=5,
                                                                                            pady=5)
        ttk.Button(main_buttons_frame, text="Güncelle", command=self.update_invoice_offer).grid(row=0, column=1, padx=5,
                                                                                                pady=5)
        ttk.Button(main_buttons_frame, text="Sil", command=self.delete_invoice_offer).grid(row=0, column=2, padx=5,
                                                                                           pady=5)
        ttk.Button(main_buttons_frame, text="Temizle", command=self.clear_invoice_offer_form).grid(row=0, column=3,
                                                                                                   padx=5, pady=5)
        ttk.Button(main_buttons_frame, text="PDF Oluştur", command=self.generate_invoice_offer_pdf).grid(row=0,
                                                                                                         column=4,
                                                                                                         padx=5, pady=5)

        # Faturalar/Teklifler Listesi
        self.invoices_offers_tree = ttk.Treeview(invoice_offer_frame,
                                                 columns=("ID", "Tip", "No", "Müşteri", "KDV Hariç", "KDV Dahil",
                                                          "Tarih", "Durum", "Notlar"), show="headings")
        self.invoices_offers_tree.heading("ID", text="ID")
        self.invoices_offers_tree.heading("Tip", text="Tip")
        self.invoices_offers_tree.heading("No", text="Belge No")
        self.invoices_offers_tree.heading("Müşteri", text="Müşteri")
        self.invoices_offers_tree.heading("KDV Hariç", text="KDV Hariç (TL)")
        self.invoices_offers_tree.heading("KDV Dahil", text="KDV Dahil (TL)")
        self.invoices_offers_tree.heading("Tarih", text="Tarih")
        self.invoices_offers_tree.heading("Durum", text="Durum")
        self.invoices_offers_tree.heading("Notlar", text="Notlar")

        self.invoices_offers_tree.column("ID", width=50, stretch=tk.NO)
        self.invoices_offers_tree.column("Tip", width=70, stretch=tk.NO)
        self.invoices_offers_tree.column("No", width=100, stretch=tk.NO)
        self.invoices_offers_tree.column("Müşteri", width=120, stretch=tk.NO)
        self.invoices_offers_tree.column("KDV Hariç", width=100, stretch=tk.NO)
        self.invoices_offers_tree.column("KDV Dahil", width=100, stretch=tk.NO)
        self.invoices_offers_tree.column("Tarih", width=100, stretch=tk.NO)
        self.invoices_offers_tree.column("Durum", width=80, stretch=tk.NO)
        self.invoices_offers_tree.column("Notlar", width=150, stretch=tk.YES)

        self.invoices_offers_tree.pack(fill="both", expand=True, pady=10)
        self.invoices_offers_tree.bind("<ButtonRelease-1>", self.select_invoice_offer)

    def update_customer_combobox(self):
        customers = self.db_manager.get_customers(self.kullanici_id)
        customer_names = [c[1] for c in customers]
        if hasattr(self, 'invoice_customer_combobox') and self.invoice_customer_combobox.winfo_exists():
            self.invoice_customer_combobox['values'] = customer_names
            if customer_names:
                self.invoice_customer_combobox.set(customer_names[0])
            else:
                self.invoice_customer_combobox.set("")

    def update_product_combobox_for_invoice_items(self):
        products = self.db_manager.get_products(self.kullanici_id)
        product_names = [p[1] for p in products]
        if hasattr(self, 'item_product_combobox') and self.item_product_combobox.winfo_exists():
            self.item_product_combobox['values'] = product_names
            if product_names:
                self.item_product_combobox.set(product_names[0])
                self.on_product_selected_for_item()
            else:
                self.item_product_combobox.set("")
                if hasattr(self, 'item_unit_price_label') and self.item_unit_price_label.winfo_exists():
                    self.item_unit_price_label.config(text="0.00 TL")
                if hasattr(self, 'item_kdv_rate_label') and self.item_kdv_rate_label.winfo_exists():
                    self.item_kdv_rate_label.config(text="0.00%")
                if hasattr(self, 'item_kdv_amount_label') and self.item_kdv_amount_label.winfo_exists():
                    self.item_kdv_amount_label.config(text="0.00 TL")
                if hasattr(self, 'item_subtotal_label') and self.item_subtotal_label.winfo_exists():
                    self.item_subtotal_label.config(text="0.00 TL")
            self.current_selected_product_details = None

    def on_product_selected_for_item(self, event=None):
        selected_product_name = self.item_product_combobox.get()
        if selected_product_name:
            product_info = self.db_manager.get_product_by_name(selected_product_name, self.kullanici_id)
            if product_info:
                self.current_selected_product_details = {
                    "id": product_info[0],
                    "name": product_info[1],
                    "stock": product_info[2],
                    "purchase_price": product_info[3],
                    "selling_price": product_info[4],
                    "kdv_rate": product_info[5]
                }
                if hasattr(self, 'item_unit_price_label') and self.item_unit_price_label.winfo_exists():
                    self.item_unit_price_label.config(text=f"{product_info[4]:.2f} TL")
                if hasattr(self, 'item_kdv_rate_label') and self.item_kdv_rate_label.winfo_exists():
                    self.item_kdv_rate_label.config(text=f"{product_info[5]:.2f}%")
                self.calculate_item_totals_on_change()
            else:
                if hasattr(self, 'item_unit_price_label') and self.item_unit_price_label.winfo_exists():
                    self.item_unit_price_label.config(text="0.00 TL")
                if hasattr(self, 'item_kdv_rate_label') and self.item_kdv_rate_label.winfo_exists():
                    self.item_kdv_rate_label.config(text="0.00%")
                if hasattr(self, 'item_kdv_amount_label') and self.item_kdv_amount_label.winfo_exists():
                    self.item_kdv_amount_label.config(text="0.00 TL")
                if hasattr(self, 'item_subtotal_label') and self.item_subtotal_label.winfo_exists():
                    self.item_subtotal_label.config(text="0.00 TL")
                self.current_selected_product_details = None
        else:
            if hasattr(self, 'item_unit_price_label') and self.item_unit_price_label.winfo_exists():
                self.item_unit_price_label.config(text="0.00 TL")
            if hasattr(self, 'item_kdv_rate_label') and self.item_kdv_rate_label.winfo_exists():
                self.item_kdv_rate_label.config(text="0.00%")
            if hasattr(self, 'item_kdv_amount_label') and self.item_kdv_amount_label.winfo_exists():
                self.item_kdv_amount_label.config(text="0.00 TL")
            if hasattr(self, 'item_subtotal_label') and self.item_subtotal_label.winfo_exists():
                self.item_subtotal_label.config(text="0.00 TL")
            self.current_selected_product_details = None

    def calculate_item_totals_on_change(self, event=None):
        if not self.current_selected_product_details:
            return

        try:
            quantity_str = self.item_quantity_entry.get()
            quantity = float(quantity_str) if quantity_str and self._validate_numeric_input_wrapper(
                quantity_str) else 0.0

            unit_price = self.current_selected_product_details["selling_price"]
            kdv_rate = self.current_selected_product_details["kdv_rate"] / 100.0

            subtotal_before_kdv = quantity * unit_price
            kdv_amount = subtotal_before_kdv * kdv_rate
            total_with_kdv = subtotal_before_kdv + kdv_amount

            if hasattr(self, 'item_kdv_amount_label') and self.item_kdv_amount_label.winfo_exists():
                self.item_kdv_amount_label.config(text=f"{kdv_amount:.2f} TL")
            if hasattr(self, 'item_subtotal_label') and self.item_subtotal_label.winfo_exists():
                self.item_subtotal_label.config(text=f"{total_with_kdv:.2f} TL")

        except ValueError:
            if hasattr(self, 'item_kdv_amount_label') and self.item_kdv_amount_label.winfo_exists():
                self.item_kdv_amount_label.config(text="0.00 TL")
            if hasattr(self, 'item_subtotal_label') and self.item_subtotal_label.winfo_exists():
                self.item_subtotal_label.config(text="0.00 TL")

    def add_invoice_item(self):
        product_name = self.item_product_combobox.get()
        quantity_str = self.item_quantity_entry.get()

        if not product_name or not quantity_str:
            self.show_error("Hata", "Lütfen ürün/hizmet ve miktar girin.")
            return

        try:
            quantity = float(quantity_str)
            if quantity <= 0:
                self.show_error("Hata", "Miktar pozitif bir sayı olmalıdır.")
                return
        except ValueError:
            self.show_error("Hata", "Geçersiz miktar formatı.")
            return

        product_info = self.current_selected_product_details
        if not product_info:
            self.show_error("Hata", "Ürün bilgileri yüklenemedi. Lütfen geçerli bir ürün seçin.")
            return

        if self.doc_type_combobox.get() == "Fatura" and quantity > product_info["stock"]:
            self.show_error("Hata", f"Yetersiz stok! Mevcut stok: {product_info['stock']:.2f}")
            return

        if hasattr(self, 'invoice_items_tree') and self.invoice_items_tree.winfo_exists():
            for item_id in self.invoice_items_tree.get_children():
                item_values = self.invoice_items_tree.item(item_id, 'values')
                if item_values[0] == product_name:
                    existing_quantity = float(item_values[1])
                    new_quantity = existing_quantity + quantity

                    if self.doc_type_combobox.get() == "Fatura" and new_quantity > product_info["stock"]:
                        self.show_error("Hata",
                                        f"Bu ürün için toplam miktar ({new_quantity}) stok ({product_info['stock']}) miktarını aşıyor. Lütfen miktarı düşürün.")
                        return

                    unit_price = product_info["selling_price"]
                    kdv_rate = product_info["kdv_rate"] / 100.0
                    subtotal_before_kdv = new_quantity * unit_price
                    kdv_amount = subtotal_before_kdv * kdv_rate
                    total_with_kdv = subtotal_before_kdv + kdv_amount

                    self.invoice_items_tree.item(item_id, values=(
                        product_name,
                        f"{new_quantity:.2f}",
                        f"{unit_price:.2f}",
                        f"{product_info['kdv_rate']:.2f}",
                        f"{kdv_amount:.2f}",
                        f"{total_with_kdv:.2f}"
                    ))
                    self.calculate_grand_totals()
                    self.temizle_invoice_item_form()
                    return

            unit_price = product_info["selling_price"]
            kdv_rate = product_info["kdv_rate"] / 100.0
            subtotal_before_kdv = quantity * unit_price
            kdv_amount = subtotal_before_kdv * kdv_rate
            total_with_kdv = subtotal_before_kdv + kdv_amount

            self.invoice_items_tree.insert("", "end", values=(
                product_name,
                f"{quantity:.2f}",
                f"{unit_price:.2f}",
                f"{product_info['kdv_rate']:.2f}",
                f"{kdv_amount:.2f}",
                f"{total_with_kdv:.2f}"
            ))
            self.calculate_grand_totals()
            self.temizle_invoice_item_form()
        else:
            self.show_error("Hata", "Fatura kalemleri tablosu henüz oluşturulmadı.")

    def remove_invoice_item(self):
        if hasattr(self, 'invoice_items_tree') and self.invoice_items_tree.winfo_exists():
            selected_item = self.invoice_items_tree.selection()
            if selected_item:
                self.invoice_items_tree.delete(selected_item)
                self.calculate_grand_totals()
                self.temizle_invoice_item_form()
            else:
                self.show_error("Hata", "Lütfen silmek istediğiniz bir kalemi seçin.")
        else:
            self.show_error("Hata", "Fatura kalemleri tablosu henüz oluşturulmadı.")

    def select_invoice_item_for_edit(self, event):
        if hasattr(self, 'invoice_items_tree') and self.invoice_items_tree.winfo_exists():
            selected_item = self.invoice_items_tree.selection()
            if selected_item:
                values = self.invoice_items_tree.item(selected_item, 'values')
                product_name = values[0]
                quantity = values[1]

                if hasattr(self, 'item_product_combobox') and self.item_product_combobox.winfo_exists():
                    self.item_product_combobox.set(product_name)
                self.on_product_selected_for_item()
                if hasattr(self, 'item_quantity_entry') and self.item_quantity_entry.winfo_exists():
                    self.item_quantity_entry.delete(0, tk.END)
                    self.item_quantity_entry.insert(0, quantity)
                self.calculate_item_totals_on_change()
        else:
            self.show_error("Hata", "Fatura kalemleri tablosu henüz oluşturulmadı.")

    def calculate_grand_totals(self):
        total_excl_kdv = 0.0
        total_kdv = 0.0

        if hasattr(self, 'invoice_items_tree') and self.invoice_items_tree.winfo_exists():
            for item_id in self.invoice_items_tree.get_children():
                values = self.invoice_items_tree.item(item_id, 'values')
                quantity = float(values[1])
                unit_price = float(values[2])
                kdv_rate = float(values[3]) / 100.0

                subtotal_before_kdv = quantity * unit_price
                kdv_amount = subtotal_before_kdv * kdv_rate

                total_excl_kdv += subtotal_before_kdv
                total_kdv += kdv_amount

        grand_total = total_excl_kdv + total_kdv

        if hasattr(self, 'total_excl_kdv_label') and self.total_excl_kdv_label.winfo_exists():
            self.total_excl_kdv_label.config(text=f"KDV Hariç Toplam: {total_excl_kdv:.2f} TL")
        if hasattr(self, 'total_kdv_label') and self.total_kdv_label.winfo_exists():
            self.total_kdv_label.config(text=f"Toplam KDV: {total_kdv:.2f} TL")
        if hasattr(self, 'grand_total_label') and self.grand_total_label.winfo_exists():
            self.grand_total_label.config(text=f"GENEL TOPLAM: {grand_total:.2f} TL")

    def generate_document_number(self, event=None):
        if not (hasattr(self, 'doc_type_combobox') and self.doc_type_combobox.winfo_exists() and \
                hasattr(self, 'doc_number_entry') and self.doc_number_entry.winfo_exists()):
            return

        doc_type = self.doc_type_combobox.get()
        last_invoice_num, last_offer_num = self.db_manager.get_user_invoice_offer_nums(self.kullanici_id)

        if doc_type == "Fatura":
            new_num = last_invoice_num + 1
            prefix = "FTR"
        elif doc_type == "Teklif":
            new_num = last_offer_num + 1
            prefix = "TKLF"
        else:
            self.doc_number_entry.config(state="normal")
            self.doc_number_entry.delete(0, tk.END)
            self.doc_number_entry.config(state="readonly")
            return

        current_year = datetime.now().year
        new_doc_number = f"{prefix}-{current_year}-{new_num:05d}"

        self.doc_number_entry.config(state="normal")
        self.doc_number_entry.delete(0, tk.END)
        self.doc_number_entry.insert(0, new_doc_number)
        self.doc_number_entry.config(state="readonly")

    def save_invoice_offer(self):
        doc_type = self.doc_type_combobox.get()
        doc_number = self.doc_number_entry.get()
        customer_name = self.invoice_customer_combobox.get()
        doc_date_str = self.invoice_date_entry.get()
        due_valid_date_str = self.invoice_due_valid_date_entry.get()
        notes = self.invoice_notes_text.get("1.0", tk.END).strip()
        status = self.invoice_status_combobox.get()

        if not doc_number or not customer_name or not doc_date_str:
            self.show_error("Hata", "Belge Numarası, Müşteri ve Belge Tarihi boş olamaz.")
            return
        if not self.invoice_items_tree.get_children():
            self.show_error("Hata", "Lütfen fatura/teklife en az bir kalem ekleyin.")
            return

        try:
            doc_date_db_format = self._parse_date_input(doc_date_str)
            due_valid_date_db_format = self._parse_date_input(due_valid_date_str) if due_valid_date_str else None
        except ValueError as e:
            self.show_error("Hata", str(e))
            return

        items_list = []
        for item_id in self.invoice_items_tree.get_children():
            values = self.invoice_items_tree.item(item_id, 'values')
            item_data = {
                "ad": values[0],
                "miktar": float(values[1]),
                "birim_fiyat": float(values[2]),
                "kdv_orani": float(values[3]),
                "kdv_miktari": float(values[4]),
                "ara_toplam": float(values[5])
            }
            items_list.append(item_data)
        items_json = json.dumps(items_list)

        total_excl_kdv = float(
            self.total_excl_kdv_label.cget("text").replace("KDV Hariç Toplam: ", "").replace(" TL", ""))
        total_kdv = float(self.total_kdv_label.cget("text").replace("Toplam KDV: ", "").replace(" TL", ""))

        if self.db_manager.insert_invoice_offer(doc_type, doc_number, customer_name, doc_date_db_format,
                                                due_valid_date_db_format,
                                                items_json, total_excl_kdv, total_kdv, notes if notes else None, status,
                                                self.kullanici_id):

            if doc_type == "Fatura":
                current_invoice_num, current_offer_num = self.db_manager.get_user_invoice_offer_nums(self.kullanici_id)
                self.db_manager.update_user_invoice_offer_num(self.kullanici_id, invoice_num=current_invoice_num + 1)
                for item_data in items_list:
                    product_name = item_data['ad']
                    quantity = item_data['miktar']
                    product_info = self.db_manager.get_product_by_name(product_name, self.kullanici_id)
                    if product_info:
                        new_stock = product_info[2] - quantity
                        self.db_manager.update_product_stock(product_info[0], new_stock)
            elif doc_type == "Teklif":
                current_invoice_num, current_offer_num = self.db_manager.get_user_invoice_offer_nums(self.kullanici_id)
                self.db_manager.update_user_invoice_offer_num(self.kullanici_id, offer_num=current_offer_num + 1)

            self.show_message("Başarılı", f"{doc_type} başarıyla kaydedildi.")
            self.clear_invoice_offer_form()
            self.listele_faturalar_teklifler()
            self.listele_urunler()

        else:
            self.show_error("Hata", f"{doc_type} kaydedilirken bir sorun oluştu veya belge numarası zaten mevcut.")

    def update_invoice_offer(self):
        if not self.selected_invoice_offer_id:
            self.show_error("Hata", "Lütfen güncellemek istediğiniz bir fatura/teklif seçin.")
            return

        doc_type = self.doc_type_combobox.get()
        doc_number = self.doc_number_entry.get()
        customer_name = self.invoice_customer_combobox.get()
        doc_date_str = self.invoice_date_entry.get()
        due_valid_date_str = self.invoice_due_valid_date_entry.get()
        notes = self.invoice_notes_text.get("1.0", tk.END).strip()
        status = self.invoice_status_combobox.get()

        if not doc_number or not customer_name or not doc_date_str:
            self.show_error("Hata", "Belge Numarası, Müşteri ve Belge Tarihi boş olamaz.")
            return
        if not self.invoice_items_tree.get_children():
            self.show_error("Hata", "Lütfen fatura/teklife en az bir kalem ekleyin.")
            return

        try:
            doc_date_db_format = self._parse_date_input(doc_date_str)
            due_valid_date_db_format = self._parse_date_input(due_valid_date_str) if due_valid_date_str else None
        except ValueError as e:
            self.show_error("Hata", str(e))
            return

        items_list = []
        for item_id in self.invoice_items_tree.get_children():
            values = self.invoice_items_tree.item(item_id, 'values')
            item_data = {
                "ad": values[0],
                "miktar": float(values[1]),
                "birim_fiyat": float(values[2]),
                "kdv_orani": float(values[3]),
                "kdv_miktari": float(values[4]),
                "ara_toplam": float(values[5])
            }
            items_list.append(item_data)
        items_json = json.dumps(items_list)

        total_excl_kdv = float(
            self.total_excl_kdv_label.cget("text").replace("KDV Hariç Toplam: ", "").replace(" TL", ""))
        total_kdv = float(self.total_kdv_label.cget("text").replace("Toplam KDV: ", "").replace(" TL", ""))

        if self.db_manager.update_invoice_offer(self.selected_invoice_offer_id, doc_type, doc_number, customer_name,
                                                doc_date_db_format, due_valid_date_db_format, items_json,
                                                total_excl_kdv,
                                                total_kdv, notes if notes else None, status, self.kullanici_id):
            self.show_message("Başarılı", f"{doc_type} başarıyla güncellendi.")
            self.clear_invoice_offer_form()
            self.listele_faturalar_teklifler()
        else:
            self.show_error("Hata", f"{doc_type} güncellenirken bir sorun oluştu.")

    def delete_invoice_offer(self):
        if not self.selected_invoice_offer_id:
            self.show_error("Hata", "Lütfen silmek istediğiniz bir fatura/teklif seçin.")
            return

        selected_item_data = self.db_manager.get_invoice_offer_by_id(self.selected_invoice_offer_id, self.kullanici_id)
        if not selected_item_data:
            self.show_error("Hata", "Seçili fatura/teklif bulunamadı.")
            return

        doc_type = selected_item_data[1]
        items_json = selected_item_data[6]

        if messagebox.askyesno("Onay", f"Seçili {doc_type}'i silmek istediğinizden emin misiniz?"):
            if self.db_manager.delete_invoice_offer(self.selected_invoice_offer_id, self.kullanici_id):
                if doc_type == "Fatura":
                    try:
                        items_list = json.loads(items_json)
                        for item_data in items_list:
                            product_name = item_data['ad']
                            quantity = item_data['miktar']
                            product_info = self.db_manager.get_product_by_name(product_name, self.kullanici_id)
                            if product_info:
                                current_stock = product_info[2]
                                new_stock = current_stock + quantity
                                self.db_manager.update_product_stock(product_info[0], new_stock)
                        self.listele_urunler()
                    except Exception as e:
                        print(f"Stok geri yükleme hatası: {e}")
                        self.show_error("Hata", f"Fatura silindi ancak stok geri yüklenirken sorun oluştu: {e}")

                self.show_message("Başarılı", f"{doc_type} başarıyla silindi.")
                self.clear_invoice_offer_form()
                self.listele_faturalar_teklifler()
            else:
                self.show_error("Hata", f"{doc_type} silinirken bir sorun oluştu.")

    def select_invoice_offer(self, event):
        selected_item = self.invoices_offers_tree.selection()
        if selected_item:
            values = self.invoices_offers_tree.item(selected_item, 'values')
            self.selected_invoice_offer_id = values[0]

            doc_detail = self.db_manager.get_invoice_offer_by_id(self.selected_invoice_offer_id, self.kullanici_id)
            if doc_detail:
                if hasattr(self, 'doc_type_combobox') and self.doc_type_combobox.winfo_exists():
                    self.doc_type_combobox.set(doc_detail[1])

                if hasattr(self, 'doc_number_entry') and self.doc_number_entry.winfo_exists():
                    self.doc_number_entry.config(state="normal")
                    self.doc_number_entry.delete(0, tk.END)
                    self.doc_number_entry.insert(0, doc_detail[2])
                    self.doc_number_entry.config(state="readonly")

                if hasattr(self, 'invoice_customer_combobox') and self.invoice_customer_combobox.winfo_exists():
                    self.invoice_customer_combobox.set(doc_detail[3])

                if hasattr(self, 'invoice_date_entry') and self.invoice_date_entry.winfo_exists():
                    try:
                        self.invoice_date_entry.set_date(datetime.strptime(doc_detail[4], '%Y-%m-%d'))
                    except ValueError:
                        self.show_error("Hata", "Veritabanından okunan belge tarih formatı geçersiz.")
                        self.invoice_date_entry.set_date(datetime.now())

                if hasattr(self, 'invoice_due_valid_date_entry') and self.invoice_due_valid_date_entry.winfo_exists():
                    if doc_detail[5]:
                        try:
                            self.invoice_due_valid_date_entry.set_date(datetime.strptime(doc_detail[5], '%Y-%m-%d'))
                        except ValueError:
                            self.show_error("Hata", "Veritabanından okunan vade/geçerlilik tarih formatı geçersiz.")
                            self.invoice_due_valid_date_entry.set_date(datetime.now())
                    else:
                        self.invoice_due_valid_date_entry.set_date(datetime.now())

                if hasattr(self, 'invoice_notes_text') and self.invoice_notes_text.winfo_exists():
                    self.invoice_notes_text.delete("1.0", tk.END)
                    if doc_detail[9]:
                        self.invoice_notes_text.insert("1.0", doc_detail[9])

                if hasattr(self, 'invoice_status_combobox') and self.invoice_status_combobox.winfo_exists():
                    self.invoice_status_combobox.set(doc_detail[10])

                if hasattr(self, 'invoice_items_tree') and self.invoice_items_tree.winfo_exists():
                    for item in self.invoice_items_tree.get_children():
                        self.invoice_items_tree.delete(item)

                    items_list = json.loads(doc_detail[6])
                    for item_data in items_list:
                        self.invoice_items_tree.insert("", "end", values=(
                            item_data.get("ad", ""),
                            f"{item_data.get('miktar', 0):.2f}",
                            f"{item_data.get('birim_fiyat', 0):.2f}",
                            f"{item_data.get('kdv_orani', 0):.2f}",
                            f"{item_data.get('kdv_miktari', 0):.2f}",
                            f"{item_data.get('ara_toplam', 0):.2f}"
                        ))

                self.calculate_grand_totals()
            else:
                self.show_error("Hata", "Seçili fatura/teklif detayları yüklenemedi.")
                self.clear_invoice_offer_form()
        else:
            self.clear_invoice_offer_form()

    def listele_faturalar_teklifler(self):
        if not (hasattr(self, 'invoices_offers_tree') and self.invoices_offers_tree.winfo_exists()):
            return

        for item in self.invoices_offers_tree.get_children():
            self.invoices_offers_tree.delete(item)

        invoices_offers = self.db_manager.get_invoice_offers(self.kullanici_id)
        for io_id, type, doc_num, customer, total_excl_kdv, total_kdv, grand_total, doc_date, status, notes in invoices_offers:
            self.invoices_offers_tree.insert("", "end", values=(io_id, type, doc_num, customer, f"{total_excl_kdv:.2f}",
                                                                f"{grand_total:.2f}", doc_date, status, notes))

    def clear_invoice_offer_form(self):
        self.selected_invoice_offer_id = None
        if hasattr(self, 'doc_type_combobox') and self.doc_type_combobox.winfo_exists():
            self.doc_type_combobox.set("Fatura")
        self.generate_document_number()
        self.update_customer_combobox()

        if hasattr(self, 'invoice_date_entry') and self.invoice_date_entry.winfo_exists():
            self.invoice_date_entry.set_date(datetime.now())

        if hasattr(self, 'invoice_due_valid_date_entry') and self.invoice_due_valid_date_entry.winfo_exists():
            self.invoice_due_valid_date_entry.set_date(datetime.now())

        if hasattr(self, 'invoice_notes_text') and self.invoice_notes_text.winfo_exists():
            self.invoice_notes_text.delete("1.0", tk.END)

        if hasattr(self, 'invoice_status_combobox') and self.invoice_status_combobox.winfo_exists():
            self.invoice_status_combobox.set("Taslak")

        if hasattr(self, 'invoice_items_tree') and self.invoice_items_tree.winfo_exists():
            for item in self.invoice_items_tree.get_children():
                self.invoice_items_tree.delete(item)
        self.temizle_invoice_item_form()
        self.calculate_grand_totals()

    def temizle_invoice_item_form(self):
        if hasattr(self, 'item_product_combobox') and self.item_product_combobox.winfo_exists():
            self.item_product_combobox.set("")

        if hasattr(self, 'item_quantity_entry') and self.item_quantity_entry.winfo_exists():
            self.item_quantity_entry.delete(0, tk.END)
            self.item_quantity_entry.insert(0, "1.0")

        if hasattr(self, 'item_unit_price_label') and self.item_unit_price_label.winfo_exists():
            self.item_unit_price_label.config(text="0.00 TL")

        if hasattr(self, 'item_kdv_rate_label') and self.item_kdv_rate_label.winfo_exists():
            self.item_kdv_rate_label.config(text="0.00%")

        if hasattr(self, 'item_kdv_amount_label') and self.item_kdv_amount_label.winfo_exists():
            self.item_kdv_amount_label.config(text="0.00 TL")

        if hasattr(self, 'item_subtotal_label') and self.item_subtotal_label.winfo_exists():
            self.item_subtotal_label.config(text="0.00 TL")

        self.current_selected_product_details = None
        self.update_product_combobox_for_invoice_items()

    def generate_invoice_offer_pdf(self):
        """Seçili fatura/teklif için PDF oluşturur."""
        if not self.selected_invoice_offer_id:
            self.show_error("Hata", "Lütfen PDF oluşturmak istediğiniz bir fatura veya teklif seçin.")
            return

        doc_detail = self.db_manager.get_invoice_offer_by_id(self.selected_invoice_offer_id, self.kullanici_id)
        if not doc_detail:
            self.show_error("Hata", "Seçili belge bulunamadı.")
            return

        try:
            doc_id, doc_type, doc_number, customer_name, doc_date, due_validity_date, items_json, \
                total_excl_kdv, total_kdv, total_with_kdv, notes, status = doc_detail

            items_list = json.loads(items_json)

            doc_data = {
                "doc_type": doc_type,
                "doc_number": doc_number,
                "customer_name": customer_name,
                "doc_date": doc_date,
                "due_valid_date": due_validity_date,
                "items": items_list,
                "total_excl_kdv": total_excl_kdv,
                "total_kdv": total_kdv,
                "grand_total": total_with_kdv,
                "notes": notes,
                "status": status
            }

            file_path = filedialog.asksaveasfilename(
                defaultextension=".pdf",
                filetypes=[("PDF files", "*.pdf")],
                initialfile=f"{doc_number}.pdf",
                title=f"{doc_type} PDF Kaydet"
            )

            if file_path:
                # generate_document_pdf, dosya yolunu PDFGenerator içinde alıp kendi içinde kaydetmeli.
                # pdf_generator.py'deki generate_document_pdf metodu, artık dosya adını kendi içinde belirliyor
                # ve geri dönüş değeri olarak abs path veriyor. O yüzden burada tekrar file_path geçmiyoruz.
                generated_file_path = self.pdf_generator.generate_document_pdf(doc_data)

                if generated_file_path:
                    self.show_message("PDF Oluşturuldu",
                                      f"{doc_type} '{doc_number}' için PDF başarıyla oluşturuldu:\n{generated_file_path}")
                else:
                    self.show_error("PDF Oluşturma Hatası", "PDF dosyası oluşturulamadı.")
            else:
                self.show_message("İptal Edildi", "PDF oluşturma işlemi iptal edildi.")

        except Exception as e:
            self.show_error("PDF Oluşturma Hatası", f"PDF oluşturulurken bir hata oluştu: {e}")
            print(f"PDF Oluşturma Hatası: {e}")

    # --- Raporlar ve Analizler UI ve Fonksiyonları ---
    def _create_reports_analysis_ui(self, parent_frame):
        """Raporlar ve Analizler arayüzünü oluşturur."""
        self.reports_analysis_frame = ttk.LabelFrame(parent_frame, text="Raporlar ve Analizler", padding="15")
        self.reports_analysis_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Grafik Butonları Alanı
        chart_buttons_frame = ttk.LabelFrame(self.reports_analysis_frame, text="Finansal Grafikler", padding="10")
        chart_buttons_frame.pack(fill="x", padx=5, pady=5)

        ttk.Button(chart_buttons_frame, text="Kategori Bazında Gelir/Gider Grafikleri",
                   command=self.show_category_charts_window).pack(side="left", padx=5, pady=5)
        ttk.Button(chart_buttons_frame, text="Aylık Bakiye Trend Grafiği", command=self.show_balance_chart_window).pack(
            side="left", padx=5, pady=5)

        # Tasarruf Analizi ve Vergi Raporu Ortak Alanı
        # Bu frame'i grid ile ikiye böleceğiz
        analysis_report_container_frame = ttk.Frame(self.reports_analysis_frame)
        analysis_report_container_frame.pack(fill="both", expand=True, padx=5, pady=5)

        # Sol Kısım: Tasarruf Analizi
        savings_frame = ttk.LabelFrame(analysis_report_container_frame, text="Tasarruf Analizi ve Önerileri",
                                       padding="10")
        savings_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)  # Grid kullanıldı

        ttk.Button(savings_frame, text="Tasarruf Analizi Yap", command=self.tasarruf_analizi_yap).pack(pady=5)
        self.savings_analysis_text = tk.Text(savings_frame, wrap="word", height=15, font=("Arial", 10),
                                             state="disabled", bg="#f8f8f8")
        self.savings_analysis_text.pack(fill="both", expand=True)

        # Sağ Kısım: Vergi Raporu
        tax_report_frame = ttk.LabelFrame(analysis_report_container_frame, text="Vergi Raporu Oluştur", padding="10")
        tax_report_frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)  # Grid kullanıldı

        date_selection_frame = ttk.Frame(tax_report_frame)
        date_selection_frame.pack(pady=5)

        ttk.Label(date_selection_frame, text="Başlangıç Tarihi:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.tax_report_start_date = DateEntry(date_selection_frame, width=12, background='darkblue',
                                               foreground='white', borderwidth=2, locale='tr_TR')
        self.tax_report_start_date.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(date_selection_frame, text="Bitiş Tarihi:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.tax_report_end_date = DateEntry(date_selection_frame, width=12, background='darkblue', foreground='white',
                                             borderwidth=2, locale='tr_TR')
        self.tax_report_end_date.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        ttk.Button(date_selection_frame, text="Rapor Oluştur", command=self.generate_tax_report).grid(row=2, column=0,
                                                                                                      columnspan=2,
                                                                                                      pady=10)

        self.tax_report_text = tk.Text(tax_report_frame, wrap="word", height=15, font=("Arial", 10), state="disabled",
                                       bg="#f8f8f8")
        self.tax_report_text.pack(fill="both", expand=True, pady=10)

        # Container frame için column yapılandırması
        analysis_report_container_frame.grid_columnconfigure(0, weight=1)
        analysis_report_container_frame.grid_columnconfigure(1, weight=1)
        analysis_report_container_frame.grid_rowconfigure(0, weight=1)  # Row'un da genişlemesini sağla

    def show_category_charts_window(self):
        """Kategori bazında gelir/gider grafiklerini yeni bir pencerede gösterir."""
        chart_window = tk.Toplevel(self.root)
        chart_window.title("Kategori Bazında Gelir/Gider Grafikleri")
        chart_window.geometry("1100x600")

        category_summary_data = self.db_manager.get_income_expenses_by_month_and_category(self.kullanici_id,
                                                                                          num_months=12)

        expense_by_category = {}
        income_by_category = {}
        if category_summary_data:
            for type, category, amount in category_summary_data:
                if category:
                    if type == 'Gider':
                        expense_by_category[category] = expense_by_category.get(category, 0) + amount
                    elif type == 'Gelir':
                        income_by_category[category] = income_by_category.get(category, 0) + amount

        fig_category, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 5))

        if expense_by_category:
            ax1.pie(expense_by_category.values(), labels=expense_by_category.keys(), autopct='%1.1f%%', startangle=90)
            ax1.set_title('Giderler Kategori Bazında')
        else:
            ax1.text(0.5, 0.5, 'Gider Verisi Yok', horizontalalignment='center', verticalalignment='center',
                     transform=ax1.transAxes)
            ax1.set_title('Giderler Kategori Bazında')

        if income_by_category:
            ax2.pie(income_by_category.values(), labels=income_by_category.keys(), autopct='%1.1f%%', startangle=90)
            ax2.set_title('Gelirler Kategori Bazında')
        else:
            ax2.text(0.5, 0.5, 'Gelir Verisi Yok', horizontalalignment='center', verticalalignment='center',
                     transform=ax2.transAxes)
            ax2.set_title('Gelirler Kategori Bazında')

        fig_category.tight_layout()

        canvas_category = FigureCanvasTkAgg(fig_category, master=chart_window)
        canvas_category.draw()
        canvas_category.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=10)

        chart_window.protocol("WM_DELETE_WINDOW", lambda: self._on_chart_window_close(chart_window, fig_category))

    def show_balance_chart_window(self):
        """Aylık bakiye trend grafiğini yeni bir pencerede gösterir."""
        chart_window = tk.Toplevel(self.root)
        chart_window.title("Aylık Bakiye Trend Grafiği")
        chart_window.geometry("800x500")

        time_series_raw_data = self.db_manager.get_monthly_balance_trend(self.kullanici_id, num_months=12)

        fig_balance, ax = plt.subplots(figsize=(8, 4))

        if time_series_raw_data:
            df = pd.DataFrame(time_series_raw_data, columns=['date', 'type', 'amount'])
            df['date'] = pd.to_datetime(df['date'])
            df.set_index('date', inplace=True)
            df['signed_amount'] = df.apply(lambda row: row['amount'] if row['type'] == 'Gelir' else -row['amount'],
                                           axis=1)
            df = df.sort_values('date')
            df['cumulative_balance'] = df['signed_amount'].cumsum()
            monthly_cumulative_balance = df['cumulative_balance'].resample('ME').last().ffill().fillna(0)

            monthly_cumulative_balance.plot(ax=ax, kind='line', marker='o')
            ax.set_title('Aylık Kümülatif Bakiye Trendi')
            ax.set_xlabel('Tarih')
            ax.set_ylabel('Bakiye (TL)')
            ax.grid(True)
        else:
            ax.text(0.5, 0.5, 'Bakiye Trendi Verisi Yok', horizontalalignment='center', verticalalignment='center',
                    transform=ax.transAxes)
            ax.set_title('Aylık Kümülatif Bakiye Trendi')

        fig_balance.tight_layout()

        canvas_balance = FigureCanvasTkAgg(fig_balance, master=chart_window)
        canvas_balance.draw()
        canvas_balance.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=10)

        chart_window.protocol("WM_DELETE_WINDOW", lambda: self._on_chart_window_close(chart_window, fig_balance))

    def _on_chart_window_close(self, window, fig):
        """Grafik penceresi kapatıldığında Matplotlib figürünü temizler."""
        plt.close(fig)
        window.destroy()

    def generate_tax_report(self):
        """Belirli tarih aralığı için vergi raporu oluşturur."""
        if not (hasattr(self, 'tax_report_start_date') and self.tax_report_start_date.winfo_exists() and \
                hasattr(self, 'tax_report_end_date') and self.tax_report_end_date.winfo_exists() and \
                hasattr(self, 'tax_report_text') and self.tax_report_text.winfo_exists()):
            self.show_error("Hata", "Rapor arayüzü henüz hazır değil. Lütfen sekmeyi tekrar kontrol edin.")
            return

        start_date_str = self.tax_report_start_date.get()
        end_date_str = self.tax_report_end_date.get()

        if not start_date_str or not end_date_str:
            self.show_error("Hata", "Lütfen rapor için başlangıç ve bitiş tarihi seçin.")
            return

        try:
            start_date_db_format = self._parse_date_input(start_date_str)
            end_date_db_format = self._parse_date_input(end_date_str)
        except ValueError as e:
            self.show_error("Hata", str(e))
            return

        report_content_list = []  # PDFGenerator'a göndermek için listeye ihtiyacımız olacak

        # Sadece rapor içeriğini hazırlayacak mantık burada kalsın
        report_text_lines = []
        report_text_lines.append("--- Vergi Raporu ---\n")
        report_text_lines.append(f"Tarih Aralığı: {start_date_db_format} - {end_date_db_format}\n")

        total_sales_kdv = self.db_manager.get_total_sales_kdv(start_date_db_format, end_date_db_format,
                                                              self.kullanici_id)

        invoice_item_jsons = self.db_manager.get_invoice_jsons_for_tax_report(start_date_db_format, end_date_db_format,
                                                                              self.kullanici_id)

        kdv_by_rate = {}

        for item_json_tuple in invoice_item_jsons:
            items_list = json.loads(item_json_tuple[0])
            for item in items_list:
                kdv_rate = item.get("kdv_orani", 0)
                kdv_amount = item.get("kdv_miktari", 0)
                kdv_by_rate[kdv_rate] = kdv_by_rate.get(kdv_rate, 0) + kdv_amount

        report_text_lines.append("--- Detaylı Satış KDV Dökümü ---")
        kdv_detail_data = [["KDV Oranı (%)", "KDV Miktarı (TL)"]]
        if kdv_by_rate:
            for rate, amount in sorted(kdv_by_rate.items()):
                report_text_lines.append(f"KDV Oranı %{rate:.2f}: {amount:.2f} TL")
                kdv_detail_data.append([f"{rate:.2f}%", f"{amount:.2f} TL"])
        else:
            report_text_lines.append("Bu dönemde satış KDV'si içeren fatura kalemi bulunamadı.")
            kdv_detail_data.append(["Veri Yok", "Veri Yok"])
        report_text_lines.append("\n")

        report_text_lines.append(f"Toplam Hesaplanan KDV (Çıkış KDV'si): {total_sales_kdv:.2f} TL")
        report_text_lines.append(
            "Giriş KDV'si (Alış KDV'si) hesaplaması için manuel giriş veya detaylı fiş/fatura takibi gereklidir.\n")
        report_text_lines.append(
            "Önemli Not: Bu rapor bir mali müşavir raporu değildir. Yalnızca bilgilendirme amaçlıdır. "
            "Gerçek vergi beyanlarınız için lütfen bir mali müşavire danışın.")

        self.tax_report_text.config(state="normal")
        self.tax_report_text.delete("1.0", tk.END)
        self.tax_report_text.insert("1.0", "\n".join(report_text_lines))
        self.tax_report_text.config(state="disabled")
        self.show_message("Rapor Oluşturuldu", "Vergi raporu başarıyla oluşturuldu.")

        # PDF çıktısı için veriyi hazırla
        pdf_report_data = {
            "title": "Vergi Raporu",
            "sections": [
                {
                    "heading": f"Tarih Aralığı: {start_date_db_format} - {end_date_db_format}",
                    "data": []  # Sadece başlık olarak kullanacağız
                },
                {
                    "heading": "Detaylı Satış KDV Dökümü",
                    "data": kdv_detail_data  # Tablo verisi
                },
                {
                    "heading": "Özet Bilgiler",
                    "data": [
                        ["Açıklama", "Tutar"],
                        ["Toplam Hesaplanan KDV (Çıkış KDV'si)", f"{total_sales_kdv:.2f} TL"],
                        ["Giriş KDV'si (Alış KDV'si)", "Manuel giriş veya detaylı fiş/fatura takibi gereklidir."]
                    ]
                },
                {
                    "heading": "Önemli Not",
                    "data": [
                        ["",
                         "Bu rapor bir mali müşavir raporu değildir. Yalnızca bilgilendirme amaçlıdır. Gerçek vergi beyanlarınız için lütfen bir mali müşavire danışın."]
                    ]
                }
            ]
        }

        # İstersen burada otomatik olarak PDF oluşturabiliriz
        # file_path = filedialog.asksaveasfilename(
        #     defaultextension=".pdf",
        #     filetypes=[("PDF files", "*.pdf")],
        #     initialfile=f"Vergi_Raporu_{start_date_db_format}_{end_date_db_format}.pdf",
        #     title="Vergi Raporunu Kaydet"
        # )
        # if file_path:
        #     try:
        #         generated_path = self.pdf_generator.generate_general_report_pdf(pdf_report_data, file_path)
        #         if generated_path:
        #             self.show_message("PDF Raporu", f"Vergi raporu PDF olarak kaydedildi:\n{generated_path}")
        #         else:
        #             self.show_error("PDF Raporu Hatası", "Vergi raporu PDF oluşturulamadı.")
        #     except Exception as e:
        #         self.show_error("PDF Raporu Hatası", f"Vergi raporu PDF oluşturulurken hata oluştu: {e}")

    def export_transactions_to_pdf(self):
        """Ana listedeki gelir/gider verilerini PDF'e aktarır."""
        data_to_export = []
        headers = [self.transactions_tree.heading(col_id)['text'] for col_id in self.transactions_tree["columns"]]

        for item_id in self.transactions_tree.get_children():
            values = self.transactions_tree.item(item_id, 'values')
            data_to_export.append([str(v) for v in values])  # Tüm değerleri string'e çevir

        if not data_to_export:
            self.show_message("Bilgi", "Dışa aktarılacak işlem verisi bulunamadı.")
            return

        file_path = filedialog.asksaveasfilename(defaultextension=".pdf",
                                                 filetypes=[("PDF dosyaları", "*.pdf")],
                                                 initialfile="gelir_gider_islemleri_raporu.pdf")
        if not file_path:
            return

        report_data = {
            "title": "Gelir ve Gider İşlemleri Raporu",
            "sections": [
                {
                    "heading": f"Rapor Tarihi: {datetime.now().strftime('%d.%m.%Y %H:%M')}",
                    "data": []  # Bu bölümün sadece başlığı var, tablo verisi yok
                },
                {
                    "heading": "İşlem Detayları",
                    "data": [headers] + data_to_export
                }
            ]
        }

        try:
            generated_path = self.pdf_generator.generate_general_report_pdf(report_data, file_path)
            if generated_path:
                self.show_message("Başarılı", f"İşlemler PDF olarak başarıyla kaydedildi: {generated_path}")
            else:
                self.show_error("Hata", "PDF raporu oluşturulamadı.")
        except Exception as e:
            self.show_error("Hata", f"PDF raporu oluşturulurken bir hata oluştu: {e}")
            print(f"Hata: İşlemleri PDF'e aktarırken: {e}")

    def export_transactions_to_excel(self):
        """Ana listedeki gelir/gider verilerini Excel'e aktarır."""
        data_to_export = []
        # Not: self.tree yerine self.transactions_tree kullanılıyor
        headers = [self.transactions_tree.heading(col_id)['text'] for col_id in self.transactions_tree["columns"]]

        for item_id in self.transactions_tree.get_children():
            values = self.transactions_tree.item(item_id, 'values')
            data_to_export.append(values)

        if not data_to_export:
            self.show_message("Bilgi", "Dışa aktarılacak işlem verisi bulunamadı.")
            return

        file_path = filedialog.asksaveasfilename(defaultextension=".xlsx",
                                                 filetypes=[("Excel dosyaları", "*.xlsx"), ("CSV dosyaları", "*.csv")],
                                                 initialfile="gelir_gider_islemleri_raporu.xlsx")
        if not file_path:
            return

        try:
            df = pd.DataFrame(data_to_export, columns=headers)
            if file_path.endswith('.xlsx'):
                df.to_excel(file_path, index=False)
            elif file_path.endswith('.csv'):
                df.to_csv(file_path, index=False, encoding='utf-8-sig')
            self.show_message("Başarılı", f"İşlemler Excel olarak başarıyla kaydedildi: {file_path}")
            os.startfile(file_path)
        except Exception as e:
            self.show_error("Hata", f"Excel raporu oluşturulurken bir hata oluştu: {e}")
            print(f"Hata: İşlemleri Excel'e aktarırken: {e}")

