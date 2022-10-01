import os
from PIL import Image
from io import BytesIO
from saral_utils.extractor.dynamo import DynamoDB
from saral_utils.extractor.dynamo_queries import DynamoQueries
from saral_utils.utils.env import get_env_var, create_env_api_url

from utils import CarbonUrl, WebDriverWrapper, Twitter, text_to_tweets, sno_from_text
from utils import code as coder
from question import Question

def hello(event, context):

    trigger = event.get('language', None) # trigger: whether to post R question or python question
    if trigger is None:
        trigger = 'R'

    start_date = event.get('start_date', None)
    if start_date is None:
        start_date = '2022-09-22'

    twitter = Twitter().client_v1
    twitter_v2 = Twitter().client_v2

    env = get_env_var('MY_ENV')
    region = get_env_var("MY_REGION")

    db = DynamoDB(table=f'saral-questions-{env}', region=region, env=env)
    queries = DynamoQueries()

    # get question
    que = Question(que_db=db, queries=queries, language=trigger, start_date=start_date)
    unique_question = que.get_unique_que()

    # convert question text to tweet text
    que_text = unique_question['question']
    options = unique_question['options']

    text = coder(text=que_text)
    text_wo_code = text['text']
    code_info = text['code_info']

    # get image for code and upload to twitter
    code_media_ids = []
    if code_info:
        for info in code_info:
            driver = WebDriverWrapper().browser
            print(f'web driver created')
            code = info['code']
            language = info['language']
            sno = info['sno']

            # convert code to images and download to temp
            # hit the carbon site to download the image
            ur = CarbonUrl(code, language).url
            print(f'fetching data from url: {ur}')
            driver.get(ur)
            print(f'url fetched')
            print(f'creating image')
            element = driver.find_element_by_id("export-container")
            location = element.location 
            size = element.size 
            full_screenshot = driver.get_screenshot_as_png()
            driver.close()

            im = Image.open(BytesIO(full_screenshot))
            left = location['x']
            top = location['y']
            right = location['x'] + size['width']
            bottom = location['y'] + size['height']

            im = im.crop((left, top, right, bottom))
            path = '/tmp/' + str(sno) + '.png'
            im.save(path)
            print(f'image saved at path: {path}')

            media_id = twitter_v2.media_upload(path).media_id_string
            twitter_v2.create_media_metadata(media_id, 'Image ' + str(sno))

            code_media_ids.append(
                {
                    'type': 'code', 
                    'media_id': media_id, 
                    'path': path, 
                    'file_name': os.path.basename(path),
                    'sno': str(sno)
                }
            )
    
    if trigger.lower().strip() == 'r':
        tweets_to_post = text_to_tweets(text=text_wo_code, hashtags=['RStats', 'DataScience'] )
    elif trigger.lower().strip() == 'python':
        tweets_to_post = text_to_tweets(text=text_wo_code, hashtags=['Python', 'Programming'] )

    code_media_count = len(code_media_ids)
    que_id = unique_question['question_id']
    print(f'question selected: {que_id}')

    if code_media_count > 0:
        if len(tweets_to_post) == 1 and code_media_count <= 4:
            tweet = twitter.create_tweet(
                text=tweets_to_post[0],
                media_ids = [c['media_id'] for c in code_media_ids]
            )
            print(f'tweet posted with id {tweet.data["id"]}')
            tweeted_id = tweet.data['id']
        elif len(tweets_to_post) > 1 and code_media_count <= 4:
            reply_id = None
            for t in tweets_to_post:
                sno = sno_from_text(t)
                code_m_ids = [x['media_id'] for x in code_media_ids if x['sno'] in sno]

                if reply_id is None:
                    tweet = twitter.create_tweet(
                        text=t, 
                        media_ids = code_m_ids,
                    )
                    reply_id = tweet.data['id']
                else:
                    tweet = twitter.create_tweet(
                        text=t, 
                        media_ids = code_m_ids,
                        in_reply_to_tweet_id=reply_id
                    )
                    reply_id = tweet.data['id']
                print(f'tweet posted with id {tweet.data["id"]}')

            tweeted_id = tweet.data['id']
        
        elif len(tweets_to_post) == 1 and code_media_count > 4:
            tweet = twitter.create_tweet(
                text=tweets_to_post[0],
                media_ids = code_media_ids[0:4]
            )
            reply_id = tweet.data['id'] 

            for i in range(4, len(code_media_ids) ,4):
                tweet = twitter.create_tweet(
                    media_ids = code_media_ids[i:i+4],
                    in_reply_to_tweet_id=reply_id
                )
                reply_id = tweet.data['id']

            tweeted_id = tweet.data['id']

        elif len(tweets_to_post) > 1 and code_media_count > 4:
            reply_id = None
            for t in tweets_to_post:
                sno = sno_from_text(t)
                code_m_ids = [x['media_id'] for x in code_media_ids if x['sno'] in sno]

                if reply_id is None:
                    tweet = twitter.create_tweet(
                        text=t, 
                        media_ids = code_m_ids, 
                    )
                    reply_id = tweet.data['id']
                else:
                    tweet = twitter.create_tweet(
                        text=t, 
                        media_ids = code_m_ids, 
                        in_reply_to_tweet_id=reply_id
                    )
                    reply_id = tweet.data['id']
            tweeted_id = tweet.data['id']
    else:
        reply_id = None
        for t in tweets_to_post:
            if reply_id is None:
                tweet = twitter.create_tweet(
                    text=t
                )
                reply_id = tweet.data['id']
            else:
                tweet = twitter.create_tweet(
                    text=t,
                    in_reply_to_tweet_id=reply_id
                )
                reply_id = tweet.data['id']
        
        tweeted_id = tweet.data['id']
    
    # tweet options to last tweeted post
    options_text = []
    for i, option in enumerate(options):
        option_text = str(i+1) + ". " + option['text'] + "\n"
        options_text.append(option_text)

    answer_link = create_env_api_url(url=f'answer.saral.club/qna/{que_id}')
    subscribe_link = create_env_api_url(url=f'saral.club')
    option_tweets_to_post = [f"Options:\n(Answer at: {answer_link}\n\nSubscribe at {subscribe_link} to get a daily question on #RStats in your inbox."]
    for opt in options_text:
        text = option_tweets_to_post[-1]
        if len("".join([text, opt])) <= 280:
            option_tweets_to_post[-1] = "".join([text, opt])
        else:
            option_tweets_to_post.append("".join([opt]))
    
    reply_id = tweeted_id
    polls = [str(i) for i in range(1, len(options)+1)]
    for opt_tweet in option_tweets_to_post:
        tweet = twitter.create_tweet(
            text=opt_tweet,
            in_reply_to_tweet_id=reply_id,
            poll_options=polls,
            poll_duration_minutes=1440
        )
        reply_id = tweet.data['id']


    print(f'all tweets tweeted. question id: {que_id}. Last tweet id: {reply_id}')
