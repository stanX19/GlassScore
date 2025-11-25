"""
Service for parsing and preparing file content for chatbot/LLM consumption.
Handles both text extraction from documents and image message preparation.
"""
from src.llm.chatbot.file_utils import extract_text_from_base64


def parse_file_content(base64_content: str, mime_type: str) -> str:
    """
    Extract text content from a base64-encoded file.
    
    Args:
        base64_content: Base64-encoded file content
        mime_type: MIME type of the file
    
    Returns:
        Extracted text content
    
    Raises:
        ValueError: If file type is unsupported or extraction fails
    """
    return extract_text_from_base64(base64_content, mime_type)


def prepare_image_message(base64_content: str, mime_type: str) -> dict:
    """
    Prepare an image attachment in multimodal message format.
    
    Args:
        base64_content: Base64-encoded image content
        mime_type: MIME type of the image (must start with 'image/')
    
    Returns:
        Message dict in LangChain multimodal format
    
    Raises:
        ValueError: If mime_type is not an image type
    """
    if not mime_type.startswith("image/"):
        raise ValueError(
            f"prepare_image_message requires an image MIME type (image/*), got '{mime_type}'"
        )
    
    return {
        "role": "user",
        "content": [
            {
                "type": "image_url",
                "image_url": {"url": f"data:{mime_type};base64,{base64_content}"}
            }
        ]
    }


def prepare_file_message(base64_content: str, mime_type: str) -> dict:
    """
    Prepare a file attachment as a text message with extracted content.
    
    Args:
        base64_content: Base64-encoded file content
        mime_type: MIME type of the file
    
    Returns:
        Message dict with extracted text content
    
    Raises:
        ValueError: If text extraction fails
    """
    extracted_text = parse_file_content(base64_content, mime_type)
    file_description = f"[Attached file content ({mime_type})]:\n\n"
    
    return {
        "role": "user",
        "content": file_description + extracted_text
    }
