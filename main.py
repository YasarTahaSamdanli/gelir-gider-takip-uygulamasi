# main.py
import tkinter as tk
from tkinter import messagebox
import time
import os
import sys
import matplotlib.pyplot as plt

# Modülleri içe aktar
from database_manager import DatabaseManager
from auth_screens import LoginScreen, RegisterScreen
from fingo_app import GelirGiderUygulamasi
# pdf_generator'dan sadece GLOBAL_REPORTLAB_FONT_NAME ve _register_pdf_font'u import et
from pdf_generator import GLOBAL_REPORTLAB_FONT_NAME, _register_pdf_font

# --- Global Font Ayarları (Uygulama Genelinde) ---
# Font dosyasının adı ve yolu
GLOBAL_FONT_FILE_NAME = "Arial.ttf"
if hasattr(sys, '_MEIPASS'):
    # PyInstaller ile derlenmişse, font dosyasını _MEIPASS dizininde ara
    GLOBAL_FONT_SOURCE_PATH = os.path.join(sys._MEIPASS, GLOBAL_FONT_FILE_NAME)
else:
    # Normal Python çalışmasında, betiğin bulunduğu dizinde ara
    GLOBAL_FONT_SOURCE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), GLOBAL_FONT_FILE_NAME)

# PDFGenerator'ın kullanacağı fontu kaydet (pdf_generator modülündeki fonksiyonu çağırarak)
try:
    _register_pdf_font(GLOBAL_FONT_SOURCE_PATH)
except Exception as e:
    messagebox.showwarning("Font Yükleme Hatası",
                           f"Hata: ReportLab'a font yüklenirken bir sorun oluştu: {e}. PDF'de Türkçe karakter sorunları olabilir.")

# Matplotlib için Türkçe font ayarı
plt.rcParams['font.sans-serif'] = [GLOBAL_REPORTLAB_FONT_NAME, 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False


class LoginRegisterApp:
    def __init__(self, root):
        """
        Giriş/Kayıt uygulamasının ana denetleyicisi.
        Veritabanı bağlantısını yönetir ve ekranlar arasında geçiş yapar.
        """
        self.root = root
        self.root.title("Giriş / Kayıt")
        self.root.geometry("400x300")
        self.root.resizable(False, False)
        self.root.configure(bg="#f5f5f5")

        self.db_manager = None  # DatabaseManager örneği
        self.current_frame = None  # Aktif ekran çerçevesi

        self.baglanti_olustur()  # Veritabanı bağlantısını kur ve tabloları oluştur

        self.show_login_screen()

    def baglanti_olustur(self):
        """DatabaseManager'ı başlatır ve veritabanı tablolarını oluşturur."""
        try:
            self.db_manager = DatabaseManager(
                "veriler.db")  # database_manager modülünden DatabaseManager sınıfını kullan
            print("Veritabanı bağlantısı ve tablolar başarıyla oluşturuldu.")
        except ConnectionError as e:
            messagebox.showerror("Veritabanı Hatası",
                                 f"{e}\nLütfen uygulamanın bulunduğu klasördeki 'veriler.db' dosyasını silip tekrar deneyin.")
            self.root.destroy()
        except Exception as e:
            messagebox.showerror("Uygulama Başlatma Hatası", f"Uygulama başlatılırken beklenmeyen bir hata oluştu: {e}")
            self.root.destroy()

    def show_login_screen(self):
        """Giriş ekranını gösterir."""
        if self.current_frame:
            self.current_frame.destroy()
        # LoginScreen'e db_manager'ı aktar
        self.current_frame = LoginScreen(self.root, self)
        self.current_frame.pack(fill="both", expand=True, padx=20, pady=20)

    def show_register_screen(self):
        """Kayıt ekranını gösterir."""
        if self.current_frame:
            self.current_frame.destroy()
        # RegisterScreen'e db_manager'ı aktar
        self.current_frame = RegisterScreen(self.root, self)
        self.current_frame.pack(fill="both", expand=True, padx=20, pady=20)

    # LoginRegisterApp sınıfındaki register_user metodu
    def register_user(self):
        # auth_screens.py'daki RegisterScreen sınıfının bir örneği olan self.current_frame'den
        # kullanıcı adı, şifre ve şifre tekrarı bilgilerini alıyoruz.
        username = self.current_frame.username_entry.get()
        password = self.current_frame.password_entry.get()
        confirm_password = self.current_frame.confirm_password_entry.get()

        if not username or not password or not confirm_password:
            self.show_message("Hata", "Lütfen tüm alanları doldurun.")
            return

        if password != confirm_password:
            self.show_message("Hata", "Şifreler eşleşmiyor.")
            return

        try:
            # KRİTİK DÜZELTME: self.db_manager.insert_user yerine self.db_manager.register_user çağrısı
            # BU SATIR DÜZELTİLDİ! Lütfen bu satırın doğru olduğundan emin ol.
            if self.db_manager.register_user(username, password):
                self.show_message("Başarılı", "Kayıt işlemi başarılı. Giriş yapabilirsiniz.")
                self.show_login_screen()  # Kayıttan sonra giriş ekranına dön
            else:
                self.show_message("Hata", "Kayıt işlemi sırasında hata oluştu. Kullanıcı adı zaten mevcut olabilir.")
        except Exception as e:
            self.show_message("Hata", f"Kayıt işlemi sırasında beklenmeyen bir hata oluştu: {e}")

    def show_message(self, title, message):
        """Mesaj kutusu gösterir."""
        messagebox.showinfo(title, message)

    def start_main_app(self, user_id, username):
        """Ana Gelir Gider Uygulamasını başlatır."""
        if self.current_frame:
            self.current_frame.destroy()
        self.root.title("Gelişmiş Gelir Gider Takibi (Fingo)")
        self.root.geometry("1200x800")
        self.root.resizable(True, True)
        # GelirGiderUygulamasi'na db_manager'ı gönder
        GelirGiderUygulamasi(self.root, self.db_manager, user_id, username)


# --- Ana Başlatma Bloğu ---
if __name__ == "__main__":
    # Yapay zeka özellikleri için scikit-learn ve joblib kütüphanelerinin yüklü olması gerekir.
    # pip install scikit-learn joblib
    root = tk.Tk()
    app = LoginRegisterApp(root)
    root.mainloop()
