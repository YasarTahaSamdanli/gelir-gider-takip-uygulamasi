# ai_predictor.py
import os
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
from sklearn.exceptions import NotFittedError


class AIPredictor:
    def __init__(self, db_manager, user_id, model_path="category_model.joblib",
                 vectorizer_path="tfidf_vectorizer.joblib"):
        """
        Yapay zeka modelini başlatır. Kayıtlı bir model varsa yükler, yoksa eğitir.
        Args:
            db_manager (DatabaseManager): Veritabanı yöneticisi örneği.
            user_id (int): Mevcut kullanıcının ID'si.
            model_path (str): Eğitilmiş modelin kaydedileceği/yükleneceği dosya yolu.
            vectorizer_path (str): TF-IDF vektörleyicin kaydedileceği/yükleneceği dosya yolu.
        """
        self.model = None
        self.vectorizer = None
        self.model_path = model_path
        self.vectorizer_path = vectorizer_path
        self.db_manager = db_manager  # DatabaseManager örneğini alıyoruz
        self.user_id = user_id

        # Debug çıktısı: Uygulama çalışma dizinini göster
        print(f"DEBUG: AIPredictor başlatıldı. Çalışma dizini: {os.getcwd()}")

        # Modelin başlatılmasını ve eğitilmesini veya yüklenmesini yönet
        self._load_or_retrain_model_with_user_data()

    def _load_or_retrain_model_with_user_data(self):
        """
        Kayıtlı modeli ve vektörleyiciyi yükler veya kullanıcı verisiyle yeniden eğitir.
        """
        descriptions = []
        categories = []

        # Kullanıcının kendi işlemlerini veritabanından çek
        user_transactions = self.db_manager.get_all_transaction_descriptions_and_categories(self.user_id)
        if user_transactions:
            for desc, cat in user_transactions:
                # Boş veya NULL değerleri atla (Bu satır önemli, veri tutarsızlığını engellemeli)
                if desc is not None and cat is not None and str(desc).strip() != '' and str(cat).strip() != '':
                    descriptions.append(str(desc).strip())
                    categories.append(str(cat).strip())


        # Eğer kullanıcının kendi verisi yoksa veya çok azsa, sentetik veriyle başla
        if len(descriptions) < 10:  # Minimum eğitim verisi eşiği
            print("Yeterli kullanıcı verisi bulunamadı, sentetik veriyle ilk eğitim yapılıyor.")
            synthetic_descriptions, synthetic_categories = self._get_synthetic_data()
            descriptions.extend(synthetic_descriptions)
            categories.extend(synthetic_categories)
        else:
            print("Yeterli kullanıcı verisi bulundu, model kullanıcı verisiyle eğitiliyor.")

        # Model dosyaları mevcut mu kontrol et
        if os.path.exists(self.model_path) and os.path.exists(self.vectorizer_path):
            try:
                # Mevcut modeli yüklemeye çalış
                loaded_pipeline = joblib.load(self.model_path)
                self.vectorizer = joblib.load(self.vectorizer_path)
                self.model = loaded_pipeline  # Yüklenen pipeline'ı doğrudan model olarak kullan
                print("Yapay zeka modeli ve vektörleyici başarıyla yüklendi.")

                # Yüklenen modeli yeni veya güncel verilerle yeniden eğit (incremental fit yerine full fit)
                if descriptions and categories:
                    print("Yüklenen model, yeni/güncel kullanıcı verisiyle yeniden eğitiliyor...")
                    self.retrain_model(descriptions, categories)

            except Exception as e:
                # Model yüklenirken bir hata olursa, hata mesajını yazdır ve yeniden eğitmeyi dene
                print(
                    f"Hata: Yapay zeka modeli yüklenirken bir sorun oluştu ({e}). Kullanıcı verisiyle yeniden eğitiliyor...")
                if descriptions and categories:
                    self.retrain_model(descriptions, categories)
                else:
                    print("Yeterli veri olmadığı için model eğitilemedi.")
        else:
            # Model dosyaları bulunamazsa, ilk eğitimi yap
            print("Yapay zeka modeli bulunamadı. Kullanıcı verisiyle ilk eğitim yapılıyor...")
            if descriptions and categories:
                self.retrain_model(descriptions, categories)
            else:
                print("Yeterli veri olmadığı için model eğitilemedi.")

    def _get_synthetic_data(self):
        """
        Detaylı sentetik veri setini döndürür. Bu veri seti, modelin daha geniş bir yelpazede
        kategorileri tanımasına yardımcı olmak için çeşitli açıklamalardan oluşur.
        Bu kısım senin için çalışan genişletilmiş sentetik veri setidir.
        """
        descriptions = [
            # Market Gideri (21)
            "Market", "Gıda harcaması A101", "Süpermarket",
            "Şok market", "Marketten günlük ihtiyaçlar",
            "Yerel manavdan taze sebze meyve", "Kasaptan et alımı",
            "Ekmek, süt, yumurta alışverişi", "Haftalık market alışverişi",
            "Atıştırmalık ve içecek alımı", "Ev için temizlik malzemeleri",
            "Bebek maması ve bezi", "Evcil hayvan maması ve kumu",
            "Online market siparişi", "Groseri'den alışveriş",
            "Yerel bakkaldan sigara ve gazete", "Kahvaltılık ürünler",
            "Deterjan ve sabun alımı", "Şarküteri ürünleri",
            "Meyve suyu ve soda", "Temel gıda maddeleri",

            # Fatura Gideri (20)
            "Fatura", "Su faturası", "Doğalgaz faturası",
            "Telefon faturası", "İnternet faturası",
            "Elektirik faturası", "Netflix aboneliği", "Su aboneliği",
            "Elektrik dağıtım bedeli", "Isınma gideri",
            "Aidat ödemesi (apartman)", "Kira ödemesi", "İGDAŞ fatura",
            "TurkNet internet faturası", "Vergi ödemesi MTV",
            "Belediye çöp vergisi", "Emlak vergisi taksiti",
            "Kredi kartı dönem borcu ödemesi (faiz hariç)",
            "Bireysel emeklilik katkı payı", "Sağlık sigortası primi",

            # Yemek Gideri (20)
            "Restoran yemeği", "Dışarıda yemek", "Cafe masrafı",
            "Pizza siparişi", "Kebapçı hesabı", "Fast food menü",
            "Öğle yemeği işyerinde", "Akşam yemeği dışarıda",
            "Kahve ve pasta", "Burger King menü", "Starbucks kahve",
            "Lokantada hesap", "Ev yemeği siparişi",
            "Çiğ köfte alımı", "Çay bahçesi oturumu",
            "Pastane tatlıları", "Dondurma alımı", "Büfeden sandviç",
            "Yemek", "Dürüm döner",

            # Maaş Geliri (14)
            "Maaş ödemesi", "Aylık kazanç", "Sabit gelir",
            "Şirket maaşı", "Ay sonu ödemesi", "Prim ödemesi",
            "İkramiye", "Fazla mesai ücreti", "Nakit maaş",
            "Banka hesabına maaş yatırma", "Girişimden gelir",
            "Emekli maaşı", "Devletten yardım", "Burs ödemesi",

            # Freelance Gelir (14)
            "Serbest çalışma geliri", "Danışmanlık ücreti", "Proje bazlı ödeme",
            "Grafik tasarım işi", "Yazılım geliştirme geliri",
            "Çeviri hizmeti karşılığı", "Web sitesi tasarımı",
            "Sosyal medya yönetimi ödemesi", "Makale yazım ücreti",
            "Eğitmenlik geliri", "Online ders ücreti", "Fotoğraf çekimi",
            "Kripto para kazancı", "Hisse senedi satış karı",

            # Araç Gideri (18)
            "Benzin istasyonu", "Akaryakıt alımı", "Araç Gideri",
            "Oto yıkama", "Lastik değişimi", "Motor yağı",
            "Muayene ücreti", "Kasko ödemesi", "Trafik sigortası",
            "Tamirci masrafı", "Yedek parça alımı", "Otoyol ücreti",
            "Köprü geçişi", "Park ücreti", "Araba kiralama",
            "Motorin alımı", "LPG dolumu", "Araç bakım",

            # Kira (Ev & İş Yeri & Gelir) (6)
            "Kira ödemesi", "Ev kirası", "Dükkan kirası",
            "Depo kirası", "Kira geliri", "Mülk kirası",

            # Alışveriş Gideri (19)
            "Online alışveriş Trendyol", "Giyim alışverişi", "Kitap alımı",
            "Elektronik eşya", "Ayakkabı alımı", "Çanta",
            "Kozmetik ürünler", "Mobilya", "Beyaz eşya",
            "Hobi malzemeleri", "Spor malzemeleri", "Telefon aksesuarları",
            "Market dışı genel alışveriş", "Amazon siparişi",
            "Hepsiburada'dan ürün", "Zara'dan giysi", "Bershka alışverişi",
            "Decathlon'dan spor ayakkabı", "Teknosa'dan laptop",

            # Ulaşım Gideri (15)
            "Ulaşım otobüs bileti", "Taksi ücreti", "Otobüs kartı dolumu",
            "Metro kartı yükleme", "Tren bileti", "Uçak bileti",
            "Servis ücreti", "Dolmuş parası", "Deniz taksi",
            "Vapur bileti", "Toplu taşıma kartı", "Özel şoför",
            "Araç paylaşım servisi", "Bisiklet tamiri", "Scooter kiralama",

            # Eğlence/Spor (20)
            "Spor salonu üyeliği", "Fitness aboneliği", "Sinema bileti",
            "Konser bileti", "Tiyatro gösterisi", "Maç bileti",
            "Hafta sonu gezisi", "Tatil harcaması", "Oyun alımı (Steam)",
            "Kitap okuma etkinliği", "Hobi kursu", "Yüzme dersi",
            "Dans kursu", "Müze girişi", "Sergi gezisi",
            "Hayvanat bahçesi ziyareti", "Lunapark bileti", "Bilgisayar oyunu",
            "Bowling oynama", "Paintball etkinliği",

            # Eğitim Gideri (12)
            "Üniversite harcı", "Dershane ücreti", "Kitap ve kırtasiye",
            "Online eğitim kursu", "Özel ders", "Yabancı dil kursu",
            "Seminer katılım ücreti", "Workshop ücreti", "Eğitim materyalleri",
            "Okul servisi", "Kreş ücreti", "Anaokulu ödemesi",

            # Sağlık Gideri (14)
            "Doktor muayene ücreti", "İlaç alımı", "Eczane masrafı",
            "Diş hekimi", "Optik gözlük alımı", "Fizik tedavi",
            "Hastane faturası", "Tıbbi testler", "Vitamin takviyeleri",
            "Diyetisyen ücreti", "Psikolog seansı", "Termal tesis",
            "Ameliyat masrafı", "Tıbbi sarf malzeme",

            # Diğer Giderler (29)
            "Hediyelik eşya", "Bağış", "Yardım",
            "Kuru temizleme", "Terzi masrafı", "Kuaför",
            "Berber", "Telefon hattı yükleme", "Vergi (ek)",
            "Borç ödemesi", "Çeyiz hesabı", "Çocuk harçlığı",
            "Bahçe bakımı", "Ev tadilatı", "Tamirci",
            "Sigara alımı", "Alkollü içecekler", "Oyun borcu",
            "Kumar", "Şans oyunu", "Hayır kurumu bağışı",
            "Dernek aidatı", "Cami yardımı", "Doğum günü hediyesi",
            "Yıldönümü hediyesi", "Hızlı para çekimi", "Komisyon ücreti",
            "Banka işlem ücreti", "Kargo ücreti", "Servis bedeli",
            "Özel ders ücreti", "Hukuk danışmanlığı", "Mali müşavir ücreti"
        ]

        categories = [
            "Market Gideri", "Market Gideri", "Market Gideri",
            "Market Gideri", "Market Gideri", "Market Gideri",
            "Market Gideri", "Market Gideri", "Market Gideri",
            "Market Gideri", "Market Gideri", "Market Gideri",
            "Evcil Hayvan Gideri", "Market Gideri", "Market Gideri",
            "Market Gideri", "Market Gideri", "Market Gideri",
            "Market Gideri", "Market Gideri", "Market Gideri",

            "Fatura Gideri", "Fatura Gideri", "Fatura Gideri",
            "Fatura Gideri", "Fatura Gideri", "Fatura Gideri",
            "Fatura Gideri", "Fatura Gideri", "Fatura Gideri",
            "Fatura Gideri", "Ev Kirası", "İş Yeri Kirası", # "Kira ödemesi" ve "Ev kirası" Ev Kirası, "Aidat ödemesi" Fatura Gideri, "Dükkan kirası" İş Yeri Kirası olmalıydı, düzeltildi
            "İş Yeri Kirası", "Kira Geliri", "Diğer Gelir", # "Kira geliri" ve "Mülk kirası" Diğer Gelir olarak işaretlendi
            "Vergi Gideri",
            "Vergi Gideri", "Vergi Gideri", "Finansal Gider",
            "Finansal Gider", "Sağlık Gideri",

            "Yemek Gideri", "Yemek Gideri", "Yemek Gideri",
            "Yemek Gideri", "Yemek Gideri", "Yemek Gideri",
            "Yemek Gideri", "Yemek Gideri", "Yemek Gideri",
            "Yemek Gideri", "Yemek Gideri", "Yemek Gideri",
            "Yemek Gideri", "Yemek Gideri", "Yemek Gideri",
            "Yemek Gideri", "Yemek Gideri", "Yemek Gideri",
            "Yemek Gideri", "Yemek Gideri",

            "Maaş Geliri", "Maaş Geliri", "Maaş Geliri",
            "Maaş Geliri", "Maaş Geliri", "Maaş Geliri",
            "Maaş Geliri", "Maaş Geliri", "Maaş Geliri",
            "Maaş Geliri", "Maaş Geliri", "Maaş Geliri",
            "Diğer Gelir", "Diğer Gelir",

            "Freelance Gelir", "Freelance Gelir", "Freelance Gelir",
            "Freelance Gelir", "Freelance Gelir",
            "Freelance Gelir", "Freelance Gelir",
            "Freelance Gelir", "Freelance Gelir",
            "Eğitim Geliri", "Eğitim Geliri", "Freelance Gelir",
            "Yatırım Geliri", "Yatırım Geliri",

            "Araç Gideri", "Araç Gideri", "Araç Gideri",
            "Araç Gideri", "Araç Gideri", "Araç Gideri",
            "Araç Gideri", "Araç Gideri", "Araç Gideri",
            "Araç Gideri", "Araç Gideri", "Ulaşım Gideri",
            "Ulaşım Gideri", "Ulaşım Gideri", "Ulaşım Gideri",
            "Araç Gideri", "Araç Gideri", "Araç Gideri",

            "Ev Kirası", "Ev Kirası", "İş Yeri Kirası",
            "İş Yeri Kirası", "Kira Geliri", "Diğer Gelir",

            "Alışveriş Gideri", "Alışveriş Gideri", "Alışveriş Gideri",
            "Alışveriş Gideri", "Alışveriş Gideri", "Alışveriş Gideri",
            "Alışveriş Gideri", "Alışveriş Gideri", "Alışveriş Gideri",
            "Alışveriş Gideri", "Alışveriş Gideri", "Alışveriş Gideri",
            "Alışveriş Gideri", "Alışveriş Gideri",
            "Alışveriş Gideri", "Alışveriş Gideri", "Alışveriş Gideri",
            "Alışveriş Gideri", "Alışveriş Gideri",

            "Ulaşım Gideri", "Ulaşım Gideri", "Ulaşım Gideri",
            "Ulaşım Gideri", "Ulaşım Gideri", "Ulaşım Gideri",
            "Ulaşım Gideri", "Ulaşım Gideri", "Ulaşım Gideri",
            "Ulaşım Gideri", "Ulaşım Gideri", "Ulaşım Gideri",
            "Ulaşım Gideri", "Ulaşım Gideri", "Ulaşım Gideri",

            "Eğlence/Spor", "Eğlence/Spor", "Eğlence/Spor",
            "Eğlence/Spor", "Eğlence/Spor", "Eğlence/Spor",
            "Eğlence/Spor", "Eğlence/Spor", "Eğlence/Spor",
            "Eğlence/Spor", "Eğlence/Spor", "Eğlence/Spor",
            "Eğlence/Spor", "Eğlence/Spor", "Eğlence/Spor",
            "Eğlence/Spor", "Eğlence/Spor", "Eğlence/Spor",
            "Eğlence/Spor", "Eğlence/Spor",

            "Eğitim Gideri", "Eğitim Gideri", "Eğitim Gideri",
            "Eğitim Gideri", "Eğitim Gideri", "Eğitim Gideri",
            "Eğitim Gideri", "Eğitim Gideri", "Eğitim Gideri",
            "Ulaşım Gideri", "Eğitim Gideri", "Eğitim Gideri",

            "Sağlık Gideri", "Sağlık Gideri", "Sağlık Gideri",
            "Sağlık Gideri", "Sağlık Gideri", "Sağlık Gideri",
            "Sağlık Gideri", "Sağlık Gideri", "Sağlık Gideri",
            "Sağlık Gideri", "Sağlık Gideri", "Sağlık Gideri",
            "Sağlık Gideri", "Sağlık Gideri",

            "Diğer Giderler", "Bağış", "Bağış",
            "Diğer Giderler", "Diğer Giderler", "Kişisel Bakım",
            "Kişisel Bakım", "Fatura Gideri", "Vergi Gideri",
            "Borç Ödemesi", "Birikim", "Çocuk Bakım",
            "Ev Bakım Gideri", "Ev Bakım Gideri", "Ev Bakım Gideri",
            "Diğer Giderler", "Diğer Giderler", "Eğlence/Spor",
            "Eğlence/Spor", "Eğlence/Spor", "Bağış",
            "Diğer Giderler", "Bağış", "Hediye",
            "Hediye", "Banka Gideri", "Banka Gideri",
            "Kargo Gideri", "Diğer Giderler",
            "Eğitim Gideri", "Danışmanlık Gideri", "Danışmanlık Gideri"
        ]
        return descriptions, categories


    def retrain_model(self, descriptions, categories):
        """
        Modeli verilen yeni verilerle eğitir ve kaydeder.
        Args:
            descriptions (list): Eğitim için açıklama metinleri listesi.
            categories (list): Açıklamalara karşılık gelen kategoriler listesi.
        """
        if not descriptions or not categories:
            print("Uyarı: Model eğitimi için yeterli veri yok. Eğitim atlandı.")
            return

        # Çok kritik: desc ve cat listelerinin uzunlukları burada hala farklıysa, model.fit hata verir.
        # Bu problem genellikle descriptions veya categories listelerinden birinin boş kalmasından
        # veya içindeki öğe sayısının diğerinden farklı olmasından kaynaklanır.
        # Bu versiyonda `_load_or_retrain_model_with_user_data` içinde bu filtreleniyor olmalı.
        if len(descriptions) != len(categories):
            print(f"HATA: retrain_model'e gelen veri setinde tutarsızlık! Açıklamalar: {len(descriptions)}, Kategoriler: {len(categories)}")
            print("Model eğitimi iptal edildi çünkü açıklama ve kategori sayıları uyuşmuyor.")
            # Hata durumunda modelin atanmadığından emin ol
            self.model = None
            self.vectorizer = None
            return # Eğitimi durdur

        print(f"BİLGİ: Model {len(descriptions)} açıklama ile eğitiliyor...")
        self.vectorizer = TfidfVectorizer(max_features=1000) # Özellik sayısını biraz artırdım
        self.model = Pipeline([
            ('vect', self.vectorizer),
            ('clf', MultinomialNB()),
        ])

        try:
            self.model.fit(descriptions, categories)
            joblib.dump(self.model, self.model_path)
            joblib.dump(self.vectorizer, self.vectorizer_path)
            print("Yapay zeka modeli yeni verilerle eğitildi ve kaydedildi.")
        except Exception as e:
            # Buradaki hata yakalama, joblib.dump'tan değil, daha çok model.fit'ten kaynaklanmalı.
            print(f"Hata: Model eğitilirken veya kaydedilirken bir sorun oluştu: {e}")
            # Hata durumunda modelin atanmadığından emin ol
            self.model = None
            self.vectorizer = None


    def predict_category(self, description):
        """
        Verilen açıklama için kategori tahmini yapar.
        Args:
            description (str): İşlem açıklaması.
        Returns:
            str or None: Tahmin edilen kategori adı veya model eğitilmemişse None.
        """
        if self.model and self.vectorizer: # Model ve vektörleyici yüklü ve geçerli mi kontrol et
            try:
                # model zaten bir Pipeline, bu yüzden doğrudan predict çağrılabilir.
                predicted_category = self.model.predict([description])[0]
                return predicted_category
            except NotFittedError:
                print("UYARI: Model eğitilmemiş, tahmin yapılamıyor (NotFittedError).")
                return None
            except Exception as e:
                print(f"Hata: Kategori tahmini yapılırken sorun oluştu: {e}")
                return None
        else:
            print(
                "UYARI: Yapay zeka modeli başlatılamadı veya eğitilmediği için tahmin yapılamıyor. Model veya vektörleyici eksik/bozuk.")
            return None

