-- Reference only. Migrations are the source of truth.
-- Update this file when writing new migrations.

CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    name TEXT,
    subdomain TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    bio TEXT,
    avatar TEXT,
    custom_domain TEXT UNIQUE,
    domain_verified_at TIMESTAMPTZ,
    domain_verification_token TEXT,
    license TEXT,
    links JSONB DEFAULT '[]',
    theme TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE posts (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    slug TEXT NOT NULL,
    title TEXT,
    body TEXT NOT NULL,
    is_draft BOOLEAN NOT NULL DEFAULT FALSE,
    is_pinned BOOLEAN NOT NULL DEFAULT FALSE,
    published_at TIMESTAMPTZ,
    sent_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, slug)
);

CREATE TABLE subscribers (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
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
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    feed_id INTEGER NOT NULL REFERENCES feeds(id),
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE indieauth_codes (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
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

CREATE INDEX idx_posts_user_id ON posts (user_id);
CREATE INDEX idx_subscribers_user_id ON subscribers (user_id);
CREATE INDEX idx_blogroll_user_id ON blogroll (user_id);
CREATE INDEX idx_indieauth_codes_user_id ON indieauth_codes (user_id);
