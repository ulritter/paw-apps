#!/bin/bash
set -e

# Database backup script with compression
# This script creates a compressed backup of the PostgreSQL database

# Color codes for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Load environment variables from .env file if available (for standalone execution)
# When running from Docker container, environment variables are already set
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
elif [ -z "$POSTGRES_USER" ] || [ -z "$POSTGRES_PASSWORD" ] || [ -z "$POSTGRES_DB" ]; then
    echo -e "${RED}❌ Error: Database environment variables not set${NC}"
    echo -e "${RED}   Required: POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB${NC}"
    exit 1
fi

# Configuration
BACKUP_DIR="./backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/pawsys_backup_${TIMESTAMP}.sql"
COMPRESSED_FILE="${BACKUP_FILE}.gz"
CONTAINER_NAME="paw_postgres"

# Create backup directory if it doesn't exist
mkdir -p "${BACKUP_DIR}"

echo -e "${BLUE}🚀 Starting database backup...${NC}"
echo -e "${BLUE}📅 Timestamp: ${TIMESTAMP}${NC}"

# Check if container is running
if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo -e "${RED}❌ Error: Container '${CONTAINER_NAME}' is not running${NC}"
    exit 1
fi

# Create the database dump
echo -e "${BLUE}💾 Creating database dump...${NC}"
docker exec -t "${CONTAINER_NAME}" pg_dump -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -F p > "${BACKUP_FILE}"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Database dump created successfully${NC}"
else
    echo -e "${RED}❌ Error: Database dump failed${NC}"
    exit 1
fi

# Compress the backup
echo -e "${BLUE}🗜️  Compressing backup...${NC}"
gzip "${BACKUP_FILE}"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Backup compressed successfully${NC}"
else
    echo -e "${RED}❌ Error: Compression failed${NC}"
    exit 1
fi

# Get file size
FILE_SIZE=$(du -h "${COMPRESSED_FILE}" | cut -f1)

echo -e "${GREEN}✨ Backup completed successfully!${NC}"
echo -e "${GREEN}📦 Backup file: ${COMPRESSED_FILE}${NC}"
echo -e "${GREEN}📏 File size: ${FILE_SIZE}${NC}"

# Keep only last 7 backups
MAX_BACKUPS=7
echo -e "${BLUE}🧹 Cleaning old backups (keeping last ${MAX_BACKUPS})...${NC}"
cd "${BACKUP_DIR}" && ls -t pawsys_backup_*.sql.gz 2>/dev/null | tail -n +$((MAX_BACKUPS + 1)) | xargs -r rm
echo -e "${GREEN}✅ Cleanup completed${NC}"

echo -e "${GREEN}🎉 All done!${NC}"
