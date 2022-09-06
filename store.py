import requests


def authenticate(client_id):
    response = requests.post(
        'https://api.moltin.com/oauth/access_token',
        data={
            'client_id': client_id,
            'grant_type': 'implicit'
        }
    )
    response.raise_for_status()
    return response.json()['access_token']


def get_all_products(access_token):
    response = requests.get(
        'https://api.moltin.com/v2/products',
        headers={
            'Authorization': f'Bearer {access_token}',
        }
    )
    response.raise_for_status()
    return response.json()['data']


def get_file(file_id, access_token):
    response = requests.get(
        f'https://api.moltin.com/v2/files/{file_id}',
        headers={
            'Authorization': f'Bearer {access_token}',
        }
    )
    response.raise_for_status()
    return response.json()['data']


def get_photo(link):
    response = requests.get(link)
    response.raise_for_status()
    return response.content


def get_product(product_id, access_token):
    response = requests.get(
        f'https://api.moltin.com/v2/products/{product_id}',
        headers={
            'Authorization': f'Bearer {access_token}',
        }
    )
    response.raise_for_status()
    return response.json()['data']


def create_cart(product_id, quantity, access_token):
    response = requests.post(
        'https://api.moltin.com/v2/carts/abd/items',
        headers={
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json',
        },
        json={
            "data": {
                "id": product_id,
                "type": "cart_item",
                "quantity": quantity,
            }
        })
    response.raise_for_status()
    return response.json()
