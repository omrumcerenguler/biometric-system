# Bitirme Projesi Teknik Dokümantasyonu
## Proje Başlığı: Liveness Detection ile Biyometrik Kimlik Doğrulama

Tarih: 6 Nisan 2026

Bu doküman yalnızca mevcut kod tabanındaki gerçek implementasyona dayanır. Kodda olmayan bir özellik tamamlanmış gibi anlatılmamıştır.

## 1. Proje Özeti

### Ne yapar
- Sistem, çok modlu biyometrik doğrulama sağlar.
- Yüz tanıma, ses doğrulama ve liveness anti-spoof kontrollerini birleştirir.
- Tek backend ile birden fazla istemciyi (portal, bank) destekler.

### Nasıl uygulanmış
1. FastAPI tabanlı backend; enrollment, identify, verify, login ve admin endpointlerini sunar.
2. Enrollment sırasında yüz ve ses şablonları çıkarılır ve veritabanına yazılır.
3. Verify akışında önce yüzle 1:N kimlik tespiti yapılır, sonra bulunan kullanıcıya karşı seste 1:1 doğrulama yapılır.
4. Son karar, yüz ve ses skorlarının ağırlıklı füzyonu ile verilir.

### Nerede
- Uygulama başlangıcı: [backend/app/main.py](backend/app/main.py)
- Kimlik doğrulama rotaları: [backend/app/api/routes_auth.py](backend/app/api/routes_auth.py)
- Enrollment rotaları: [backend/app/api/routes_enrollment.py](backend/app/api/routes_enrollment.py)
- Identify ve liveness rotaları: [backend/app/api/routes_identify.py](backend/app/api/routes_identify.py)
- Ana iş mantığı: [backend/app/services/authentication_service.py](backend/app/services/authentication_service.py)

## 2. Sistem Mimarisi

### Ne yapar
- API, servis, veri katmanı ve istemci katmanları arasında uçtan uca veri akışını tanımlar.

### Nasıl uygulanmış
- Backend tarafı:
1. API katmanı Pydantic ile istek doğrular.
2. Servis katmanı embedding üretir, benzerlik ve eşik kontrollerini yapar.
3. DB katmanı kullanıcı ve biyometrik şablonları tutar.
4. Yardımcı katman base64 görsel/ses verisini çözer.
- Frontend tarafı:
1. Portal ve bank için ayrı klasör yapısı vardır.
2. Kamera/ses yakalama ve API çağrıları JS modülleri ile yönetilir.
3. Oturum bilgisi localStorage üzerinde tutulur.

### Nerede
- Router bağlama ve CORS: [backend/app/main.py](backend/app/main.py)
- Şema modelleri: [backend/app/domain/schemas.py](backend/app/domain/schemas.py)
- ORM modelleri: [backend/app/db/models.py](backend/app/db/models.py)
- Portal istemci: [clients/portal](clients/portal)
- Bank istemci: [clients/bank](clients/bank)

## 3. Multi-Client Mimarisi

### Ne yapar
- Aynı backend üzerinde farklı istemcilerin verisini ayırır.

### Nasıl uygulanmış
1. İstemciler her isteğe X-Client header ekler.
2. Portal X-Client: portal, bank X-Client: bank gönderir.
3. Backend route katmanı bu değeri alır ve servise geçirir.
4. Servis katmanı kullanıcı sorgularını username + client ile filtreler.

### Nerede
- Portal header ekleme: [clients/portal/assets/js/api.js](clients/portal/assets/js/api.js#L31)
- Bank header ekleme: [clients/bank/assets/js/api.js](clients/bank/assets/js/api.js#L31)
- Auth route header okuma: [backend/app/api/routes_auth.py](backend/app/api/routes_auth.py#L27)
- User sorgusu (client filtreli): [backend/app/services/authentication_service.py](backend/app/services/authentication_service.py#L189)

### Mevcut durum notu
- Kod seviyesinde client filtreleme var.
- User tablosunda username+client için DB seviyesinde unique constraint tanımlı değil.

## 4. Authentication ve Authorization (JWT)

### Ne yapar
- Login sonrası JWT üretir, korumalı endpointlerde token doğrular.

### Nasıl uygulanmış
1. Login endpointi kullanıcıyı doğrular.
2. JWT içine sub (username), role ve exp eklenir.
3. Bearer token dependency tokenı çözer, kullanıcıyı DB’den bulur, aktiflik kontrolü yapar.
4. Admin endpointleri require_admin ile role kontrolü uygular.

### Nerede
- JWT üretme/doğrulama: [backend/app/core/security.py](backend/app/core/security.py)
- JWT ayarları: [backend/app/core/config.py](backend/app/core/config.py)
- Login endpoint: [backend/app/api/routes_auth.py](backend/app/api/routes_auth.py#L23)
- Auth dependency: [backend/app/api/dependencies/auth.py](backend/app/api/dependencies/auth.py)
- Admin endpoint: [backend/app/api/routes_admin.py](backend/app/api/routes_admin.py)

### Frontend oturum yönetimi
- accessToken localStorage’a yazılır.
- Sonraki API çağrılarında Authorization header otomatik eklenir.

Nerede:
- Token saklama: [clients/portal/assets/js/portal.js](clients/portal/assets/js/portal.js#L45)
- Header ekleme: [clients/portal/assets/js/api.js](clients/portal/assets/js/api.js#L36)

### Kritik gerçek durum
- Parola doğrulama hash ile değil, düz metin karşılaştırması ile yapılıyor.

## 5. Tam Authentication Akışı

### Ne yapar
- Login’den multimodal verify sonucuna kadar tüm adımları yürütür.

### Nasıl uygulanmış (adım adım)
1. Login:
- Frontend, /auth/login çağırır.
- Backend kullanıcı/parola doğrular, access token döner.

2. Yüz identify (1:N):
- Frontend yüz görselini /identify/ endpointine yollar.
- Backend görseli çözer, kalite kontrollerini ve 1:N karşılaştırmayı yapar.

3. Verify (yüz + ses):
- Frontend /auth/verify ile hem yüz hem ses gönderir.
- Backend tekrar yüzle kullanıcıyı bulur, sonra bu kullanıcıya karşı sesi 1:1 doğrular.
- Füzyon skoru hesaplanır, ACCEPTED veya DENIED döner.

4. Yardımcı liveness endpointleri:
- /identify/pose-check
- /identify/blink-check
- /identify/voice-challenge
- /identify/voice-challenge/validate

### Nerede
- Verify route: [backend/app/api/routes_auth.py](backend/app/api/routes_auth.py#L52)
- Verify servis akışı: [backend/app/services/authentication_service.py](backend/app/services/authentication_service.py#L340)
- Identify route: [backend/app/api/routes_identify.py](backend/app/api/routes_identify.py#L101)

## 6. Veri Temsili ve Depolama

### Ne yapar
- Yüz/ses şablonlarını vektör olarak saklar.

### Nasıl uygulanmış
1. User tablosu: username, client, role, password_hash, is_active.
2. BiometricData tablosu: type, enc_feature_blob, user_id.
3. Embeddingler L2 normalize edilir.
4. float32 diziler bytes’a çevrilip LargeBinary alana yazılır.
5. Okuma sırasında bytes, numpy frombuffer ile tekrar vektöre çevrilir.

### Nerede
- Modeller: [backend/app/db/models.py](backend/app/db/models.py)
- Upsert vektör: [backend/app/services/authentication_service.py](backend/app/services/authentication_service.py#L273)

### Depolama formatı
- Yüz: 512 boyut float32 embedding (InsightFace)
- Ses: 256 boyut float32 embedding (Resemblyzer)
- Saklama: raw float32 bytes

### Ham veri saklanıyor mu
- Normal akışta ham görsel/ses DB’ye kaydedilmiyor.
- Verify içinde debug amaçlı wav dosyası yazımı bulunuyor.

Nerede:
- Debug wav yazımı: [backend/app/services/authentication_service.py](backend/app/services/authentication_service.py#L392)

### Şifreleme durumu
- Şifreleme yardımcı fonksiyonları mevcut.
- Ancak biometrik blob yazımında aktif kullanılmıyor.

Nerede:
- Şifreleme fonksiyonları: [backend/app/core/security.py](backend/app/core/security.py#L7)

## 7. Teknik İşleme Pipeline

### Ne yapar
- Kameradan ve mikrofondan gelen veriyi skorlanabilir biyometrik temsile çevirir.

### Nasıl uygulanmış
Yüz pipeline:
1. Frontend frame’i base64 JPEG üretir.
2. Backend base64 -> OpenCV BGR dönüşümü yapar.
3. InsightFace yüz ve embedding çıkarır.
4. Ek kalite/liveness kontrolleri:
- çoklu yüz kontrolü
- yaw kontrolü
- frontal nose ratio
- göz açık kontrolü (EAR)
- bbox boyutu
- blur skoru
5. Cosine similarity ile eşleşme hesaplanır.

Ses pipeline:
1. Frontend WAV base64 üretir.
2. Backend WAV çözer, mono waveform elde eder.
3. Gerekirse resample, trim ve normalize uygular.
4. Resemblyzer ile ses embedding çıkarır.
5. Kullanıcı şablonuyla cosine benzerlik hesaplar.
6. AASIST spoof skoru ayrıca üretilir.

### Nerede
- Görsel decode: [backend/app/utils/image_io.py](backend/app/utils/image_io.py)
- Ses decode: [backend/app/utils/audio_io.py](backend/app/utils/audio_io.py)
- Face processor: [backend/app/services/face_processor.py](backend/app/services/face_processor.py)
- Voice processor: [backend/app/services/voice_processor.py](backend/app/services/voice_processor.py)
- Eye state: [backend/app/services/eye_state_detector.py](backend/app/services/eye_state_detector.py)

## 8. Kullanılan Modeller ve Kütüphaneler

### Ne yapar
- Biyometrik çıkarım ve API altyapısını sağlar.

### Nasıl uygulanmış
- InsightFace: yüz embedding ve landmark bilgisi.
- MediaPipe FaceMesh: göz açıklığı (EAR) için landmark çıkarımı.
- Resemblyzer: speaker embedding üretimi.
- Torch + AASIST: ses spoof tespiti.
- FastAPI + SQLAlchemy + Pydantic: servis omurgası.

### Nerede
- Face entegrasyon: [backend/app/services/face_processor.py](backend/app/services/face_processor.py)
- Voice embedding entegrasyon: [backend/app/services/voice_processor.py](backend/app/services/voice_processor.py)
- Spoof entegrasyon: [backend/app/services/voice_spoof_detector.py](backend/app/services/voice_spoof_detector.py)
- Bağımlılıklar: [backend/requirements.txt](backend/requirements.txt)

## 9. Liveness Detection

### Ne yapar
- Kullanıcının canlı olup olmadığını yüz davranışı üzerinden kontrol etmeye çalışır.

### Nasıl uygulanmış
Blink:
1. Birden fazla frame alınır.
2. Her frame için EAR hesaplanır.
3. baseline ve min EAR oranı hesaplanır.
4. Düşüş ve tekrar açılma varsa blink geçti kabul edilir.

Pose:
1. required_turn (center/left/right) alınır.
2. nose_x_ratio ile poz sınıflaması yapılır.
3. Gerekirse referans görsel farkı ve minimum delta kontrol edilir.
4. Mutlak sağ/sol eşiklerle zayıf hareketler elenir.

State machine:
1. VISUAL_ID -> TURN_RIGHT -> TURN_LEFT -> BLINK adımlarını içerir.
2. Her adımda timeout/retry kuralları uygulanır.
3. Başarısızlıkta sebep kodu üretir.

### Nerede
- Pose-check: [backend/app/api/routes_identify.py](backend/app/api/routes_identify.py#L215)
- Blink-check: [backend/app/api/routes_identify.py](backend/app/api/routes_identify.py#L422)
- State machine: [backend/app/services/face_liveness_state_machine.py](backend/app/services/face_liveness_state_machine.py)

### Mevcut durum notu
- State machine implementasyonu var.
- Ancak verify içinde zorunlu adım olarak entegre edilmemiş.

## 10. Voice Verification

### Ne yapar
- Konuşan kişinin sesinin, yüzle bulunan kullanıcıya ait olup olmadığını kontrol eder.

### Nasıl uygulanmış
1. Ses dalga formu doğrulanır (mono, finite, minimum süre).
2. Gerekirse hedef örnekleme hızına çevrilir.
3. Sessiz kısımlar trim edilir, normalize edilir.
4. Resemblyzer embedding üretilir.
5. DB’deki kullanıcı voice template’i ile cosine similarity hesaplanır.
6. Eşik altı ise doğrulama reddedilir.

Challenge-response:
1. Dinamik Türkçe challenge üretimi endpointi vardır.
2. Challenge validate endpointi, metin içinde beklenen anahtar kelime/sayı eşleşmesi arar.
3. Bu doğrulama, verify akışında zorunlu kapı olarak otomatik kullanılmıyor.

### Nerede
- Voice processor: [backend/app/services/voice_processor.py](backend/app/services/voice_processor.py)
- Verify voice match: [backend/app/services/authentication_service.py](backend/app/services/authentication_service.py#L422)
- Challenge endpointleri: [backend/app/api/routes_identify.py](backend/app/api/routes_identify.py#L177)

## 11. Spoofing ve Güvenlik

### Ne yapar
- Sesin sahte/oynatım olma olasılığını ölçer.

### Nasıl uygulanmış
1. Spoof detector WAV verisini işler.
2. AASIST ile spoof skoru üretir.
3. spoof_decision sonucu döndürür.
4. Verify yanıtında spoof_score ve spoof_decision taşınır.

### Nerede
- Spoof detector: [backend/app/services/voice_spoof_detector.py](backend/app/services/voice_spoof_detector.py)
- Verify entegrasyonu: [backend/app/services/authentication_service.py](backend/app/services/authentication_service.py#L399)
- Config: [backend/app/core/config.py](backend/app/core/config.py#L31)

### Log vs enforce davranışı
- Config tarafında SPOOF_MODE tanımı var.
- Mevcut verify kararında spoof sonucu bloklayıcı kural olarak kullanılmıyor.
- Pratikte spoof sonucu şu an ağırlıklı olarak skor bilgisi olarak dönüyor.

### Güvenlik gerçekleri
- Parolalar hashsiz.
- Varsayılan SECRET_KEY geliştirme seviyesi.
- Token localStorage’da tutuluyor.
- CORS localhost ile sabit.

## 12. Değerlendirme ve Karar Mantığı

### Ne yapar
- Modality skorlarını ve final kararı üretir.

### Nasıl uygulanmış
1. Face identify başarısızsa süreç deny ile biter.
2. Voice match eşik altındaysa deny döner.
3. Füzyon formülü uygulanır:

$fusion = 0.55 \times face\_score + 0.45 \times voice\_score$

4. Final karar:
- fusion >= FUSION_PASS_THRESHOLD ise ACCEPTED
- değilse DENIED

### Nerede
- Füzyon fonksiyonu: [backend/app/services/fusion.py](backend/app/services/fusion.py)
- Verify karar akışı: [backend/app/services/authentication_service.py](backend/app/services/authentication_service.py#L340)
- Eşikler: [backend/app/core/config.py](backend/app/core/config.py#L11)

## 13. Mevcut Implementasyon Durumu

### Tamamlanmış parçalar
- Face enrollment (çoklu açı)
- Voice enrollment
- Face 1:N identify
- Voice 1:1 verify
- Füzyon kararı
- Multi-client header tabanlı ayrım
- JWT login ve bearer dependency
- Pose-check ve blink-check endpointleri

### Eksik/kararsız parçalar
- Password hashing yok.
- Spoof mode enforce kararına bağlanmamış.
- Liveness state machine verify içinde zorunlu değil.
- Voice challenge doğrulaması verify içinde zorunlu değil.
- Debug wav yazımı production için riskli.
- Test kapsamı sınırlı.

### Nerede
- Test örneği: [backend/app/tests/test_fusion.py](backend/app/tests/test_fusion.py)

## 14. Kısıtlar

### Teknik kısıtlar
- Multi-client ayrımı büyük ölçüde header ve uygulama mantığına bağlı.
- CORS sabit originlerle tanımlı.
- Token dependency kullanıcıyı username ile buluyor, client bağlamı token içinde taşınmıyor.
- Biyometrik blob alanı şifreli isimlendirilse de pratikte raw yazılıyor.
- Challenge üretimi Türkçe odaklı.
- Refresh token akışı yok.
- API ve servis seviyesinde kapsamlı otomatik test az.

### Nerede
- CORS: [backend/app/main.py](backend/app/main.py#L20)
- Token kullanıcı çözümü: [backend/app/api/dependencies/auth.py](backend/app/api/dependencies/auth.py#L28)

## 15. Gelecek İyileştirmeler

Kod mimarisiyle uyumlu ve doğrudan uygulanabilir öneriler:
1. Password hashing (bcrypt/argon2) eklenmesi.
2. SPOOF_MODE enforce dalının verify kararına bağlanması.
3. State machine liveness’in verify içinde zorunlu gate olması.
4. Challenge-response doğrulamasının verify’ye opsiyonel zorunlu adım olarak eklenmesi.
5. FEATURE_ENC_KEY_B64 ile biometrik blob şifrelemenin aktif kullanılması.
6. username+client için DB seviyesinde unique constraint.
7. CORS originlerinin config/env üzerinden yönetimi.
8. Verify içindeki debug dosya yazımının kaldırılması.
9. Endpoint ve servis testlerinin genişletilmesi.
10. Token doğrulama katmanında client bağlamının daha güçlü bağlanması.

## Sonuç

Mevcut proje, bitirme projesi seviyesinde güçlü bir teknik iskelet sunmaktadır: gerçek zamanlı yüz/ses işleme, çok modlu karar mekanizması ve yeniden kullanılabilir servis tasarımı çalışır durumdadır. En büyük ihtiyaç yeni özellik eklemekten çok güvenlik sertleştirmesi ve mevcut liveness/spoof bileşenlerini final karara daha sıkı bağlamaktır.
