from bs4 import BeautifulSoup
import requests
import sqlite3
import os

BASE_URL = "https://www.funda.nl/zoeken/koop?search_result="
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

db = sqlite3.connect('housing.db')


class Listing:
    def __init__(self, address, zip_code, price, size):
        self.address = address
        self.zip_code = zip_code
        self.price = price
        self.size = size


class FundaScraper:
    def __init__(self):
        self.listings = []


    def get_links(self):
        links = []
        page = 1

        while page < 100:
            url = f"{BASE_URL}{page}"
            response = requests.get(url, headers=HEADERS)

            if response.status_code != 200:
                break

            soup = BeautifulSoup(response.text, 'html.parser')
            page_listings = soup.find_all('a', {'data-testid': 'listingDetailsAddress'})
            hrefs_page = [a.get('href') for a in page_listings]

            links.extend(hrefs_page)
            page += 1
        return links
        

    def scrape_listing(self, url):
        response = requests.get(url, headers=HEADERS)
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
        details = details_html.find_all('span', class_='md:font-bold')

        details_keys = details_html.find_all('span', class_='ml-1 hidden text-neutral-50 md:inline-block')
        details_keys = [span.get_text(strip=True) for span in details_keys]

        details_data = [span.get_text(strip=True) for span in details]
        details_data = [s.split(' ')[0] for s in details_data]
        
        details_dict = dict(zip(details_keys, details_data))
        price_dict = {'price': int(price_data)}

        listing_dict = labels | details_dict | price_dict

        # Check for duplicate before inserting
        cursor = db.execute("SELECT 1 FROM listings WHERE postcode = ? AND housenumber = ?", 
                            (listing_dict.get('postcode'), listing_dict.get('housenumber')))
        if cursor.fetchone():
            print("Duplicate listing found, skipping insert.")
            return

        try:
            db.execute("INSERT INTO listings (neighbourhood, city, postcode, housenumber, province, country, wonen, slaapkamers, energielabel, price) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", 
                        (listing_dict.get('neighbourhoodidentifier'), listing_dict.get('city'), listing_dict.get('postcode'), 
                        listing_dict.get('housenumber'), listing_dict.get('province'), listing_dict.get('country'), 
                        listing_dict.get('wonen'), listing_dict.get('slaapkamers'), listing_dict.get('energielabel'), 
                        listing_dict.get('price')))
            
            db.commit()
            print("Inserted listing:", listing_dict)
        except Exception as e:
            db.close()
            print("DB insert error:", e)


    def scrape_funda(self):
        links = self.get_links()

        for link in links:
            full_url = f"https://www.funda.nl{link}"
            self.scrape_listing(full_url)
    
        db.close()  # <-- Close here, after all inserts


if __name__ == "__main__":
    scraper = FundaScraper()
    listing = scraper.scrape_funda()
