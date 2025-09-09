import asyncio
import time
import newspaper
from pydoll.browser import Chrome
from pydoll.constants import Key


async def google_search(queries: list):
    datas = []
    async with Chrome() as browser:
        tab = await browser.start()
        for query in queries:
            print(f"Query: {query}")
           
            await tab.go_to(
                query
            )
            current_url = None
            # find rss in query
            if "/rss/" in query:
                last_url = ""
                while True:
                    current_url = await tab.current_url
                    if current_url == last_url and current_url != "":
                        break
                    last_url = current_url
                    await asyncio.sleep(0.5)
                    print(f"Final URL: {current_url}")
            else:
                current_url = await tab.current_url
            
            # exctract with newspaper3k
            contents = await tab.request.get(current_url)
            article = newspaper.Article('')
            article.set_html(contents.text)
            article.parse()
            tab.recaptcha_solver = None
            print(f"Text: {article.text}")
            datas.append({
                "text": article.text,
                "title": article.title,
                'published_at': article.publish_date
            })
            
        await tab.close() 
        await browser.stop()
        return datas
           
queries = [
    #'https://news.google.com/rss/articles/CBMiygFBVV95cUxNUjdySENfRndqaTJvbXFLb016LWNnWXRoczhMVzN6UlZKODVZamdwRTFwU09keFRwYnl4RmNsZzA5NDJlWjctdVR0VVFLWmtESG1SSHNfRUJjN2daMUJSWllmWEJwbVkyWkc4SWpEX0Y4c3ZQVmM4OUlOM0ZhdXFxdXZvNXgwX0habHR4bU1Wb1RUNmNMaU9fajVMSnM3am5ZV1BlOTNBLU1IeVMzaXBucklSWnVJT0taamdfTjQ0am5JUG85YmpnQlJn?oc=5',
    "https://www.bloomberg.com/news/articles/2025-09-05/tiktok-rival-xiaohongshu-expects-profit-to-triple-to-3-billion?srnd=phx-technology",
]
asyncio.run(google_search(queries))

