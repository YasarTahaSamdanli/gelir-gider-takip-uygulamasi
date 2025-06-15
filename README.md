# Gelir Gider Takip Uygulaması

Bu uygulama, kullanıcıların gelir ve giderlerini kolayca takip etmelerini, kategorize etmelerini, tekrarlayan işlemleri otomatikleştirmelerini ve mali durumlarını görsel raporlarla analiz etmelerini sağlayan gelişmiş bir finans takip aracıdır.

---

## 🚀 Özellikler

- **Kullanıcı Girişi ve Kayıt Sistemi:**  
  Güvenli `bcrypt` şifreleme ile kullanıcı hesapları oluşturma ve oturum açma. Yanlış şifre denemelerine karşı hesap kilitleme özelliği.

- **İşlem Takibi:**  
  Gelir ve giderleri miktar, kategori, açıklama ve tarih bilgileriyle kaydetme, güncelleme ve silme.

- **Kategori Yönetimi:**  
  Kullanıcı tanımlı gelir ve gider kategorileri oluşturma, düzenleme ve silme.

- **Tekrarlayan İşlemler:**  
  Düzenli aralıklarla (günlük, haftalık, aylık, yıllık) otomatik olarak oluşturulacak gelir veya gider işlemleri tanımlama.

- **Filtreleme ve Arama:**  
  İşlemleri türe, kategoriye, tarih aralığına ve açıklama/arama terimine göre filtreleme ve arama.

- **Özet Bilgiler:**  
  Toplam gelir, toplam gider ve mevcut bakiyeyi anlık olarak görüntüleme.

- **Grafik Raporlama:**
  - Gelir dağılımını gösteren pasta grafik  
  - Gider dağılımını gösteren pasta grafik  
  - Zaman içindeki kümülatif bakiye değişimini gösteren çizgi grafik

- **Veri Dışa Aktarma:**  
  İşlem verilerini Excel (`.xlsx`) veya PDF (`.pdf`) formatında rapor olarak kaydetme. PDF raporlarında Türkçe karakter desteği.

- **Fatura & Teklifler Sekmesi:**
  Bu yeni sekme, müşterileriniz için profesyonel faturalar ve teklifler oluşturmanızı, yönetmenizi ve PDF olarak dışa aktarmanızı sağlar.


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

- Python 3.x  
- `Tkinter` *(Python ile birlikte gelir, genellikle ek kurulum gerekmez)*  
- `sqlite3` *(Python ile birlikte gelir)*  
- `matplotlib`  
- `pandas`  
- `tkcalendar`  
- `bcrypt`  
- `reportlab`

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

