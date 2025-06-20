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
import pandas as pd  # Pandas kütüphanesini import et

# Gerekli modüllerin import edilmesi
from database_manager import DatabaseManager
from pdf_generator import PDFGenerator, GLOBAL_REPORTLAB_FONT_NAME
from ai_predictor import AIPredictor

# Matplotlib için Türkçe font ayarı
plt.rcParams['font.sans-serif'] = [GLOBAL_REPORTLAB_FONT_NAME, 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False


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

        self.pdf_generator = PDFGenerator(db_manager=self.db_manager, user_id=self.kullanici_id)
        self.ai_predictor = AIPredictor(db_manager=self.db_manager, user_id=self.kullanici_id)

        # validate_numeric_input fonksiyonunu bir kere kaydet
        self.validate_numeric_cmd = self.root.register(self._validate_numeric_input)

        self._create_main_ui()  # Yeni ana UI oluşturma metodunu çağırıyoruz

        # AI modelini UI oluşturulduktan sonra yükle/eğit
        # Çünkü UI elemanlarına (örneğin savings_analysis_text) ihtiyacı olabilir.
        self.ai_predictor.load_or_train_model()

        # İlk sekmelerin yüklenmesi ve veri çekimi notebook sekme değişim olayına bağlandı
        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_change)

        # Uygulama açılışında ilk sekmenin içeriğini yükle
        self._load_current_tab_content()

        print(
            f"DEBUG: GelirGiderUygulamasi başlatıldı. Kullanıcı ID: {self.kullanici_id}, Kullanıcı Adı: {self.username}")

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
        self.tax_report_tab_frame = ttk.Frame(self.notebook)

        self.notebook.add(self.transactions_tab_frame, text="Ana İşlemler")
        self.notebook.add(self.reports_analysis_tab_frame, text="Gelişmiş Araçlar & Raporlar")
        self.notebook.add(self.invoice_offer_tab_frame, text="Fatura & Teklifler")
        self.notebook.add(self.recurring_transactions_tab_frame, text="Tekrarlayan İşlemler")
        self.notebook.add(self.savings_goals_tab_frame, text="Tasarruf Hedefleri")
        self.notebook.add(self.customer_management_tab_frame, text="Müşteri Yönetimi")
        self.notebook.add(self.product_management_tab_frame, text="Ürün/Hizmet Yönetimi")
        self.notebook.add(self.category_management_tab_frame, text="Kategori Yönetimi")
        self.notebook.add(self.tax_report_tab_frame, text="Vergi Raporu")

        # Her sekmeye ilgili UI'ları oluştur
        self._create_transactions_ui(self.transactions_tab_frame)
        self._create_reports_analysis_ui(self.reports_analysis_tab_frame)
        self._create_invoice_offer_ui(self.invoice_offer_tab_frame)
        self._create_recurring_transactions_ui(self.recurring_transactions_tab_frame)
        self._create_savings_goals_ui(self.savings_goals_tab_frame)
        self._create_customer_management_ui(self.customer_management_tab_frame)
        self._create_product_management_ui(self.product_management_tab_frame)
        self._create_category_management_ui(self.category_management_tab_frame)
        self._create_tax_report_ui(self.tax_report_tab_frame)

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
        self._load_current_tab_content()

    def _load_current_tab_content(self):
        """Aktif sekmenin içeriğini yükler/günceller."""
        selected_tab = self.notebook.tab(self.notebook.select(), "text")
        print(f"DEBUG: Selected tab changed to: {selected_tab}")

        # Her sekmeye özel yükleme/listeleme fonksiyonlarını çağır
        if selected_tab == "Ana İşlemler":
            self.listele_islemler()
            self.guncelle_kategori_listesi()  # İşlem ekranı için kategori listesini güncelle
            self.on_transaction_type_selected()  # Varsayılan işlem tipi seçildiğinde kategorileri yükle
        elif selected_tab == "Gelişmiş Araçlar & Raporlar":
            self.render_charts()
            self.tasarruf_analizi_yap()
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
        elif selected_tab == "Vergi Raporu":
            self.generate_tax_report()

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
        # Şimdilik kullanıcıya özel etikette göstermeye devam edelim.
        # self.balance_label.config(text=f"Bakiye: {bakiye:.2f} TL")
        # if bakiye < 0:
        #     self.balance_label.config(foreground="red")
        # else:
        #     self.balance_label.config(foreground="green")

    # --- Ekran Geçiş Fonksiyonları (Artık sekme seçimi yapacak) ---
    # Bu fonksiyonlar artık doğrudan çağrılmayacak, Notebook sekme seçimi yapacak.
    # Yine de menü butonları olsaydı bu şekilde kullanılırdı.
    # Bu fonksiyonlar _on_tab_change metoduyla otomatik çağrıldığı için doğrudan arayüzde bir butona bağlanmaları gerekmiyor.
    # Eğer doğrudan bir butona bağlanacak olsaydı, self.notebook.select(frame_obj) yapılırdı.
    # Ancak burada sekmeler arası geçişi yönetmek için _on_tab_change yeterli.
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
        self.render_charts()
        self.tasarruf_analizi_yap()

    def show_category_management_screen(self):
        self.notebook.select(self.category_management_tab_frame)
        self.listele_kategoriler()

    def show_tax_report_screen(self):
        self.notebook.select(self.tax_report_tab_frame)
        self.generate_tax_report()

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

        # Bu kısım artık _create_main_ui içinde yapıldığı için burada çağırmaya gerek yok
        # self.listele_kategoriler()  # Başlangıçta kategorileri listele

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
            self.guncelle_kategori_listesi()  # Diğer ekranlardaki kategori comboboxlarını güncelle
            self.ai_predictor.load_or_train_model(force_retrain=True)  # Yeni kategori eklenince AI'ı tekrar eğit
        else:
            self.show_error("Hata", "Kategori eklenirken bir sorun oluştu veya bu kategori adı zaten mevcut.")

    def kategori_sil(self):
        if not self.selected_category_id:
            self.show_error("Hata", "Lütfen silmek istediğiniz kategoriyi seçin.")
            return

        # Kategori adını al
        selected_item = self.category_tree.selection()
        if not selected_item:
            self.show_error("Hata", "Lütfen silmek istediğiniz kategoriyi seçin.")
            return
        category_name_to_delete = self.category_tree.item(selected_item, 'values')[1]

        # Bu kategoriye ait işlem olup olmadığını kontrol et
        transaction_count = self.db_manager.count_transactions_by_category(category_name_to_delete, self.kullanici_id)

        if transaction_count > 0:
            confirm = messagebox.askyesno(
                "Onay",
                f"'{category_name_to_delete}' kategorisine ait {transaction_count} adet işlem bulunmaktadır. "
                "Bu kategoriyi silerseniz, ilgili işlemlerin kategorisi 'NULL' olarak ayarlanacaktır. Devam etmek istiyor musunuz?"
            )
            if not confirm:
                return

            # İşlemlerin kategorisini NULL yap
            if not self.db_manager.update_transactions_category_to_null(category_name_to_delete, self.kullanici_id):
                self.show_error("Hata", "İşlemlerin kategorisi güncellenirken bir sorun oluştu.")
                return

        if self.db_manager.delete_category(self.selected_category_id, self.kullanici_id):
            self.show_message("Başarılı", "Kategori başarıyla silindi.")
            self.selected_category_id = None
            self.temizle_kategori_formu()
            self.listele_kategoriler()
            self.guncelle_kategori_listesi()  # Diğer ekranlardaki kategori comboboxlarını güncelle
            self.listele_islemler()  # İşlem listesini yenile (NULL olanlar görünecek)
            self.ai_predictor.load_or_train_model(force_retrain=True)  # Kategori değiştiği için AI'ı tekrar eğit
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
        # Check if category_tree exists before configuring it
        if not (hasattr(self, 'category_tree') and self.category_tree.winfo_exists()):
            return  # If treeview is not yet created, just return

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
        categories = self.db_manager.get_all_categories(self.kullanici_id)  # Sadece isimleri çeken metot
        # Eğer bu comboboxlar oluşturulmuşsa güncelle
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
        transactions_frame.pack(fill="x", pady=10)  # expand=False, sadece genişlesin

        # Giriş Alanları
        input_grid_frame = ttk.Frame(transactions_frame)
        input_grid_frame.pack(pady=10, fill="x", padx=5)

        # İşlem Türü
        ttk.Label(input_grid_frame, text="İşlem Türü:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.transaction_type_combobox = ttk.Combobox(input_grid_frame, values=["Gelir", "Gider"], state="readonly",
                                                      width=20)
        self.transaction_type_combobox.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.transaction_type_combobox.set("Gider")  # Varsayılan değer
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
        self.guncelle_kategori_listesi()  # Kategori listesini yükle

        # Açıklama
        ttk.Label(input_grid_frame, text="Açıklama:").grid(row=3, column=0, padx=5, pady=5, sticky="w")
        self.transaction_description_entry = ttk.Entry(input_grid_frame, width=40)
        self.transaction_description_entry.grid(row=3, column=1, padx=5, pady=5, sticky="ew", columnspan=2)  # Daha uzun

        # Tarih
        ttk.Label(input_grid_frame, text="Tarih:").grid(row=4, column=0, padx=5, pady=5, sticky="w")
        self.transaction_date_entry = DateEntry(input_grid_frame, width=12, background='darkblue',
                                                foreground='white', borderwidth=2, locale='tr_TR')
        self.transaction_date_entry.grid(row=4, column=1, padx=5, pady=5, sticky="ew")

        # Grid ayarlamaları
        input_grid_frame.grid_columnconfigure(1, weight=1)  # Entry alanlarının genişlemesini sağla
        input_grid_frame.grid_columnconfigure(2, weight=1)  # Açıklama için ekstra genişlik

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
        filter_frame.pack(fill="x", pady=10)  # expand=False, sadece genişlesin

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
        ttk.Label(filter_grid_frame, text="-").grid(row=1, column=2, padx=2, pady=5)  # Ayırıcı
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
        self.transactions_tree = ttk.Treeview(parent_frame,
                                              columns=("ID", "Tarih", "Tip", "Miktar", "Kategori", "Açıklama"),
                                              show="headings")
        self.transactions_tree.heading("ID", text="ID")
        self.transactions_tree.heading("Tarih", text="Tarih")
        self.transactions_tree.heading("Tip", text="Tür")  # Resimdeki "Tür"e göre düzenlendi
        self.transactions_tree.heading("Miktar", text="Miktar (₺)")  # Resimdeki "Miktar (₺)"'e göre düzenlendi
        self.transactions_tree.heading("Kategori", text="Kategori")
        self.transactions_tree.heading("Açıklama", text="Açıklama")  # Resimdeki "Açıklama/Arama" değil "Açıklama"

        self.transactions_tree.column("ID", width=50, stretch=tk.NO)
        self.transactions_tree.column("Tarih", width=100, stretch=tk.NO)
        self.transactions_tree.column("Tip", width=70, stretch=tk.NO)
        self.transactions_tree.column("Miktar", width=100, stretch=tk.NO)
        self.transactions_tree.column("Kategori", width=150, stretch=tk.YES)
        self.transactions_tree.column("Açıklama", width=250, stretch=tk.YES)

        self.transactions_tree.pack(fill="both", expand=True, pady=10, padx=10)
        self.transactions_tree.bind("<ButtonRelease-1>", self.islem_sec)

    def _validate_numeric_input(self, P):
        """Sayısal giriş doğrulaması için utils'den gelen fonksiyonu kullanır."""
        from utils import validate_numeric_input as util_validate_numeric_input
        return util_validate_numeric_input(P)

    def on_transaction_type_selected(self, event=None):
        """İşlem tipi değiştiğinde kategori seçeneklerini günceller."""
        selected_type = self.transaction_type_combobox.get()
        categories = self.db_manager.get_categories_for_user(self.kullanici_id)

        filtered_categories = []
        for cat_id, cat_name, cat_type in categories:
            if cat_type == selected_type or cat_type == "Genel":
                filtered_categories.append(cat_name)

        # Check if the combobox exists before trying to configure it
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
            self.ai_predictor.load_or_train_model(force_retrain=True)  # Yeni işlem eklenince AI'ı tekrar eğit
            self.render_charts()  # Grafiklerin güncellenmesi için çağır
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
            self.ai_predictor.load_or_train_model(force_retrain=True)  # İşlem güncellenince AI'ı tekrar eğit
            self.render_charts()  # Grafiklerin güncellenmesi için çağır
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
                self.ai_predictor.load_or_train_model(force_retrain=True)  # İşlem silinince AI'ı tekrar eğit
                self.render_charts()  # Grafiklerin güncellenmesi için çağır
            else:
                self.show_error("Hata", "İşlem silinirken bir sorun oluştu.")

    def islem_sec(self, event):
        selected_item = self.transactions_tree.selection()
        if selected_item:
            values = self.transactions_tree.item(selected_item, 'values')
            self.selected_item_id = values[0]
            # tkcalendar DateEntry set_date için datetime objesi bekler
            if hasattr(self, 'transaction_date_entry') and self.transaction_date_entry.winfo_exists():
                try:
                    # Tarih veritabanından YYYY-MM-DD olarak gelir
                    self.transaction_date_entry.set_date(datetime.strptime(values[1], '%Y-%m-%d'))
                except ValueError:
                    self.show_error("Hata", "Veritabanından okunan tarih formatı geçersiz.")
                    self.transaction_date_entry.set_date(datetime.now())  # Varsayılan olarak bugünü ayarla
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
            return  # If treeview is not yet created, just return

        for item in self.transactions_tree.get_children():
            self.transactions_tree.delete(item)

        type_filter = self.filter_type_combobox.get()
        category_filter = self.filter_category_combobox.get()

        # Filtre tarihlerini ayrıştır
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
            start_date_db_format,  # Düzenlenmiş tarih formatını kullan
            end_date_db_format,  # Düzenlenmiş tarih formatını kullan
            search_term
        )

        for row in transactions:
            self.transactions_tree.insert("", "end", values=row)

    def temizle_islem_formu(self):
        if hasattr(self, 'transaction_date_entry') and self.transaction_date_entry.winfo_exists():
            self.transaction_date_entry.set_date(datetime.now())
        if hasattr(self, 'transaction_type_combobox') and self.transaction_type_combobox.winfo_exists():
            self.transaction_type_combobox.set("Gider")
            self.on_transaction_type_selected()  # Tipi "Gider" olarak ayarladıktan sonra kategorileri güncelle
        if hasattr(self, 'transaction_amount_entry') and self.transaction_amount_entry.winfo_exists():
            self.transaction_amount_entry.delete(0, tk.END)
        if hasattr(self, 'transaction_category_combobox') and self.transaction_category_combobox.winfo_exists():
            self.transaction_category_combobox.set("")
        if hasattr(self, 'transaction_description_entry') and self.transaction_description_entry.winfo_exists():
            self.transaction_description_entry.delete(0, tk.END)
        self.selected_item_id = None

        # Filtreleri de temizle
        if hasattr(self, 'filter_type_combobox') and self.filter_type_combobox.winfo_exists():
            self.filter_type_combobox.set("Tümü")
        if hasattr(self, 'filter_category_combobox') and self.filter_category_combobox.winfo_exists():
            self.filter_category_combobox.set("Tümü")
        # Tarih girişlerini de temizle veya varsayılan tarihe ayarla
        if hasattr(self, 'filter_start_date_entry') and self.filter_start_date_entry.winfo_exists():
            # Varsayılan olarak son bir ayı veya başlangıcı ayarlayabiliriz
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
            self.guncelle_kategori_listesi()  # Kategori listesi değişebileceği için güncelle

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
        self.guncelle_kategori_listesi()  # Kategori listesini yükle

        ttk.Label(input_frame, text="Başlangıç Tarihi:").grid(row=4, column=0, padx=5, pady=5, sticky="w")
        self.recurring_start_date_entry = DateEntry(input_frame, width=12, background='darkblue', foreground='white',
                                                    borderwidth=2, locale='tr_TR')
        self.recurring_start_date_entry.grid(row=4, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(input_frame, text="Sıklık:").grid(row=5, column=0, padx=5, pady=5, sticky="w")
        self.recurring_frequency_combobox = ttk.Combobox(input_frame, values=["Günlük", "Haftalık", "Aylık", "Yıllık"],
                                                         state="readonly")
        self.recurring_frequency_combobox.grid(row=5, column=1, padx=5, pady=5, sticky="ew")
        self.recurring_frequency_combobox.set("Aylık")  # Varsayılan

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

        # Check if the combobox exists before trying to configure it
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

        # İlk eklendiğinde son üretilen tarih başlangıç tarihi ile aynı olsun
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
                self.recurring_frequency_combobox.set(values[6])
        else:
            self.temizle_tekrarlayan_islem_formu()

    def listele_tekrarlayan_islemler(self):
        if not (hasattr(self, 'recurring_tree') and self.recurring_tree.winfo_exists()):
            return  # If treeview is not yet created, just return

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
            self.on_recurring_type_selected()  # Tipi "Gider" olarak ayarladıktan sonra kategorileri güncelle
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
            # Tarihleri datetime.date objesine çevir
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            last_generated_date = datetime.strptime(last_generated_date_str,
                                                    '%Y-%m-%d').date() if last_generated_date_str else start_date

            next_due_date = last_generated_date

            # İlk işlem henüz kaydedilmemişse (last_generated_date == start_date ve bugünden küçükse)
            # veya last_generated_date henüz güncellenmemişse, başlangıç tarihinden itibaren kontrol et
            if last_generated_date < start_date:  # Bu durum olmamalı ama önlem alalım
                next_due_date = start_date

            # Gelecekteki ilk uygun tarihi bul
            while next_due_date <= today:
                # next_due_date, last_generated_date'den büyük veya eşit olmalı
                if next_due_date > last_generated_date:
                    # Ana işlemlere ekle
                    if self.db_manager.insert_transaction(type, amount, category, description,
                                                          next_due_date.strftime('%Y-%m-%d'), self.kullanici_id):
                        generated_count += 1
                        print(f"Tekrarlayan işlem '{description}' ({next_due_date.strftime('%Y-%m-%d')}) oluşturuldu.")
                    else:
                        print(
                            f"Hata: Tekrarlayan işlem '{description}' ({next_due_date.strftime('%Y-%m-%d')}) eklenirken sorun oluştu.")

                    # İşlem eklendikten sonra last_generated_date'i güncelle
                    self.db_manager.update_recurring_transaction_last_generated_date(rec_id,
                                                                                     next_due_date.strftime('%Y-%m-%d'))
                    self.guncelle_bakiye()  # Bakiye değiştiği için güncelle
                    self.listele_islemler()  # İşlem listesini yenile
                    self.ai_predictor.load_or_train_model(force_retrain=True)  # Yeni işlem eklenince AI'ı tekrar eğit
                    self.render_charts()  # Grafiklerin güncellenmesi için çağır

                # Bir sonraki tekrarlama tarihini hesapla
                if frequency == "Günlük":
                    next_due_date += timedelta(days=1)
                elif frequency == "Haftalık":
                    next_due_date += timedelta(weeks=1)
                elif frequency == "Aylık":
                    # Ay atlamalarında gün sayısını doğru hesaplamak için
                    current_month = next_due_date.month
                    current_year = next_due_date.year
                    next_month = current_month + 1
                    next_year = current_year
                    if next_month > 12:
                        next_month = 1
                        next_year += 1

                    try:
                        next_due_date = next_due_date.replace(year=next_year, month=next_month)
                    except ValueError:  # Örneğin Şubat ayında 31. gün olmaz
                        # Ayın son gününe ayarla
                        last_day_of_next_month = (datetime(next_year, next_month + 1, 1) - timedelta(
                            days=1)).date() if next_month < 12 else (
                                    datetime(next_year + 1, 1, 1) - timedelta(days=1)).date()
                        next_due_date = last_day_of_next_month

                elif frequency == "Yıllık":
                    next_due_date = next_due_date.replace(year=next_due_date.year + 1)
                else:
                    break  # Geçersiz sıklık

        if generated_count > 0:
            self.show_message("Tekrarlayan İşlemler",
                              f"{generated_count} adet tekrarlayan işlem başarıyla oluşturuldu.")
            self.listele_tekrarlayan_islemler()  # Son üretilen tarihleri yansıtmak için listeyi yenile
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
        self.goal_current_amount_entry.insert(0, "0.0")  # Varsayılan 0

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
        self.goal_status_combobox.set("Devam Ediyor")  # Varsayılan durum

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
            return  # If treeview is not yet created, just return

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

        goal_name = self.goal_name_entry.get().strip()  # Adı göstermek için alıyoruz
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

            # Text widget'ı oluşturulmuşsa içeriği güncelle
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

        # Müşteri adı değiştiyse, fatura/tekliflerdeki müşteri adını da güncelle
        selected_item = self.customer_tree.selection()
        current_customer_name = self.customer_tree.item(selected_item[0], 'values')[1] if selected_item else None

        if not name:
            self.show_error("Hata", "Müşteri adı boş olamaz.")
            return

        # Eğer müşteri adı değiştiyse ve yeni isim zaten başka bir müşteride varsa hata ver.
        if name != current_customer_name and self.db_manager.get_customer_by_name(name, self.kullanici_id):
            self.show_error("Hata", f"'{name}' isimli bir müşteri zaten mevcut.")
            return

        if self.db_manager.update_customer(self.selected_customer_id, name, address if address else None,
                                           phone if phone else None, email if email else None, self.kullanici_id):
            # Müşteri adı değiştiyse, ilgili faturaları da güncelle
            if name != current_customer_name:
                self.db_manager.update_invoice_customer_name(current_customer_name, name, self.kullanici_id)

            self.show_message("Başarılı", "Müşteri başarıyla güncellendi.")
            self.temizle_musteri_formu()
            self.listele_musteriler()
            self.listele_faturalar_teklifler()  # Fatura/teklif listesini de yenile
        else:
            self.show_error("Hata", "Müşteri güncellenirken bir sorun oluştu.")

    def musteri_sil(self):
        if not self.selected_customer_id:
            self.show_error("Hata", "Lütfen silmek istediğiniz bir müşteri seçin.")
            return

        selected_item = self.customer_tree.selection()
        customer_name_to_delete = self.customer_tree.item(selected_item[0], 'values')[1] if selected_item else None

        # Müşteriye ait fatura/teklif olup olmadığını kontrol et
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
            return  # If treeview is not yet created, just return

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
        self.product_kdv_rate_entry.insert(0, "18.0")  # Varsayılan KDV oranı

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

        # Ürün adı değiştiyse, yeni adın başka bir üründe olup olmadığını kontrol et
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
            self.listele_faturalar_teklifler()  # Fatura/teklif listesi güncellenmiş ürün isimleri için yenile
        else:
            self.show_error("Hata", "Ürün/Hizmet güncellenirken bir sorun oluştu.")

    def urun_sil(self):
        if not self.selected_product_id:
            self.show_error("Hata", "Lütfen silmek istediğiniz bir ürün/hizmet seçin.")
            return

        # Ürünün herhangi bir faturada/teklifte kullanılıp kullanılmadığını kontrol etmek daha karmaşık olabilir
        # (items_json içinde arama yapmak gerekir). Şimdilik bu kontrolü atlıyorum.
        # Eğer bu kontrolü eklemek istersek, items_json'ları parse edip içinde ürün adına göre arama yapmalıyız.

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
            return  # If treeview is not yet created, just return

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
        self.doc_number_entry = ttk.Entry(header_frame, state="readonly")  # Otomatik atanacak
        self.doc_number_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        ttk.Button(header_frame, text="Numara Oluştur", command=self.generate_document_number).grid(row=1, column=2,
                                                                                                    padx=5, pady=5)

        ttk.Label(header_frame, text="Müşteri:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.invoice_customer_combobox = ttk.Combobox(header_frame, state="readonly")
        self.invoice_customer_combobox.grid(row=2, column=1, padx=5, pady=5, sticky="ew")
        # self.update_customer_combobox() # Müşteri listesini yükle - _load_current_tab_content() içinde çağrılacak

        ttk.Label(header_frame, text="Belge Tarihi:").grid(row=3, column=0, padx=5, pady=5, sticky="w")
        self.invoice_date_entry = DateEntry(header_frame, width=12, background='darkblue', foreground='white',
                                            borderwidth=2, locale='tr_TR')
        self.invoice_date_entry.grid(row=3, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(header_frame, text="Vade/Geçerlilik Tarihi:").grid(row=4, column=0, padx=5, pady=5, sticky="w")
        self.invoice_due_valid_date_entry = DateEntry(header_frame, width=12, background='darkblue', foreground='white',
                                                      borderwidth=2, locale='tr_TR')
        self.invoice_due_valid_date_entry.grid(row=4, column=1, padx=5, pady=5, sticky="ew")
        # self.generate_document_number() # İlk numarayı oluştur - _load_current_tab_content() içinde çağrılacak

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
        # self.update_product_combobox_for_invoice_items() # Ürün listesini yükle - _load_current_tab_content() içinde çağrılacak

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

        notes_status_frame.grid_columnconfigure(1, weight=1)  # Notlar alanının genişlemesini sağla

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
        # Check if the combobox exists before trying to configure it
        if hasattr(self, 'invoice_customer_combobox') and self.invoice_customer_combobox.winfo_exists():
            self.invoice_customer_combobox['values'] = customer_names
            if customer_names:
                self.invoice_customer_combobox.set(customer_names[0])
            else:
                self.invoice_customer_combobox.set("")

    def update_product_combobox_for_invoice_items(self):
        products = self.db_manager.get_products(self.kullanici_id)
        product_names = [p[1] for p in products]
        # Check if the combobox exists before trying to configure it
        if hasattr(self, 'item_product_combobox') and self.item_product_combobox.winfo_exists():
            self.item_product_combobox['values'] = product_names
            if product_names:
                self.item_product_combobox.set(product_names[0])
                self.on_product_selected_for_item()  # İlk ürünün bilgilerini otomatik yükle
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
                # product_info: id, name, stock, purchase_price, selling_price, kdv_rate
                self.current_selected_product_details = {
                    "id": product_info[0],
                    "name": product_info[1],
                    "stock": product_info[2],
                    "purchase_price": product_info[3],
                    "selling_price": product_info[4],
                    "kdv_rate": product_info[5]
                }
                if hasattr(self, 'item_unit_price_label') and self.item_unit_price_label.winfo_exists():
                    self.item_unit_price_label.config(text=f"{product_info[4]:.2f} TL")  # Satış fiyatı
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
            # Eğer miktar boşsa veya geçerli bir sayı değilse 0 olarak kabul et
            quantity = float(quantity_str) if quantity_str and self._validate_numeric_input(quantity_str) else 0.0

            unit_price = self.current_selected_product_details["selling_price"]
            kdv_rate = self.current_selected_product_details["kdv_rate"] / 100.0  # Yüzdeyi ondalığa çevir

            subtotal_before_kdv = quantity * unit_price
            kdv_amount = subtotal_before_kdv * kdv_rate
            total_with_kdv = subtotal_before_kdv + kdv_amount

            if hasattr(self, 'item_kdv_amount_label') and self.item_kdv_amount_label.winfo_exists():
                self.item_kdv_amount_label.config(text=f"{kdv_amount:.2f} TL")
            if hasattr(self, 'item_subtotal_label') and self.item_subtotal_label.winfo_exists():
                self.item_subtotal_label.config(text=f"{total_with_kdv:.2f} TL")  # Ara toplam KDV dahil gösteriliyor

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

        product_info = self.current_selected_product_details  # Already loaded on product selection
        if not product_info:
            self.show_error("Hata", "Ürün bilgileri yüklenemedi. Lütfen geçerli bir ürün seçin.")
            return

        # Stok kontrolü sadece fatura için yapılır
        if self.doc_type_combobox.get() == "Fatura" and quantity > product_info["stock"]:
            self.show_error("Hata", f"Yetersiz stok! Mevcut stok: {product_info['stock']:.2f}")
            return

        # Eğer aynı ürün zaten eklenmişse miktarı güncelle
        if hasattr(self, 'invoice_items_tree') and self.invoice_items_tree.winfo_exists():
            for item_id in self.invoice_items_tree.get_children():
                item_values = self.invoice_items_tree.item(item_id, 'values')
                if item_values[0] == product_name:
                    existing_quantity = float(item_values[1])
                    new_quantity = existing_quantity + quantity

                    # Güncellenmiş stok kontrolü
                    if self.doc_type_combobox.get() == "Fatura" and new_quantity > product_info["stock"]:
                        self.show_error("Hata",
                                        f"Bu ürün için toplam miktar ({new_quantity}) stok ({product_info['stock']}) miktarını aşıyor. Lütfen miktarı düşürün.")
                        return

                    # Hesaplamaları yeniden yap
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

            # Yeni kalem ekle
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

                # Ürün combobox'ını ve miktar alanını güncelle
                if hasattr(self, 'item_product_combobox') and self.item_product_combobox.winfo_exists():
                    self.item_product_combobox.set(product_name)
                self.on_product_selected_for_item()  # Ürün bilgilerini yükle
                if hasattr(self, 'item_quantity_entry') and self.item_quantity_entry.winfo_exists():
                    self.item_quantity_entry.delete(0, tk.END)
                    self.item_quantity_entry.insert(0, quantity)
                self.calculate_item_totals_on_change()  # Toplamları tekrar hesapla
        else:
            self.show_error("Hata", "Fatura kalemleri tablosu henüz oluşturulmadı.")

    def calculate_grand_totals(self):
        total_excl_kdv = 0.0
        total_kdv = 0.0

        if hasattr(self, 'invoice_items_tree') and self.invoice_items_tree.winfo_exists():
            for item_id in self.invoice_items_tree.get_children():
                values = self.invoice_items_tree.item(item_id, 'values')
                # amounts are already formatted strings, convert back to float
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
            return  # If widgets are not yet created, just return

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

            # Belge numarası sayacını güncelle
            if doc_type == "Fatura":
                current_invoice_num, current_offer_num = self.db_manager.get_user_invoice_offer_nums(self.kullanici_id)
                self.db_manager.update_user_invoice_offer_num(self.kullanici_id, invoice_num=current_invoice_num + 1)
                # Stoktan düşme işlemi (sadece fatura oluşturulurken)
                for item_data in items_list:
                    product_name = item_data['ad']
                    quantity = item_data['miktar']
                    product_info = self.db_manager.get_product_by_name(product_name, self.kullanici_id)
                    if product_info:
                        new_stock = product_info[2] - quantity  # product_info[2] is stock
                        self.db_manager.update_product_stock(product_info[0],
                                                             new_stock)  # product_info[0] is product_id
            elif doc_type == "Teklif":
                current_invoice_num, current_offer_num = self.db_manager.get_user_invoice_offer_nums(self.kullanici_id)
                self.db_manager.update_user_invoice_offer_num(self.kullanici_id, offer_num=current_offer_num + 1)

            self.show_message("Başarılı", f"{doc_type} başarıyla kaydedildi.")
            self.clear_invoice_offer_form()
            self.listele_faturalar_teklifler()
            self.listele_urunler()  # Stok güncellendiği için ürün listesini yenile

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

        # Eğer fatura güncellenirken tipi veya kalemi değişiyorsa stokları düzeltmek karmaşık olabilir.
        # Bu yüzden, eğer fatura ise ve stok etkilenecekse, bu işlemi basitleştirmek adına:
        # Eski kalemlerin stoklarını geri yükleyip, yeni kalemlerin stoklarını düşürebiliriz.
        # Ancak bu, daha önce kaydedilmiş olan faturaların stoklarını doğru takip etmeyi gerektirir.
        # Basitlik adına, mevcut durumda yalnızca yeni fatura oluşturulduğunda stok düşüşü yapıyoruz.
        # Güncelleme sırasında stok yönetimi, iş mantığına göre daha detaylı ele alınabilir.

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

        doc_type = selected_item_data[1]  # type (Fatura/Teklif)
        items_json = selected_item_data[6]  # items_json

        if messagebox.askyesno("Onay", f"Seçili {doc_type}'i silmek istediğinizden emin misiniz?"):
            if self.db_manager.delete_invoice_offer(self.selected_invoice_offer_id, self.kullanici_id):
                # Eğer fatura siliniyorsa, stokları geri yükle
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
                        self.listele_urunler()  # Ürün listesini yenile
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

            # Detayları veritabanından çek (items_json ve diğer tüm alanlar için)
            doc_detail = self.db_manager.get_invoice_offer_by_id(self.selected_invoice_offer_id, self.kullanici_id)
            if doc_detail:
                # doc_detail: id, type, document_number, customer_name, document_date, due_validity_date, items_json, total_amount_excluding_kdv, total_kdv_amount, total_amount_with_kdv, notes, status

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
                    if doc_detail[5]:  # due_validity_date olabilir
                        try:
                            self.invoice_due_valid_date_entry.set_date(datetime.strptime(doc_detail[5], '%Y-%m-%d'))
                        except ValueError:
                            self.show_error("Hata", "Veritabanından okunan vade/geçerlilik tarih formatı geçersiz.")
                            self.invoice_due_valid_date_entry.set_date(datetime.now())
                    else:
                        self.invoice_due_valid_date_entry.set_date(datetime.now())  # Varsayılan olarak bugünü ayarla

                if hasattr(self, 'invoice_notes_text') and self.invoice_notes_text.winfo_exists():
                    self.invoice_notes_text.delete("1.0", tk.END)
                    if doc_detail[9]:
                        self.invoice_notes_text.insert("1.0", doc_detail[9])

                if hasattr(self, 'invoice_status_combobox') and self.invoice_status_combobox.winfo_exists():
                    self.invoice_status_combobox.set(doc_detail[10])

                # Kalemleri Treeview'e yükle
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

                self.calculate_grand_totals()  # Seçili belgenin toplamlarını güncelle
            else:
                self.show_error("Hata", "Seçili fatura/teklif detayları yüklenemedi.")
                self.clear_invoice_offer_form()
        else:
            self.clear_invoice_offer_form()

    def listele_faturalar_teklifler(self):
        # Check if invoices_offers_tree exists before configuring it
        if not (hasattr(self, 'invoices_offers_tree') and self.invoices_offers_tree.winfo_exists()):
            return  # If treeview is not yet created, just return

        for item in self.invoices_offers_tree.get_children():
            self.invoices_offers_tree.delete(item)

        invoices_offers = self.db_manager.get_invoice_offers(self.kullanici_id)
        for io_id, type, doc_num, customer, total_excl_kdv, total_kdv, grand_total, doc_date, status, notes in invoices_offers:
            self.invoices_offers_tree.insert("", "end", values=(io_id, type, doc_num, customer, f"{total_excl_kdv:.2f}",
                                                                f"{grand_total:.2f}", doc_date, status, notes))

    def clear_invoice_offer_form(self):
        self.selected_invoice_offer_id = None
        # Check if doc_type_combobox exists before configuring it
        if hasattr(self, 'doc_type_combobox') and self.doc_type_combobox.winfo_exists():
            self.doc_type_combobox.set("Fatura")
        self.generate_document_number()  # Yeni belge numarası oluştur
        self.update_customer_combobox()  # Müşteri combobox'ını yenile

        # Check if invoice_date_entry exists before configuring it
        if hasattr(self, 'invoice_date_entry') and self.invoice_date_entry.winfo_exists():
            self.invoice_date_entry.set_date(datetime.now())

        # Check if invoice_due_valid_date_entry exists before configuring it
        if hasattr(self, 'invoice_due_valid_date_entry') and self.invoice_due_valid_date_entry.winfo_exists():
            self.invoice_due_valid_date_entry.set_date(datetime.now())

        # Check if invoice_notes_text exists before configuring it
        if hasattr(self, 'invoice_notes_text') and self.invoice_notes_text.winfo_exists():
            self.invoice_notes_text.delete("1.0", tk.END)

        # Check if invoice_status_combobox exists before configuring it
        if hasattr(self, 'invoice_status_combobox') and self.invoice_status_combobox.winfo_exists():
            self.invoice_status_combobox.set("Taslak")

        # Kalemler listesini temizle
        if hasattr(self, 'invoice_items_tree') and self.invoice_items_tree.winfo_exists():
            for item in self.invoice_items_tree.get_children():
                self.invoice_items_tree.delete(item)
        self.temizle_invoice_item_form()  # Kalem ekleme formunu da temizle
        self.calculate_grand_totals()  # Toplamları sıfırla

    def temizle_invoice_item_form(self):
        # Check if item_product_combobox exists before configuring it
        if hasattr(self, 'item_product_combobox') and self.item_product_combobox.winfo_exists():
            self.item_product_combobox.set("")

        # Check if item_quantity_entry exists before configuring it
        if hasattr(self, 'item_quantity_entry') and self.item_quantity_entry.winfo_exists():
            self.item_quantity_entry.delete(0, tk.END)
            self.item_quantity_entry.insert(0, "1.0")

        # Check if item_unit_price_label exists before configuring it
        if hasattr(self, 'item_unit_price_label') and self.item_unit_price_label.winfo_exists():
            self.item_unit_price_label.config(text="0.00 TL")

        # Check if item_kdv_rate_label exists before configuring it
        if hasattr(self, 'item_kdv_rate_label') and self.item_kdv_rate_label.winfo_exists():
            self.item_kdv_rate_label.config(text="0.00%")

        # Check if item_kdv_amount_label exists before configuring it
        if hasattr(self, 'item_kdv_amount_label') and self.item_kdv_amount_label.winfo_exists():
            self.item_kdv_amount_label.config(text="0.00 TL")

        # Check if item_subtotal_label exists before configuring it
        if hasattr(self, 'item_subtotal_label') and self.item_subtotal_label.winfo_exists():
            self.item_subtotal_label.config(text="0.00 TL")

        self.current_selected_product_details = None
        self.update_product_combobox_for_invoice_items()  # Ürün combobox'ını yenile

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
            # doc_detail'den gerekli bilgileri al
            doc_id, doc_type, doc_number, customer_name, doc_date, due_validity_date, items_json, \
                total_excl_kdv, total_kdv, total_with_kdv, notes, status = doc_detail

            items_list = json.loads(items_json)

            # PDFGenerator'a gönderilecek veriyi tek bir sözlükte topla
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
                # Yeni PDFGenerator'da total_excl_kdv + total_kdv olarak yeniden hesaplanıyor, ama yine de gönderelim
                "notes": notes,
                "status": status
            }

            # Dosya kaydetme diyaloğunu aç
            file_path = filedialog.asksaveasfilename(
                defaultextension=".pdf",
                filetypes=[("PDF files", "*.pdf")],
                initialfile=f"{doc_number}.pdf",
                title=f"{doc_type} PDF Kaydet"
            )

            if file_path:
                # PDFGenerator'daki generate_document_pdf metodunu çağır
                # Bu metot kendi içinde müşteri bilgilerini çekecektir.
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

        # Grafik Alanı
        chart_frame = ttk.LabelFrame(self.reports_analysis_frame, text="Finansal Grafikler", padding="10")
        chart_frame.pack(fill="both", expand=True, padx=5, pady=5)
        self.chart_canvas_frame = ttk.Frame(chart_frame)
        self.chart_canvas_frame.pack(fill="both", expand=True)
        # Grafiklerin buraya yerleşeceğini belirtiyoruz. Render metodunda eski grafikler temizlenip yenileri eklenecek.

        # Tasarruf Analizi Alanı
        analysis_frame = ttk.LabelFrame(self.reports_analysis_frame, text="Tasarruf Analizi ve Önerileri", padding="10")
        analysis_frame.pack(fill="both", expand=True, padx=5, pady=5)
        self.savings_analysis_text = tk.Text(analysis_frame, wrap="word", height=15, width=80, font=("Arial", 10),
                                             state="disabled", bg="#f8f8f8")
        self.savings_analysis_text.pack(fill="both", expand=True)

    def render_charts(self):
        """Grafikleri çizer veya günceller."""
        # Mevcut grafik widget'larını temizle ve figürleri kapat
        if self.canvas_category and self.canvas_category.get_tk_widget().winfo_exists():
            self.canvas_category.get_tk_widget().destroy()
        if self.fig_category:
            plt.close(self.fig_category)
            self.fig_category = None  # Figürü sıfırla

        if self.canvas_balance and self.canvas_balance.get_tk_widget().winfo_exists():
            self.canvas_balance.get_tk_widget().destroy()
        if self.fig_balance:
            plt.close(self.fig_balance)
            self.fig_balance = None  # Figürü sıfırla

        # Kategori bazında gelir/gider verisi
        # Bu metod DatabaseManager'dan kategori ve toplam miktar döner: (type, category, total_amount)
        category_summary_data = self.db_manager.get_income_expenses_by_month_and_category(self.kullanici_id,
                                                                                          num_months=12)

        # Zaman serisi bakiye verisi
        # Bu metod DatabaseManager'dan (date, type, amount) döner
        time_series_raw_data = self.db_manager.get_monthly_balance_trend(self.kullanici_id, num_months=12)

        # Kategori Bazında Gelir/Gider Pastası
        expense_by_category = {}
        income_by_category = {}
        if category_summary_data:
            for type, category, amount in category_summary_data:
                if category:  # Kategorisi olmayanları dahil etmiyoruz
                    if type == 'Gider':
                        expense_by_category[category] = expense_by_category.get(category, 0) + amount
                    elif type == 'Gelir':
                        income_by_category[category] = income_by_category.get(category, 0) + amount

        self.fig_category, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 5))  # İki grafik yan yana

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

        self.fig_category.tight_layout()
        self.canvas_category = FigureCanvasTkAgg(self.fig_category, master=self.chart_canvas_frame)
        self.canvas_category.draw()
        self.canvas_category.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True, pady=10)

        # Zaman Serisi Bakiye Grafiği
        if time_series_raw_data:
            # Pandas DataFrame'e dönüştür
            df = pd.DataFrame(time_series_raw_data, columns=['date', 'type', 'amount'])
            df['date'] = pd.to_datetime(df['date'])
            df.set_index('date', inplace=True)

            # İşlem tipine göre miktarları işaretle (Gelir pozitif, Gider negatif)
            df['signed_amount'] = df.apply(lambda row: row['amount'] if row['type'] == 'Gelir' else -row['amount'],
                                           axis=1)

            # Tarihe göre sırala
            df = df.sort_values('date')

            # Kümülatif bakiyeyi hesapla
            df['cumulative_balance'] = df['signed_amount'].cumsum()

            # Her ayın sonundaki kümülatif bakiyeyi al
            # resample('M') aylık frekans. last() ayın son günündeki değeri alır. ffill() ileriye doğru doldurur. fillna(0) boşlukları 0 yapar.
            monthly_cumulative_balance = df['cumulative_balance'].resample('M').last().ffill().fillna(0)

            self.fig_balance, ax = plt.subplots(figsize=(10, 5))
            monthly_cumulative_balance.plot(ax=ax, kind='line', marker='o')
            ax.set_title('Aylık Kümülatif Bakiye Trendi')
            ax.set_xlabel('Tarih')
            ax.set_ylabel('Bakiye (TL)')
            ax.grid(True)
            self.fig_balance.tight_layout()
            self.canvas_balance = FigureCanvasTkAgg(self.fig_balance, master=self.chart_canvas_frame)
            self.canvas_balance.draw()
            self.canvas_balance.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True, pady=10)
        else:
            self.fig_balance, ax = plt.subplots(figsize=(10, 5))
            ax.text(0.5, 0.5, 'Bakiye Trendi Verisi Yok', horizontalalignment='center', verticalalignment='center',
                    transform=ax.transAxes)
            ax.set_title('Aylık Kümülatif Bakiye Trendi')
            self.canvas_balance = FigureCanvasTkAgg(self.fig_balance, master=self.chart_canvas_frame)
            self.canvas_balance.draw()
            self.canvas_balance.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True, pady=10)

    # --- Vergi Raporu UI ve Fonksiyonları ---
    def _create_tax_report_ui(self, parent_frame):
        """Vergi Raporu arayüzünü oluşturur."""
        tax_report_frame = ttk.LabelFrame(parent_frame, text="Vergi Raporu", padding="15")
        tax_report_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Tarih Seçimi
        date_selection_frame = ttk.Frame(tax_report_frame)
        date_selection_frame.pack(pady=10)

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

        # Rapor Metin Alanı
        self.tax_report_text = tk.Text(tax_report_frame, wrap="word", height=20, font=("Arial", 10), state="disabled",
                                       bg="#f8f8f8")
        self.tax_report_text.pack(fill="both", expand=True, pady=10)

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

        report_content = []
        report_content.append("--- Vergi Raporu ---\n")
        report_content.append(f"Tarih Aralığı: {start_date_db_format} - {end_date_db_format}\n")

        # Toplam KDV'leri hesapla
        total_sales_kdv = self.db_manager.get_total_sales_kdv(start_date_db_format, end_date_db_format,
                                                              self.kullanici_id)

        # Alış KDV'sini hesaplamak için, ürünlerin alış fiyatlarındaki KDV'yi çekmemiz gerekir.
        # Bu, doğrudan bir fatura kaleminden gelmediği için biraz daha karmaşık.
        # Basit bir yaklaşım olarak, buraya manuel giriş veya transaction kayıtlarındaki giderlerden KDV tahmini ekleyebiliriz.
        # Şu an için sadece satış KDV'si raporlanıyor.

        # Detaylı KDV dökümü (fatura kalemlerinden)
        invoice_item_jsons = self.db_manager.get_invoice_jsons_for_tax_report(start_date_db_format, end_date_db_format,
                                                                              self.kullanici_id)

        kdv_by_rate = {}  # {KDV_Oranı: Toplam_KDV_Miktarı}

        for item_json_tuple in invoice_item_jsons:
            items_list = json.loads(item_json_tuple[0])
            for item in items_list:
                kdv_rate = item.get("kdv_orani", 0)
                kdv_amount = item.get("kdv_miktari", 0)
                kdv_by_rate[kdv_rate] = kdv_by_rate.get(kdv_rate, 0) + kdv_amount

        report_content.append("--- Detaylı Satış KDV Dökümü ---")
        if kdv_by_rate:
            for rate, amount in sorted(kdv_by_rate.items()):
                report_content.append(f"KDV Oranı %{rate:.2f}: {amount:.2f} TL")
        else:
            report_content.append("Bu dönemde satış KDV'si içeren fatura kalemi bulunamadı.")
        report_content.append("\n")

        report_content.append(f"Toplam Hesaplanan KDV (Çıkış KDV'si): {total_sales_kdv:.2f} TL")
        report_content.append(
            "Giriş KDV'si (Alış KDV'si) hesaplaması için manuel giriş veya detaylı fiş/fatura takibi gereklidir.\\n")
        report_content.append(
            "Önemli Not: Bu rapor bir mali müşavir raporu değildir. Yalnızca bilgilendirme amaçlıdır. "
            "Gerçek vergi beyanlarınız için lütfen bir mali müşavire danışın.")

        self.tax_report_text.config(state="normal")
        self.tax_report_text.delete("1.0", tk.END)
        self.tax_report_text.insert("1.0", "\n".join(report_content))
        self.tax_report_text.config(state="disabled")
        self.show_message("Rapor Oluşturuldu", "Vergi raporu başarıyla oluşturuldu.")

