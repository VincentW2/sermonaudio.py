import requests
from bs4 import BeautifulSoup
import os
import urllib.parse
import re
import time

def sanitize_filename(filename):
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    filename = filename.strip()
    return filename[:251] + '.mp3'

def fetch_sermon_data(url):
    if not url.startswith('https://'):
        url = 'https://' + url

    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')

    title = None
    title_element = soup.find(attrs={"data-v-29c0d6dd": True, "class": "title"})
    if title_element:
        title = title_element.text.strip()
    
    if not title:
        meta_title = soup.find('meta', property='og:title')
        if meta_title:
            title = meta_title['content']
    
    if not title:
        title_tag = soup.find('title')
        if title_tag:
            title = title_tag.text.strip()
    
    if not title:
        h1_tag = soup.find('h1')
        if h1_tag:
            title = h1_tag.text.strip()

    if not title:
        title_element = soup.find(class_=re.compile('title', re.I))
        if title_element:
            title = title_element.text.strip()

    title = title if title else "Untitled Sermon"

    speaker_element = soup.find(attrs={"data-v-29c0d6dd": True, "class": "speaker"})
    date_element = soup.find(attrs={"data-v-29c0d6dd": True, "class": "date"})

    speaker = speaker_element.text.strip() if speaker_element else "Unknown Speaker"
    date = date_element.text.strip() if date_element else "Unknown Date"

    audio_element = soup.find('audio')
    mp3_url = audio_element.get('src') if audio_element else None

    return {
        "title": title,
        "speaker": speaker,
        "date": date,
        "mp3_url": mp3_url
    }

def download_sermon(url, output_directory):
    sermon_data = fetch_sermon_data(url)
    print("Sermon Title:", sermon_data['title'])
    print("Speaker:", sermon_data['speaker'])
    print("Date:", sermon_data['date'])
    print("MP3 URL:", sermon_data['mp3_url'])

    if sermon_data['mp3_url']:
        try:
            encoded_url = urllib.parse.quote(sermon_data['mp3_url'], safe=':/?&=')
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            head_response = requests.head(encoded_url, headers=headers)
            head_response.raise_for_status()
            
            content_type = head_response.headers.get('Content-Type', '')
            content_length = int(head_response.headers.get('Content-Length', 0))
            
            if 'audio' not in content_type.lower():
                print(f"Warning: Content type is {content_type}, not audio as expected.")
            
            print(f"File size: {content_length / (1024*1024):.2f} MB")
            
            mp3_response = requests.get(encoded_url, headers=headers, stream=True)
            mp3_response.raise_for_status()

            filename = sanitize_filename(sermon_data['title'])
            filepath = os.path.join(output_directory, filename)
            
            with open(filepath, 'wb') as f:
                for chunk in mp3_response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            print(f"Downloaded: {filename}")
            return True
        except requests.exceptions.RequestException as e:
            print(f"Error during download: {e}")
        except IOError as e:
            print(f"Error writing file: {e}")
    else:
        print("MP3 URL not found in sermon data")
    return False

def fetch_sermon_urls(series_url):
    if not series_url.startswith('https://'):
        series_url = 'https://' + series_url

    print(f"Fetching series page: {series_url}")
    response = requests.get(series_url)
    print(f"Response status code: {response.status_code}")

    soup = BeautifulSoup(response.content, 'html.parser')

    sermon_urls = []
    
    # Find the first div with data-v-29c0d6dd attribute
    outer_div = soup.find('div', attrs={'data-v-29c0d6dd': True})
    
    if outer_div:
        print("Found outer div with data-v-29c0d6dd attribute")
        
        # Find the div with data-fetch-key="SiteFilteredSermonList:0"
        filtered_list_div = outer_div.find('div', attrs={'data-fetch-key': 'SiteFilteredSermonList:0'})
        
        if filtered_list_div:
            print("Found div with data-fetch-key='SiteFilteredSermonList:0'")
            
            # Find the div with data-fetch-key="ScrollList:0"
            scroll_list_div = filtered_list_div.find('div', attrs={'data-fetch-key': 'ScrollList:0'})
            
            if scroll_list_div:
                print("Found div with data-fetch-key='ScrollList:0'")
                
                # Find all sermon links within this div
                sermon_links = scroll_list_div.find_all('a', class_='sermon-title', href=True)
                
                for link in sermon_links:
                    full_url = 'https://beta.sermonaudio.com' + link['href']
                    sermon_urls.append(full_url)
                    print(f"Found sermon URL: {full_url}")
            else:
                print("Could not find div with data-fetch-key='ScrollList:0'")
        else:
            print("Could not find div with data-fetch-key='SiteFilteredSermonList:0'")
    else:
        print("Could not find outer div with data-v-29c0d6dd attribute")

    print(f"Total sermon URLs found: {len(sermon_urls)}")
    return sermon_urls

def download_series(series_url, output_directory):
    sermon_urls = fetch_sermon_urls(series_url)
    print(f"Found {len(sermon_urls)} sermons in the series.")

    for i, url in enumerate(sermon_urls, 1):
        print(f"\nDownloading sermon {i} of {len(sermon_urls)}")
        success = download_sermon(url, output_directory)
        if success:
            print(f"Successfully downloaded sermon {i}")
        else:
            print(f"Failed to download sermon {i}")
        
        # Add a delay to avoid overwhelming the server
        if i < len(sermon_urls):
            time.sleep(2)


# Example usage
series_url = "beta.sermonaudio.com/series/155070/"
output_directory = "downloaded_sermons"

os.makedirs(output_directory, exist_ok=True)

sermon_urls = fetch_sermon_urls(series_url)
print(f"Found {len(sermon_urls)} sermons in the series.")

if sermon_urls:
    download_series(series_url, output_directory)
else:
    print("No sermons found. Cannot proceed with download.")