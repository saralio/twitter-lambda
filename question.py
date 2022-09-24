# handles fetching question from dynamdb and maintains unique question are posted
from saral_utils.extractor.dynamo import DynamoDB
from saral_utils.extractor.dynamo_queries import DynamoQueries
import saral_utils.utils.qna as qna
from typing import Tuple, Dict 
import pandas as pd
import warnings
from datetime import datetime


class Question:

    def __init__(self, que_db: DynamoDB, queries: DynamoQueries, language: str):

        self.que_db = que_db
        self.queries = queries
        self.language = language.lower()

    def get_queries(self) -> Tuple: 
        if self.language in ['r']:
            attr = self.queries.r_prog_que_attr_values
            key_cond = self.queries.r_prog_que_key_cond_expr
            filter = self.queries.r_prog_que_filter_expr

        elif self.language == 'python':
            attr = self.queries.py_prog_que_attr_values
            key_cond = self.queries.py_prog_que_key_cond_expr
            filter = self.queries.py_prog_que_filter_expr
        
        elif self.language in ['data science', 'machine learning', 'ds', 'ml']:
            attr = self.queries.ds_que_attr_values
            key_cond = self.queries.ds_que_key_cond_expr
            filter = self.queries.ds_que_filter_expr

        else:
            attr, key_cond, filter = None, None, None
            warnings.warn(f'{self.language} provided did not match any tags available in db')
        
        return attr, key_cond, filter

    def fetch_questions(self) -> Dict:
        attr, key_cond, filter = self.get_queries()
        if any([x is None for x in [attr, key_cond]]):
            raise RuntimeError('One of attr, key_cond is None, cannot fetch data from dynamodb')
        if filter is not None:
            questions = self.que_db.query(KeyConditionExpression=key_cond, ExpressionAttributeValues=attr, FilterExpression=filter)
        else:
            questions = self.que_db.query(KeyConditionExpression=key_cond, ExpressionAttributeValues=attr)

        return questions

    @staticmethod 
    def parse_que_frm_db(question: Dict) -> Dict:

        if qna.links_exist(question):
            links = qna.normalize_links(question['links']['L'])
        else:
            links = None
        
        id = question['id']['S']
        question_text = question['questionText']["S"]
        options = qna.normalize_options(question['options']['L'])
        created_at = question['createdAt']['S']
        image_exist = qna.image_exist(question)

        return {
            'question_id': id,
            'question': question_text,
            'options': options,
            'links': links,
            'image_exist': image_exist,
            'created_at': created_at
        }


    def get_unique_que(self) -> Dict:

        ques = self.fetch_questions()
        ques = [self.parse_que_frm_db(que) for que in ques]
        ques = [q for q in ques if not q['image_exist']]

        ques_db = pd.DataFrame(ques)
        ques_db['created_at'] = pd.to_datetime(ques_db['created_at'])
        time_stamp = datetime.strptime('2022-09-22', '%Y-%m-%d')
        ndays = (datetime.now() - time_stamp).days 
        remainder = len(ques) % ndays 

        ques_db.sort_values(by='created_at', ascending=True, inplace=True)
        question = ques_db.iloc[remainder, :]

        return question.to_dict()

