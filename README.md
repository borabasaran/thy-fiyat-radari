# THY Fiyat Radarı ✈

Birden çok destinasyonu ve tarih aralığını Google Flights üzerinden sorgular, yalnızca Turkish Airlines (`TK`) sonuçlarını gösterir ve en düşük fiyatları GitHub Pages panosunda sunar.

## Neler var?

- Avrupa, Asya ve Amerika için ayrı sekmeler
- IATA kodlarının yanında şehir adları
- Mobil telefonlara uyumlu arayüz
- Her rota için bekliyor, sorgulanıyor, tamamlandı ve hata durumları
- Gerçek ilerleme yüzdesi, etkin rota ve yaklaşık kalan süre
- En fazla üç rotayı aynı anda sorgulayan kontrollü paralel çalışma
- Rota başına 210 saniyelik betik sınırı ve 6 dakikalık iş emniyet sınırı
- Hatalı rotayı tek başına yeniden deneme ve devam eden sorguyu durdurma
- Bölge bazlı son güncelleme zamanı
- Başarılı, bulunamayan ve teknik hatalı sorgular için özet
- Önceki fiyata göre artış/düşüş ve 24 saatten eski veri uyarısı
- Yeni sorgu hata verse bile son başarılı fiyatı koruma
- Kalıcı fiyat geçmişi (`docs/data/history.jsonl`)

## Çalışma biçimi

```text
docs/config.json
      ↓
GitHub Actions → rota matrisi → en fazla 3 paralel sorgu
      ↓
sonuçları birleştir → docs/data/results.json + docs/data/history.jsonl
      ↓
GitHub Pages
```

## Sorgu başlatma

Panoda **Sorguyu çalıştır** düğmesine basın. İlk kullanımda yalnızca bu depoya erişen fine-grained bir GitHub token gerekir:

- Contents: Read and write
- Actions: Read and write

Token yalnızca kullandığınız tarayıcının yerel saklama alanında tutulur.

Pano açıkken yayımlanmış sonuç dosyasını beş dakikada bir sessizce yeniden
okur. Bu yalnızca mevcut sonuçları ekranda günceller; fiyat taraması başlatmaz.
**Ekrandaki veriyi yenile** düğmesi de aynı şekilde yalnızca bu dosyayı yeniden
yükler ve yeni bir GitHub Actions çalışması başlatmaz.

Alternatif olarak GitHub → Actions → **THY fiyatlarını güncelle** → **Run workflow** yolunu kullanabilirsiniz.

Otomatik veya zamanlanmış tarama yoktur. Fiyat sorgusu yalnızca panodaki bölge
düğmesiyle ya da GitHub Actions ekranındaki **Run workflow** işlemiyle açıkça
başlatılır. Pano yalnızca seçili bölgeyi tarar. Actions ekranı varsayılan olarak
Avrupa'yı tarar; kullanıcı Asya, Amerika, tüm bölgeler veya tek rota kapsamını
açıkça seçebilir.

Sorgu sırasında pano GitHub Actions işlerini izler. Her rotanın yanında gerçek
durum gösterilir. Teknik hata alan bir rotadaki **yalnız bunu yeniden dene**
düğmesi diğer rotaları tekrar çalıştırmadan yalnızca o rotayı sorgular.

## Rotaları düzenleme

Panodaki **Rotaları düzenle** düğmesiyle tarih aralığını `GG.AA.YYYY`
biçiminde, yolcu sayısını, kalkış ve varış kodlarını ve rota başına aktarma
sınırını değiştirebilirsiniz.

Geçerli örnek:

```json
{
  "kalkis": "IST",
  "varislar": ["BER", "MUC", "FRA"],
  "bolge": "Avrupa",
  "seyahatTipi": "R",
  "tarihler": {
    "baslangic": "2026-08-17",
    "bitis": "2026-08-24",
    "adimGun": 2
  },
  "konaklamaGun": 7,
  "maxAktarma": 0
}
```

## Veri kaynağı ve sınırlamalar

THY sitesi bot koruması nedeniyle doğrudan taranmaz. Fiyatlar `fast-flights` aracılığıyla Google Flights verisinden alınır ve TK uçuşlarıyla sınırlandırılır. Bu resmî bir THY API entegrasyonu değildir; Google sayfa yapısı değişirse geçici sorgu sorunları yaşanabilir. Fiyatlar bilgilendirme amaçlıdır ve rezervasyon anında farklılaşabilir.
