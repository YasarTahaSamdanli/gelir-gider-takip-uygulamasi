# 💰 Gelir Gider Takip Uygulaması

Bu, Tkinter ile geliştirilmiş, SQLite veritabanı kullanan kapsamlı bir gelir-gider takip uygulamasıdır.  
Kullanıcıların finansal işlemlerini kolayca kaydetmelerini, filtrelemelerini, güncellemelerini, silmelerini ve hatta tekrarlayan gelir/giderlerini otomatik olarak yönetmelerini sağlar. Ayrıca, finansal durumunuzu görselleştirmek için grafikler sunar.

---

## 🚀 Özellikler

- 📥 **İşlem Kaydı:** Gelir ve giderleri miktar, kategori, açıklama ve tarih bilgileriyle kaydetme  
- ✏️ **İşlem Düzenleme/Silme:** Mevcut kayıtları seçip düzenleme veya silme  
- 🔍 **Detaylı Filtreleme & Arama:** İşlem türüne, kategoriye, tarih aralığına veya açıklamaya göre filtreleme  
- 📊 **Özet Bilgiler:** Toplam gelir, gider ve mevcut bakiye bilgileri  
- 🔁 **Tekrarlayan İşlemler Yönetimi:**
  - Düzenli gelir/giderleri bir kez tanımla
  - Günlük, haftalık, aylık, yıllık gibi sıklıklarla otomatik oluşturma
  - Uygulama açılışında otomatik ekleme ve hatırlatıcı

- 📈 **Finansal Görselleştirme:**
  - Kategori bazlı gelir-gider dağılımı (Pasta grafik)
  - Kümülatif bakiye değişimi (Çizgi grafik)

- 🧩 **Kullanıcı Dostu Arayüz:** Modern ve anlaşılır arayüz (Tkinter & ttk)  
- 🗓️ **Takvim Widget'ı:** Kolay tarih seçimi için `tkcalendar`  
- 🗄️ **Dayanıklı Veritabanı:** SQLite ile veriler yerel olarak saklanır  

---

## 🖼️ Ekran Görüntüleri

### Ana Arayüz  
![Ana Arayüz](https://github.com/YasarTahaSamdanli/gelir-gider-takip-uygulamasi/blob/ade8218a6b606473e1cd7dae3279ed66ad784a37/aray%C3%BCz.png)

### Gelir & Gider Grafik Ekranı  
![Grafik Ekranı](https://github.com/YasarTahaSamdanli/gelir-gider-takip-uygulamasi/blob/ade8218a6b606473e1cd7dae3279ed66ad784a37/Grafik.png)

---

## 🛠️ Kullanılan Teknolojiler

- Python 3.x  
- Tkinter (GUI)  
- SQLite3 (Veritabanı)  
- Matplotlib (Grafik çizimi)  
- tkcalendar (Takvim seçimi)

---

## ⚙️ Kurulum ve Çalıştırma

### 🔧 Ön Gereksinimler
- Python 3.x yüklü olmalıdır

### 📥 Kurulum Adımları

```bash
# Depoyu klonla
git clone https://github.com/YasarTahaSamdanli/gelir-gider-takip-uygulamasi.git

# Dizin içine gir
cd gelir-gider-takip-uygulamasi

# Gerekli kütüphaneleri yükle
pip install tkinter
pip install matplotlib
pip install tkcalendar


python main.py
# veya
python gelir_gider_uygulamasi.py

# PyInstaller kur
pip install pyinstaller

# .exe dosyasını oluştur
pyinstaller --onefile --windowed --hidden-import=babel.numbers main.py

