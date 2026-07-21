-- ============================================================
-- schema.sql
-- Initialises the supportdesk database.
-- Applied manually against RDS, or via a bootstrap Job — this
-- project intentionally has no docker-compose / local dev DB.
-- ============================================================

CREATE DATABASE IF NOT EXISTS supportdesk;
USE supportdesk;

-- Users table — stores signup/login credentials for both
-- customers (who raise tickets) and agents (who get assigned tickets)
CREATE TABLE IF NOT EXISTS users (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    name       VARCHAR(100)  NOT NULL,
    email      VARCHAR(255)  UNIQUE NOT NULL,
    password   VARCHAR(255)  NOT NULL,          -- stored as bcrypt hash
    created_at TIMESTAMP     DEFAULT CURRENT_TIMESTAMP
);

-- Tickets table — the support ticket catalogue
CREATE TABLE IF NOT EXISTS tickets (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    title       VARCHAR(200) NOT NULL,
    description VARCHAR(1000) NOT NULL,
    priority    VARCHAR(20)  NOT NULL DEFAULT 'medium',
    status      VARCHAR(20)  NOT NULL DEFAULT 'open',
    created_at  TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);

-- Assignment records — tracks which agent (user) is assigned to which ticket
-- Unique constraint prevents assigning the same ticket to the same agent twice
CREATE TABLE IF NOT EXISTS assignment_records (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    user_id       INT NOT NULL,
    ticket_id     INT NOT NULL,
    assigned_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY unique_assignment (user_id, ticket_id),
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (ticket_id) REFERENCES tickets(id)
);

-- Seed a few tickets so the UI has data to display immediately
INSERT IGNORE INTO tickets (title, description, priority, status) VALUES
    ('VPN drops every morning',        'VPN client disconnects roughly every 20 minutes after login.', 'high',   'open'),
    ('Cannot reset email password',    'Self-service password reset link returns a 404 error.',        'medium', 'open'),
    ('Laptop fan very loud',           'Fan runs at full speed even under light load.',                 'low',    'open'),
    ('Printer offline on 3rd floor',   'Shared office printer shows offline for the whole team.',       'medium', 'open'),
    ('Onboarding access request',      'New hire needs access to the shared drive and Slack.',          'high',   'open');
