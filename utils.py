# utils.py
import bcrypt
import re

# --- Şifre Hashleme Fonksiyonları ---
def hash_password_bcrypt(password):
    """
    Belirtilen şifreyi bcrypt kullanarak hashler.
    Args:
        password (str): Hashlenecek şifre.
    Returns:
        str: Hashlenmiş şifrenin UTF-8 kodlu dize temsili.
    """
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    return hashed.decode('utf-8')

def check_password_bcrypt(hashed_password_from_db, user_password_input):
    """
    Kullanıcının girdiği şifreyi veritabanındaki hashlenmiş şifreyle karşılaştırır.
    Args:
        hashed_password_from_db (str): Veritabanından alınan hashlenmiş şifre.
        user_password_input (str): Kullanıcının girdiği şifre.
    Returns:
        bool: Şifreler eşleşiyorsa True, aksi takdirde False.
    """
    try:
        return bcrypt.checkpw(user_password_input.encode('utf-8'), hashed_password_from_db.encode('utf-8'))
    except ValueError:
        # Geçersiz hash formatı vb. durumlarda hata yakalama
        return False

def is_valid_password(password):
    """
    Şifrenin karmaşıklık gereksinimlerini kontrol eder.
    Args:
        password (str): Kontrol edilecek şifre.
    Returns:
        tuple: (bool, str) - Şifre geçerliyse (True, ""), aksi takdirde (False, hata_mesajı).
    """
    if len(password) < 8:
        return False, "Şifre en az 8 karakter olmalıdır."
    if not re.search("[a-z]", password):
        return False, "Şifre küçük harf içermelidir."
    if not re.search("[A-Z]", password):
        return False, "Şifre büyük harf içermelidir."
    if not re.search("[0-9]", password):
        return False, "Şifre sayı içermelidir."
    if not re.search("[!@#$%^&*(),.?\":{}|<>]", password):
        return False, "Şifre en az bir özel karakter içermelidir (!@#$%^&* vb.)."
    return True, ""

# --- Yeni Eklenen Fonksiyon ---
def validate_numeric_input(P):
    """Tkinter Entry widget'ları için sayısal giriş doğrulaması yapar."""
    if P.strip() == "":
        return True # Boş girişlere izin ver (silme, temizleme gibi durumlarda)
    try:
        float(P)
        return True
    except ValueError:
        return False
