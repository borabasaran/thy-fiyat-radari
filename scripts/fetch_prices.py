#!/usr/bin/env python3
"""
THY Fiyat Radarı — veri toplama betiği (API anahtarı GEREKTİRMEZ)
=================================================================
docs/config.json içindeki rota × tarih kombinasyonlarını Google Flights
üzerinden (fast-flights kütüphanesi, anahtarsız) sorgular, sonuçları
Turkish Airlines uçuşlarına filtreler ve en düşük fiyatları
docs/data/results.json dosyasına yazar.

Opsiyonel ortam değişkeni:
  FF_PROXY : Google engellerse kullanılacak proxy adresi (http://...)

Kurulum: pip install fast-flights
"""

import datetime as dt
import json
import os
import subprocess
import sys
import time
from pathlib import Path


def _bagimliliklari_garanti_et():
    """fast-flights 3.0.2, typing_extensions bağımlılığını beyan etmiyor
    (paketleme hatası); eksikse çalışma anında kur."""
    try:
        import typing_extensions  # noqa: F401
    except ModuleNotFoundError:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "--quiet", "typing_extensions"]
        )


_bagimliliklari_garanti_et()

from fast_flights import FlightQuery, Passengers, create_query, get_flights
from fast_flights.exceptions import FlightsNotFound

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "docs" / "config.json"
OUTPUT_PATH = ROOT / "docs" / "data" / "results.json"
PROXY = os.environ.get("FF_PROXY") or None


def tarih_uret(tarihler: dict):
    """Config'teki tarih tanımından (liste veya aralık) date nesneleri üretir."""
    if "liste" in tarihler:
        for t in tarihler["liste"]:
            yield dt.date.fromisoformat(t)
        return
    d = dt.date.fromisoformat(tarihler["baslangic"])
    son = dt.date.fromisoformat(tarihler["bitis"])
    adim = max(1, int(tarihler.get("adimGun", 1)))
    while d <= son:
        yield d
        d += dt.timedelta(days=adim)


def sorgula(rota: dict, gidis: dt.date, ayarlar: dict):
    """Tek bir rota+tarih için Google Flights sorgusu; (fiyat, paraBirimi,
    ucusSayisi, aktarma) döner ya da FlightsNotFound fırlatır."""
    tip = rota.get("seyahatTipi", "O").upper()
    havayolular = rota.get("havayolular") or ayarlar.get("havayolular") or ["TK"]
    max_aktarma = rota.get("maxAktarma", ayarlar.get("maxAktarma"))
    para = (ayarlar.get("paraBirimiTercihi") or "TRY").upper()

    ucuslar = [FlightQuery(
        date=gidis.isoformat(),
        from_airport=rota["kalkis"],
        to_airport=rota["varis"],
        max_stops=max_aktarma,
        airlines=havayolular,
    )]
    if tip == "R":
        donus = gidis + dt.timedelta(days=int(rota.get("konaklamaGun", 7)))
        ucuslar.append(FlightQuery(
            date=donus.isoformat(),
            from_airport=rota["varis"],
            to_airport=rota["kalkis"],
            max_stops=max_aktarma,
            airlines=havayolular,
        ))

    q = create_query(
        flights=ucuslar,
        trip="round-trip" if tip == "R" else "one-way",
        seat=ayarlar.get("kabin", "economy"),
        passengers=Passengers(adults=int(ayarlar.get("yolcuSayisi", 1))),
        language="tr",
        currency=para,
    )
    sonuc = get_flights(q, proxy=PROXY)

    # Sorgu zaten havayolu filtreli; yine de savunmacı davranıp fiyatı 0'dan
    # büyük seçenekler arasından en düşüğünü alıyoruz.
    fiyatli = [f for f in sonuc if getattr(f, "price", 0) and f.price > 0]
    if not fiyatli:
        raise FlightsNotFound("fiyatlı seçenek yok")
    en_ucuz = min(fiyatli, key=lambda f: f.price)
    aktarma = max(len(en_ucuz.flights) - 1, 0) if getattr(en_ucuz, "flights", None) else None
    return float(en_ucuz.price), para, len(fiyatli), aktarma


def main() -> int:
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    ayarlar = config.get("ayarlar", {})
    bekleme = float(ayarlar.get("istekArasiBeklemeSn", 3))

    hucreler = []
    hata_sayisi = 0

    for rota in config.get("rotalar", []):
        for gidis in tarih_uret(rota["tarihler"]):
            hucre = {
                "rota": rota.get("ad") or f'{rota["kalkis"]} → {rota["varis"]}',
                "kalkis": rota["kalkis"],
                "varis": rota["varis"],
                "seyahatTipi": rota.get("seyahatTipi", "O").upper(),
                "gidisTarihi": gidis.isoformat(),
            }
            if hucre["seyahatTipi"] == "R":
                hucre["donusTarihi"] = (
                    gidis + dt.timedelta(days=int(rota.get("konaklamaGun", 7)))
                ).isoformat()

            son_hata = None
            for deneme in range(3):  # geçici engellere karşı 3 deneme
                try:
                    tutar, para, aday, aktarma = sorgula(rota, gidis, ayarlar)
                    hucre.update({
                        "tutar": round(tutar, 2),
                        "paraBirimi": para,
                        "adayFiyatSayisi": aday,
                        "durum": "ok",
                    })
                    if aktarma is not None:
                        hucre["aktarma"] = aktarma
                    son_hata = None
                    break
                except FlightsNotFound as e:
                    hucre["durum"] = "fiyat-bulunamadi"
                    hucre["detay"] = str(e)[:200]
                    son_hata = None
                    break
                except Exception as e:  # ağ/parse hatası — bekleyip yeniden dene
                    son_hata = e
                    time.sleep(5 * (deneme + 1))
            if son_hata is not None:
                hata_sayisi += 1
                hucre["durum"] = "hata"
                hucre["detay"] = f"{type(son_hata).__name__}: {son_hata}"[:300]

            print(f'[{hucre["durum"]:>16}] {hucre["rota"]} {hucre["gidisTarihi"]}'
                  + (f' → {hucre.get("tutar")} {hucre.get("paraBirimi")}'
                     if hucre.get("tutar") else ""))
            hucreler.append(hucre)
            time.sleep(bekleme)

    cikti = {
        "guncellemeZamani": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "kaynak": "google-flights (Turkish Airlines filtreli)",
        "hucreSayisi": len(hucreler),
        "hataSayisi": hata_sayisi,
        "sonuclar": hucreler,
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(cikti, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n{len(hucreler)} hücre yazıldı → {OUTPUT_PATH} (hata: {hata_sayisi})")
    # Hücrelerin tamamı hata verdiyse iş akışı da kırmızı görünsün:
    return 1 if hucreler and hata_sayisi == len(hucreler) else 0


if __name__ == "__main__":
    sys.exit(main())
