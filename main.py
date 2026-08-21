from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
import smtplib
from datetime import datetime, date, timedelta, timezone
from typing import Optional
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from apscheduler.schedulers.background import BackgroundScheduler

app = FastAPI(title="Ofis Nöbet Sistemi API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# 1. JSONBIN BULUT BAĞLANTISI
# ==========================================
BIN_ID = "6a8411c3da38895dfef1d1a8"
API_KEY = "$2a$10$pXDTgZeZJDW/a0zcomMd3uEEBbVQ7S8xILRQcvsJIChKFF3phMvcW"
JSONBIN_URL = f"https://api.jsonbin.io/v3/b/{BIN_ID}"

def veriyi_oku():
    headers = {'X-Master-Key': API_KEY}
    response = requests.get(JSONBIN_URL, headers=headers)
    if response.status_code == 200:
        return response.json()['record']
    return {"kullanicilar": [], "loglar": [], "cay_listesi": [], "su_listesi": [], "izinler": []}

def veriyi_kaydet(veri):
    headers = {'Content-Type': 'application/json', 'X-Master-Key': API_KEY}
    requests.put(JSONBIN_URL, json=veri, headers=headers)

def log_ekle(veri, eylem):
    veri["loglar"].insert(0, {"id": len(veri["loglar"]) + 1, "eylem": eylem, "tarih": datetime.now().isoformat()})

def get_turkey_today():
    tz_tr = timezone(timedelta(hours=3))
    return str(datetime.now(tz_tr).date())

# ==========================================
# 2. E-POSTA GÖNDERME
# ==========================================
def eposta_gonder(alici_email: str, konu: str, icerik: str):
    gonderici_email = "ayseyalcin2222ay@gmail.com"
    gonderici_sifre = "waho ecij ocqk fqlv" 
    msg = MIMEMultipart()
    msg['From'] = gonderici_email
    msg['To'] = alici_email
    msg['Subject'] = konu
    msg.attach(MIMEText(icerik, 'plain', 'utf-8'))
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(gonderici_email, gonderici_sifre)
        server.send_message(msg)
        server.quit()
    except Exception as e:
        print(f"Mail gönderme hatası: {e}")

# ==========================================
# 3. PYDANTIC ŞEMALARI
# ==========================================
class KullaniciEkle(BaseModel):
    ad_soyad: str
    email: str

class KullaniciGuncelle(BaseModel):
    ad_soyad: str
    email: str

class TakasModel(BaseModel):
    yeni_kullanici_id: int

class IzinModel(BaseModel):
    kullanici_id: int
    baslangic_tarihi: str
    bitis_tarihi: Optional[str] = None

# ==========================================
# 4. KULLANICI İŞLEMLERİ
# ==========================================
@app.get("/")
def read_root():
    return {"mesaj": "Ofis Nöbet Sistemi API başarıyla çalışıyor!"}

@app.get("/kullanicilar/")
def get_kullanicilar():
    return veriyi_oku()["kullanicilar"]

@app.post("/kullanicilar/ekle")
def add_kullanici(k: KullaniciEkle):
    veri = veriyi_oku()
    if any(x["email"] == k.email for x in veri["kullanicilar"]):
        raise HTTPException(status_code=400, detail="Bu e-posta kayıtlı.")
    
    kullanici_id = len(veri["kullanicilar"]) + 1
    yeni_kullanici = {"id": kullanici_id, "ad_soyad": k.ad_soyad, "email": k.email, "kullanici_durum": "aktif"}
    veri["kullanicilar"].append(yeni_kullanici)
    
    for gorev in ["cay_listesi", "su_listesi"]:
        son_sira = len(veri[gorev]) + 1
        veri[gorev].append({"nobet_id": int(f"{kullanici_id}{son_sira}"), "kullanici_id": kullanici_id, "sira_no": son_sira, "ad_soyad": k.ad_soyad, "sorumlu_mu": False, "kullanici_durum": "aktif"})

    log_ekle(veri, f"{k.ad_soyad} sisteme eklendi.")
    veriyi_kaydet(veri)
    return {"mesaj": "Başarıyla eklendi!"}

@app.put("/api/kullanicilar/{kullanici_id}")
def update_kullanici(kullanici_id: int, k_veri: KullaniciGuncelle):
    veri = veriyi_oku()
    kullanici = next((k for k in veri["kullanicilar"] if k["id"] == kullanici_id), None)
    if not kullanici:
        raise HTTPException(status_code=404, detail="Kullanıcı bulunamadı.")
        
    eski_isim = kullanici["ad_soyad"]
    kullanici["ad_soyad"] = k_veri.ad_soyad
    kullanici["email"] = k_veri.email
    
    for liste_adi in ["cay_listesi", "su_listesi"]:
        for k in veri[liste_adi]:
            if k["kullanici_id"] == kullanici_id:
                k["ad_soyad"] = k_veri.ad_soyad
                
    log_ekle(veri, f"'{eski_isim}' bilgileri güncellendi: {k_veri.ad_soyad}")
    veriyi_kaydet(veri)
    return {"mesaj": "Kullanıcı güncellendi."}

@app.delete("/api/kullanicilar/{kullanici_id}")
def delete_kullanici(kullanici_id: int):
    veri = veriyi_oku()
    kullanici = next((k for k in veri["kullanicilar"] if k["id"] == kullanici_id), None)
    if not kullanici:
        raise HTTPException(status_code=404, detail="Kullanıcı bulunamadı.")

    veri["kullanicilar"] = [k for k in veri["kullanicilar"] if k["id"] != kullanici_id]
    veri["cay_listesi"] = [k for k in veri["cay_listesi"] if k["kullanici_id"] != kullanici_id]
    veri["su_listesi"] = [k for k in veri["su_listesi"] if k["kullanici_id"] != kullanici_id]
    veri["izinler"] = [i for i in veri["izinler"] if i["kullanici_id"] != kullanici_id]
    
    log_ekle(veri, f"{kullanici['ad_soyad']} silindi.")
    veriyi_kaydet(veri)
    return {"mesaj": "Silindi."}

@app.put("/api/kullanicilar/{kullanici_id}/durum")
def kullanici_durum(kullanici_id: int, yeni_durum: str):
    veri = veriyi_oku()
    kullanici = next((k for k in veri["kullanicilar"] if k["id"] == kullanici_id), None)
    kullanici["kullanici_durum"] = yeni_durum
    for liste_adi in ["cay_listesi", "su_listesi"]:
        for k in veri[liste_adi]:
            if k["kullanici_id"] == kullanici_id:
                k["kullanici_durum"] = yeni_durum
    log_ekle(veri, f"{kullanici['ad_soyad']} durumu '{yeni_durum}' yapıldı.")
    veriyi_kaydet(veri)
    return {"mesaj": "Güncellendi."}

@app.post("/api/izin/ekle")
def izin_ekle(model: IzinModel):
    veri = veriyi_oku()
    kullanici = next((k for k in veri["kullanicilar"] if k["id"] == model.kullanici_id), None)
    veri["izinler"].append(model.dict())
    log_ekle(veri, f"{kullanici['ad_soyad']} için izin girildi.")
    veriyi_kaydet(veri)
    return {"mesaj": "İzin kaydedildi"}

@app.post("/api/bildirim/cay")
def cay_bildirimi(durum: str, background_tasks: BackgroundTasks):
    veri = veriyi_oku()
    sorumlu = next((k for k in veri["cay_listesi"] if k["sorumlu_mu"]), None)
    kullanici = next((k for k in veri["kullanicilar"] if k["id"] == sorumlu["kullanici_id"]))
    
    if durum == "azaldi":
        konu = "🔔 Ofiste Çay Azaldı!"
        mesaj = f"Merhaba {kullanici['ad_soyad']}, \n\nOfiste çay azalmış durumda. Müsait olduğunda ilgilenebilir misin?"
    else:
        konu = "🚨 Yeni Çay Alınacak!"
        mesaj = f"Merhaba {kullanici['ad_soyad']}, \n\nOfiste an itibariyle çay bitti! Çay nöbeti sende olduğu için yeni çay alınması bekleniyor."

    background_tasks.add_task(eposta_gonder, kullanici["email"], konu, mesaj)
    log_ekle(veri, f"{kullanici['ad_soyad']} kişisine çay {durum} bildirimi gönderildi.")
    veriyi_kaydet(veri)
    return {"mesaj": "Gönderildi."}

@app.post("/api/bildirim/su")
def su_bildirimi(background_tasks: BackgroundTasks):
    veri = veriyi_oku()
    sorumlu = next((k for k in veri["su_listesi"] if k["sorumlu_mu"]), None)
    kullanici = next((k for k in veri["kullanicilar"] if k["id"] == sorumlu["kullanici_id"]))
    
    konu = "💧 Yarın Su Geliyor - Nöbet Hatırlatması"
    mesaj = f"Merhaba {kullanici['ad_soyad']}, \n\nBu haftanın su sorumlusu sensin. Yarın su teslimatı yapılacak."

    background_tasks.add_task(eposta_gonder, kullanici["email"], konu, mesaj)
    log_ekle(veri, f"{kullanici['ad_soyad']} kişisine manuel su hatırlatması gönderildi.")
    veriyi_kaydet(veri)
    return {"mesaj": "Gönderildi."}

# ==========================================
# 5. DÖNGÜ VE İZİN ATLAMALARI 
# ==========================================
@app.get("/api/nobet/liste/{gorev_tipi}")
def get_liste(gorev_tipi: str):
    liste = veriyi_oku()[f"{gorev_tipi}_listesi"]
    return sorted(liste, key=lambda x: x["sira_no"])

@app.get("/api/loglar")
def get_loglar():
    return veriyi_oku()["loglar"][:15]

@app.post("/api/nobet/baslat/{gorev_tipi}")
def sistemi_baslat(gorev_tipi: str):
    veri = veriyi_oku()
    liste = veri[f"{gorev_tipi}_listesi"]
    
    liste.sort(key=lambda x: x["sira_no"])
    
    if any(k["sorumlu_mu"] for k in liste):
        return {"mesaj": "Sistem zaten aktif."}
    if len(liste) == 0:
        raise HTTPException(status_code=400, detail="Listede kimse yok!")

    bugun_str = get_turkey_today()
    for k in liste:
        if k["kullanici_durum"] == "pasif":
            continue
            
        izinli_mi = False
        for izin in veri["izinler"]:
            if izin["kullanici_id"] == k["kullanici_id"]:
                bas, bit = izin["baslangic_tarihi"], izin["bitis_tarihi"]
                if (bit and bas <= bugun_str <= bit) or (not bit and bas <= bugun_str):
                    izinli_mi = True
        
        if not izinli_mi:
            k["sorumlu_mu"] = True
            log_ekle(veri, f"{gorev_tipi.upper()} nöbeti başlatıldı. İlk sorumlu: {k['ad_soyad']}")
            veriyi_kaydet(veri)
            return {"mesaj": "Sistem başlatıldı"}
            
    raise HTTPException(status_code=400, detail="Herkes izinli veya pasif olduğu için başlatılamadı.")

@app.post("/api/nobet/tamamla/{gorev_tipi}")
def tamamla(gorev_tipi: str):
    veri = veriyi_oku()
    liste = veri[f"{gorev_tipi}_listesi"]
    
    liste.sort(key=lambda x: x["sira_no"]) 
    
    aktif_index = next((i for i, k in enumerate(liste) if k["sorumlu_mu"]), -1)
    if aktif_index == -1 or len(liste) == 0:
        raise HTTPException(status_code=400, detail="Devredilecek aktif sorumlu bulunamadı.")
        
    aranan_index = aktif_index
    yeni_sorumlu_bulundu = False
    bugun_str = get_turkey_today()

    for _ in range(len(liste) - 1):
        aranan_index = (aranan_index + 1) % len(liste)
        aday = liste[aranan_index]

        if aday["kullanici_durum"] == "pasif":
            continue

        izinli_mi = False
        for izin in veri["izinler"]:
            if izin["kullanici_id"] == aday["kullanici_id"]:
                bas, bit = izin["baslangic_tarihi"], izin["bitis_tarihi"]
                if (bit and bas <= bugun_str <= bit) or (not bit and bas <= bugun_str):
                    izinli_mi = True
        
        if izinli_mi:
            continue
            
        liste[aktif_index]["sorumlu_mu"] = False
        aday["sorumlu_mu"] = True
        yeni_sorumlu_bulundu = True
        log_ekle(veri, f"{gorev_tipi.upper()} nöbeti devredildi. Yeni sorumlu: {aday['ad_soyad']}")
        break

    if not yeni_sorumlu_bulundu:
        raise HTTPException(status_code=400, detail="Sırada devredilecek başka aktif/izinsiz kimse yok!")

    veriyi_kaydet(veri)
    return {"mesaj": "Sıra devredildi"}

@app.post("/api/nobet/atla/{gorev_tipi}")
def atla(gorev_tipi: str):
    veri = veriyi_oku()
    liste = veri[f"{gorev_tipi}_listesi"]
    
    liste.sort(key=lambda x: x["sira_no"]) 
    
    aktif_index = next((i for i, k in enumerate(liste) if k["sorumlu_mu"]), -1)
    if aktif_index == -1 or len(liste) == 0:
        raise HTTPException(status_code=400, detail="Atlanacak aktif sorumlu bulunamadı.")
        
    aranan_index = aktif_index
    yeni_sorumlu_bulundu = False
    bugun_str = get_turkey_today()

    for _ in range(len(liste) - 1):
        aranan_index = (aranan_index + 1) % len(liste)
        aday = liste[aranan_index]

        if aday["kullanici_durum"] == "pasif":
            continue

        izinli_mi = False
        for izin in veri["izinler"]:
            if izin["kullanici_id"] == aday["kullanici_id"]:
                bas, bit = izin["baslangic_tarihi"], izin["bitis_tarihi"]
                if (bit and bas <= bugun_str <= bit) or (not bit and bas <= bugun_str):
                    izinli_mi = True
        
        if izinli_mi:
            continue
            
        eski_sorumlu_ad = liste[aktif_index]["ad_soyad"]
        liste[aktif_index]["sorumlu_mu"] = False
        aday["sorumlu_mu"] = True
        yeni_sorumlu_bulundu = True
        log_ekle(veri, f"{eski_sorumlu_ad}, {gorev_tipi.upper()} sırasını pas geçti. Yeni sorumlu: {aday['ad_soyad']}")
        break

    if not yeni_sorumlu_bulundu:
        raise HTTPException(status_code=400, detail="Sırada atlanacak başka aktif/izinsiz kimse yok!")

    veriyi_kaydet(veri)
    return {"mesaj": "Sıra atlandı"}

@app.put("/api/nobet/devret/{gorev_tipi}")
def takas(gorev_tipi: str, model: TakasModel):
    veri = veriyi_oku()
    liste = veri[f"{gorev_tipi}_listesi"]
    
    eski_sorumlu = next((k for k in liste if k["sorumlu_mu"]), None)
    yeni_sorumlu = next((k for k in liste if k["kullanici_id"] == model.yeni_kullanici_id), None)
    
    if not eski_sorumlu or not yeni_sorumlu:
        raise HTTPException(status_code=400, detail="Takas edilecek kişiler bulunamadı.")

    gecici_sira = eski_sorumlu["sira_no"]
    eski_sorumlu["sira_no"] = yeni_sorumlu["sira_no"]
    yeni_sorumlu["sira_no"] = gecici_sira
    
    eski_sorumlu["sorumlu_mu"] = False
    yeni_sorumlu["sorumlu_mu"] = True
    
    log_ekle(veri, f"{eski_sorumlu['ad_soyad']} görevini {yeni_sorumlu['ad_soyad']} ile takas etti.")
    veriyi_kaydet(veri)
    return {"mesaj": "Takas başarılı"}

def otomatik_su_maili_gonder():
    try:
        veri = veriyi_oku()
        mevcut_sorumlu = next((k for k in veri["su_listesi"] if k["sorumlu_mu"]), None)
        if mevcut_sorumlu:
            kullanici = next((k for k in veri["kullanicilar"] if k["id"] == mevcut_sorumlu["kullanici_id"]))
            eposta_gonder(kullanici["email"], "💧 Yarın Su Geliyor", f"Merhaba {kullanici['ad_soyad']}, \nBu haftanın su sorumlusu sensin. Yarın su teslimatı yapılacak.")
            log_ekle(veri, f"Otomatik Sistem: {kullanici['ad_soyad']} (Çarşamba) maili atıldı.")
            veriyi_kaydet(veri)
    except Exception as e:
        pass

scheduler = BackgroundScheduler()
scheduler.add_job(otomatik_su_maili_gonder, 'cron', day_of_week='wed', hour=9, minute=0)

@app.on_event("startup")
def startup_event():
    scheduler.start()