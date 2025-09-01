from bs4 import BeautifulSoup
import re
import urllib3
import requests

url = "https://news.google.com/rss/articles/CBMirAFBVV95cUxQTFh0eHY4Q2tQSE9BRUd2MmdmZHFHdm40OTJ6MnpoUFlPV3pOV3pPRlJRWEt1MU0zY25fVVhQaWRzNllWS0tUa1hWWEZMTzJoclk5Z2FWNUNXbWUweUM2eWdXR0dTbGJTTGpFRnI3MmFSbGVTVmhzOWloMkx3V2dqY2tWZ2I1RG1Sdi1RdlU0SVNLdk1uQktTS2h6a3liUUo1bGRwOUsyajB4UFpt?oc=5"
def handle_redirects(initial_url):
    # Create a PoolManager instance
    http = urllib3.PoolManager()

    # Define the initial URL that may redirect


    try:
        # Make a GET request with allow_redirects set to True
        response = http.request('GET', initial_url, redirect=True)

        # Check if the request was successful (status code 200)
        if response.status == 200:
            # Print the final response URL after following redirects
            print("Final Response URL:")
            print(response.geturl())
        else:
            # Print an error message if the request was not successful
            print(f"Error: Unable to fetch data. Status Code: {response.status}")

    except urllib3.exceptions.RequestError as e:
        print(f"Error: {e}")

handle_redirects(url)