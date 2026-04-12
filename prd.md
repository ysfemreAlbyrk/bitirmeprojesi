# VibeTale — Backend Project Brief

## Genel Bakış

VibeTale, e-kitap okuma deneyimini sürükleyici hale getirmek için geliştirilmiş bir mobil uygulamadır. Kullanıcı bir kitap yüklediğinde sistem arka planda kitabın tüm metnini analiz eder; metni anlamlı sahnelere böler, her sahne için duygusal ton ve atmosfer çıkarır, ardından ortam sesi ve sahne görseli üretir. Üretilen tüm medya içerikleri veritabanına kaydedilir. Kullanıcı kitabı okurken bu içerikler sunucudan indirilerek okuma ekranına senkronize biçimde yansıtılır.

Bu doküman, uygulamanın **backend ve yapay zeka entegrasyon katmanını** kapsamaktadır. Mobil uygulama (Flutter) ayrı bir ekip üyesi tarafından geliştirilmektedir. Bu dokümanda anlatılan tüm bileşenler backend geliştirici tarafından yapılacaktır.

---

## Sistem Mimarisine Genel Bakış

Sistem beş ana katmandan oluşmaktadır:

**Mobil İstemci (Flutter)** — Kullanıcı arayüzünü sunar, kitap yükleme işlemlerini başlatır, okuma oturumlarını yönetir ve sunucudan gelen ambiyans verilerini (ses/görsel) senkronize biçimde oynatır. Bu katman bu dokümanda ele alınmamaktadır.

**FastAPI Backend** — Tüm iş mantığının merkezi. Mobil istemciden gelen istekleri karşılar, yapay zeka bileşenlerini orkestre eder, üretilen içerikleri veritabanına kaydeder ve istemciye URL döner.

**Gemini API (Google) veya Lokal model(ollama)** — Metin analizi, sahne çıkarımı ve prompt üretimi için kullanılır. Metin segmentleri bu servise gönderilir; servis sahne türünü, duygusal tonu, ses üretim prompt'unu ve görsel üretim prompt'unu JSON formatında döner.

**MMAudio (Lokal Model)** — Ortam sesi üretimi için kullanılan lokal yapay zeka modeli. WSL2 üzerinde RTX 4060 GPU ile çalışmaktadır. Gemini'den gelen ses prompt'unu alarak WAV formatında ortam sesi üretir.

**Image Generation (Lokal Model)** — Sahne görseli üretimi için kullanılan lokal yapay zeka modeli. Gemini'den gelen görsel prompt'unu alarak sahneye uygun bir arka plan görseli üretir.

**Supabase (Lokal, Docker)** — Kullanıcı verileri, kitap metadata'sı, okuma ilerleme bilgisi ve üretilen medya varlıklarının URL'lerini saklayan veritabanı ve object storage katmanı. Supabase Docker üzerinde lokal olarak çalıştırılacaktır.

---

## Geliştirme Ortamı

- **İşletim Sistemi:** WSL2 (Ubuntu), Windows üzerinde çalışıyor
- **GPU:** NVIDIA RTX 4060 (8GB VRAM), CUDA destekli
- **MMAudio:** Halihazırda kurulu ve çalışır durumda. `~/mm/MMAudio` dizininde bulunuyor. `demo.py` üzerinden CLI ile çalıştırılabiliyor.
- **Image Generation Modeli:** Henüz seçilmedi, lightweight bir model kullanılacak (SDXL-Turbo veya benzeri), Veya API üzerinden external olarak çağrılabilir.m
- **Veritabanı:** Supabase, Docker container içinde lokal olarak çalıştırılıyor. PostgreSQL + Object Storage içeriyor.
- **Depolama:** Üretilen ses ve görsel dosyaları Supabase Object Storage'a kaydedilecek, URL olarak servis edilecek

---

## Kitap İşleme ve Medya Üretim Akışı

Bu akış, kullanıcının kitabı yüklediği anda arka planda tetiklenir. Okuma sırasında değil, yükleme sonrasında çalışır. Üretilen tüm içerikler veritabanına kaydedilir ve kullanıcı okumaya başladığında hazır bekler.

### Adım 1: Kitap Yükleme ve Ön İşleme

Kullanıcı mobil uygulamadan EPUB veya PDF formatında bir kitap yükler. Backend dosyayı alır, format ve boyut doğrulaması yapar ve Supabase Object Storage'a kaydeder. Ardından dosyanın içeriğini düz metne dönüştürür. Bu dönüştürme işlemi EPUB için bölüm yapısını, PDF için sayfa düzenini koruyacak biçimde yapılmalıdır.

### Adım 2: Telif ve Etik Denetim

Yüklenen kitabın içeriği otomatik olarak denetlenir. Denetim iki katmandan oluşur: telif ve lisans uygunluk kontrolü ile etik içerik kontrolü (nefret söylemi, şiddet vb.). Denetim sonucu kitap kaydına işlenir. Uygunsuz içerik tespit edilirse kitap kütüphaneye eklenmez ve kullanıcıya gerekçeli bildirim yapılır. Bu denetim, kitabın sisteme girişini kapsayan bir kapı katmanıdır.

### Adım 3: Metin Segmentasyonu (SemanticSplitter)

Düz metne dönüştürülmüş kitap içeriği anlamlı sahnelere bölünür. Bu bölme işlemi kelime sayısına göre değil, anlam ve atmosfer sürekliliğine göre yapılır. Her segment (TextChunk), mekân, zaman ve olay örgüsü bakımından tutarlı bir alt bölümü temsil eder. Segmentler veritabanında kitap kaydıyla ilişkilendirilmiş TextChunk nesneleri olarak saklanır. Bir kitap Chapter (bölüm) yapısına ayrılır, her Chapter birden fazla TextChunk içerir.

### Adım 4: Sahne Analizi ve Prompt Üretimi (Gemini API)

Her TextChunk Gemini API'ye gönderilir. Gemini her segment için aşağıdaki alanları içeren bir JSON üretir:

- `scene`: Sahnenin kısa İngilizce tanımı (örneğin "dark forest at night", "medieval tavern")
- `emotion`: Sahnenin duygusal tonu (örneğin "tense, mysterious", "warm, cozy")
- `sfx_prompt`: MMAudio için hazırlanmış ortam sesi prompt'u
- `image_prompt`: Görsel üretim modeli için hazırlanmış prompt

Gemini'ye verilen sistem talimatı MMAudio'nun kısıtlamalarını açıkça içermelidir. MMAudio insan konuşması içeren sahnelerde tutarsız sonuçlar üretir, müzik üretimi için eğitilmemiştir ve çok spesifik mekanik sesleri tanımayabilir. Bu nedenle sfx_prompt yalnızca doğa sesleri, ortam gürültüleri ve genel fiziksel sesler içermelidir.

### Adım 5: Ortam Sesi Üretimi (MMAudio)

Her segment için Gemini'den gelen sfx_prompt, MMAudio modeline gönderilir. Model 8 saniyelik WAV formatında ortam sesi üretir. Daha uzun süreler gerektiğinde birden fazla segment üretilip crossfade ile birleştirilir. Üretim parametreleri olarak `num_steps=50` ve gürültüyü azaltmak için `negative_prompt="music, speech, noise, distortion"` kullanılır. Üretilen dosya Supabase Object Storage'a kaydedilir ve URL'i ilgili TextChunk kaydına işlenir.

### Adım 6: Görsel Üretimi (Image Generation)

Her segment için Gemini'den gelen image_prompt, lokal image generation modeline gönderilir. Model 512x512 veya 768x768 çözünürlüğünde bir sahne görseli üretir. Üretilen görsel Supabase Object Storage'a kaydedilir ve URL'i ilgili TextChunk kaydına işlenir.

### Adım 7: Medya Varlıklarının Veritabanına Kaydedilmesi

Her TextChunk için üretilen ses URL'i ve görsel URL'i veritabanında ilgili TextChunk kaydına bağlanır. Böylece kullanıcı okumaya başladığında mobil uygulama hangi segmentte hangi ses ve görsel URL'inin kullanılacağını doğrudan veritabanından sorgulayabilir.

---

## Okuma Sırasındaki Veri Akışı

Yukarıdaki işlem akışı kitap yükleme sırasında tamamlanmış ve tüm medya varlıkları veritabanına kaydedilmiş olur. Kullanıcı okumaya başladığında:

1. Mobil uygulama, kullanıcının bulunduğu TextChunk bilgisini backend'e iletir.
2. Backend ilgili TextChunk'ın ses URL'ini ve görsel URL'ini veritabanından çeker ve döner.
3. Mobil uygulama bu URL'lerden içerikleri indirir ve okuma ekranında oynatır.
4. Kullanıcı ilerledikçe bir sonraki segment için aynı sorgu tekrarlanır.

Bu yaklaşım sayesinde okuma sırasında gerçek zamanlı AI işlemi yapılmaz; tüm yük kitap yükleme aşamasına taşınmış olur.

---

## Backend Bileşenleri ve Sorumlulukları

### 1. FastAPI Ana Sunucu

Tüm endpoint'leri barındıran ana uygulama. Aşağıdaki endpoint gruplarını içermelidir:

**Kitap Yükleme Endpoint'i**
Mobil istemciden gelen EPUB/PDF dosyasını alır, format ve boyut doğrulaması yapar, Supabase Storage'a yükler, metne dönüştürür ve kitap işleme pipeline'ını tetikler.

**Kitap İşleme Pipeline Endpoint'i**
Yüklenen kitabı segmentlere böler, her segment için Gemini analizi yapar, ses ve görsel üretir, tüm URL'leri veritabanına kaydeder. Bu işlem arka planda çalışır; işlem durumu (pending, processing, completed, failed) ayrı bir endpoint üzerinden sorgulanabilir.

**Kütüphane Endpoint'leri**
Kullanıcının kütüphanesindeki kitapları listeleme, kitap detaylarını getirme, kitap silme ve arama işlemleri.

**Okuma Oturumu Endpoint'leri**
Okuma oturumu (session) başlatma, aktif segmentin ses ve görsel URL'lerini getirme, okuma ilerlemesini kaydetme ve senkronize etme.

**Ambiyans Verisi Endpoint'i**
Verilen TextChunk ID'si için ses URL'i ve görsel URL'ini döner. Mobil uygulama bu endpoint'i kullanarak okuma sırasında ilgili medya içeriklerini çeker.

---

### 2. Kitap Yükleme ve Kütüphane Yönetimi

Kullanıcılar EPUB veya PDF formatındaki kitaplarını sisteme yükleyebilir. Backend dosya formatını ve boyutunu doğrular, dosyayı Supabase Object Storage'a kaydeder ve kitabın metadata bilgilerini (başlık, yazar, sayfa sayısı, format) veritabanına yazar. Kütüphane yönetimi; kitap listeleme, arama, filtreleme, kitap detayı görüntüleme ve silme işlemlerini kapsar. Kitap silindiğinde ilişkili tüm medya varlıkları (ses dosyaları, görseller) ve TextChunk kayıtları da temizlenir.

---

### 3. Telif ve Etik Denetim

Yüklenen her kitap için otomatik denetim süreci tetiklenir. Denetim iki bağımsız servise ayrılmıştır:

**CopyrightService:** Kitap metninden örnek pasajlar alarak telif ve lisans uygunluğunu sorgular. LLM tabanlı bir değerlendirme kullanılabilir.

**EthicsChecker:** Metni hassas kavramlar (nefret söylemi, şiddet, müstehcen içerik) açısından tarar.

Her iki denetim paralel olarak çalışır. Denetim sonucu kitap kaydına "uygun", "telif şüpheli" veya "etik dışı içerik" olarak işlenir. Olumsuz sonuçta kitap kütüphaneye eklenmez ve kullanıcıya açıklayıcı bildirim yapılır. Denetim servisi geçici olarak yanıt vermezse işlem "tamamlanamadı" olarak işaretlenir ve yeniden deneme mekanizması devreye girer.

---

### 4. Metin Segmentasyonu (SemanticSplitter)

Kitap metni anlamlı sahnelere bölünür. Segmentasyon mekanik (kelime/cümle sayısı) değil, anlamsal bağlam odaklıdır. Her TextChunk; mekân, zaman dilimi, duygusal atmosfer ve olay örgüsü bakımından iç tutarlılığa sahip bir birim olmalıdır. Segmentasyon için Gemini API veya başka bir LLM kullanılabilir. Her TextChunk veritabanında sıra numarası (order), ait olduğu Chapter ve kitap bilgisiyle birlikte saklanır.

---

### 5. Gemini API Entegrasyonu

Google Gemini API ücretsiz katmanı kullanılacak. Her TextChunk bu servise gönderilir ve sahne/duygu analizi ile üretim prompt'ları alınır. Gemini'ye gönderilen sistem talimatı MMAudio'nun bilinen kısıtlamalarını açıkça içermeli, yalnızca doğa sesleri ve ortam gürültüleri içeren prompt'lar üretilmesi sağlanmalıdır. Gemini API'nin ücretsiz katman rate limitine dikkat edilmeli; gerekirse basit bir önbellekleme mekanizması ile aynı metin tekrar analiz edilmemelidir.

---

!ATTENTION!

### 6. Soyutlama Katmanı (AIProvider Arayüzü)

Metin analizi, ses üretimi ve görsel üretimi bileşenlerinin her biri soyut bir arayüz arkasında tanımlanmalıdır. Bu sayede lokal model ile bulut API arasında geçiş yapmak, yeni bir model entegre etmek veya mevcut bir modeli değiştirmek sistemin geri kalanını etkilemez. Üç ayrı soyutlama tanımlanmalıdır:

**LLMProvider:** Mevcut implementasyon: Gemini API. ancak isteğe bağlı ollama veya başka bir LLM servisi ile de kullanılabilir.

**AudioGenerationProvider:** sfx_prompt alır, üretilen ses dosyasının yolunu döner. Mevcut implementasyon: MMAudio (lokal).

**ImageGenerationProvider:** image_prompt alır, üretilen görsel dosyasının yolunu döner. Mevcut implementasyon: Lokal lightweight model (SDXL-Turbo veya benzeri).

Her provider bağımsız olarak test edilebilir ve değiştirilebilir olmalıdır.

---

### 7. MMAudio Entegrasyonu

MMAudio halihazırda kurulu ve CLI üzerinden çalışır durumda. Backend bu modeli doğrudan Python modülü olarak import ederek kullanmalıdır. Subprocess yaklaşımı her istekte model yeniden yükleneceğinden performanssızdır; model bir kez belleğe alınmalı ve sonraki istekler için hazır bekletilmelidir.

**Üretim parametreleri:** `num_steps=50`, `negative_prompt="music, speech, noise, distortion"`, `duration=8`. Daha uzun süreler için birden fazla 8 saniyelik segment üretilip crossfade ile birleştirilir.

---

### 8. Image Generation Entegrasyonu

Sahne görseli üretimi için lokal bir model kullanılacak. RTX 4060'ın 8GB VRAM sınırına uygun, hızlı çıkarım yapabilen lightweight bir model tercih edilmeli. Gereksinimler: 512x512 veya 768x768 çözünürlük, tercihen 10 saniyenin altında üretim süresi.

---

### 9. Okuma İlerleme Takibi

Kullanıcının okuma ilerlemesi ReadingSession ve ReadingProgress modelleri ile takip edilir. Her okuma oturumunda aktif TextChunk, bölüm numarası ve offset bilgisi tutulur. Kullanıcı uygulamayı kapattığında veya cihaz değiştirdiğinde kaldığı yerden devam edebilmesi için ilerleme Supabase üzerinde senkronize edilir. Yer imi (Bookmark) ekleme, listeleme ve yer iminden konuma gitme de bu modülün kapsamındadır. Kullanıcının günlük/haftalık okuma süresi ve immersif modda geçirdiği süre istatistik olarak saklanır.

---

## Veritabanı Şeması (Özet)

Supabase PostgreSQL üzerinde aşağıdaki ana tablolar yer alacaktır:

**users:** Kullanıcı hesap bilgileri ve profil tercihleri (ambiyans yoğunluğu, tema, dil vb.)

**books:** Kitap metadata bilgileri (başlık, yazar, format, boyut, yükleme tarihi, denetim sonucu, işlem durumu)

**chapters:** Kitabın bölüm yapısı, sıra numarası ve kitap referansı

**text_chunks:** Her segmentin metni, sıra numarası, ait olduğu chapter, sahne bilgisi, duygusal ton, ses URL'i ve görsel URL'i

**reading_sessions:** Kullanıcı-kitap çifti için okuma oturumu bilgisi, başlangıç/bitiş zamanı

**reading_progress:** Aktif TextChunk, bölüm numarası, offset, son güncelleme zamanı

**bookmarks:** Kullanıcının eklediği yer imleri, konum bilgisi ve not

**media_assets:** Üretilen ses ve görsel dosyalarının Supabase Storage URL'leri ve ilişkili TextChunk referansları

---

## API Kontratı (Mobil Uygulama ile Arayüz)

Mobil geliştirici (Flutter) ile önceden netleştirilmesi gereken temel endpoint formatları:

**Kitap yükleme isteği:** Dosya (multipart), kullanıcı ID'si

**İşlem durumu sorgusu:** Kitap ID'si → işlem durumu (pending, processing, completed, failed), tamamlanan segment sayısı

**Kütüphane listesi:** Kullanıcı ID'si → kitap listesi (başlık, kapak, işlem durumu, son okuma tarihi)

**Ambiyans verisi:** TextChunk ID'si → ses URL'i, görsel URL'i, sahne bilgisi, duygusal ton

**İlerleme kaydetme:** Kullanıcı ID'si, kitap ID'si, aktif TextChunk ID'si, offset

**İlerleme getirme:** Kullanıcı ID'si, kitap ID'si → son kaldığı TextChunk ID'si, offset

Hata durumları (model meşgul, üretim başarısız, denetim reddetti vb.) için standart hata kodları ve açıklayıcı mesajlar mobil geliştiriciyle birlikte tanımlanmalıdır.

---

## Kapsam Dışı Konular

- Kullanıcı kimlik doğrulama ve oturum yönetimi (Supabase Auth ileriki aşamaya bırakıldı, şimdilik kullanıcı ID ile çalışılacak)
- Ödeme ve lisans yönetimi
- Arka plan müziği üretimi (vazgeçildi, sadece ortam sesi üretilecek)
- Sosyal özellikler (yorum, paylaşım, arkadaşlık)

---

## Öncelik Sırası

1. Supabase Docker kurulumu ve veritabanı şemasının oluşturulması
2. FastAPI iskeletinin kurulması, temel endpoint yapısı
3. Kitap yükleme, metin dönüştürme ve kütüphane yönetimi
4. Telif ve etik denetim modülü
5. Metin segmentasyonu (SemanticSplitter)
6. Gemini API entegrasyonu ve sahne analizi
7. MMAudio entegrasyonu ve ses üretim endpoint'i
8. Image generation entegrasyonu ve görsel üretim endpoint'i
9. Pipeline'ın uçtan uca bağlanması
10. Okuma ilerleme takibi endpoint'leri

---

## Teknik Notlar

- Supabase lokal Docker kurulumunda Object Storage ve PostgreSQL birlikte çalışır. Üretilen medya dosyaları Object Storage'a yüklenir, URL'ler PostgreSQL'de saklanır.
- Tüm üretilen dosyalar için UUID tabanlı benzersiz isimler kullanılmalı, aynı isimli dosyaların üzerine yazılmasının önüne geçilmelidir.
- Gemini API ücretsiz katmanı rate limit içerir. Aynı TextChunk'ın tekrar analiz edilmemesi için veritabanında analiz durumu takip edilmelidir.
- AIProvider soyutlama katmanı sayesinde Gemini yerine başka bir LLM, MMAudio yerine başka bir ses modeli, Lokal image generation modeli yerine API tabanlı bir model kolayca takılabilir olmalıdır.