import streamlit as st
import requests
from bs4 import BeautifulSoup
import json
import random
import re
from requests_html import HTMLSession
from urllib.parse import urlparse
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

def extract_meta_tags(soup):
    return {tag.get("name") or tag.get("property"): tag.get("content") for tag in soup.find_all("meta") if tag.get("name") or tag.get("property")}

def extract_links(url, soup):
    internal_links, external_links = [], []
    for link in soup.find_all("a", href=True):
        if link["href"].startswith("http"):
            (internal_links if url in link["href"] else external_links).append(link["href"])
    return internal_links, external_links

def extract_json_ld(soup):
    return [json.loads(script.string) for script in soup.find_all("script", type="application/ld+json") if script.string]

def extract_scripts_and_tracking(soup):
    return [script.get("src") for script in soup.find_all("script", src=True) if "analytics" in script.get("src") or "tracking" in script.get("src")]

def extract_media(soup):
    return [{"src": tag.get("src"), "alt": tag.get("alt", "No alt text")} for tag in soup.find_all(["img", "video"], src=True)]

def extract_comments(soup):
    return [comment for comment in soup.find_all(string=lambda text: isinstance(text, Comment))]

def extract_http_info(url):
    try:
        response = requests.get(url)
        return {"status_code": response.status_code, "headers": dict(response.headers)}
    except requests.RequestException as e:
        return {"error": str(e)}

def extract_tables(soup):
    return [[[cell.get_text() for cell in row.find_all(["th", "td"])] for row in table.find_all("tr")] for table in soup.find_all("table")]

def extract_headings(soup):
    return {f"h{level}": [h.get_text() for h in soup.find_all(f"h{level}")] for level in range(1, 7)}

def extract_social_media_links(external_links):
    social_media_domains = ["facebook", "twitter", "instagram", "linkedin", "youtube"]
    return [link for link in external_links if any(domain in link for domain in social_media_domains)]

def extract_audio_files(soup):
    return [audio.get("src") for audio in soup.find_all("audio", src=True)]

def extract_stylesheets(soup):
    return [link.get("href") for link in soup.find_all("link", rel="stylesheet", href=True)]

def extract_iframes(soup):
    return [iframe.get("src") for iframe in soup.find_all("iframe", src=True)]

def extract_external_js(soup):
    return [script.get("src") for script in soup.find_all("script", src=True)]

def extract_http_response_time(url):
    try:
        response = requests.get(url)
        return response.elapsed.total_seconds()
    except requests.RequestException as e:
        return {"error": str(e)}

def check_broken_images(media):
    broken_images = []
    for media_item in media:
        try:
            if media_item.get("src") and requests.head(media_item["src"], timeout=5).status_code != 200:
                broken_images.append(media_item["src"])
        except:
            broken_images.append(media_item["src"])
    return broken_images

def extract_meta_keywords(soup):
    return [keyword for meta_tag in soup.find_all("meta", {"name": "keywords"}) for keyword in meta_tag.get("content", "").split(",")]

def extract_contact_info(soup):
    emails = set(re.findall(r'mailto:([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', str(soup)))
    phone_numbers = set(re.findall(r'(\+?\(?\d{1,4}\)?[\s\-]?\d{1,3}[\s\-]?\d{3}[\s\-]?\d{4})', str(soup)))
    contact_forms = [form for form in soup.find_all("form") if "contact" in form.get("action", "").lower()]
    return {"emails": list(emails), "phone_numbers": list(phone_numbers), "contact_forms": contact_forms}

def extract_meta_tags_by_prefix(soup, prefix):
    return {tag.get("name") or tag.get("property"): tag.get("content") for tag in soup.find_all("meta") if (tag.get("name") or tag.get("property", "")).startswith(prefix)}

def extract_open_graph_tags(soup):
    return extract_meta_tags_by_prefix(soup, "og:")

def extract_twitter_card_tags(soup):
    return extract_meta_tags_by_prefix(soup, "twitter:")

def extract_canonical_url(soup):
    link = soup.find("link", rel="canonical")
    return link.get("href") if link else None

def extract_favicon_url(soup):
    link = soup.find("link", rel="icon")
    return link.get("href") if link else None

def extract_rss_feeds(soup):
    return [link.get("href") for link in soup.find_all("link", type="application/rss+xml")]

def extract_dublin_core_metadata(soup):
    return extract_meta_tags_by_prefix(soup, "DC.")

def extract_schema_org_data(soup):
    return extract_json_ld(soup)

def extract_opensearch_description(soup):
    link = soup.find("link", type="application/opensearchdescription+xml")
    return link.get("href") if link else None

def extract_alternate_language_links(soup):
    return [{"lang": link.get("hreflang"), "url": link.get("href")} for link in soup.find_all("link", rel="alternate") if link.get("hreflang")]

def extract_hreflang_links(soup):
    return extract_alternate_language_links(soup)

def extract_structured_data(soup):
    return extract_json_ld(soup)

def extract_amp_links(soup):
    return [link.get("href") for link in soup.find_all("link", rel="amphtml")]

def extract_pwa_manifest(soup):
    link = soup.find("link", rel="manifest")
    return link.get("href") if link else None

def extract_viewport_meta(soup):
    tag = soup.find("meta", attrs={"name": "viewport"})
    return tag.get("content") if tag else None

def extract_charset_meta(soup):
    tag = soup.find("meta", attrs={"charset": True})
    return tag.get("charset") if tag else None

def extract_refresh_meta(soup):
    tag = soup.find("meta", attrs={"http-equiv": "refresh"})
    return tag.get("content") if tag else None

def extract_site_verification_meta(soup):
    return extract_meta_tags_by_prefix(soup, "site-verification")

def extract_copyright_meta(soup):
    tag = soup.find("meta", attrs={"name": "copyright"})
    return tag.get("content") if tag else None

def extract_web_mention_links(soup):
    return [link.get("href") for link in soup.find_all("link", rel="webmention")]

def extract_pingback_links(soup):
    return [link.get("href") for link in soup.find_all("link", rel="pingback")]

def extract_alternate_media_links(soup):
    return [{"type": link.get("type"), "href": link.get("href")} for link in soup.find_all("link", rel="alternate") if link.get("type")]

def extract_sitemap_links(soup):
    return [link.get("href") for link in soup.find_all("link", rel="sitemap")]

def extract_meta_by_name(soup, name):
    tag = soup.find("meta", attrs={"name": name})
    return tag.get("content") if tag else None

def extract_author_meta(soup):
    return extract_meta_by_name(soup, "author")

def extract_publisher_meta(soup):
    return extract_meta_by_name(soup, "publisher")

def extract_rating_meta(soup):
    return extract_meta_by_name(soup, "rating")

def extract_distribution_meta(soup):
    return extract_meta_by_name(soup, "distribution")

def extract_robots_meta(soup):
    return extract_meta_by_name(soup, "robots")

def extract_revisit_meta(soup):
    return extract_meta_by_name(soup, "revisit-after")

def extract_keywords_meta(soup):
    return extract_meta_by_name(soup, "keywords")

def extract_description_meta(soup):
    return extract_meta_by_name(soup, "description")

def extract_generator_meta(soup):
    return extract_meta_by_name(soup, "generator")

def extract_handheld_friendly_meta(soup):
    return extract_meta_by_name(soup, "HandheldFriendly")

def extract_mobile_optimized_meta(soup):
    return extract_meta_by_name(soup, "MobileOptimized")

def extract_theme_color_meta(soup):
    return extract_meta_by_name(soup, "theme-color")

def extract_msapplication_tile_color_meta(soup):
    return extract_meta_by_name(soup, "msapplication-TileColor")

def extract_msapplication_tile_image_meta(soup):
    return extract_meta_by_name(soup, "msapplication-TileImage")

def extract_msapplication_config_meta(soup):
    return extract_meta_by_name(soup, "msapplication-config")

def extract_apple_mobile_web_app_capable_meta(soup):
    return extract_meta_by_name(soup, "apple-mobile-web-app-capable")

def extract_apple_mobile_web_app_status_bar_style_meta(soup):
    return extract_meta_by_name(soup, "apple-mobile-web-app-status-bar-style")

def extract_apple_mobile_web_app_title_meta(soup):
    return extract_meta_by_name(soup, "apple-mobile-web-app-title")

def extract_apple_touch_icon_links(soup):
    return [link.get("href") for link in soup.find_all("link", rel="apple-touch-icon")]

def extract_apple_touch_startup_image_links(soup):
    return [link.get("href") for link in soup.find_all("link", rel="apple-touch-startup-image")]

def scrape_website(url):
    session = HTMLSession()
    headers = {"User-Agent": get_random_user_agent()}
    response = session.get(url, headers=headers)
    soup = BeautifulSoup(response.content, "html.parser")
    
    data = {
        "Meta Tags": extract_meta_tags(soup),
        "Main Content": " ".join([p.get_text() for p in soup.find_all("p")])[:1000] + "...",
        "Internal Links": (internal_links := extract_links(url, soup))[0],
        "External Links": internal_links[1],
        "JSON-LD Data": extract_json_ld(soup),
        "Tracking Scripts": extract_scripts_and_tracking(soup),
        "Media": extract_media(soup),
        "Comments": extract_comments(soup),
        "HTTP Info": extract_http_info(url),
        "Tables": extract_tables(soup),
        "Headings": extract_headings(soup),
        "Social Media Links": extract_social_media_links(data["External Links"]),
        "Audio Files": extract_audio_files(soup),
        "Stylesheets": extract_stylesheets(soup),
        "iFrames": extract_iframes(soup),
        "External JavaScript": extract_external_js(soup),
        "HTTP Response Time": extract_http_response_time(url),
        "Broken Images": check_broken_images(data["Media"]),
        "Meta Keywords": extract_meta_keywords(soup),
        "Contact Info": extract_contact_info(soup),
        "Open Graph Tags": extract_open_graph_tags(soup),
        "Twitter Card Tags": extract_twitter_card_tags(soup),
        "Canonical URL": extract_canonical_url(soup),
        "Favicon URL": extract_favicon_url(soup),
        "RSS Feeds": extract_rss_feeds(soup),
        "Dublin Core Metadata": extract_dublin_core_metadata(soup),
        "Schema.org Data": extract_schema_org_data(soup),
        "OpenSearch Description": extract_opensearch_description(soup),
        "Alternate Language Links": extract_alternate_language_links(soup),
        "Hreflang Links": extract_hreflang_links(soup),
        "Structured Data": extract_structured_data(soup),
        "AMP Links": extract_amp_links(soup),
        "PWA Manifest": extract_pwa_manifest(soup),
        "Viewport Meta": extract_viewport_meta(soup),
        "Charset Meta": extract_charset_meta(soup),
        "Refresh Meta": extract_refresh_meta(soup),
        "Site Verification Meta": extract_site_verification_meta(soup),
        "Copyright Meta": extract_copyright_meta(soup),
        "Web Mention Links": extract_web_mention_links(soup),
        "Pingback Links": extract_pingback_links(soup),
        "Alternate Media Links": extract_alternate_media_links(soup),
        "Sitemap Links": extract_sitemap_links(soup),
        "Author Meta": extract_author_meta(soup),
        "Publisher Meta": extract_publisher_meta(soup),
        "Rating Meta": extract_rating_meta(soup),
        "Distribution Meta": extract_distribution_meta(soup),
        "Robots Meta": extract_robots_meta(soup),
        "Revisit Meta": extract_revisit_meta(soup),
        "Keywords Meta": extract_keywords_meta(soup),
        "Description Meta": extract_description_meta(soup),
        "Generator Meta": extract_generator_meta(soup),
        "Handheld Friendly Meta": extract_handheld_friendly_meta(soup),
        "Mobile Optimized Meta": extract_mobile_optimized_meta(soup),
        "Theme Color Meta": extract_theme_color_meta(soup),
        "MSApplication Tile Color Meta": extract_msapplication_tile_color_meta(soup),
        "MSApplication Tile Image Meta": extract_msapplication_tile_image_meta(soup),
        "MSApplication Config Meta": extract_msapplication_config_meta(soup),
        "Apple Mobile Web App Capable Meta": extract_apple_mobile_web_app_capable_meta(soup),
        "Apple Mobile Web App Status Bar Style Meta": extract_apple_mobile_web_app_status_bar_style_meta(soup),
        "Apple Mobile Web App Title Meta": extract_apple_mobile_web_app_title_meta(soup),
        "Apple Touch Icon Links": extract_apple_touch_icon_links(soup),
        "Apple Touch Startup Image Links": extract_apple_touch_startup_image_links(soup),
    }

    return data

st.title("Comprehensive Web Scraping Tool")
url = st.text_input("Enter a URL for analysis")

if st.button("Analyze"):
    if not is_valid_url(url):
        st.error("Please enter a valid URL.")
    else:
        with st.spinner("Scraping and analyzing..."):
            scraped_data = scrape_website(url)
            if scraped_data:
                st.json(scraped_data)
