# FİNGO

Bu uygulama, kullanıcıların gelir ve giderlerini kolayca takip etmelerini, kategorize etmelerini, tekrarlayan işlemleri otomatikleştirmelerini ve mali durumlarını görsel raporlarla analiz etmelerini sağlayan gelişmiş bir finans takip aracıdır.

---

## 🚀 Özellikler

### 🔐 Güvenli Kullanıcı Yönetimi
- Kullanıcı kaydı ve giriş sistemi
- Şifrelerin güvenli `bcrypt` ile hash'lenerek saklanması
- Art arda başarısız giriş denemelerinde hesap kilitleme mekanizması

### 💰 Detaylı Gelir-Gider Takibi
- Gelir ve gider işlemlerini kaydetme, düzenleme ve silme
- İşlemleri tür, kategori, tarih aralığı ve açıklama/arama terimine göre filtreleme
- Gerçek zamanlı toplam gelir, gider ve bakiye özetleri

### 🔁 Tekrarlayan İşlem Yönetimi
- Günlük, haftalık, aylık, yıllık tekrarlayan işlemler tanımlama
- Belirlenen sıklığa göre işlemlerin otomatik olarak eklenmesi

### 🗂️ Kategori Yönetimi
- Gelir ve gider kategorileri oluşturma, düzenleme ve silme
- Yapay zeka ile açıklamalarından yola çıkarak Kategori ekleme :D .

### 📊 Gelişmiş Raporlama ve Görselleştirme
- Kategori bazında pasta grafikleri ile gelir-gider dağılımı
- Zaman içindeki kümülatif bakiye değişimi grafiği
- Excel ve PDF raporları oluşturma

### 🧾 Fatura ve Teklif Yönetimi
- Otomatik belge numarası oluşturma (fatura/teklif)
- KDV oranlı ürün/hizmet ekleme, PDF çıktısı alma

### 👥 Müşteri Yönetimi
- Müşteri bilgilerini (ad, adres, telefon, e-posta) kaydetme ve düzenleme
- Müşteri adı değiştirildiğinde, ilişkili faturalarda otomatik güncelleme

### 📦 Envanter Yönetimi
- Ürün adı, stok miktarı, alış/satış fiyatı ve KDV oranını takip etme
- Faturalara ürün ekledikçe otomatik stok düşümü

### 📑 Vergi Raporları (KDV Odaklı)
- Belirli tarih aralıklarında toplam satış KDV’si hesaplama
- KDV oranlarına göre detaylı dağılım
  
### 💬 Kişisel Finans Koçu (Chatbot) (DAHA YAPILMADI)
- Kullanıcının finansal sorularını yanıtlayan yapay zeka destekli sohbet sistemi

### 📊 Otomatik Bütçe Önerisi (DAHA YAPILMADI)
- Kullanıcının geçmiş harcama verilerini analiz ederek aylık önerilen bütçe dağılımı oluşturur

- Gelirin belirli oranlarını kategori bazlı paylaştırır (örneğin: %30 gıda, %20 kira, %10 eğlence vb.)

- Harcama eğilimlerine göre kişiselleştirilmiş bütçe desteği sunar.

### 🎮 “Ne Alsam?” Danışmanı (DAHA YAPILMADI)
- Kullanıcının belirttiği bütçe ve ilgi alanına göre alışveriş önerileri sunar


---

- **Uygulamadan Ekran Görüntüleri:**

### Giriş Ve Kayıt olma
  ![Giriş](https://github.com/YasarTahaSamdanli/Fingo/blob/dc532b6aec6f852e980eed2401b24d5fdf10d66d/Giri%C5%9F-%C3%87%C4%B1k%C4%B1%C5%9F.png)

### Ana işlemler Sayfası
  ![anaişlemler](https://github.com/YasarTahaSamdanli/Fingo/blob/4cc0b1fe1d164796d0bef7f57800544460713701/anai%C5%9Flemler.png)

### Gelişmiş Araç Ve Rapor Sayfası
  ![gelişmiş](https://github.com/YasarTahaSamdanli/Fingo/blob/4cc0b1fe1d164796d0bef7f57800544460713701/geli%C5%9Fmi%C5%9Fara%C3%A7lar.png)

### Fatura ve Teklif Sayfası
  ![fatura](https://github.com/YasarTahaSamdanli/Fingo/blob/4cc0b1fe1d164796d0bef7f57800544460713701/Fatura-Teklif.png)
---

## ⚙️ Kurulum ve Çalıştırma

### Gereksinimler

`tkinter` (Python ile birlikte gelir)

`sqlite3` (Python ile birlikte gelir)

`matplotlib`

`tkcalendar`

`reportlab`

`scikit-learn`

`joblib`

`pandas` (AI modülü için yardımcı olabilir, manuel kurulum gerekebilir)

`numpy` (scikit-learn bağımlılığı olabilir)

### Bağımlılıkların Yüklenmesi

Projenin bulunduğu dizinde (veya bir sanal ortamda) aşağıdaki komutu çalıştırarak gerekli kütüphaneleri yükleyebilirsiniz:

```bash
pip install matplotlib pandas tkcalendar bcrypt reportlab
Font Kurulumu (PDF Raporları İçin)
PDF raporlarında Türkçe karakterlerin düzgün görünmesi için, Arial.ttf (veya Türkçe karakterleri destekleyen başka bir .ttf fontu) dosyasının main.py ile aynı dizinde bulunması gerekmektedir.

Windows kullanıcıları bu fontu genellikle C:\Windows\Fonts\ dizininden alabilir.
```


## ▶️ Uygulamayı Çalıştırma
Ana Python dosyasını çalıştırmak için terminalde (veya Komut İstemi/Git Bash) şu komutu kullanın:

`python main.py`


## 🗄️Veritabanı
Uygulama, verilerini veriler.db adlı bir SQLite veritabanı dosyasında saklar. Bu dosya, uygulama ilk başlatıldığında otomatik olarak oluşturulur.

📦 PyInstaller ile Uygulamayı Paketleme (EXE Oluşturma)
PyInstaller Kurulumu
`pip install pyinstaller`
Uygulamayı Paketleme
Projenizin ana dizininde aşağıdaki komutu çalıştırın:


`pyinstaller --onefile --windowed --hidden-import=babel.numbers --add-data "Arial.ttf;." --icon=app_icon.ico main.py`
## Parametre Açıklamaları:
--onefile: Tek bir yürütülebilir dosya oluşturur.

--windowed veya -w: Konsol penceresini gizler.

--hidden-import=babel.numbers: tkcalendar için olası eksik bağımlılığı çözer.

--add-data "Arial.ttf;.": Font dosyasını dahil eder. Farklı font kullanıyorsanız güncelleyin.

--icon=app_icon.ico: Uygulama ikonu (ana dizinde olmalı).

main.py: Ana dosya.

Paketlenmiş Uygulamayı Bulma
Oluşturulan .exe dosyası, projenizin kök dizininde yer alan dist klasörü içinde bulunur.

## 🤝 Katkıda Bulunma
Geliştirmelere katkıda bulunmak isterseniz, bir issue açabilir veya pull request gönderebilirsiniz.

