# 🏢 Ofis Nöbet Sistemi - Backend (API)

Bu proje, ofis içi çay ve su nöbetlerini yönetmek, takip etmek ve otomatik e-posta bildirimleri göndermek için geliştirilmiş bir RESTful API servisidir. 

Veritabanı sunucularına olan bağımlılığı ortadan kaldırmak amacıyla veriler bulut tabanlı bir JSON kasasında (**JSONBin.io**) tutulmaktadır.

## 🚀 Özellikler
* **JSONBin Entegrasyonu:** Tüm veriler (personeller, nöbetler, loglar) bulutta tutulur, sunucu uyku moduna geçse bile veriler silinmez.
* **Akıllı Nöbet Döngüsü:** Sıra devredilirken pasif veya o gün izinde olan personeller otomatik olarak atlanır.
* **Sıra Atlama (Pas Geçme):** Personel o an müsait değilse sırasını bir sonrakine devredebilir.
* **Takas Sistemi:** İki personel kendi aralarında nöbet sıralarını değiştirebilir.
* **E-Posta Bildirimleri (smtplib):** Çay azaldığında/bittiğinde veya su siparişi günü geldiğinde ilgili sorumluya otomatik e-posta atılır.
* **Zamanlanmış Görevler (APScheduler):** Her Çarşamba sabahı saat 09:00'da o haftanın su sorumlusuna otomatik hatırlatma maili gider.

## 🛠️ Kullanılan Teknolojiler
* **Python 3**
* **FastAPI:** Hızlı ve modern API geliştirme altyapısı.
* **Uvicorn:** ASGI sunucusu.
* **Requests:** JSONBin.io ile haberleşmek için.
* **APScheduler:** Arka plan zamanlanmış görevleri için.

## ⚙️ Kurulum ve Çalıştırma

**
1. Projeyi bilgisayarınıza indirin:
```bash
git clone [https://github.com/AyseYALCIN2/ofis-nobet-backend](https://github.com/AyseYALCIN2/ofis-nobet-backend)
cd ofis-nobet-backend
2. Gerekli kütüphaneleri yükleyin:
pip install fastapi uvicorn pydantic requests apscheduler
3. API Anahtarlarını Ayarlayın:
main.py dosyası içindeki şu alanları kendi JSONBin ve Gmail bilgilerinizle güncelleyin:

BIN_ID ve API_KEY (JSONBin.io üzerinden alınır)

gonderici_email ve gonderici_sifre (Gmail Uygulama Şifresi)
4. Sunucuyu Başlatın:
uvicorn main:app --reload
API varsayılan olarak http://127.0.0.1:8000 adresinde çalışacaktır. **#