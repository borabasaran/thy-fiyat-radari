// THY Fiyat Radarı: sürüm imzası. Görünür bir değişiklik yayınlandığında SURUM'u artırın;
// sayfaların altında "© 2026 THY Fiyat Radarı v1.1 by bbasaran" olarak görünür.
// "bbasaran" bbasaran.net'e bağlanır; yazı çevresindeki metinle aynı görünür,
// altı çizilmez ve rengi değişmez, yalnızca üzerine gelince altçizgi belirir.
(function () {
  var AD = 'THY Fiyat Radarı';
  var SURUM = '1.1';
  var YAZAR = 'bbasaran';
  var YAZAR_URL = 'https://bbasaran.net';

  function ekle() {
    if (document.querySelector('.bb-imza')) return;
    var el = document.createElement('div');
    el.className = 'bb-imza';
    el.innerHTML = '© ' + new Date().getFullYear() + ' ' + AD + ' v' + SURUM +
      ' by <a href="' + YAZAR_URL + '" target="_blank" rel="noopener">' + YAZAR + '</a>';
    var st = document.createElement('style');
    st.textContent = '.bb-imza{font-size:12px;line-height:1.6;opacity:.7;text-align:center;padding:14px 16px 18px;width:100%;flex-basis:100%}' +
      'footer .bb-imza{padding:10px 0 0}' +
      '.bb-imza a{color:inherit;text-decoration:none}' +
      '.bb-imza a:hover{color:inherit;text-decoration:underline;text-underline-offset:2px}';
    document.head.appendChild(st);
    var altbilgi = document.querySelector('footer');
    (altbilgi || document.body).appendChild(el);
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', ekle); else ekle();
})();
