from saral_utils.extractor.dynamo import DynamoDB
from saral_utils.extractor.dynamo_queries import DynamoQueries
import saral_utils.utils.qna as qna
from typing import Tuple, Dict, Union
import warnings
from datetime import datetime


class Question:

    def __init__(self, que_db: DynamoDB, queries: DynamoQueries, language: str, start_date: Union[str, None] = None):

        self.que_db = que_db
        self.queries = queries
        self.language = language.lower()
        self.start_date = start_date if start_date else '2022-09-22'

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

        sorted_list = sorted(ques, key= lambda x: datetime.strptime(x['created_at'], '%Y-%m-%dT%H:%M:%S.%f'), reverse=True)
        time_stamp = datetime.strptime(self.start_date, '%Y-%m-%d')
        ndays = (datetime.now() - time_stamp).days 
        remainder = ndays % len(ques)
        question = sorted_list[remainder]

        return question