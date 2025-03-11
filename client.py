import requests
import json
import argparse
import os
import readline
import sys
import time
import threading
import boto3
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from urllib.parse import urlparse
from dotenv import load_dotenv
from typing import List, Dict, Optional, Any
API_ENDPOINT = "/v1/chat/completions"
class ThinkingIndicator:
    """Animated thinking indicator for the chat client."""
    def __init__(self):
        self._stop_event = threading.Event()
        self._thread = None
    def start(self):
        """Start the thinking animation in a separate thread."""
        print("\n", end='', flush=True)
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._animate)
        self._thread.daemon = True
        self._thread.start()
    def stop(self):
        """Stop the thinking animation and clean up."""
        if self._thread:
            self._stop_event.set()
            self._thread.join()
            print("\r\033[K", end='', flush=True)
    def _animate(self):
        """Animation loop for the thinking indicator."""
        while not self._stop_event.is_set():
            for frame in ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]:
                if self._stop_event.is_set():
                    break
                print(f"\r\033[K{frame} Thinking...", end='', flush=True)
                time.sleep(0.1)
class ChatClient:
    """Client for interacting with the serverless LLM API."""
    def __init__(self, api_base: str, max_tokens: int = 512, temperature: float = 0.6,
                 credentials: Optional[Any] = None, region: Optional[str] = None):
        """Initialize the chat client.
        Args:
            api_base: Base URL for the API
            max_tokens: Maximum tokens to generate in responses
            temperature: Sampling temperature for text generation
            credentials: AWS credentials (optional, will be loaded from environment if None)
            region: AWS region (optional, will be extracted from URL if None)
        """
        self.api_base = api_base.rstrip('/')
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.session = requests.Session()
        self.messages: List[Dict[str, str]] = []
        self.thinking = ThinkingIndicator()
        if credentials is None:
            session = boto3.Session()
            self.credentials = session.get_credentials()
            if not self.credentials:
                raise ValueError("AWS credentials not found. Please configure AWS credentials.")
        else:
            self.credentials = credentials
        if region is None:
            self.region = urlparse(self.api_base).hostname.split('.')[2]
        else:
            self.region = region
        self.new_conversation()
    def new_conversation(self):
        """Start a new conversation by resetting the message history."""
        self.messages = []
    def _sign_request(self, url: str, method: str, body: Optional[Dict]) -> requests.PreparedRequest:
        """Sign an HTTP request with AWS SigV4 authentication.
        Args:
            url: The full URL for the request
            method: HTTP method (e.g., 'GET', 'POST')
            body: Request body to be JSON serialized
        Returns:
            A signed request ready to be sent
        """
        aws_request = AWSRequest(
            method=method,
            url=url,
            data=json.dumps(body) if body else None,
            headers={
                'Content-Type': 'application/json',
                'Accept': 'text/event-stream'
            }
        )
        SigV4Auth(self.credentials, 'lambda', self.region).add_auth(aws_request)
        return requests.Request(
            method,
            url,
            headers=dict(aws_request.headers),
            data=aws_request.data
        ).prepare()
    def send_message(self, message: str) -> Optional[str]:
        """Send a message to the LLM and get the response.
        Args:
            message: The user's message
        Returns:
            The assistant's response, or None if there was an error
        """
        self.messages.append({"role": "user", "content": message})
        try:
            url = f"{self.api_base}{API_ENDPOINT}"
            body = {
                "messages": self.messages,
                "max_tokens": self.max_tokens,
                "temperature": self.temperature
            }
            prepared_request = self._sign_request(
                url=url,
                method='POST',
                body=body
            )
            self.thinking.start()
            response = self.session.send(prepared_request, stream=True)
            response.raise_for_status()
            assistant_message = ""
            first_chunk = True
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
                                    if first_chunk:
                                        self.thinking.stop()
                                        print("<think>", flush=True)
                                        first_chunk = False
                                    print(content, end='', flush=True)
                                    assistant_message += content
                        except json.JSONDecodeError:
                            continue
            print()  # Add a newline at the end
            if assistant_message:
                self.messages.append({"role": "assistant", "content": assistant_message})
            return assistant_message
        except requests.exceptions.RequestException as e:
            self.thinking.stop()
            print(f"\nError making request: {str(e)}")
            return None
        except Exception as e:
            self.thinking.stop()
            print(f"\nUnexpected error: {str(e)}")
            return None
def get_api_base() -> str:
    """Get the API base URL from command line arguments or environment variables.
    Returns:
        The API base URL
    Raises:
        ValueError: If the API base URL is not provided
    """
    load_dotenv()
    parser = argparse.ArgumentParser(description='Interactive chat client')
    parser.add_argument('--api-base', help='API base URL')
    parser.add_argument('--temperature', type=float, default=0.6,
                       help='Sampling temperature (0.0-1.0)')
    parser.add_argument('--max-tokens', type=int, default=8192,
                       help='Maximum tokens to generate')
    args = parser.parse_args()
    if args.api_base:
        return args.api_base, args.temperature, args.max_tokens
    elif 'CHAT_API_BASE' in os.environ:
        return os.environ['CHAT_API_BASE'], args.temperature, args.max_tokens
    else:
        raise ValueError(
            "API base URL not found. Please set it via --api-base argument "
            "or CHAT_API_BASE environment variable in .env file"
        )
def main():
    """Main function for the chat client."""
    try:
        api_base, temperature, max_tokens = get_api_base()
        client = ChatClient(
            api_base=api_base,
            temperature=temperature,
            max_tokens=max_tokens
        )
        print(f"Using API base URL: {api_base}")
        print(f"Temperature: {temperature}")
        print(f"Max tokens: {max_tokens}")
        print("\nChat started. Available commands:")
        print("  /quit - Exit the chat")
        print("  /new  - Start a new conversation")
        print("  Use ↑/↓ keys to navigate through history")
        histfile = ".chat_history"
        try:
            readline.read_history_file(histfile)
            readline.set_history_length(1000)
        except FileNotFoundError:
            pass
        def get_input():
            user_input = input("\n➤ ")  # Unicode right-pointing triangle
            return user_input.strip()
        while True:
            user_input = get_input()
            readline.write_history_file(histfile)
            if user_input == '/quit':
                print("\nChat ended. Goodbye!")
                break
            elif user_input == '/new':
                client.new_conversation()
                print("\nStarting new conversation...")
                continue
            elif not user_input:
                continue
            client.send_message(user_input)
    except ValueError as e:
        print(f"Error: {e}")
    except KeyboardInterrupt:
        print("\nChat ended by user. Goodbye!")
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
if __name__ == "__main__":
    main()