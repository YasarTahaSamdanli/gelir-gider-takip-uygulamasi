# pdf_generator.py
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.lib.colors import HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os
from datetime import datetime
import json  # Fatura/Teklif kalemlerini JSON'dan okumak için

# Global font adı (main.py'den veya başka yerden erişilebilir olmalı)
GLOBAL_REPORTLAB_FONT_NAME = "ArialCustom"


# Fontu ReportLab'a kaydetme fonksiyonu
def _register_pdf_font(font_path):
    """
    ReportLab için özel bir TrueType fontunu kaydeder.
    Uygulama başlatılırken main.py veya ilgili modül tarafından çağrılmalıdır.
    """
    if not os.path.exists(font_path):
        print(f"Uyarı: Font dosyası bulunamadı: {font_path}. ReportLab'ın varsayılan fontları kullanılacak.")
        return

    try:
        pdfmetrics.registerFont(TTFont(GLOBAL_REPORTLAB_FONT_NAME, font_path))
        print(f"Font '{GLOBAL_REPORTLAB_FONT_NAME}' başarıyla kaydedildi: {font_path}")
    except Exception as e:
        print(f"Hata: ReportLab'a font yüklenirken bir sorun oluştu: {e}")
        print("PDF'de Türkçe karakter sorunları yaşanabilir. Lütfen font dosyasının geçerli olduğundan emin olun.")


class PDFGenerator:
    def __init__(self, db_manager, user_id, font_name=GLOBAL_REPORTLAB_FONT_NAME):
        self.font_name = font_name
        self.db_manager = db_manager
        self.user_id = user_id
        # getSampleStyleSheet() çağrısını bir kere yapıp stil nesnesini al
        self.styles = getSampleStyleSheet()
        self._setup_styles()

    def _setup_styles(self):
        """PDF için özel stilleri ayarlar."""
        # ReportLab'ın varsayılan stil sayfasını kopyala, böylece güvenle değiştirebiliriz
        # ve add metoduyla çakışmayız.
        # Aslında en doğru yöntem, varsayılan stillerin özelliklerini direkt değiştirmektir
        # ve kendi eklediğimiz stilleri add metoduyla eklemektir.

        # Title Style: Varsayılan 'Title' stilini doğrudan güncelliyoruz.
        # Bu, 'KeyError: "Style 'Title' already defined in stylesheet"' hatasını önler.
        if 'Title' in self.styles:
            self.styles['Title'].fontName = self.font_name
            self.styles['Title'].fontSize = 20
            self.styles['Title'].leading = 24
            self.styles['Title'].alignment = TA_CENTER
            self.styles['Title'].spaceAfter = 20
        else:  # Nadiren buraya düşer, ama tanımlı olsun
            self.styles.add(ParagraphStyle(name='Title',
                                           parent=self.styles['h1'] if 'h1' in self.styles else self.styles['Normal'],
                                           fontName=self.font_name,
                                           fontSize=20,
                                           leading=24,
                                           alignment=TA_CENTER,
                                           spaceAfter=20))

        # Ortak bir yardımcı fonksiyon, bir stili ekler veya eğer varsa günceller.
        # Bu, tekrar tekrar if/else yazmaktan kurtarır.
        def add_or_update_custom_style(style_obj):
            if style_obj.name in self.styles:
                # Var olan stili güncelle
                existing_style = self.styles[style_obj.name]
                for attr, value in style_obj.__dict__.items():
                    # 'name' ve '_private' özniteliklerini değiştirmemeye dikkat et
                    if not attr.startswith('_') and attr != 'name':
                        setattr(existing_style, attr, value)
            else:
                # Yeni stili ekle
                self.styles.add(style_obj)

        # Diğer özel stilleri eklerken bu yardımcı fonksiyonu kullan.
        # Heading1 Style
        add_or_update_custom_style(ParagraphStyle(name='Heading1',
                                                  parent=self.styles['h2'] if 'h2' in self.styles else self.styles[
                                                      'Normal'],
                                                  fontName=self.font_name,
                                                  fontSize=14,
                                                  leading=18,
                                                  alignment=TA_LEFT,
                                                  spaceBefore=12,
                                                  spaceAfter=6,
                                                  textColor=HexColor('#0056b3')))

        # BodyText Style
        add_or_update_custom_style(ParagraphStyle(name='BodyText',
                                                  parent=self.styles['Normal'],
                                                  fontName=self.font_name,
                                                  fontSize=10,
                                                  leading=12,
                                                  alignment=TA_LEFT,
                                                  spaceAfter=6))

        # TableHeader Style
        add_or_update_custom_style(ParagraphStyle(name='TableHeader',
                                                  parent=self.styles['Normal'],
                                                  fontName=self.font_name,
                                                  fontSize=9,
                                                  leading=11,
                                                  alignment=TA_CENTER,
                                                  textColor=HexColor('#ffffff'),
                                                  backColor=HexColor('#4CAF50')))

        # TableBody Style
        add_or_update_custom_style(ParagraphStyle(name='TableBody',
                                                  parent=self.styles['Normal'],
                                                  fontName=self.font_name,
                                                  fontSize=9,
                                                  leading=11,
                                                  alignment=TA_LEFT))

        # Totals Style
        add_or_update_custom_style(ParagraphStyle(name='Totals',
                                                  parent=self.styles['Normal'],
                                                  fontName=self.font_name,
                                                  fontSize=11,
                                                  leading=14,
                                                  alignment=TA_RIGHT,
                                                  spaceBefore=10,
                                                  textColor=HexColor('#333333')))

        # GrandTotal Style
        add_or_update_custom_style(ParagraphStyle(name='GrandTotal',
                                                  parent=self.styles['Normal'],
                                                  fontName=self.font_name,
                                                  fontSize=14,
                                                  leading=16,
                                                  alignment=TA_RIGHT,
                                                  spaceBefore=10,
                                                  textColor=HexColor('#0056b3'),
                                                  backColor=HexColor('#e6f2ff'),
                                                  borderPadding=(5, 5, 5, 5)))

        # SmallText Style
        add_or_update_custom_style(ParagraphStyle(name='SmallText',
                                                  parent=self.styles['Normal'],
                                                  fontName=self.font_name,
                                                  fontSize=8,
                                                  leading=9,
                                                  alignment=TA_LEFT,
                                                  textColor=HexColor('#666666')))

    def generate_general_report_pdf(self, report_data, filename="genel_rapor.pdf"):
        """
        Genel gelir-gider raporunu PDF olarak oluşturur.
        report_data: Sözlük formatında rapor verisi.
        Örnek report_data yapısı:
        {
            "title": "Başlık",
            "sections": [
                {"heading": "Bölüm 1 Başlığı", "data": [["Kolon1", "Kolon2"], ["veri1", "veri2"]]},
                {"heading": "Bölüm 2 Başlığı", "data": [["KolonA", "KolonB"], ["veriA", "veriB"]]}
            ]
        }
        """
        doc = SimpleDocTemplate(filename, pagesize=A4, rightMargin=cm, leftMargin=cm, topMargin=cm, bottomMargin=cm)
        story = []

        # Başlık
        story.append(Paragraph(report_data.get("title", "Genel Rapor"), self.styles['Title']))
        story.append(Spacer(1, 0.5 * cm))

        for section in report_data.get("sections", []):
            story.append(Paragraph(section.get("heading", ""), self.styles['Heading1']))
            story.append(Spacer(1, 0.2 * cm))

            data = section.get("data", [])
            if data and len(data) > 0:  # Veri olup olmadığını ve başlık satırı olduğunu kontrol et
                # Tablo oluştur
                table_data = []
                # Başlık satırı
                header_row = [Paragraph(col, self.styles['TableHeader']) for col in data[0]]
                table_data.append(header_row)

                # Veri satırları
                for row_data in data[1:]:
                    table_data.append([Paragraph(str(item), self.styles['TableBody']) for item in row_data])

                # Kolon genişliklerini dinamik olarak ayarla
                if len(data[0]) > 0:
                    col_widths = [doc.width / len(data[0])] * len(data[0])
                else:
                    col_widths = [doc.width]  # Tek sütunlu durum için fallback

                table = Table(table_data, colWidths=col_widths)
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), HexColor('#4CAF50')),  # Başlık satırı yeşil
                    ('TEXTCOLOR', (0, 0), (-1, 0), HexColor('#ffffff')),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('FONTNAME', (0, 0), (-1, 0), self.font_name),
                    ('FONTSIZE', (0, 0), (-1, 0), 9),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                    ('BACKGROUND', (0, 1), (-1, -1), HexColor('#f5f5f5')),  # Veri satırları açık gri
                    ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#cccccc')),  # Izgara çizgileri
                    ('BOX', (0, 0), (-1, -1), 1, HexColor('#cccccc')),
                    ('LEFTPADDING', (0, 0), (-1, -1), 6),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 6),
                    ('TOPPADDING', (0, 0), (-1, -1), 4),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ]))
                story.append(table)
                story.append(Spacer(1, 0.5 * cm))
            else:
                story.append(Paragraph("Gösterilecek veri bulunamadı.", self.styles['BodyText']))
                story.append(Spacer(1, 0.5 * cm))

        # PDF'i oluştur
        try:
            doc.build(story)
            return os.path.abspath(filename)
        except Exception as e:
            raise Exception(f"PDF oluşturma hatası: {e}")

    def generate_document_pdf(self, doc_data):
        """
        Fatura veya Teklif belgesini PDF olarak oluşturur.
        doc_data: fingo_app.py'den gelen sözlük formatında fatura/teklif detayları.
        Örnek doc_data yapısı:
        {
            "doc_type": "Fatura",
            "doc_number": "FTR-2024-00001",
            "customer_name": "Müşteri Adı",
            "doc_date": "2024-06-19",
            "due_valid_date": "2024-07-19",
            "items": [{"ad": "Ürün 1", "miktar": 2, ...}],
            "total_excl_kdv": 100.0,
            "total_kdv": 18.0,
            "notes": "Ek Notlar",
            "status": "Ödendi"
        }
        """
        doc_type = doc_data.get("doc_type", "Belge")
        document_number = doc_data.get("doc_number", "N/A")
        customer_name = doc_data.get("customer_name", "N/A")
        document_date = doc_data.get("doc_date", "N/A")
        due_validity_date = doc_data.get("due_valid_date", "N/A")
        items = doc_data.get("items", [])  # Zaten JSON'dan dönüştürülmüş liste olmalı
        total_excl_kdv = doc_data.get("total_excl_kdv", 0.0)
        total_kdv = doc_data.get("total_kdv", 0.0)
        notes = doc_data.get("notes", "")
        status = doc_data.get("status", "N/A")

        # Müşteri bilgilerini al
        # db_manager'daki get_customer_by_name metodunu kullanarak müşteri bilgilerini al
        customer_info = self.db_manager.get_customer_by_name(customer_name, self.user_id)
        # customer_info bir tuple döneceği için güvenli erişim sağlayalım
        customer_address = customer_info[2] if customer_info and len(customer_info) > 2 and customer_info[
            2] else "Belirtilmemiş"
        customer_phone = customer_info[3] if customer_info and len(customer_info) > 3 and customer_info[
            3] else "Belirtilmemiş"
        customer_email = customer_info[4] if customer_info and len(customer_info) > 4 and customer_info[
            4] else "Belirtilmemiş"

        filename = f"{document_number}_{doc_type}.pdf"
        doc = SimpleDocTemplate(filename, pagesize=A4, rightMargin=1.5 * cm, leftMargin=1.5 * cm, topMargin=1.5 * cm,
                                bottomMargin=1.5 * cm)
        story = []

        # Başlık
        story.append(Paragraph(f"{doc_type.upper()}", self.styles['Title']))
        story.append(Spacer(1, 0.5 * cm))

        # Belge ve Müşteri Bilgileri
        info_data = [
            [Paragraph("Belge Numarası:", self.styles['BodyText']),
             Paragraph(document_number, self.styles['BodyText'])],
            [Paragraph("Belge Tarihi:", self.styles['BodyText']), Paragraph(document_date, self.styles['BodyText'])],
            [Paragraph(f"{doc_type} Durumu:", self.styles['BodyText']), Paragraph(status, self.styles['BodyText'])],
            [Paragraph(f"{'Vade Tarihi:' if doc_type == 'Fatura' else 'Geçerlilik Tarihi:'}", self.styles['BodyText']),
             Paragraph(due_validity_date, self.styles['BodyText'])]
        ]

        customer_data = [
            [Paragraph("Müşteri Adı:", self.styles['BodyText']), Paragraph(customer_name, self.styles['BodyText'])],
            [Paragraph("Adres:", self.styles['BodyText']), Paragraph(customer_address, self.styles['BodyText'])],
            [Paragraph("Telefon:", self.styles['BodyText']), Paragraph(customer_phone, self.styles['BodyText'])],
            [Paragraph("E-posta:", self.styles['BodyText']), Paragraph(customer_email, self.styles['BodyText'])]
        ]

        # Tabloları yan yana koymak için
        header_table_data = [
            [
                Table(info_data, colWidths=[4 * cm, 6 * cm], style=TableStyle([
                    ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                    ('TOPPADDING', (0, 0), (-1, -1), 2), ('BOTTOMPADDING', (0, 0), (-1, -1), 2)
                ])),
                Table(customer_data, colWidths=[4 * cm, 6 * cm], style=TableStyle([
                    ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                    ('TOPPADDING', (0, 0), (-1, -1), 2), ('BOTTOMPADDING', (0, 0), (-1, -1), 2)
                ]))
            ]
        ]
        story.append(Table(header_table_data, colWidths=[doc.width / 2, doc.width / 2]))
        story.append(Spacer(1, 0.5 * cm))

        # Kalemler Tablosu
        story.append(Paragraph("Kalemler", self.styles['Heading1']))
        story.append(Spacer(1, 0.2 * cm))

        table_data = [
            [
                Paragraph("Ürün/Hizmet", self.styles['TableHeader']),
                Paragraph("Miktar", self.styles['TableHeader']),
                Paragraph("Birim Fiyat (₺)", self.styles['TableHeader']),
                Paragraph("KDV %", self.styles['TableHeader']),
                Paragraph("KDV Miktar (₺)", self.styles['TableHeader']),
                Paragraph("Ara Toplam (₺)", self.styles['TableHeader'])
            ]
        ]

        for item in items:
            table_data.append([
                Paragraph(item.get("ad", ""), self.styles['TableBody']),
                Paragraph(str(item.get("miktar", "")), self.styles['TableBody']),
                Paragraph(f"{item.get('birim_fiyat', 0):.2f}", self.styles['TableBody']),
                Paragraph(f"{item.get('kdv_orani', 0):.2f}", self.styles['TableBody']),
                Paragraph(f"{item.get('kdv_miktari', 0):.2f}", self.styles['TableBody']),
                Paragraph(f"{item.get('ara_toplam', 0):.2f}", self.styles['TableBody'])
            ])

        # Kolon genişlikleri orantılı olarak ayarlanabilir
        col_widths = [2.5 * cm, 1.5 * cm, 2 * cm, 1.5 * cm, 2 * cm, 2.5 * cm]
        # Toplam belge genişliğine göre yeniden hesapla
        total_col_width = sum(col_widths)
        col_widths_normalized = [w * (doc.width / total_col_width) for w in col_widths]

        item_table = Table(table_data, colWidths=col_widths_normalized)
        item_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), HexColor('#4CAF50')),
            ('TEXTCOLOR', (0, 0), (-1, 0), HexColor('#ffffff')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 0), (-1, 0), self.font_name),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('BACKGROUND', (0, 1), (-1, -1), HexColor('#f5f5f5')),
            ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#cccccc')),
            ('BOX', (0, 0), (-1, -1), 1, HexColor('#cccccc')),
            ('ALIGN', (1, 1), (1, -1), 'CENTER'),  # Miktar sütunu ortala
            ('ALIGN', (2, 1), (-1, -1), 'RIGHT'),  # Fiyat, KDV sütunlarını sağa hizala
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        story.append(item_table)
        story.append(Spacer(1, 0.5 * cm))

        # Toplamlar
        story.append(Paragraph(f"KDV Hariç Toplam: {total_excl_kdv:.2f} TL", self.styles['Totals']))
        story.append(Paragraph(f"Toplam KDV: {total_kdv:.2f} TL", self.styles['Totals']))
        story.append(Paragraph(f"GENEL TOPLAM: {total_excl_kdv + total_kdv:.2f} TL", self.styles['GrandTotal']))
        story.append(Spacer(1, 0.5 * cm))

        # Notlar
        if notes:
            story.append(Paragraph("Notlar:", self.styles['Heading1']))
            story.append(Paragraph(notes, self.styles['BodyText']))
            story.append(Spacer(1, 0.5 * cm))

        story.append(
            Paragraph(f"Oluşturulma Tarihi: {datetime.now().strftime('%Y-%m-%d %H:%M')}", self.styles['SmallText']))

        try:
            doc.build(story)
            return os.path.abspath(filename)
        except Exception as e:
            raise Exception(f"PDF oluşturma hatası: {e}")

