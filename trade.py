from lxml import html
import requests

# Round floating point number to 2 digits
def roundTo2Dig(num):
    num = float(str(num)[:4])   
    return num 

def getPrices():
    # Get current prices and create prices dictionary
    prices = {}
    price_html = requests.get('https://www.rltprices.com/ps4')
    price_tree = html.fromstring(price_html.content)
    for i in range(1,493):
        element = price_tree.xpath('/html/body/div[2]/div[2]/div[2]/div[2]/div[%s]/div[2]/div/text()' % i)
        
        # element[1] is the string that contains the price range
        # If there is no price then the length of element[1] is <3
        if element[1] != [] and len(element[1])>2:
            # Calculate the average price out of the given price range
            range_str = element[1].split()
            av_price = ( float(range_str[0]) + float(range_str[2]) ) / 2.0 
            av_price = roundTo2Dig(av_price)
        else:
            av_price = 0
        prices[element[0]] = av_price
    return prices

def getOffers():
    base_url = "https://rocket-league.com/trading?filterItem=1159&filterCertification=0&filterPaint=0&filterPlatform=2&filterSearchType=2&p="
    offs = {}
    # Just one page right now
    max_page = 1

    for i in range (0,max_page):
        trade_url = base_url + str(i)
        # Get Items you can get for triumph crate
        trade_html = requests.get(trade_url)
        trade_tree = html.fromstring(trade_html.content)

        items = trade_tree.xpath('//*[@id="rlg-youritems"]//img/@alt')

        n = 1
        offers = trade_tree.xpath('//*[@class="rlg-trade-display-container is--user"]')
        for o in offers:
            # get offer link
            link = o.xpath('./div[@class="rlg-trade-display-header"]/a/@href')
            link_str = "https://rocket-league.com/" + link[0]
            # get offer items 
            # items_path = o.xpath('.//*[@id="rlg-youritems"]')
            item_paths = o.xpath('.//*[@id="rlg-youritems"]//*[@class="rlg-trade-display-item rlg-trade-display-item-read"]')
            items=[]
            for i in item_paths:
                name = i.xpath('.//img/@alt')
                num_strs = i.xpath('.//*[@class="rlg-trade-display-item__amount is--premium"]/text()')
                if (num_strs == []): # if the amount is not given it's 1 item
                    num = 1
                else: 
                    num = int(num_strs[0]) # index 0 because num_strs a list of one string
                # print link_str
                item = (name, num)
                items.append(item)
            
            offs[link_str] = items
        return offs