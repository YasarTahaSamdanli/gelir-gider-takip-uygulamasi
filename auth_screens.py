# auth_screens.py
import tkinter as tk
from tkinter import messagebox, ttk
from database_manager import DatabaseManager # DatabaseManager sınıfını import et
from utils import is_valid_password # is_valid_password fonksiyonunu import et

class AuthScreens:
    def __init__(self, root, app_controller):
        self.root = root
        self.app_controller = app_controller
        self.db_manager = app_controller.db_manager # DatabaseManager örneğini app_controller'dan al
        self.root.title("Fingo - Giriş / Kayıt")
        # self.root.geometry("400x350") # Bu satırı main.py'de yönetiyoruz
        # self.root.resizable(False, False) # BU SATIR KALDIRILDI / YORUM SATIRINA ALINDI

        # Style ayarları
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TFrame", background="#f5f5f5")
        style.configure("TLabel", background="#f5f5f5", font=("Arial", 10))
        style.configure("TEntry", font=("Arial", 10))
        # Buton metin rengi artık daha belirgin olması için beyaz olarak ayarlandı
        style.configure("TButton", font=("Arial", 10, "bold"), padding=8, background="#007bff", foreground="white")
        style.map("TButton", background=[('active', '#0056b3')]) # Hover rengi

        self.current_frame = None
        self.show_login_screen()

    def clear_frame(self):
        """Mevcut frame'i temizler."""
        if self.current_frame:
            for widget in self.current_frame.winfo_children():
                widget.destroy()
            self.current_frame.destroy()
            self.current_frame = None

    def show_login_screen(self):
        """Giriş ekranını gösterir."""
        self.clear_frame()
        self.current_frame = ttk.Frame(self.root, padding="20 20 20 20")
        self.current_frame.pack(expand=True, fill='both')

        ttk.Label(self.current_frame, text="Fingo'ya Hoş Geldiniz", font=("Arial", 16, "bold")).pack(pady=10)
        ttk.Label(self.current_frame, text="Giriş Yapın", font=("Arial", 12)).pack(pady=5)

        ttk.Label(self.current_frame, text="Kullanıcı Adı:").pack(pady=5)
        self.login_username_entry = ttk.Entry(self.current_frame)
        self.login_username_entry.pack(pady=2)

        ttk.Label(self.current_frame, text="Şifre:").pack(pady=5)
        self.login_password_entry = ttk.Entry(self.current_frame, show="*")
        self.login_password_entry.pack(pady=2)

        ttk.Button(self.current_frame, text="Giriş Yap", command=self.login).pack(pady=10)
        ttk.Button(self.current_frame, text="Hesabınız Yok Mu? Kayıt Ol", command=self.show_register_screen).pack(pady=5)

    def show_register_screen(self):
        """Kayıt ekranını gösterir."""
        self.clear_frame()
        self.current_frame = ttk.Frame(self.root, padding="20 20 20 20")
        self.current_frame.pack(expand=True, fill='both')

        ttk.Label(self.current_frame, text="Yeni Hesap Oluştur", font=("Arial", 16, "bold")).pack(pady=10)

        ttk.Label(self.current_frame, text="Kullanıcı Adı:").pack(pady=5)
        self.register_username_entry = ttk.Entry(self.current_frame)
        self.register_username_entry.pack(pady=2)

        ttk.Label(self.current_frame, text="Şifre:").pack(pady=5)
        self.register_password_entry = ttk.Entry(self.current_frame, show="*")
        self.register_password_entry.pack(pady=2)

        ttk.Label(self.current_frame, text="Şifre Tekrar:").pack(pady=5)
        self.register_password_confirm_entry = ttk.Entry(self.current_frame, show="*")
        self.register_password_confirm_entry.pack(pady=2)

        ttk.Button(self.current_frame, text="Kayıt Ol", command=self.register).pack(pady=10)
        ttk.Button(self.current_frame, text="Zaten hesabınız var mı? Giriş Yap", command=self.show_login_screen).pack(pady=5)

    def login(self):
        """Kullanıcı girişi işlemini yapar."""
        username = self.login_username_entry.get()
        password = self.login_password_entry.get()

        user_id = self.db_manager.check_user(username, password)
        if user_id:
            messagebox.showinfo("Başarılı", "Giriş başarılı!")
            self.app_controller.start_main_app(user_id, username)
        else:
            messagebox.showerror("Hata", "Kullanıcı adı veya şifre hatalı.")

    def register(self):
        """Yeni kullanıcı kaydı işlemini yapar."""
        username = self.register_username_entry.get()
        password = self.register_password_entry.get()
        password_confirm = self.register_password_confirm_entry.get()

        if not username or not password or not password_confirm:
            messagebox.showerror("Hata", "Lütfen tüm alanları doldurun.")
            return

        if password != password_confirm:
            messagebox.showerror("Hata", "Şifreler uyuşmuyor.")
            return

        # Şifre karmaşıklık kontrolü
        is_valid, error_message = is_valid_password(password)
        if not is_valid:
            messagebox.showerror("Şifre Hatası", error_message)
            return

        # Kullanıcı ekleme işlemi ve olası hata yönetimi
        if self.db_manager.add_user(username, password):
            messagebox.showinfo("Başarılı", "Kayıt işlemi başarılı! Giriş yapabilirsiniz.")
            self.show_login_screen()
        else:
            # add_user metodu IntegrityError'ı yakalayıp False döndürüyor
            messagebox.showerror("Kayıt Hatası", "Kayıt işlemi başarısız. Kullanıcı adı zaten mevcut olabilir.")

