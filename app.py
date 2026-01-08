import streamlit as st
import pandas as pd
import time
import base64
# Import the robust scraper logic from our updated scraper.py
from scraper import scrape_producthunt

# --- Page Configuration ---
st.set_page_config(
    page_title="Product Hunt Scraper",
    page_icon="🚀",
    layout="wide"
)

# --- Main App ---
def main():
    st.title("🚀 Product Hunt Scraper")
    st.markdown("Extract product details directly from Product Hunt URLs.")
    
    # Check if we successfully imported the new scraper logic
    # (Just a sanity check implicitly via usage)

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
            
            # Using the improved scraper function
            data = scrape_producthunt(url)
            results.append(data)
            
            # Update table on the fly
            df_live = pd.DataFrame(results)
            table_placeholder.dataframe(df_live)
            
            progress_bar.progress((i + 1) / len(urls))
            
            # Note: scrape_producthunt inside scraper.py handles internal short delays,
            # but we can add a small UI delay here if desired, or rely on scraper.py.
            
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
