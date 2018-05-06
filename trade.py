from lxml import html
import requests

# Round floating point number to 2 digits
def roundTo2Dig(num):
    num = float(str(num)[:4])   
    return num 

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


trade_url = "https://rocket-league.com/trading?filterItem=1159&filterCertification=0&filterPaint=0&filterPlatform=2&filterSearchType=2"
# Get Items you can get for triumph crate
trade_html = requests.get(trade_url)
trade_tree = html.fromstring(trade_html.content)

items = trade_tree.xpath('//*[@id="rlg-youritems"]//img/@alt')

n = 1
link = trade_tree.xpath('/html/body/main/div/div/div/div[7]/div[%d]/div[1]/a/@href' % n)
link_str = "https://rocket-league.com/" + link[0]

item_prices = {}
for item in items:
    # Check if the item's price is in the price dictionary
    if item in prices:
        item_prices[item] = prices[item]

it = max(item_prices, key=item_prices.get)
print it
print item_prices[it]

print link_str