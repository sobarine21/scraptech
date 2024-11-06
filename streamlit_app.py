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
from urllib.parse import urlparse, urljoin
from requests_html import HTMLSession
from urllib.robotparser import RobotFileParser
import re

# Seed the language detector for consistent results
DetectorFactory.seed = 0

# Random user agents to avoid bot detection
def get_random_user_agent():
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.82 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Safari/605.1.15',
        'Mozilla/5.0 (Linux; Android 10; SM-G960F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.90 Mobile Safari/537.36'
    ]
    return random.choice(user_agents)

# Check URL validity
def is_valid_url(url):
    return validators.url(url)

# Check if scraping is allowed
def is_scraping_allowed(url):
    parsed_url = urlparse(url)
    robots_url = f"{parsed_url.scheme}://{parsed_url.netloc}/robots.txt"
    rp = RobotFileParser()
    rp.set_url(robots_url)
    try:
        rp.read()
        return rp.can_fetch("*", url)
    except:
        return False

# Detect language
def detect_language(text):
    try:
        return detect(text)
    except LangDetectException:
        return "Language detection failed"

# Extract metadata tags
def extract_meta_tags(soup):
    meta_info = {}
    for tag in soup.find_all("meta"):
        if tag.get("name"):
            meta_info[tag.get("name")] = tag.get("content")
        elif tag.get("property"):
            meta_info[tag.get("property")] = tag.get("content")
    return meta_info

# Extract all links
def extract_links(url, soup):
    internal_links, external_links = set(), set()
    for link in soup.find_all("a", href=True):
        href = urljoin(url, link["href"])
        if url in href:
            internal_links.add(href)
        else:
            external_links.add(href)
    return list(internal_links), list(external_links)

# Extract and parse JSON-LD
def extract_json_ld(soup):
    json_ld_data = []
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            json_ld_data.append(json.loads(script.string))
        except json.JSONDecodeError:
            continue
    return json_ld_data

# Detect keyword density
def get_keyword_density(text):
    words = text.split()
    return {word: words.count(word) / len(words) * 100 for word in set(words)}

# Main content extraction
def extract_content(soup):
    return " ".join([p.get_text() for p in soup.find_all("p")])

# Generate and return word cloud
def generate_wordcloud(keyword_density):
    wordcloud = WordCloud(width=800, height=400).generate_from_frequencies(keyword_density)
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.imshow(wordcloud, interpolation="bilinear")
    ax.axis("off")
    return fig

# Function to scrape all possible data
def scrape_website(url):
    headers = {"User-Agent": get_random_user_agent()}
    session = HTMLSession()
    response = session.get(url, headers=headers)

    if response.status_code != 200:
        st.warning("Could not access the webpage.")
        return None

    soup = BeautifulSoup(response.content, "html.parser")
    data = {}

    # Basic Data
    data["Page Title"] = soup.title.string if soup.title else "No title"
    data["Meta Tags"] = extract_meta_tags(soup)
    content = extract_content(soup)
    data["Main Content Snippet"] = content[:1000] + "..."

    # Keyword Density & Word Cloud
    data["Keyword Density"] = get_keyword_density(content)
    if data["Keyword Density"]:
        wordcloud_fig = generate_wordcloud(data["Keyword Density"])
        st.pyplot(wordcloud_fig)

    # Sentiment Analysis
    sentiment = TextBlob(content).sentiment.polarity
    data["Sentiment Score"] = sentiment

    # Language Detection
    data["Detected Language"] = detect_language(content)

    # Links and JSON-LD data
    internal_links, external_links = extract_links(url, soup)
    data["Internal Links"] = internal_links
    data["External Links"] = external_links
    data["JSON-LD Data"] = extract_json_ld(soup)

    # Extended Data
    data["Readability Score"] = textstat.flesch_kincaid_grade(content)
    data["Image Data"] = [{"src": img.get("src"), "alt": img.get("alt", "No alt text")} for img in soup.find_all("img", src=True)]
    data["Video Links"] = [video.get("src") for video in soup.find_all("video", src=True)]
    data["Script URLs"] = [script.get("src") for script in soup.find_all("script", src=True)]

    # Detect Emails, Phones, and Social Media Links
    data["Emails"] = re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", content)
    data["Phone Numbers"] = re.findall(r"\+?\d[\d -]{8,}\d", content)
    data["Social Media Links"] = [link for link in external_links if any(domain in link for domain in ["facebook", "twitter", "instagram", "linkedin"])]

    # Accessibility and Structured Data
    data["Accessibility (ARIA) Tags"] = [tag.get("aria-label") for tag in soup.find_all(attrs={"aria-label": True})]
    data["Headings"] = {f"h{level}": [h.get_text() for h in soup.find_all(f"h{level}")] for level in range(1, 7)}
    data["Tables"] = [[cell.get_text() for cell in row.find_all(["th", "td"])] for row in soup.find_all("table")]

    # Advanced Features
    data["Captcha Detected"] = "Yes" if "captcha" in content.lower() else "No"
    data["HTTPS Enabled"] = urlparse(url).scheme == "https"
    data["Page Load Speed"] = round(response.elapsed.total_seconds(), 2)

    # Ads & Downloads
    data["Ads Detected"] = any("ads" in script["src"] for script in soup.find_all("script", src=True))
    data["File Downloads (PDFs)"] = [link["href"] for link in soup.find_all("a", href=True) if link["href"].endswith(".pdf")]

    return data

# Streamlit UI
st.title("Ultimate Web Scraper and Data Extractor")

url = st.text_input("Enter a URL for extraction")

if st.button("Extract Data"):
    if not is_valid_url(url):
        st.error("Please enter a valid URL.")
    elif not is_scraping_allowed(url):
        st.warning("Scraping is not allowed on this website.")
    else:
        with st.spinner("Extracting..."):
            scraped_data = scrape_website(url)
            if scraped_data:
                st.json(scraped_data)

