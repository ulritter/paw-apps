from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
from .base_crawler import BaseCrawler
import time
import os

class FreelancerMapCrawler(BaseCrawler):
    """Crawler for FreelancerMap.de"""
    
    def __init__(self):
        super().__init__(name='freelancermap', headless=True)
    
    def crawl(self):
        """Crawl FreelancerMap job listings"""
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
            url = f"{base_url}{search_path}?query={query.replace(' ', '+')}"
            
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
                    debug_file = f"/tmp/freelancermap_{query.replace(' ', '_')}.html"
                    with open(debug_file, 'w', encoding='utf-8') as f:
                        f.write(self.driver.page_source)
                    self.logger.info(f"🐛 Debug: Page source saved to {debug_file}")
                    
                    # Take screenshot
                    screenshot_file = f"/tmp/freelancermap_{query.replace(' ', '_')}.png"
                    self.driver.save_screenshot(screenshot_file)
                    self.logger.info(f"🐛 Debug: Screenshot saved to {screenshot_file}")
                
                # Correct selector for FreelancerMap job cards
                job_cards = soup.select('.project-card')
                
                self.logger.info(f"📋 Found {len(job_cards)} job listings for '{query}'")
                
                # Debug: Log what we found
                if len(job_cards) == 0:
                    self.logger.warning(f"⚠️  No job cards found. Page title: {self.driver.title}")
                    # Try to find any links that might be jobs
                    all_links = soup.select('a[href*="projekt"]')
                    self.logger.info(f"🔍 Found {len(all_links)} links containing 'projekt'")
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
                    
                    self.random_delay(0.5, 1)
                
            except Exception as e:
                self.logger.error(f"❌ Error crawling query '{query}': {e}")
        
        self.logger.info(f"📊 Total jobs saved: {total_jobs}")
        self.logger.info(f"🔍 Total jobs filtered out: {total_filtered}")
    
    def _parse_job_card(self, card):
        """Parse individual job card based on FreelancerMap structure"""
        try:
            # Title: <a data-testid="title" class="h3 no-underline">
            title_elem = card.select_one('a[data-testid="title"]')
            
            # Company: First div with class "mg-b-display-m line-height-base" in project-info
            project_info = card.select_one('.project-info')
            company_elem = project_info.select_one('.mg-b-display-m.line-height-base') if project_info else None
            
            # Location: Combine city and country
            city_elem = card.select_one('a[data-id="project-card-city"]')
            country_elem = card.select_one('a[data-id="project-card-country"]')
            
            # Posted date: <span data-testid="created">
            posted_elem = card.select_one('span[data-testid="created"]')
            
            # Contract type: <div data-testid="type">
            type_elem = card.select_one('div[data-testid="type"]')
            
            # Build location string
            location_parts = []
            if city_elem:
                location_parts.append(city_elem.get_text(strip=True).rstrip(','))
            if country_elem:
                location_parts.append(country_elem.get_text(strip=True))
            location = ', '.join(location_parts) if location_parts else 'N/A'
            
            # Build job data
            job_data = {
                'title': title_elem.get_text(strip=True) if title_elem else 'N/A',
                'link': self._make_absolute_url(title_elem.get('href')) if title_elem else None,
                'company': company_elem.get_text(strip=True) if company_elem else 'N/A',
                'location': location,
                'posted': posted_elem.get_text(strip=True) if posted_elem else 'N/A',
            }
            
            # Add contract type to company field for context
            if type_elem:
                contract_type = type_elem.get_text(strip=True)
                job_data['company'] = f"{job_data['company']} ({contract_type})"
            
            return job_data if job_data['link'] else None
            
        except Exception as e:
            self.logger.debug(f"Error parsing job card: {e}")
            return None
    
    def _make_absolute_url(self, url):
        """Convert relative URL to absolute"""
        if not url:
            return None
        if url.startswith('http'):
            return url
        base_url = self.get_base_url()
        return f"{base_url}{url}" if url.startswith('/') else f"{base_url}/{url}"
