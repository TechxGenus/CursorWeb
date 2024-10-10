from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from special_tokens import *
from utils import decorate_code, postprocess_output_wf, blockwise_if_continuous_modify
import json
import uvicorn
import argparse
import requests

parser = argparse.ArgumentParser()
parser.add_argument("--model_map", type=str, help="Model name, base and port")
parser.add_argument("--use_target_area", action="store_true", help="Whether to use target area")
parser.add_argument("--sliding_window", type=int, default=2, help="Sliding window size")
parser.add_argument("--max_tokens", type=int, default=3072, help="Max tokens")
parser.add_argument("--temperature", type=float, default=0.0, help="Temperature")
parser.add_argument("--top_p", type=float, default=1.0, help="Top-p sampling")
parser.add_argument("--frequency_penalty", type=float, default=0, help="Frequency penalty")
parser.add_argument("--presence_penalty", type=float, default=0, help="Presence penalty")
args = parser.parse_args()

with open(args.model_map, "r") as f:
    model_map = json.load(f)

model = list(model_map.keys())[0]
api_key = model_map[model]['api']
base_url = model_map[model]['base']
if not base_url.endswith('/'):
    base_url += '/'
url = f"{base_url}chat/completions"

headers = {
    'Content-Type': 'application/json',
    'Authorization': f'Bearer {api_key}',
}

history_current = []
chat_conversation = []

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Model for normal chat requests
class ChatMessage(BaseModel):
    text: str

# Model for tab-autoedit requests
class CodeRequest(BaseModel):
    code: str
    area: list

# Model for inline-chat requests
class InlineRequest(BaseModel):
    code: str
    area: list
    instruction: str

@app.post("/api/chat")
async def chat(message: ChatMessage):    
    """
    Handles the chat conversation by appending the user's message to the chat history,
    sending the conversation to an external API for processing, and appending the 
    assistant's response to the chat history.
    Args:
        message (ChatMessage): The message object containing the user's input text.
    Returns:
        dict: A dictionary containing the assistant's response text.
    Raises:
        requests.exceptions.RequestException: If there is an issue with the HTTP request.
    """
    global chat_conversation

    chat_conversation.append({'role': 'user', 'content': message.text})

    data = {
        'model': model,
        'messages': chat_conversation,
        'temperature': args.temperature,
        'max_tokens': args.max_tokens,
        'top_p': args.top_p,
        'frequency_penalty': args.frequency_penalty,
        'presence_penalty': args.presence_penalty,
    }

    response = requests.post(url, headers=headers, json=data, verify=False)

    if response.status_code == 200:
        result = response.json()
        assistant = result['choices'][0]['message']['content']
    else:
        assistant = "Sorry, there was an error processing your request."

    chat_conversation.append({'role': 'assistant', 'content': assistant.rstrip()})
    return {"assistant": assistant.rstrip()}

@app.post("/api/tab")
async def tab(request: CodeRequest):
    """
    Handles the tab completion request by updating the history of code inputs and generating a response from an assistant model.
    Args:
        request (CodeRequest): The request object containing the code and area information.
    Returns:
        dict: A dictionary containing the assistant's response.
    The function performs the following steps:
    1. Updates the global `history_current` list with the new code from the request.
    2. If `args.use_target_area` is True, it modifies the current code based on the specified area.
    3. Prepares the messages for the assistant model by decorating the code history.
    4. Sends a POST request to the assistant model with the prepared data.
    5. Processes the response from the assistant model and extracts the assistant's message.
    6. Returns the assistant's response in a dictionary.
    """
    global history_current
    
    # The model does not enforce a specific granularity for historical snippets during training.
    # It can record changes ranging from single characters to large code blocks.
    # For deployment, we use a heuristic to decide how to record historical snippets.
    # This decision is based on whether the change blocks are continuous and if the edit distance is continuous.
    # Other heuristic is also ok, such as just using edit distance
    if not history_current:
        if request.code == "":
            return {"assistant": ""}
        history_current.append(request.code)
    else:
        if len(history_current) == 1:
            if blockwise_if_continuous_modify("", history_current[-1], request.code):
                history_current[-1] = request.code
            else:
                history_current.append(request.code)
        elif blockwise_if_continuous_modify(history_current[-2], history_current[-1], request.code):
            history_current[-1] = request.code
        else:
            history_current.append(request.code)

    if args.use_target_area:
        try:
            if request.area[0] == request.area[1]:
                current = history_current[-1][:request.area[0]] + TARGET + history_current[-1][request.area[1]:]
            else:
                current = history_current[-1][:request.area[0]] + TARGET_START + history_current[-1][request.area[0]:request.area[1]] + TARGET_END + history_current[-1][request.area[1]:]
        except:
            current = history_current[-1]
    else:
        current = history_current[-1]

    # TODO: support others modification types like Location-and-Change and Search-and-Replace
    if args.sliding_window > 0:
        history = history_current[-args.sliding_window-1:-1]
    else:
        history = history_current[:-1]
    messages = [{'role': 'history', 'content': decorate_code(code)} for code in history] + [{'role': 'current', 'content': decorate_code(current)}]

    # TODO: Implement streaming return
    data = {
        'model': model,
        'messages': messages,
        'temperature': args.temperature,
        'max_tokens': args.max_tokens,
        'top_p': args.top_p,
        'frequency_penalty': args.frequency_penalty,
        'presence_penalty': args.presence_penalty,
        'chat_template': 'assistant-conversation',
        'stop': [NEXT_END],
        "skip_special_tokens": False,
    }

    # TODO: Strategy: Pre-Prefill of History
    # Currently, to handle conversation retrieval/compression, we implement a simple sliding window strategy that discards previous edit history.
    # When making a request, the model needs to recalculate the input because the initial history has been modified.
    # In the sliding window strategy, part of the historical segment in the request is determined before the sliding window moves to that position.
    # We can consider sending a request to have this part prefilled in advance, so that only part of it needs to be prefilled later.
    # If the model inference backend supports request prioritization, this should be a low-priority request.
    response = requests.post(url, headers=headers, json=data, verify=False)

    if response.status_code == 200:
        result = response.json()
        assistant = postprocess_output_wf(current, result['choices'][0]['message']['content'])
    else:
        assistant = request.code

    # In the current implementation, regardless of the modification format types (WF, LC, SR) of the model, the changes are eventually converted into the whole file format and passed to the front end.
    # The front end then chooses different display methods according to the specific requirements of the application.
    # If we want to split a predicted change and return it to the front end multiple times to achieve an effect similar to "Tab Tab Tab", we need to split the changes and add some caching mechanisms. It should be good to implement it on the frontend or the backend.
    # Currently, for a simple demonstration, we return all changes at once.
    return {"assistant": assistant.rstrip()}

@app.post("/api/inline")
async def inline(request: InlineRequest):
    """
    Handles inline requests by updating the history of code snippets and generating a response based on the current state.
    Args:
        request (InlineRequest): The incoming request containing code, area, and instruction.
    Returns:
        dict: A dictionary containing the assistant's response.
    The function performs the following steps:
    1. Updates the global `history_current` list with the new code from the request.
    2. Modifies the current code snippet based on the specified area if `args.use_target_area` is True.
    3. Prepares a list of messages for the model, including the history and the current code snippet.
    4. Sends a POST request to the specified URL with the prepared data.
    5. Extracts the assistant's response from the model's output.
    6. Returns the assistant's response as a dictionary.
    """
    global history_current

    # The model does not enforce a specific granularity for historical snippets during training.
    # It can record changes ranging from single characters to large code blocks.
    # For deployment, we use a heuristic to decide how to record historical snippets.
    # This decision is based on whether the change blocks are continuous and if the edit distance is continuous.
    # Other heuristic is also ok, such as just using edit distance
    if not history_current:
        history_current.append(request.code)
    else:
        if len(history_current) == 1:
            if blockwise_if_continuous_modify("", history_current[-1], request.code):
                history_current[-1] = request.code
            else:
                history_current.append(request.code)
        elif blockwise_if_continuous_modify(history_current[-2], history_current[-1], request.code):
            history_current[-1] = request.code
        else:
            history_current.append(request.code)

    if args.use_target_area:
        try:
            if request.area[0] == request.area[1]:
                current = history_current[-1][:request.area[0]] + TARGET + history_current[-1][request.area[1]:]
            else:
                current = history_current[-1][:request.area[0]] + TARGET_START + history_current[-1][request.area[0]:request.area[1]] + TARGET_END + history_current[-1][request.area[1]:]
        except:
            current = history_current[-1]
    else:
        current = history_current[-1]

    # TODO: support others modification types like Location-and-Change and Search-and-Replace
    if args.sliding_window > 0:
        history = history_current[-args.sliding_window-1:-1]
    else:
        history = history_current[:-1]
    messages = [{'role': 'history', 'content': decorate_code(code)} for code in history] + [{'role': 'current', 'content': decorate_code(current)}] + [{'role': 'user', 'content': request.instruction}]

    
    # TODO: Implement streaming return
    data = {
        'model': model,
        'messages': messages,
        'temperature': args.temperature,
        'max_tokens': args.max_tokens,
        'top_p': args.top_p,
        'frequency_penalty': args.frequency_penalty,
        'presence_penalty': args.presence_penalty,
        'chat_template': 'assistant-conversation',
        'stop': [NEXT_END],
        "skip_special_tokens": False,
    }

    # TODO: Strategy: Pre-Prefill of History
    # Currently, to handle conversation retrieval/compression, we implement a simple sliding window strategy that discards previous edit history.
    # When making a request, the model needs to recalculate the input because the initial history has been modified.
    # In the sliding window strategy, part of the historical segment in the request is determined before the sliding window moves to that position.
    # We can consider sending a request to have this part prefilled in advance, so that only part of it needs to be prefilled later.
    # If the model inference backend supports request prioritization, this should be a low-priority request.
    response = requests.post(url, headers=headers, json=data, verify=False)

    if response.status_code == 200:
        result = response.json()
        assistant = postprocess_output_wf(current, result['choices'][0]['message']['content'])
    else:
        assistant = request.code

    # In the current implementation, regardless of the modification format types (WF, LC, SR) of the model, the changes are eventually converted into the whole file format and passed to the front end.
    # The front end then chooses different display methods according to the specific requirements of the application.
    # If we want to split a predicted change and return it to the front end multiple times to achieve an effect similar to "Tab Tab Tab", we need to split the changes and add some caching mechanisms. It should be good to implement it on the frontend or the backend.
    # Currently, for a simple demonstration, we return all changes at once.
    return {"assistant": assistant.rstrip()}

@app.post("/api/reset")
async def reset():
    """
    Resets the global chat conversation and history.
    This function clears the global variables `chat_conversation` and `history_current`,
    setting them to empty lists. It is intended to reset the state of the chat and history.
    Returns:
        dict: A dictionary containing the status of the reset operation.
    """
    global chat_conversation
    chat_conversation = []
    
    global history_current
    history_current = []

    return {"status": True}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
