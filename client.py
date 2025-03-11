import requests
import json
import argparse
import os
import readline
import boto3
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from urllib.parse import urlparse
from dotenv import load_dotenv
API_ENDPOINT = "/v1/chat/completions"
def get_api_base():
    load_dotenv()
    parser = argparse.ArgumentParser(description='Interactive chat client')
    parser.add_argument('--api-base', help='API base URL')
    args = parser.parse_args()
    if args.api_base:
        return args.api_base.rstrip('/')
    elif 'CHAT_API_BASE' in os.environ:
        return os.environ['CHAT_API_BASE'].rstrip('/')
    else:
        raise ValueError("API base URL not found. Please set it via --api-base argument or CHAT_API_BASE environment variable in .env file")
def sign_request(url, method, body, credentials, region):
    aws_request = AWSRequest(
        method=method,
        url=url,
        data=json.dumps(body) if body else None,
        headers={
            'Content-Type': 'application/json',
            'Accept': 'text/event-stream'
        }
    )
    SigV4Auth(credentials, 'lambda', region).add_auth(aws_request)
    prepared_request = requests.Request(
        method,
        url,
        headers=dict(aws_request.headers),
        data=aws_request.data
    ).prepare()
    return prepared_request
def chat_with_model(messages, api_base, session, credentials, region):
    try:
        url = f"{api_base}{API_ENDPOINT}"
        body = {
            "messages": messages,
            "max_tokens": 512,
            "temperature": 0.6
        }
        prepared_request = sign_request(
            url=url,
            method='POST',
            body=body,
            credentials=credentials,
            region=region
        )
        response = session.send(prepared_request, stream=True)
        response.raise_for_status()
        print("\nAssistant:", end=' ', flush=True)
        assistant_message = ""
        for line in response.iter_lines():
            if line:
                line = line.decode('utf-8')
                if line == "data: [DONE]":
                    break
                if line.startswith("data: "):
                    try:
                        json_data = json.loads(line[6:])
                        if 'choices' in json_data and len(json_data['choices']) > 0:
                            choice = json_data['choices'][0]
                            if 'delta' in choice and 'content' in choice['delta']:
                                content = choice['delta']['content']
                                print(content, end='', flush=True)
                                assistant_message += content
                    except json.JSONDecodeError:
                        continue
        print()  # Add a newline at the end
        return assistant_message
    except requests.exceptions.RequestException as e:
        print(f"\nError making request: {str(e)}")
        return None
def get_initial_messages():
    return [
        {"role": "system", "content": "You are a helpful assistant"}
    ]
def main():
    try:
        api_base = get_api_base()
        messages = get_initial_messages()
        session = boto3.Session()
        credentials = session.get_credentials()
        if not credentials:
            raise ValueError("AWS credentials not found. Please configure AWS credentials.")
        region = urlparse(api_base).hostname.split('.')[2]
        requests_session = requests.Session()
        print(f"Using API base URL: {api_base}")
        print("\nChat started. Available commands:")
        print("  /quit - Exit the chat")
        print("  /new  - Start a new conversation")
        print("  Use ↑/↓ keys to navigate through history")
        histfile = ".chat_history"  # Store in current working directory
        try:
            readline.read_history_file(histfile)
            readline.set_history_length(1000)
        except FileNotFoundError:
            pass
        while True:
            user_input = input("\nYou: ").strip()
            readline.write_history_file(histfile)
            if user_input == '/quit':
                print("\nChat ended. Goodbye!")
                break
            elif user_input == '/new':
                messages = get_initial_messages()
                print("\nStarting new conversation...")
                continue
            messages.append({"role": "user", "content": user_input})
            assistant_message = chat_with_model(
                messages, 
                api_base, 
                requests_session, 
                credentials, 
                region
            )
            if assistant_message is not None:
                messages.append({"role": "assistant", "content": assistant_message})
    except ValueError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
if __name__ == "__main__":
    main()