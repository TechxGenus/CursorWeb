import re
import difflib
import Levenshtein
from special_tokens import *
from search_and_replace import find_best_match

def decorate_code(code, lang="", use_line_num=False, start_line=None, end_line=None):
    """
    Decorates the given code with markdown syntax.

    Args:
        code (str): The code to be decorated.
        lang (str, optional): The language identifier for syntax highlighting. Defaults to "".
        use_line_num (bool, optional): Whether to include line numbers. Defaults to False.
        start_line (int, optional): The starting line number. Defaults to None.
        end_line (int, optional): The ending line number. Defaults to None.

    Returns:
        str: The decorated code.

    """
    decorate = "```"
    if lang:
        decorate += lang.lower()
    decorate += "\n"
    code_lines = code.split("\n")
    if start_line is None:
        start_line = 0
    if end_line is None:
        end_line = len(code_lines)
    if start_line != 0:
        decorate += "...\n"
    if use_line_num:
        decorate += "\n".join([f"{i + 1 + start_line} {line}" for i, line in enumerate(code_lines[start_line: end_line])])
    else:
        decorate += "\n".join(code_lines[start_line: end_line])
    if end_line != len(code_lines):
        decorate += "\n..."
    decorate += "\n```"
    return decorate

def postprocess_output_wf(current, output):
    """
    Processes the given output string to extract a specific section of text 
    between defined markers and returns the first match found.

    Args:
        current (str): The current string to return in case of an error.
        output (str): The output string to be processed.

    Returns:
        str: The extracted section of text if found, otherwise returns the 
        current string.

    Raises:
        Exception: If an error occurs during processing, the exception is 
        caught and the current string is returned.
    """
    try:
        output = output.split(NEXT_START)[-1].split(NEXT_END)[0]
        pattern = r"```(.*?)\n([\s\S]*?)\n```"
        wf = re.findall(pattern, output)
        return wf[0][1]
    except Exception as e:
        print(e)
        return current

def postprocess_output_lc(current, output):
    """
    Post-processes the output by extracting and applying code modifications to the current code.

    Args:
        current (str): The current code as a string.
        output (str): The output containing the modifications.

    Returns:
        str: The updated code after applying the modifications.

    The function expects the `output` to contain code modifications in a specific format:
    - The modifications are enclosed between `NEXT_START` and `NEXT_END` markers.
    - Each modification block follows the pattern: `start_line,end_line\n```<language>\n<code>\n````
    - `start_line` and `end_line` specify the line range in the current code to be replaced by `<code>`.

    If an error occurs during processing, the function prints the exception and returns the original `current` code.
    """
    try:
        output = output.split(NEXT_START)[-1].split(NEXT_END)[0].strip()
        pattern = r"(\d+),(\d+)\n```(.*?)\n([\s\S]*?)\n```"
        lc = re.findall(pattern, output)
        current_lines = current.split("\n")
        for start_line, end_line, _, code in lc[::-1]:
            start_line = int(start_line)
            end_line = int(end_line)
            current_lines = current_lines[:start_line] + code.split("\n") + current_lines[end_line:]
        return "\n".join(current_lines)
    except Exception as e:
        print(e)
        return current

def postprocess_output_sr(current, output):
    """
    Post-processes the output string by extracting and applying search-and-replace operations.

    Args:
        current (str): The current string content to be modified.
        output (str): The output string containing the search-and-replace instructions.

    Returns:
        str: The modified string after applying the search-and-replace operations.

    The function performs the following steps:
    1. Extracts the relevant portion of the output string between NEXT_START and NEXT_END markers.
    2. Finds all code blocks within the extracted portion using a regular expression pattern.
    3. For each code block, splits it into 'before' and 'after' parts using the SEARCH_AND_REPLACE marker.
    4. Finds the best match for the 'before' part in the current string.
    5. Replaces the matched portion in the current string with the 'after' part.
    6. Returns the modified string.

    If an exception occurs during processing, the function prints the exception and returns the original current string.
    """
    try:
        output = output.split(NEXT_START)[-1].split(NEXT_END)[0].strip()
        pattern = r"```(.*?)\n([\s\S]*?)\n```"
        sr = re.findall(pattern, output)
        current_lines = current.split("\n")
        for _, before_and_after in sr[::-1]:
            before, after = before_and_after.split("\n" + SEARCH_AND_REPLACE + "\n")
            match_before = find_best_match(before, current)
            current_lines = current_lines[:match_before.start] + after.split("\n") + current_lines[match_before.end:]
        return "\n".join(current_lines)
    except Exception as e:
        print(e)
        return current

def markdown_codeblock_extract(response):
    """
    Extracts the first code block from a markdown-formatted string.

    Args:
        response (str): The markdown-formatted string containing the code block.

    Returns:
        str: The extracted code block as a string. If no code block is found, returns an empty string.
    """
    lines = response.split("\n")
    code = ""
    in_codeblock = False
    for ln in lines:
        if ln.startswith("```"):
            if in_codeblock:
                break
            else:
                in_codeblock = True
        elif in_codeblock:
            code += ln + "\n"
    return code

def if_continuous_modify(code1, code2, code3):
    """
    Check if code3 is a continuous modification of code1 and code2.

    Args:
        code1 (str): The first code string.
        code2 (str): The second code string.
        code3 (str): The third code string.

    Returns:
        bool: True if code3 is a continuous modification of code1 and code2, False otherwise.
    """
    # Calculate the Levenshtein distance between code1 and code2
    dist1 = Levenshtein.distance(code1, code2)
    # Calculate the Levenshtein distance between code2 and code3
    dist2 = Levenshtein.distance(code2, code3)
    # Calculate the Levenshtein distance between code1 and code3
    dist3 = Levenshtein.distance(code1, code3)

    # Check if code3 is a continuous modification of code1 and code2
    if dist3 == dist1 + dist2:
        return True
    else:
        return False

def blockwise_if_continuous_modify(code1, code2, code3):
    """
    Check if code3 is a continuous modification of code1 and code2.

    Args:
        code1 (str): The first code string.
        code2 (str): The second code string.
        code3 (str): The third code string.

    Returns:
        bool: True if code3 is a continuous modification of code1 and code2, False otherwise.
    """
    # Calculate the Levenshtein distance between code1 and code2
    dist1 = Levenshtein.distance(code1, code2)
    # Calculate the Levenshtein distance between code2 and code3
    dist2 = Levenshtein.distance(code2, code3)
    # Calculate the Levenshtein distance between code1 and code3
    dist3 = Levenshtein.distance(code1, code3)

    past_diff_blocks = generate_diff_blocks(code1, code2)
    new_diff_blocks = generate_diff_blocks(code1, code3)
    
    # Check if code3 is a continuous modification of code1 and code2
    if dist3 == dist1 + dist2 and len(past_diff_blocks) == len(new_diff_blocks):
        return True
    else:
        return False

def generate_diff_blocks(original, modified):
    """
    Generate diff blocks between two strings.

    Args:
        original (str): The original string.
        modified (str): The modified string.

    Returns:
        list: A list of tuples, where each tuple contains a block of modified lines and the line number in the original string where the block starts.
    """
    # Use difflib's ndiff to find differences
    differ = difflib.Differ()
    diff = list(differ.compare(original.split('\n'), modified.split('\n')))
    
    # store all modified blocks
    blocks = []
    current_block = []
    
    # track the current line number
    orig_line_no = 0
    block_line_len = 0

    # Traverse the diff results into chunks
    for line in diff:
        if line.startswith('  '):
            # If the current block has content and an unmodified line is encountered, save the current block and reset
            if current_block:
                blocks.append((current_block, orig_line_no - block_line_len))
                current_block = []
                block_line_len = 0
            orig_line_no += 1
        elif line.startswith('- '):
            current_block.append(line)
            orig_line_no += 1
            block_line_len += 1
        else:
            current_block.append(line)
    
    # Make sure the last chunk is added
    if current_block:
        blocks.append((current_block, orig_line_no - block_line_len))
    
    return blocks
