import streamlit as st
import requests
from bs4 import BeautifulSoup
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from textblob import TextBlob
import re
import random
import time
import pandas as pd
import langdetect
import textstat
import validators
import json
import hashlib
import os

# Additional Imports for enhanced functionalities
from urllib.parse import urlparse
from requests_html import HTMLSession
from urllib.robotparser import RobotFileParser

# Function to get a random user agent
def get_random_user_agent():
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.82 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Safari/605.1.15',
        'Mozilla/5.0 (Linux; Android 10; SM-G960F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.90 Mobile Safari/537.36',
        'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1'
    ]
    return random.choice(user_agents)

# Function to check if a URL is valid
def is_valid_url(url):
    return validators.url(url)

# Extract all links from the page
def extract_links(soup):
    links = []
    for link in soup.find_all('a', href=True):
        href = link['href']
        if is_valid_url(href):
            links.append(href)
    return links

# Function to check if a website is allowed to be scraped based on robots.txt
def is_scraping_allowed(url):
    parsed_url = urlparse(url)
    robots_url = f"{parsed_url.scheme}://{parsed_url.netloc}/robots.txt"
    rp = RobotFileParser()
    rp.set_url(robots_url)
    rp.read()
    return rp.can_fetch("*", url)

# Function to extract meta data like OpenGraph, Twitter Card
def extract_meta_data(soup):
    meta_data = {}
    for meta_tag in soup.find_all('meta'):
        if meta_tag.get('property') == 'og:title':
            meta_data['og_title'] = meta_tag.get('content')
        if meta_tag.get('property') == 'og:image':
            meta_data['og_image'] = meta_tag.get('content')
        if meta_tag.get('name') == 'twitter:title':
            meta_data['twitter_title'] = meta_tag.get('content')
        if meta_tag.get('name') == 'twitter:image':
            meta_data['twitter_image'] = meta_tag.get('content')
    return meta_data

# Function to extract internal links and external links
def classify_links(url, links):
    internal_links = []
    external_links = []
    for link in links:
        if url in link:
            internal_links.append(link)
        else:
            external_links.append(link)
    return internal_links, external_links

# Function to perform sentiment analysis
def get_sentiment(text):
    blob = TextBlob(text)
    return blob.sentiment.polarity

# Function to perform language detection
def detect_language(text):
    return langdetect.detect(text)

# Function to perform keyword density analysis
def get_keyword_density(text):
    words = text.split()
    keyword_density = {word: words.count(word) / len(words) * 100 for word in set(words)}
    return keyword_density

# Function to perform readability analysis
def get_readability_score(text):
    return textstat.flesch_kincaid_grade(text)

# Function to check for broken links
def check_broken_links(links):
    broken_links = []
    for link in links:
        try:
            response = requests.head(link, timeout=5, allow_redirects=True)
            if response.status_code != 200:
                broken_links.append(link)
        except Exception as e:
            broken_links.append(link)
    return broken_links

# Function to fetch structured data (JSON-LD)
def extract_json_ld(soup):
    json_ld = []
    for script in soup.find_all('script', type='application/ld+json'):
        try:
            json_ld.append(json.loads(script.string))
        except json.JSONDecodeError:
            continue
    return json_ld

# Function to handle advanced image data extraction
def extract_image_data(soup):
    image_data = []
    for img in soup.find_all('img', src=True):
        image_data.append({'src': img['src'], 'alt': img.get('alt', 'No alt text')})
    return image_data

# Main scraping function
def scrape_website(url):
    try:
        headers = {
            'User-Agent': get_random_user_agent()
        }
        
        # Check if scraping is allowed for the website
        if not is_scraping_allowed(url):
            st.warning("Scraping is not allowed on this site according to its robots.txt.")
            return
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        # Parse the HTML content
        soup = BeautifulSoup(response.content, 'html.parser')

        # Extract data
        page_title = soup.title.string if soup.title else 'No title found'
        meta_data = extract_meta_data(soup)
        content = ' '.join([p.get_text() for p in soup.find_all('p')])

        # Perform keyword density analysis
        keyword_density = get_keyword_density(content)

        # Perform sentiment analysis
        sentiment = get_sentiment(content)

        # Detect language of the content
        language = detect_language(content)

        # Perform readability analysis
        readability_score = get_readability_score(content)

        # Extract links
        links = extract_links(soup)
        internal_links, external_links = classify_links(url, links)

        # Extract images
        image_data = extract_image_data(soup)

        # Extract JSON-LD structured data
        json_ld_data = extract_json_ld(soup)

        # Check for broken links
        broken_links = check_broken_links(links)

        # Collect all data in a dictionary
        data = {
            'Page Title': page_title,
            'Meta Data': meta_data,
            'Keyword Density': keyword_density,
            'Sentiment': sentiment,
            'Language': language,
            'Readability Score': readability_score,
            'Internal Links': internal_links,
            'External Links': external_links,
            'Image Data': image_data,
            'JSON-LD Data': json_ld_data,
            'Broken Links': broken_links
        }

        return data

    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching URL: {e}")
        return None

# Streamlit UI
st.title("Advanced Web Scraping and Data Analysis")
url = st.text_input("Enter Website URL", "https://example.com")

if st.button("Start Scraping"):
    if not is_valid_url(url):
        st.error("Please enter a valid URL")
    else:
        data = scrape_website(url)
        if data:
            st.subheader("Page Data")
            for key, value in data.items():
                st.write(f"**{key}:** {value}")
            
            # Optionally, show the content word cloud if available
            if 'Keyword Density' in data:
                wordcloud = WordCloud(width=800, height=400).generate_from_frequencies(data['Keyword Density'])
                st.image(wordcloud.to_array(), caption="Keyword Cloud", use_column_width=True)

            # Optionally, show JSON-LD data
            if 'JSON-LD Data' in data:
                st.json(data['JSON-LD Data'])

            # Allow CSV export
            df = pd.DataFrame([data])
            csv_file = f"{url.split('//')[-1].replace('/', '_')}.csv"
            df.to_csv(csv_file, index=False)
            st.download_button(label="Download Data as CSV", data=csv_file, mime="text/csv")
