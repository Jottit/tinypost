-- Reference only. Migrations are the source of truth.
-- Update this file when writing new migrations.

CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    name TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE sites (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    subdomain TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    bio TEXT,
    avatar TEXT,
    custom_domain TEXT UNIQUE,
    domain_verified_at TIMESTAMPTZ,
    domain_verification_token TEXT,
    design JSONB,
    custom_css TEXT,
    license TEXT,
    social_links JSONB DEFAULT '[]',
    comments_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    menu TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE posts (
    id SERIAL PRIMARY KEY,
    site_id INTEGER NOT NULL REFERENCES sites(id),
    slug TEXT NOT NULL,
    title TEXT,
    body TEXT NOT NULL,
    is_draft BOOLEAN NOT NULL DEFAULT FALSE,
    published_at TIMESTAMPTZ,
    sent_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(site_id, slug)
);

CREATE TABLE pages (
    id SERIAL PRIMARY KEY,
    site_id INTEGER NOT NULL REFERENCES sites(id),
    slug TEXT NOT NULL,
    title TEXT NOT NULL,
    body TEXT NOT NULL DEFAULT '',
    is_draft BOOLEAN NOT NULL DEFAULT TRUE,
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(site_id, slug)
);

CREATE TABLE subscribers (
    id SERIAL PRIMARY KEY,
    site_id INTEGER NOT NULL REFERENCES sites(id),
    email TEXT NOT NULL,
    confirmed BOOLEAN NOT NULL DEFAULT FALSE,
    token TEXT NOT NULL UNIQUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE feeds (
    id SERIAL PRIMARY KEY,
    url TEXT NOT NULL UNIQUE,
    feed_url TEXT,
    feed_title TEXT,
    feed_icon_url TEXT,
    latest_post_title TEXT,
    latest_post_url TEXT,
    last_updated TIMESTAMPTZ,
    last_fetched TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE blogroll (
    id SERIAL PRIMARY KEY,
    site_id INTEGER NOT NULL REFERENCES sites(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    feed_id INTEGER NOT NULL REFERENCES feeds(id),
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE comments (
    id SERIAL PRIMARY KEY,
    post_id INTEGER NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    site_id INTEGER NOT NULL REFERENCES sites(id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    name TEXT NOT NULL,
    email_hash TEXT NOT NULL,
    body TEXT NOT NULL,
    author_url TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE indieauth_codes (
    id SERIAL PRIMARY KEY,
    site_id INTEGER NOT NULL REFERENCES sites(id) ON DELETE CASCADE,
    code TEXT UNIQUE NOT NULL,
    client_id TEXT NOT NULL,
    redirect_uri TEXT NOT NULL,
    scope TEXT NOT NULL DEFAULT '',
    code_challenge TEXT NOT NULL,
    code_challenge_method TEXT NOT NULL DEFAULT 'S256',
    token TEXT UNIQUE,
    used_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_sites_user_id ON sites (user_id);
CREATE INDEX idx_subscribers_site_id ON subscribers (site_id);
CREATE INDEX idx_blogroll_site_id ON blogroll (site_id);
CREATE INDEX idx_comments_post_id ON comments (post_id);
CREATE INDEX idx_comments_site_id ON comments (site_id);
CREATE INDEX idx_indieauth_codes_site_id ON indieauth_codes (site_id);
