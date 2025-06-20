# ai_predictor.py
import os
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
from sklearn.exceptions import NotFittedError
from datetime import datetime, timedelta


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

        # Modelin başlatılmasını ve eğitilmesini veya yüklenmesini __init__ yerine
        # ayrı bir metoda taşıdık, böylece UI hazır olduğunda çağrılabilir.
        # self.load_or_train_model() # Bu satır fingo_app.py'ye taşındı

    def load_or_train_model(self, force_retrain=False):
        """
        Kayıtlı modeli veya vektörleyiciyi yükler. Eğer yoksa veya yeniden eğitim istenirse,
        veritabanından verileri çekip modeli eğitir ve kaydeder.
        Args:
            force_retrain (bool): True ise model ve vektörleyici yüklü olsa bile yeniden eğitir.
        """
        if self.model and self.vectorizer and not force_retrain:
            print("Yapay zeka modeli ve vektörleyici zaten yüklü.")
            return

        # Model ve vektörleyiciyi yüklemeyi dene
        if os.path.exists(self.model_path) and os.path.exists(self.vectorizer_path) and not force_retrain:
            try:
                self.model = joblib.load(self.model_path)
                self.vectorizer = joblib.load(self.vectorizer_path)
                print("Kayıtlı yapay zeka modeli ve vektörleyici yüklendi.")
                return
            except Exception as e:
                print(f"Hata: Kayıtlı model veya vektörleyici yüklenirken sorun oluştu: {e}. Yeniden eğitiliyor.")
                self.model = None
                self.vectorizer = None

        # Model yoksa veya yüklenemediyse veya yeniden eğitim isteniyorsa eğit
        print("Kayıtlı model bulunamadı veya yeniden eğitim isteniyor, model eğitiliyor.")
        self._train_model()

    def _train_model(self):
        """
        Veritabanından işlem verilerini çekerek kategorizasyon modelini eğitir.
        """
        # Sadece kategori ve açıklaması olan işlemleri çek
        data = self.db_manager.get_all_transactions_for_ai_training(self.user_id)

        if not data:
            print("UYARI: Yapay zeka modeli eğitimi için veri bulunamadı. Lütfen işlem ekleyin.")
            self.model = None
            self.vectorizer = None
            return

        # En az N (örneğin 10) farklı işlem veya yeterli çeşitlilikte veri olması önerilir
        # Daha iyi bir çeşitlilik kontrolü için benzersiz kategori sayısına bakılabilir.
        descriptions = [item[0] for item in data]
        categories = [item[1] for item in data]

        if len(descriptions) < 10 or len(set(categories)) < 2:
            print(
                "UYARI: Yapay zeka modeli eğitimi için yeterli veya çeşitli veri bulunamadı (en az 10 işlem ve 2 farklı kategori gerekli). Lütfen daha fazla işlem ekleyin.")
            self.model = None
            self.vectorizer = None
            return

        try:
            # Pipeline oluştur: TF-IDF vektörleyici ve Naive Bayes sınıflandırıcı
            self.vectorizer = TfidfVectorizer(max_features=1000)  # En çok geçen 1000 kelimeyi kullan
            self.model = Pipeline([
                ('vectorizer', self.vectorizer),
                ('classifier', MultinomialNB())
            ])

            # Modeli eğit
            self.model.fit(descriptions, categories)

            # Modeli ve vektörleyiciyi kaydet
            joblib.dump(self.model, self.model_path)
            joblib.dump(self.vectorizer, self.vectorizer_path)
            print("Yapay zeka modeli başarıyla eğitildi ve kaydedildi.")
        except Exception as e:
            print(f"Hata: Model eğitilirken veya kaydedilirken bir sorun oluştu: {e}")
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
        if self.model and self.vectorizer:  # Model ve vektörleyici yüklü ve geçerli mi kontrol et
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

    def analyze_and_suggest_savings(self):
        """
        Kullanıcının finansal verilerini analiz eder ve tasarruf önerileri sunar.
        """
        report = []
        report.append("--- Tasarruf Analizi ve Finansal Sağlık Raporu ---\n")

        # 1. Mevcut Bakiye ve Trend
        balance = self.db_manager.get_balance(self.user_id)
        report.append(f"Güncel Bakiye: {balance:.2f} TL\n")

        monthly_trend_data = self.db_manager.get_monthly_balance_trend(self.user_id, num_months=6)  # Son 6 ay
        if monthly_trend_data:
            # Pandas ile işleme
            import pandas as pd
            df = pd.DataFrame(monthly_trend_data, columns=['date', 'type', 'amount'])
            df['date'] = pd.to_datetime(df['date'])
            df.set_index('date', inplace=True)

            # Aylık net bakiyeyi hesapla
            monthly_net = df.groupby(pd.Grouper(freq='M')).apply(
                lambda x: (x[x['type'] == 'Gelir']['amount'].sum() - x[x['type'] == 'Gider']['amount'].sum()))

            # Kümülatif bakiyeyi hesapla (önceki ayları da hesaba katarak)
            # Bu, her ayın sonunda toplam bakiyenin nasıl değiştiğini gösterir.
            all_transactions = self.db_manager.get_transactions(self.user_id)
            if all_transactions:
                df_all = pd.DataFrame(all_transactions,
                                      columns=['id', 'date', 'type', 'amount', 'category', 'description'])
                df_all['date'] = pd.to_datetime(df_all['date'])
                df_all['signed_amount'] = df_all.apply(
                    lambda row: row['amount'] if row['type'] == 'Gelir' else -row['amount'], axis=1)
                df_all = df_all.sort_values('date')
                df_all['cumulative_balance'] = df_all['signed_amount'].cumsum()

                # Aylık kümülatif bakiye trendini daha doğru çekelim
                monthly_cumulative_balance = df_all.set_index('date')['cumulative_balance'].resample(
                    'M').last().ffill().fillna(0)

                if len(monthly_cumulative_balance) > 1:
                    first_month_balance = monthly_cumulative_balance.iloc[0]
                    last_month_balance = monthly_cumulative_balance.iloc[-1]
                    balance_change = last_month_balance - first_month_balance

                    if balance_change > 0:
                        report.append(
                            f"Son {len(monthly_cumulative_balance)} ayda bakiye trendi genel olarak YÜKSELİYOR. ({balance_change:.2f} TL artış)\n")
                    elif balance_change < 0:
                        report.append(
                            f"Son {len(monthly_cumulative_balance)} ayda bakiye trendi genel olarak DÜŞÜYOR. ({abs(balance_change):.2f} TL düşüş)\n")
                    else:
                        report.append(
                            f"Son {len(monthly_cumulative_balance)} ayda bakiye trendi stabil. (Değişim yok)\n")
                else:
                    report.append("Yeterli bakiye trendi verisi bulunamadı (en az 2 aylık işlem gerekli).\n")
            else:
                report.append("Bakiye trendi analizi için işlem verisi bulunamadı.\n")
        else:
            report.append("Bakiye trendi verisi bulunamadı.\n")

        # 2. Gelir ve Gider Analizi (Kategori Bazında)
        report.append("--- Gelir ve Gider Genel Bakışı ---\n")
        income_expense_data = self.db_manager.get_income_expenses_by_month_and_category(self.user_id, num_months=6)

        total_income = sum(item[2] for item in income_expense_data if item[0] == 'Gelir')
        total_expense = sum(item[2] for item in income_expense_data if item[0] == 'Gider')

        report.append(f"Son 6 ayda Toplam Gelir: {total_income:.2f} TL")
        report.append(f"Son 6 ayda Toplam Gider: {total_expense:.2f} TL\n")

        if total_income > 0:
            report.append("Gelir Kategorileri:\n")
            for item in income_expense_data:
                if item[0] == 'Gelir':
                    report.append(f"  - {item[1] if item[1] else 'Belirtilmemiş'}: {item[2]:.2f} TL")
            report.append("\n")

        if total_expense > 0:
            report.append("Gider Kategorileri:\n")
            for item in income_expense_data:
                if item[0] == 'Gider':
                    report.append(f"  - {item[1] if item[1] else 'Belirtilmemiş'}: {item[2]:.2f} TL")
            report.append("\n")

        # 3. Tasarruf Hedefleri Durumu
        report.append("--- Tasarruf Hedefleri Durumu ---\n")
        goals = self.db_manager.get_savings_goals(self.user_id)
        if goals:
            for goal_id, name, target, current, target_date, description, status in goals:
                remaining = target - current
                if remaining <= 0:
                    report.append(f"  - '{name}': Hedef Tamamlandı! ({target:.2f} TL)")
                else:
                    report.append(
                        f"  - '{name}': {current:.2f} / {target:.2f} TL birikti. Kalan: {remaining:.2f} TL. Hedef Tarihi: {target_date}. Durum: {status}")
            report.append("\n")
        else:
            report.append("Tanımlanmış bir tasarruf hedefi bulunmamaktadır.\n")
            report.append("Tasarruf hedefleri belirlemek finansal sağlığınızı iyileştirmenize yardımcı olabilir.")

        # 4. Genel Öneriler
        report.append("--- Genel Tasarruf Önerileri ---\n")
        if balance < 0:
            report.append("- Acilen giderlerinizi gözden geçirin ve gereksiz harcamaları kısın.")
            report.append("- Ek gelir kaynakları arayarak bakiyenizi dengelemeye çalışın.\n")
        elif total_expense > total_income:
            report.append("- Gelirleriniz giderlerinizi karşılamakta zorlanıyor. Detaylı harcama analizi yapın.")
            report.append("- Yüksek gider kategorilerini (örn: yeme-içme, eğlence) belirleyip azaltmaya çalışın.\n")
        elif total_income > total_expense and total_expense > 0:
            report.append("- Düzenli olarak tasarruf hedefleri belirleyin ve bu hedeflere bağlı kalın.")
            report.append("- Gereksiz abonelikleri iptal edin veya daha uygun alternatiflerini bulun.")
            report.append("- Büyük harcamalarınız için önceden bütçe ayırın.\n")
        else:
            report.append("- Finansal durumunuz iyi görünüyor! Mevcut iyi alışkanlıklarınıza devam edin.")
            report.append("- Yatırım seçeneklerini araştırarak birikimlerinizi değerlendirebilirsiniz.")
            report.append("- Acil durum fonunuzun yeterli olduğundan emin olun.\n")

        report.append("Bu rapor bilgilendirme amaçlıdır. Detaylı finansal danışmanlık için bir uzmana başvurun.")

        return "\n".join(report)

