from bs4 import BeautifulSoup
import datetime
import time
import random
import requests
import duckdb

BASE_URL = "https://www.funda.nl/zoeken/koop?search_result="
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:130.0) Gecko/20100101 Firefox/130.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 14; Pixel 7 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Mobile Safari/537.36"
]


db = duckdb.connect('src/housing.duckdb')

def safe_get(url, headers, retries=3, backoff=5):
    for i in range(retries):
        try:
            return requests.get(url, headers=headers, timeout=10)
        except requests.exceptions.RequestException as e:
            print(f"Request failed ({e}), retrying in {backoff} seconds...")
            time.sleep(backoff)
    return None

def get_random_headers():
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept-Language": random.choice(["en-US,en;q=0.9", "nl-NL,nl;q=0.9,en;q=0.8"]),
        "Referer": "https://www.funda.nl/",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Connection": "keep-alive"
    }


class FundaScraper:
    def __init__(self):
        self.listings = []
        self.links = []
        self.log = []
        self.duplicate_listings = 0

    def get_links(self, N):
        links = []
        page = 1

        while page < N:
            url = f"{BASE_URL}{page}"
            response = safe_get(url, get_random_headers())
            time.sleep(random.uniform(5,10))

            if response is None or response.status_code != 200:
                return []

            soup = BeautifulSoup(response.text, 'html.parser')
            page_listings = soup.find_all('a', {'data-testid': 'listingDetailsAddress'})
            hrefs_page = [a.get('href') for a in page_listings]

            links.extend(hrefs_page)
            page += 1
        return links
        

    def scrape_listing(self, url):
        response = requests.get(url, headers=get_random_headers())
        time.sleep(random.uniform(5,10))
        soup = BeautifulSoup(response.text, 'html.parser')

        price_div = soup.find('div', class_='flex gap-2 font-bold')
        if price_div:
            price_data = price_div.get_text(strip=True).replace('€', '').replace('.', '').replace(' kk', '').strip()
            # only keep numbers
            price_data = ''.join(filter(str.isdigit, price_data))

        tags = soup.find('div', class_='relative flex justify-between')
        if tags:
            labels = tags.attrs
            labels.pop('class')

        details_html = soup.find('ul', class_='flex flex-wrap gap-4')

        if details_html:
            details = details_html.find_all('span', class_='md:font-bold')
            # parse as usual
        else:
            print(f"⚠️ Skipping {url} — details block not found")
            return

        details_keys = details_html.find_all('span', class_='ml-1 hidden text-neutral-50 md:inline-block')
        details_keys = [span.get_text(strip=True) for span in details_keys]

        details_data = [span.get_text(strip=True) for span in details]
        details_data = [s.split(' ')[0] for s in details_data]
        
        details_dict = dict(zip(details_keys, details_data))
        
        try:
            price_dict = {'price': int(price_data)}
        except:
            price_dict = {'price': None}

        listing_dict = labels | details_dict | price_dict

        # Check for duplicate before inserting
        cursor = db.execute("SELECT 1 FROM listings WHERE postcode = ? AND housenumber = ?", 
                            (listing_dict.get('postcode'), listing_dict.get('housenumber')))
        if cursor.fetchone():
            print("Duplicate listing found, skipping insert.")
            self.duplicate_listings += 1
            return

        try:
            db.execute("INSERT INTO listings (neighbourhood, city, postcode, housenumber, province, country, wonen, slaapkamers, energielabel, price) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", 
                        (listing_dict.get('neighbourhoodidentifier'), listing_dict.get('city'), listing_dict.get('postcode'), 
                        listing_dict.get('housenumber'), listing_dict.get('province'), listing_dict.get('country'), 
                        listing_dict.get('wonen'), listing_dict.get('slaapkamers'), listing_dict.get('energielabel'), 
                        listing_dict.get('price')))
            
            db.commit()
            self.listings.append(listing_dict)
        except Exception as e:
            db.close()
            print("DB insert error:", e)

    def log_scraper_run(self):

        self.log.append(f"Ran at {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.log.append(f"Found {len(self.links)} links.")
        self.log.append(f"Scraped {len(self.listings)} listings.")
        self.log.append(f"Found {self.duplicate_listings} duplicate listings.")

        with open("../logs/scraper.log", "a") as f:
            f.writelines("\n".join(self.log) + "\n\n")

    def scrape_funda(self, N):
        links = self.get_links(N)

        for link in links:
            full_url = f"https://www.funda.nl{link}"
            self.scrape_listing(full_url)
    
        db.close()

