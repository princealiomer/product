from bs4 import BeautifulSoup
import json
import os

def parse_content(html_content, url):
    soup = BeautifulSoup(html_content, 'html.parser')
    
    data = {
        'url': url,
        'product_name': '',
        'website_url': '',
        'tagline': '',
        'rating': '',
        'reviews_count': '',
        'categories': '',
        'error': ''
    }

    print("--- Debugging Parse Logic ---")

    # 1. Try JSON-LD first
    json_ld = soup.find('script', type='application/ld+json')
    if json_ld:
        print("Found JSON-LD script tag.")
        try:
            data_json = json.loads(json_ld.string)
            target_item = None
            
            if isinstance(data_json, list):
                print(f"JSON-LD is a list of {len(data_json)} items.")
                for item in data_json:
                    if item.get('@type') in ['Product', 'WebApplication', ['WebApplication', 'Product']]:
                        target_item = item
                        print("Match found!")
                        break
            elif isinstance(data_json, dict):
                 target_item = data_json

            if target_item:
                if target_item.get('name'):
                    data['product_name'] = target_item['name']
                
                if target_item.get('aggregateRating'):
                    rating_obj = target_item['aggregateRating']
                    if rating_obj.get('ratingValue'):
                        data['rating'] = str(rating_obj['ratingValue'])
                    if rating_obj.get('ratingCount'):
                        data['reviews_count'] = str(rating_obj['ratingCount'])
                
                if target_item.get('applicationCategory'):
                    data['categories'] = target_item['applicationCategory']
        except Exception as e:
            print(f"Error parsing JSON-LD: {e}")
    else:
        print("No JSON-LD script tag found.")

    print("Checking Apollo State (Iterative)...")
    try:
        scripts = soup.find_all('script')
        print(f"Total scripts found: {len(scripts)}")
        apollo_script = None
        apollo_script = None
        for i, s in enumerate(scripts):
            content = s.get_text()
            if content and 'ApolloSSRDataTransport' in content:
                print(f"Found Apollo string in script #{i}")
                apollo_script = content
                break
        
        if apollo_script:
            print("Found Apollo Script tag.")
            start_marker = '.push('
            end_marker = ')'
            
            start_idx = apollo_script.find(start_marker)
            if start_idx != -1:
                json_start = start_idx + len(start_marker)
                json_end = apollo_script.rfind(end_marker)
                
                if json_end > json_start:
                    json_str = apollo_script[json_start:json_end]
                    
                    # Fix: Replace JS 'undefined' with JSON 'null'
                    json_str = json_str.replace('undefined', 'null')
                    
                    try:
                        apollo_data = json.loads(json_str)
                        print("Parsed Apollo JSON successfully.")
                        
                        if 'rehydrate' in apollo_data:
                            # Dump keys to see structure if needed
                            # print(apollo_data['rehydrate'].keys())
                            
                            for key, value in apollo_data['rehydrate'].items():
                                if value and 'data' in value and value['data'] and 'product' in value['data']:
                                    prod = value['data']['product']
                                    print("Found product data in Apollo.")
                                    
                                    # We found the product object!
                                    if 'structuredData' in prod:
                                         sd = prod['structuredData']
                                         if sd.get('name'):
                                             data['product_name'] = sd['name']
                                         if sd.get('aggregateRating'):
                                             ar = sd['aggregateRating']
                                             if isinstance(ar, dict):
                                                 data['rating'] = str(ar.get('ratingValue', ''))
                                                 data['reviews_count'] = str(ar.get('ratingCount', ''))
                                    
                                    # Fallbacks from product object directly
                                    if not data['product_name'] and prod.get('name'):
                                        data['product_name'] = prod['name']
                                    
                                    if not data['tagline'] and prod.get('tagline'):
                                        data['tagline'] = prod['tagline']
                                        
                                    if not data['website_url'] and prod.get('websiteUrl'):
                                        data['website_url'] = prod['websiteUrl']
                                    
                                    if not data['reviews_count'] and prod.get('reviewsCount'):
                                        data['reviews_count'] = str(prod['reviewsCount'])

                                    if not data['rating'] and prod.get('reviewsRating'):
                                        data['rating'] = str(prod['reviewsRating'])

                                    break
                    except json.JSONDecodeError as e:
                        print(f"JSON Decode Error: {e.msg}")
    except Exception as e:
        print(f"Error in Apollo logic: {e}")

    # 3. HTML Fallbacks
    print("Running HTML Fallbacks...")
    if not data['product_name']:
        name_el = soup.find('h1')
        if name_el:
            data['product_name'] = name_el.text.strip()
            print(f"Fallback Name found: {data['product_name']}")

    return data

if __name__ == "__main__":
    import sys
    sys.stdout = open('debug_log.txt', 'w', encoding='utf-8')
    
    file_path = r"d:\product hunt\example\Coda Reviews (2026) _ Product Hunt.html"
    print(f"Reading {file_path}...")
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            print(f"Read {len(content)} bytes.")
            result = parse_content(content, "http://local-test")
            print("\n--- Final Result ---")
            print(json.dumps(result, indent=2))
    except Exception as e:
        print(f"Error: {e}")
