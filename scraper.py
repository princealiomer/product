import cloudscraper
from bs4 import BeautifulSoup
import pandas as pd
import time
import os

def scrape_producthunt(url):
    print(f"Scraping: {url}")
    
    try:
        scraper = cloudscraper.create_scraper()
        response = scraper.get(url, timeout=15)
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
        
        # Try to extract from JSON-LD first (Structured Data)
        import json
        json_ld = soup.find('script', type='application/ld+json')
        if json_ld:
            try:
                data_json = json.loads(json_ld.string)
                if isinstance(data_json, list):
                    # Sometimes it's a list, find the Product
                    for item in data_json:
                        if item.get('@type') in ['Product', 'WebApplication', ['WebApplication', 'Product']]:
                             data_json = item
                             break
                
                if data_json.get('name'):
                    data['product_name'] = data_json['name']
                
                # Tagline: prefer HTML extraction as JSON description is usually long text
                # if data_json.get('description'):
                #    data['tagline'] = data_json['description']
                
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

        # Fallback/Refinement for fields if missing
        
        # Product Name
        if not data['product_name']:
            name_el = soup.find('h1')
            if name_el:
                data['product_name'] = name_el.text.strip()
        
        # Site URL
        if not data['website_url']:
            website_link = soup.find('a', {'data-test': 'visit-website-button'})
            if website_link:
                data['website_url'] = website_link.get('href', '')

        # Tagline (Refined)
        if not data['tagline']:
            tagline_el = soup.find('h2', class_='text-18')
            if not tagline_el:
                tagline_el = soup.find('h2', class_='font-medium') 
            if not tagline_el:
                 tagline_el = soup.find('h2')
            if tagline_el:
                data['tagline'] = tagline_el.text.strip()

        # Rating (Refined)
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

        # Reviews Check (Fixing bug where script content was grabbed)
        if not data['reviews_count']:
            reviews_link = soup.find('a', href=lambda x: x and '/reviews' in x)
            if reviews_link and 'review' in reviews_link.text.lower():
                 data['reviews_count'] = reviews_link.text.strip()
            else:
                # Find text visible only (not scripts)
                reviews_el = soup.find(string=lambda x: x and 'review' in x.lower() and x.parent.name not in ['script', 'style'])
                if reviews_el:
                    data['reviews_count'] = reviews_el.parent.text.strip()

        # Categories
        # HTML extraction is often better for multiple categories than just 'applicationCategory' string
        category_links = soup.find_all('a', href=lambda x: x and '/categories/' in x)
        categories = []
        for link in category_links:
            cat_name = link.text.strip()
            if cat_name and cat_name not in categories:
                categories.append(cat_name)
        
        if categories:
            data['categories'] = ', '.join(categories[:5])

        # Extract categories
        # Links containing /categories/
        category_links = soup.find_all('a', href=lambda x: x and '/categories/' in x)
        categories = []
        for link in category_links:
            cat_name = link.text.strip()
            if cat_name and cat_name not in categories:
                categories.append(cat_name)
        
        data['categories'] = ', '.join(categories[:5])
        
        return data
        
    except Exception as e:
        print(f"Error scraping {url}: {e}")
        return {
            'url': url,
            'error': str(e)
        }

if __name__ == "__main__":
    # Check if urls.txt exists
    if not os.path.exists('urls.txt'):
        print("urls.txt not found. Please create it with one URL per line.")
        exit(1)

    # Read URLs from file
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
        time.sleep(2)  # Be respectful - wait 2 seconds between requests
    
    # Save to CSV
    try:
        df = pd.DataFrame(results)
        output_file = 'producthunt_data.csv'
        df.to_csv(output_file, index=False)
        print(f"\n✅ Done! Saved {len(results)} results to {output_file}")
    except Exception as e:
        print(f"Error saving CSV: {e}")
