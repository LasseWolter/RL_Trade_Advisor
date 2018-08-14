from lxml import html
import requests
from enum import Enum

# encoding=utf8
import sys
#sys.setdefaultencoding('utf8')

# Enumeration for the side of the offer - placeholder for id
class Side(Enum):
    HAS = "rlg-youritems"
    WANTS = "rlg-theiritems"

class Item:
    def __init__(self, name, amount=1, colour=""):
        self.name = name
        self.amount = amount
        self.colour = colour
        self.price = 0.0

    def getPrice(self, price):
        if self.name in price:
            self.price = roundTo2Dig(price[self.name] * self.amount)
        # Have to find better solution - just a quick fix
        elif self.name == "Key":    
            self.price = 1.0 * self.amount
        return self.price

    def __repr__(self):
        out = "{} {} {} ({})".format(self.amount, self.colour, self.name, self.price)
        return out


# Class representing a one-to-one offer
class Offer:
    def __init__(self, has, wants, link):
        self.has = has
        self.wants = wants
        self.link = link

    def __repr__(self):
        out = "{} - {} vs. {}".format(self.link, self.has, self.wants)
        return out

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
            av_price = 0.0
        prices[element[0]] = av_price
    return prices

def getIndex():
    # Dictionary that maps items to the corresponding index
    index = {}
    url = "https://rocket-league.com/trading"

    # Make the request and create corresponding e_tree
    ind_html = requests.get(url)
    tree = html.fromstring(ind_html.content)

    # Find the list of items and their indices and iterate over them
    items = tree.xpath('//*[@class="rlg-select" and @id="filterItem"]/*/*')
    for item in items:
        index[item.text] = item.get('value')
    return index

def getMaxPage(tree):
    # Contains since it can also be "rlg-trade-pagination-button rlg-trade-pagination-button-end" if there are lots of pages
    num = tree.xpath('//*[contains(@class,"rlg-trade-pagination-button")]/text()')
    num.append('0')     # to make sure that there is at least one number in case no results are found
    return int(max(num, key=lambda num:int(num)))

# Get items from particular side for particular offer
def getItems(offer, side, price):
    items=[]
    item_paths = offer.xpath('.//*[@id="' + side.value + '"]//*[@class="rlg-trade-display-item rlg-trade-display-item-read"]')

    for i in item_paths:
        name = i.xpath('.//img/@alt')
        if not name == []:
            name = name[0]
        else:
            name = ''
        # contains has to be used since the class contains the rarity of the item ("rare, "premium",etc)
        num_str = i.xpath('.//*[contains(@class,"rlg-trade-display-item__amount")]/text()')     
        if num_str == []: # if the amount is not given it's 1 item
            num = 1
        else: 
            num = int(num_str[0]) # index 0 because num_str is a list of one string

        colour = i.xpath('.//*[@class="rlg-trade-display-item-paint"]/@data-name')
        # Keys cannot have colours
        if colour == [] or name == "Key":
            colour = ""
        else:
            colour = colour[0]

        item = Item(name, num, colour)
        item.getPrice(price)
        items.append(item)
    return items

def getOffers(url, item, price):
    offList = []

    # Start on the first page to check how many pages there are
    trade_html = requests.get(url + str(1))
    trade_tree = html.fromstring(trade_html.content)
    max_page = getMaxPage(trade_tree)

    # Iterate over all pages
    for i in range (0,max_page):
        print("Processing Page " + str(i) + " of " + str(max_page) + "...")
        trade_url = url + str(i)
        trade_html = requests.get(trade_url)
        trade_tree = html.fromstring(trade_html.content)

        # Find offers in tree structure and iterate over them       
        offers = trade_tree.xpath('//*[@class="rlg-trade-display-container is--user"]')
        for o in offers:
            # Get offer link
            link = o.xpath('./div[@class="rlg-trade-display-header"]/a/@href')
            link_str = "https://rocket-league.com/" + link[0]

            # Get items on 'Has'- and 'Wants'-side of the offer o  
            itemsHas = getItems(o, Side.HAS, price)
            itemsWants = getItems(o, Side.WANTS, price)

            # If the offer is a possible 1:1 create cor. 1:1-offers
            if len(itemsHas) == len(itemsWants):
                oneToOne = zip(itemsHas, itemsWants)
                for i in oneToOne:
                    if i[1].name == item: 
                        off = Offer(i[0], i[1], link_str)
                        offList.append(off)
    return offList

# sort dict by amount of item (used in the query) in ascending order
def sortOffers(offers, price):
    sorted_offs = {}
    # Separate one list into dict with the different amounts as keys and offer-lists as values
    for o in offers:
        if o.wants.amount not in sorted_offs:
            sorted_offs[o.wants.amount] = [o]
        else:
            sorted_offs[o.wants.amount].append(o)

    # Now sort each offer-list in dict by price (high-to-low)
    for off in sorted_offs:
        sorted_offs[off] = sorted(sorted_offs[off], key= lambda x: x.has.price, reverse=True)

    return sorted_offs

# Pretty print for the dict that is used for the output of the offers
def prettyPrint(d, item):
    for key in d.keys():
        print("-------------------- {} {} --------------------".format(str(key), item))
        for entry in d[key]:
            print(entry)        

        

# ------------------------------------------------------------------------------
# MAIN
if __name__ == '__main__':
    while True:
        price = getPrices()
        if price != {}:
            break
    
    while True:
        index = getIndex()
        if index != {}:
            break
    
    # Iterate until valid item was entered
    while(True):
        item_str = input("Which item would you like to offer? ")
        try:
            item_ind = index[item_str]
            break
        except KeyError as err:
            print("There is no such item - please try again")
    
    base_url = "https://rocket-league.com/trading?filterItem=" + item_ind +"&filterCertification=0&filterPaint=0&filterPlatform=2&filterSearchType=2&p="
    o = getOffers(base_url, item_str, price)
    s = sortOffers(o, price)
    prettyPrint(s, item_str)
