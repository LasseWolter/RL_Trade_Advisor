from lxml import html
import requests
from enum import Enum

# Enumeration for the side of the offer
class Side(Enum):
    HAS = 1
    WANTS = 2


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

# Get items from particular side for particular offer
def getItems(offer, side):
    items=[]

    if side == Side.HAS:
        item_paths = offer.xpath('.//*[@id="rlg-youritems"]//*[@class="rlg-trade-display-item rlg-trade-display-item-read"]')
    elif side == Side.WANTS:
        item_paths = offer.xpath('.//*[@id="rlg-theiritems"]//*[@class="rlg-trade-display-item rlg-trade-display-item-read"]')    
    else:
        raise ValueError("Invalid offer side")

    for i in item_paths:
        name = i.xpath('.//img/@alt')
        if not name == []:
            name = name[0]
        else:
            name = ''
        num_str = i.xpath('.//*[contains(@class,"rlg-trade-display-item__amount")]/text()')     # contains has to be used since the class contains the rarity of the item ("rare, "premium",etc)
        if (num_str == []): # if the amount is not given it's 1 item
            num = 1
        else: 
            num = int(num_str[0]) # index 0 because num_str is a list of one string

        item = (name, num)
        items.append(item)
    return items

def getOffers():
    base_url = "https://rocket-league.com/trading?filterItem=1159&filterCertification=0&filterPaint=0&filterPlatform=2&filterSearchType=2&p="
    offs = {}
    # Just one page right now
    max_page = 9

    # iterate over all pages
    for i in range (0,max_page):
        trade_url = base_url + str(i)
        # Get Items you can get for triumph crate
        trade_html = requests.get(trade_url)
        trade_tree = html.fromstring(trade_html.content)

        offers = trade_tree.xpath('//*[@class="rlg-trade-display-container is--user"]')
        for o in offers:
            # Get offer link
            link = o.xpath('./div[@class="rlg-trade-display-header"]/a/@href')
            link_str = "https://rocket-league.com/" + link[0]

            # Get items on 'Has'-side in offer o  
            itemsHas = getItems(o, Side.HAS)
            itemsWants = getItems(o, Side.WANTS)
            oneToOne = []
            relOffers = []
            if len(itemsHas) == len(itemsWants):
                oneToOne = zip(itemsHas, itemsWants)
                for off in oneToOne:
                    if off[1][0] == "Triumph Crate":
                        relOffers.append(off)
            if not relOffers == []:
                offs[link_str] = relOffers
    return offs

def printDict(d):
    for link in d:
        print link, d[link] 