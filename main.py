from fastapi import FastAPI, HTTPException, Query, Request
import configparser
from graph_api import GraphUser
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import time
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)

app = FastAPI()


class Assignment(BaseModel):
    message_id: str
    user_id: str


# Set up CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080", "http://127.0.0.1:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load settings once during startup
config = configparser.ConfigParser()
config.read(['config.cfg', 'config.dev.cfg'])
azure_settings = config['azure']
graph_user = GraphUser(azure_settings)  # Initialize the Graph API client


@app.get("/messages")
async def list_outlook_messages(user_principal_name: str, load_number: int = Query(None, title="Load Number", description="Search messages by load number in the subject")):
    start_time = time.time()
    try:
        # Fetch messages from the inbox
        message_page = await graph_user.get_inbox(user_principal_name)
        messages = []
        if message_page and 'value' in message_page:
            for message in message_page['value']:
                # Check if the load number is in the subject
                if load_number is not None and str(load_number) in message['subject']:
                    msg_details = {
                        "Message ID": message['id'],
                        "Subject": message['subject'],
                        "From": message['from']['emailAddress']['name'] if message['from'] and message['from']['emailAddress'] else "NONE",
                        "Status": "Read" if message['isRead'] else "Unread",
                        "Received": message['receivedDateTime']
                    }
                    messages.append(msg_details)
        if not messages:
            return {"message": "No messages found with the specified load number."}
        return {"messages": messages}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/")
async def read_root():
    start_time = time.time()
    response = {"Hello": "World"}
    return response


@app.post("/assign/")
async def assign_message(assignment: Assignment):
    start_time = time.time()
    response = {"message": "Assignment successful", "data": assignment}
    return response


@app.get("/redirected")
async def get_redirected(request: Request):
    start_time = time.time()
    query_params = request.query_params
    response = {"message": "received", "query_params": dict(query_params)}
    return response
