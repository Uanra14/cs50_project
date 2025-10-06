Real State Dashboard + Automated Scraper

#### Video Demo: <>
#### Description:

This project consists of two interconnected parts: one is a html scraper built in Python and the other one is a dashboard built using Streamlit on Python that displays some of the data gathered by the scraper. The two are linked by a database which uses the DuckDB management system.

The scraper is implemented as a python class and has two main processes in the src/Scraper.py file. First, it reads and stores the links off of the main results page of the Dutch online housing portal Funda. Then, uses the links to scrape the listing contained in them. After inspecting the page and finding the correct html classes where the useful information was stored, the package BeautifulSoup was used. This package allows us to extract the contents of specific sections of a website. For every listing, we obtained the following variables:

- Neighbourhood identifier
- City
- Postal Code
- House Number
- Province
- Country
- Size
- Number of Bedrooms
- Energy Label
- Price

All of these variables together with the timestamp at which the listing was scraped are stored in a database called housing.duckdb which contains only 1 table. Finally, to continually update the database, I used the Windows Task Scheduler to run the script scrape.py every week.

The dashboard runs from app.py and it reads the listings from the database and displays the results while offering some interactivity. Using Streamlit means that the program cannot read click events or have the interactivity of other tools, but its simplicity and easy of use are sufficient for a dashboard. The dashboard consists of 3 main elements: A scatterplot of the listings of price (y-axis) against surface area (x-axis), a map showing the average house price per province in the Netherlands, and finally, a sidebar which allows you to insert a point in the scatterplot based on your own price and surface area. The sidebar also allows you to customize the results by selecting a province, this filters the results shown in the scatterplot and highlights the selected province in the map. 

Furthermore, after adding your own listing to the scatterplot, a summary appears at the bottom of the page dsiplaying your selected price and surface area, as well as your average price per m^2. The latter comes with a label that tells you how your house price compares to the average in the selected area.

One fo the main challenges that I encountered is being rate-restricted by Funda, the housing portal. In order to circumvent that I added waiting times for the requests and rotating agents. Funda does not allow scraping for commercial purposes and they have tools to prevent it,  but after implementing the waiting times between requests, there have been no more issues related to not being able to load the website content.

In the middle of the development process, I realised that I might want to use a faster database management than sqlite3, and after some research I decided to use DuckDB, however, large parts of the data scraping had already been done, so I had to migrate from one system to the other. This was also a learning experience, as I had to be careful to have backups in case the migration went wrong. In the end, migrating from sqlite3 to DuckDB was easy and I encountered no problems when running the code in notebooks/migration.ipynb.

Some of the assets used in the dasboard (mainly to create the map) are stored in static/ and some miscellanious code is contained in the notebooks/ folder. helpers/ contains a function used to create the scatterplot in streamlit. logs/ contains the log messages of the weekly automated scrape which helps to troubleshoot whether the scraper is still working as intended. Finally .streamlit/ contains some aesthetic choices for the dashboard.