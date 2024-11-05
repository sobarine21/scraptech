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
import textstat  # Changed from readability to textstat
import validators

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

# Function to check if a link is valid
def is_valid_url(url):
    return validators.url(url)

# Function to extract and validate links
def extract_links(soup):
    links = []
    for link in soup.find_all('a', href=True):
        href = link['href']
        if is_valid_url(href):
            links.append(href)
    return links

st.title("Advanced Web Data Scraping Tool")
st.write("Enter a website URL to scrape and discover hidden insights.")

# User input for the website URL
url = st.text_input("Website URL", "https://example.com")

# Button to initiate scraping
if st.button("Scrape Data"):
    attempt = 0
    max_attempts = 5
    while attempt < max_attempts:
        try:
            headers = {
                'User-Agent': get_random_user_agent()
            }
            start_time = time.time()
            response = requests.get(url, headers=headers)
            response.raise_for_status()  # Raise an error for bad responses

            # Adding a random delay to mimic human behavior
            time.sleep(random.uniform(2, 5))

            # Parse the content with BeautifulSoup
            soup = BeautifulSoup(response.content, 'html.parser')

            # 1. Extract and Display Page Title
            page_title = soup.title.string if soup.title else "No title found"
            st.write("**Page Title:**", page_title)

            # 2. Fetch and Display Meta Tags
            meta_tags = {meta.get('name', ''): meta.get('content', '') for meta in soup.find_all('meta')}
            st.write("**Meta Tags:**", meta_tags)

            # 3. Keyword Density Analysis
            paragraphs = [p.get_text() for p in soup.find_all('p')]
            text_content = ' '.join(paragraphs)

            if text_content.strip():
                wordcloud = WordCloud(width=800, height=400, background_color='white').generate(text_content)
                st.write("**Keyword Tag Cloud**")
                fig, ax = plt.subplots()
                ax.imshow(wordcloud, interpolation='bilinear')
                ax.axis('off')
                st.pyplot(fig)

                # Keyword Density Calculation
                words = text_content.split()
                keyword_density = {word: words.count(word) / len(words) * 100 for word in set(words)}
                st.write("**Keyword Density:**", dict(sorted(keyword_density.items(), key=lambda item: item[1], reverse=True)))

            # 4. Sentiment Analysis
            blob = TextBlob(text_content)
            sentiment = blob.sentiment.polarity
            st.write("**Sentiment Analysis:**", "Positive" if sentiment > 0 else "Negative" if sentiment < 0 else "Neutral")

            # 5. Content Length Analysis
            content_length = len(text_content)
            st.write("**Content Length:**", content_length, "characters")

            # 6. Language Detection
            detected_language = langdetect.detect(text_content)
            st.write("**Detected Language:**", detected_language)

            # 7. Top 5 Links Extraction
            links = extract_links(soup)
            top_internal_links = [link for link in links if url in link][:5]
            top_external_links = [link for link in links if url not in link][:5]
            st.write("**Top 5 Internal Links:**", top_internal_links)
            st.write("**Top 5 External Links:**", top_external_links)

            # 8. Extract Social Media Links
            social_media_links = [link for link in links if "facebook.com" in link or "twitter.com" in link or "instagram.com" in link]
            st.write("**Social Media Links:**", social_media_links)

            # 9. Check for Broken Links
            broken_links = []
            for link in links:
                try:
                    res = requests.head(link, allow_redirects=True)
                    if res.status_code != 200:
                        broken_links.append(link)
                except Exception as e:
                    broken_links.append(link)
            st.write("**Broken Links:**", broken_links)

            # 10. Extract JSON-LD Data
            json_ld_data = []
            for script in soup.find_all('script', type='application/ld+json'):
                json_ld_data.append(script.string)
            st.write("**JSON-LD Data:**", json_ld_data)

            # 11. Image and Alt Text Extraction
            st.write("**Images and Alt Text on the Page**")
            images = soup.find_all('img', src=True)
            image_data = [(img['src'], img.get('alt', 'No description')) for img in images]
            for img_url, alt in image_data[:5]:  # Limit to first 5 images for demo
                st.image(img_url, caption=alt, use_column_width=True)

            # 12. Video Extraction
            video_links = [source['src'] for source in soup.find_all('source') if 'video' in source['src']]
            st.write("**Video Links:**", video_links)

            # 13. Check SSL Certificate Validity
            try:
                ssl_response = requests.get(url, verify=True)
                st.write("**SSL Certificate Validity:** Valid")
            except requests.exceptions.SSLError:
                st.write("**SSL Certificate Validity:** Invalid")

            # 14. Extract Author Information
            author = soup.find('meta', attrs={'name': 'author'})
            if author:
                st.write("**Author Information:**", author['content'])
            else:
                st.write("**Author Information:** Not found.")

            # 15. Readability Score using textstat
            readability_score = textstat.flesch_kincaid_grade(text_content)
            st.write("**Readability Score (Flesch-Kincaid Grade):**", readability_score)

            # 16. FAQs Extraction
            faqs = []
            for faq in soup.find_all('div', class_='faq'):
                questions = faq.find_all('h3')
                answers = faq.find_all('p')
                for question, answer in zip(questions, answers):
                    faqs.append({'question': question.get_text(), 'answer': answer.get_text()})
            st.write("**FAQs:**", faqs)

            # 17. Content Extraction from Tables
            tables = soup.find_all('table')
            table_data = []
            for table in tables:
                rows = table.find_all('tr')
                for row in rows:
                    cols = row.find_all('td')
                    table_data.append([col.get_text() for col in cols])
            st.write("**Table Data:**", table_data)

            # 18. Responsive Design Checker (Placeholder)
            st.write("**Responsive Design Checker:**")
            st.write("This feature simulates checking the responsiveness of the site (not implemented).")

            # 19. Heatmap Data (Placeholder)
            st.write("**Heatmap Data:**")
            st.write("This feature simulates user interaction heatmap (not implemented).")

            # 20. Export to CSV
            data_to_export = {
                'Title': page_title,
                'Meta Tags': meta_tags,
                'Keyword Density': keyword_density,
                'Sentiment': sentiment,
                'Content Length': content_length,
                'Language': detected_language,
                'Internal Links': top_internal_links,
                'External Links': top_external_links,
                'Social Media Links': social_media_links,
                'Broken Links': broken_links,
                'JSON-LD Data': json_ld_data,
                'Image Data': image_data,
                'Video Links': video_links,
                'Author': author['content'] if author else 'Not found',
                'Readability Score': readability_score,
                'FAQs': faqs,
                'Table Data': table_data,
            }
            df = pd.DataFrame(data_to_export)
            csv_file = f"{url.split('//')[-1].replace('/', '_')}.csv"
            df.to_csv(csv_file, index=False)
            st.download_button(label="Download CSV", data=csv_file, mime='text/csv')

            break  # Exit the while loop if successful

        except requests.exceptions.HTTPError as e:
            if response.status_code == 401:
                st.error("Unauthorized access. You may need to log in to view this content.")
                break  # Exit on 401 error
            elif response.status_code == 429:
                st.warning("Too many requests. Slowing down...")
                time.sleep(random.uniform(10, 20))  # Wait longer if 429 error
            else:
                st.error(f"An HTTP error occurred: {e}")
                break  # Exit on other HTTP errors
        except requests.exceptions.RequestException as e:
            st.error(f"A network error occurred: {e}")
            break  # Exit on request exception
        attempt += 1  # Increment the attempt counter
