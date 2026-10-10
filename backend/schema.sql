
-- Store indexed words
CREATE TABLE IF NOT EXISTS lexicon (
    id INTEGER PRIMARY KEY,
    word TEXT UNIQUE
);

-- Store crawled documents
CREATE TABLE IF NOT EXISTS document_index (
    id INTEGER PRIMARY KEY,
    url TEXT UNIQUE
);

-- Map words to documents
CREATE TABLE IF NOT EXISTS inverted_index (
    word_id INTEGER REFERENCES lexicon(id),
    document_id INTEGER REFERENCES document_index(id),
    positions TEXT,
    PRIMARY KEY (word_id, document_id)
);

-- Store PageRank scores
CREATE TABLE IF NOT EXISTS pagerank (
    document_id INTEGER PRIMARY KEY
        REFERENCES document_index(id),
    score DOUBLE PRECISION
);

-- Speed up keyword lookups
CREATE INDEX IF NOT EXISTS idx_inverted_word
ON inverted_index(word_id);