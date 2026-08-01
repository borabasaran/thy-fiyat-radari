import sys
import types
import unittest
from unittest.mock import patch

import fetch_prices as fp


class FetchPricesTests(unittest.TestCase):
    def test_rota_zaman_asimi_teknik_tur_olarak_siniflanir(self):
        self.assertEqual(fp.hata_turu(fp.RotaZamanAsimi("süre doldu")), "zaman-asimi")

    def test_ayristirma_hatasi_teknik_hata_olur(self):
        rota = {
            "ad": "Test", "anahtar": "IST-BER", "kalkis": "IST", "varis": "BER",
            "bolge": "Avrupa", "seyahatTipi": "O", "tarihler": {"liste": ["2026-08-17"]},
        }
        exceptions = types.ModuleType("fast_flights.exceptions")
        exceptions.FlightsNotFound = type("FlightsNotFound", (Exception,), {})
        package = types.ModuleType("fast_flights")
        package.exceptions = exceptions
        with patch.dict(sys.modules, {"fast_flights": package, "fast_flights.exceptions": exceptions}), patch.object(fp, "sorgula", side_effect=TypeError("bozuk yanıt")), patch.object(fp.time, "sleep"):
            with self.subTest("durum"):
                import tempfile, json
                from pathlib import Path
                with tempfile.TemporaryDirectory() as dizin:
                    yol = Path(dizin) / "sonuc.json"
                    fp.rota_sorgula(rota, {"yenidenDenemeSayisi": 1, "istekArasiBeklemeSn": 0}, yol, 30)
                    hucre = json.loads(yol.read_text(encoding="utf-8"))["sonuclar"][0]
                    self.assertEqual(hucre["durum"], "hata")
                    self.assertEqual(hucre["hataTuru"], "veri-ayristirma")


if __name__ == "__main__":
    unittest.main()
