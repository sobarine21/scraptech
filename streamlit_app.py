import streamlit as st
import requests
from bs4 import BeautifulSoup
import json
import random
import re
from requests_html import HTMLSession
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser
from langdetect import detect, LangDetectException
import validators
import pandas as pd
from langdetect import DetectorFactory

DetectorFactory.seed = 0

def get_random_user_agent():
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.82 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Safari/605.1.15',
        'Mozilla/5.0 (Linux; Android 10; SM-G960F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.90 Mobile Safari/537.36',
        'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1'
    ]
    return random.choice(user_agents)

def is_valid_url(url):
    return validators.url(url)

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

def detect_language(text):
    if not text or len(text.split()) < 3:
        return "Insufficient text for detection"
    try:
        return detect(text)
    except LangDetectException:
        return "Detection failed"

def extract_meta_tags(soup):
    meta_info = {}
    for tag in soup.find_all("meta"):
        if tag.get("name"):
            meta_info[tag.get("name")] = tag.get("content")
        elif tag.get("property"):
            meta_info[tag.get("property")] = tag.get("content")
    return meta_info

def extract_links(url, soup):
    internal_links, external_links = [], []
    for link in soup.find_all("a", href=True):
        if link["href"].startswith("http"):
            if url in link["href"]:
                internal_links.append(link["href"])
            else:
                external_links.append(link["href"])
    return internal_links, external_links

def extract_json_ld(soup):
    json_ld_data = []
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            json_ld_data.append(json.loads(script.string))
        except json.JSONDecodeError:
            continue
    return json_ld_data

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

def extract_scripts_and_tracking(soup):
    tracking_scripts = []
    for script in soup.find_all("script"):
        src = script.get("src")
        if src:
            if "analytics" in src or "tracking" in src:
                tracking_scripts.append(src)
    return tracking_scripts

def extract_media(soup):
    media_data = []
    images = [{"src": img.get("src"), "alt": img.get("alt", "No alt text")} for img in soup.find_all("img", src=True)]
    media_data.extend(images)
    videos = [{"src": video.get("src")} for video in soup.find_all("video", src=True)]
    media_data.extend(videos)
    return media_data

def extract_comments(soup):
    comments = []
    for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
        comments.append(comment)
    return comments

def extract_http_info(url):
    try:
        response = requests.get(url)
        return {
            "status_code": response.status_code,
            "headers": dict(response.headers)
        }
    except requests.RequestException as e:
        return {"error": str(e)}

def extract_tables(soup):
    tables = []
    for table in soup.find_all("table"):
        table_data = [[cell.get_text() for cell in row.find_all(["th", "td"])] for row in table.find_all("tr")]
        tables.append(table_data)
    return tables

def extract_headings(soup):
    headings = {}
    for level in range(1, 7):
        headings[f"h{level}"] = [h.get_text() for h in soup.find_all(f"h{level}")]
    return headings

def extract_social_media_links(external_links):
    social_links = []
    social_media_domains = ["facebook", "twitter", "instagram", "linkedin", "youtube"]
    for link in external_links:
        if any(domain in link for domain in social_media_domains):
            social_links.append(link)
    return social_links

def extract_audio_files(soup):
    audio_files = []
    for audio in soup.find_all("audio"):
        src = audio.get("src")
        if src:
            audio_files.append(src)
    return audio_files

def extract_stylesheets(soup):
    stylesheets = []
    for link in soup.find_all("link", rel="stylesheet"):
        href = link.get("href")
        if href:
            stylesheets.append(href)
    return stylesheets

def extract_iframes(soup):
    iframes = []
    for iframe in soup.find_all("iframe"):
        src = iframe.get("src")
        if src:
            iframes.append(src)
    return iframes

def extract_external_js(soup):
    external_js = []
    for script in soup.find_all("script", src=True):
        external_js.append(script.get("src"))
    return external_js

def extract_http_response_time(url):
    try:
        response = requests.get(url)
        return response.elapsed.total_seconds()
    except requests.RequestException as e:
        return {"error": str(e)}

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

def extract_meta_keywords(soup):
    meta_keywords = []
    meta_tags = soup.find_all("meta", {"name": "keywords"})
    for meta_tag in meta_tags:
        if meta_tag.get("content"):
            meta_keywords.extend(meta_tag["content"].split(","))
    return meta_keywords

def extract_contact_info(soup):
    contact_info = {
        "emails": [],
        "phone_numbers": [],
        "contact_forms": []
    }
    emails = set(re.findall(r'mailto:([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', str(soup)))
    contact_info["emails"] = list(emails)
    phone_numbers = set(re.findall(r'(\+?\(?\d{1,4}\)?[\s\-]?\d{1,3}[\s\-]?\d{3}[\s\-]?\d{4})', str(soup)))
    contact_info["phone_numbers"] = list(phone_numbers)
    for form in soup.find_all("form"):
        action = form.get("action", "").lower()
        if "contact" in action:
            contact_info["contact_forms"].append(form)
    return contact_info

def extract_open_graph_tags(soup):
    og_tags = {}
    for tag in soup.find_all("meta"):
        if tag.get("property", "").startswith("og:"):
            og_tags[tag.get("property")] = tag.get("content")
    return og_tags

def extract_twitter_card_tags(soup):
    twitter_tags = {}
    for tag in soup.find_all("meta"):
        if tag.get("name", "").startswith("twitter:"):
            twitter_tags[tag.get("name")] = tag.get("content")
    return twitter_tags

def extract_canonical_url(soup):
    link = soup.find("link", rel="canonical")
    if link:
        return link.get("href")
    return None

def extract_favicon_url(soup):
    link = soup.find("link", rel="icon")
    if link:
        return link.get("href")
    return None

def extract_rss_feeds(soup):
    feeds = []
    for link in soup.find_all("link", type="application/rss+xml"):
        feeds.append(link.get("href"))
    return feeds

def extract_dublin_core_metadata(soup):
    dc_metadata = {}
    for tag in soup.find_all("meta"):
        if tag.get("name", "").startswith("DC."):
            dc_metadata[tag.get("name")] = tag.get("content")
    return dc_metadata

def extract_schema_org_data(soup):
    schema_data = []
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            schema_data.append(json.loads(script.string))
        except json.JSONDecodeError:
            continue
    return schema_data

def extract_opensearch_description(soup):
    link = soup.find("link", type="application/opensearchdescription+xml")
    if link:
        return link.get("href")
    return None

def extract_alternate_language_links(soup):
    alt_links = []
    for link in soup.find_all("link", rel="alternate"):
        if link.get("hreflang"):
            alt_links.append({"lang": link.get("hreflang"), "url": link.get("href")})
    return alt_links

def extract_hreflang_links(soup):
    hreflang_links = []
    for link in soup.find_all("link", rel="alternate", hreflang=True):
        hreflang_links.append({"hreflang": link.get("hreflang"), "url": link.get("href")})
    return hreflang_links

def extract_structured_data(soup):
    structured_data = []
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            structured_data.append(json.loads(script.string))
        except json.JSONDecodeError:
            continue
    return structured_data

def extract_amp_links(soup):
    amp_links = []
    for link in soup.find_all("link", rel="amphtml"):
        amp_links.append(link.get("href"))
    return amp_links

def extract_pwa_manifest(soup):
    link = soup.find("link", rel="manifest")
    if link:
        return link.get("href")
    return None

def extract_viewport_meta(soup):
    tag = soup.find("meta", attrs={"name": "viewport"})
    if tag:
        return tag.get("content")
    return None

def extract_charset_meta(soup):
    tag = soup.find("meta", attrs={"charset": True})
    if tag:
        return tag.get("charset")
    return None

def extract_refresh_meta(soup):
    tag = soup.find("meta", attrs={"http-equiv": "refresh"})
    if tag:
        return tag.get("content")
    return None

def extract_site_verification_meta(soup):
    verification_tags = {}
    for tag in soup.find_all("meta"):
        if tag.get("name", "").endswith("site-verification"):
            verification_tags[tag.get("name")] = tag.get("content")
    return verification_tags

def extract_copyright_meta(soup):
    tag = soup.find("meta", attrs={"name": "copyright"})
    if tag:
        return tag.get("content")
    return None

def extract_web_mention_links(soup):
    web_mention_links = []
    for link in soup.find_all("link", rel="webmention"):
        href = link.get("href")
        if href:
            web_mention_links.append(href)
    return web_mention_links

def extract_pingback_links(soup):
    pingback_links = []
    for link in soup.find_all("link", rel="pingback"):
        href = link.get("href")
        if href:
            pingback_links.append(href)
    return pingback_links

def extract_alternate_media_links(soup):
    alternate_media_links = []
    for link in soup.find_all("link", rel="alternate"):
        if link.get("type") and link.get("href"):
            alternate_media_links.append({"type": link.get("type"), "href": link.get("href")})
    return alternate_media_links

def extract_sitemap_links(soup):
    sitemap_links = []
    for link in soup.find_all("link", rel="sitemap"):
        href = link.get("href")
        if href:
            sitemap_links.append(href)
    return sitemap_links

def extract_author_meta(soup):
    tag = soup.find("meta", attrs={"name": "author"})
    if tag:
        return tag.get("content")
    return None

def extract_publisher_meta(soup):
    tag = soup.find("meta", attrs={"name": "publisher"})
    if tag:
        return tag.get("content")
    return None

def extract_rating_meta(soup):
    tag = soup.find("meta", attrs={"name": "rating"})
    if tag:
        return tag.get("content")
    return None

def extract_distribution_meta(soup):
    tag = soup.find("meta", attrs={"name": "distribution"})
    if tag:
        return tag.get("content")
    return None

def extract_robots_meta(soup):
    tag = soup.find("meta", attrs={"name": "robots"})
    if tag:
        return tag.get("content")
    return None

def extract_revisit_meta(soup):
    tag = soup.find("meta", attrs={"name": "revisit-after"})
    if tag:
        return tag.get("content")
    return None

def extract_keywords_meta(soup):
    tag = soup.find("meta", attrs={"name": "keywords"})
    if tag:
        return tag.get("content")
    return None

def extract_description_meta(soup):
    tag = soup.find("meta", attrs={"name": "description"})
    if tag:
        return tag.get("content")
    return None

def extract_generator_meta(soup):
    tag = soup.find("meta", attrs={"name": "generator"})
    if tag:
        return tag.get("content")
    return None

def extract_handheld_friendly_meta(soup):
    tag = soup.find("meta", attrs={"name": "HandheldFriendly"})
    if tag:
        return tag.get("content")
    return None

def extract_mobile_optimized_meta(soup):
    tag = soup.find("meta", attrs={"name": "MobileOptimized"})
    if tag:
        return tag.get("content")
    return None

def extract_theme_color_meta(soup):
    tag = soup.find("meta", attrs={"name": "theme-color"})
    if tag:
        return tag.get("content")
    return None

def extract_msapplication_tile_color_meta(soup):
    tag = soup.find("meta", attrs={"name": "msapplication-TileColor"})
    if tag:
        return tag.get("content")
    return None

def extract_msapplication_tile_image_meta(soup):
    tag = soup.find("meta", attrs={"name": "msapplication-TileImage"})
    if tag:
        return tag.get("content")
    return None

def extract_msapplication_config_meta(soup):
    tag = soup.find("meta", attrs={"name": "msapplication-config"})
    if tag:
        return tag.get("content")
    return None

def extract_apple_mobile_web_app_capable_meta(soup):
    tag = soup.find("meta", attrs={"name": "apple-mobile-web-app-capable"})
    if tag:
        return tag.get("content")
    return None

def extract_apple_mobile_web_app_status_bar_style_meta(soup):
    tag = soup.find("meta", attrs={"name": "apple-mobile-web-app-status-bar-style"})
    if tag:
        return tag.get("content")
    return None

def extract_apple_mobile_web_app_title_meta(soup):
    tag = soup.find("meta", attrs={"name": "apple-mobile-web-app-title"})
    if tag:
        return tag.get("content")
    return None

def extract_apple_touch_icon_links(soup):
    apple_touch_icon_links = []
    for link in soup.find_all("link", rel="apple-touch-icon"):
        href = link.get("href")
        if href:
            apple_touch_icon_links.append(href)
    return apple_touch_icon_links

def extract_apple_touch_startup_image_links(soup):
    apple_touch_startup_image_links = []
    for link in soup.find_all("link", rel="apple-touch-startup-image"):
        href = link.get("href")
        if href:
            apple_touch_startup_image_links.append(href)
    return apple_touch_startup_image_links

def scrape_website(url):
    session = HTMLSession()
    headers = {"User-Agent": get_random_user_agent()}
    response = session.get(url, headers=headers)
    soup = BeautifulSoup(response.content, "html.parser")
    
    data = {}

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
    data["External JavaScript"]
