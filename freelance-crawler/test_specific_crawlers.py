#!/usr/bin/env python3
"""
Test script to debug Solcom and Hays crawlers with specific queries
"""
import os
os.environ['DEBUG_MODE'] = 'true'

from crawlers.solcom_crawler import SolcomCrawler
from crawlers.hays_crawler import HaysCrawler

if __name__ == '__main__':
    print("="*60)
    print("🧪 Testing Solcom Crawler (LLM query)")
    print("="*60)
    print()
    
    solcom = SolcomCrawler()
    solcom.run()
    
    print()
    print("="*60)
    print("🧪 Testing Hays Crawler (LLM and Salesforce queries)")
    print("="*60)
    print()
    
    hays = HaysCrawler()
    hays.run()
    
    print()
    print("="*60)
    print("✅ Test complete!")
    print("="*60)
    print()
    print("Check debug files:")
    print("  - /tmp/solcom_llm.html")
    print("  - /tmp/solcom_llm.png")
    print("  - /tmp/hays_llm.html")
    print("  - /tmp/hays_llm.png")
    print("  - /tmp/hays_salesforce.html")
    print("  - /tmp/hays_salesforce.png")
