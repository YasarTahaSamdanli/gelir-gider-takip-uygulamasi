# 💰 Gelir Gider Takip Uygulaması

Bu, **Tkinter** ile geliştirilmiş, **SQLite** veritabanı kullanan kapsamlı bir **gelir-gider takip uygulamasıdır**. Kullanıcıların finansal işlemlerini kolayca **kaydetmesini, filtrelemesini, güncellemesini, silmesini** ve hatta **tekrarlayan gelir/giderleri otomatik olarak yönetmesini** sağlar. Ayrıca **finansal durumu grafiklerle görselleştirme** imkanı sunar.

## 🚀 Özellikler

- ✅ **İşlem Kaydı**: Gelir ve giderleri miktar, kategori, açıklama ve tarih bilgileriyle kaydedin.
- 🔁 **Tekrarlayan İşlemler**: Maaş, kira gibi düzenli işlemleri tanımlayın ve otomatik olarak uygulansın.
- 🔍 **Filtreleme ve Arama**: İşlem türüne, kategoriye veya tarih aralığına göre kayıtları filtreleyin ya da arama yapın.
- ✏️ **İşlem Düzenleme ve Silme**: Mevcut kayıtlar üzerinde değişiklik yapın veya silin.
- 📊 **Finansal Görselleştirme**:
  - Kategorilere göre **pasta grafik**
  - Zaman içindeki **kümülatif bakiye çizgisi**
- 📆 **Takvim Desteği**: Tarih seçimleri için kullanıcı dostu takvim widget’ı.
- 📁 **SQLite Veritabanı**: Verileriniz yerel olarak güvenli bir şekilde saklanır.
- 🧮 **Özet Bilgiler**: Toplam gelir, gider ve güncel bakiyeyi anlık görüntüleyin.

## 🖼️ Ekran Görüntüleri

> ⚠️ Aşağıdaki alanlara ilgili ekran görüntülerini ekleyebilirsiniz:

- Ana arayüz: `images/ana-arayuz.png`
- Gelir/Gider grafikleri: `images/grafikler.png`


## 🛠️ Kullanılan Teknolojiler

- **Python 3.x**
- **Tkinter** – GUI
- **SQLite3** – Veritabanı
- **Matplotlib** – Grafik çizimi
- **tkcalendar** – Takvim widget'ı

## ⚙️ Kurulum ve Çalıştırma

### 📌 Ön Gereksinimler

- Python 3.x yüklü olmalı

### 🔧 Kurulum Adımları

```bash
git clone https://github.com/YasarTahaSamdanli/gelir-gider-takip-uygulamasi.git
cd gelir-gider-takip-uygulamasi
pip install tkinter matplotlib tkcalendar
python main.py
