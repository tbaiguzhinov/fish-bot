from itertools import product
import requests
import os

from dotenv import load_dotenv


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
            # 'Content-Type': 'application/json',
        }
    )
    response.raise_for_status()
    return response.json()


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


def main():
    load_dotenv()
    client_id = os.getenv('MOLTIN_CLIENT_ID')
    access_token = authenticate(client_id)
    products = get_all_products(access_token)
    product_id = products['data'][0]['id']
    cart = create_cart(product_id, 1, access_token)
    print(cart)


if __name__ == "__main__":
    main()
