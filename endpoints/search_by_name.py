from endpoints.search_by_url import *


def get_url_using_name(name):
    pass


def search_by_name(params):
    name = params.get('name')
    if not name:
        return {
            'statusCode': 400,
            'body': json.dumps({'message': 'Missing name parameter'})
        }

    params['url'] = get_url_using_name(name)
    response = search_by_url(params)
    return response
