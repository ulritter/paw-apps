#!/usr/bin/env python3
"""
Debug script to inspect page structure and find correct selectors
"""
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time

def setup_driver():
    """Initialize Selenium WebDriver"""
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    service = Service(executable_path='/usr/bin/chromedriver')
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    return driver

def debug_freelancermap():
    """Debug FreelancerMap page structure"""
    print("\n" + "="*60)
    print("DEBUGGING FREELANCERMAP.DE")
    print("="*60 + "\n")
    
    driver = setup_driver()
    
    try:
        url = "https://www.freelancermap.de/projektboerse.html?query=salesforce"
        print(f"Loading: {url}")
        driver.get(url)
        time.sleep(3)
        
        # Save page source for inspection
        with open('/tmp/freelancermap_page.html', 'w', encoding='utf-8') as f:
            f.write(driver.page_source)
        print("✅ Page source saved to /tmp/freelancermap_page.html")
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        # Look for common job listing patterns
        print("\n🔍 Looking for job listing containers...")
        
        patterns = [
            ('article', 'article tags'),
            ('.project', 'class="project"'),
            ('.job', 'class="job"'),
            ('[data-testid]', 'data-testid attributes'),
            ('.card', 'class="card"'),
            ('.listing', 'class="listing"'),
            ('div[class*="project"]', 'divs with "project" in class'),
            ('div[class*="job"]', 'divs with "job" in class'),
        ]
        
        for selector, description in patterns:
            elements = soup.select(selector)
            if elements:
                print(f"  ✅ Found {len(elements)} elements: {description}")
                if len(elements) > 0:
                    print(f"     First element classes: {elements[0].get('class', [])}")
                    print(f"     First element preview: {str(elements[0])[:200]}...")
            else:
                print(f"  ❌ No elements: {description}")
        
        # Look for links
        print("\n🔍 Looking for job links...")
        links = soup.select('a[href*="projekt"]')
        print(f"  Found {len(links)} links containing 'projekt'")
        if links:
            print(f"  Sample link: {links[0].get('href')}")
        
        # Print page title
        print(f"\n📄 Page title: {driver.title}")
        
        # Check for any error messages
        if '403' in driver.page_source or 'Access Denied' in driver.page_source:
            print("⚠️  WARNING: Page may be blocked (403/Access Denied detected)")
        
    finally:
        driver.quit()

def debug_malt():
    """Debug Malt page structure"""
    print("\n" + "="*60)
    print("DEBUGGING MALT.DE")
    print("="*60 + "\n")
    
    driver = setup_driver()
    
    try:
        url = "https://www.malt.de/search?query=salesforce"
        print(f"Loading: {url}")
        driver.get(url)
        time.sleep(4)
        
        # Save page source for inspection
        with open('/tmp/malt_page.html', 'w', encoding='utf-8') as f:
            f.write(driver.page_source)
        print("✅ Page source saved to /tmp/malt_page.html")
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        # Look for common freelancer listing patterns
        print("\n🔍 Looking for freelancer listing containers...")
        
        patterns = [
            ('article', 'article tags'),
            ('.freelancer', 'class="freelancer"'),
            ('.profile', 'class="profile"'),
            ('[data-testid]', 'data-testid attributes'),
            ('.card', 'class="card"'),
            ('div[class*="freelancer"]', 'divs with "freelancer" in class'),
            ('div[class*="profile"]', 'divs with "profile" in class'),
            ('div[class*="search"]', 'divs with "search" in class'),
        ]
        
        for selector, description in patterns:
            elements = soup.select(selector)
            if elements:
                print(f"  ✅ Found {len(elements)} elements: {description}")
                if len(elements) > 0:
                    print(f"     First element classes: {elements[0].get('class', [])}")
                    print(f"     First element preview: {str(elements[0])[:200]}...")
            else:
                print(f"  ❌ No elements: {description}")
        
        # Look for links
        print("\n🔍 Looking for profile links...")
        links = soup.select('a[href*="/profile/"]') or soup.select('a[href*="/freelancer/"]')
        print(f"  Found {len(links)} profile/freelancer links")
        if links:
            print(f"  Sample link: {links[0].get('href')}")
        
        # Print page title
        print(f"\n📄 Page title: {driver.title}")
        
        # Check for blocking
        if '403' in driver.page_source or 'Access Denied' in driver.page_source or 'Forbidden' in driver.title:
            print("⚠️  WARNING: Page may be blocked (403/Access Denied detected)")
        
    finally:
        driver.quit()

if __name__ == '__main__':
    debug_freelancermap()
    debug_malt()
    
    print("\n" + "="*60)
    print("DEBUG COMPLETE")
    print("="*60)
    print("\nCheck the saved HTML files:")
    print("  - /tmp/freelancermap_page.html")
    print("  - /tmp/malt_page.html")
    print("\nYou can inspect these files to find the correct selectors.")
