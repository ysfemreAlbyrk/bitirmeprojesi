# Supabase Cloud Setup — VibeTale

VibeTale uses **Supabase Cloud** for the database and file storage. No Docker or local services required.

## İlk Kurulum

### 1 — Proje Oluştur

1. [app.supabase.com](https://app.supabase.com) adresine git
2. **New Project** → isim: `vibetale`, şifre seç, bölge: `eu-central-1` (Frankfurt)
3. Proje oluşturulana kadar bekle (~1-2 dakika)

### 2 — API Anahtarlarını Al

**Project → Settings → API** sayfasından:

| Değişken | Kaynak |
|---|---|
| `SUPABASE_URL` | Project URL |
| `SUPABASE_KEY` | `anon` `public` anahtarı |
| `SUPABASE_SERVICE_KEY` | `service_role` `secret` anahtarı |

`.env` dosyasını güncelle:

```env
SUPABASE_URL=https://xxxxxxxxxxxx.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5...
SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5...
```

### 3 — Veritabanı Şemasını Uygula

**Project → SQL Editor → New query** açıp `supabase/migrations/001_initial_schema.sql` dosyasının içeriğini yapıştır ve çalıştır.

Bu işlem şunları oluşturur:
- `users`, `books`, `chapters`, `text_chunks`
- `reading_sessions`, `reading_progress`, `bookmarks`, `media_assets`
- RLS politikaları
- `media-assets` storage bucket

### 4 — Storage Bucket Doğrula

**Project → Storage** sayfasında `media-assets` bucket'ın oluştuğunu kontrol et.

Görünmüyorsa SQL Editor'de manuel olarak çalıştır:

```sql
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
    'media-assets', 'media-assets', true, 52428800,
    ARRAY['audio/wav', 'audio/mpeg', 'image/jpeg', 'image/png', 'image/webp']
)
ON CONFLICT (id) DO NOTHING;
```

### 5 — FastAPI'yi Başlat

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Sağlık kontrolü: `http://localhost:8000/health`

## Bağlantı Bilgileri

FastAPI, Supabase'e şu şekilde bağlanır:

```python
# config.py otomatik olarak .env'den okur
SUPABASE_URL  = "https://xxxx.supabase.co"   # PostgREST + Auth + Storage
SUPABASE_KEY  = "<anon key>"                  # Kullanıcı istekleri
SUPABASE_SERVICE_KEY = "<service_role key>"   # Backend/admin işlemleri
```

## Yeni Geliştirici Kurulumu

1. Repoyu klonla
2. `pip install -r requirements.txt`
3. `.env` dosyasını oluştur ve Supabase Cloud bilgilerini doldur
4. `uvicorn main:app --port 8000 --reload`

## Troubleshooting

**`Invalid API key` hatası**  
→ `.env` içindeki `SUPABASE_KEY` veya `SUPABASE_SERVICE_KEY` yanlış. Dashboard'dan yeniden kopyala.

**`relation "public.users" does not exist`**  
→ SQL migration henüz çalıştırılmamış. Adım 3'ü tekrarla.

**`Bucket not found: media-assets`**  
→ Storage bucket oluşturulmamış. Adım 4'teki SQL'i çalıştır.

**RLS politikaları erişimi engelliyor**  
→ Backend'den yapılan admin işlemleri için `SUPABASE_KEY` yerine `SUPABASE_SERVICE_KEY` kullan (service role RLS'yi atlar).
