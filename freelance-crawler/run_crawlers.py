#!/usr/bin/env python3
"""
Main script to run all crawlers
"""
import sys
import logging
from crawlers.freelancermap_crawler import FreelancerMapCrawler
# from crawlers.malt_crawler import MaltCrawler  # Commented out: Malt is a freelancer marketplace, not a project portal
from crawlers.solcom_crawler import SolcomCrawler
from crawlers.solcom_crawler_undetected import SolcomCrawlerUndetected
from crawlers.hays_crawler import HaysCrawler

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def main():
    """Run all crawlers"""
    crawlers = [
        FreelancerMapCrawler(),
        # MaltCrawler(),  # Commented out: Malt is a freelancer marketplace, not a project portal
        # SolcomCrawler(),  # Disabled: Blocked by Cloudflare
        SolcomCrawlerUndetected(),  # Using undetected-chromedriver to bypass Cloudflare
        HaysCrawler(),
    ]
    
    success_count = 0
    failed_count = 0
    
    for crawler in crawlers:
        try:
            crawler.run()
            success_count += 1
        except Exception as e:
            logging.error(f"Failed to run {crawler.name}: {e}")
            failed_count += 1
    
    logging.info(f"\n{'='*50}")
    logging.info(f"Crawling Summary:")
    logging.info(f"  ✅ Successful: {success_count}")
    logging.info(f"  ❌ Failed: {failed_count}")
    logging.info(f"{'='*50}\n")
    
    return 0 if failed_count == 0 else 1

if __name__ == '__main__':
    sys.exit(main())
