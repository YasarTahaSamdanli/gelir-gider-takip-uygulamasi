# pdf_generator.py
import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import json
import os
import sys
from datetime import datetime

# --- Global Font Tanımlamaları ---
# Bu değişken main.py tarafından doldurulacak.
GLOBAL_FONT_PATH_FOR_PDF = None
GLOBAL_REPORTLAB_FONT_NAME = "Arial"  # ReportLab'da kullanacağımız font adı


def _register_pdf_font(font_path):
    """ReportLab'a fontu kaydeder."""
    global GLOBAL_REPORTLAB_FONT_NAME
    try:
        if os.path.exists(font_path):
            if not pdfmetrics.isFontRegistered(GLOBAL_REPORTLAB_FONT_NAME):
                pdfmetrics.registerFont(TTFont(GLOBAL_REPORTLAB_FONT_NAME, font_path))
                pdfmetrics.registerFont(TTFont(GLOBAL_REPORTLAB_FONT_NAME + "-Bold", font_path))
                pdfmetrics.registerFontFamily(GLOBAL_REPORTLAB_FONT_NAME,
                                              normal=GLOBAL_REPORTLAB_FONT_NAME,
                                              bold=GLOBAL_REPORTLAB_FONT_NAME + "-Bold",
                                              italic=GLOBAL_REPORTLAB_FONT_NAME,
                                              boldItalic=GLOBAL_REPORTLAB_FONT_NAME + "-Bold")
                print(f"Font '{GLOBAL_REPORTLAB_FONT_NAME}' başarıyla yüklendi: {font_path}")
        else:
            print(f"Uyarı: Font dosyası bulunamadı: {font_path}. PDF'de Türkçe karakter sorunları olabilir.")
            GLOBAL_REPORTLAB_FONT_NAME = "Helvetica"  # Fallback font
    except Exception as e:
        print(f"Hata: ReportLab'a font yüklenirken bir sorun oluştu: {e}. PDF'de Türkçe karakter sorunları olabilir.")
        GLOBAL_REPORTLAB_FONT_NAME = "Helvetica"  # Fallback font


class PDFGenerator:
    def __init__(self, font_name=GLOBAL_REPORTLAB_FONT_NAME):
        """
        PDF oluşturma yardımcı sınıfı.
        Args:
            font_name (str): PDF'lerde kullanılacak font adı (ReportLab tarafından kayıtlı olmalı).
        """
        self.font_name = font_name
        self.styles = getSampleStyleSheet()
        self._setup_styles()

    def _setup_styles(self):
        """PDF metin stillerini ayarlar."""
        self.title_style = ParagraphStyle(
            'TitleStyle',
            parent=self.styles['h1'],
            fontName=self.font_name,
            fontSize=20,
            spaceAfter=14,
            alignment=TA_CENTER
        )
        self.heading_style = ParagraphStyle(
            'HeadingStyle',
            parent=self.styles['h2'],
            fontName=self.font_name,
            fontSize=14,
            spaceAfter=10,
            alignment=TA_CENTER
        )
        self.sub_heading_style = ParagraphStyle(
            'SubHeadingStyle',
            parent=self.styles['h3'],
            fontName=self.font_name,
            fontSize=12,
            spaceAfter=8,
            alignment=TA_LEFT
        )
        self.normal_style = ParagraphStyle(
            'NormalStyle',
            parent=self.styles['Normal'],
            fontName=self.font_name,
            fontSize=10,
            leading=12
        )
        self.bold_style = ParagraphStyle(
            'BoldStyle',
            parent=self.normal_style,
            fontName=self.font_name + '-Bold' if self.font_name != "Helvetica" else "Helvetica-Bold",
            fontSize=10,
            leading=12,
        )

    def generate_excel_report(self, data, file_path):
        """
        Verilen veriden bir Excel raporu oluşturur ve belirtilen yola kaydeder.
        Args:
            data (list): İşlem verilerini içeren liste.
            file_path (str): Raporun kaydedileceği dosya yolu.
        """
        if not data:
            raise ValueError("Excel raporu oluşturulacak veri bulunamadı.")

        df = pd.DataFrame(data, columns=["ID", "Tür", "Miktar", "Kategori", "Açıklama", "Tarih"])
        df.to_excel(file_path, index=False)

    def generate_pdf_report(self, data, file_path, username, filter_info):
        """
        Verilen veriden bir PDF raporu oluşturur ve belirtilen yola kaydeder.
        Args:
            data (list): İşlem verilerini içeren liste.
            file_path (str): Raporun kaydedileceği dosya yolu.
            username (str): Raporu oluşturan kullanıcının adı.
            filter_info (dict): Rapor filtreleme bilgilerini içeren sözlük (örn. tür, kategori, tarih aralığı).
        """
        if not data:
            raise ValueError("PDF raporu oluşturulacak veri bulunamadı.")

        doc = SimpleDocTemplate(file_path, pagesize=letter)
        elements = []

        elements.append(Paragraph("Gelir-Gider Uygulaması Raporu", self.title_style))
        elements.append(Spacer(1, 0.2 * 10 * 6))

        filtre_bilgisi = f"<b>Rapor Tarihi:</b> {datetime.now().strftime('%Y-%m-%d %H:%M')}<br/>" \
                         f"<b>Kullanıcı:</b> {username}<br/>" \
                         f"<b>Filtreler:</b> Tür: {filter_info['tur']}, Kategori: {filter_info['kategori']}<br/>" \
                         f"Tarih Aralığı: {filter_info['bas_tarih']} - {filter_info['bit_tarih']}<br/>" \
                         f"Arama Terimi: {filter_info['arama_terimi'] or 'Yok'}"
        elements.append(Paragraph(filtre_bilgisi, self.normal_style))
        elements.append(Spacer(1, 0.2 * 10 * 6))

        table_data = [["ID", "Tür", "Miktar (₺)", "Kategori", "Açıklama", "Tarih"]]
        total_gelir = 0
        total_gider = 0

        for row in data:
            table_data.append([
                Paragraph(str(row[0]), self.normal_style),
                Paragraph(row[1], self.normal_style),
                Paragraph(f"{row[2]:,.2f}".replace(".", ","), self.normal_style),
                Paragraph(row[3] if row[3] else '', self.normal_style),
                Paragraph(row[4] if row[4] else '', self.normal_style),
                Paragraph(row[5], self.normal_style)
            ])
            if row[1] == "Gelir":
                total_gelir += row[2]
            else:
                total_gider += row[2]

        table_style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#D0D0D0")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 0), (-1, 0), self.font_name),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor("#F5F5F5")),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('FONTNAME', (0, 1), (-1, -1), self.font_name),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
        ])

        col_widths = [0.05 * letter[0], 0.08 * letter[0], 0.12 * letter[0], 0.15 * letter[0], 0.45 * letter[0],
                      0.15 * letter[0]]

        table_style.add('ALIGN', (2, 0), (2, -1), 'RIGHT')

        table = Table(table_data, colWidths=col_widths)
        table.setStyle(table_style)
        elements.append(table)
        elements.append(Spacer(1, 0.2 * 10 * 6))

        elements.append(
            Paragraph(f"<b>Toplam Gelir:</b> <font color='green'>₺{total_gelir:,.2f}</font>", self.normal_style))
        elements.append(
            Paragraph(f"<b>Toplam Gider:</b> <font color='red'>₺{total_gider:,.2f}</font>", self.normal_style))
        elements.append(
            Paragraph(f"<b>Bakiye:</b> <font color='blue'>₺{total_gelir - total_gider:,.2f}</font>", self.normal_style))

        doc.build(elements)

    def generate_invoice_offer_pdf(self, invoice_data, customer_info, file_path):
        """
        Fatura veya teklif için PDF belgesi oluşturur.
        Args:
            invoice_data (tuple): Fatura/teklif verisi (DB'den çekilen tüm 12 sütun).
            customer_info (tuple): Müşteri bilgileri (adres, telefon, email).
            file_path (str): PDF'in kaydedileceği yol.
        """
        if not invoice_data:
            raise ValueError("Fatura/Teklif verisi bulunamadı.")

        # Burası güncellendi: Artık database_manager'dan 12 değer bekliyoruz.
        (id, tur, belge_numarasi, musteri_adi, belge_tarihi_str, son_odeme_gecerlilik_tarihi_str, urun_hizmetler_json,
         toplam_tutar_kdv_haric, toplam_kdv, notlar, durum, kullanici_id) = invoice_data
        genel_toplam = toplam_tutar_kdv_haric + toplam_kdv

        musteri_adres = customer_info[0] if customer_info and len(customer_info) > 0 else "Belirtilmemiş"
        musteri_telefon = customer_info[1] if customer_info and len(customer_info) > 1 else "Belirtilmemiş"
        musteri_email = customer_info[2] if customer_info and len(customer_info) > 2 else "Belirtilmemiş"

        doc = SimpleDocTemplate(file_path, pagesize=letter)
        elements = []

        elements.append(Paragraph(f"{tur} / Teklif Belgesi", self.heading_style))
        elements.append(Spacer(1, 0.2 * 10 * 6))

        # 2. Şirket Bilgileri (Sabit Metin)
        elements.append(Paragraph("<b>Şirket Adı:</b> ABC Finansal Hizmetler", self.normal_style))
        elements.append(
            Paragraph("<b>Adres:</b> Örnek Mahallesi, Deneme Caddesi No: 123, Şehir, Ülke", self.normal_style))
        elements.append(Paragraph("<b>Telefon:</b> +90 5XX XXX XX XX", self.normal_style))
        elements.append(Paragraph("<b>E-posta:</b> info@abcfınans.com", self.normal_style))
        elements.append(Spacer(1, 0.2 * 10 * 6))

        # 3. Belge Bilgileri ve Müşteri Bilgileri
        belge_bilgi_data = [
            [Paragraph(f"<b>{tur} No:</b> {belge_numarasi}", self.bold_style),
             Paragraph(f"<b>Müşteri Adı:</b> {musteri_adi}", self.bold_style)],
            [Paragraph(f"<b>Belge Tarihi:</b> {belge_tarihi_str}", self.normal_style),
             Paragraph(f"<b>Adres:</b> {musteri_adres}", self.normal_style)],
            [Paragraph(
                f"<b>{'Son Ödeme Tarihi' if tur == 'Fatura' else 'Geçerlilik Tarihi'}:</b> {son_odeme_gecerlilik_tarihi_str}",
                self.normal_style), Paragraph(f"<b>Telefon:</b> {musteri_telefon}", self.normal_style)],
            [Paragraph(f"<b>Durum:</b> {durum}", self.normal_style),
             Paragraph(f"<b>E-posta:</b> {musteri_email}", self.normal_style)],
        ]

        belge_bilgi_table = Table(belge_bilgi_data, colWidths=[letter[0] / 2, letter[0] / 2])
        belge_bilgi_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
        ]))
        elements.append(belge_bilgi_table)
        elements.append(Spacer(1, 0.2 * 10 * 6))

        # 4. Ürün/Hizmet Tablosu
        elements.append(Paragraph("<b>Ürünler / Hizmetler</b>", self.sub_heading_style))
        elements.append(Spacer(1, 0.1 * 10 * 6))

        urun_hizmetler_data = [
            [
                Paragraph("<b>Açıklama</b>", self.bold_style),
                Paragraph("<b>Miktar</b>", self.bold_style),
                Paragraph("<b>Birim Fiyat (₺)</b>", self.bold_style),
                Paragraph("<b>KDV (%)</b>", self.bold_style),
                Paragraph("<b>KDV Tutarı (₺)</b>", self.bold_style),
                Paragraph("<b>Ara Toplam (₺)</b>", self.bold_style)
            ]
        ]

        parsed_items = json.loads(urun_hizmetler_json)
        for item in parsed_items:
            urun_hizmetler_data.append([
                Paragraph(item.get('ad', ''), self.normal_style),
                Paragraph(f"{item.get('miktar', 0):g}".replace(".", ","), self.normal_style),
                Paragraph(f"{item.get('birim_fiyat', 0):,.2f}".replace(".", ","), self.normal_style),
                Paragraph(f"{item.get('kdv_orani', 0):g}".replace(".", ","), self.normal_style),
                Paragraph(f"{item.get('kdv_miktari', 0):,.2f}".replace(".", ","), self.normal_style),
                Paragraph(f"{item.get('ara_toplam', 0):,.2f}".replace(".", ","), self.normal_style)
            ])

        urun_hizmet_table_style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#D0D0D0")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 0), (-1, 0), self.font_name),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor("#F5F5F5")),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('FONTNAME', (0, 1), (-1, -1), self.font_name),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
            ('ALIGN', (2, 0), (5, -1), 'RIGHT'),
        ])

        col_widths_urun = [0.28 * letter[0], 0.1 * letter[0], 0.15 * letter[0], 0.1 * letter[0], 0.12 * letter[0],
                           0.15 * letter[0]]

        urun_hizmet_table = Table(urun_hizmetler_data, colWidths=col_widths_urun)
        urun_hizmet_table.setStyle(urun_hizmet_table_style)
        elements.append(urun_hizmet_table)
        elements.append(Spacer(1, 0.2 * 10 * 6))

        # 5. Toplam Tutarlar
        elements.append(Paragraph(
            f"<b>Toplam (KDV Hariç):</b> <font color='blue'>₺{toplam_tutar_kdv_haric:,.2f}".replace(".",
                                                                                                    ",") + "</font>",
            self.bold_style))
        elements.append(
            Paragraph(f"<b>Toplam KDV:</b> <font color='orange'>₺{toplam_kdv:,.2f}".replace(".", ",") + "</font>",
                      self.bold_style))
        elements.append(
            Paragraph(f"<b>Genel Toplam:</b> <font color='green'>₺{genel_toplam:,.2f}".replace(".", ",") + "</font>",
                      self.bold_style))
        elements.append(Spacer(1, 0.2 * 10 * 6))

        # 6. Notlar
        if notlar:
            elements.append(Paragraph("<b>Notlar:</b>", self.sub_heading_style))
            elements.append(Paragraph(notlar, self.normal_style))

        doc.build(elements)

