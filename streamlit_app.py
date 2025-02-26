import streamlit as st
import requests
from bs4 import BeautifulSoup, Comment
import json
import random
import re
from requests_html import HTMLSession
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser
from langdetect import detect, LangDetectException
import validators
import pandas as pd

# Seed the language detector for consistent results
from langdetect import DetectorFactory
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
    try:
        rp.read()
        return rp.can_fetch("*", url)
    except:
        return False

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

# Extract forms
def extract_forms(soup):
    forms = []
    for form in soup.find_all("form"):
        form_data = {
            "action": form.get("action"),
            "method": form.get("method"),
            "inputs": []
        }
        for input_tag in form.find_all("input"):
            input_data = {
                "type": input_tag.get("type"),
                "name": input_tag.get("name"),
                "value": input_tag.get("value")
            }
            form_data["inputs"].append(input_data)
        forms.append(form_data)
    return forms

# Extract scripts and tracking tags
def extract_scripts_and_tracking(soup):
    tracking_scripts = []
    for script in soup.find_all("script"):
        src = script.get("src")
        if src:
            if "analytics" in src or "tracking" in src:
                tracking_scripts.append(src)
    return tracking_scripts

# Extract images and media content
def extract_media(soup):
    media_data = []
    # Images
    images = [{"src": img.get("src"), "alt": img.get("alt", "No alt text")} for img in soup.find_all("img", src=True)]
    media_data.extend(images)
    # Videos
    videos = [{"src": video.get("src")} for video in soup.find_all("video", src=True)]
    media_data.extend(videos)
    return media_data

# Extract comments from HTML
def extract_comments(soup):
    comments = []
    for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
        comments.append(comment)
    return comments

# Extract HTTP Headers and Status Code
def extract_http_info(url):
    try:
        response = requests.get(url)
        return {
            "status_code": response.status_code,
            "headers": dict(response.headers)
        }
    except requests.RequestException as e:
        return {"error": str(e)}

# Extract tables
def extract_tables(soup):
    tables = []
    for table in soup.find_all("table"):
        table_data = [[cell.get_text() for cell in row.find_all(["th", "td"])] for row in table.find_all("tr")]
        tables.append(table_data)
    return tables

# Extract headings
def extract_headings(soup):
    headings = {}
    for level in range(1, 7):
        headings[f"h{level}"] = [h.get_text() for h in soup.find_all(f"h{level}")]
    return headings

# Extract links to social media
def extract_social_media_links(external_links):
    social_links = []
    social_media_domains = ["facebook", "twitter", "instagram", "linkedin", "youtube"]
    for link in external_links:
        if any(domain in link for domain in social_media_domains):
            social_links.append(link)
    return social_links

# Extract audio files
def extract_audio_files(soup):
    audio_files = []
    for audio in soup.find_all("audio"):
        src = audio.get("src")
        if src:
            audio_files.append(src)
    return audio_files

# Extract stylesheets
def extract_stylesheets(soup):
    stylesheets = []
    for link in soup.find_all("link", rel="stylesheet"):
        href = link.get("href")
        if href:
            stylesheets.append(href)
    return stylesheets

# Extract iFrames
def extract_iframes(soup):
    iframes = []
    for iframe in soup.find_all("iframe"):
        src = iframe.get("src")
        if src:
            iframes.append(src)
    return iframes

# Extract external JavaScript files
def extract_external_js(soup):
    external_js = []
    for script in soup.find_all("script", src=True):
        external_js.append(script.get("src"))
    return external_js

# Extract HTTP response time
def extract_http_response_time(url):
    try:
        response = requests.get(url)
        return response.elapsed.total_seconds()
    except requests.RequestException as e:
        return {"error": str(e)}

# Check for broken images
def check_broken_images(media):
    broken_images = []
    for media_item in media:
        if media_item.get("src"):
            try:
                response = requests.head(media_item["src"], timeout=5)
                if response.status_code != 200:
                    broken_images.append(media_item["src"])
            except:
                broken_images.append(media_item["src"])
    return broken_images

# Extract meta keywords
def extract_meta_keywords(soup):
    meta_keywords = []
    meta_tags = soup.find_all("meta", {"name": "keywords"})
    for meta_tag in meta_tags:
        if meta_tag.get("content"):
            meta_keywords.extend(meta_tag["content"].split(","))
    return meta_keywords

# Extract contact information
def extract_contact_info(soup):
    contact_info = {
        "emails": [],
        "phone_numbers": [],
        "contact_forms": []
    }

    # Extract email addresses using regex (mailto: links)
    emails = set(re.findall(r'mailto:([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', str(soup)))
    contact_info["emails"] = list(emails)

    # Extract phone numbers using regex (formats like (555) 555-5555, +1-555-555-5555)
    phone_numbers = set(re.findall(r'(\+?\(?\d{1,4}\)?[\s\-]?\d{1,3}[\s\-]?\d{3}[\s\-]?\d{4})', str(soup)))
    contact_info["phone_numbers"] = list(phone_numbers)

    # Extract forms (if the form contains "contact" in the action or method)
    for form in soup.find_all("form"):
        action = form.get("action", "").lower()
        if "contact" in action:
            contact_info["contact_forms"].append(form)

    return contact_info

# Main Scraping Function
def scrape_website(url):
    session = HTMLSession()
    headers = {"User-Agent": get_random_user_agent()}
    response = session.get(url, headers=headers)
    soup = BeautifulSoup(response.content, "html.parser")
    
    data = {}

    # Extracting data
    data["Meta Tags"] = extract_meta_tags(soup)
    content = " ".join([p.get_text() for p in soup.find_all("p")])
    data["Main Content"] = content[:1000] + "..."
    data["Detected Language"] = detect_language(content)
    internal_links, external_links = extract_links(url, soup)
    data["Internal Links"] = internal_links
    data["External Links"] = external_links
    data["JSON-LD Data"] = extract_json_ld(soup)
    data["Forms"] = extract_forms(soup)
    data["Tracking Scripts"] = extract_scripts_and_tracking(soup)
    data["Media"] = extract_media(soup)
    data["Comments"] = extract_comments(soup)
    data["HTTP Info"] = extract_http_info(url)
    data["Tables"] = extract_tables(soup)
    data["Headings"] = extract_headings(soup)
    data["Social Media Links"] = extract_social_media_links(external_links)
    data["Audio Files"] = extract_audio_files(soup)
    data["Stylesheets"] = extract_stylesheets(soup)
    data["iFrames"] = extract_iframes(soup)
    data["External JavaScript"] = extract_external_js(soup)
    data["HTTP Response Time"] = extract_http_response_time(url)
    data["Broken Images"] = check_broken_images(data.get("Media", []))
    data["Meta Keywords"] = extract_meta_keywords(soup)
    data["Contact Info"] = extract_contact_info(soup)  # Added contact info extraction

    return data

# Streamlit UI
st.set_page_config(page_title="Comprehensive Web Scraping Tool", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
        .main {
            background-color: #1e1e1e;
            color: #ffffff;
            padding: 2rem;
            border-radius: 10px;
        }
        .stButton>button {
            background-color: #0078d4;
            color: white;
            border-radius: 5px;
            padding: 0.5rem 1rem;
            font-size: 1rem;
        }
        .stTextInput>div>div>input {
            background-color: #333333;
            color: #ffffff;
            border: 1px solid #555555;
            padding: 0.5rem;
            border-radius: 5px;
        }
        .stAlert {
            border-radius: 5px;
        }
        .css-1aumxhk {
            padding-top: 2rem;
        }
        .reportview-container .main footer {
            visibility: hidden;
        }
    </style>
""", unsafe_allow_html=True)

st.title("Comprehensive Web Scraping Tool")
st.subheader("Analyze and extract detailed information from any web page")

st.sidebar.header("User Guide")
st.sidebar.info("""
    1. Enter a valid URL that you want to analyze.
    2. Click on the "Analyze" button to start scraping.
    3. View the extracted information in a structured format.
    4. Ensure you have permission to scrape the website.
""")

url = st.text_input("Enter a URL for analysis", placeholder="https://example.com")

if st.button("Analyze"):
    if not is_valid_url(url):
        st.error("Please enter a valid URL.")
    elif not is_scraping_allowed(url):
        st.warning("Scraping is not allowed on this website.")
    else:
        with st.spinner("Scraping and analyzing..."):
            scraped_data = scrape_website(url)
            if scraped_data:
                st.success("Scraping completed successfully!")
                st.json(scraped_data)
