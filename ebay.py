import os
import json
import requests
import dicttoxml
import xmltodict
from base64 import b64encode
from urllib.parse import urlparse, parse_qs
import webbrowser
from datetime import datetime
from threading import Thread
from concurrent.futures import ThreadPoolExecutor, Future
import asyncio
from tkinter import simpledialog

mode = 'PRODUCTION'

API_ENDPOINT = "https://api.sandbox.ebay.com/ws/api.dll" if mode == 'SANDBOX' else "https://api.ebay.com/ws/api.dll"
RESTFUL_API_ENDPOINT = "https://api.sandbox.ebay.com" if mode == 'SANDBOX' else "https://api.ebay.com"
CLIENT_ID = "BambiIve-ListingD-SBX-566ca3cf7-2a51ab02" if mode == 'SANDBOX' else "BambiIve-ListingD-PRD-f66269612-8be4f45b"
DEV_ID = "22ef2f9c-0045-46a9-a008-91cecff74ae1" if mode == 'SANDBOX' else "22ef2f9c-0045-46a9-a008-91cecff74ae1"
CLIENT_SECRET = "SBX-66ca3cf7b186-6b54-42fc-87ea-e283" if mode == 'SANDBOX' else "PRD-662696129406-1233-4c4a-a8e2-afac"
REDIRECT_URI = "Bambi_Iversen-BambiIve-Listin-aarjz" if mode == 'SANDBOX' else "Bambi_Iversen-BambiIve-Listin-akmwwycb"

def call_with_future(fn, future, args, kwargs):
    try:
        result = fn(*args, **kwargs)
        future.set_result(result)
    except Exception as exc:
        future.set_exception(exc)


def threaded(fn):
    def wrapper(*args, **kwargs):
        future = Future()
        Thread(target=call_with_future, args=(fn, future, args, kwargs)).start()
        return future
    return wrapper

class EBaySDK:
    def __init__(self, window=None):

        # Initialize credentials and API endpoint from environment variables
        self.client_id = CLIENT_ID
        self.client_secret = CLIENT_SECRET
        self.dev_id = DEV_ID
        self.redirect_uri = REDIRECT_URI
        self.api_endpoint = API_ENDPOINT
        self.restful_api_endpoint = RESTFUL_API_ENDPOINT
        
        self.scopes = (
            "https://api.ebay.com/oauth/api_scope "
            "https://api.ebay.com/oauth/api_scope/sell.marketing.readonly "
            "https://api.ebay.com/oauth/api_scope/sell.marketing "
            "https://api.ebay.com/oauth/api_scope/sell.inventory.readonly "
            "https://api.ebay.com/oauth/api_scope/sell.inventory "
            "https://api.ebay.com/oauth/api_scope/sell.account.readonly "
            "https://api.ebay.com/oauth/api_scope/sell.account "
            "https://api.ebay.com/oauth/api_scope/sell.fulfillment.readonly "
            "https://api.ebay.com/oauth/api_scope/sell.fulfillment "
            "https://api.ebay.com/oauth/api_scope/sell.analytics.readonly "
            "https://api.ebay.com/oauth/api_scope/sell.finances "
            "https://api.ebay.com/oauth/api_scope/sell.payment.dispute "
            "https://api.ebay.com/oauth/api_scope/commerce.identity.readonly "
            "https://api.ebay.com/oauth/api_scope/sell.reputation "
            "https://api.ebay.com/oauth/api_scope/sell.reputation.readonly "
            "https://api.ebay.com/oauth/api_scope/commerce.notification.subscription "
            "https://api.ebay.com/oauth/api_scope/commerce.notification.subscription.readonly "
            "https://api.ebay.com/oauth/api_scope/sell.stores "
            "https://api.ebay.com/oauth/api_scope/sell.stores.readonly "
            "https://api.ebay.com/oauth/scope/sell.edelivery "
        ) if mode == 'PRODUCTION' else (
            "https://api.ebay.com/oauth/api_scope https://api.ebay.com/oauth/api_scope/buy.order.readonly https://api.ebay.com/oauth/api_scope/buy.guest.order https://api.ebay.com/oauth/api_scope/sell.marketing.readonly https://api.ebay.com/oauth/api_scope/sell.marketing https://api.ebay.com/oauth/api_scope/sell.inventory.readonly https://api.ebay.com/oauth/api_scope/sell.inventory https://api.ebay.com/oauth/api_scope/sell.account.readonly https://api.ebay.com/oauth/api_scope/sell.account https://api.ebay.com/oauth/api_scope/sell.fulfillment.readonly https://api.ebay.com/oauth/api_scope/sell.fulfillment https://api.ebay.com/oauth/api_scope/sell.analytics.readonly https://api.ebay.com/oauth/api_scope/sell.marketplace.insights.readonly https://api.ebay.com/oauth/api_scope/commerce.catalog.readonly https://api.ebay.com/oauth/api_scope/buy.shopping.cart https://api.ebay.com/oauth/api_scope/buy.offer.auction https://api.ebay.com/oauth/api_scope/commerce.identity.readonly https://api.ebay.com/oauth/api_scope/commerce.identity.email.readonly https://api.ebay.com/oauth/api_scope/commerce.identity.phone.readonly https://api.ebay.com/oauth/api_scope/commerce.identity.address.readonly https://api.ebay.com/oauth/api_scope/commerce.identity.name.readonly https://api.ebay.com/oauth/api_scope/commerce.identity.status.readonly https://api.ebay.com/oauth/api_scope/sell.finances https://api.ebay.com/oauth/api_scope/sell.payment.dispute https://api.ebay.com/oauth/api_scope/sell.item.draft https://api.ebay.com/oauth/api_scope/sell.item https://api.ebay.com/oauth/api_scope/sell.reputation https://api.ebay.com/oauth/api_scope/sell.reputation.readonly https://api.ebay.com/oauth/api_scope/commerce.notification.subscription https://api.ebay.com/oauth/api_scope/commerce.notification.subscription.readonly https://api.ebay.com/oauth/api_scope/sell.stores https://api.ebay.com/oauth/api_scope/sell.stores.readonly"
        )
        # Set the target endpoint for the consent request in production
        consent_endpoint = "https://auth.sandbox.ebay.com/oauth2/authorize" if mode == 'SANDBOX' else "https://auth.ebay.com/oauth2/authorize"
        self.token_endpoint = "https://api.sandbox.ebay.com/identity/v1/oauth2/token" if mode == 'SANDBOX' else "https://api.ebay.com/identity/v1/oauth2/token"

        # Define the consent URL
        self.consent_url = (
            f"{consent_endpoint}?"
            f"client_id={self.client_id}&"
            f"response_type=code&"
            f"redirect_uri={self.redirect_uri}&"
            f"scope={self.scopes}"
        )
        
        self.window = window

        # if (self.token is None):
        #     raise Exception(
        #         "Failed to get the user access token. Please check the client id and secret...")

    @threaded
    def get_token(self, isForce=False):
        if not os.path.exists('tokens.json') and not isForce:
            self.log_to_status_label(
                "The file 'tokens.json' does not exist... Start to get token from Ebay...")
            self.get_user_access_token()
        else:
            try:
                with open('tokens.json', 'r') as f:
                    token_data = json.load(f)

                if 'timestamp' not in token_data or 'expires_in' not in token_data or 'refresh_token' not in token_data or 'access_token' not in token_data or 'refresh_token_expires_in' not in token_data:
                    self.log_to_status_label("Data of file 'tokens.json' is invalid. Retry using the auth flow...")
                    self.get_user_access_token()

                if token_data['timestamp'] + token_data['expires_in'] < datetime.now().timestamp() or isForce:
                    if not isForce:
                        self.log_to_status_label('Expired access token. Update access token using refresh token')
                    # Check Refresh Token Expiration
                    if token_data['timestamp'] + token_data['refresh_token_expires_in'] < datetime.now().timestamp():
                        self.log_to_status_label(
                            "The refresh token is also invalid. Retry using the auth flow...")
                        self.get_user_access_token()
                    else:
                        self.log_to_status_label(
                            "The refresh token is valid. Trying to update the access token...")
                        # Update the access token and token.json file
                        updated_token_data = self.update_user_access_token(
                            token_data['refresh_token'])
                        token_data['access_token'] = updated_token_data['access_token']
                        token_data['expires_in'] = updated_token_data['expires_in']
                        token_data['timestamp'] = datetime.now().timestamp()
                        with open('tokens.json', 'w') as f:
                            json.dump(token_data, f, indent=4)
                        self.token = updated_token_data['access_token']
                        self.window.duplicate_button.config(state="normal")
                else:
                    self.log_to_status_label("The access token is valid. Please start the duplicate process...")
                    self.token = token_data['access_token']
                    self.window.duplicate_button.config(state="normal")

            except Exception as e:
                self.log_to_status_label(
                    "Failed to get the user access token from tokens.json. Retry using the auth flow...")
                self.get_user_access_token()
            

    def update_user_access_token(self, refreshToken: str):
        # Make the authorization code grant request to obtain the token
        payload = {
            "grant_type": "refresh_token",
            "refresh_token": refreshToken,
            "scope": self.scopes
        }

        # Encode the client credentials for the Authorization header
        credentials = f"{self.client_id}:{self.client_secret}"
        encoded_credentials = b64encode(credentials.encode()).decode()

        # Set the headers for the token request
        token_headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Basic {encoded_credentials}"
        }

        # Make the POST request to the token endpoint
        response = requests.post(
            self.token_endpoint, headers=token_headers, data=payload)

        # Check the response
        if response.status_code == 200:
            # Parse and print the response JSON
            response_json = response.json()
            self.log_to_status_label("User access token has been updated successfully. Please start the duplicate process...")
            return response_json
        else:
            self.log_to_status_label(f"Error: {response.status_code}, {response.text}")

    def get_user_access_token(self):
        webbrowser.open(self.consent_url)
        self.log_to_status_label("Opening the browser. Please grant consent in the browser.")

        # Schedule the dialog to open in the main thread
        if self.window:
            self.window.after(0, self.open_authorization_dialog)
        else:
            exit(0)

    def open_authorization_dialog(self):
        authorization_code_url = simpledialog.askstring(
            "Authorization", "Enter the authorization code URL:", parent=self.window)
        
        if authorization_code_url is None:
            self.log_to_status_label("User canceled the input dialog.")
            self.token = None
            return None


        try:
            if mode == 'SANDBOX':
                # Parse the URL to extract the authorization code
                parsed_url = urlparse(authorization_code_url)
                query_params = parse_qs(parsed_url.query)
                ru_url = query_params.get('ru', [])[0]
                ru_params = urlparse(ru_url)
                ru_query_params = parse_qs(ru_params.query)
                authorization_code = ru_query_params.get('code', [])[0]
            else:
                # Parse the URL to extract the authorization code
                parsed_url = urlparse(authorization_code_url)
                query_params = parse_qs(parsed_url.query)
                authorization_code = query_params.get('code', [])[0]
        except:
            self.log_to_status_label("The Authorization Code URL is invalid.")
            self.token = None
            return None

        # Make the authorization code grant request to obtain the token
        payload = {
            "grant_type": "authorization_code",
            "code": authorization_code,
            "redirect_uri": self.redirect_uri
        }

        # Encode the client credentials for the Authorization header
        credentials = f"{self.client_id}:{self.client_secret}"
        encoded_credentials = b64encode(credentials.encode()).decode()

        # Set the headers for the token request
        token_headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Basic {encoded_credentials}"
        }

        # Make the POST request to the token endpoint
        response = requests.post(
            self.token_endpoint, headers=token_headers, data=payload)

        # Check the response
        if response.status_code == 200:
            # Parse and print the response JSON
            response_json = response.json()
            token_data = response_json
            token_data['timestamp'] = datetime.now().timestamp()
            # Write the updated JSON data back to the file
            with open('tokens.json', 'w') as f:
                json.dump(token_data, f, indent=4)
            self.log_to_status_label("Succeed to get the user access token and save it to tokens.json")
            self.token = token_data['access_token']
            self.window.duplicate_button.config(state="normal")
        else:
            self.log_to_status_label("Failed to get the user access token. Please check the client id and secret...")
            self.window.duplicate_button.config(state="disabled")
            self.token = None

    def execute(self, funcName: str, item: dict):
        item['ErrorLanguage'] = 'en_US'
        item['WarningLevel'] = 'High'

        # Convert JSON item to XML with the root node name as funcName+'Request'
        xml_body = dicttoxml.dicttoxml(
            item,
            custom_root=funcName+'Request',
            attr_type=False,
            item_func=lambda x: 'NameValueList' if isinstance(
                x, object) else x,
            root=True
        ).decode('utf-8')

        # Add the namespace to the root node
        xml_body = xml_body.replace(
            f"<{funcName}Request>",
            f"<{funcName}Request xmlns=\"urn:ebay:apis:eBLBaseComponents\">"
        )

        # Define headers
        headers = {
            'X-EBAY-API-SITEID': '0',
            'X-EBAY-API-COMPATIBILITY-LEVEL': '967',
            'X-EBAY-API-CALL-NAME': funcName,
            'X-EBAY-API-IAF-TOKEN': self.token,
            'Content-Type': 'text/xml'
        }
        # return
        # Make the POST request
        response = requests.post(
            self.api_endpoint, headers=headers, data=xml_body)

        # Convert XML response to a dictionary
        response_dict = xmltodict.parse(response.text, encoding='Utf-8')

        # Return the response as a dictionary
        return response_dict
    
    def execute_with_xml(self, funcName, xml_body):
        # Define headers
        headers = {
            'X-EBAY-API-SITEID': '0',
            'X-EBAY-API-COMPATIBILITY-LEVEL': '967',
            'X-EBAY-API-CALL-NAME': funcName,
            'X-EBAY-API-IAF-TOKEN': self.token,
            'Content-Type': 'text/xml'
        }

        # Make the POST request
        response = requests.post(
            self.api_endpoint, headers=headers, data=xml_body)

        # Convert XML response to a dictionary
        response_dict = xmltodict.parse(response.text, encoding='Utf-8')

        succeed = response_dict['AddFixedPriceItemResponse']['Ack']
        
        if succeed == 'Success' or succeed == 'Warning' :
            return response_dict['AddFixedPriceItemResponse']['ItemID']
        else:
            return response_dict['AddFixedPriceItemResponse']['Errors']

    def get_item_by_legacy_id(self, item_legacy_id):
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }
        url = f"{
            self.restful_api_endpoint}/buy/browse/v1/item/get_item_by_legacy_id?legacy_item_id={item_legacy_id}"
        response = requests.get(url, headers=headers)
        return response.json()
    
    def get_items_by_item_group(self, item_group_id):
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }
        url = f"{
            self.restful_api_endpoint}/buy/browse/v1/item/get_items_by_item_group?item_group_id={item_group_id}"
        response = requests.get(url, headers=headers)
        return response.json()

    def upload_site_hosted_picture(self, picture_url):
        headers = {
            "X-EBAY-API-IAF-TOKEN": self.token,
            "X-EBAY-API-COMPATIBILITY-LEVEL":"1295",
            "X-EBAY-API-DEV-NAME":self.dev_id,
            "X-EBAY-API-APP-NAME":self.client_id,
            "X-EBAY-API-CERT-NAME":self.client_secret,
            "X-EBAY-API-SITEID":"0",
            "X-EBAY-API-CALL-NAME": "UploadSiteHostedPictures",
            "X-EBAY-API-RESPONSE-ENCODING": "XML",
            "X-EBAY-API-DETAIL-LEVEL": "0",
        }

        # XML payload
        xml_payload = f"""<?xml version="1.0" encoding="utf-8"?>
        <UploadSiteHostedPicturesRequest xmlns="urn:ebay:apis:eBLBaseComponents">
            <RequesterCredentials>
                <ebl:eBayAuthToken xmlns:ebl="urn:ebay:apis:eBLBaseComponents">{self.token}</ebl:eBayAuthToken>
            </RequesterCredentials>
            <PictureName>pictures</PictureName>
            <PictureSet>Supersize</PictureSet>
            <ExtensionInDays>20</ExtensionInDays>
        </UploadSiteHostedPicturesRequest>"""

        # Download image data from picture_url
        response = requests.get(picture_url)
        if response.status_code == 200:
            image_data = response.content
        else:
            print(f"Failed to download image from {
                  picture_url}. Status code: {response.status_code}")
            return

        files = {
            "pictures": ("downloaded_image.jpg", image_data, 'image/jpeg')
        }

        # Make the POST request
        response = requests.post(self.api_endpoint, headers=headers, data={
            'XML Payload' : xml_payload.encode('utf-8')
        }, files=files)

        # Check the response
        if response.status_code == 200:
            responseJson = xmltodict.parse(response.text, encoding='Utf-8')
            return responseJson['UploadSiteHostedPicturesResponse']['SiteHostedPictureDetails']['FullURL'];
        else:
            print(f"Error: {response.status_code}")
            return None
        
    def log_to_status_label(self, message):
        """Log a message to the Tkinter Text widget with ID 'status_label'."""
        if self.window:
            self.window.status_label.config(text=message)
        else:
            print("Status label not found. Message:", message)
