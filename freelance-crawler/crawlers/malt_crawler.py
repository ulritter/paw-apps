from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
from .base_crawler import BaseCrawler
import time
import os

class MaltCrawler(BaseCrawler):
    """Crawler for Malt.de with enhanced anti-blocking measures"""
    
    def __init__(self):
        super().__init__(name='malt', headless=True)
    
    def crawl(self):
        """Crawl Malt job listings"""
        total_jobs = 0
        total_filtered = 0
        
        # Get search queries from config
        search_queries = self.get_search_queries()
        
        if not search_queries:
            self.logger.warning("No search queries found in config")
            return
        
        # Get base URL and search path from config
        base_url = self.get_base_url()
        search_path = self.get_search_path()
        
        if not base_url or not search_path:
            self.logger.error("Missing base_url or search_path in config")
            return
        
        for query in search_queries:
            # Get filter keywords for this query
            filter_keywords = self.get_filter_keywords(query)
            self.logger.info(f"🔍 Searching for: {query}")
            url = f"{base_url}{search_path}?query={query.replace(' ', '%20')}"
            
            try:
                self.driver.get(url)
                
                # Longer delay for Malt to avoid detection
                self.random_delay(3, 5)
                
                # Check if we got blocked
                if '403' in self.driver.title or 'Access Denied' in self.driver.page_source:
                    self.logger.warning(f"⚠️  Access blocked for query '{query}'. Trying alternative approach...")
                    
                    # Try going to homepage first
                    self.driver.get(base_url)
                    self.random_delay(2, 4)
                    
                    # Then navigate to search
                    self.driver.get(url)
                    self.random_delay(3, 5)
                
                # Wait for content to load
                self.wait_for_element(By.TAG_NAME, 'body', timeout=15)
                
                # Scroll slowly to mimic human behavior
                self._human_like_scroll()
                
                # Parse with BeautifulSoup
                soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                
                # Debug: Save page source if needed
                if os.getenv('DEBUG_MODE', 'false').lower() == 'true':
                    debug_file = f"/tmp/malt_{query.replace(' ', '_')}.html"
                    with open(debug_file, 'w', encoding='utf-8') as f:
                        f.write(self.driver.page_source)
                    self.logger.info(f"🐛 Debug: Page source saved to {debug_file}")
                    
                    # Take screenshot
                    screenshot_file = f"/tmp/malt_{query.replace(' ', '_')}.png"
                    self.driver.save_screenshot(screenshot_file)
                    self.logger.info(f"🐛 Debug: Screenshot saved to {screenshot_file}")
                
                # Try multiple possible selectors for job/freelancer listings
                job_cards = (
                    soup.select('.freelancer-card') or
                    soup.select('[data-testid="freelancer-card"]') or
                    soup.select('.profile-card') or
                    soup.select('article') or
                    soup.select('.search-result') or
                    soup.select('div[class*="freelancer"]') or
                    soup.select('div[class*="profile"]') or
                    soup.select('div[class*="card"]')
                )
                
                self.logger.info(f"📋 Found {len(job_cards)} listings for '{query}'")
                
                # Debug: Log what we found
                if len(job_cards) == 0:
                    self.logger.warning(f"⚠️  No listings found. Page title: {self.driver.title}")
                    # Check if blocked
                    if '403' in self.driver.page_source or 'Forbidden' in self.driver.title:
                        self.logger.error("🚫 Page appears to be blocked (403 Forbidden)")
                    # Try to find any profile links
                    all_links = soup.select('a[href*="/profile/"]') or soup.select('a[href*="/freelancer/"]')
                    self.logger.info(f"🔍 Found {len(all_links)} profile/freelancer links")
                    if all_links:
                        self.logger.info(f"   Sample link: {all_links[0].get('href')}")
                
                for card in job_cards:
                    job_data = self._parse_job_card(card)
                    if job_data and job_data.get('link'):
                        # Apply filter keywords
                        if self.matches_filter(job_data, filter_keywords):
                            if self.save_job(job_data):
                                total_jobs += 1
                        else:
                            total_filtered += 1
                            self.logger.debug(f"⏭️  Filtered out: {job_data.get('title')}")
                    
                    self.random_delay(1, 2)
                
            except Exception as e:
                self.logger.error(f"❌ Error crawling query '{query}': {e}")
        
        self.logger.info(f"📊 Total jobs saved: {total_jobs}")
        self.logger.info(f"🔍 Total jobs filtered out: {total_filtered}")
    
    def _human_like_scroll(self):
        """Scroll page in a human-like manner"""
        total_height = self.driver.execute_script("return document.body.scrollHeight")
        viewport_height = self.driver.execute_script("return window.innerHeight")
        
        current_position = 0
        while current_position < total_height:
            # Scroll by random amount
            scroll_amount = viewport_height * (0.3 + (0.4 * __import__('random').random()))
            current_position += scroll_amount
            
            self.driver.execute_script(f"window.scrollTo(0, {current_position});")
            time.sleep(__import__('random').uniform(0.5, 1.5))
    
    def _parse_job_card(self, card):
        """Parse individual job/freelancer card"""
        try:
            # Try multiple selectors for each field
            title = (
                card.select_one('.freelancer-name')
                or card.select_one('h2')
                or card.select_one('h3')
                or card.select_one('[data-testid="name"]')
                or card.select_one('.profile-title')
            )
            
            link_elem = (
                card.select_one('a[href*="/profile/"]')
                or card.select_one('a[href*="/freelancer/"]')
                or card.select_one('a')
            )
            
            company = (
                card.select_one('.company')
                or card.select_one('.freelancer-tagline')
                or card.select_one('[data-testid="tagline"]')
            )
            
            location = (
                card.select_one('.location')
                or card.select_one('[data-testid="location"]')
                or card.select_one('.freelancer-location')
            )
            
            # For Malt, we might not have a "posted" date, use availability or rate instead
            posted = (
                card.select_one('.availability')
                or card.select_one('.rate')
                or card.select_one('[data-testid="availability"]')
            )
            
            job_data = {
                'title': title.get_text(strip=True) if title else 'N/A',
                'link': self._make_absolute_url(link_elem.get('href')) if link_elem else None,
                'company': company.get_text(strip=True) if company else 'Freelancer',
                'location': location.get_text(strip=True) if location else 'N/A',
                'posted': posted.get_text(strip=True) if posted else 'N/A',
            }
            
            return job_data if job_data['link'] else None
            
        except Exception as e:
            self.logger.debug(f"Error parsing card: {e}")
            return None
    
    def _make_absolute_url(self, url):
        """Convert relative URL to absolute"""
        if not url:
            return None
        if url.startswith('http'):
            return url
        base_url = self.get_base_url()
        return f"{base_url}{url}" if url.startswith('/') else f"{base_url}/{url}"
