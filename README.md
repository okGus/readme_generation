# Readme Generator

## Description

This project automates the generation of `README.md` files for software projects. It analyzes the source code within a specified directory, extracts relevant information, and utilizes AI models (such as Ollama, Gemini, Groq, or OpenAI) to create a comprehensive `README.md` file. The tool identifies project files, filters out irrelevant directories and files, and formats the codebase content into a prompt for the AI model. The generated `README.md` file is then saved to a specified output file or a temporary directory.

## Features

- **Codebase Scanning:** Recursively scans a given directory for relevant source code files.
- **File Filtering:** Excludes specified directories (e.g., `.venv`, `node_modules`, `build`) and file types (e.g., `.o`, `.dll`, `.exe`) to focus on relevant code.
- **AI-Powered Generation:** Leverages AI models (Ollama, Gemini, Groq, OpenAI) to generate `README.md` content based on the codebase.
- **API Key Support:** Supports Gemini, Groq, and OpenAI API keys for utilizing their respective AI models.
- **Ollama Integration:** Defaults to using the local Ollama API if no API keys are provided.
- **Output Options:** Saves the generated `README.md` file to a user-specified path or a temporary directory.
- **Markdown Formatting:** Ensures the generated content is properly formatted in Markdown.
- **Clean Output:** Removes any unnecessary markdown fences from the AI-generated output.

## Installation

- Ensure you have Python 3 installed.
- Install the required Python packages. It's recommended to use a virtual environment.

```bash
# Example using pip:
pip install requests tqdm google-generativeai openai
```

- Ensure Ollama is installed and running locally if you intend to use it.

## Usage

To generate a `README.md` file for a project:

```bash
python main.py -d <project_directory> -o <output_file> --gemini-api-key <your_gemini_api_key>
```

Or

```bash
python main.py -d <project_directory>
```

- `-d` or `--directory`: Specifies the path to the project directory.
- `-o` or `--output_file`: Specifies the file path to save the generated `README.md`. If not provided, the file will be saved to a temporary directory.
- `--gemini-api-key`: (Optional) Your Gemini API key for using the Gemini AI model.
- `--openai-api-key`: (Optional) Your OpenAI API key for using OpenAI's models.
- `--groq-api-key`: (Optional) Your Groq API key for using Groq's models.

If no API keys are provided, the tool defaults to using the local Ollama API, for which you must have Ollama installed and running.

If no output file is specified, a temporary directory will be created to save the generated `README.md`, currently set to `/tmp/generated_readme`.

## Ollama

Download and install Ollama from the official website: [Ollama](https://ollama.com/download)

Once installed, pull the default model:

```bash
ollama pull llama3.2:3b
```

Or pull a model that fits your needs and modify the `generate_with_ollama` function in `main.py` and update the `model` parameter accordingly. Since different models have different context window sizes, you may need to adjust the `num_ctx` option in the `generate_with_ollama` function.

The bigger the context window the bigger the AI's memory and ability to understand codebase. However, larger models also require more computational resources and may take longer to generate responses.

```python
data = {
    'model': <model_name>,
    ...
    'options': {
        'num_ctx': <context_window_size>
    }
}
```

## System Prompt

The system prompt is used to set the context for the conversation. It should be a concise and informative statement that helps guide the AI's responses.

If you would like to modify the system prompt, you can do so by changing the `SYSTEM_PROMPT` variable in the `system_prompt.py` file.

## Filtering

The filtering data structure would have to be updated depending on the specific requirements of your application. The current implementation is based on a simple set of strings that are filtered out from the generated text.

If a file, or extension or directory are not filtered out, they will be included in the final output and might lead to unexpected results like `Request too large for <model>`.