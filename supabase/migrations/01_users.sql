-- 01_users.sql
-- Description: Core users table with role-based access control.

CREATE TYPE user_role AS ENUM ('compliance_officer', 'ml_engineer', 'cto');

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT auth.uid(),
    email TEXT NOT NULL UNIQUE,
    role user_role NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enable RLS
ALTER TABLE users ENABLE ROW LEVEL SECURITY;

-- Policies
CREATE POLICY "Users can view their own profile" ON users
    FOR SELECT USING (auth.uid() = id);

CREATE POLICY "CTOs can view all users" ON users
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM users WHERE id = auth.uid() AND role = 'cto'
        )
    );
