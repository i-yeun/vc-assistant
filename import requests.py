import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

def get_html(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        html = response.text
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
        print(f"Error fetching {url}: {e}")
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

        print(f"Scraping: {url}")

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
    openai_api_key = 'your-key' #add your key here
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
        "model": "gpt-3.5-turbo-1106",
        "messages": messages
    }

    response = requests.post(api_url, headers=headers, json=data)
    if response.status_code == 200:
        result = response.json()['choices'][0]['message']['content']
        return result
    else:
        print(f"Error with API request: {response.status_code}, {response.text}")
        return None

def main():
    base_url = 'YOUR URL' #add your url here
    scraped_html = scrape_website(base_url)
    
    soup = BeautifulSoup(scraped_html, 'html.parser')
    text_content = soup.get_text()
    
    prompt = "YOUR PROMPT" #add your prompt here
    
    response = chat_with_gpt(text_content, prompt)
    if response:
        print("ChatGPT Response:")
        print(response)
    else:
        print("Failed to get response from ChatGPT API")

if __name__ == '__main__':
    main()
