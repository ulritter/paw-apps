#!/bin/bash

# PAW Systems - User Management Script

set -e

echo "👤 PAW Systems - Add User"
echo "========================="
echo ""

# Check if email is provided
if [ -z "$1" ]; then
    echo "Usage: ./add-user.sh <email@paw-systems.com>"
    echo ""
    echo "Example:"
    echo "  ./add-user.sh john.doe@paw-systems.com"
    exit 1
fi

EMAIL=$1

# Validate email domain
if [[ ! "$EMAIL" =~ @paw-systems\.com$ ]]; then
    echo "❌ Error: Email must be from @paw-systems.com domain"
    exit 1
fi

# Check if Docker is running
if ! docker compose ps db | grep -q "running"; then
    echo "❌ Error: Database service is not running!"
    echo "   Please start services first: docker compose up -d"
    exit 1
fi

echo "Adding user: $EMAIL"
echo ""

# Add user to database
docker compose exec -T db psql -U ${POSTGRES_USER:-pawuser} -d ${POSTGRES_DB:-pawsystems} << EOF
-- Check if user already exists
DO \$\$
BEGIN
    IF EXISTS (SELECT 1 FROM users WHERE email = '$EMAIL') THEN
        RAISE NOTICE 'User % already exists', '$EMAIL';
    ELSE
        INSERT INTO users (email, created_at) VALUES ('$EMAIL', NOW());
        RAISE NOTICE 'User % added successfully', '$EMAIL';
    END IF;
END
\$\$;

-- Show user details
SELECT id, email, created_at, last_login FROM users WHERE email = '$EMAIL';
EOF

echo ""
echo "✅ Done!"
echo ""
echo "📧 The user can now login at: http://localhost/login.html"
echo "   They will receive an authentication code via email."
