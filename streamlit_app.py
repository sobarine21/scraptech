import streamlit as st
import requests
from bs4 import BeautifulSoup, Comment
import json
import random
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
    content = " ".join([p.get_text() for p in soup.find_all("p")])
    data["Main Content"] = content[:1000] + "..."  # Displaying a snippet

    # 4. Language Detection
    data["Detected Language"] = detect_language(content)

    # 5. Internal and External Links
    internal_links, external_links = extract_links(url, soup)
    data["Internal Links"] = internal_links
    data["External Links"] = external_links

    # 6. JSON-LD Structured Data
    data["JSON-LD Data"] = extract_json_ld(soup)

    # 7. Forms
    data["Forms"] = extract_forms(soup)

    # 8. Tracking Scripts
    data["Tracking Scripts"] = extract_scripts_and_tracking(soup)

    # 9. Media (Images, Videos)
    data["Media"] = extract_media(soup)

    # 10. Comments
    data["Comments"] = extract_comments(soup)

    # 11. HTTP Headers and Status Code
    data["HTTP Info"] = extract_http_info(url)

    # 12. Tables
    data["Tables"] = extract_tables(soup)

    # 13. Headings
    data["Headings"] = extract_headings(soup)

    # 14. Social Media Links
    data["Social Media Links"] = extract_social_media_links(external_links)

    # 15. Audio Files
    data["Audio Files"] = extract_audio_files(soup)

    # 16. Stylesheets
    data["Stylesheets"] = extract_stylesheets(soup)

    # 17. iFrames
    data["iFrames"] = extract_iframes(soup)

    # 18. External JavaScript
    data["External JavaScript"] = extract_external_js(soup)

    # 19. HTTP Response Time
    data["HTTP Response Time"] = extract_http_response_time(url)

    # 20. Broken Images
    data["Broken Images"] = check_broken_images(data.get("Media", []))

    # 21. Meta Keywords
    data["Meta Keywords"] = extract_meta_keywords(soup)

    return data

# Streamlit app
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
