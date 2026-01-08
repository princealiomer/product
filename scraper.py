from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import pandas as pd
import time
import os
import random
import json
import subprocess

def install_playwright_browser():
    """
    Installs Playwright Chromium browser if not already present.
    """
    print("Checking/Installing Playwright Chromium...")
    try:
        subprocess.run(["playwright", "install", "chromium"], check=True)
        print("Playwright installation check complete.")
    except Exception as e:
        print(f"Error installing Playwright: {e}")

class ProductHuntScraper:
    def __init__(self, headless=True):
        self.headless = headless
        self.playwright = None
        self.browser = None
        self.context = None

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()

    def start(self):
        """Starts the Playwright browser session."""
        install_playwright_browser()
        self.playwright = sync_playwright().start()
        
        try:
            self.browser = self.playwright.chromium.launch(
                headless=self.headless,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu'
                ]
            )
        except Exception as e:
            print(f"Launch failed, retrying after install: {e}")
            install_playwright_browser()
            self.browser = self.playwright.chromium.launch(
                headless=self.headless,
                args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
            )

        self.context = self.browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080}
        )

    def stop(self):
        """Closes the browser session."""
        if self.context:
            self.context.close()
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()

    def scrape_url(self, url, retry_count=0, max_retries=2):
        """Scrapes a single URL using the active browser context with automatic retry."""
        if not self.context:
            raise RuntimeError("Browser not started. Use 'with ProductHuntScraper() as scraper:' or call scraper.start() first.")

        retry_suffix = f" (Retry {retry_count}/{max_retries})" if retry_count > 0 else ""
        print(f"Scraping: {url}{retry_suffix}")
        page = self.context.new_page()
        
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

        try:
            # Reduced timeout to fail faster on bad pages
            page.goto(url, timeout=30000, wait_until="domcontentloaded")
            
            # Fast check for content
            try:
                page.wait_for_selector('h1', timeout=10000)
            except:
                print(f"Warning: Timeout waiting for h1 on {url}")

            content = page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            self._parse_content(soup, data)
            
            # Check if scrape was successful (got at least product name)
            if not data['product_name'] and retry_count < max_retries:
                print(f"⚠️ Incomplete data extracted, retrying...")
                page.close()
                time.sleep(2 ** retry_count)  # Exponential backoff: 1s, 2s, 4s
                return self.scrape_url(url, retry_count + 1, max_retries)

        except Exception as e:
            print(f"❌ Error scraping {url}: {e}")
            data['error'] = str(e)
            
            # Retry on error
            if retry_count < max_retries:
                print(f"⚠️ Retrying after error...")
                page.close()
                time.sleep(2 ** retry_count)  # Exponential backoff
                return self.scrape_url(url, retry_count + 1, max_retries)
        finally:
            page.close()
            
        return data

    def _parse_content(self, soup, data):
        """Helper to parse HTML/JSON-LD content."""
        # 1. Try JSON-LD first
        json_ld = soup.find('script', type='application/ld+json')
        if json_ld:
            try:
                data_json = json.loads(json_ld.string)
                target_item = None
                
                if isinstance(data_json, list):
                    for item in data_json:
                        if item.get('@type') in ['Product', 'WebApplication', ['WebApplication', 'Product']]:
                            target_item = item
                            break
                elif isinstance(data_json, dict):
                     target_item = data_json

                if target_item:
                    self._map_json_ld(target_item, data)
            except Exception as e:
                print(f"Error parsing JSON-LD: {e}")

        # 2. Try Apollo State (Robust fallback for Reviews/Other pages)
        if not data['product_name'] or not data['rating']:
             self._extract_apollo_state(soup, data)

        # 3. HTML Fallbacks
        if not data['product_name']:
            name_el = soup.find('h1')
            if name_el:
                data['product_name'] = name_el.text.strip()
        
        
        if not data['website_url']:
            # Try multiple selectors for website link
            selectors = [
                ('a', {'data-test': 'visit-website-button'}),
                ('a', {'class': 'styles_websiteLink__zSEaT'}),
                ('a', lambda tag: (tag and tag.get('href', '') and 
                                  tag.get('href', '').startswith('http') and 
                                  tag.text and 
                                  ('Visit' in tag.text or 'Website' in tag.text or 'Get' in tag.text)))
            ]
            
            for selector in selectors:
                try:
                    if isinstance(selector[1], dict):
                        website_link = soup.find(selector[0], selector[1])
                    else:
                        website_link = soup.find(selector[0], selector[1])
                    
                    if website_link:
                        href = website_link.get('href', '')
                        # Filter out producthunt.com links
                        if href and 'producthunt.com' not in href:
                            data['website_url'] = href
                            break
                except Exception as e:
                    # Skip this selector if it fails
                    continue

        if not data['tagline']:
            for tag in ['h2.text-18', 'h2.font-medium', 'h2']:
                parts = tag.split('.')
                tag_name = parts[0]
                cls_name = parts[1] if len(parts) > 1 else None
                
                if cls_name:
                    el = soup.find(tag_name, class_=cls_name)
                else:
                    el = soup.find(tag_name)
                
                if el:
                    data['tagline'] = el.text.strip()
                    break

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

        if not data['reviews_count']:
            reviews_link = soup.find('a', href=lambda x: x and '/reviews' in x)
            if reviews_link and 'review' in reviews_link.text.lower():
                data['reviews_count'] = reviews_link.text.strip()
            else:
                reviews_el = soup.find(string=lambda x: x and 'review' in x.lower() and x.parent.name not in ['script', 'style'])
                if reviews_el:
                    data['reviews_count'] = reviews_el.parent.text.strip()

        # Categories fallback
        if not data['categories']:
            category_links = soup.find_all('a', href=lambda x: x and '/categories/' in x)
            cats = []
            for link in category_links:
                c = link.text.strip()
                if c and c not in cats:
                    cats.append(c)
            if cats:
                data['categories'] = ', '.join(cats[:5])
    
    def _map_json_ld(self, item, data):
        if item.get('name'):
            data['product_name'] = item['name']
        
        if item.get('aggregateRating'):
            rating_obj = item['aggregateRating']
            if rating_obj.get('ratingValue'):
                data['rating'] = str(rating_obj['ratingValue'])
            if rating_obj.get('ratingCount'):
                data['reviews_count'] = str(rating_obj['ratingCount'])
        
        if item.get('applicationCategory'):
            data['categories'] = item['applicationCategory']

    def _extract_apollo_state(self, soup, data):
        """Extracts data from Apollo Client state (usually in scripts)."""
        try:
            scripts = soup.find_all('script')
            apollo_script = None
            for s in scripts:
                content = s.get_text()
                if content and 'ApolloSSRDataTransport' in content:
                    apollo_script = content
                    break
            
            if not apollo_script:
                return

            # Format is usually: (window[Symbol.for("ApolloSSRDataTransport")] ??= []).push({...})
            start_marker = '.push('
            end_marker = ')'
            
            start_idx = apollo_script.find(start_marker)
            if start_idx == -1: return

            json_start = start_idx + len(start_marker)
            json_end = apollo_script.rfind(end_marker)
            
            if json_end <= json_start: return

            json_str = apollo_script[json_start:json_end]
            
            # Sanitize JS 'undefined' which refers to missing/null data in Apollo state
            json_str = json_str.replace('undefined', 'null')
            
            # Sanitize potentially unquoted keys if any (though usually Apollo is JSON-like)
            # But the main issue observed was 'undefined'
            
            apollo_data = json.loads(json_str)
            
            # Extract slug from URL for verification
            # URL format: .../products/slug OR .../products/slug/reviews
            # Remove query params
            clean_url = data['url'].split('?')[0].split('#')[0]
            parts = clean_url.rstrip('/').split('/')
            
            target_slug = None
            if 'products' in parts:
                try:
                    p_index = parts.index('products')
                    if len(parts) > p_index + 1:
                        target_slug = parts[p_index + 1]
                except:
                    pass
            
            # Navigate rehydrate -> keys -> structuredData
            if 'rehydrate' in apollo_data:
                for key, value in apollo_data['rehydrate'].items():
                    if value and 'data' in value and value['data'] and 'product' in value['data']:
                        prod = value['data']['product']
                        
                        # VERIFY SLUG matches target (if we could extract one)
                        # This prevents grabbing "Related Products" or "Alternatives" data
                        if target_slug and prod.get('slug') and prod.get('slug').lower() != target_slug.lower():
                            continue

                        # Prioritize structuredData if available
                        if 'structuredData' in prod:
                             self._map_json_ld(prod['structuredData'], data)
                        
                        # Direct Product Object props
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
                            
                        # If found (and slug matched), stop searching
                        if data['product_name']:
                            break

        except Exception as e:
            print(f"Error parsing Apollo state: {e}")

# Legacy wrapper for backward compatibility with app.py
def scrape_producthunt(url):
    """
    One-off scraper function. Warning: inefficient for bulk operations
    as it launches a browser instance for a single URL.
    """
    with ProductHuntScraper() as scraper:
        return scraper.scrape_url(url)

if __name__ == "__main__":
    if not os.path.exists('urls.txt'):
        print("urls.txt not found. Please create it with one URL per line.")
        exit(1)

    with open('urls.txt', 'r') as f:
        urls = [line.strip() for line in f if line.strip()]
    
    if not urls:
        print("No URLs found in urls.txt")
        exit(1)

    print(f"Loaded {len(urls)} URLs. Starting high-performance scraper...")
    
    results = []
    
    # Use the context manager to keep browser open across all URLs
    with ProductHuntScraper(headless=True) as scraper:
        for i, url in enumerate(urls, 1):
            print(f"[{i}/{len(urls)}] Processing...")
            result = scraper.scrape_url(url)
            results.append(result)
            # Fixed 25 second delay to avoid any blocking
            if i < len(urls):  # Don't wait after the last URL
                delay = 25
                print(f"Waiting {delay}s...")
                time.sleep(delay)

    # Save to CSV
    try:
        df = pd.DataFrame(results)
        # Timestamped filename to avoid overwriting
        timestamp = time.strftime("%Y-%m-%dT%H-%M")
        output_file = f'final files/{timestamp}_export.csv'
        
        # Ensure directory exists
        os.makedirs('final files', exist_ok=True)
        
        df.to_csv(output_file, index=False)
        print(f"\\n✅ Done! Saved {len(results)} results to {output_file}")
    except Exception as e:
        print(f"Error saving CSV: {e}")
