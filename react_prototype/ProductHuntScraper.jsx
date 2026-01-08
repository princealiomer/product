import React, { useState } from "react";
import {
  Download,
  Upload,
  Loader2,
  CheckCircle,
  AlertCircle,
} from "lucide-react";

const ProductHuntScraper = () => {
  const [urls, setUrls] = useState("");
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState({ current: 0, total: 0 });

  const extractUrls = (htmlContent) => {
    const parser = new DOMParser();
    const doc = parser.parseFromString(htmlContent, "text/html");

    const urlData = {
      productUrl: "",
      websiteUrl: "",
      productName: "",
      tagline: "",
      rating: "",
      reviews: "",
      categories: [],
    };

    // Extract product name
    const nameEl = doc.querySelector('[data-test*="thumbnail"]');
    if (nameEl) {
      urlData.productName = nameEl.getAttribute("alt") || "";
    }

    // Extract tagline
    const taglineEl = doc.querySelector("h2.text-18");
    if (taglineEl) {
      urlData.tagline = taglineEl.textContent.trim();
    }

    // Extract website URL
    const websiteLink = doc.querySelector(
      'a[data-test="visit-website-button"]'
    );
    if (websiteLink) {
      urlData.websiteUrl = websiteLink.getAttribute("href") || "";
    }

    // Extract rating
    const ratingEl = doc.querySelector(".text-14.font-medium");
    if (ratingEl) {
      urlData.rating = ratingEl.textContent.trim();
    }

    // Extract reviews count
    const reviewsLink = doc.querySelector('a[href*="/reviews"]');
    if (reviewsLink) {
      const reviewText = reviewsLink.textContent;
      const match = reviewText.match(/(\d+)\s*review/);
      if (match) {
        urlData.reviews = match[1];
      }
    }

    // Extract categories
    const categoryLinks = doc.querySelectorAll('a[href*="/categories"]');
    categoryLinks.forEach((link) => {
      const category = link.textContent.trim();
      if (category && !urlData.categories.includes(category)) {
        urlData.categories.push(category);
      }
    });

    return urlData;
  };

  const scrapeUrl = async (url) => {
    try {
      // Since we can't directly fetch due to CORS, we'll provide instructions
      // In a real implementation, you'd need a backend proxy or browser extension
      return {
        url,
        status: "pending",
        message: "Manual scraping required - see instructions below",
      };
    } catch (error) {
      return {
        url,
        status: "error",
        message: error.message,
      };
    }
  };

  const handleFileUpload = (event) => {
    const file = event.target.files[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = (e) => {
        setUrls(e.target.result);
      };
      reader.readAsText(file);
    }
  };

  const processScraping = async () => {
    const urlList = urls.split("\n").filter((url) => url.trim());
    setProgress({ current: 0, total: urlList.length });
    setResults([]);
    setLoading(true);

    const scrapedResults = [];

    for (let i = 0; i < urlList.length; i++) {
      const url = urlList[i].trim();
      if (url) {
        const result = await scrapeUrl(url);
        scrapedResults.push(result);
        setProgress({ current: i + 1, total: urlList.length });
      }
    }

    setResults(scrapedResults);
    setLoading(false);
  };

  const exportToCSV = () => {
    if (results.length === 0) return;

    const headers = [
      "URL",
      "Product Name",
      "Website URL",
      "Tagline",
      "Rating",
      "Reviews",
      "Categories",
      "Status",
    ];
    const rows = results.map((r) => [
      r.url,
      r.productName || "",
      r.websiteUrl || "",
      r.tagline || "",
      r.rating || "",
      r.reviews || "",
      (r.categories || []).join("; "),
      r.status,
    ]);

    const csvContent = [
      headers.join(","),
      ...rows.map((row) => row.map((cell) => `"${cell}"`).join(",")),
    ].join("\n");

    const blob = new Blob([csvContent], { type: "text/csv" });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `producthunt-urls-${Date.now()}.csv`;
    a.click();
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 p-4 md:p-8">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="bg-white rounded-2xl shadow-lg p-6 mb-6">
          <div className="flex items-center gap-3 mb-2">
            <svg
              className="w-8 h-8 text-blue-600"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1"
              />
            </svg>
            <h1 className="text-3xl font-bold text-gray-900">
              Product Hunt URL Scraper
            </h1>
          </div>
          <p className="text-gray-600">
            Extract product data from Product Hunt pages
          </p>
        </div>

        {/* Input Section */}
        <div className="bg-white rounded-2xl shadow-lg p-6 mb-6">
          <div className="mb-4">
            <label className="block text-sm font-semibold text-gray-700 mb-2">
              Enter URLs (one per line)
            </label>
            <textarea
              className="w-full h-48 px-4 py-3 border-2 border-gray-200 rounded-xl focus:border-blue-500 focus:outline-none resize-none font-mono text-sm"
              placeholder="https://www.producthunt.com/products/seo-bot&#10;https://www.producthunt.com/products/example&#10;..."
              value={urls}
              onChange={(e) => setUrls(e.target.value)}
            />
          </div>

          <div className="flex gap-3 flex-wrap">
            <label className="cursor-pointer">
              <input
                type="file"
                accept=".txt,.csv"
                onChange={handleFileUpload}
                className="hidden"
              />
              <div className="flex items-center gap-2 px-6 py-3 bg-gray-100 hover:bg-gray-200 rounded-xl font-semibold text-gray-700 transition-colors">
                <Upload className="w-5 h-5" />
                Upload File
              </div>
            </label>

            <button
              onClick={processScraping}
              disabled={!urls.trim() || loading}
              className="flex items-center gap-2 px-6 py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed rounded-xl font-semibold text-white transition-colors"
            >
              {loading ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  Processing...
                </>
              ) : (
                <>
                  <CheckCircle className="w-5 h-5" />
                  Start Scraping
                </>
              )}
            </button>
          </div>

          {loading && (
            <div className="mt-4">
              <div className="flex justify-between text-sm text-gray-600 mb-2">
                <span>Progress</span>
                <span>
                  {progress.current} / {progress.total}
                </span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-3">
                <div
                  className="bg-blue-600 h-3 rounded-full transition-all duration-300"
                  style={{
                    width: `${(progress.current / progress.total) * 100}%`,
                  }}
                />
              </div>
            </div>
          )}
        </div>

        {/* Important Note */}
        <div className="bg-yellow-50 border-2 border-yellow-200 rounded-2xl p-6 mb-6">
          <div className="flex gap-3">
            <AlertCircle className="w-6 h-6 text-yellow-600 flex-shrink-0 mt-1" />
            <div>
              <h3 className="font-bold text-yellow-900 mb-2">
                Important: CORS Limitation
              </h3>
              <p className="text-yellow-800 mb-3">
                Due to browser security restrictions (CORS), this app cannot
                directly fetch Product Hunt pages.
              </p>
              <div className="bg-white rounded-lg p-4 text-sm">
                <p className="font-semibold text-gray-900 mb-2">
                  Recommended Solutions:
                </p>
                <ol className="list-decimal list-inside space-y-2 text-gray-700">
                  <li>
                    Use a <strong>browser extension</strong> like "Web Scraper"
                    or "Data Miner"
                  </li>
                  <li>
                    Use a <strong>backend server</strong> with Python (Beautiful
                    Soup, Scrapy)
                  </li>
                  <li>
                    Use <strong>Puppeteer/Playwright</strong> for automated
                    scraping
                  </li>
                  <li>Manually save HTML files and parse them offline</li>
                </ol>
              </div>
            </div>
          </div>
        </div>

        {/* Results */}
        {results.length > 0 && (
          <div className="bg-white rounded-2xl shadow-lg p-6">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-bold text-gray-900">
                Results ({results.length})
              </h2>
              <button
                onClick={exportToCSV}
                className="flex items-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-700 rounded-lg font-semibold text-white transition-colors"
              >
                <Download className="w-5 h-5" />
                Export CSV
              </button>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b-2 border-gray-200">
                    <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700">
                      URL
                    </th>
                    <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700">
                      Status
                    </th>
                    <th className="px-4 py-3 text-left text-sm font-semibold text-gray-700">
                      Message
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {results.map((result, idx) => (
                    <tr
                      key={idx}
                      className="border-b border-gray-100 hover:bg-gray-50"
                    >
                      <td className="px-4 py-3 text-sm text-blue-600 truncate max-w-md">
                        {result.url}
                      </td>
                      <td className="px-4 py-3">
                        <span
                          className={`px-3 py-1 rounded-full text-xs font-semibold ${
                            result.status === "success"
                              ? "bg-green-100 text-green-700"
                              : result.status === "error"
                              ? "bg-red-100 text-red-700"
                              : "bg-yellow-100 text-yellow-700"
                          }`}
                        >
                          {result.status}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-600">
                        {result.message}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Python Script Alternative */}
        <div className="bg-gray-900 rounded-2xl shadow-lg p-6 mt-6 text-white">
          <h3 className="text-lg font-bold mb-3">Alternative: Python Script</h3>
          <p className="text-gray-300 mb-4 text-sm">
            Use this Python script for actual scraping:
          </p>
          <pre className="bg-black rounded-lg p-4 overflow-x-auto text-xs">
            {`import requests
from bs4 import BeautifulSoup
import pandas as pd
import time

def scrape_producthunt(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Extract data
    data = {
        'url': url,
        'product_name': '',
        'website_url': '',
        'tagline': '',
        'rating': '',
        'reviews': ''
    }
    
    # Product name
    name_el = soup.find('h1', class_='font-semibold')
    if name_el:
        data['product_name'] = name_el.text.strip()
    
    # Website URL
    website_link = soup.find('a', {'data-test': 'visit-website-button'})
    if website_link:
        data['website_url'] = website_link.get('href', '')
    
    return data

# Read URLs
with open('urls.txt', 'r') as f:
    urls = [line.strip() for line in f if line.strip()]

# Scrape
results = []
for url in urls:
    print(f"Scraping: {url}")
    result = scrape_producthunt(url)
    results.append(result)
    time.sleep(2)  # Be respectful

# Save to CSV
df = pd.DataFrame(results)
df.to_csv('producthunt_data.csv', index=False)
print("Done!")`}
          </pre>
        </div>
      </div>
    </div>
  );
};

export default ProductHuntScraper;
