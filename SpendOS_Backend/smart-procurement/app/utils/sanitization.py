import re
import html

def sanitize_for_llm(text: str | None) -> str | None:
    """
    Strips dangerous characters, markdown blocks, and known prompt injection phrases 
    from user input before passing it to LLM processing.
    """
    if text is None:
        return None
        
    original_text = str(text)
    
    # 1. Unescape HTML to ensure we don't fall for obfuscated injections
    clean_text = html.unescape(original_text)
    
    # 2. Strip Markdown code blocks (```...```) and inline code (`...`)
    # Attackers often use fences to break out of template strings.
    clean_text = re.sub(r'```.*?```', '', clean_text, flags=re.DOTALL)
    clean_text = re.sub(r'`.*?`', '', clean_text)
    
    # 3. Strip suspicious prompt engineering instructions
    # We use a case-insensitive match for common phrases
    suspicious_patterns = [
        r"ignore previous instructions",
        r"ignore all previous instructions",
        r"forget previous instructions",
        r"system prompt",
        r"you are now a",
        r"override instructions",
        r"bypass rules",
        r"do not follow",
        r"ignore rules"
    ]
    
    for pattern in suspicious_patterns:
        clean_text = re.sub(pattern, "", clean_text, flags=re.IGNORECASE)
        
    # 4. Remove excessive consecutive newlines and spaces that might be used to flush the context window
    clean_text = re.sub(r'\n{3,}', '\n\n', clean_text)
    clean_text = re.sub(r' {4,}', '   ', clean_text)
    
    # 5. Remove invisible control characters (except newline, tab)
    clean_text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', clean_text)
    
    return clean_text.strip()


def clean_llm_output(text: str) -> str:
    """
    Robust utility to extract the primary JSON object from LLM string outputs.
    Handles markdown fences, conversational prefix/suffix text, and whitespace.
    """
    if not text:
        return ""

    # Use regex to find the content between the first { and the last }
    # re.DOTALL is critical to match across newlines.
    match = re.search(r'(\{.*\})', text, re.DOTALL)
    if match:
        return match.group(1).strip()

    # Fallback to simple strip if no braces found (likely to fail json.loads, but safe)
    return text.strip()
