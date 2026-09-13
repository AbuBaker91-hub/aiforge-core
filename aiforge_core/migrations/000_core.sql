CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS chunks (
    id        bigserial PRIMARY KEY,
    doc       text NOT NULL,
    page      integer,
    section   text,
    text      text NOT NULL,
    embedding vector(384) NOT NULL,
    tsv       tsvector GENERATED ALWAYS AS (to_tsvector('english', text)) STORED,
    UNIQUE (doc, page, section, text)
);
CREATE INDEX IF NOT EXISTS chunks_tsv_idx ON chunks USING gin (tsv);

CREATE TABLE IF NOT EXISTS audit_log (
    id             bigserial PRIMARY KEY,
    stage          text NOT NULL,
    ref            text NOT NULL DEFAULT '',
    input_hash     text NOT NULL DEFAULT '',
    prompt_version text NOT NULL DEFAULT '',
    ok             boolean NOT NULL,
    detail         text NOT NULL DEFAULT '',
    created_at     timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS audit_log_ref_idx ON audit_log (ref);

CREATE TABLE IF NOT EXISTS processed_keys (
    key         text PRIMARY KEY,
    result_json jsonb,
    created_at  timestamptz NOT NULL DEFAULT now()
);
