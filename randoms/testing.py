from newspaper import Article
url = "https://seekingalpha.com/article/4817541-11-ways-to-profit-from-nvidia-regardless-of-what-happens-from-here"
article = Article(url)
article.download()
article.parse()
print(article.text)