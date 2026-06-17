# VibeTale Pipeline Test

Bu dizin, VibeTale backend’ini **doğrudan test etmek** için kullanılan bağımsız araçları içerir. Gerçek Flutter uygulamasıyla aynı API endpoint’lerini çağırır, hiçbir mock içermez.

## 1. Web Panel (`index.html`)

Mobil uygulamanın yaptığı her şeyi tarayıcıdan yapabilirsiniz: kitap yükleme, status takip, chunk/ambiance sorgulama, reading session ve stats görüntüleme.

### Çalıştırma

1. Backend’in çalıştığından emin olun:
   ```bash
   uv run python main.py
   ```
2. Bu HTML dosyasını herhangi bir HTTP sunucusuyla açın. En basit yol:
   ```bash
   cd pipeline-test
   python3 -m http.server 3000
   ```
   Sonra tarayıcıdan `http://localhost:3000` açın.
3. **JWT Token** alanına Supabase’den aldığınız auth token’ı yapıştırın (eğer backend auth gerektiriyorsa).
4. **Backend Base URL**’yi `http://localhost:8000` olarak bırakın (router prefix’leri zaten `/books`, `/reading`, `/ambiance`).
5. Bir PDF/EPUB seçip **"Kitap Yükle"** butonuna basın.

### Özellikler

- **Kitap Yükle**: `POST /books/upload` → dosya upload + processing trigger
- **Kütüphane**: `GET /books/` → tüm kitapları listele (paginated: `items`, `total`, `page`)
- **Okuma & Ambiyans**: `GET /books/{id}/chunks`, `GET /ambiance/chunk/{chunkId}`
- **Session & Stats**: `POST /reading/sessions`, `PUT /reading/sessions/{id}`, `GET /reading/stats?period=week`
- **Console**: Tüm API istekleri ve yanıtları anlık loglanır

> Not: Backend’de CORS `allow_origins=["*"]` açık olduğu için tarayıcıdan doğrudan istek atılabilir.

---

## 2. CLI Script (`test_pipeline.py`)

Terminalden tek komutla uçtan uca pipeline testi çalıştırır. Gerçek provider’ları (Gemini, StableAudio, Clipdrop) kullanır.

### Çalıştırma

```bash
uv run python pipeline-test/test_pipeline.py /path/to/kitap.pdf --title "Kitap Adı" --author "Yazar"
```

### Yaptıkları

1. Dosyayı Supabase Storage’a yükler
2. DB’ye kitap kaydı oluşturur
3. `BookProcessingService.process_book()` çalıştırır (extraction → audit → split → analyze → media)
4. Her adımı ekrana loglar
5. Sonuçları doğrular: chapters, chunks, media_assets, cover_url, total_pages
6. Reading session oluşturur ve stats endpoint’ini test eder

---

## 3. Pipeline Akışı (Adım Adım)

Bir dosya yüklendiğinde backend’in yaptığı **tüm** işlemler:

### 3.1 Upload Aşaması (Sync — API tarafında)

| # | Adım | Açıklama | Endpoint / Çağrı |
|---|------|----------|------------------|
| 1 | **Dosya alımı** | Frontend’ten `multipart/form-data` ile gelir | `POST /books/upload` |
| 2 | **Validasyon** | MIME type, uzantı (.pdf/.epub), boyut limiti kontrolü | `FileValidator.validate_upload()` |
| 3 | **Storage upload** | Dosya Supabase Storage bucket’ına yüklenir, public URL alınır | `StorageService.upload_file()` |
| 4 | **Book kaydı** | `books` tablosuna `PENDING` durumuyla kayıt atılır (`total_pages`, `cover_url` boş) | `BookRepository.create()` |
| 5 | **Celery trigger** | Asenkron işlem başlatılır (`process_book_async.delay(...)`) | Celery task |

### 3.2 Processing Aşaması (Async — Celery / arka planda)

| # | Adım | Açıklama | Kullanılan Provider / Servis |
|---|------|----------|-------------------------------|
| 6 | **Text extraction** | PDF/EPUB → ham metin çıkarılır | `PyMuPDF` (PDF) / `ebooklib` (EPUB) |
| 7 | **total_pages hesaplama** | Kelime sayısı / 250 → `total_pages` DB’ye yazılır | BookRepository.update() |
| 8 | **Content audit** *(opsiyonel)* | LLM ile copyright & ethics tarama; `audit_result` alanı doldurulur | `GeminiProvider.check_copyright()` |
| 9 | **Chapter splitting** | Metin bölüm başlıklarına göre `chapters` tablosuna ayrılır | Regex + LLM |
| 10 | **Semantic chunking** | Her chapter paragraflara bölünür, LLM ile sahne sınırları tespit edilir | `GeminiProvider.detect_scene_boundaries()` |
| 11 | **Chunk kaydı** | Her chunk `text_chunks` tablosuna `sequence`, `chapter_id` ile kaydedilir | `TextChunkRepository.create()` |

### 3.3 Medya Üretimi (Her chunk için tekrarlanır)

| # | Adım | Açıklama | Kullanılan Provider |
|---|------|----------|-------------------|
| 12 | **Scene analysis** | Chunk metni analiz edilir: `scene`, `emotion`, `sfx_prompt`, `image_prompt` üretilir | `GeminiProvider.analyze_scene()` |
| 13 | **Audio generation** | `sfx_prompt` + `negative_prompt` → ses dosyası üretilir | `StableAudioProvider.generate_audio()` |
| 14 | **Image generation** | `image_prompt` → görsel üretilir | `ClipdropProvider.generate_image()` |
| 15 | **media_assets kaydı** | Üretilen her medya `media_assets` tablosuna kaydedilir | `MediaAssetRepository.create()` |
| 16 | **Chunk güncelleme** | Chunk satırına `audio_url`, `image_url`, `scene`, `emotion`, `analyzed=true` yazılır | `TextChunkRepository.update()` |
| 17 | **Cover generation** | Kitap başlığı + yazar → kapak görseli; `cover_url` DB’ye yazılır | `ClipdropProvider.generate_image()` |

### 3.4 Tamamlanma

| # | Adım | Açıklama |
|---|------|----------|
| 18 | **Status güncelleme** | `books.processing_status` → `COMPLETED` (veya `FAILED`) |
| 19 | **Temp dosya temizliği** | `/tmp/` altındaki geçici dosyalar silinir |

### 3.5 Okuma Aşaması (Frontend → API)

| # | Adım | Açıklama | Endpoint |
|---|------|----------|----------|
| 20 | **Chunk listesi** | Kitaba ait tüm chunk’lar sıralı getirilir | `GET /books/{id}/chunks` |
| 21 | **Ambiyans verisi** | Chunk’un `audio_url`, `image_url`, `scene`, `emotion` bilgisi | `GET /ambiance/chunk/{id}` |
| 22 | **Session başlat** | Okuma oturumu oluşturulur, `started_at` yazılır | `POST /reading/sessions` |
| 23 | **Session bitir** | `ended_at`, `duration_seconds`, `immersive_mode_seconds` güncellenir | `PUT /reading/sessions/{id}` |
| 24 | **Progress kaydet** | `current_chunk_id`, `chapter_number`, `offset` + `last_read_date` güncellenir | `POST /reading/progress` |
| 25 | **Stats oku** | Toplam süre, immersive süre, session sayısı, günlük grafik verisi | `GET /reading/stats?period=week` |

---

## Gereksinimler

- `.env` dosyası proje kökünde olmalı (Supabase URL, service key, API key’ler)
- `uv` ortamı aktif olmalı
- Eğer Stable Audio kullanılacaksa GPU + `torch` kurulu olmalı
