from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
from .base_crawler import BaseCrawler
import time
import os
from datetime import datetime, timedelta
import re

class SolcomCrawler(BaseCrawler):
    """Crawler for Solcom.de"""
    
    def __init__(self):
        super().__init__(name='solcom', headless=True)
    
    def crawl(self):
        """Crawl Solcom job listings"""
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
        
        first_query = True
        for query in search_queries:
            # Get filter keywords for this query
            filter_keywords = self.get_filter_keywords(query)
            self.logger.info(f"🔍 Searching for: {query}")
            
            # Solcom uses a web form, not URL parameters
            # Only navigate to base URL for first query, then reuse the form on results page
            form_url = f"{base_url}/de/projektportal"
            
            try:
                # Only navigate for the first query
                if first_query:
                    self.logger.info(f"🌐 Navigating to: {form_url}")
                    self.driver.get(form_url)
                    self.random_delay(4, 6)
                    first_query = False
                else:
                    # For subsequent queries, just wait a bit for the form to be ready
                    self.logger.info("🔄 Reusing search form on current page")
                    self.random_delay(2, 3)
                
                # Wait for page to fully load
                self.wait_for_element(By.TAG_NAME, 'body', timeout=15)
                
                # Check if we got redirected or blocked
                current_url = self.driver.current_url
                if 'projektportal' not in current_url:
                    self.logger.error(f"❌ Redirected to unexpected URL: {current_url}")
                    continue
                
                # Always check for iframes (form might be in iframe on both initial and results page)
                # First, make sure we're in default content
                try:
                    self.driver.switch_to.default_content()
                except:
                    pass
                
                # Wait for JavaScript to load the form (it might be dynamically loaded)
                self.random_delay(2, 3)
                
                # Check if content is in an iframe
                iframes = self.driver.find_elements(By.TAG_NAME, 'iframe')
                if iframes:
                    self.logger.info(f"🔍 Found {len(iframes)} iframes, checking for form...")
                    for idx, iframe in enumerate(iframes):
                        try:
                            self.driver.switch_to.frame(iframe)
                            inputs = self.driver.find_elements(By.TAG_NAME, 'input')
                            if inputs:
                                self.logger.info(f"✅ Found form in iframe {idx}")
                                break
                            self.driver.switch_to.default_content()
                        except:
                            self.driver.switch_to.default_content()
                            continue
                else:
                    self.logger.info("🔍 No iframes found, form should be in main content")
                
                # Try to accept cookies if present
                try:
                    cookie_buttons = self.driver.find_elements(By.CSS_SELECTOR, 
                        'button[id*="accept"], button[class*="accept"], '
                        'button:contains("Akzeptieren"), button:contains("Accept"), '
                        'a[id*="accept"], a[class*="accept"]'
                    )
                    for btn in cookie_buttons:
                        if btn.is_displayed():
                            btn.click()
                            self.logger.info("🍪 Accepted cookies")
                            self.random_delay(1, 2)
                            break
                except Exception as e:
                    self.logger.debug(f"No cookie banner found: {e}")
                
                # Remove any overlays/popups/modals
                try:
                    self.driver.execute_script("""
                        // Remove all blocking elements
                        var selectors = [
                            '.overlay', '[class*="overlay"]',
                            '.modal', '[class*="modal"]',
                            '.cookie-banner', '[class*="cookie"]', '[id*="cookie"]',
                            '[class*="consent"]', '[id*="consent"]',
                            '.backdrop', '[class*="backdrop"]',
                            '[style*="z-index"]'
                        ];
                        selectors.forEach(function(sel) {
                            try {
                                var elements = document.querySelectorAll(sel);
                                elements.forEach(function(el) {
                                    if (el && el.style) {
                                        el.style.display = 'none';
                                        el.style.visibility = 'hidden';
                                        el.remove();
                                    }
                                });
                            } catch(e) {}
                        });
                        // Reset body overflow
                        document.body.style.overflow = 'auto';
                    """)
                    self.logger.info("🛡️ Removed overlays")
                    self.random_delay(1, 2)
                except Exception as e:
                    self.logger.debug(f"Overlay removal failed: {e}")
                
                # Find and fill the search input field ("Stichwort")
                try:
                    # Try different possible selectors for the search input
                    search_input = None
                    selectors = [
                        'input[id="keyword"]',  # On results page
                        'input[id="stichwort"]',  # On initial page
                        'input[name*="searchParameter"]',  # By name pattern
                        'input[placeholder*="Projektmanager"]',  # By placeholder
                        'input[placeholder*="Stichwort"]',
                        'input[type="text"][class*="search"]',
                        'input.search-param',  # Specific class on results page
                        'input.form-control'
                    ]
                    
                    for selector in selectors:
                        try:
                            elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                            for elem in elements:
                                # Check if element is visible and interactable
                                if elem.is_displayed() and elem.is_enabled():
                                    search_input = elem
                                    self.logger.info(f"✅ Found search input with selector: {selector}")
                                    break
                            if search_input:
                                break
                        except:
                            continue
                    
                    if not search_input:
                        self.logger.error(f"❌ Could not find search input field")
                        
                        # Debug: Log all input fields found
                        all_inputs = self.driver.find_elements(By.TAG_NAME, 'input')
                        self.logger.error(f"🐛 Found {len(all_inputs)} input fields on page:")
                        for idx, inp in enumerate(all_inputs[:10]):  # Show first 10
                            try:
                                inp_type = inp.get_attribute('type')
                                inp_name = inp.get_attribute('name')
                                inp_id = inp.get_attribute('id')
                                inp_class = inp.get_attribute('class')
                                inp_placeholder = inp.get_attribute('placeholder')
                                self.logger.error(f"  Input {idx}: type={inp_type}, name={inp_name}, id={inp_id}, class={inp_class}, placeholder={inp_placeholder}")
                            except:
                                pass
                        
                        # Debug: Save page source and screenshot
                        query_safe = query.replace(' ', '_')
                        
                        # Save debug info text file
                        debug_info_file = f"{self.debug_dir}/solcom_no_input_{query_safe}.txt"
                        with open(debug_info_file, 'w', encoding='utf-8') as f:
                            f.write(f"=== Solcom Debug Info ===\n")
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
                        debug_file = f"{self.debug_dir}/solcom_no_input_{query_safe}.html"
                        with open(debug_file, 'w', encoding='utf-8') as f:
                            f.write(self.driver.page_source)
                        self.logger.error(f"🐛 Page source saved to {debug_file}")
                        
                        # Save screenshot
                        screenshot_file = f"{self.debug_dir}/solcom_no_input_{query_safe}.png"
                        self.driver.save_screenshot(screenshot_file)
                        self.logger.error(f"🐛 Screenshot saved to {screenshot_file}")
                        
                        continue
                    
                    # Clear and enter search query
                    search_input.clear()
                    search_input.send_keys(query)
                    self.logger.info(f"✏️ Entered search term: {query}")
                    
                    self.random_delay(1, 2)
                    
                    # Close any overlays that might block the button
                    try:
                        # Try to find and hide overlay
                        self.driver.execute_script("""
                            var overlays = document.querySelectorAll('.overlay, [class*="overlay"]');
                            overlays.forEach(function(overlay) {
                                overlay.style.display = 'none';
                            });
                        """)
                        self.logger.info("🛡️ Removed overlays")
                    except:
                        pass
                    
                    # Find submit button with multiple selectors
                    submit_button = None
                    button_selectors = [
                        'button.submitSearch',
                        'button[type="submit"]',
                        'button.btn-default',
                        'input[type="submit"]',
                        'button:contains("Projekte finden")'
                    ]
                    
                    for btn_selector in button_selectors:
                        try:
                            buttons = self.driver.find_elements(By.CSS_SELECTOR, btn_selector)
                            for btn in buttons:
                                if btn.is_displayed() and btn.is_enabled():
                                    btn_text = btn.text.lower() if btn.text else ''
                                    btn_class = btn.get_attribute('class') or ''
                                    # Check if it's the right button
                                    if 'submit' in btn_class.lower() or 'projekt' in btn_text:
                                        submit_button = btn
                                        self.logger.info(f"✅ Found submit button: {btn_selector}")
                                        break
                            if submit_button:
                                break
                        except:
                            continue
                    
                    if not submit_button:
                        self.logger.error("❌ Could not find submit button")
                        # Debug: log all buttons
                        all_buttons = self.driver.find_elements(By.TAG_NAME, 'button')
                        self.logger.error(f"🐛 Found {len(all_buttons)} buttons on page")
                        for idx, btn in enumerate(all_buttons[:5]):
                            try:
                                self.logger.error(f"  Button {idx}: text='{btn.text}', class='{btn.get_attribute('class')}'")
                            except:
                                pass
                        continue
                    
                    # Scroll button into view
                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", submit_button)
                    self.random_delay(1, 2)
                    
                    # Try to click the button (with fallback to JavaScript click)
                    try:
                        submit_button.click()
                        self.logger.info(f"👆 Clicked 'Projekte finden' button")
                    except Exception as click_error:
                        # Fallback: Use JavaScript click
                        self.logger.info(f"⚠️  Normal click failed, using JavaScript click")
                        self.driver.execute_script("arguments[0].click();", submit_button)
                        self.logger.info(f"👆 Clicked 'Projekte finden' button (JavaScript)")
                    
                    # Wait for results to load
                    self.random_delay(3, 5)
                    
                except Exception as e:
                    self.logger.error(f"❌ Error filling form: {e}")
                    continue
                
                # Scroll to load any lazy-loaded content
                self.scroll_page(scroll_pause_time=1)
                
                # Parse with BeautifulSoup
                soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                
                # Debug: Save page source if needed
                if self.debug_mode:
                    debug_file = f"{self.debug_dir}/solcom_{query.replace(' ', '_')}.html"
                    with open(debug_file, 'w', encoding='utf-8') as f:
                        f.write(self.driver.page_source)
                    self.logger.info(f"🐛 Debug: Page source saved to {debug_file}")
                    
                    # Take screenshot
                    screenshot_file = f"{self.debug_dir}/solcom_{query.replace(' ', '_')}.png"
                    self.driver.save_screenshot(screenshot_file)
                    self.logger.info(f"🐛 Debug: Screenshot saved to {screenshot_file}")
                
                # Find job listings - will need to inspect actual HTML structure
                # Common selectors to try:
                job_cards = (
                    soup.select('.project-item') or
                    soup.select('.job-item') or
                    soup.select('.project-card') or
                    soup.select('article') or
                    soup.select('[class*="project"]') or
                    soup.select('[class*="job"]')
                )
                
                if not job_cards:
                    self.logger.warning(f"⚠️  No job cards found for query '{query}'. Selectors may need updating.")
                    self.logger.info(f"💡 Enable DEBUG_MODE=true to inspect HTML structure")
                else:
                    self.logger.info(f"📋 Found {len(job_cards)} job listings for '{query}'")
                
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
        """Parse individual job card - will need to be updated based on actual HTML structure"""
        try:
            # These selectors are placeholders and will need to be updated
            # after inspecting the actual Solcom HTML structure
            
            # Try to find title
            title_elem = (
                card.select_one('h2 a') or
                card.select_one('h3 a') or
                card.select_one('.title a') or
                card.select_one('a[href*="projekt"]')
            )
            
            # Try to find company
            company_elem = (
                card.select_one('.company') or
                card.select_one('[class*="company"]') or
                card.select_one('.client')
            )
            
            # Try to find location
            location_elem = (
                card.select_one('.location') or
                card.select_one('[class*="location"]') or
                card.select_one('[class*="ort"]')
            )
            
            # Try to find posted date
            posted_elem = (
                card.select_one('.date') or
                card.select_one('[class*="date"]') or
                card.select_one('time')
            )
            
            if not title_elem:
                return None
            
            title = title_elem.get_text(strip=True)
            link = self._make_absolute_url(title_elem.get('href'))
            company = company_elem.get_text(strip=True) if company_elem else 'Solcom'
            location = location_elem.get_text(strip=True) if location_elem else 'N/A'
            posted_text = posted_elem.get_text(strip=True) if posted_elem else 'N/A'
            
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
            
            # Format: "HH:MM" (e.g., "18:31") - posted today
            if re.match(r'^\d{1,2}:\d{2}$', posted_text):
                hour, minute = map(int, posted_text.split(':'))
                return now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            
            # Format: "DD.MM.YYYY" (e.g., "06.10.2025")
            if re.match(r'^\d{2}\.\d{2}\.\d{4}$', posted_text):
                return datetime.strptime(posted_text, '%d.%m.%Y')
            
            # Format: "MM/YYYY" (e.g., "11/2025")
            if re.match(r'^\d{1,2}/\d{4}$', posted_text):
                month, year = map(int, posted_text.split('/'))
                return datetime(year, month, 1)
            
            # Format: "MM/YY" (e.g., "11/25")
            if re.match(r'^\d{1,2}/\d{2}$', posted_text):
                month, year = map(int, posted_text.split('/'))
                year = 2000 + year if year < 100 else year
                return datetime(year, month, 1)
            
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
