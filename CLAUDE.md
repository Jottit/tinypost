# CLAUDE.md

## What is Jottit?

Blogging without the blogging software. Write a post, it's published. No themes, no plugins, no settings to fiddle with.

Jottit is a radically simple blogging platform. You sign up, you get a blog at yourname.jottit.pub, and you start writing. That's it.

Originally co-created with Aaron Swartz in 2007. Now being rebuilt as open infrastructure for web publishing.

## Stack

- Flask + Jinja2 (server-side rendered)
- Vanilla JS islands for interactivity
- PostgreSQL (production), SQLite (development)
- IndieWeb protocols: Micropub, IndieAuth, ActivityPub
- Deployed on Fly.io (Amsterdam region)

All pages served dynamically from the database. No static site generation.

## Commands

- `flask run --debug` — dev server with auto-reload
- `pytest` — run tests
- `fly deploy` — deploy to production
- Commits: one-line messages only, no co-authored-by trailers

## Project Structure
```
app.py              — routes and application setup
templates/          — Jinja2 templates
static/             — CSS, JS islands
```

## Code Style

- Python: simple, readable, no clever abstractions
- HTML: semantic, minimal classes
- CSS: reuse existing classes and variables before adding new ones. Check what's already defined in stylesheets first. Never use inline styles — always use classes.
- JS: vanilla only, no build step, no frameworks
- Keep files small and focused
- Prefer explicit over clever
- Don't swallow errors — let exceptions propagate in development
- Don't add unused imports or reorganize existing ones
- Don't add comments that restate what the code does
- Do only what was asked — no bonus features, no "while I'm at it" additions

## Testing

- Always add tests when implementing new features
- Bug fixes: write a failing test first, then fix the bug, then verify the test passes
- Cover the happy path and obvious edge cases, don't over-test

## Design Principles

- If it needs a settings page, rethink it.
- One beautiful default, no themes.
- Micropub clients handle editing — don't build an admin UI.
- Every dependency is a liability — keep them minimal.
- Clarity over performance.

## Content Model

A blog is a list of posts. A post has a slug, markdown body, title, and timestamps. The blog itself has a name, subdomain, and an optional about page. That's the whole data model.

## Don't

- Add features without discussing the tradeoff
- Introduce dependencies without justification
- Build settings, dashboards, or admin UIs
- Generate static files
- Over-engineer — this is a simple app, keep it that way
