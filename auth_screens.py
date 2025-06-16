# auth_screens.py
import tkinter as tk
from tkinter import messagebox

class LoginScreen(tk.Frame):
    def __init__(self, parent, app_controller):
        """
        Giriş ekranı.
        Args:
            parent (tk.Tk): Ana Tkinter penceresi.
            app_controller (LoginRegisterApp): Ana uygulama denetleyicisi.
        """
        super().__init__(parent, bg="#f5f5f5")
        self.app_controller = app_controller

        tk.Label(self, text="Fingo'ya Hoş Geldiniz!", font=("Arial", 16, "bold"), bg="#f5f5f5", fg="#333").pack(pady=20)

        input_frame = tk.Frame(self, bg="#f5f5f5")
        input_frame.pack(pady=10)

        tk.Label(input_frame, text="Kullanıcı Adı:", bg="#f5f5f5", fg="#555").grid(row=0, column=0, pady=5, sticky="w")
        self.username_entry = tk.Entry(input_frame, width=30, font=("Arial", 10), bd=1, relief="solid")
        self.username_entry.grid(row=0, column=1, pady=5, padx=5)

        tk.Label(input_frame, text="Şifre:", bg="#f5f5f5", fg="#555").grid(row=1, column=0, pady=5, sticky="w")
        self.password_entry = tk.Entry(input_frame, show="*", width=30, font=("Arial", 10), bd=1, relief="solid")
        self.password_entry.grid(row=1, column=1, pady=5, padx=5)

        login_button = tk.Button(self, text="Giriş Yap", command=self.login, bg="#4CAF50", fg="white", font=("Arial", 10, "bold"), relief="raised", bd=2)
        login_button.pack(pady=10)

        register_link = tk.Label(self, text="Hesabınız yok mu? Kayıt Olun", fg="#007bff", bg="#f5f5f5", cursor="hand2")
        register_link.pack(pady=5)
        register_link.bind("<Button-1>", lambda e: self.app_controller.show_register_screen())

    def login(self):
        """Giriş işlemini yapar."""
        username = self.username_entry.get()
        password = self.password_entry.get()

        if not username or not password:
            messagebox.showerror("Hata", "Lütfen tüm alanları doldurun.")
            return

        user_id = self.app_controller.db_manager.verify_user(username, password)
        if user_id:
            messagebox.showinfo("Başarılı", "Giriş başarılı!")
            self.app_controller.start_main_app(user_id, username)
        else:
            messagebox.showerror("Hata", "Kullanıcı adı veya şifre hatalı.")


class RegisterScreen(tk.Frame):
    def __init__(self, parent, app_controller):
        """
        Kayıt ekranı.
        Args:
            parent (tk.Tk): Ana Tkinter penceresi.
            app_controller (LoginRegisterApp): Ana uygulama denetleyicisi.
        """
        super().__init__(parent, bg="#f5f5f5")
        self.app_controller = app_controller

        tk.Label(self, text="Yeni Hesap Oluştur", font=("Arial", 16, "bold"), bg="#f5f5f5", fg="#333").pack(pady=20)

        input_frame = tk.Frame(self, bg="#f5f5f5")
        input_frame.pack(pady=10)

        tk.Label(input_frame, text="Kullanıcı Adı:", bg="#f5f5f5", fg="#555").grid(row=0, column=0, pady=5, sticky="w")
        self.username_entry = tk.Entry(input_frame, width=30, font=("Arial", 10), bd=1, relief="solid")
        self.username_entry.grid(row=0, column=1, pady=5, padx=5)

        tk.Label(input_frame, text="Şifre:", bg="#f5f5f5", fg="#555").grid(row=1, column=0, pady=5, sticky="w")
        self.password_entry = tk.Entry(input_frame, show="*", width=30, font=("Arial", 10), bd=1, relief="solid")
        self.password_entry.grid(row=1, column=1, pady=5, padx=5)

        tk.Label(input_frame, text="Şifre Tekrarı:", bg="#f5f5f5", fg="#555").grid(row=2, column=0, pady=5, sticky="w")
        self.confirm_password_entry = tk.Entry(input_frame, show="*", width=30, font=("Arial", 10), bd=1, relief="solid")
        self.confirm_password_entry.grid(row=2, column=1, pady=5, padx=5)

        # Buton doğrudan LoginRegisterApp'teki register_user metodunu çağırıyor
        register_button = tk.Button(self, text="Kayıt Ol", command=self.app_controller.register_user, bg="#007bff", fg="white", font=("Arial", 10, "bold"), relief="raised", bd=2)
        register_button.pack(pady=10)

        login_link = tk.Label(self, text="Zaten hesabınız var mı? Giriş Yapın", fg="#007bff", bg="#f5f5f5", cursor="hand2")
        login_link.pack(pady=5)
        login_link.bind("<Button-1>", lambda e: self.app_controller.show_login_screen())
