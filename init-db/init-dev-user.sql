-- Create the restricted user
CREATE USER dev_user WITH PASSWORD 'dev_pass_123';

-- Grant permissions to the specific database
GRANT ALL PRIVILEGES ON DATABASE the_turing_trials TO dev_user;

-- Connect to the DB to grant schema permissions
\c the_turing_trials

-- Ensure the dev user can actually do things inside the public schema
GRANT USAGE ON SCHEMA public TO dev_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO dev_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO dev_user;