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
        return {"error": f"Failed to fetch HTTP info: {e}"}

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
        return {"error": f"Failed to get response time: {e}"}

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

# New Function to Extract Contact Information
def extract_contact_info(soup):
    contact_info = {
        "emails": [],
        "phone_numbers": [],
        "contact_forms": []
    }

    # 1. Extract email addresses using regex (mailto: links)
    emails = set(re.findall(r'mailto:([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', str(soup)))
    contact_info["emails"] = list(emails)

    # 2. Extract phone numbers using regex (formats like (555) 555-5555, +1-555-555-5555)
    phone_numbers = set(re.findall(r'(\+?\(?\d{1,4}\)?[\s\-]?\d{1,3}[\s\-]?\d{3}[\s\-]?\d{4})', str(soup)))
    contact_info["phone_numbers"] = list(phone_numbers)

    # 3. Extract forms (if the form contains "contact" in the action or method)
    for form in soup.find_all("form"):
        action = form.get("action", "").lower()
        if "contact" in action:
            contact_info["contact_forms"].append(form)

    return contact_info

# Main Scraping Function
def scrape_website(url):
    session = HTMLSession()
    headers = {"User-Agent": get_random_user_agent()}

    # Check if the URL is valid and scraping is allowed
    if not is_valid_url(url):
        return {"error": "Invalid URL"}

    if not is_scraping_allowed(url):
        return {"error": "Scraping not allowed by robots.txt"}

    try:
        response = session.get(url, headers=headers)
        if response.status_code != 200:
            return {"error": f"Failed to fetch the page. Status code: {response.status_code}"}

        soup = BeautifulSoup(response.text, "html.parser")

        # Data extraction
        data = {
            "meta_tags": extract_meta_tags(soup),
            "links": extract_links(url, soup),
            "json_ld": extract_json_ld(soup),
            "forms": extract_forms(soup),
            "tracking_scripts": extract_scripts_and_tracking(soup),
            "media": extract_media(soup),
            "comments": extract_comments(soup),
            "http_info": extract_http_info(url),
            "tables": extract_tables(soup),
            "headings": extract_headings(soup),
            "social_links": extract_social_media_links(data["links"][1]),
            "audio_files": extract_audio_files(soup),
            "stylesheets": extract_stylesheets(soup),
            "iframes": extract_iframes(soup),
            "external_js": extract_external_js(soup),
            "response_time": extract_http_response_time(url),
            "broken_images": check_broken_images(data["media"]),
            "meta_keywords": extract_meta_keywords(soup),
            "contact_info": extract_contact_info(soup)
        }

        return data

    except Exception as e:
        return {"error": str(e)}

# Streamlit User Interface
def main():
    st.title("Website Scraping Tool")
    st.write("Enter the URL of the website you want to scrape:")

    url = st.text_input("Website URL")
    
    if url:
        data = scrape_website(url)

        if "error" in data:
            st.error(data["error"])
        else:
            st.subheader("Meta Tags")
            st.json(data["meta_tags"])

            st.subheader("Links (Internal and External)")
            st.write("Internal Links:")
            st.write(data["links"][0])
            st.write("External Links:")
            st.write(data["links"][1])

            st.subheader("JSON-LD Data")
            st.json(data["json_ld"])

            st.subheader("Forms on the Website")
            st.write(data["forms"])

            st.subheader("Tracking Scripts")
            st.write(data["tracking_scripts"])

            st.subheader("Media Files (Images, Videos, etc.)")
            st.write(data["media"])

            st.subheader("Comments in the HTML")
            st.write(data["comments"])

            st.subheader("HTTP Response Information")
            st.write(data["http_info"])

            st.subheader("Tables")
            st.write(data["tables"])

            st.subheader("Headings")
            st.write(data["headings"])

            st.subheader("Social Media Links")
            st.write(data["social_links"])

            st.subheader("Audio Files")
            st.write(data["audio_files"])

            st.subheader("Stylesheets")
            st.write(data["stylesheets"])

            st.subheader("iFrames")
            st.write(data["iframes"])

            st.subheader("External JavaScript Files")
            st.write(data["external_js"])

            st.subheader("HTTP Response Time")
            st.write(data["response_time"])

            st.subheader("Broken Images")
            st.write(data["broken_images"])

            st.subheader("Meta Keywords")
            st.write(data["meta_keywords"])

            st.subheader("Contact Information")
            st.write(data["contact_info"])

# Run the Streamlit app
if __name__ == "__main__":
    main()
