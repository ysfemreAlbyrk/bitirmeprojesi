-- VibeTale — social/reading features
-- Adds book metadata, user profile fields, and a per-user library relation
-- (reading status + favorites) powering the Library tabs, Discovery, Stats,
-- Leaderboard and Achievements.

-- ── Book metadata ────────────────────────────────────────────────────────────
ALTER TABLE books ADD COLUMN IF NOT EXISTS genre VARCHAR(100);
ALTER TABLE books ADD COLUMN IF NOT EXISTS description TEXT;
ALTER TABLE books ADD COLUMN IF NOT EXISTS rating NUMERIC(2,1);
ALTER TABLE books ADD COLUMN IF NOT EXISTS is_public BOOLEAN DEFAULT FALSE;
ALTER TABLE books ADD COLUMN IF NOT EXISTS read_count INTEGER DEFAULT 0;

CREATE INDEX IF NOT EXISTS idx_books_is_public ON books(is_public);
CREATE INDEX IF NOT EXISTS idx_books_genre ON books(genre);

-- ── User profile fields ──────────────────────────────────────────────────────
ALTER TABLE users ADD COLUMN IF NOT EXISTS avatar_url TEXT;
-- Visible on the public leaderboard. Defaults to true.
ALTER TABLE users ADD COLUMN IF NOT EXISTS is_public BOOLEAN DEFAULT TRUE;

-- ── Per-user library (reading status + favorites) ────────────────────────────
-- Represents a user's relationship with a book without changing book ownership:
-- the uploader owns the book; any user can add a public book to their library.
CREATE TABLE IF NOT EXISTS user_library (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    book_id UUID NOT NULL REFERENCES books(id) ON DELETE CASCADE,
    reading_status VARCHAR(20) NOT NULL DEFAULT 'reading'
        CHECK (reading_status IN ('not_started', 'reading', 'completed')),
    is_favorite BOOLEAN NOT NULL DEFAULT FALSE,
    added_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, book_id)
);

CREATE INDEX IF NOT EXISTS idx_user_library_user ON user_library(user_id);
CREATE INDEX IF NOT EXISTS idx_user_library_book ON user_library(book_id);
CREATE INDEX IF NOT EXISTS idx_user_library_status ON user_library(user_id, reading_status);

ALTER TABLE user_library ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users manage own library" ON user_library
    FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

-- ── Backfill: give existing owners a library entry for their own books ───────
INSERT INTO user_library (user_id, book_id, reading_status)
SELECT user_id, id, 'reading' FROM books
ON CONFLICT (user_id, book_id) DO NOTHING;

-- ── Grants (service_role + anon, local Supabase compatibility) ───────────────
GRANT ALL PRIVILEGES ON TABLE user_library TO service_role;
GRANT ALL PRIVILEGES ON TABLE user_library TO anon;
