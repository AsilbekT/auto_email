import httpx
from configparser import SectionProxy, ConfigParser
from datetime import datetime, timedelta
import asyncio
import aioredis
import time
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)


class GraphUser:
    settings: SectionProxy

    def __init__(self, config: SectionProxy):
        self.settings = config
        self.client_id = self.settings['clientId']
        self.tenant_id = self.settings['tenantId']
        self.client_secret = self.settings['clientSecret']
        self.scopes = self.settings['graphUserScopes']
        self.lock = asyncio.Lock()

        # Initialize Redis client with connection pooling
        self.redis_client = aioredis.from_url(
            "redis://localhost:6379", decode_responses=True)

    async def get_user_token(self):
        async with self.lock:
            start_time = time.time()
            token = await self.redis_client.get('graph_api_token')
            if token:
                return token

            url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            body = {
                'client_id': self.client_id,
                'scope': self.scopes,
                'client_secret': self.client_secret,
                'grant_type': 'client_credentials'
            }
            async with httpx.AsyncClient() as client:
                response = await client.post(url, headers=headers, data=body)
                if response.status_code == 200:
                    token_data = response.json()
                    token = token_data.get('access_token')
                    expires_in = token_data.get('expires_in', 3600)
                    # Cache the token in Redis with an expiration time
                    await self.redis_client.setex('graph_api_token', expires_in, token)
                    return token
                else:
                    raise Exception(
                        f"Failed to get token: {response.status_code} - {response.text}")

    async def get_headers(self):
        start_time = time.time()
        token = await self.get_user_token()
        return {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }

    async def get_user_id(self, user_principal_name):
        cache_key = f"user_id:{user_principal_name}"
        start_time = time.time()
        user_id = await self.redis_client.get(cache_key)
        if user_id:
            return user_id

        url = f'https://graph.microsoft.com/v1.0/users/{user_principal_name}'
        headers = await self.get_headers()
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
            if response.status_code == 200:
                user_id = response.json().get('id')
                # Cache for 1 day
                await self.redis_client.set(cache_key, user_id, ex=86400)
                return user_id
            else:
                raise Exception(
                    f"Failed to get user ID: {response.status_code} - {response.text}")

    async def get_inbox(self, user_principal_name):
        start_time = time.time()
        user_id = await self.get_user_id(user_principal_name)
        url = f'https://graph.microsoft.com/v1.0/users/{user_id}/mailFolders/inbox/messages?$top=25&$select=id,from,isRead,receivedDateTime,subject'
        headers = await self.get_headers()
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
            if response.status_code == 200:
                return response.json()
            else:
                raise Exception(
                    f"Failed to get inbox: {response.status_code} - {response.text}")

    async def send_mail(self, user_principal_name, subject: str, body: str, recipient: str):
        start_time = time.time()
        user_id = await self.get_user_id(user_principal_name)
        url = f'https://graph.microsoft.com/v1.0/users/{user_id}/sendMail'
        headers = await self.get_headers()
        email = {
            "message": {
                "subject": subject,
                "body": {
                    "contentType": "Text",
                    "content": body
                },
                "toRecipients": [
                    {
                        "emailAddress": {
                            "address": recipient
                        }
                    }
                ]
            },
            "saveToSentItems": "true"
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=email)
            if response.status_code == 202:
                return {"message": "Email sent successfully"}
            else:
                raise Exception(
                    f"Failed to send email: {response.status_code} - {response.text}")
