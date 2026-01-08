import streamlit as st
import pandas as pd
import cloudscraper
from bs4 import BeautifulSoup
import time
import base64
import json

# --- Page Configuration ---
st.set_page_config(
    page_title="Product Hunt Scraper",
    page_icon="🚀",
    layout="wide"
)

# --- Scraper Function ---
def scrape_producthunt(url):
    """
    Scrapes a single Product Hunt URL for product details using Cloudscraper and JSON-LD.
    """
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

        # 1. Try JSON-LD first
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
                
                # Note: We prefer HTML tagline usually, but can look here if needed
                # if data_json.get('description'): 
                #     data['tagline'] = data_json['description']
                
                if data_json.get('aggregateRating'):
                    rating_obj = data_json['aggregateRating']
                    if rating_obj.get('ratingValue'):
                        data['rating'] = str(rating_obj['ratingValue'])
                    if rating_obj.get('ratingCount'):
                        data['reviews_count'] = str(rating_obj['ratingCount'])
                
                if data_json.get('applicationCategory'):
                    data['categories'] = data_json['applicationCategory']

            except Exception as e:
                pass # Silently fail JSON parsing and move to fallback

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
        # HTML is often better for multiple categories
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
            'error': str(e)
        }

# --- Main App ---
def main():
    st.title("🚀 Product Hunt Scraper")
    st.markdown("Extract product details directly from Product Hunt URLs.")

    # Input Section
    st.sidebar.header("Input Data")
    input_method = st.sidebar.radio("Choose input method:", ["Manual Entry", "Upload Text File"])
    
    urls = []
    
    if input_method == "Manual Entry":
        raw_urls = st.sidebar.text_area("Paste URLs (one per line)", height=200)
        if raw_urls:
            urls = [url.strip() for url in raw_urls.split('\n') if url.strip()]
    else:
        uploaded_file = st.sidebar.file_uploader("Upload urls.txt", type=['txt'])
        if uploaded_file is not None:
            stringio = uploaded_file.getvalue().decode("utf-8")
            urls = [line.strip() for line in stringio.split('\n') if line.strip()]

    # Main Area logic
    if not urls:
        st.info("👈 Please provide some URLs in the sidebar to get started!")
        return

    st.write(f"**Loaded {len(urls)} URLs for scraping.**")
    
    if st.button("Start Scraping", type="primary"):
        progress_bar = st.progress(0)
        status_text = st.empty()
        results = []
        
        table_placeholder = st.empty()

        for i, url in enumerate(urls):
            status_text.text(f"Processing ({i+1}/{len(urls)}): {url}")
            
            data = scrape_producthunt(url)
            results.append(data)
            
            # Update table on the fly
            df_live = pd.DataFrame(results)
            table_placeholder.dataframe(df_live)
            
            progress_bar.progress((i + 1) / len(urls))
            time.sleep(1) # Polite delay

        status_text.text("✅ Scraping Complete!")
        progress_bar.progress(100)
        
        # Final DataFrame
        df = pd.DataFrame(results)
        
        # CSV Download
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Download CSV",
            data=csv,
            file_name='producthunt_data.csv',
            mime='text/csv',
        )

if __name__ == "__main__":
    main()
