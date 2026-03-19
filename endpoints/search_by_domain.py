import sys
sys.path.append('..')
from endpoints.search_by_url import *


def search_by_domain(params, debug=True):
    domain = params.get('domain') or params.get('url')
    if not domain:
        return {
            'statusCode': 400,
            'body': json.dumps({'message': 'Missing domain parameter'})
        }
    if not domain.startswith('http'):
        params['url'] = f'https://{domain}'
    else:
        params['url'] = domain
    response = search_by_url(params, debug)
    return response