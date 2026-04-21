import requests
import pandas as pd

print('running..')
url = 'https://www.tractorsupply.com/gtwy/SiteSearch/catalogSearch?searchType=category&minAttr=true&storeNumber=2304&pageNumber=1&pageSize=50&q=24585&categoryId=24585&sort=2'

headers = { "Channel" : "web",
    "sessionid": "1",
    "uniqueid": "48af6da2-be56-43e4-a7d9-74def7747787",
    "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
    "x-api-version": "v2",
    "zoneid": "63"
}

response = requests.get(url, headers = headers)

print(response.status_code)
