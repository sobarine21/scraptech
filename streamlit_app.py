import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
from textblob import TextBlob
import validators
import json
import random
import re
from urllib.parse import urlparse, urljoin
from requests_html import HTMLSession
from urllib.robotparser import RobotFileParser
import time

# Helper functions
def get_random_user_agent():
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.82 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Safari/605.1.15',
        'Mozilla/5.0 (Linux; Android 10; SM-G960F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.90 Mobile Safari/537.36'
    ]
    return random.choice(user_agents)

# URL Validation
def is_valid_url(url):
    return validators.url(url)

# Scraping Allowance
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

# Language Detection
def detect_language(text):
    try:
        return detect(text)
    except LangDetectException:
        return "Language detection failed"

# Metadata Extraction
def extract_meta_tags(soup):
    meta_info = {}
    for tag in soup.find_all("meta"):
        if tag.get("name"):
            meta_info[tag.get("name")] = tag.get("content")
        elif tag.get("property"):
            meta_info[tag.get("property")] = tag.get("content")
    return meta_info

# Extracting Links (Internal and External)
def extract_links(url, soup):
    internal_links, external_links = set(), set()
    for link in soup.find_all("a", href=True):
        href = urljoin(url, link["href"])
        if url in href:
            internal_links.add(href)
        else:
            external_links.add(href)
    return list(internal_links), list(external_links)

# Extract JSON-LD Data
def extract_json_ld(soup):
    json_ld_data = []
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            json_ld_data.append(json.loads(script.string))
        except json.JSONDecodeError:
            continue
    return json_ld_data

# Extracting Media (Images, Videos, Audio)
def extract_media(soup, url):
    images = [{"src": urljoin(url, img.get("src")), "alt": img.get("alt", "No alt text")} for img in soup.find_all("img", src=True)]
    videos = [{"src": urljoin(url, video.get("src"))} for video in soup.find_all("video", src=True)]
    audios = [{"src": urljoin(url, audio.get("src"))} for audio in soup.find_all("audio", src=True)]
    return images, videos, audios

# Extract Form Inputs (Text, Select, Checkbox)
def extract_forms(soup):
    forms = []
    for form in soup.find_all("form"):
        form_data = {
            "action": form.get("action"),
            "method": form.get("method"),
            "inputs": []
        }
        for input_tag in form.find_all("input"):
            form_data["inputs"].append({
                "name": input_tag.get("name"),
                "type": input_tag.get("type"),
                "value": input_tag.get("value")
            })
        for select_tag in form.find_all("select"):
            form_data["inputs"].append({
                "name": select_tag.get("name"),
                "options": [option.get("value") for option in select_tag.find_all("option")]
            })
        forms.append(form_data)
    return forms

# Extract HTTP Headers and Status Code
def extract_http_headers(url):
    response = requests.get(url)
    headers = dict(response.headers)
    return headers, response.status_code

# Extracting Comments
def extract_comments(soup):
    comments = [comment.string for comment in soup.find_all(string=lambda text: isinstance(text, Comment))]
    return comments

# Extract Tracking Scripts
def extract_tracking_scripts(soup):
    tracking_scripts = []
    for script in soup.find_all("script", src=True):
        src = script["src"]
        if "google-analytics" in src or "facebook" in src or "analytics" in src:
            tracking_scripts.append(src)
    return tracking_scripts

# Extract Redirect Information
def extract_redirect_chain(url):
    session = HTMLSession()
    response = session.get(url, allow_redirects=True)
    return response.history

# Extract Favicons and Open Graph Tags
def extract_favicon_and_og(soup):
    favicon = soup.find("link", rel="icon")
    og_tags = {tag.get("property"): tag.get("content") for tag in soup.find_all("meta") if "og:" in tag.get("property", "")}
    return favicon, og_tags

# Scrape All Data
def scrape_website(url):
    headers = {"User-Agent": get_random_user_agent()}
    session = HTMLSession()
    response = session.get(url, headers=headers)

    if response.status_code != 200:
        st.warning("Could not access the webpage.")
        return None

    soup = BeautifulSoup(response.content, "html.parser")
    data = {}

    # Basic Data Extraction
    data["Page Title"] = soup.title.string if soup.title else "No title"
    data["Meta Tags"] = extract_meta_tags(soup)
    content = " ".join([p.get_text() for p in soup.find_all("p")])
    data["Main Content Snippet"] = content[:1000] + "..."

    # Sentiment Analysis and Language Detection
    sentiment = TextBlob(content).sentiment.polarity
    data["Sentiment Score"] = sentiment
    data["Detected Language"] = detect_language(content)

    # Extract Links
    internal_links, external_links = extract_links(url, soup)
    data["Internal Links"] = internal_links
    data["External Links"] = external_links
    data["JSON-LD Data"] = extract_json_ld(soup)

    # Extract Media
    data["Images"], data["Videos"], data["Audios"] = extract_media(soup, url)

    # Forms & Inputs
    data["Forms"] = extract_forms(soup)

    # Extract Headers & Status Codes
    headers, status_code = extract_http_headers(url)
    data["HTTP Headers"] = headers
    data["Status Code"] = status_code

    # Comments
    data["Comments"] = extract_comments(soup)

    # Tracking Scripts
    data["Tracking Scripts"] = extract_tracking_scripts(soup)

    # Redirect Chain
    data["Redirect Chain"] = extract_redirect_chain(url)

    # Favicons & Open Graph Data
    favicon, og_tags = extract_favicon_and_og(soup)
    data["Favicon"] = favicon["href"] if favicon else "No favicon"
    data["Open Graph Tags"] = og_tags

    return data

# Streamlit Interface
st.title("Comprehensive Web Scraping Tool")
url = st.text_input("Enter a URL for analysis")

if st.button("Analyze"):
    if not is_valid_url(url):
        st.error("Please enter a valid URL.")
    elif not is_scraping_allowed(url):
        st.warning("Scraping is not allowed on this website.")
    else:
        with st.spinner("Scraping and analyzing..."):
            scraped_data = scrape_website(url)
            if scraped_data:
                st.json(scraped_data)
