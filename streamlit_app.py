import streamlit as st
import requests
from bs4 import BeautifulSoup

# Set up the Streamlit app layout
st.title("Live Web Data Scraping Tool")
st.write("Enter a website URL to scrape data.")

# User input for the website URL
url = st.text_input("Website URL", "https://example.com")

# Button to initiate scraping
if st.button("Scrape Data"):
    try:
        # Make an HTTP GET request to fetch the page content
        response = requests.get(url)
        response.raise_for_status()  # Check if request was successful

        # Parse the content with BeautifulSoup
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract the title of the page as a sample output
        page_title = soup.title.string if soup.title else "No title found"
        st.write("**Page Title:**", page_title)
        
        # Display the first few paragraphs of text (or other data points)
        paragraphs = soup.find_all('p', limit=3)  # Limit to first 3 paragraphs for preview
        for idx, p in enumerate(paragraphs, start=1):
            st.write(f"**Paragraph {idx}:**", p.get_text())
            
        # Additional scraped data (e.g., links on the page)
        links = soup.find_all('a', href=True, limit=5)
        st.write("**Some Links on the Page:**")
        for link in links:
            st.write(link['href'])
            
    except requests.exceptions.RequestException as e:
        st.error(f"An error occurred: {e}")
