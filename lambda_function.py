import json
import time
from endpoints.search_by_url import search_by_url
from endpoints.search_by_domain import search_by_domain
from endpoints.search_by_name import search_by_name

def response_credits(response, total_credits=1):
    if response.get('statusCode') != 200: total_credits = 0
    response['headers'] = {
        'Content-Type': 'application/json',
        'X-RapidAPI-Billing': f"Credits={total_credits}"
    }
    return response


def lambda_handler(event, context):
    try:
        params = event.get('queryStringParameters') or {}

        # Get the input parameters
        url = params.get('url')
        domain = params.get('domain')
        local_run = params.get('local_run')
        if local_run:
            return response_credits({
                'statusCode': 200,
                'body': json.dumps('Okay!')
            }, 0)

        # Determine validity:
        # A valid URL starts with 'http', whereas a domain should not.
        url_valid = url and url.startswith('http')
        domain_valid = domain and not domain.startswith('http')

        # Correct swapped parameters:
        if url and not url_valid:
            # If 'url' is provided but does NOT start with http,
            # then we assume the user meant to pass a domain.
            params['domain'] = url
            params.pop('url', None)
            url_valid = False
            domain_valid = True
        elif domain and domain.startswith('http'):
            # If 'domain' is provided but starts with http,
            # then we assume the user meant to pass a URL.
            params['url'] = domain
            params.pop('domain', None)
            url_valid = True
            domain_valid = False

        # Now, choose the endpoint based on what’s valid.
        # Priority is given to a valid URL.
        if url_valid:
            path = 'search-by-url'
        elif domain_valid:
            path = 'search-by-domain'
        else:
            # If neither parameter is clearly valid, keep the original path.
            path = event['rawPath'].strip('/').split('/')[0]

        # Call the corresponding endpoint.
        if path == 'search-by-url':
            response = search_by_url(params)
            return response_credits(response)

        elif path == 'search-by-domain':
            response = search_by_domain(params)
            return response_credits(response)

        elif path == 'search-by-name':
            # This endpoint is under development.
            return response_credits({
                'statusCode': 200,
                'body': json.dumps(f'under development Please Try again Latter!, and send me a message to notify me'),
            }, 0)
            response = search_by_name(params)
            return response_credits(response)
        else:
            return response_credits({
                'statusCode': 200,
                'body': json.dumps('Welcome to Contact API!')
            }, 0)


    except TimeoutError:
        return {
            'statusCode': 408,  # Request Timeout
            'body': json.dumps({'message': 'The operation timed out before 30 seconds'}),
            'headers': {
                'Content-Type': 'application/json',
                'X-RapidAPI-Billing': "Credits=0"
            }
        }
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps(f'An error occurred, Please Try again Latter!'),
            'headers': {
                'Content-Type': 'application/json',
                'X-RapidAPI-Billing': "Credits=0"
            }
        }


if __name__ == "__main__":
    urls = [
        # 'https://aautobodyshop.com',
        # 'http://aautobodyshop.com',
        # 'aautobodyshop.com',
        # 'https://onestopcarrepair.com',
        # 'https://101collisioncenter.com',
        # 'https://1492coachworks.com',
        # 'https://1stchoicecollision.com',
        # 'https://1stclassauto.com',
        # 'https://2brotherscollision.com',
        # 'https://25thstreetautomotive.com',
        # 'https://3aautorepair.com',
        # 'https://3acollision.com',
        # 'https://3dbodybusiness.site',
        # 'https://fivestarsbodyshop.com',
        # 'https://7-eleven.com',
        # 'https://821collision.com',
        # 'https://a-aautorepairs.com',
        # 'https://adautobody.com',
        # # 'https://arauto505.com',
        # 'https://arbodyspecialty.com',
        # 'https://ac-auto.com',
        # 'https://amastermechanic.com',
        # 'https://asuperiorshop.com',
        # 'http://www.714-studios.com',
        # 'http://www.darrellsells.com/',
        # # '//5525ebeachdrive.staydirectly.com',
        # # 'angieglobalrealty.com/',
        # 'http://www.sapphireresidencescr.com',
        # 'https://taylorgarandrealestate.com/',
        # 'http://www.nilpatel.net/',
        # 'http://inspireddreamrealestatenj.net/',
        # 'https://www.booking.com/hotel/mx/amp-suites-ferri.es.html',
        # 'https://www.facebook.com/story.php?story_fbid=922926163194483&id=100064313246709&mibextid=xfxF2&rdid=lAeukyB7legMG9fU',
        # 'https://ilockedyou.hu',
        # "https://www.elitelandscapingny.com/",  # this url gives 404
        # 'https://lipotipekseg.hu',
        # 'https://siapnikah.org/',
        # 'http://fauna.com',
        # 'aautobodyshop.com',
        # 'https://www.onestoptruckequipment.com/',
        # 'legacyatwaltonkennesawmountain.com',
        'https://3006springfield.com.tr/',
        'https://rubricx.com'

    ]

    for url in urls:
        start = time.time()
        event = {
            'rawPath': 'search-by-domain',
            "queryStringParameters": {
                "url": url,
                # "domain": url,
                "use-db": "false",
                # 'local_run':'true'
            }
        }
        response = lambda_handler(event, None)
        print(response)
        print(f"Execution time: {time.time() - start:.2f} seconds")
