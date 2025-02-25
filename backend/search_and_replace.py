# Ref: https://github.com/sweepai/sweep/blob/main/sweepai/utils/search_and_replace.py

import re
from dataclasses import dataclass
from functools import lru_cache

from rapidfuzz import fuzz
from tqdm import tqdm


@lru_cache()
def score_line(str1: str, str2: str) -> float:
    if str1 == str2:
        return 100

    if str1.lstrip() == str2.lstrip():
        whitespace_ratio = abs(len(str1) - len(str2)) / (len(str1) + len(str2))
        score = 90 - whitespace_ratio * 10
        return max(score, 0)

    if str1.strip() == str2.strip():
        whitespace_ratio = abs(len(str1) - len(str2)) / (len(str1) + len(str2))
        score = 80 - whitespace_ratio * 10
        return max(score, 0)

    levenshtein_ratio = fuzz.ratio(str1, str2)

    score = 85 * (levenshtein_ratio / 100)
    return max(score, 0)


def match_without_whitespace(str1: str, str2: str) -> bool:
    return str1.strip() == str2.strip()


def line_cost(line: str) -> float:
    if line.strip() == "":
        return 50
    if line.strip().startswith("#") or line.strip().startswith("//"):
        return 50 + len(line) / (len(line) + 1) * 30
    return len(line) / (len(line) + 1) * 100


def score_multiline(query: list[str], target: list[str]) -> float:
    # TODO: add weighting on first and last lines

    q, t = 0, 0  # indices for query and target
    scores: list[tuple[float, float]] = []
    skipped_comments = 0

    def get_weight(q: int) -> float:
        # Prefers lines at beginning and end of query
        # Sequence: 1, 2/3, 1/2, 2/5...
        index = min(q, len(query) - q)
        return 100 / (index / 2 + 1)

    while q < len(query) and t < len(target):
        q_line = query[q]
        t_line = target[t]
        weight = get_weight(q)

        if match_without_whitespace(q_line, t_line):
            # Case 1: lines match
            scores.append((score_line(q_line, t_line), weight))
            q += 1
            t += 1
        elif q_line.strip().startswith("...") or q_line.strip().endswith("..."):
            # Case 3: ellipsis wildcard
            t += 1
            if q + 1 == len(query):
                scores.append((100 - (len(target) - t), weight))
                q += 1
                t = len(target)
                break
            max_score = 0
            # Radix optimization
            indices = [
                t + i
                for i, line in enumerate(target[t:])
                if match_without_whitespace(line, query[q + 1])
            ]
            if not indices:
                indices = range(t, len(target))
            for i in indices:
                score, weight = score_multiline(query[q + 1 :], target[i:]), (
                    100 - (i - t) / len(target) * 10
                )
                new_scores = scores + [(score, weight)]
                total_score = sum(
                    [value * weight for value, weight in new_scores]
                ) / sum([weight for _, weight in new_scores])
                max_score = max(max_score, total_score)
            return max_score
        elif (
            t_line.strip() == ""
            or t_line.strip().startswith("#")
            or t_line.strip().startswith("//")
            or t_line.strip().startswith("print")
            or t_line.strip().startswith("logger")
            or t_line.strip().startswith("console.")
        ):
            # Case 2: skipped comment
            skipped_comments += 1
            t += 1
            scores.append((90, weight))
        else:
            break

    if q < len(query):
        scores.extend(
            (100 - line_cost(line), get_weight(index))
            for index, line in enumerate(query[q:])
        )
    if t < len(target):
        scores.extend(
            (100 - line_cost(line), 100) for index, line in enumerate(target[t:])
        )

    final_score = (
        sum([value * weight for value, weight in scores])
        / sum([weight for _, weight in scores])
        if scores
        else 0
    )
    final_score *= 1 - 0.05 * skipped_comments

    return final_score


@dataclass
class Match:
    start: int
    end: int
    score: float
    indent: str = ""

    def __gt__(self, other):
        return self.score > other.score


def get_indent_type(content: str):
    two_spaces = len(re.findall(r"\n {2}[^ ]", content))
    four_spaces = len(re.findall(r"\n {4}[^ ]", content))

    return "  " if two_spaces > four_spaces else "    "


def get_max_indent(content: str, indent_type: str):
    return max(len(line) - len(line.lstrip()) for line in content.split("\n")) // len(
        indent_type
    )

# Bug: raise "not enough values to unpack (expected 2, got 1)" for some inputs
def find_best_match(query: str, code_file: str):
    best_match = Match(-1, -1, 0)

    code_file_lines = code_file.split("\n")
    query_lines = query.split("\n")
    if len(query_lines) > 0 and query_lines[-1].strip() == "...":
        query_lines = query_lines[:-1]
    if len(query_lines) > 0 and query_lines[0].strip() == "...":
        query_lines = query_lines[1:]
    indent = get_indent_type(code_file)
    max_indents = get_max_indent(code_file, indent)

    top_matches = []

    if len(query_lines) == 1:
        for i, line in enumerate(code_file_lines):
            score = score_line(line, query_lines[0])
            if score > best_match.score:
                best_match = Match(i, i + 1, score)
        return best_match

    truncate = min(40, len(code_file_lines) // 5)
    if truncate < 1:
        truncate = len(code_file_lines)

    indent_array = [i for i in range(0, max(min(max_indents + 1, 20), 1))]
    if max_indents > 3:
        indent_array = [3, 2, 4, 0, 1] + list(range(5, max_indents + 1))
    for num_indents in indent_array:
        indented_query_lines = [indent * num_indents + line for line in query_lines]

        start_pairs = [
            (i, score_line(line, indented_query_lines[0]))
            for i, line in enumerate(code_file_lines)
        ]
        start_pairs.sort(key=lambda x: x[1], reverse=True)
        start_pairs = start_pairs[:truncate]
        start_indices = [i for i, _ in start_pairs]

        for i in tqdm(
            start_indices,
            position=0,
            desc=f"Indent {num_indents}/{max_indents}",
            leave=False,
        ):
            end_pairs = [
                (j, score_line(line, indented_query_lines[-1]))
                for j, line in enumerate(code_file_lines[i:], start=i)
            ]
            end_pairs.sort(key=lambda x: x[1], reverse=True)
            end_pairs = end_pairs[:truncate]
            end_indices = [j for j, _ in end_pairs]

            for j in tqdm(
                end_indices, position=1, leave=False, desc=f"Starting line {i}"
            ):
                candidate = code_file_lines[i : j + 1]
                raw_score = score_multiline(indented_query_lines, candidate)

                score = raw_score * (1 - num_indents * 0.01)
                current_match = Match(i, j + 1, score, indent * num_indents)

                if raw_score >= 99.99:  # early exit, 99.99 for floating point error
                    return current_match

                top_matches.append(current_match)

                if score > best_match.score:
                    best_match = current_match

    unique_top_matches: list[Match] = []
    unique_spans = set()
    for top_match in sorted(top_matches, reverse=True):
        if (top_match.start, top_match.end) not in unique_spans:
            unique_top_matches.append(top_match)
            unique_spans.add((top_match.start, top_match.end))

    # Todo: on_comment file comments able to modify multiple files
    return unique_top_matches[0] if unique_top_matches else Match(-1, -1, 0)


def split_ellipses(query: str) -> list[str]:
    queries = []
    current_query = ""
    for line in query.split("\n"):
        if line.strip() == "...":
            queries.append(current_query.strip("\n"))
            current_query = ""
        else:
            current_query += line + "\n"
    queries.append(current_query.strip("\n"))
    return queries


def match_indent(generated: str, original: str) -> str:
    indent_type = "\t" if "\t" in original[:5] else " "
    generated_indents = len(generated) - len(generated.lstrip())
    target_indents = len(original) - len(original.lstrip())
    diff_indents = target_indents - generated_indents
    if diff_indents > 0:
        generated = indent_type * diff_indents + generated.replace(
            "\n", "\n" + indent_type * diff_indents
        )
    return generated
