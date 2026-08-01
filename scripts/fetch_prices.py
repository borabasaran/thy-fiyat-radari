#!/usr/bin/env python3
"""THY Fiyat Radarı: rota matrisi, sorgulama ve sonuç birleştirme."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import signal
import sys
import time
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "docs" / "config.json"
OUTPUT_PATH = ROOT / "docs" / "data" / "results.json"
HISTORY_PATH = ROOT / "docs" / "data" / "history.jsonl"
PROXY = os.environ.get("FF_PROXY") or None
IATA_DUZELTMELERI = {"HGK": "HKG", "DWF": "DFW"}
SEHIRLER = {
    "IST": "İstanbul",
    "SAW": "İstanbul (Sabiha Gökçen)",
    "ESB": "Ankara",
    "BER": "Berlin",
    "MUC": "Münih",
    "FRA": "Frankfurt",
    "VIE": "Viyana",
    "AMS": "Amsterdam",
    "FCO": "Roma",
    "CGN": "Köln",
    "MIA": "Miami",
    "PVG": "Şanghay",
    "HKG": "Hong Kong",
    "PEK": "Pekin",
    "CAN": "Guangzhou",
    "NRT": "Tokyo (Narita)",
    "HND": "Tokyo (Haneda)",
    "KIX": "Osaka",
    "ICN": "Seul",
    "SGN": "Ho Chi Minh City",
    "JFK": "New York",
    "ORD": "Chicago",
    "BOS": "Boston",
    "DFW": "Dallas/Fort Worth",
    "IAH": "Houston",
    "IAD": "Washington, DC",
    "LAS": "Las Vegas",
    "SDU": "Rio de Janeiro",
    "EZE": "Buenos Aires",
    "HAV": "Havana",
}


def kodu_duzelt(kod: str) -> str:
    temiz = str(kod or "").strip().upper()
    return IATA_DUZELTMELERI.get(temiz, temiz)


def sehir(kod: str) -> str:
    return SEHIRLER.get(kod, kod)


def rota_anahtari(kalkis: str, varis: str) -> str:
    return f"{kodu_duzelt(kalkis)}-{kodu_duzelt(varis)}"


def rota_etiketi(kalkis: str, varis: str) -> str:
    return f"{sehir(kalkis)} ({kalkis}) → {sehir(varis)} ({varis})"


def tarih_uret(tarihler: dict[str, Any]) -> Iterable[dt.date]:
    if "liste" in tarihler:
        for tarih in tarihler["liste"]:
            yield dt.date.fromisoformat(tarih)
        return

    gun = dt.date.fromisoformat(tarihler["baslangic"])
    son = dt.date.fromisoformat(tarihler["bitis"])
    adim = max(1, int(tarihler.get("adimGun", 1)))
    while gun <= son:
        yield gun
        gun += dt.timedelta(days=adim)


def rotalari_ac(config: dict[str, Any]) -> list[dict[str, Any]]:
    rotalar: list[dict[str, Any]] = []
    for blok in config.get("rotalar", []):
        kalkislar = blok.get("kalkislar") or [blok.get("kalkis")]
        varislar = blok.get("varislar") or [blok.get("varis")]
        for ham_kalkis in kalkislar:
            for ham_varis in varislar:
                kalkis, varis = kodu_duzelt(ham_kalkis), kodu_duzelt(ham_varis)
                rota = {
                    anahtar: deger
                    for anahtar, deger in blok.items()
                    if anahtar not in ("kalkislar", "varislar", "ad")
                }
                rota.update(
                    {
                        "kalkis": kalkis,
                        "varis": varis,
                        "ad": blok.get("ad") or rota_etiketi(kalkis, varis),
                        "anahtar": rota_anahtari(kalkis, varis),
                        "bolge": blok.get("bolge") or "Avrupa",
                    }
                )
                rotalar.append(rota)
    return rotalar


def bolge_secimi(ham: str | None) -> str | None:
    temiz = (ham or "").strip()
    return None if temiz.lower() in ("", "hepsi", "all") else temiz


def secili_rotalar(
    config: dict[str, Any], bolge: str | None = None, anahtar: str | None = None
) -> list[dict[str, Any]]:
    secili = rotalari_ac(config)
    if bolge:
        secili = [rota for rota in secili if rota["bolge"] == bolge]
    if anahtar:
        duzeltilmis = anahtar.replace("_", "-").upper()
        secili = [rota for rota in secili if rota["anahtar"] == duzeltilmis]
    return secili


def matrix_yaz(config: dict[str, Any], bolge: str | None, anahtar: str | None) -> int:
    rotalar = secili_rotalar(config, bolge, anahtar)
    matrix = {
        "include": [
            {
                "key": rota["anahtar"],
                "label": rota["ad"],
                "region": rota["bolge"],
            }
            for rota in rotalar
        ]
    }
    metin = json.dumps(matrix, ensure_ascii=False, separators=(",", ":"))
    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with Path(github_output).open("a", encoding="utf-8") as dosya:
            dosya.write(f"matrix={metin}\n")
            dosya.write(f"route_count={len(rotalar)}\n")
    print(metin)
    return 0


def sorgula(rota: dict[str, Any], gidis: dt.date, ayarlar: dict[str, Any]):
    from fast_flights import FlightQuery, Passengers, create_query, get_flights
    from fast_flights.exceptions import FlightsNotFound

    tip = str(rota.get("seyahatTipi", "O")).upper()
    havayollari = rota.get("havayolular") or ayarlar.get("havayolular") or ["TK"]
    max_aktarma = rota.get("maxAktarma", ayarlar.get("maxAktarma"))
    para = str(ayarlar.get("paraBirimiTercihi") or "TRY").upper()

    ucuslar = [
        FlightQuery(
            date=gidis.isoformat(),
            from_airport=rota["kalkis"],
            to_airport=rota["varis"],
            max_stops=max_aktarma,
            airlines=havayollari,
        )
    ]
    if tip == "R":
        donus = gidis + dt.timedelta(days=int(rota.get("konaklamaGun", 7)))
        ucuslar.append(
            FlightQuery(
                date=donus.isoformat(),
                from_airport=rota["varis"],
                to_airport=rota["kalkis"],
                max_stops=max_aktarma,
                airlines=havayollari,
            )
        )

    sonuc = get_flights(
        create_query(
            flights=ucuslar,
            trip="round-trip" if tip == "R" else "one-way",
            seat=ayarlar.get("kabin", "economy"),
            passengers=Passengers(adults=int(ayarlar.get("yolcuSayisi", 1))),
            language="tr",
            currency=para,
        ),
        proxy=PROXY,
    )
    fiyatli = [ucus for ucus in sonuc if getattr(ucus, "price", 0) and ucus.price > 0]
    if not fiyatli:
        raise FlightsNotFound("uygun fiyatlı TK uçuşu bulunamadı")

    en_ucuz = min(fiyatli, key=lambda ucus: ucus.price)
    bacaklar = getattr(en_ucuz, "flights", None)
    aktarma = max(len(bacaklar) - 1, 0) if bacaklar else None
    return float(en_ucuz.price), para, len(fiyatli), aktarma


def tekrar_edilebilir_hata(hata: Exception) -> bool:
    ad = type(hata).__name__.lower()
    metin = str(hata).lower()
    isaretler = ("timeout", "connection", "proxy", "temporar", "429", "503", "network")
    return any(isaret in ad or isaret in metin for isaret in isaretler)


def hata_turu(hata: Exception) -> str:
    metin = f"{type(hata).__name__} {hata}".lower()
    if isinstance(hata, TimeoutError) or "timeout" in metin:
        return "zaman-asimi"
    if any(x in metin for x in ("connection", "network", "proxy", "429", "503")):
        return "baglanti"
    if isinstance(hata, (IndexError, TypeError, ValueError, KeyError, AttributeError)):
        return "veri-ayristirma"
    return "beklenmeyen"


class RotaZamanAsimi(TimeoutError):
    """Bir rotaya ayrılan toplam süre doldu."""


def _zaman_asimi_sinyali(_isaret: int, _cerceve: Any) -> None:
    raise RotaZamanAsimi("rota için ayrılan süre doldu")


def hucre_taslagi(rota: dict[str, Any], gidis: dt.date, simdi: str) -> dict[str, Any]:
    hucre: dict[str, Any] = {
        "rota": rota["ad"],
        "rotaAnahtari": rota["anahtar"],
        "kalkis": rota["kalkis"],
        "kalkisSehir": sehir(rota["kalkis"]),
        "varis": rota["varis"],
        "varisSehir": sehir(rota["varis"]),
        "bolge": rota["bolge"],
        "seyahatTipi": str(rota.get("seyahatTipi", "O")).upper(),
        "gidisTarihi": gidis.isoformat(),
        "sorguZamani": simdi,
    }
    if hucre["seyahatTipi"] == "R":
        hucre["donusTarihi"] = (
            gidis + dt.timedelta(days=int(rota.get("konaklamaGun", 7)))
        ).isoformat()
    return hucre


def rota_sorgula(
    rota: dict[str, Any],
    ayarlar: dict[str, Any],
    cikis: Path,
    max_saniye: int | None = None,
) -> int:
    from fast_flights.exceptions import FlightsNotFound

    simdi = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    bekleme = max(0.0, float(ayarlar.get("istekArasiBeklemeSn", 2.5)))
    deneme_sayisi = max(1, int(ayarlar.get("yenidenDenemeSayisi", 2)))
    sonuclar: list[dict[str, Any]] = []
    tarihler = list(tarih_uret(rota["tarihler"]))
    max_saniye = max_saniye or int(ayarlar.get("rotaZamanSiniriSn", 210))
    baslangic = time.monotonic()
    sinyal_destegi = hasattr(signal, "SIGALRM") and hasattr(signal, "setitimer")
    onceki_isleyici = None
    if sinyal_destegi:
        onceki_isleyici = signal.signal(signal.SIGALRM, _zaman_asimi_sinyali)

    for sira, gidis in enumerate(tarihler, start=1):
        hucre = hucre_taslagi(rota, gidis, simdi)
        kalan = max_saniye - (time.monotonic() - baslangic)
        if kalan <= 0:
            hucre.update(
                {
                    "durum": "hata",
                    "hataTuru": "zaman-asimi",
                    "detay": (
                        "Rota zaman sınırı dolduğu için bu tarih sorgulanamadı."
                    ),
                }
            )
            sonuclar.append(hucre)
            continue
        print(f"[{sira}/{len(tarihler)}] {rota['anahtar']} {gidis.isoformat()}", flush=True)
        for deneme in range(deneme_sayisi):
            try:
                kalan = max_saniye - (time.monotonic() - baslangic)
                if kalan <= 0:
                    raise RotaZamanAsimi("rota için ayrılan süre doldu")
                if sinyal_destegi:
                    signal.setitimer(signal.ITIMER_REAL, max(0.1, kalan))
                tutar, para, aday, aktarma = sorgula(rota, gidis, ayarlar)
                hucre.update(
                    {
                        "tutar": round(tutar, 2),
                        "paraBirimi": para,
                        "adayFiyatSayisi": aday,
                        "durum": "ok",
                    }
                )
                if aktarma is not None:
                    hucre["aktarma"] = aktarma
                break
            except FlightsNotFound as hata:
                hucre.update(
                    {"durum": "fiyat-bulunamadi", "detay": str(hata)[:240]}
                )
                break
            except (IndexError, TypeError, ValueError, KeyError, AttributeError) as hata:
                hucre.update(
                    {
                        "durum": "hata",
                        "hataTuru": "veri-ayristirma",
                        "detay": (
                            "Google Flights yanıtı ayrıştırılamadı: "
                            f"{type(hata).__name__}: {hata}"
                        )[:300],
                    }
                )
                break
            except Exception as hata:  # noqa: BLE001
                son_deneme = deneme == deneme_sayisi - 1
                if son_deneme or not tekrar_edilebilir_hata(hata):
                    hucre.update(
                        {
                            "durum": "hata",
                            "hataTuru": hata_turu(hata),
                            "detay": f"{type(hata).__name__}: {hata}"[:300],
                        }
                    )
                    break
                hucre["deneme"] = deneme + 2
                time.sleep(min(4 * (deneme + 1), max(0, kalan)))
            finally:
                if sinyal_destegi:
                    signal.setitimer(signal.ITIMER_REAL, 0)

        print(
            f"[{hucre.get('durum', 'hata')}] {rota['anahtar']} {gidis.isoformat()}",
            flush=True,
        )
        sonuclar.append(hucre)
        if bekleme and sira < len(tarihler):
            time.sleep(bekleme)

    if sinyal_destegi and onceki_isleyici is not None:
        signal.signal(signal.SIGALRM, onceki_isleyici)

    payload = {
        "rotaAnahtari": rota["anahtar"],
        "bolge": rota["bolge"],
        "tamamlanmaZamani": simdi,
        "sonuclar": sonuclar,
    }
    cikis.parent.mkdir(parents=True, exist_ok=True)
    cikis.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return 0


def eski_veriyi_oku() -> dict[str, Any]:
    if not OUTPUT_PATH.exists():
        return {}
    try:
        return json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
    except Exception as hata:  # noqa: BLE001
        print("Önceki sonuçlar okunamadı:", hata)
        return {}


def hucre_anahtari(hucre: dict[str, Any]) -> str:
    return "|".join(
        (
            rota_anahtari(hucre.get("kalkis", ""), hucre.get("varis", "")),
            str(hucre.get("gidisTarihi") or ""),
            str(hucre.get("donusTarihi") or ""),
        )
    )


def onceki_fiyati_ekle(
    yeni: dict[str, Any], onceki: dict[str, Any] | None
) -> dict[str, Any]:
    if not onceki:
        return yeni
    onceki_tutar = (
        onceki.get("tutar")
        if onceki.get("durum") == "ok"
        else onceki.get("sonBasariliTutar")
    )
    onceki_para = (
        onceki.get("paraBirimi")
        if onceki.get("durum") == "ok"
        else onceki.get("sonBasariliParaBirimi")
    )
    onceki_zaman = (
        onceki.get("sorguZamani")
        if onceki.get("durum") == "ok"
        else onceki.get("sonBasariliSorguZamani")
    )
    if onceki_tutar is None:
        return yeni
    if yeni.get("durum") == "ok":
        yeni["oncekiTutar"] = onceki_tutar
    else:
        yeni.update(
            {
                "sonBasariliTutar": onceki_tutar,
                "sonBasariliParaBirimi": onceki_para,
                "sonBasariliSorguZamani": onceki_zaman,
            }
        )
    return yeni


def birlestir(parca_dizini: Path) -> int:
    eski = eski_veriyi_oku()
    eski_sonuclar = eski.get("sonuclar", [])
    eski_harita = {hucre_anahtari(hucre): hucre for hucre in eski_sonuclar}
    payloadlar: list[dict[str, Any]] = []

    for yol in sorted(parca_dizini.glob("*.json")):
        try:
            payload = json.loads(yol.read_text(encoding="utf-8"))
            if payload.get("rotaAnahtari") and isinstance(payload.get("sonuclar"), list):
                payloadlar.append(payload)
        except (OSError, json.JSONDecodeError) as hata:
            print(f"Parça atlandı ({yol.name}): {hata}")

    if not payloadlar:
        raise RuntimeError("Birleştirilecek rota sonucu bulunamadı.")

    guncellenen_anahtarlar = {p["rotaAnahtari"] for p in payloadlar}
    korunan = [
        hucre
        for hucre in eski_sonuclar
        if rota_anahtari(hucre.get("kalkis", ""), hucre.get("varis", ""))
        not in guncellenen_anahtarlar
    ]
    yeni_sonuclar: list[dict[str, Any]] = []
    for payload in payloadlar:
        for hucre in payload["sonuclar"]:
            yeni_sonuclar.append(
                onceki_fiyati_ekle(hucre, eski_harita.get(hucre_anahtari(hucre)))
            )

    tum_hucreler = korunan + yeni_sonuclar
    simdi = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    bolge_zamanlari = dict(eski.get("bolgeGuncellemeZamanlari") or {})
    for payload in payloadlar:
        bolge_zamanlari[payload["bolge"]] = payload["tamamlanmaZamani"]

    durumlar = [hucre.get("durum") for hucre in tum_hucreler]
    cikti = {
        "guncellemeZamani": simdi,
        "kaynak": "google-flights (Turkish Airlines filtreli)",
        "sorgulananBolge": (
            payloadlar[0]["bolge"]
            if len({p["bolge"] for p in payloadlar}) == 1
            else "hepsi"
        ),
        "bolgeGuncellemeZamanlari": bolge_zamanlari,
        "hucreSayisi": len(tum_hucreler),
        "basariSayisi": durumlar.count("ok"),
        "fiyatBulunamadiSayisi": durumlar.count("fiyat-bulunamadi"),
        "hataSayisi": durumlar.count("hata"),
        "yeniHucreSayisi": len(yeni_sonuclar),
        "yeniHataSayisi": sum(
            1 for hucre in yeni_sonuclar if hucre.get("durum") == "hata"
        ),
        "sonuclar": sorted(
            tum_hucreler,
            key=lambda h: (
                str(h.get("bolge")),
                str(h.get("kalkis")),
                str(h.get("varis")),
                str(h.get("gidisTarihi")),
            ),
        ),
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(cikti, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    satirlar = []
    for hucre in yeni_sonuclar:
        if hucre.get("durum") != "ok":
            continue
        satirlar.append(
            json.dumps(
                {
                    "olcum": hucre["sorguZamani"],
                    "rota": hucre["rota"],
                    "kalkis": hucre["kalkis"],
                    "kalkisSehir": hucre["kalkisSehir"],
                    "varis": hucre["varis"],
                    "varisSehir": hucre["varisSehir"],
                    "bolge": hucre["bolge"],
                    "gidisTarihi": hucre["gidisTarihi"],
                    "donusTarihi": hucre.get("donusTarihi"),
                    "tutar": hucre["tutar"],
                    "paraBirimi": hucre["paraBirimi"],
                },
                ensure_ascii=False,
            )
        )
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    if satirlar:
        with HISTORY_PATH.open("a", encoding="utf-8") as dosya:
            dosya.write("\n".join(satirlar) + "\n")

    print(
        f"{len(payloadlar)} rota birleştirildi; başarılı={durumlar.count('ok')}, "
        f"bulunamadı={durumlar.count('fiyat-bulunamadi')}, hata={durumlar.count('hata')}"
    )
    return 0


def argumanlar() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--matrix", action="store_true")
    parser.add_argument("--route")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--merge", type=Path)
    parser.add_argument("--region")
    parser.add_argument("--max-seconds", type=int)
    return parser.parse_args()


def main() -> int:
    args = argumanlar()
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    bolge = bolge_secimi(args.region or os.environ.get("BOLGE"))
    anahtar = args.route or os.environ.get("ROTA")

    if args.matrix:
        return matrix_yaz(config, bolge, anahtar)
    if args.merge:
        return birlestir(args.merge)
    if args.route:
        rotalar = secili_rotalar(config, bolge, args.route)
        if len(rotalar) != 1:
            raise ValueError(f"Rota bulunamadı veya benzersiz değil: {args.route}")
        return rota_sorgula(
            rotalar[0],
            config.get("ayarlar", {}),
            args.output or Path("partial.json"),
            args.max_seconds,
        )
    raise SystemExit("--matrix, --route veya --merge seçeneklerinden biri gerekli.")


if __name__ == "__main__":
    sys.exit(main())
