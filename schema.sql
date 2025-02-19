CREATE TABLE crawler_state (
    cursor_state TEXT NOT NULL,
    last_created_at TEXT NOT NULL
);

CREATE TABLE pages (
    url TEXT PRIMARY KEY,
    slug TEXT NOT NULL,
    title TEXT NOT NULL,
    category TEXT NOT NULL,
    created_at TEXT NOT NULL,
    wikidot_page_id INTEGER NOT NULL,
    source TEXT NOT NULL
);

CREATE TABLE extracts (
    page_url TEXT NOT NULL,
    extract_type TEXT NOT NULL,
    extract_index INTEGER NOT NULL,
    source TEXT NOT NULL,

    UNIQUE (page_url, extract_type, extract_index)
);
