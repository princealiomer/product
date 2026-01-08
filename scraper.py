import cloudscraper
from bs4 import BeautifulSoup
import pandas as pd
import time
import os
import random

def get_scraper():
    # extensive browser simulation to bypass Cloudflare
    return cloudscraper.create_scraper(
        browser={
            'browser': 'chrome',
            'platform': 'windows',
            'desktop': True
        }
    )

def scrape_producthunt(url, retries=3):
    print(f"Scraping: {url}")
    scraper = get_scraper()
    
    for attempt in range(retries):
        try:
            # Add random delay before request
            time.sleep(random.uniform(1, 3))
            
            response = scraper.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
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
            import json
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
            print(f"Attempt {attempt+1} failed for {url}: {e}")
            if attempt < retries - 1:
                time.sleep(5)  # Backoff before retry
            else:
                return {
                    'url': url,
                    'error': f"Failed after {retries} attempts: {str(e)}"
                }

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
        result = scrape_producthunt(url)
        results.append(result)
        time.sleep(random.uniform(2, 5)) 
    
    try:
        df = pd.DataFrame(results)
        output_file = 'producthunt_data.csv'
        df.to_csv(output_file, index=False)
        print(f"\n✅ Done! Saved {len(results)} results to {output_file}")
    except Exception as e:
        print(f"Error saving CSV: {e}")
