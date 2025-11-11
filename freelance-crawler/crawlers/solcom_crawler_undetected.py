#!/usr/bin/env python3
"""
Solcom crawler using undetected-chromedriver to bypass Cloudflare
"""
from crawlers.base_crawler_undetected import BaseCrawlerUndetected
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from bs4 import BeautifulSoup
import time

class SolcomCrawlerUndetected(BaseCrawlerUndetected):
    """Crawler for Solcom project portal with Cloudflare bypass"""
    
    def __init__(self):
        super().__init__('solcom', headless=True)
        self.base_url = "https://www.solcom.de"
        self.search_path = "/de/projektportal"
    
    def run(self):
        """Main crawler execution"""
        try:
            self.logger.info("🚀 Starting solcom crawler (Cloudflare bypass mode)")
            self._setup_driver()
            self._setup_database()
            
            # Get search queries from config
            queries = self.get_search_queries()
            if not queries:
                self.logger.warning("⚠️  No search queries configured for solcom")
                return
            
            self.logger.info(f"📋 Found {len(queries)} search queries")
            
            for query in queries:
                try:
                    self.search_and_scrape(query)
                    self.random_delay(2, 4)
                except Exception as e:
                    self.logger.error(f"❌ Error processing query '{query}': {e}")
                    continue
            
            self.logger.info("✅ solcom crawler finished successfully")
            
        except Exception as e:
            self.logger.error(f"❌ Fatal error in solcom crawler: {e}")
            raise
        finally:
            self.cleanup()
    
    def search_and_scrape(self, query):
        """Search for a query and scrape results"""
        self.logger.info(f"🔍 Searching for: {query}")
        
        # Get filter keywords for this query
        filter_keywords = self.get_filter_keywords(query)
        self.logger.info(f"🎯 Using filter keywords: {filter_keywords}")
        
        # Navigate directly to Solcom project search page
        url = "https://www.solcom.de/de/projektportal/projektangebote"
        self.logger.info(f"📍 Navigating to {url}")
        self.driver.get(url)
        time.sleep(3)
        
        # Wait for Cloudflare challenge to complete (if any)
        self.logger.info("⏳ Waiting for page to load (Cloudflare check)...")
        time.sleep(5)  # Give Cloudflare time to process
        
        # Save debug info after initial load
        if self.debug_mode:
            query_safe = query.replace(' ', '_')
            debug_info_file = f"{self.debug_dir}/solcom_initial_{query_safe}.txt"
            with open(debug_info_file, 'w', encoding='utf-8') as f:
                f.write(f"=== Solcom Initial Load ===\n")
                f.write(f"Query: {query}\n")
                f.write(f"Current URL: {self.driver.current_url}\n")
                f.write(f"Page Title: {self.driver.title}\n")
                f.write(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            self.logger.info(f"🐛 Initial load debug info saved to {debug_info_file}")
        
        # Check if we got blocked
        if "Kundeninformation" in self.driver.title or "nicht zur Verfügung" in self.driver.page_source:
            self.logger.error(f"❌ Blocked by Cloudflare/geo-restriction on initial load")
            self._save_error_artifacts(query, "initial_load_blocked")
            return
        
        # Try to dismiss cookie banner if present (Solcom specific)
        cookie_dismissed = False
        try:
            # Wait a moment for cookie banner to appear
            time.sleep(2)
            
            # Try multiple selectors for Solcom's cookie banner
            cookie_selectors = [
                "button.acceptall",  # "Alle akzeptieren" button
                ".acceptall",
                "button.prio1.acceptall",
                ".allow-essential-only",  # "Nur essenzielle Cookies akzeptieren"
                "button[class*='accept']",
                "button[class*='cookie']"
            ]
            
            for selector in cookie_selectors:
                if cookie_dismissed:
                    break
                try:
                    buttons = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for btn in buttons:
                        if btn.is_displayed():
                            # Scroll to button and click
                            self.driver.execute_script("arguments[0].scrollIntoView(true);", btn)
                            time.sleep(0.3)
                            btn.click()
                            self.logger.info(f"🍪 Dismissed cookie banner with selector: {selector}")
                            time.sleep(2)  # Wait for banner to disappear
                            cookie_dismissed = True
                            break
                except Exception as e:
                    continue
        except Exception as e:
            self.logger.warning(f"⚠️ Could not dismiss cookie banner: {e}")
        
        # Wait for search input to be present and interactable
        self.logger.info("🔍 Looking for search input field with id='keyword'...")
        try:
            # Wait for the search input to be present (using id="keyword" on projektangebote page)
            search_input = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "keyword"))
            )
            
            # Scroll the input into view
            self.driver.execute_script("arguments[0].scrollIntoView(true);", search_input)
            time.sleep(0.5)
            
            # Wait for it to be clickable
            search_input = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.ID, "keyword"))
            )
            
            # Use JavaScript to set the value directly (avoids click interception)
            self.driver.execute_script("arguments[0].value = arguments[1];", search_input, query)
            # Trigger input event to ensure any listeners are notified
            self.driver.execute_script("""
                var event = new Event('input', { bubbles: true });
                arguments[0].dispatchEvent(event);
            """, search_input)
            self.logger.info(f"✅ Entered search query via JavaScript: {query}")
            time.sleep(0.5)
            
            # Find and click the "Projekte finden" submit button
            self.logger.info("🔘 Looking for 'Projekte finden' submit button...")
            
            # Try multiple selectors in order of specificity for projektangebote page
            button_selectors = [
                "button.submitSearch[type='submit']",
                "button.submitSearch",
                "button[type='submit']",
                "input[type='submit']"
            ]
            
            submit_button = None
            for selector in button_selectors:
                try:
                    submit_button = WebDriverWait(self.driver, 3).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    )
                    self.logger.info(f"✅ Found submit button with selector: {selector}")
                    break
                except TimeoutException:
                    continue
            
            if not submit_button:
                raise Exception("Could not find submit button with any selector")
            
            # Use JavaScript to click the button (avoids click interception)
            self.driver.execute_script("arguments[0].click();", submit_button)
            self.logger.info("✅ Clicked 'Projekte finden' button via JavaScript")
            time.sleep(3)
            self.logger.info("✅ Search submitted successfully")
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            self.logger.error(f"❌ Could not interact with search form: {e}")
            self.logger.error(f"Full traceback:\n{error_details}")
            self._save_error_artifacts(query, "search_form_error")
            return
        
        # Wait for results to load
        time.sleep(3)
        
        # Check if we got blocked after search
        if "Kundeninformation" in self.driver.title or "nicht zur Verfügung" in self.driver.page_source:
            self.logger.error(f"❌ Blocked by Cloudflare/geo-restriction after search")
            self._save_error_artifacts(query, "search_blocked")
            return
        
        # Save debug artifacts if in debug mode
        if self.debug_mode:
            self._save_success_artifacts(query)
        
        # Parse results
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        
        # Find job listings
        job_cards = (
            soup.select('.project-item') or
            soup.select('.job-item') or
            soup.select('.project-card') or
            soup.select('article') or
            soup.select('[class*="project"]') or
            soup.select('[class*="job"]')
        )
        
        if not job_cards:
            self.logger.warning(f"⚠️  No job cards found for query: {query}")
            return
        
        self.logger.info(f"📦 Found {len(job_cards)} potential jobs")
        
        saved_count = 0
        filtered_count = 0
        
        for card in job_cards:
            try:
                job_data = self._extract_job_data(card)
                if not job_data:
                    continue
                
                # Check if job matches filter keywords
                if not self.matches_filter(job_data, filter_keywords):
                    filtered_count += 1
                    self.logger.info(f"⏭️  Filtered out: {job_data.get('title', 'Unknown')}")
                    continue
                
                # Save to database
                if self.save_job(job_data):
                    saved_count += 1
                    self.logger.info(f"💾 Saved: {job_data.get('title', 'Unknown')}")
                
            except Exception as e:
                self.logger.error(f"❌ Error processing job card: {e}")
                continue
        
        self.logger.info(f"✅ Query '{query}' complete: {saved_count} saved, {filtered_count} filtered")
    
    def _extract_job_data(self, card):
        """Extract job data from a job card element"""
        try:
            # Try to find title
            title_elem = (
                card.select_one('h2') or
                card.select_one('h3') or
                card.select_one('.title') or
                card.select_one('[class*="title"]')
            )
            title = title_elem.get_text(strip=True) if title_elem else None
            
            # Try to find link
            link_elem = card.select_one('a[href]')
            link = link_elem['href'] if link_elem else None
            if link and not link.startswith('http'):
                link = self.base_url + link
            
            if not title or not link:
                return None
            
            # Try to find company
            company_elem = card.select_one('.company, [class*="company"]')
            company = company_elem.get_text(strip=True) if company_elem else ''
            
            # Try to find location
            location_elem = card.select_one('.location, [class*="location"]')
            location = location_elem.get_text(strip=True) if location_elem else ''
            
            # Try to find posted date
            posted_elem = card.select_one('.date, [class*="date"], time')
            posted = posted_elem.get_text(strip=True) if posted_elem else ''
            
            return {
                'source': 'solcom',
                'title': title,
                'link': link,
                'company': company,
                'location': location,
                'posted': posted,
                'posted_date': None  # Would need date parsing
            }
        except Exception as e:
            self.logger.error(f"Error extracting job data: {e}")
            return None
    
    def _save_error_artifacts(self, query, error_type):
        """Save debug artifacts when an error occurs"""
        query_safe = query.replace(' ', '_')
        
        # Save debug info text file
        debug_info_file = f"{self.debug_dir}/solcom_{error_type}_{query_safe}.txt"
        with open(debug_info_file, 'w', encoding='utf-8') as f:
            f.write(f"=== Solcom Error: {error_type} ===\n")
            f.write(f"Query: {query}\n")
            f.write(f"Current URL: {self.driver.current_url}\n")
            f.write(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"User Agent: {self.driver.execute_script('return navigator.userAgent')}\n")
            f.write(f"Languages: {self.driver.execute_script('return navigator.languages')}\n")
            f.write(f"WebDriver: {self.driver.execute_script('return navigator.webdriver')}\n")
            f.write(f"\n=== Cookies ===\n")
            for cookie in self.driver.get_cookies():
                f.write(f"{cookie['name']}: {cookie['value']}\n")
            f.write(f"\n=== Page Title ===\n")
            f.write(f"{self.driver.title}\n")
        self.logger.error(f"🐛 Debug info saved to {debug_info_file}")
        
        # Save HTML
        debug_file = f"{self.debug_dir}/solcom_{error_type}_{query_safe}.html"
        with open(debug_file, 'w', encoding='utf-8') as f:
            f.write(self.driver.page_source)
        self.logger.error(f"🐛 Page source saved to {debug_file}")
        
        # Save screenshot
        screenshot_file = f"{self.debug_dir}/solcom_{error_type}_{query_safe}.png"
        self.driver.save_screenshot(screenshot_file)
        self.logger.error(f"🐛 Screenshot saved to {screenshot_file}")
    
    def _save_success_artifacts(self, query):
        """Save debug artifacts for successful searches"""
        query_safe = query.replace(' ', '_')
        
        # Save debug info text file
        debug_info_file = f"{self.debug_dir}/solcom_success_{query_safe}.txt"
        with open(debug_info_file, 'w', encoding='utf-8') as f:
            f.write(f"=== Solcom Success ===\n")
            f.write(f"Query: {query}\n")
            f.write(f"Current URL: {self.driver.current_url}\n")
            f.write(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"User Agent: {self.driver.execute_script('return navigator.userAgent')}\n")
            f.write(f"Languages: {self.driver.execute_script('return navigator.languages')}\n")
            f.write(f"WebDriver: {self.driver.execute_script('return navigator.webdriver')}\n")
            f.write(f"\n=== Cookies ===\n")
            for cookie in self.driver.get_cookies():
                f.write(f"{cookie['name']}: {cookie['value']}\n")
            f.write(f"\n=== Page Title ===\n")
            f.write(f"{self.driver.title}\n")
        self.logger.info(f"🐛 Debug info saved to {debug_info_file}")
        
        # Save HTML
        debug_file = f"{self.debug_dir}/solcom_success_{query_safe}.html"
        with open(debug_file, 'w', encoding='utf-8') as f:
            f.write(self.driver.page_source)
        self.logger.info(f"🐛 Page source saved to {debug_file}")
        
        # Save screenshot
        screenshot_file = f"{self.debug_dir}/solcom_success_{query_safe}.png"
        self.driver.save_screenshot(screenshot_file)
        self.logger.info(f"🐛 Screenshot saved to {screenshot_file}")
