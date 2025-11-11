#!/usr/bin/env python3
"""
Quick test script to verify FreelancerMap crawler with updated selectors
"""
import os
os.environ['DEBUG_MODE'] = 'true'

from crawlers.freelancermap_crawler import FreelancerMapCrawler

if __name__ == '__main__':
    print("🧪 Testing FreelancerMap Crawler with updated selectors...\n")
    crawler = FreelancerMapCrawler()
    crawler.run()
    print("\n✅ Test complete!")
