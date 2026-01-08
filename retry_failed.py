"""
Retry failed scrapes from latest.csv
Only processes entries with missing website_url
"""
import pandas as pd
from scraper import ProductHuntScraper
import time

# Read the CSV
df = pd.read_csv(r'D:\product hunt\final files\latest.csv')

# Find failed entries (missing website_url)
failed = df[df['website_url'].isna() | (df['website_url'] == '')]
print(f"Found {len(failed)} failed entries to retry")

if len(failed) == 0:
    print("No failed entries to retry!")
    exit(0)

# Extract URLs to retry
retry_urls = failed['url'].tolist()

print(f"\nRetrying {len(retry_urls)} URLs...")
results = []

with ProductHuntScraper(headless=True) as scraper:
    for i, url in enumerate(retry_urls, 1):
        print(f"[{i}/{len(retry_urls)}] Retrying: {url}")
        result = scraper.scrape_url(url)
        results.append(result)
        
        # Random delay
        if i < len(retry_urls):
            import random
            delay = random.uniform(3, 6)  # Longer delay for retries
            print(f"Waiting {delay:.2f}s...")
            time.sleep(delay)

# Create results DataFrame
results_df = pd.DataFrame(results)

# Show success rate
success = results_df['website_url'].notna() & (results_df['website_url'] != '')
print(f"\n=== Retry Results ===")
print(f"Successful: {success.sum()}/{len(results_df)}")
print(f"Still failed: {(~success).sum()}/{len(results_df)}")

# Save retry results
timestamp = time.strftime("%Y-%m-%dT%H-%M")
output_file = f'final files/{timestamp}_retry_results.csv'
results_df.to_csv(output_file, index=False)
print(f"\nSaved retry results to: {output_file}")

# Update the original CSV with successful retries
for idx, row in results_df.iterrows():
    if pd.notna(row['website_url']) and row['website_url'] != '':
        # Find matching row in original df by URL
        mask = df['url'] == row['url']
        if mask.any():
            # Update the row
            df.loc[mask, 'website_url'] = row['website_url']
            df.loc[mask, 'tagline'] = row['tagline']
            df.loc[mask, 'rating'] = row['rating']
            df.loc[mask, 'reviews_count'] = row['reviews_count']
            df.loc[mask, 'categories'] = row['categories']

# Save updated CSV
updated_file = f'final files/{timestamp}_updated.csv'
df.to_csv(updated_file, index=False)
print(f"Saved updated CSV to: {updated_file}")

# Final stats
final_missing = df['website_url'].isna().sum() + (df['website_url'] == '').sum()
print(f"\n=== Final Stats ===")
print(f"Total products: {len(df)}")
print(f"Complete: {len(df) - final_missing} ({(len(df) - final_missing)/len(df)*100:.1f}%)")
print(f"Still missing URL: {final_missing} ({final_missing/len(df)*100:.1f}%)")
