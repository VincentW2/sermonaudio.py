import requests
from bs4 import BeautifulSoup
import os
import urllib.parse
import re
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm

def sanitize_filename(filename):
    """Remove invalid characters from filename and truncate if necessary."""
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    return filename[:251] + '.mp3'

def fetch_sermon_data(url):
    """Fetch sermon details from the given URL."""
    if not url.startswith('https://'):
        url = 'https://' + url

    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')

    # Extract title
    title_element = soup.find(attrs={"data-v-29c0d6dd": True, "class": "title"})
    title = title_element.text.strip() if title_element else None

    if not title:
        for selector in ['meta[property="og:title"]', 'title', 'h1', '.title']:
            element = soup.select_one(selector)
            if element:
                title = element.get('content') if selector == 'meta[property="og:title"]' else element.text.strip()
                break

    title = title or "Untitled Sermon"

    if title.lower() == "sermonaudio":
        return None

    # Extract speaker and date
    speaker_element = soup.find(attrs={"data-v-29c0d6dd": True, "class": "speaker"})
    date_element = soup.find(attrs={"data-v-29c0d6dd": True, "class": "date"})

    speaker = speaker_element.text.strip() if speaker_element else "Unknown Speaker"
    date = date_element.text.strip() if date_element else "Unknown Date"

    # Extract MP3 URL
    audio_element = soup.find('audio')
    mp3_url = audio_element.get('src') if audio_element else None

    return {
        "title": title,
        "speaker": speaker,
        "date": date,
        "mp3_url": mp3_url
    }

def download_sermon(url, output_directory, downloaded_titles):
    """Download a sermon from the given URL."""
    sermon_data = fetch_sermon_data(url)
    if not sermon_data or sermon_data['title'] in downloaded_titles:
        return False

    print(f"Downloading: {sermon_data['title']}")

    if sermon_data['mp3_url']:
        try:
            encoded_url = urllib.parse.quote(sermon_data['mp3_url'], safe=':/?&=')
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            response = requests.get(encoded_url, headers=headers, stream=True)
            response.raise_for_status()

            total_size = int(response.headers.get('content-length', 0))
            
            filename = sanitize_filename(sermon_data['title'])
            filepath = os.path.join(output_directory, filename)
            
            with open(filepath, 'wb') as file, tqdm(
                desc=filename,
                total=total_size,
                unit='iB',
                unit_scale=True,
                unit_divisor=1024,
            ) as progress_bar:
                for data in response.iter_content(chunk_size=1024):
                    size = file.write(data)
                    progress_bar.update(size)
            
            downloaded_titles.add(sermon_data['title'])
            return True
        except requests.exceptions.RequestException as e:
            print(f"Error downloading {sermon_data['title']}: {e}")
        except IOError as e:
            print(f"Error writing file for {sermon_data['title']}: {e}")
    else:
        print(f"MP3 URL not found for {sermon_data['title']}")
    return False

def fetch_sermon_urls(series_url):
    """Fetch all sermon URLs from the series page."""
    if not series_url.startswith('https://'):
        series_url = 'https://' + series_url

    print(f"Fetching series page: {series_url}")
    
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    with webdriver.Chrome(options=chrome_options) as driver:
        driver.get(series_url)
        
        # Scroll to load all content
        last_height = driver.execute_script("return document.body.scrollHeight")
        while True:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height

        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
    sermon_urls = set()
    for link in soup.find_all('a', href=True):
        if '/sermons/' in link['href']:
            full_url = urllib.parse.urljoin('https://beta.sermonaudio.com', link['href'])
            sermon_urls.add(full_url)

    print(f"Total unique sermon URLs found: {len(sermon_urls)}")
    return list(sermon_urls)

def download_series(series_url, output_directory):
    """Download all sermons in the series."""
    sermon_urls = fetch_sermon_urls(series_url)
    print(f"Found {len(sermon_urls)} unique sermons in the series.")

    downloaded_titles = set()

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(download_sermon, url, output_directory, downloaded_titles) for url in sermon_urls]
        for future in tqdm(futures, total=len(sermon_urls), desc="Overall Progress"):
            future.result()

# Example usage
if __name__ == "__main__":
    series_url = "beta.sermonaudio.com/series/155070/"
    output_directory = "downloaded_sermons"

    os.makedirs(output_directory, exist_ok=True)

    download_series(series_url, output_directory)