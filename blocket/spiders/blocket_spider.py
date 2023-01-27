import logging
import os
import re
from datetime import datetime, timedelta
from time import sleep

from bs4 import BeautifulSoup
from scrapy import Spider, Request
from scrapy.spiders import CrawlSpider
from scrapy_selenium import SeleniumRequest
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By

from blocket.items import AdItem

# logging.getLogger('scrapy').setLevel(logging.ERROR)
logging.getLogger('urllib3').setLevel(logging.ERROR)
logging.getLogger('selenium').setLevel(logging.ERROR)


class BlocketSpider(CrawlSpider):
    name = "blocket"

    def __init__(self, *a, **kw):
        self.urls_set = load_urls_from_file()
        super().__init__(*a, **kw)

    def start_requests(self):
        url = 'https://www.blocket.se/annonser/hela_sverige/fordon/bilar?cg=1020&page={}'
        for i in range(1, 40):
            yield Request(url=url.format(i), callback=self.parse)

    def parse(self, response, **kwargs):
        driver = create_web_driver()
        url = response.request.url
        driver.get(url)
        sleep(2)
        try:
            element = driver.find_element(By.ID, 'close-modal')
            driver.execute_script("arguments[0].click();", element)
        except Exception:
            pass
        driver.execute_script("window.scrollTo(0, 1080);")
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        inner_div = soup.find('div', attrs={'class': 'MediumLayout__BodyWrapper-sc-q6qal1-2 gYhFaY'})
        urls = inner_div.find_all('a', attrs={'class': 'Link-sc-6wulv7-0 styled__StyledTitleLink-sc-1kpvi4z-11 cDtkQI buxcTF'},
                                  href=True)
        for url in urls:
            url = url['href']
            if 'https' not in url:
                url = 'https://www.blocket.se/'+ url
                if url in self.urls_set:
                    continue
                try:
                    yield Request(url=url, callback=self.parse_vehicle)
                except Exception as e:
                    print(e)
        driver.quit()

    def parse_vehicle(self, response):

        driver = create_web_driver()
        url = response.request.url
        driver.get(url)
        result_dict = {}
        sleep(2)
        write_url_to_file(url)
        elements = driver.find_elements(By.XPATH, '//button[@class="ExpandableContent__StyledShowMoreButton-sc-11a0rym-2 ciXgYN"]')
        for element in elements:
            driver.execute_script("arguments[0].click();", element)
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        info_all = soup.find_all('div', attrs={'class': 'TextBody__TextBodyWrapper-sc-cuv1ht-0 jigUjJ BodyCard__DescriptionPart-sc-15r463q-2 emQvjf'})
        text = ''
        for info in info_all:
            text += info.text
        result_dict.update({'description': text})
        names = soup.find_all('div', attrs={'class': 'TextCallout2__TextCallout2Wrapper-sc-1bir8f0-0 cKftCy ParamsWithIcons__StyledLabel-sc-hanfos-2 jDzBlo'})
        values = soup.find_all('div', attrs={
            'class': 'TextCallout1__TextCallout1Wrapper-sc-swd73-0 dgjfBr ParamsWithIcons__StyledParamValue-sc-hanfos-3 fKapdA'})
        for name, value in zip(names, values):
            result_dict.update({name.text: value.text})

        date = soup.find('span', attrs={'class': 'TextCallout2__TextCallout2Wrapper-sc-1bir8f0-0 cKftCy PublishedTime__StyledTime-sc-pjprkp-1 hCZACp'})
        if date:
            date = self.process_date(date.text)
            result_dict.update({'date': date})
        title = soup.find('h1', attrs={'class': 'TextHeadline1__TextHeadline1Wrapper-sc-1bi3cli-0 deiffs Hero__StyledSubject-sc-1mjgwl-4 kusrLk'}).text
        price = soup.find('div', attrs={'class': 'TextHeadline1__TextHeadline1Wrapper-sc-1bi3cli-0 deiffs Price__StyledPrice-sc-crp2x0-0 gJzyZt'}).text
        price_vat = soup.find('div', attrs={'class': 'TextCallout2__TextCallout2Wrapper-sc-1bir8f0-0 cKftCy Hero__StyledPriceWithoutVat-sc-1mjgwl-6 hDRzcc'}).text
        url = driver.current_url
        car_id = driver.current_url.split('/')[-1]
        pictures = self.extract_pictures(driver)
        result_dict.update({'_id': car_id,
                            'pictures': pictures, 'title': title, 'price': price, 'price_ex_vat':price_vat,
                            'vat': True if price_vat else False, 'url': url })
        item = self.create_ad_item(result_dict)
        driver.quit()
        return item

    @staticmethod
    def extract_pictures(driver):
        pictures_list = []
        try:
            el = driver.find_element(By.XPATH, '//article//div//div')
            driver.execute_script("arguments[0].click();", el)
        except Exception:
            pass
        ele = driver.find_elements(By.XPATH, '//div[contains(@style,"background-image: url")]')
        sleep(1)
        for i in ele:
            slide_button = driver.find_elements(By.XPATH, '//button[contains(@class,"SliderControls__StyledButton")]')
            if slide_button:
                driver.execute_script("arguments[0].click();", slide_button[0])
                sleep(0.1)
            pictures_list.append(re.search('\(([^)]+)', i.get_attribute('style')).group(1).replace('"',''))
        return [url for url in pictures_list if url]


    def create_ad_item(self, data: dict):
        ad = AdItem()
        ad['_id'] = data.get('_id')
        ad['description'] = data.get('description')
        ad['fuel'] = data.get('Bränsle','').strip()
        ad['title'] = data.get('title')
        ad['make']= data.get('Märke', '').strip()
        ad['year']= data.get('Datum i trafik')
        ad['price'] = data.get('price')
        ad['url'] = data.get('url')
        ad['distance'] = data.get('Miltal', '').replace(r'\xa', '')
        ad['image_urls'] = data.get('pictures', '')
        ad['model'] = data.get('Modell', '')
        ad['date'] = data.get('date', )
        ad['engine'] = data.get('Motorstorlek')
        ad['date_in_traffic'] = data.get('Datum i trafik')
        return ad

    def process_date(self, date):
        if 'idag' in date:
            date = datetime.today().strftime('%Y-%m-%d')
        elif 'igår' in date:
            yesterday = datetime.now() - timedelta(1)
            date = yesterday.strftime('%Y-%m-%d')
        return date.replace('Inlagd: ', '')


def create_web_driver(driver_name='chrome'):
    if driver_name == 'chrome':
        s = Service('./chromedriver.exe')
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--enable-javascript")
        chrome_options.add_argument('ignore-certificate-errors')
        chrome_options.add_experimental_option("prefs", {"profile.default_content_setting_values.cookies": 2})
        driver = webdriver.Chrome(service=s, options=chrome_options)
        return driver

def write_url_to_file(url):
    with open('url.txt', 'a') as the_file:
        the_file.write(url + '\n')

def load_urls_from_file(file_name = 'url.txt'):
    url_set = set()
    if not os.path.exists(file_name):
        return url_set
    with open('url.txt') as file:
        for line in file:
            url_set.add(line.rstrip())
    return url_set
