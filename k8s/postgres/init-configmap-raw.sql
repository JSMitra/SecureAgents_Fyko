CREATE TABLE IF NOT EXISTS ann_requests (
    ulid VARCHAR(26) PRIMARY KEY,
    callback_url TEXT NOT NULL,
    use_complex_model BOOLEAN DEFAULT FALSE,
    status VARCHAR(20) DEFAULT 'PENDING',
    published BOOLEAN DEFAULT FALSE,
    model_name VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS agent_keys (
    agent_name VARCHAR(100) PRIMARY KEY,
    public_key_pem TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);
