-- ============================================================
-- Supabase Schema for India & Gujarat Labour Law Tracker
-- ============================================================
-- Copy and paste this script into your Supabase SQL Editor
-- (https://supabase.com/dashboard/project/_/sql) and click "Run".
-- ============================================================

-- 1. Create Articles Table
CREATE TABLE IF NOT EXISTS public.articles (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    link TEXT NOT NULL UNIQUE,
    source TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT 'Labour Codes',
    state TEXT NOT NULL DEFAULT 'National / Central',
    sector TEXT NOT NULL DEFAULT 'General / All Sectors',
    summary TEXT NOT NULL,
    added_date DATE NOT NULL DEFAULT CURRENT_DATE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Indexing for fast search & filtering
CREATE INDEX IF NOT EXISTS idx_articles_state ON public.articles(state);
CREATE INDEX IF NOT EXISTS idx_articles_category ON public.articles(category);
CREATE INDEX IF NOT EXISTS idx_articles_sector ON public.articles(sector);
CREATE INDEX IF NOT EXISTS idx_articles_added_date ON public.articles(added_date DESC);

-- 2. Create Custom Sources Table
CREATE TABLE IF NOT EXISTS public.custom_sources (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    domain TEXT NOT NULL UNIQUE,
    url TEXT NOT NULL,
    type TEXT DEFAULT 'domain_search',
    query TEXT,
    category TEXT DEFAULT 'Labour Codes',
    state TEXT DEFAULT 'National / Central',
    active BOOLEAN DEFAULT true,
    added_at DATE DEFAULT CURRENT_DATE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 3. Create User Bookmarks Table
CREATE TABLE IF NOT EXISTS public.user_bookmarks (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    article_id TEXT REFERENCES public.articles(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    UNIQUE(user_id, article_id)
);

-- 4. Create Newsletter & Alert Subscribers Table
CREATE TABLE IF NOT EXISTS public.subscribers (
    id BIGSERIAL PRIMARY KEY,
    email TEXT UNIQUE,
    telegram_chat_id TEXT,
    state_preference TEXT DEFAULT 'All',
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- ============================================================
-- Row Level Security (RLS) Policies
-- ============================================================

-- Enable RLS
ALTER TABLE public.articles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.custom_sources ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_bookmarks ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.subscribers ENABLE ROW LEVEL SECURITY;

-- Articles: Allow everyone to read, authenticated users/service role to insert/update
CREATE POLICY "Public articles read access" 
ON public.articles FOR SELECT 
USING (true);

CREATE POLICY "Allow service role or authenticated insert on articles" 
ON public.articles FOR ALL 
USING (true);

-- Custom Sources: Allow public read, authenticated insert/update
CREATE POLICY "Public sources read access" 
ON public.custom_sources FOR SELECT 
USING (true);

CREATE POLICY "Allow public insert on custom_sources" 
ON public.custom_sources FOR ALL 
USING (true);

-- User Bookmarks: Users can read and write only their own bookmarks
CREATE POLICY "Users can manage their own bookmarks" 
ON public.user_bookmarks FOR ALL 
USING (auth.uid() = user_id);

-- Subscribers: Allow insert for subscription
CREATE POLICY "Allow subscriber registration" 
ON public.subscribers FOR INSERT 
WITH CHECK (true);
