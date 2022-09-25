try:
    import unzip_requirements #type ignore
except:
    pass
from typing import Union
import re
import tweepy
import urllib.parse
import os
from selenium import webdriver


def code(text: str, pattern: str = "(?<=```)(.*?)(?=```)") -> dict:
    """
    for a given text string it extracts the code part from the string. It returns a dictionary
    of the form text and code separately. The returned "text" is without code
    return value: dict
    return value format: {
        "text": the text without code,
        "code": {
            "code_text": code text,
            "language": r|python,
            "sno": 1|2|3...,
        }
    }
    """
    matches = re.findall(pattern, text, flags=re.S)

    j = 1
    code_list = []
    for i in range(0, len(matches), 2):
        text = text.replace(matches[i], "[see_image_" + str(j) + "]")

        language = re.search("^ *\w*?\n", matches[i], re.S).group(0).strip() # type: ignore
        code = re.sub(language, "", matches[i], 1).strip()

        code_list.append(
            {
                "code": f"# image: {j}\n{code}",
                "language": language.strip(),
                "sno": j
            }
        )
        j += 1

    text3 = text.replace("```", " ")
    text3 = re.sub(" +", " ", text3)

    return {
        "text": text3,
        "code_info": code_list
    }


def text_to_tweets(text: str, hashtags: list) -> list:
    """
    Given a text and hashtags list, it converts the text to be within the tweeter word limit and adds hashtag
    Returns:
        List: of tweets
    """
    if not isinstance(hashtags, list):
        raise TypeError("Hashtags are to be provided in a list")

    if not hashtags:
        raise ValueError("Hashtags not provided")

    hashtag_string = ""
    for hashtag in hashtags:
        hashtag_string = hashtag_string + "#" + \
            hashtag + " "  # 1 is for space b/w hashtags

    # replace newline characters with space and carriage returns with space
    text = text.replace("\n", " ").replace("\r", " ").strip()
    # replacing more than one space with single space character
    text = re.sub(" +", " ", text)

    text_list = text.split(" ")
    tweets = []

    threshold = 280 - len(hashtag_string) - 1

    tweets_wo_hastag = [""]
    for word in text_list:
        text = tweets_wo_hastag[-1]
        if len(" ".join([text, word])) <= threshold:
            tweets_wo_hastag[-1] = " ".join([text, word])
        else:
            tweets_wo_hastag.append(word)

    tweets = []
    for t in tweets_wo_hastag:
        t = t + " " + hashtag_string
        tweets.append(t)

    return tweets

class WebDriverWrapper:
    def __init__(self):
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1280x1696')
        chrome_options.add_argument('--hide-scrollbars')
        chrome_options.add_argument('--enable-logging')
        chrome_options.add_argument('--log-level=0')
        chrome_options.add_argument('--v=99')
        chrome_options.add_argument('--single-process')
        chrome_options.add_argument('--ignore-certificate-errors')
        chrome_options.add_argument(
            'user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36')

        chrome_options.binary_location = os.getcwd() + "/bin/headless-chromium"
        print(os.getcwd())

        self.driver = webdriver.Chrome(
            chrome_options=chrome_options,
            executable_path=os.getcwd() + '/bin/chromedriver'
        )


class CarbonUrl:
    def __init__(self, code: str, language: str):
        first_encoding = urllib.parse.quote(code, safe='*()')
        self.code = urllib.parse.quote(first_encoding, safe='*')
        self.language = language
        self.config = f't=seti&bg=rgba(171,184,195,1)&l={self.language}'
        self.url = f'https://carbon.now.sh/?{self.config}&code={self.code}'



class Twitter:

    def __init__(
        self,
        consumer_key: Union[str, None] = None,
        consumer_secret: Union[str, None] = None,
        access_token: Union[str, None] = None,
        access_token_secret: Union[str, None] = None
    ):
        self.consumer_key = consumer_key if consumer_key else os.environ['TWITTER_API_KEY']
        self.consumer_secret = consumer_secret if consumer_secret else os.environ['TWITTER_API_SECRET']
        self.access_token = access_token if access_token else os.environ['TWITTER_ACCESS_TOKEN']
        self.access_token_secret = access_token_secret if access_token_secret else os.environ['TWITTER_ACCESS_TOKEN_SECRET']

        self.client_v1 = tweepy.Client(
            consumer_key=self.consumer_key,
            consumer_secret=self.consumer_secret,
            access_token=self.access_token,
            access_token_secret=self.access_token_secret
        )

        auth = tweepy.OAuthHandler(consumer_key=self.consumer_key, consumer_secret=self.consumer_secret)
        auth.set_access_token(self.access_token, self.access_token_secret)
        self.client_v2 = tweepy.API(auth)


def sno_from_text(text: str) -> list:
    return [re.search("\d", t).group(0) for t in re.findall("\[see_image_\d\]", text, re.S)]