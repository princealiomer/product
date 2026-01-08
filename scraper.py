from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import pandas as pd
import time
import os
import random
import json

def scrape_producthunt_with_playwright(url):
    print(f"Scraping: {url}")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # Use a consistent, real user agent
        context = browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080}
        )
        
        page = context.new_page()
        
        try:
            # Go to page with extended timeout
            page.goto(url, timeout=60000, wait_until="domcontentloaded")
            
            # Wait for specific element to ensure page loaded (e.g. product name header)
            # This implicitly waits for Cloudflare to pass
            try:
                page.wait_for_selector('h1', timeout=30000)
            except:
                print("Timeout waiting for content, page might be blocked or slow.")
            
            # Get the full HTML content after JS execution
            content = page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            data = {
                'url': url,
                'product_name': '',
                'website_url': '',
                'tagline': '',
                'rating': '',
                'reviews_count': '',
                'categories': ''
            }
            
            # 1. Try JSON-LD first (Structured Data)
            json_ld = soup.find('script', type='application/ld+json')
            if json_ld:
                try:
                    data_json = json.loads(json_ld.string)
                    if isinstance(data_json, list):
                        for item in data_json:
                            if item.get('@type') in ['Product', 'WebApplication', ['WebApplication', 'Product']]:
                                    data_json = item
                                    break
                    
                    if data_json.get('name'):
                        data['product_name'] = data_json['name']
                    
                    if data_json.get('aggregateRating'):
                        rating_obj = data_json['aggregateRating']
                        if rating_obj.get('ratingValue'):
                            data['rating'] = str(rating_obj['ratingValue'])
                        if rating_obj.get('ratingCount'):
                            data['reviews_count'] = str(rating_obj['ratingCount'])
                    
                    if data_json.get('applicationCategory'):
                        data['categories'] = data_json['applicationCategory']
                        
                except Exception as e:
                    print(f"Error parsing JSON-LD: {e}")

            # 2. HTML Fallbacks / Refinements
            
            # Product Name
            if not data['product_name']:
                name_el = soup.find('h1')
                if name_el:
                    data['product_name'] = name_el.text.strip()
            
            # Website URL
            if not data['website_url']:
                website_link = soup.find('a', {'data-test': 'visit-website-button'})
                if website_link:
                    data['website_url'] = website_link.get('href', '')

            # Tagline
            if not data['tagline']:
                tagline_el = soup.find('h2', class_='text-18')
                if not tagline_el:
                    tagline_el = soup.find('h2', class_='font-medium')
                if not tagline_el:
                    tagline_el = soup.find('h2')
                
                if tagline_el:
                    data['tagline'] = tagline_el.text.strip()

            # Rating
            if not data['rating']:
                rating_spans = soup.find_all('span', class_='text-14 font-medium')
                for span in rating_spans:
                    text = span.text.strip()
                    try:
                        val = float(text)
                        if 0 <= val <= 5:
                            data['rating'] = text
                            break
                    except ValueError:
                        continue

            # Reviews Count
            if not data['reviews_count']:
                reviews_link = soup.find('a', href=lambda x: x and '/reviews' in x)
                if reviews_link and 'review' in reviews_link.text.lower():
                        data['reviews_count'] = reviews_link.text.strip()
                else:
                    reviews_el = soup.find(string=lambda x: x and 'review' in x.lower() and x.parent.name not in ['script', 'style'])
                    if reviews_el:
                        data['reviews_count'] = reviews_el.parent.text.strip()

            # Categories
            category_links = soup.find_all('a', href=lambda x: x and '/categories/' in x)
            categories = []
            for link in category_links:
                cat_name = link.text.strip()
                if cat_name and cat_name not in categories:
                    categories.append(cat_name)
            
            if categories:
                data['categories'] = ', '.join(categories[:5])
            
            return data
            
        except Exception as e:
            return {
                'url': url,
                'error': f"Playwright Error: {str(e)}"
            }
        finally:
            browser.close()

# For module compatibility
def scrape_producthunt(url):
    return scrape_producthunt_with_playwright(url)

if __name__ == "__main__":
    if not os.path.exists('urls.txt'):
        print("urls.txt not found. Please create it with one URL per line.")
        exit(1)

    with open('urls.txt', 'r') as f:
        urls = [line.strip() for line in f if line.strip()]
    
    if not urls:
        print("No URLs found in urls.txt")
        exit(1)

    results = []
    total = len(urls)
    
    for i, url in enumerate(urls, 1):
        print(f"[{i}/{total}] Processing...")
        result = scrape_producthunt_with_playwright(url)
        results.append(result)
        # Playwright isolates sessions well, but a small delay is still polite
        time.sleep(1) 
    
    try:
        df = pd.DataFrame(results)
        output_file = 'producthunt_data.csv'
        df.to_csv(output_file, index=False)
        print(f"\n✅ Done! Saved {len(results)} results to {output_file}")
    except Exception as e:
        print(f"Error saving CSV: {e}")
