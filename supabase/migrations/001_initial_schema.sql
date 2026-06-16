-- VibeTale Database Schema
-- Initial schema for Supabase PostgreSQL

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Users table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    display_name VARCHAR(255) NOT NULL,
    preferences JSONB DEFAULT '{"ambient_intensity": 0.7, "theme": "dark", "language": "tr", "auto_play_audio": true}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_active TIMESTAMP WITH TIME ZONE
);

-- Books table
CREATE TABLE books (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(500) NOT NULL,
    author VARCHAR(255) NOT NULL,
    format VARCHAR(10) NOT NULL CHECK (format IN ('epub', 'pdf', 'txt', 'docx')),
    file_size INTEGER NOT NULL,
    file_url TEXT NOT NULL,
    upload_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    processing_status VARCHAR(20) DEFAULT 'pending' CHECK (processing_status IN ('pending', 'processing', 'completed', 'failed')),
    audit_result VARCHAR(30) CHECK (audit_result IN ('approved', 'copyright_suspicious', 'ethics_violation', 'audit_failed')),
    total_pages INTEGER,
    cover_url TEXT,
    last_read_date TIMESTAMP WITH TIME ZONE
);

-- Chapters table
CREATE TABLE chapters (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    book_id UUID NOT NULL REFERENCES books(id) ON DELETE CASCADE,
    chapter_number INTEGER NOT NULL,
    title VARCHAR(500) NOT NULL,
    start_page INTEGER,
    end_page INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(book_id, chapter_number)
);

-- Text chunks table
CREATE TABLE text_chunks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    book_id UUID NOT NULL REFERENCES books(id) ON DELETE CASCADE,
    chapter_id UUID NOT NULL REFERENCES chapters(id) ON DELETE CASCADE,
    "order" INTEGER NOT NULL,
    text TEXT NOT NULL,
    scene TEXT,
    emotion TEXT,
    sfx_prompt TEXT,
    image_prompt TEXT,
    audio_url TEXT,
    image_url TEXT,
    word_count INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    analyzed BOOLEAN DEFAULT FALSE
);

-- Reading sessions table
CREATE TABLE reading_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    book_id UUID NOT NULL REFERENCES books(id) ON DELETE CASCADE,
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    ended_at TIMESTAMP WITH TIME ZONE,
    duration_seconds INTEGER,
    immersive_mode_seconds INTEGER
);

-- Reading progress table
CREATE TABLE reading_progress (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    book_id UUID NOT NULL REFERENCES books(id) ON DELETE CASCADE,
    current_chunk_id UUID REFERENCES text_chunks(id) ON DELETE SET NULL,
    chapter_number INTEGER NOT NULL,
    "offset" INTEGER NOT NULL,
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, book_id)
);

-- Bookmarks table
CREATE TABLE bookmarks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    book_id UUID NOT NULL REFERENCES books(id) ON DELETE CASCADE,
    chunk_id UUID NOT NULL REFERENCES text_chunks(id),
    chapter_number INTEGER NOT NULL,
    "offset" INTEGER NOT NULL,
    note TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Media assets table (for tracking generated files)
CREATE TABLE media_assets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    chunk_id UUID NOT NULL REFERENCES text_chunks(id) ON DELETE CASCADE,
    asset_type VARCHAR(10) NOT NULL CHECK (asset_type IN ('audio', 'image')),
    storage_url TEXT NOT NULL,
    file_size INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for better query performance
CREATE INDEX idx_books_user_id ON books(user_id);
CREATE INDEX idx_books_processing_status ON books(processing_status);
CREATE INDEX idx_chapters_book_id ON chapters(book_id);
CREATE INDEX idx_text_chunks_book_id ON text_chunks(book_id);
CREATE INDEX idx_text_chunks_chapter_id ON text_chunks(chapter_id);
CREATE INDEX idx_reading_progress_user_book ON reading_progress(user_id, book_id);
CREATE INDEX idx_bookmarks_user_book ON bookmarks(user_id, book_id);
CREATE INDEX idx_media_assets_chunk_id ON media_assets(chunk_id);

-- Row Level Security (RLS) policies
-- Enable RLS on all tables
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE books ENABLE ROW LEVEL SECURITY;
ALTER TABLE chapters ENABLE ROW LEVEL SECURITY;
ALTER TABLE text_chunks ENABLE ROW LEVEL SECURITY;
ALTER TABLE reading_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE reading_progress ENABLE ROW LEVEL SECURITY;
ALTER TABLE bookmarks ENABLE ROW LEVEL SECURITY;
ALTER TABLE media_assets ENABLE ROW LEVEL SECURITY;

-- Users: Users can only see their own data
CREATE POLICY "Users can view own data" ON users
    FOR SELECT USING (auth.uid() = id);

CREATE POLICY "Users can update own data" ON users
    FOR UPDATE USING (auth.uid() = id);

-- Books: Users can only see their own books
CREATE POLICY "Users can view own books" ON books
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own books" ON books
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own books" ON books
    FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own books" ON books
    FOR DELETE USING (auth.uid() = user_id);

-- Reading sessions: Users can only see their own sessions
CREATE POLICY "Users can view own sessions" ON reading_sessions
    FOR SELECT USING (auth.uid() = user_id);

-- Reading progress: Users can only see their own progress
CREATE POLICY "Users can view own progress" ON reading_progress
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can upsert own progress" ON reading_progress
    FOR ALL USING (auth.uid() = user_id);

-- Bookmarks: Users can only see their own bookmarks
CREATE POLICY "Users can view own bookmarks" ON bookmarks
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own bookmarks" ON bookmarks
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete own bookmarks" ON bookmarks
    FOR DELETE USING (auth.uid() = user_id);

-- Chapters: viewable if user can view parent book
CREATE POLICY "Chapters viewable via book" ON chapters
    FOR SELECT USING (
        EXISTS (SELECT 1 FROM books WHERE books.id = chapters.book_id)
    );

CREATE POLICY "Chapters insert via book" ON chapters
    FOR ALL USING (true) WITH CHECK (true);

-- Text chunks: viewable if user can view parent book
CREATE POLICY "Chunks viewable via book" ON text_chunks
    FOR SELECT USING (
        EXISTS (SELECT 1 FROM books WHERE books.id = text_chunks.book_id)
    );

CREATE POLICY "Chunks insert via book" ON text_chunks
    FOR ALL USING (true) WITH CHECK (true);

CREATE POLICY "Chunks update via book" ON text_chunks
    FOR UPDATE USING (true);

-- Media assets: viewable if user can view parent chunk's book
CREATE POLICY "Media assets viewable via chunk" ON media_assets
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM text_chunks
            JOIN books ON books.id = text_chunks.book_id
            WHERE text_chunks.id = media_assets.chunk_id
        )
    );

-- Grant privileges for service_role and anon (local Supabase compatibility)
-- Per-table grants (more reliable than ALL TABLES)
GRANT ALL PRIVILEGES ON TABLE users TO service_role;
GRANT ALL PRIVILEGES ON TABLE books TO service_role;
GRANT ALL PRIVILEGES ON TABLE chapters TO service_role;
GRANT ALL PRIVILEGES ON TABLE text_chunks TO service_role;
GRANT ALL PRIVILEGES ON TABLE reading_sessions TO service_role;
GRANT ALL PRIVILEGES ON TABLE reading_progress TO service_role;
GRANT ALL PRIVILEGES ON TABLE bookmarks TO service_role;
GRANT ALL PRIVILEGES ON TABLE media_assets TO service_role;

-- Default privileges for future tables
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO service_role;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO service_role;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO anon;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO anon;

-- Sync auth.users with public.users on signup (trigger on Supabase managed auth schema)
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.users (id, email, display_name)
    VALUES (
        new.id,
        new.email,
        COALESCE(new.raw_user_meta_data->>'display_name', new.email)
    )
    ON CONFLICT (id) DO NOTHING;
    RETURN new;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW
    EXECUTE FUNCTION public.handle_new_user();

-- Storage bucket (for lokal Supabase)
INSERT INTO storage.buckets (id, name, public, avif_autodetection, file_size_limit, allowed_mime_types)
VALUES ('media-assets', 'media-assets', true, false, 52428800, ARRAY['audio/wav', 'audio/mpeg', 'image/png', 'image/jpeg', 'image/webp', 'application/epub+zip', 'application/pdf'])
ON CONFLICT (id) DO NOTHING;

