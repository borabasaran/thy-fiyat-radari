# THY Fiyat Radarı ✈

Önceden belirlediğiniz **birden çok destinasyonu ve tarih aralığını** tek seferde sorgulayıp
tüm en düşük **Turkish Airlines** fiyatlarını **tek ekranda, ısı haritalı bir pano** olarak
gösteren, tamamen GitHub üzerinde çalışan (sunucu ve **API anahtarı gerektirmeyen**) bir araçtır.

> **Veri kaynağı:** thy.com.tr bot koruması (Akamai) nedeniyle doğrudan taranamaz; THY'nin
> geliştirici API'si ise yalnızca kurumsal hesaplara açıktır. Bu yüzden fiyatlar, anahtarsız
> sorgulanabilen **Google Flights** verisinden alınır ve **yalnızca TK uçuşlarına filtrelenir**
> ([fast-flights](https://github.com/AWeirdDev/flights) kütüphanesi). Fiyatlar THY sitesindekiyle
> pratikte aynıdır; hücreye tıklayınca satın alma için aynı arama turkishairlines.com'da açılır.

## Mimari

```
config.json  ──▶  GitHub Actions (tek tık / günlük cron)
                      │  scripts/fetch_prices.py → Google Flights (TK filtreli)
                      ▼
              docs/data/results.json  ──▶  GitHub Pages panosu (docs/index.html)
```

## Rota ve tarihleri belirleme

`docs/config.json` dosyasını düzenleyin — commit ettiğiniz anda sorgu otomatik yeniden çalışır:

```jsonc
{
  "ayarlar": {
    "yolcuSayisi": 1,
    "paraBirimiTercihi": "TRY",   // EUR, USD... da olabilir
    "havayolular": ["TK"],        // boş liste = tüm havayolları
    "kabin": "economy",           // premium-economy | business | first
    "istekArasiBeklemeSn": 3      // Google'a nazik davranmak için
  },
  "rotalar": [
    { // tarih ARALIĞI ile (2 günde bir örneklenir)
      "ad": "İstanbul → Berlin",
      "kalkis": "IST", "varis": "BER",
      "seyahatTipi": "O",         // O = tek yön, R = gidiş-dönüş
      "tarihler": { "baslangic": "2026-08-01", "bitis": "2026-08-15", "adimGun": 2 }
    },
    { // gidiş-dönüş: dönüş = gidiş + konaklamaGun
      "ad": "İstanbul → Münih",
      "kalkis": "IST", "varis": "MUC",
      "seyahatTipi": "R", "konaklamaGun": 7,
      "tarihler": { "baslangic": "2026-09-01", "bitis": "2026-09-10", "adimGun": 3 }
    },
    { // tek tek TARİH LİSTESİ + yalnız aktarmasız uçuşlar
      "ad": "Ankara → Köln (aktarmasız)",
      "kalkis": "ESB", "varis": "CGN",
      "seyahatTipi": "O", "maxAktarma": 0,
      "tarihler": { "liste": ["2026-08-05", "2026-08-12", "2026-08-19"] }
    }
  ]
}
```

## "Tek tıkla" sorgulama — iki yol

1. **Panodaki buton:** *"Sorguyu şimdi çalıştır"* butonu GitHub API üzerinden iş akışını
   tetikler. İlk kullanımda bir **fine-grained personal access token** ister (GitHub →
   *Settings → Developer settings → Fine-grained tokens*; yalnızca bu depoya,
   **Actions: Read and write** izniyle). Token sadece kendi tarayıcınızda saklanır.
2. **Actions sekmesi:** Depo → *Actions* → "THY fiyatlarını güncelle" → *Run workflow*.

İş akışı ayrıca her gün 08:00'de (TR) otomatik çalışır; `cron` satırını
`.github/workflows/fiyat-guncelle.yml` içinde değiştirebilirsiniz.

## Bilinmesi gerekenler

- Bu, Google Flights'ın **resmî olmayan** bir kullanımıdır: Google sayfa yapısını değiştirirse
  kütüphane güncellenene kadar sorgular hata verebilir (`pip install -U fast-flights` genelde
  yeterli olur). Hatalı hücreler panoda işaretlenir; ayrıntı fare üzerine gelince görünür.
- GitHub Actions IP'leri nadiren Google tarafından sınırlanabilir; betik her hücre için
  3 deneme yapar. Kalıcı olursa depoya `FF_PROXY` secret'ı ekleyip bir proxy tanımlayabilirsiniz.
- Çok sayıda rota × tarih tanımlarsanız sorgu süresi uzar (hücre başına ~5-10 sn).
- Fiyatlar bilgilendirme amaçlıdır; rezervasyon anındaki fiyat farklılık gösterebilir.
