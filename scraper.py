import logging
import requests
import os
import json
from flask import Flask, request, jsonify
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Debug: Print all environment variables
print("Environment Variables:")
for key, value in os.environ.items():
    print(f"{key}: {value}")

supabase_url = "sike"
supabase_key = "sike"
openai_api_key = "sike"

# Debug statements to check if the variables are loaded
print(f"Supabase URL: {supabase_url}")
print(f"Supabase Key: {supabase_key}")

if not supabase_url or not supabase_key:
    raise ValueError("Supabase URL and Key must be provided")

supabase: Client = create_client(supabase_url, supabase_key)

logging.basicConfig(level=logging.DEBUG, filename='scraper.log', filemode='w')

app = Flask(__name__)

def get_html(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        html = response.text
        logging.debug(f"Fetched HTML from {url}: {html[:500]}")  # Log first 500 characters
        soup = BeautifulSoup(html, 'html.parser')

        for tag in soup(["script", "style", "img"]):
            tag.extract()

        main_content = soup.get_text(separator='\n')

        links = set()
        for link in soup.find_all('a', href=True):
            href = link.get('href').strip()
            full_url = urljoin(url, href)
            links.add(full_url)

        return main_content, links, soup
    except requests.RequestException as e:
        logging.error(f"Error fetching {url}: {e}")
        return None, set(), None

def get_links(html, base_url):
    soup = BeautifulSoup(html, 'html.parser')
    links = set()

    base_domain = urlparse(base_url).netloc

    for link in soup.find_all('a', href=True):
        href = link.get('href').strip()
        full_url = urljoin(base_url, href)
        full_url = full_url.split('?', 1)[0].split('#', 1)[0]

        parsed_url = urlparse(full_url)
        if parsed_url.netloc == base_domain:
            links.add(full_url)

    return links

def scrape_website(base_url):
    visited = set()
    all_html = ''
    
    def scrape_page(url, depth):
        nonlocal all_html

        domain_quivr = 'https://www.quivr.com/'

        if url in visited:
            return
        visited.add(url)

        logging.debug(f"Scraping: {url}")

        max_depth = 2 if url.startswith(domain_quivr) else 1

        if depth > max_depth:
            return

        main_content, all_links, soup = get_html(url)
        if not main_content:
            return

        all_html += main_content

        for link in all_links:
            scrape_page(link, depth + 1)

    scrape_page(base_url, 0)

    return all_html

def chat_with_gpt(context, prompt):
    if not openai_api_key:
        raise ValueError("OpenAI API key must be provided")

    api_url = 'https://api.openai.com/v1/chat/completions'
    
    headers = {
        'Authorization': f'Bearer {openai_api_key}',
        'Content-Type': 'application/json'
    }

    context_chunks = [context[i:i+25000] for i in range(0, len(context), 25000)]

    messages = [{"role": "system", "content": "You are a helpful assistant."}]
    for chunk in context_chunks:
        messages.append({"role": "user", "content": chunk})

    messages.append({"role": "user", "content": prompt})

    data = {
        "model": "gpt-4-turbo",
        "messages": messages
    }

    response = requests.post(api_url, headers=headers, json=data)
    if response.status_code == 200:
        result = response.json()['choices'][0]['message']['content']
        
        # Clean up the result to ensure it's valid JSON
        result = result.strip().strip('```json').strip('```').strip()
        
        # Parse the cleaned result to ensure it's valid JSON
        try:
            json_result = json.loads(result)
            return json_result
        except json.JSONDecodeError as e:
            print(f"JSON decode error: {e}")
            return None
    else:
        print(f"Error with API request: {response.status_code}, {response.text}")
        return None

@app.route('/scrape', methods=['POST'])
def scrape():
    data = request.get_json()
    base_url = data.get('url')
    if not base_url:
        return jsonify({'error': 'No URL provided'}), 400
    
    # Scrape the website content
    scraped_html = scrape_website(base_url)
    
    # Parse the scraped HTML content
    soup = BeautifulSoup(scraped_html, 'html.parser')
    text_content = soup.get_text()
    
    # Define the prompt for the GPT model
    prompt = (
        "Extract the following information in JSON format: Company Name, Employee Count, Founder LinkedIn Links, "
        "Products, and Sectors. For Founder LinkedIn Links, ensure you find the official LinkedIn profiles of the founders. "
        "Verify the accuracy of the LinkedIn links for founders by checking their names and roles. Ensure the products and sectors are correctly identified. "
        "Exclude any information if it is uncertain or ambiguous, and translate any non-English information into English. If you are unsure about any detail, omit it from the response. "
        "Your output should only be valid JSON, do not include any other text."
    )
    
    # Get the response from the GPT model
    response = chat_with_gpt(text_content, prompt)
    if response:
        return jsonify(response)
    else:
        return jsonify({'error': 'Failed to get response from ChatGPT API'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
