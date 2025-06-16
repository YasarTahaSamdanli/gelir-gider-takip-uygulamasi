# auth_screens.py
import tkinter as tk
from tkinter import ttk, messagebox
import time
from datetime import datetime, timedelta

from utils import hash_password_bcrypt, check_password_bcrypt, is_valid_password  # utils'den import


# database_manager'ı LoginRegisterApp'dan alacağız, direkt import etmiyoruz

class LoginScreen(ttk.Frame):
    MAX_LOGIN_ATTEMPTS = 3
    LOCKOUT_DURATION_MINUTES = 5

    def __init__(self, master, app_instance):
        """
        Giriş ekranı arayüzünü ve mantığını oluşturur.
        Args:
            master (tk.Tk): Ana Tkinter penceresi.
            app_instance (LoginRegisterApp): Ana uygulama örneği.
        """
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
        """Kullanıcının giriş denemesini yönetir."""
        username = self.username_entry.get()
        password = self.password_entry.get()

        if not username or not password:
            messagebox.showerror("Hata", "Kullanıcı adı ve şifre boş bırakılamaz.")
            return

        # database_manager üzerinden kullanıcı verisini çek
        user_data = self.app_instance.db_manager.get_user_by_username(username)

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
                # database_manager üzerinden login denemelerini sıfırla
                self.app_instance.db_manager.update_user_login_attempts(user_id, 0, None)
                self.app_instance.start_main_app(user_id, username)
            else:
                login_attempts += 1
                # database_manager üzerinden login denemelerini güncelle
                self.app_instance.db_manager.update_user_login_attempts(user_id, login_attempts)

                if login_attempts >= self.MAX_LOGIN_ATTEMPTS:
                    lockout_time = datetime.now() + timedelta(minutes=self.LOCKOUT_DURATION_MINUTES)
                    # database_manager üzerinden kilitlenme zamanını ayarla
                    self.app_instance.db_manager.update_user_login_attempts(user_id, login_attempts,
                                                                            lockout_time.strftime("%Y-%m-%d %H:%M:%S"))
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
        """
        Kayıt ekranı arayüzünü ve mantığını oluşturur.
        Args:
            master (tk.Tk): Ana Tkinter penceresi.
            app_instance (LoginRegisterApp): Ana uygulama örneği.
        """
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
        """Yeni kullanıcı kaydını yönetir."""
        username = self.username_entry.get()
        password = self.password_entry.get()
        password_confirm = self.password_confirm_entry.get()

        if not username or not password or not password_confirm:
            messagebox.showerror("Hata", "Tüm alanlar doldurulmalıdır.")
            return

        if password != password_confirm:
            messagebox.showerror("Hata", "Şifreler uyuşmuyor.")
            return

        is_valid, msg = is_valid_password(password)
        if not is_valid:
            messagebox.showerror("Hata", msg)
            return

        try:
            # database_manager üzerinden kullanıcı adının varlığını kontrol et
            if self.app_instance.db_manager.get_user_by_username(username):
                messagebox.showerror("Hata", "Bu kullanıcı adı zaten mevcut.")
                return

            hashed_password = hash_password_bcrypt(password)
            # database_manager üzerinden yeni kullanıcı ekle
            self.app_instance.db_manager.insert_user(username, hashed_password)
            messagebox.showinfo("Başarılı", "Kayıt başarıyla tamamlandı. Şimdi giriş yapabilirsiniz.")
            self.app_instance.show_login_screen()
        except Exception as e:  # database_manager'daki hatalar artık daha spesifik yakalanabilir
            messagebox.showerror("Hata", f"Kayıt işlemi sırasında hata oluştu: {e}")

