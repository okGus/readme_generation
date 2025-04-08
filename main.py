#!/usr/bin/env python3
import argparse
import os
import sys
import json
import uuid
from typing import Dict, Optional

import requests

from tqdm import tqdm

# Ollama API
from ollama import chat, ChatResponse

# Gemini API
from google import genai
from google.genai import types

# OpenAI API, Groq API Key is OpenAI compatible
from openai import OpenAI

from system_prompt import SYSTEM_PROMPT

# When reading the codebase I want to ignore the following since they are not relevant
# and are to big, might have to research to make sure that I'm getting most languages and frameworks
# like python, rust, go, javascript, next.js projects etc.
# If virtual environment name is not in IGNORE_DIRS then the prompt_content will be filled
# with useless files that we don't want. And we might get errors like response headers too big
IGNORE_DIRS = {'.venv', 'venv', 'myenv', '__pycache__', 'node_modules', 'build', 'dist',
               'target', '.codecrafters', '.next'}
IGNORE_EXTENSIONS = {'.o', '.dll', '.exe', '.yml'}
IGNORE_FILES = {'Cargo.lock', 'Cargo.toml', 'package-lock.json', 'requirements.txt'}

def read_codebase(directory_path: str) -> Dict[str, str]:
    """
    Reads relevant files in the directory and its subdirectories.

    Args:
        directory_path (str): The path to the root directory of the codebase.

    Returns:
        dict[str, str]: A dictionary where keys are relative file paths and values
                        are the content of the files.
                        Returns and empty dict if the directory is invalid.
        bool: A boolean set if a README.md is found in the project directory.
    """
    code_contents = {}

    if not os.path.isdir(directory_path):
        print(f"Error: Directory not found: {directory_path}", file=sys.stderr)

    # print(f"Scanning directory: {directory_path}")

    for root, dirs, files in tqdm(os.walk(directory_path, topdown=True), desc='Scanning directory'):
        # Directory Filtering
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS and not d.startswith('.')]

        relative_root = os.path.relpath(root, directory_path)

        if relative_root == ".":
            relative_root = ""  # Avoid "./filename" -> "filename"

        for filename in files:
            # File Filtering
            if filename in IGNORE_FILES or filename.startswith('.'):
                continue
            _, extension = os.path.splitext(filename)
            if extension in IGNORE_EXTENSIONS:
                continue

            relative_path = os.path.join(relative_root, filename)

            try:
                with open(os.path.join(root, filename),
                          'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    # Store the association
                    code_contents[relative_path] = content
            except Exception as e:
                print(f"Error reading {relative_path}: {e}")

    if not code_contents:
        print("Warning: No relevant files found or read in the specfied directory.",
              file=sys.stderr)

    return code_contents

def format_codebase_for_prompt(code_contents: dict[str, str]):
    """
    Formats the collected codebase content into a single string for an AI prompt.
    """
    if not code_contents:
        return "No code content was read from the directory."

    prompt_string = "Project Files:\n\n"
    for file_path, content in tqdm(code_contents.items(), desc='Formatting'):
        prompt_string += f"--- File: {file_path} ---\n"
        prompt_string += f"```\n{content}\n```\n\n"  # Using ``` for code blocks

    return prompt_string

# Issues?
def generate_with_ollama_api(formatted_prompt_content: str) -> str:
    response: ChatResponse = chat(
        model='llama3.2:3b',
        messages=[
            {'role': 'system', 'content': SYSTEM_PROMPT},
            {'role': 'user', 'content': formatted_prompt_content},
        ],
        stream=False,
        options={
            'num_ctx': 128000  # Max context window for gemma3 4b
        }
    )
    res = response['message']['content']
    return res

def generate_with_ollama(formatted_prompt_content: str) -> str:
    url = 'http://localhost:11434/api/chat'
    data = {
        'model': 'llama3.2:3b',
        'messages': [
            {'role': 'system', 'content': SYSTEM_PROMPT},
            {'role': 'user', 'content': formatted_prompt_content},
        ],
        'stream': False,
        'options': {
            'num_ctx': 64000  # Half max context window for gemma3 4b
        }
    }
    headers = {'Content-Type': 'application/json'}

    try:
        response = requests.post(url, json=data, headers=headers)

        # Check for HTTP errors (like 404, 500, etc.)
        response.raise_for_status()

        res = response.json()

        if 'message' in res and 'content' in res['message']:
            print('\n', res['message']['content'], '\n')
            return res['message']['content']

        print("Unexpected JSON structure in response.")
        print(res)
        return ""
    except requests.exceptions.Timeout:
        print("Timed out")
        return ""
    except requests.exceptions.RequestException as e:
        print(f"Error during Ollama request {e}")
        return ""
    except json.JSONDecodeError:
        print("Error: Failed to decode JSON response.")
        return ""

def clean_ai_output(ai_response_string: str) -> str:
    """
    Removes ```markdown fences from the start and end of an AI response string.

    Args:
        ai_response_string: The response string from the AI.

    Returns:
        The cleaned string, potentially the same as the input if no fences were found.
    """
    if not ai_response_string:
        return ""

    lines = ai_response_string.splitlines(keepends=True)

    if not lines:
        return ""

    starts_with_fence = False
    ends_with_fence = False

    first_line_stripped = lines[0].strip()
    last_line_stripped = lines[-1].strip()

    if first_line_stripped.lower() == "```markdown" or first_line_stripped == "```":
        starts_with_fence = True
    if starts_with_fence and last_line_stripped.lower() == "```":
        ends_with_fence = True

    cleaned_lines = lines

    if starts_with_fence and ends_with_fence and len(lines) >= 2:
        cleaned_lines = lines[1:-1]

    cleaned_response = "".join(cleaned_lines)

    return cleaned_response

def generate_with_gemini(prompt_content: str, gemini_api_key: str) -> str:
    client = genai.Client(api_key=gemini_api_key)

    response = client.models.generate_content(
        model='gemini-2.0-flash',
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT
        ),
        contents=prompt_content
    )

    content: Optional[str] = response.text
    if not content:
        raise ValueError("The response content is None.")

    return content

def generate_with_openai(prompt_content: str, openai_api_key: str) -> str:
    client = OpenAI(api_key=openai_api_key)

    response = client.chat.completions.create(
        model='gpt-4o-mini',
        messages=[
            {'role': 'system', 'content': SYSTEM_PROMPT},
            {'role': 'user', 'content': prompt_content},
        ],
    )

    content: Optional[str] = response.choices[0].message.content
    if not content:
        raise ValueError("The response content is None.")

    return content

def generate_with_groq(prompt_content: str, groq_api_key: str) -> str:
    client = OpenAI(base_url='https://api.groq.com/openai/v1',
                    api_key=groq_api_key)

    response = client.chat.completions.create(
        model='llama-3.3-70b-versatile',
        messages=[
            {'role': 'system', 'content': SYSTEM_PROMPT},
            {'role': 'user', 'content': prompt_content},
        ],
    )

    content: Optional[str] = response.choices[0].message.content
    if not content:
        raise ValueError("The response content is None.")

    return content

def handle_generation(prompt_content: str,
                      gemini_api_key: str | None,
                      openai_api_key: str | None,
                      groq_api_key: str | None) -> str:
    # Handle generating README.md with AI models like Gemini, ChatGPT, etc, given their API keys
    if gemini_api_key:
        return generate_with_gemini(prompt_content, gemini_api_key)
    if openai_api_key:
        return generate_with_openai(prompt_content, openai_api_key)
    if groq_api_key:
        return generate_with_groq(prompt_content, groq_api_key)

    print('\n', prompt_content, '\n')
    # Default is Ollama API, local
    return generate_with_ollama(prompt_content)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generate readme')
    parser.add_argument('-d', '--directory',
                        metavar='path',
                        type=str,
                        required=True,
                        help='Path to the project directory')
    parser.add_argument('-o', '--output_file',
                        metavar='output_file',
                        type=str,
                        help='Optional: File path to save the formatted prompt content')
    parser.add_argument('--gemini-api-key',
                        metavar='gemini_api_key',
                        type=str,
                        help='Optional: Gemini API Key to access Google\'s AI models')
    parser.add_argument('--openai-api-key',
                        metavar='openai_api_key',
                        type=str,
                        help='Optional: OpenAI API Key to access OpenAI\'s models')
    parser.add_argument('--groq-api-key',
                        metavar='groq_api_key',
                        type=str,
                        help='Optional: Groq API Key to access other larger models')

    args = parser.parse_args()
    target_dir = args.directory
    output_file = args.output_file
    gemini_api_key = args.gemini_api_key
    openai_api_key = args.openai_api_key
    groq_api_key = args.groq_api_key

    # Read codebase files
    code_data = read_codebase(target_dir)

    if code_data:
        # Format the data for the prompt
        formatted_prompt_content = format_codebase_for_prompt(code_data)

        # Generate README.md
        generated_readme = handle_generation(formatted_prompt_content,
                                             gemini_api_key,
                                             openai_api_key,
                                             groq_api_key)
        # Clean up AI output as it might start the markdown file with ```markdown
        # and end with ``` even thought it should be the raw content
        raw_readme = clean_ai_output(generated_readme)

        if output_file:
            print(output_file)
            # Generate readme with AI and save to output_file
            try:
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(raw_readme)
                    print(f"\nGenerated README.md saved to {output_file}")
            except IOError as e:
                print(f"\nError writing to output file {output_file}: {e}", file=sys.stderr)
        else:
            # Generate readme with AI and save to /tmp/
            output_dir = '/tmp/generated_readme'
            if not os.path.isdir(output_dir):
                os.makedirs(output_dir)
                print(f"Directory created: {output_dir}")

            output_filename = str(uuid.uuid4()) + '.md'
            output_path = os.path.join(output_dir, output_filename)

            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(raw_readme)
                print(f"\nGenerated README.md saved to {output_path}")
    else:
        print("Could not read any relevant code content.")
