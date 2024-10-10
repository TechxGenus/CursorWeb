# CursorWeb

<p align="center">
<a href="http://arxiv.org/abs/2410.07002">[📄arXiv]</a> |
<a href="https://hf.co/papers/2410.07002">[🤗HF Paper]</a> |
<a href="https://huggingface.co/collections/TechxGenus/cursorcore-series-6706618c38598468866b60e2">[🤖Models]</a> |
<a href="https://github.com/TechxGenus/CursorCore">[🛠️Code]</a> |
<a href="https://github.com/TechxGenus/CursorWeb">[<img src="https://github.com/TechxGenus/CursorCore/blob/main/pictures/cursorcore.png" width="12.5px">Web]</a> |
<a href="https://discord.gg/Z5Tev8fV">[<img src="https://github.com/TechxGenus/CursorCore/blob/main/pictures/discord.png" width="15x">Discord]</a>
</p>

<hr>

- [CursorWeb](#cursorweb)
  - [Introduction](#introduction)
  - [Features](#features)
  - [Installation](#installation)
    - [Prerequisites](#prerequisites)
    - [Frontend Setup](#frontend-setup)
    - [Backend Setup](#backend-setup)
  - [Usage](#usage)
  - [Citation](#citation)
  - [Contribution](#contribution)

<hr>

## Introduction

CursorWeb is the frontend display interface of [CursorCore](https://github.com/TechxGenus/CursorCore), designed to implement popular features of Cursor in the browser without relying on specific editor or IDE. The application is built using Vue.js for the frontend and FastAPI for the backend. Please read [our paper](http://arxiv.org/abs/2410.07002) to learn more.

<p align="center">
<img width="100%" alt="conversation" src="https://github.com/TechxGenus/CursorCore/blob/main/pictures/conversation.png">
</p>

![CursorWeb](https://github.com/TechxGenus/CursorCore/blob/main/pictures/CursorWeb.gif)

## Features

- **Chat**: A conversational interface similar to ChatGPT.
- **Inline Chat**: An inline chat feature similar to Github Copilot Chat or Cursor Command K.
- **Tab**: An automated editing feature similar to Cursor Copilot++

## Installation

### Prerequisites

- Node.js (version 14 or higher)
- Python (version 3.7 or higher)

### Frontend Setup

1. Enter the frontend directory:

   ```bash
   cd frontend
   ```

2. Install the dependencies:

   ```bash
   yarn install
   ```

3. Start the development server:

   ```bash
   yarn serve
   ```

### Backend Setup

1. Enter the backend directory:

   ```bash
   cd backend
   ```

2. Install the required Python packages:

   ```bash
   pip install -r requirements.txt
   ```

3. Start the model inference service
   CursorCore uses `vllm`'s OpenAI-compatible server to run its services. Below is an example command to start the service:

   ```bash
   python -m vllm.entrypoints.openai.api_server --port 10086 --model TechxGenus/CursorCore-Yi-1.5B --dtype bfloat16 --enable-prefix-caching
   ```

   For more details on model inference configuration and optimization options, refer to [the documentation of vllm](https://docs.vllm.ai/en/latest/).

   **Note**: The backend leverages extra parameters specific to `vllm`'s OpenAI-compatible server for handling custom chat templates and special tokens. Other OpenAI-compatible inference services may not be directly applicable.

4. Configure model service settings:
   Define the model inference service parameters in `model_map.json`. An example configuration is as follows:

   ```json
   {
       "TechxGenus/CursorCore-Yi-1.5B": {
           "base": "http://127.0.0.1:10086/v1",
           "api": "sk-xxx"
       }
   }
   ```

5. Run the FastAPI server:

   ```bash
   python main.py --model_map model_map.json
   ```

## Usage

Open your browser and go to `http://localhost:8080` to access the interface.

The left window provides the chat interface, while the code editor on the right displays the inline chat and tab features. To use the inline chat, press **Ctrl+I** (or **Command+I** on Mac). To accept automated editing suggestions, press **Tab**.

## Citation

```bibtex
@article{jiang2024cursorcore,
  title   = {CursorCore: Assist Programming through Aligning Anything},
  author  = {Hao Jiang and Qi Liu and Rui Li and Shengyu Ye and Shijin Wang},
  year    = {2024},
  journal = {arXiv preprint arXiv: 2410.07002}
}
```

## Contribution

Contributions are welcome! If you find any bugs or have suggestions for improvements, please open an issue or submit a pull request.
