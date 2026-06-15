from __future__ import annotations

import re


MIN_TEXT_LENGTH = 50


def clean_text(raw_text: str) -> str:
    text = raw_text.replace('\x00', ' ')
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r'([=_\-])\1{4,}', r'\1\1\1', text)
    lines = [line.strip() for line in text.splitlines()]
    return chr(10).join(line for line in lines if line)


def is_text_sufficient(cleaned_text: str) -> bool:
    return len(cleaned_text.strip()) >= MIN_TEXT_LENGTH
