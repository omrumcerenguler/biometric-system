# JWT Authentication & Authorization Roadmap

Bu roadmap, mevcut biyometrik sistemi portal odaklı akıştan çıkarıp bağımsız bir authentication service mantığına yaklaştırmak için hazırlanmıştır.

Amaç:

* Sisteme JWT tabanlı kimlik doğrulama eklemek
* Korumalı endpoint’lerde token zorunlu hale getirmek
* Rol bazlı yetkilendirme eklemek
* Portalı sadece bir istemci (client) olarak konumlandırmak
* İlerlemeyi kontrollü ve geri alınabilir şekilde yapmak

Kapsam:

* FastAPI backend
* JWT access token üretimi ve doğrulaması
* Frontend’de token saklama ve gönderme
* Protected endpoint kontrolü
* Role-based authorization
* Temel otomatik testler
* Dokümantasyon güncellemesi

Kapsam dışı (ilk sürüm):

* Refresh token sistemi
* OAuth / SSO entegrasyonu
* Çoklu cihaz oturum yönetimi
* Gelişmiş logout blacklist mekanizması
* Tam client ayrıştırması için ayrı repo yapısı

---

## Genel Kurallar

1. Her adım küçük ve test edilebilir olmalı.
2. Her adım sonunda sistem ayağa kalkmalı.
3. Her adımın net kabul kriteri olmalı.
4. Token mantığı frontend’de dağınık yazılmamalı; merkezi API katmanında yönetilmeli.
5. Role kontrolü backend’de yapılmalı.
6. Portal, sistemin kendisi değil; sistemi kullanan istemcilerden biri olarak düşünülmeli.

---

## Başlangıç Durumu

Tamamlanan hazırlıklar:

* Legacy incelemesi yapıldı
* Kritik legacy çakışma bulunmadı
* API base URL merkezileştirildi
* Frontend API çağrıları `api.js` katmanına toplanmaya başlandı
* Portal login akışı config / api katmanına bağlandı

Not edilen riskler:

* Session bilgileri hâlâ localStorage’da tutuluyor
* Password hashing/doğrulama backend’de ayrıca teyit edilmeli
* `authentication_service.py` içinde backward compatibility amaçlı `face_feature` desteği var

---

# Aşama 1 — JWT Altyapısını Kur

## 1.1 JWT kütüphanesini ekle

Yapılacaklar:

* JWT için kullanılacak kütüphaneyi projeye ekle
* Tercih: `python-jose`

Kabul kriteri:

* Proje JWT encode/decode yapabilecek hale gelmeli

## 1.2 Config alanlarını ekle

Yapılacaklar:

* Secret key
* Algorithm
* Access token expire süresi
* Config üzerinden okunacak şekilde ayarla

Kabul kriteri:

* JWT ayarları kod içine gömülü değil, config üzerinden geliyor olmalı

## 1.3 Token yardımcı fonksiyonlarını yaz

Yapılacaklar:

* Access token oluşturma fonksiyonu
* Token çözümleme / doğrulama fonksiyonu
* Expire alanı ekleme

Kabul kriteri:

* Test amaçlı örnek bir payload ile token üretilebilmeli ve çözülebilmeli

---

# Aşama 2 — Login Endpoint’ini JWT Döndürecek Hale Getir

## 2.1 Login response modelini güncelle

Yapılacaklar:

* `username`, `role` yanına `access_token` ve `token_type` ekle

Kabul kriteri:

* Başarılı login response’u JWT içermeli

## 2.2 Login service güvenliğini doğrula

Yapılacaklar:

* Password doğrulama gerçekten hash verify ile mi yapılıyor kontrol et
* Gerekirse string compare yerine güvenli verify ekle

Kabul kriteri:

* Düz metin şifre karşılaştırması kalmamalı

## 2.3 Login endpoint’ten token üret

Yapılacaklar:

* Login başarılıysa JWT oluştur
* Role ve username bilgisini token içine claim olarak ekle

Kabul kriteri:

* `/auth/login` token döndürmeli
* Hatalı login’de 401 dönmeli

---

# Aşama 3 — Token Doğrulama Katmanını Ekleyin

## 3.1 Current user dependency oluştur

Yapılacaklar:

* Authorization header’dan bearer token oku
* Token’ı doğrula
* Kullanıcı bilgisini çözüp route’a aktar

Kabul kriteri:

* Geçerli token ile kullanıcı context’i üretilebilmeli
* Geçersiz token ile 401 dönmeli

## 3.2 Opsiyonel / yardımcı auth dependency’lerini hazırla

Yapılacaklar:

* `get_current_user`
* `require_admin`
* Gerekirse `require_roles(...)`

Kabul kriteri:

* Endpoint’lerde kolayca uygulanabilir dependency yapısı hazır olmalı

---

# Aşama 4 — Protected Endpoint’leri Belirle ve Koruma Ekle

## 4.1 Endpoint sınıflandırması yap

Sınıflar:

* Public
* Authenticated
* Admin only

Örnek başlangıç kararı:

* `/auth/login` → public
* `/identify/` → authenticated veya tasarıma göre public bırakılabilir (karar verilecek)
* `/enroll/*` → authenticated
* `/admin/*` → admin only
* `/auth/verify` → authenticated veya özel akışa göre ayrıca değerlendirilecek

Kabul kriteri:

* Tüm kritik endpoint’lerin erişim türü netleşmiş olmalı

## 4.2 Protected route’lara dependency ekle

Yapılacaklar:

* Token zorunlu hale getir
* Eksik token → 401
* Geçersiz token → 401

Kabul kriteri:

* Korumalı route’lara tokensız erişim engellenmeli

---

# Aşama 5 — Role-Based Authorization Ekle

## 5.1 Rol kontrolü yap

Yapılacaklar:

* Admin endpoint’lerine sadece admin erişebilsin
* User token ile admin endpoint’e giriş engellensin

Kabul kriteri:

* Yetersiz yetki durumunda 403 dönmeli

## 5.2 Role claim kullanımını standardize et

Yapılacaklar:

* Token içindeki role bilgisi ile backend authorization kontrolü yap
* localStorage’daki role bilgisini güven kaynağı olarak kullanma

Kabul kriteri:

* Yetki kontrolü frontend state’e değil token’a dayanmalı

---

# Aşama 6 — Frontend Token Yönetimini Kur

## 6.1 Login sonrası token sakla

Yapılacaklar:

* Login response’tan access token al
* Uygun şekilde localStorage’da sakla (ilk sürüm için kabul edilebilir)
* Username / role state’ini token response ile senkron tut

Kabul kriteri:

* Login sonrası token frontend’de bulunmalı

## 6.2 API katmanına token header ekle

Yapılacaklar:

* `api.js` içinde merkezi şekilde Authorization header ekle
* UI dosyalarında token logic yazma

Kabul kriteri:

* Korumalı endpoint çağrıları bearer token ile gitmeli

## 6.3 Logout temizliği yap

Yapılacaklar:

* localStorage’daki token ve ilgili session alanlarını temizle

Kabul kriteri:

* Logout sonrası korumalı akışlar kullanılamamalı

---

# Aşama 7 — Smoke Test ve Auth Testleri Ekle

## 7.1 Backend auth testleri

Yapılacaklar:

* Login başarılı senaryo
* Login başarısız senaryo
* Geçersiz token senaryosu
* Tokensız istek senaryosu

Kabul kriteri:

* Temel auth testleri geçmeli

## 7.2 Authorization testleri

Yapılacaklar:

* Admin endpoint’e user token ile erişim → 403
* Admin token ile erişim → 200

Kabul kriteri:

* Yetki kontrolü test ile doğrulanmalı

---

# Aşama 8 — Dokümantasyon Güncelle

## 8.1 API auth dokümantasyonu

Yapılacaklar:

* Login örneği
* Bearer token kullanımı
* Public/protected/admin endpoint listesi
* 401 ve 403 hata davranışları

Kabul kriteri:

* Geliştirici, sistemi entegre etmek için yeterli bilgiye sahip olmalı

## 8.2 Mimari not ekle

Yapılacaklar:

* Sistem bağımsız auth service mantığında konumlandırılsın
* Portalın yalnızca örnek istemci olduğu not edilsin

Kabul kriteri:

* Projenin servis mantığı dokümana yansıtılmış olmalı

---

# Önerilen Uygulama Sırası

1. JWT config ve helper fonksiyonları
2. Login endpoint’ini JWT döndürecek hale getirme
3. Password verify kontrolü
4. Current-user dependency
5. Protected endpoint’lere token zorunluluğu
6. Admin role kontrolü
7. Frontend token saklama
8. API katmanına Authorization header ekleme
9. Logout temizliği
10. Testler
11. Dokümantasyon

---

# Bloklayıcı Kontrol Noktaları

Aşağıdakilerden biri çözülmeden sonraki kritik adıma geçilmemeli:

* Password doğrulama güvenli değilse
* Login token üretmiyorsa
* Protected endpoint tokensız erişilebiliyorsa
* Admin endpoint role kontrolü yapmıyorsa

---

# İlk Sürüm İçin Kabul Edilen Basitleştirmeler

Bu sürümde kabul edilebilir:

* Sadece access token kullanmak
* Refresh token eklememek
* Token’ı localStorage’da tutmak
* Logout’u yalnızca frontend temizliği olarak yapmak

Bu sürümde ertelenebilir:

* Refresh token
* Token blacklist
* Ayrı repo/client ayrıştırması
* Gelişmiş audit ve rate limiting

---

# Bu Roadmap’in Başarı Kriteri

Bu roadmap tamamlandığında sistem:

* Login sonrası JWT üreten
* Protected endpoint’leri token ile koruyan
* Admin endpoint’lerinde rol kontrolü yapan
* Portal dışında başka istemciler tarafından da kullanılabilecek
  bir authentication service temelini kazanmış olmalı.
