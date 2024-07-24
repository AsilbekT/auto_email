# graph.py
from configparser import SectionProxy
from azure.identity import ClientSecretCredential
from msgraph import GraphServiceClient
from kiota_authentication_azure.azure_identity_authentication_provider import AzureIdentityAuthenticationProvider
from msgraph.generated.users.item.user_item_request_builder import UserItemRequestBuilder
from msgraph.generated.users.item.mail_folders.item.messages.messages_request_builder import (
    MessagesRequestBuilder)
from msgraph.generated.users.item.send_mail.send_mail_post_request_body import (
    SendMailPostRequestBody)
from msgraph.generated.models.message import Message
from msgraph.generated.models.item_body import ItemBody
from msgraph.generated.models.body_type import BodyType
from msgraph.generated.models.recipient import Recipient
from msgraph.generated.models.email_address import EmailAddress
from msgraph.generated.users.item.messages.item.reply.reply_post_request_body import ReplyPostRequestBody
from msgraph.generated.users.item.messages.item.reply_all.reply_all_post_request_body import ReplyAllPostRequestBody


class Graph:
    settings: SectionProxy
    client_secret_credential: ClientSecretCredential
    user_client: GraphServiceClient

    def __init__(self, config: SectionProxy):
        self.settings = config
        client_id = self.settings['clientId']
        tenant_id = self.settings['tenantId']
        client_secret = self.settings['clientSecret']
        scopes = [self.settings['graphUserScopes']]

        self.client_secret_credential = ClientSecretCredential(
            tenant_id=tenant_id,
            client_id=client_id,
            client_secret=client_secret
        )

        auth_provider = AzureIdentityAuthenticationProvider(
            self.client_secret_credential, scopes=scopes)
        self.user_client = GraphServiceClient(auth_provider)

    async def get_user(self):
        # Only request specific properties using $select
        query_params = UserItemRequestBuilder.UserItemRequestBuilderGetQueryParameters(
            select=['displayName', 'mail', 'userPrincipalName']
        )

        request_config = UserItemRequestBuilder.UserItemRequestBuilderGetRequestConfiguration(
            query_parameters=query_params
        )

        user = await self.user_client.me.get(request_configuration=request_config)
        return user

    async def get_inbox(self):
        query_params = MessagesRequestBuilder.MessagesRequestBuilderGetQueryParameters(
            # Only request specific properties
            select=['id', 'from', 'isRead', 'receivedDateTime', 'subject'],
            # Get at most 25 results
            top=25,
            # Sort by received time, newest first
            orderby=['receivedDateTime DESC']
        )
        request_config = MessagesRequestBuilder.MessagesRequestBuilderGetRequestConfiguration(
            query_parameters=query_params
        )

        messages = await self.user_client.me.mail_folders.by_mail_folder_id('inbox').messages.get(
            request_configuration=request_config)
        return messages

    async def send_mail(self, subject: str, body: str, recipient: str):
        message = Message()
        message.subject = subject

        message.body = ItemBody()
        message.body.content_type = BodyType.Text
        message.body.content = body

        to_recipient = Recipient()
        to_recipient.email_address = EmailAddress()
        to_recipient.email_address.address = recipient
        message.to_recipients = []
        message.to_recipients.append(to_recipient)

        request_body = SendMailPostRequestBody()
        request_body.message = message

        await self.user_client.me.send_mail.post(body=request_body)

    async def reply_to_message(self, message_id: str, comment: str):
        request_body = ReplyAllPostRequestBody(
            comment=comment,
        )
        await self.user_client.me.messages.by_message_id(message_id).reply_all.post(request_body)

    async def make_graph_call(self):
        # INSERT YOUR CODE HERE
        return
