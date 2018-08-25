from lxml import html
import requests
from enum import Enum

# encoding=utf8
import sys, os, re

#sys.setdefaultencoding('utf8')

# Global Variables
# Settings
VIEWRECENT = False
ONLYDIRECT = False

# Other
OFFERS_LIST = []
PRICE_IND = {}
CURFILE = 0
CURITEM = ""

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
    def __init__(self, has, wants, link, note, lastAct):
        self.has = has
        self.wants = wants
        self.link = link
        self.note = note
        self.lastAct = lastAct

    def __repr__(self):
        out = "{} - {} vs. {} - {}".format(self.link, self.has, self.wants, self.lastAct)
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
    items = price_tree.xpath('//*[@class="rocket-league-item "]')
    for i in items:
        name = i.xpath('.//*[@class="itemName"]/text()')[0]
        #element = price_tree.xpath('/html/body/div[2]/div[2]/div[2]/div[2]/div[%s]/div[2]/div/text()' % i)
        priceRange = i.xpath('./div[2]/div[2]/text()')
        # If there is no price then the length of priceRange is < 3
        if priceRange != [] and len(priceRange[0])>2:
            # Calculate the average price out of the given price range
            range_arr = priceRange[0].split()
            av_price = ( float(range_arr[0]) + float(range_arr[2]) ) / 2.0 
            av_price = roundTo2Dig(av_price)
        else:
            av_price = 0.0
        prices[name] = av_price
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

def getOffers(url, price):
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

            # Get Offer note
            note_list = o.xpath('.//*[@class="rlg-trade-note-area-filter"]/../p/text()')
            if note_list != []:
                note = note_list[0]
            else:
                note = ""
            
            # Get LastActive
            lastAct_list = o.xpath('.//*[@class="rlg-trade-display-added"]/text()')
            lastAct = lastAct_list[0]
            lastAct = lastAct.split("ago")[0]
            lastAct = lastAct[7:]

            # Get items on 'Has'- and 'Wants'-side of the offer o  
            itemsHas = getItems(o, Side.HAS, price)
            itemsWants = getItems(o, Side.WANTS, price)

            # If the offer is a possible 1:1 create cor. 1:1-offers
            if len(itemsHas) == len(itemsWants):
                oneToOne = zip(itemsHas, itemsWants)
                for i in oneToOne:
                    if i[1].name == CURITEM:
                        off = Offer(i[0], i[1], link_str, note, lastAct)
                        offList.append(off)
    return offList


# sort dict by amount of item (used in the query) in ascending order
def sortOffers(offers, price, VIEWRECENT, ONLYDIRECT):
    sorted_offs = {}
    # Separate one list into dict with the different amounts as keys and offer-lists as values
    for o in offers:
        if VIEWRECENT:
            if not ("minute" in o.lastAct or "second" in o.lastAct):
                continue
        
        if ONLYDIRECT:
            if re.match(r"(\d+)[:\-;](\d+)", o.note) == None:
                continue

        if o.wants.amount not in sorted_offs:
            sorted_offs[o.wants.amount] = [o]
        else:
            sorted_offs[o.wants.amount].append(o)

    # Now sort each offer-list in dict by price (high-to-low)
    for off in sorted_offs:
        sorted_offs[off] = sorted(sorted_offs[off], key= lambda x: x.has.price, reverse=True)

    return sorted_offs

# Pretty print for the dict that is used for the output of the offers
def prettyPrint(d):
    global CURFILE
    f = open("{}{}.txt".format(CURITEM, str(CURFILE)),"w+")
    f.write("Settings for this file: \nOnlyDirectOffers: {}\nViewRecentOffers: {}\n\n\n".format(str(ONLYDIRECT), str(VIEWRECENT)))
    for key in d.keys():
        f.write("\n-------------------- {} {} --------------------\n".format(str(key), CURITEM))
        print("\n-------------------- {} {} --------------------".format(str(key), CURITEM))
        for entry in d[key]:
            f.write(str(entry) + "\n")
            print(entry)        
    f.close()
    CURFILE += 1

# ------------------------------------------------------------------------------
# MENU
# ------------------------------------------------------------------------------

# Main menu
def mainMenu():
    print ("Welcome to Main Menu,\n")
    print ("Please choose the what you want to do:")
    print ("1. Find Offers")
    print ("2. Print Offers")
    print ("3. Toggle ViewDirectOffers")
    print ("4. Toggle ViewRecentOffers")
    print ("\n0. Quit")
    choice = input(" >>  ")
    execMenu(choice)
    return

# Execute main menu
def execMenu(choice):
    os.system("clear")    
    ch = choice.lower()
    if ch == '':
        menuActions['mainMenu']()
    else:
        try:
            menuActions[ch]()
        except KeyError:
            print ("Invalid selection, please try again.\n")
            menuActions['mainMenu']()
    return

# MAIN MENU FUNCTIONS
# Function that finds offers for a corresponding item
def findOffers():
    global CURITEM
    global OFFERS_LIST 
    # Get Item Index
    while True:
        it_index = getIndex()
        if it_index != {}:
            break
    
    # Iterate until valid item was entered
    while(True):
        item_str = input("Which item would you like to offer? ")
        try:
            item_ind = it_index[item_str]
            CURITEM = item_str
            break
        except KeyError:
            print("There is no such item - please try again")
    
    base_url = "https://rocket-league.com/trading?filterItem=" + item_ind +"&filterCertification=0&filterPaint=0&filterPlatform=2&filterSearchType=2&p="

    OFFERS_LIST = getOffers(base_url, PRICE_IND)
    printOffs()

# Print list of offers to console
def printOffs():
    s = sortOffers(OFFERS_LIST, PRICE_IND, VIEWRECENT, ONLYDIRECT)
    prettyPrint(s)

    print('\n\n')
    mainMenu()

# Toggle DirectOffers setting
def changeDirOffer():
    global ONLYDIRECT
    if ONLYDIRECT == False:
        ONLYDIRECT = True
        print("OnlyDirectOffers was set to TRUE\n")
    else:
        ONLYDIRECT = False
        print("OnlyDirectOffers was set to FALSE\n")
    
    mainMenu()

# Toggle the ViewRecent setting
def changeViewRecent():
    global VIEWRECENT
    if VIEWRECENT == False:
        VIEWRECENT = True
        print("ViewRecent was set to TRUE\n")
    else:
        VIEWRECENT = False
        print("ViewRecent was set to FALSE\n")

    mainMenu()

def exit():
    sys.exit()

# Menu definitions
menuActions = {
    "mainMenu": mainMenu,
    '1': findOffers,
    '2': printOffs,
    '3': changeDirOffer,
    '4': changeViewRecent,
    '0': exit
}
# ------------------------------------------------------------------------------
# MAIN
# ------------------------------------------------------------------------------

if __name__ == '__main__':
    os.system("clear")
    # Get Item-Prices from Website
    while True:
        PRICE_IND = getPrices()
        if PRICE_IND != {}:
            break
    
    mainMenu()