import json
import requests
import re
from money_parser import price_str

def extract_total_from_invoice_text(invoice_text):
    # determine if text might qualify as invoice by looking for currency symbols
    print(invoice_text)
    if '€' in invoice_text:
        prices = []
        for line in invoice_text.splitlines():
            # determine if a number is present in the line
            if any(char.isdigit() for char in line):
                # check for currency symbols, eliminating dates or miscellaneous numbers
                if '€' in line:
                    # remove alphabetical characters
                    price_string = re.sub('[a-zA-z]', '', line)
                    # convert string to float price value
                    price = float(price_str(price_string))
                    print('detected price: ' + str(price))
                    prices.append(price)
        # if more than two amounts of currency have been detected in the documents text,
        # we will assume that the document can be classified as an invoice.
        # obviously this is a pretty rough mechanism and it may be prone to accept letters
        # or e-mails as invoices.
        print(prices)
        if len(prices) > 2:
            return max(prices)
    else:
        print("no currency sign detected, assuming the document is not an invoice")
        return 0

key = "Your_API_Key_Here"
object_id = "df00e281-cffc-45b7-87b1-8f99c69f3145"

header_dict = {}
base_url = 'https' + '://' + 'api.yuuvis.io' + '/dms-view'

header_dict['Ocp-Apim-Subscription-Key'] = key

response = requests.get(str(base_url+'/objects/'+object_id+'/contents/renditions/text'), headers=header_dict)
response_text = response.text
total = extract_total_from_invoice_text(response_text)
print(response_text, total)
