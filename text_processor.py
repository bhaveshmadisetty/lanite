"""
Text processing utilities for Lanite.

Provides grammar cleanup functions for improving raw speech
transcription output. Note: With Whisper's contextual
understanding, many of these functions are less necessary
than they were with Vosk.

Usage:
    from text_processor import process
    cleaned_text = process(raw_text)
"""

import re


def fix_contractions(text):
    """
    Expand contractions to their full form for consistency.
    
    Note: Whisper typically handles contractions correctly,
    so this function may not be necessary in most cases.
    
    Args:
        text: Input text with potential contractions
        
    Returns:
        Text with expanded contractions
        
    Example:
        >>> fix_contractions("I'm going to the store")
        "I am going to the store"
    """
    replacements = {
        "i'm": "I am",
        "i've": "I have",
        "i'll": "I will",
        "i'd": "I would",
        "don't": "do not",
        "doesn't": "does not",
        "didn't": "did not",
        "can't": "cannot",
        "won't": "will not",
        "it's": "it is",
        "that's": "that is",
        "there's": "there is",
        "he's": "he is",
        "she's": "she is",
        "we're": "we are",
        "they're": "they are",
        "you're": "you are",
    }

    lower_text = text.lower()
    for contraction, expansion in replacements.items():
        if contraction in lower_text:
            # Use regex for word boundary matching
            text = re.sub(
                rf"\b{contraction}\b",
                expansion,
                text,
                flags=re.IGNORECASE
            )

    return text


def remove_fillers(text):
    """
    Remove filler words from transcribed text.
    
    Filler words are common speech patterns that don't add
    meaning to the text and can make it sound less polished.
    
    Args:
        text: Input text with potential filler words
        
    Returns:
        Text with filler words removed
        
    Example:
        >>> remove_fillers("Um, I think, uh, that's right")
        "I think that's right"
    """
    fillers = [
        "um", "uh", "hmm", "er", "ah",
        "like", "you know", "basically",
        "actually", "literally", "sort of"
    ]
    
    for filler in fillers:
        # Remove filler with surrounding whitespace
        text = re.sub(
            rf"\b{filler}\b",
            "",
            text,
            flags=re.IGNORECASE
        )
    
    # Clean up multiple spaces
    text = re.sub(r"\s+", " ", text)
    
    return text.strip()


def remove_repeated_words(text):
    """
    Remove consecutive repeated words.
    
    Speech recognition sometimes captures stuttering or
    emphasis as repeated words.
    
    Args:
        text: Input text with potential repeated words
        
    Returns:
        Text with consecutive duplicates removed
        
    Example:
        >>> remove_repeated_words("I I think that's right")
        "I think that's right"
    """
    return re.sub(r'\b(\w+)( \1\b)+', r'\1', text)


def smart_punctuation(text):
    """
    Add appropriate punctuation based on sentence content.
    
    Analyzes the beginning of the sentence to determine
    if it should end with a question mark or period.
    
    Note: Whisper typically handles punctuation automatically,
    so this is primarily a fallback.
    
    Args:
        text: Input text without terminal punctuation
        
    Returns:
        Text with appropriate ending punctuation
        
    Example:
        >>> smart_punctuation("what time is it")
        "what time is it?"
    """
    text = text.strip()
    
    if not text:
        return ""
    
    # Don't add punctuation if already present
    if text.endswith(('.', '?', '!', ',')):
        return text
    
    # Question words
    question_starters = (
        "who", "what", "when", "where", 
        "why", "how", "is", "are", "do",
        "does", "can", "could", "would",
        "should", "will", "has", "have"
    )
    
    first_word = text.split()[0].lower() if text.split() else ""
    
    if first_word in question_starters:
        text += "?"
    else:
        text += "."
    
    return text


def capitalize_sentences(text):
    """
    Capitalize the first letter of the text.
    
    Args:
        text: Input text potentially starting with lowercase
        
    Returns:
        Text with first character capitalized
        
    Example:
        >>> capitalize_sentences("hello world")
        "Hello world"
    """
    if not text:
        return ""
    return text[0].upper() + text[1:]


def process(text):
    """
    Process text through the complete cleanup pipeline.
    
    Applies all text processing functions in the optimal order:
    1. Remove filler words
    2. Remove repeated words
    3. Fix contractions
    4. Add smart punctuation
    5. Capitalize first letter
    
    Args:
        text: Raw transcribed text
        
    Returns:
        Cleaned and formatted text
        
    Example:
        >>> process("um hello world this is a test")
        "Hello world this is a test."
    """
    if not text:
        return ""
    
    # Apply processing pipeline
    text = remove_fillers(text)
    text = remove_repeated_words(text)
    text = fix_contractions(text)
    text = smart_punctuation(text)
    text = capitalize_sentences(text)
    
    return text.strip()


# === TESTING ===
if __name__ == "__main__":
    # Test cases
    test_cases = [
        "um hello world",
        "I I think that's right",
        "what time is it",
        "the quick brown fox",
        "uh basically this is a test",
    ]
    
    print("Text Processor Test Results:")
    print("-" * 50)
    for test in test_cases:
        result = process(test)
        print(f"Input:  '{test}'")
        print(f"Output: '{result}'")
        print()
