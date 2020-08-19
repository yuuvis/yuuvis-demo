import json
import requests
import re
from money_parser import price_str

# empirically determined currency signs that serve to detect invoices
currency_signs = ['€', 'EUR']


def extract_total_from_invoice_text(invoice_text):
    # determine if text might qualify as invoice by looking for currency symbols
    if any(cs in invoice_text for cs in currency_signs):
        prices = []
        for line in invoice_text.splitlines():
            # determine if a number is present in the line
            if any(char.isdigit() for char in line):
                # check for currency symbols, eliminating dates or miscellaneous numbers
                if any(cs in line for cs in currency_signs):
                    # remove alphabetical characters
                    price_string = re.sub('[a-zA-z]', '', line)
                    # convert string to float price value
                    price = float(price_str(price_string))
                    prices.append(price)
        # if more than two amounts of currency have been detected in the documents text,
        # we will assume that the document can be classified as an invoice.
        # obviously this is a pretty rough mechanism and it may be prone to accept letters
        # or e-mails as invoices.
        if len(prices) > 2:
            total = max(prices)
            print(f'determined invoice with total: {total}')
            return total
    else:
        print("no currency sign detected, assuming the document is not an invoice")
        return 0
