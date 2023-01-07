import logging
from time import sleep

from bs4 import BeautifulSoup
from scrapy import Spider, Request
from scrapy_selenium import SeleniumRequest
from selenium import webdriver

logging.getLogger('scrapy').setLevel(logging.ERROR)
logging.getLogger('urllib3').setLevel(logging.ERROR)
logging.getLogger('selenium').setLevel(logging.ERROR)


class BlocketSpider(Spider):
    name = "blocket"

    def start_requests(self):
        url = 'https://www.blocket.se/annonser/hela_sverige/fordon/bilar?cg=1020'

        yield SeleniumRequest(url=url, callback=self.parse)

    def parse(self, response, **kwargs):
        driver = response.request.meta['driver']
        try:
            driver.find_element_by_xpath('//*[@id="accept-ufti"]').click()
        except:
            pass
        sleep(2)
        driver.execute_script("window.scrollTo(0, 1080);")
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        inner_div = soup.find('div', attrs={'class': 'MediumLayout__BodyWrapper-sc-q6qal1-2 gYhFaY'})
        models = inner_div.find_all('span', attrs={'class': 'styled__SubjectContainer-sc-1kpvi4z-12 dvfBcm'})
        tables = inner_div.find_all('ul', attrs={'class': 'ParametersList__List-sc-18ndpo4-1 icmkUf'})
        prices = inner_div.find_all('div', attrs={'class': 'Price__StyledPrice-sc-1v2maoc-1 hAKWLn'})
        urls = inner_div.find_all('a', attrs={'class': 'Link-sc-6wulv7-0 styled__StyledTitleLink-sc-1kpvi4z-11 cDtkQI buxcTF'},
                        href=True)

        for model, table, price, url in zip(models, tables, prices, urls):
            url = url['href']
            if 'https' not in url:
                url = 'https://www.blocket.se/'+ url
            data_table = [i.text.replace(u'\xa0', '') for i in list(table.children)]

            additional_info = self.parse_vehicle(driver, url)
            data = {'title': model.text, 'data': data_table,
                    'price': price.text, 'url': url}
            result ={**additional_info, **data}
            # print(result)
            yield result
        try:
            next_page = 'https://www.blocket.se/'\
                        + soup.find('a', attrs={'class': 'Pagination__Button-sc-uamu6s-1 Pagination__PrevNextButton-sc-uamu6s-7 jUbFsW iHgjRU', 'rel': 'next'}, href=True)['href']
            yield Request(url=next_page, callback=self.parse)
        except TypeError:
            print('TypeError: no more pages')

    def parse_vehicle(self, driver: webdriver.Chrome, url):
        result_dict = {}
        driver.get(url)
        sleep(2.5)
        element = driver.find_elements(By.CLASS_NAME, 'ExpandableContent__StyledShowMoreButton-sc-11a0rym-2 ciXgYN')
        if element:
            print('click')
            element[0].click()
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
        time = soup.find('span', attrs={'class': 'TextCallout2__TextCallout2Wrapper-sc-1bir8f0-0 cKftCy PublishedTime__StyledTime-sc-pjprkp-1 hCZACp'})
        if time:
            result_dict.update({'time': time.text.split(':')[-1]})
        car_id = driver.current_url.split('/')[-1]
        result_dict.update({'_id': car_id})
        return result_dict