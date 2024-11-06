import streamlit as st
import requests
from bs4 import BeautifulSoup
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from textblob import TextBlob
import pandas as pd
from langdetect import detect, DetectorFactory, LangDetectException
import textstat
import validators
import json
import random
import time
from urllib.parse import urlparse
from requests_html import HTMLSession
from urllib.robotparser import RobotFileParser
import hashlib

# Seed the detector for consistent results
DetectorFactory.seed = 0

# Initialize random user-agents to bypass bot detection
def get_random_user_agent():
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.82 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Safari/605.1.15',
        'Mozilla/5.0 (Linux; Android 10; SM-G960F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.90 Mobile Safari/537.36',
        'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1'
    ]
    return random.choice(user_agents)

# Function to check if URL is valid
def is_valid_url(url):
    return validators.url(url)

# Function to check if scraping is allowed based on robots.txt
def is_scraping_allowed(url):
    parsed_url = urlparse(url)
    robots_url = f"{parsed_url.scheme}://{parsed_url.netloc}/robots.txt"
    rp = RobotFileParser()
    rp.set_url(robots_url)
    rp.read()
    return rp.can_fetch("*", url)

# Detect language
def detect_language(text):
    if not text or len(text.split()) < 3:
        return "Insufficient text for detection"
    try:
        return detect(text)
    except LangDetectException:
        return "Detection failed"

# Extract meta tags
def extract_meta_tags(soup):
    meta_info = {}
    for tag in soup.find_all("meta"):
        if tag.get("name"):
            meta_info[tag.get("name")] = tag.get("content")
        elif tag.get("property"):
            meta_info[tag.get("property")] = tag.get("content")
    return meta_info

# Extract all links and categorize them
def extract_links(url, soup):
    internal_links, external_links = [], []
    for link in soup.find_all("a", href=True):
        if link["href"].startswith("http"):
            if url in link["href"]:
                internal_links.append(link["href"])
            else:
                external_links.append(link["href"])
    return internal_links, external_links

# Extract JSON-LD structured data
def extract_json_ld(soup):
    json_ld_data = []
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            json_ld_data.append(json.loads(script.string))
        except json.JSONDecodeError:
            continue
    return json_ld_data

# Detect keywords density
def get_keyword_density(text):
    words = text.split()
    return {word: words.count(word) / len(words) * 100 for word in set(words)}

# Extract main content from paragraphs
def extract_content(soup):
    return " ".join([p.get_text() for p in soup.find_all("p")])

# Generate word cloud
def generate_wordcloud(keyword_density):
    wordcloud = WordCloud(width=800, height=400).generate_from_frequencies(keyword_density)
    plt.figure(figsize=(10, 5))
    plt.imshow(wordcloud, interpolation="bilinear")
    plt.axis("off")
    return wordcloud

# Scrape the website and extract features
def scrape_website(url):
    headers = {"User-Agent": get_random_user_agent()}
    session = HTMLSession()
    response = session.get(url, headers=headers)

    if response.status_code != 200:
        st.warning("Could not access the webpage.")
        return None

    soup = BeautifulSoup(response.content, "html.parser")
    data = {}

    # 1. Page Title
    data["Page Title"] = soup.title.string if soup.title else "No title"

    # 2. Meta tags
    data["Meta Tags"] = extract_meta_tags(soup)

    # 3. Main Content
    content = extract_content(soup)
    data["Main Content"] = content[:1000] + "..."  # Displaying a snippet

    # 4. Keyword Density
    data["Keyword Density"] = get_keyword_density(content)

    # 5. Word Cloud
    if data["Keyword Density"]:
        wordcloud = generate_wordcloud(data["Keyword Density"])
        st.pyplot(wordcloud.to_array())

    # 6. Sentiment Analysis
    sentiment = TextBlob(content).sentiment.polarity
    data["Sentiment Score"] = sentiment

    # 7. Language Detection
    data["Detected Language"] = detect_language(content)

    # 8. Internal and External Links
    internal_links, external_links = extract_links(url, soup)
    data["Internal Links Count"] = len(internal_links)
    data["External Links Count"] = len(external_links)

    # 9. JSON-LD Structured Data
    data["JSON-LD Data"] = extract_json_ld(soup)

    # 10. Readability Score
    data["Readability Score"] = textstat.flesch_kincaid_grade(content)

    # 11. Social Media Links
    social_links = [link for link in external_links if any(domain in link for domain in ["facebook", "twitter", "instagram", "linkedin"])]
    data["Social Media Links"] = social_links

    # 12. Image Data
    image_data = [{"src": img.get("src"), "alt": img.get("alt", "No alt text")} for img in soup.find_all("img", src=True)]
    data["Image Data"] = image_data

    # 13. Video Links
    data["Video Links"] = [video["src"] for video in soup.find_all("video")]

    # 14. Broken Links
    broken_links = []
    for link in internal_links + external_links:
        try:
            link_response = requests.head(link, timeout=5)
            if link_response.status_code != 200:
                broken_links.append(link)
        except:
            broken_links.append(link)
    data["Broken Links"] = broken_links

    # 15. Author Information
    author = soup.find(attrs={"name": "author"})
    data["Author"] = author["content"] if author else "Not available"

    # 16. Robots.txt Check
    data["Scraping Allowed"] = is_scraping_allowed(url)

    # 17. Headings Structure
    headings = {}
    for level in range(1, 7):
        headings[f"h{level}"] = [h.get_text() for h in soup.find_all(f"h{level}")]
    data["Headings"] = headings

    # 18. Table Data
    tables = []
    for table in soup.find_all("table"):
        table_data = [[cell.get_text() for cell in row.find_all(["th", "td"])] for row in table.find_all("tr")]
        tables.append(table_data)
    data["Tables"] = tables

    # 19. Favicon
    favicon = soup.find("link", rel="icon")
    data["Favicon URL"] = favicon["href"] if favicon else "No favicon found"

    # 20. Canonical Link
    canonical = soup.find("link", rel="canonical")
    data["Canonical Link"] = canonical["href"] if canonical else "No canonical link"

    # 21. Most Common Words
    data["Common Words"] = pd.Series(content.split()).value_counts().head(10).to_dict()

    # 22. FAQ Schema (if present in JSON-LD)
    data["FAQs"] = [faq for faq in data["JSON-LD Data"] if faq.get("@type") == "FAQPage"]

    # 23. Open Graph and Twitter Meta Data
    data["Open Graph and Twitter Data"] = {key: value for key, value in data["Meta Tags"].items() if "og:" in key or "twitter:" in key}

    # 24. Last Modified Date (if present)
    last_modified = response.headers.get("Last-Modified")
    data["Last Modified"] = last_modified if last_modified else "No last modified date found"

    # 25. Word Count
    data["Word Count"] = len(content.split())

    return data

# Streamlit app
st.title("Advanced Web Scraping and Analysis Tool")

url = st.text_input("Enter the URL to scrape:", "https://example.com")

if st.button("Scrape Website"):
    if not is_valid_url(url):
        st.error("Please enter a valid URL.")
    elif not is_scraping_allowed(url):
        st.warning("Scraping not allowed on this website.")
    else:
        with st.spinner("Scraping and analyzing..."):
            scraped_data = scrape_website(url)
            if scraped_data:
                st.json(scraped_data)
