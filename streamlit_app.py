import streamlit as st
import requests
from bs4 import BeautifulSoup
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import pandas as pd
from textblob import TextBlob
from requests_html import HTMLSession
from urllib.parse import urlparse
import random
import validators

# Generate random user agents to help bypass basic bot detection
def get_random_user_agent():
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.82 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Safari/605.1.15',
        'Mozilla/5.0 (Linux; Android 10; SM-G960F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.90 Mobile Safari/537.36',
        'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1'
    ]
    return random.choice(user_agents)

# Extract GIFs, memes, and short-form media URLs
def extract_multimedia_links(soup):
    media_links = []
    for img in soup.find_all("img", src=True):
        if "gif" in img["src"] or "meme" in img["src"]:
            media_links.append(img["src"])
    return media_links

# Identify dynamic elements (AJAX and JS-rendered)
def check_dynamic_content(session, url):
    try:
        response = session.get(url)
        if "ajax" in response.text or "XMLHttpRequest" in response.text:
            return "Dynamic content detected (AJAX/JavaScript driven)"
        else:
            return "Static content"
    except:
        return "Unable to determine"

# Detect trending topics based on frequency and sentiment
def detect_trending_topics(text):
    words = text.split()
    trending_words = pd.Series(words).value_counts().head(10)
    return trending_words[trending_words > 3].to_dict()

# Generate word cloud based on identified trends
def generate_trend_wordcloud(trending_topics):
    wordcloud = WordCloud(width=800, height=400).generate_from_frequencies(trending_topics)
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.imshow(wordcloud, interpolation="bilinear")
    ax.axis("off")
    return fig

# Extract voice or podcast content if available
def detect_audio_content(soup):
    audio_links = []
    for audio in soup.find_all("audio"):
        if audio.get("src"):
            audio_links.append(audio.get("src"))
    return audio_links

# Detect and extract CSS animations
def extract_css_animations(soup):
    css_links = []
    for link in soup.find_all("link", rel="stylesheet"):
        css_links.append(link["href"])
    return css_links

# Detect interactive elements such as forms and pop-ups
def detect_interactive_elements(soup):
    forms_count = len(soup.find_all("form"))
    popups = "Yes" if any("popup" in str(tag) for tag in soup.find_all()) else "No"
    return {"Forms": forms_count, "Pop-Ups": popups}

# Fetch embedded scripts and categorize them
def fetch_embedded_scripts(soup):
    scripts = [script["src"] for script in soup.find_all("script") if script.get("src")]
    return scripts

# Scrape the website and extract the requested features
def scrape_website(url):
    headers = {"User-Agent": get_random_user_agent()}
    session = HTMLSession()
    response = session.get(url, headers=headers)

    if response.status_code != 200:
        st.warning("Could not access the webpage.")
        return None

    soup = BeautifulSoup(response.content, "html.parser")
    data = {}

    # 1. Multimedia Links (GIFs/Memes)
    data["Multimedia Links (GIFs/Memes)"] = extract_multimedia_links(soup)

    # 2. Content Type
    data["Content Type"] = check_dynamic_content(session, url)

    # 3. Trending Topics Detection
    content = " ".join([p.get_text() for p in soup.find_all("p")])
    data["Trending Topics"] = detect_trending_topics(content)

    # 4. Word Cloud
    if data["Trending Topics"]:
        wordcloud_fig = generate_trend_wordcloud(data["Trending Topics"])
        st.pyplot(wordcloud_fig)

    # 5. Audio Content Detection
    data["Audio Content Links"] = detect_audio_content(soup)

    # 6. CSS Animation Detection
    data["CSS Animations"] = extract_css_animations(soup)

    # 7. Interactive Elements Detection
    data["Interactive Elements"] = detect_interactive_elements(soup)

    # 8. Embedded Scripts
    data["Embedded Scripts"] = fetch_embedded_scripts(soup)

    # 9. High-Engagement Keywords
    words = content.split()
    keyword_density = {word: words.count(word) for word in set(words) if len(word) > 4}
    data["High-Engagement Keywords"] = sorted(keyword_density.items(), key=lambda x: x[1], reverse=True)[:10]

    # 10. Article Date Detection
    date_elements = soup.find_all("time")
    data["Article Dates"] = [date.get_text() for date in date_elements]

    # 11. API Data Extraction
    api_links = [link["href"] for link in soup.find_all("link", href=True) if "api" in link["href"]]
    data["API Data Links"] = api_links

    # 12. Call-to-Action Analysis
    cta_phrases = ["buy now", "sign up", "subscribe", "learn more", "download"]
    ctas = [phrase for phrase in cta_phrases if phrase in content.lower()]
    data["Call-to-Action Phrases"] = ctas

    return data

# Streamlit app
st.title("Advanced Web Data Scraping and Analysis Tool")

url = st.text_input("Enter a URL for analysis")

if st.button("Analyze"):
    if not validators.url(url):
        st.error("Please enter a valid URL.")
    else:
        with st.spinner("Scraping and analyzing..."):
            scraped_data = scrape_website(url)
            if scraped_data:
                st.json(scraped_data)
