import streamlit as st
import requests
from bs4 import BeautifulSoup
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from textblob import TextBlob
import re
import random
import time

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

st.title("Advanced Web Data Scraping Tool")
st.write("Enter a website URL to scrape and discover hidden insights.")

# User input for the website URL
url = st.text_input("Website URL", "https://example.com")

# Button to initiate scraping
if st.button("Scrape Data"):
    try:
        # Adding a random User-Agent header to the request
        headers = {
            'User-Agent': get_random_user_agent()
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raise an error for bad responses

        # Adding a random delay to mimic human behavior
        time.sleep(random.uniform(1, 3))

        # Parse the content with BeautifulSoup
        soup = BeautifulSoup(response.content, 'html.parser')

        # 1. Extract and Display Page Title
        page_title = soup.title.string if soup.title else "No title found"
        st.write("**Page Title:**", page_title)

        # 2. Keyword Extraction and Tag Cloud
        paragraphs = [p.get_text() for p in soup.find_all('p')]
        text_content = ' '.join(paragraphs)

        if text_content.strip():  # Check if text_content is not empty
            wordcloud = WordCloud(width=800, height=400, background_color='white').generate(text_content)
            st.write("**Keyword Tag Cloud**")
            fig, ax = plt.subplots()
            ax.imshow(wordcloud, interpolation='bilinear')
            ax.axis('off')
            st.pyplot(fig)
        else:
            st.warning("No text content found to generate a word cloud.")

        # 3. Sentiment Analysis
        blob = TextBlob(text_content)
        sentiment = blob.sentiment.polarity
        st.write("**Sentiment Analysis:**", "Positive" if sentiment > 0 else "Negative" if sentiment < 0 else "Neutral")

        # 4. Automatic Summary Generator
        sentences = text_content.split('. ')
        summary = '. '.join(sentences[:5])  # Simple summarization (first few sentences)
        st.write("**Page Summary:**", summary)

        # 5. Image and Metadata Extraction
        st.write("**Images on the Page**")
        images = soup.find_all('img', src=True)
        for img in images[:5]:  # Limit to first 5 images for demo
            img_url = img['src']
            if not img_url.startswith('http'):
                img_url = requests.compat.urljoin(url, img_url)
            st.image(img_url, caption=img.get('alt', 'No description'), use_column_width=True)

        # 6. Contact Information Extraction
        st.write("**Contact Information on Page**")
        emails = set(re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text_content))
        if emails:
            for email in emails:
                st.write(email)
        else:
            st.write("No email addresses found on this page.")

        # 7. Interactive Page Structure Visualization
        st.write("**Page Structure (Heading Levels)**")
        headings = [soup.find_all(f'h{i}') for i in range(1, 7)]
        for i, heading_group in enumerate(headings, start=1):
            if heading_group:
                st.write(f"### Heading Level {i}")
                for heading in heading_group:
                    st.write(f"- {heading.get_text().strip()}")

    except requests.exceptions.HTTPError as e:
        if response.status_code == 401:
            st.error("Unauthorized access. You may need to log in to view this content.")
        else:
            st.error(f"An HTTP error occurred: {e}")
    except requests.exceptions.RequestException as e:
        st.error(f"A network error occurred: {e}")
