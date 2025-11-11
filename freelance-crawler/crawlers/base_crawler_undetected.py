import os
import logging
import psycopg2
from psycopg2 import sql
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import time
import random
import json

load_dotenv()

class BaseCrawlerUndetected:
    """Base class for undetected-chromedriver based web crawlers (bypasses Cloudflare)"""
    
    def __init__(self, name, headless=True):
        self.name = name
        self.headless = headless
        self.driver = None
        self.db_conn = None
        self.db_cursor = None
        self.logger = self._setup_logger()
        self.search_config = self._load_search_config()
        self.debug_mode = os.getenv('DEBUG_MODE', 'false').lower() == 'true'
        self.debug_dir = '/debug_artifacts' if self.debug_mode else '/tmp'
        
    def _setup_logger(self):
        """Setup logging for the crawler"""
        logger = logging.getLogger(self.name)
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            f'[{self.name}] %(levelname)s: %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        return logger
    
    def _load_search_config(self):
        """Load search patterns and filter keywords from JSON config"""
        # Use shared config volume path
        config_path = '/app/config/search_config.json'
        # Fallback to local path for development
        if not os.path.exists(config_path):
            config_path = os.path.join(os.path.dirname(__file__), 'search_config.json')
        
        try:
            with open(config_path, 'r') as f:
                full_config = json.load(f)
                
            # Store global keywords
            self._global_keywords = full_config.get('keywords', {})
            
            # Return crawler-specific config
            crawler_config = full_config.get(self.name, {})
            return crawler_config.get('queries', [])
        except FileNotFoundError:
            self.logger.warning(f"⚠️  Config file not found at {config_path}, using empty config")
            self._global_keywords = {}
            return []
        except Exception as e:
            self.logger.error(f"❌ Error loading config: {e}")
            self._global_keywords = {}
            return []
    
    def get_search_queries(self):
        """Get list of search queries from config"""
        return [item['query'] for item in self.search_config]
    
    def get_filter_keywords(self, query):
        """Get filter keywords for a specific search query"""
        for item in self.search_config:
            if item['query'] == query:
                # Get the keyword set name
                keyword_set = item.get('keywords', '')
                # Return the actual keywords from global keywords
                return self._global_keywords.get(keyword_set, [])
        return []
    
    def matches_filter(self, job_data, filter_keywords):
        """Check if job data matches any of the filter keywords"""
        if not filter_keywords:
            return True  # No filters means accept all
        
        # Combine all searchable fields into one string
        searchable_text = ' '.join([
            str(job_data.get('title', '')),
            str(job_data.get('company', '')),
            str(job_data.get('location', '')),
        ]).lower()
        
        # Check if any filter keyword is present
        for keyword in filter_keywords:
            if keyword.lower() in searchable_text:
                return True
        
        return False
    
    def _setup_driver(self):
        """Initialize undetected ChromeDriver to bypass Cloudflare"""
        options = uc.ChromeOptions()
        
        # Don't use headless mode - Cloudflare detects it
        # if self.headless:
        #     options.add_argument('--headless=new')
        
        # Essential options for Docker environment
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        
        # Realistic Mac User-Agent (not HeadlessChrome!)
        options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        # Language settings for German sites
        options.add_argument('--lang=de-DE')
        options.add_argument('--accept-lang=de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7')
        
        # Create undetected Chrome instance
        self.driver = uc.Chrome(
            options=options,
            driver_executable_path='/usr/bin/chromedriver',
            version_main=None,  # Auto-detect Chrome version
            use_subprocess=True,
            headless=False  # Explicitly disable headless
        )
        
        # Set page load timeout
        self.driver.set_page_load_timeout(30)
        
        self.logger.info("✅ Undetected ChromeDriver initialized (Cloudflare bypass enabled)")
    
    def _setup_database(self):
        """Initialize database connection and create table"""
        db_url = os.getenv("DATABASE_URL")
        if not db_url:
            raise RuntimeError("❌ DATABASE_URL not found!")
        
        self.db_conn = psycopg2.connect(db_url)
        self.db_cursor = self.db_conn.cursor()
        
        # Create jobs table if not exists
        self.db_cursor.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id SERIAL PRIMARY KEY,
                source TEXT,
                title TEXT,
                link TEXT UNIQUE,
                company TEXT,
                location TEXT,
                posted TEXT,
                posted_date DATE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                processed BOOLEAN DEFAULT FALSE
            );
        """)
        self.db_conn.commit()
        self.logger.info("✅ Database connection established")
    
    def save_job(self, job_data):
        """Save job to database"""
        try:
            self.db_cursor.execute("""
                INSERT INTO jobs (source, title, link, company, location, posted, posted_date)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (link) DO NOTHING
                RETURNING id;
            """, (
                job_data['source'],
                job_data['title'],
                job_data['link'],
                job_data.get('company', ''),
                job_data.get('location', ''),
                job_data.get('posted', ''),
                job_data.get('posted_date', None)
            ))
            
            result = self.db_cursor.fetchone()
            if result:
                self.db_conn.commit()
                return True
            return False
        except Exception as e:
            self.logger.error(f"❌ Error saving job: {e}")
            self.db_conn.rollback()
            return False
    
    def random_delay(self, min_seconds=1, max_seconds=3):
        """Add random delay to mimic human behavior"""
        delay = random.uniform(min_seconds, max_seconds)
        time.sleep(delay)
    
    def cleanup(self):
        """Clean up resources"""
        if self.driver:
            self.driver.quit()
            self.logger.info("🧹 Browser closed")
        
        if self.db_cursor:
            self.db_cursor.close()
        if self.db_conn:
            self.db_conn.close()
            self.logger.info("🧹 Database connection closed")
    
    def run(self):
        """Main run method - to be implemented by subclasses"""
        raise NotImplementedError("Subclasses must implement run() method")
