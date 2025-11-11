from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
from .base_crawler import BaseCrawler
import time
import os
from datetime import datetime, timedelta
import re

class HaysCrawler(BaseCrawler):
    """Crawler for Hays.de"""
    
    def __init__(self):
        super().__init__(name='hays', headless=True)
    
    def crawl(self):
        """Crawl Hays job listings"""
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
            
            # Build URL using search_path from config
            # Format: {base_url}{search_path}?q={query}&e=false&pt=false
            url = f"{base_url}{search_path}?q={query.replace(' ', '+')}&e=false&pt=false"
            
            try:
                self.driver.get(url)
                self.random_delay(2, 4)
                
                # Wait for page to load
                self.wait_for_element(By.TAG_NAME, 'body', timeout=10)
                
                # Scroll to load any lazy-loaded content
                self.scroll_page(scroll_pause_time=1)
                
                # Parse with BeautifulSoup
                soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                
                # Debug: Save page source if needed
                if os.getenv('DEBUG_MODE', 'false').lower() == 'true':
                    debug_file = f"/tmp/hays_{query.replace(' ', '_')}.html"
                    with open(debug_file, 'w', encoding='utf-8') as f:
                        f.write(self.driver.page_source)
                    self.logger.info(f"🐛 Debug: Page source saved to {debug_file}")
                    
                    # Take screenshot
                    screenshot_file = f"/tmp/hays_{query.replace(' ', '_')}.png"
                    self.driver.save_screenshot(screenshot_file)
                    self.logger.info(f"🐛 Debug: Screenshot saved to {screenshot_file}")
                
                # Find job listings - try multiple selectors
                job_cards = (
                    soup.select('article.job-item') or
                    soup.select('.job-result') or
                    soup.select('[class*="job-card"]') or
                    soup.select('article') or
                    soup.select('[class*="result"]')
                )
                
                if not job_cards:
                    self.logger.warning(f"⚠️  No job cards found for query '{query}'. Selectors may need updating.")
                    self.logger.info(f"💡 Enable DEBUG_MODE=true to inspect HTML structure")
                else:
                    self.logger.info(f"📋 Found {len(job_cards)} job listings for '{query}'")
                    
                    # Debug: Log first job card HTML structure
                    if os.getenv('DEBUG_MODE', 'false').lower() == 'true' and job_cards:
                        first_card = str(job_cards[0])[:500]
                        self.logger.info(f"🐛 First job card HTML: {first_card}...")
                
                for card in job_cards:
                    job_data = self._parse_job_card(card)
                    if job_data and job_data.get('link'):
                        self.logger.info(f"📄 Found: {job_data.get('title')}")
                        # Apply filter keywords
                        if self.matches_filter(job_data, filter_keywords):
                            self.logger.info(f"✅ Matched filter: {job_data.get('title')}")
                            if self.save_job(job_data):
                                total_jobs += 1
                        else:
                            total_filtered += 1
                            self.logger.info(f"⏭️  Filtered out (no keyword match): {job_data.get('title')}")
                    
                    self.random_delay(0.5, 1)
                
            except Exception as e:
                self.logger.error(f"❌ Error crawling query '{query}': {e}")
        
        self.logger.info(f"📊 Total jobs saved: {total_jobs}")
        self.logger.info(f"🔍 Total jobs filtered out: {total_filtered}")
    
    def _parse_job_card(self, card):
        """Parse individual job card based on Hays structure"""
        try:
            # Hays structure: <a class="search__result__link" href="..."></a>
            # Title is in a separate element within the card
            
            # Find the link
            link_elem = (
                card.select_one('a.search__result__link') or
                card.select_one('a[href*="stellenangebote-jobs-detail"]') or
                card.select_one('a[href*="job"]')
            )
            
            if not link_elem:
                return None
            
            # Find title - try multiple possible locations
            title_elem = (
                card.select_one('h2') or
                card.select_one('h3') or
                card.select_one('.search__result__title') or
                card.select_one('[class*="title"]') or
                card.select_one('strong') or
                card.select_one('b')
            )
            
            # Find location
            location_elem = (
                card.select_one('.search__result__location') or
                card.select_one('[class*="location"]') or
                card.select_one('[class*="ort"]')
            )
            
            # Find posted date
            posted_elem = (
                card.select_one('.search__result__date') or
                card.select_one('[class*="date"]') or
                card.select_one('time')
            )
            
            # Find reference number
            ref_elem = (
                card.select_one('[class*="reference"]') or
                card.select_one('[class*="referenz"]')
            )
            
            # Extract link
            link = self._make_absolute_url(link_elem.get('href'))
            
            # Extract title
            if title_elem:
                title = title_elem.get_text(strip=True)
            else:
                # Fallback: extract from URL if no title element found
                # URL format: .../stellenangebote-jobs-detail-salesforce-entwickler-stuttgart-839258/1
                url_parts = link.split('stellenangebote-jobs-detail-')
                if len(url_parts) > 1:
                    title_slug = url_parts[1].split('/')[0]
                    title = title_slug.replace('-', ' ').title()
                else:
                    return None
            
            location = location_elem.get_text(strip=True) if location_elem else 'N/A'
            posted_text = posted_elem.get_text(strip=True) if posted_elem else 'N/A'
            
            # Company is Hays (they're the recruiter)
            company = 'Hays'
            if ref_elem:
                ref_number = ref_elem.get_text(strip=True)
                company = f"Hays ({ref_number})"
            
            # Parse posted date to timestamp
            posted_date = self._parse_posted_date(posted_text)
            
            job_data = {
                'title': title,
                'link': link,
                'company': company,
                'location': location,
                'posted': posted_text,
                'posted_date': posted_date,
            }
            
            return job_data
            
        except Exception as e:
            self.logger.debug(f"Error parsing job card: {e}")
            return None
    
    def _parse_posted_date(self, posted_text):
        """Parse posted date string to datetime object"""
        if not posted_text or posted_text == 'N/A':
            return None
        
        try:
            now = datetime.now()
            
            # Clean up the text
            posted_text = posted_text.replace('Online seit:', '').strip()
            
            # Format: "Fri Sep 19 15:31:40 CEST 2025"
            # Try to parse full datetime string
            try:
                # Remove timezone abbreviation
                date_str = re.sub(r'\s+[A-Z]{3,4}\s+', ' ', posted_text)
                return datetime.strptime(date_str, '%a %b %d %H:%M:%S %Y')
            except:
                pass
            
            # Format: "DD.MM.YYYY" (4-digit year)
            if re.match(r'^\d{2}\.\d{2}\.\d{4}$', posted_text):
                return datetime.strptime(posted_text, '%d.%m.%Y')
            
            # Format: "DD.MM.YY" (2-digit year)
            if re.match(r'^\d{2}\.\d{2}\.\d{2}$', posted_text):
                return datetime.strptime(posted_text, '%d.%m.%y')
            
            # Format: "HH:MM" (today)
            if re.match(r'^\d{1,2}:\d{2}$', posted_text):
                hour, minute = map(int, posted_text.split(':'))
                return now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            
            # Text formats
            if 'heute' in posted_text.lower() or 'today' in posted_text.lower():
                return now
            
            if 'gestern' in posted_text.lower() or 'yesterday' in posted_text.lower():
                return now - timedelta(days=1)
            
            # If we can't parse it, return current time
            return now
            
        except Exception as e:
            self.logger.debug(f"Could not parse posted date '{posted_text}': {e}")
            return datetime.now()
    
    def _make_absolute_url(self, url):
        """Convert relative URL to absolute"""
        if not url:
            return None
        if url.startswith('http'):
            return url
        base_url = self.get_base_url()
        return f"{base_url}{url}" if url.startswith('/') else f"{base_url}/{url}"
