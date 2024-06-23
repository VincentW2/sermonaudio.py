import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import sys

def search_sermonaudio(query):
    base_url = 'https://www.sermonaudio.com'
    search_url = f'{base_url}/sermons.asp?keyword={query}'
    
    try:
        response = requests.get(search_url)
        response.raise_for_status()  # Ensure the request was successful
    except requests.exceptions.RequestException as e:
        print(f"Error fetching the search results page: {e}")
        return []

    soup = BeautifulSoup(response.content, 'html.parser')

    search_results = []
    results = soup.find_all('div')
    
    for result in results:
        title_tag = result.find('a', class_='sermonlink')
        link_tag = title_tag  # Usually, the title tag itself is the link tag

        if title_tag and link_tag:
            title = title_tag.text.strip()
            relative_url = link_tag.get('href')
            full_url = urljoin(base_url, relative_url)
            search_results.append({'title': title, 'url': full_url})
    
    return search_results

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python scriptname.py (query)")
        sys.exit(1)
    
    query = sys.argv[1]
    results = search_sermonaudio(query)

    for result in results:
        print(f"Title: {result['title']}")
        print(f"URL: {result['url']}")
        print()
