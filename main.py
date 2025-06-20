# main.py
import tkinter as tk
from database_manager import DatabaseManager
from auth_screens import AuthScreens
from fingo_app import GelirGiderUygulamasi
from pdf_generator import _register_pdf_font
import os

# Font dosyasının yolu (Fingo klasörünün içinde olmalı)
FONT_FILE_PATH = "Arial.ttf"  # Eğer farklı bir font kullanacaksan burayı değiştir


class AppController:
    def __init__(self, root):
        self.root = root
        # Ana uygulama penceresinin başlangıç boyutunu ayarla
        self.root.geometry("1024x768")  # Daha büyük bir başlangıç boyutu
        self.root.minsize(800, 600)  # Minimum boyut da belirleyebiliriz
        self.root.resizable(True, True)  # Pencerenin yatay ve dikey olarak boyutlandırılmasına izin ver

        self.db_manager = DatabaseManager()
        self.current_app = None

        _register_pdf_font(FONT_FILE_PATH)

        self.start_auth_screens()

    def start_auth_screens(self):
        """Giriş/Kayıt ekranlarını başlatır."""
        if self.current_app:
            self.current_app.clear_frame()
        self.current_app = AuthScreens(self.root, self)
        # AuthScreens'in kendi içinde root.resizable ayarını kaldırdık,
        # böylece main.py'deki genel ayar geçerli olacak.
        self.root.mainloop()

    def start_main_app(self, user_id, username):
        """Ana uygulamayı (GelirGiderUygulamasi) başlatır."""
        if self.current_app:
            self.current_app.clear_frame()
            self.root.title("Fingo - Gelir Gider Takip")

        self.current_app = GelirGiderUygulamasi(self.root, self.db_manager, user_id, username)
        # Mainloop zaten devam ediyor.
        # GelirGiderUygulamasi içindeki pack/grid ayarları pencerenin kalanını doldurmalı.


if __name__ == "__main__":
    app_root = tk.Tk()
    app = AppController(app_root)
