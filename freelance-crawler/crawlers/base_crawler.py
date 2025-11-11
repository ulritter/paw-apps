import os
import logging
import psycopg2
from psycopg2 import sql
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
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

class BaseCrawler:
    """Base class for Selenium-based web crawlers"""
    
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
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                # Store the full config for this crawler
                self._full_config = config.get(self.name, {})
                # Store global keywords
                self._global_keywords = config.get('keywords', {})
                return self._full_config.get('queries', [])
        except FileNotFoundError:
            self.logger.warning(f"Config file not found: {config_path}")
            self._full_config = {}
            self._global_keywords = {}
            return []
        except json.JSONDecodeError as e:
            self.logger.error(f"Error parsing config file: {e}")
            self._full_config = {}
            self._global_keywords = {}
            return []
    
    def get_base_url(self):
        """Get base URL from config"""
        return self._full_config.get('base_url', '')
    
    def get_search_path(self):
        """Get search path from config"""
        return self._full_config.get('search_path', '')
    
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
        """Initialize Selenium WebDriver with Chrome/Chromium"""
        chrome_options = Options()
        
        if self.headless:
            chrome_options.add_argument('--headless')
        
        # Essential options for Docker/headless environment
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        
        # Anti-detection measures
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # Add realistic browser preferences
        prefs = {
            "profile.default_content_setting_values.notifications": 2,
            "credentials_enable_service": False,
            "profile.password_manager_enabled": False
        }
        chrome_options.add_experimental_option("prefs", prefs)
        
        # Add language headers (important for German sites)
        chrome_options.add_argument('--lang=de-DE')
        chrome_options.add_argument('--accept-lang=de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7')
        
        # Random user agent rotation
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        ]
        chrome_options.add_argument(f'user-agent={random.choice(user_agents)}')
        
        # Use system ChromeDriver
        service = Service(executable_path='/usr/bin/chromedriver')
        
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # Enhanced stealth JavaScript - hide webdriver and add realistic properties
        self.driver.execute_cdp_cmd('Network.setUserAgentOverride', {
            "userAgent": self.driver.execute_script("return navigator.userAgent").replace('HeadlessChrome', 'Chrome'),
            "acceptLanguage": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7"
        })
        
        self.driver.execute_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
            Object.defineProperty(navigator, 'languages', {get: () => ['de-DE', 'de', 'en-US', 'en']});
            window.chrome = {runtime: {}};
        """)
        
        self.logger.info("✅ Selenium WebDriver initialized")
    
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
                created_at TIMESTAMP DEFAULT NOW(),
                processed BOOLEAN DEFAULT FALSE
            );
        """)
        
        # Add posted_date column if it doesn't exist (for existing tables)
        self.db_cursor.execute("""
            DO $$ 
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name = 'jobs' AND column_name = 'posted_date'
                ) THEN
                    ALTER TABLE jobs ADD COLUMN posted_date TIMESTAMP;
                END IF;
            END $$;
        """)
        
        # Create index for faster sorting by posted_date
        self.db_cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_jobs_posted_date 
            ON jobs(posted_date DESC);
        """)
        
        self.db_conn.commit()
        self.logger.info("✅ Database table 'jobs' is ready")
    
    def save_job(self, job_data):
        """Save job to database"""
        try:
            insert_query = sql.SQL("""
                INSERT INTO jobs (source, title, link, company, location, posted, posted_date)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (link) DO NOTHING
                RETURNING id;
            """)
            
            self.db_cursor.execute(insert_query, (
                self.name,
                job_data.get('title'),
                job_data.get('link'),
                job_data.get('company'),
                job_data.get('location'),
                job_data.get('posted'),
                job_data.get('posted_date'),  # New field
            ))
            
            result = self.db_cursor.fetchone()
            self.db_conn.commit()
            
            if result:
                self.logger.info(f"💾 Saved: {job_data.get('title')}")
                return True
            else:
                self.logger.debug(f"⏭️  Skipped (duplicate): {job_data.get('title')}")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Error saving job: {e}")
            self.db_conn.rollback()
            return False
    
    def random_delay(self, min_seconds=1, max_seconds=3):
        """Add random delay to mimic human behavior"""
        delay = random.uniform(min_seconds, max_seconds)
        time.sleep(delay)
    
    def wait_for_element(self, by, value, timeout=10):
        """Wait for element to be present"""
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            return element
        except TimeoutException:
            self.logger.warning(f"⏱️  Timeout waiting for element: {value}")
            return None
    
    def scroll_page(self, scroll_pause_time=2):
        """Scroll page to load dynamic content"""
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        
        while True:
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(scroll_pause_time)
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            
            if new_height == last_height:
                break
            last_height = new_height
    
    def crawl(self):
        """Main crawl method - to be implemented by subclasses"""
        raise NotImplementedError("Subclasses must implement crawl() method")
    
    def run(self):
        """Execute the crawler"""
        try:
            self.logger.info(f"🚀 Starting {self.name} crawler...")
            self._setup_driver()
            self._setup_database()
            self.crawl()
            self.logger.info(f"✅ {self.name} crawler finished successfully")
        except Exception as e:
            self.logger.error(f"❌ Crawler failed: {e}", exc_info=True)
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Clean up resources"""
        if self.driver:
            self.driver.quit()
            self.logger.info("🔒 WebDriver closed")
        
        if self.db_cursor:
            self.db_cursor.close()
        if self.db_conn:
            self.db_conn.close()
            self.logger.info("🔒 Database connection closed")
