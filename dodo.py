import os
from functools import partial
ID_LIST_FILENAME = os.environ.get('ID_LIST_FILENAME', 'cfss/filenames.txt')
SEG_DIR = os.environ.get('SEG_DIR', 'data/manual_segmentation')

with open(ID_LIST_FILENAME) as f:
    id_list = [l.rstrip() for l in f.readlines()]

def task_ids():
    '''
    Print IDs
    '''
    def do():
        print('\n'.join(id_list))
    return {'actions': [do], 'verbosity': 2}

def task_vars():
    '''
    Print variables
    '''
    def do():
        print('\n'.join(id_list))
    return {'actions': [do], 'verbosity': 2}

def task_levelset():
    '''
    Perform levelset segmentation
    '''

    def do(data_id):
        print(data_id)

    for data_id in id_list:
        yield {'name': f'levelset {data_id}',
               'actions': [partial(do, data_id)],
               'verbosity': 2}