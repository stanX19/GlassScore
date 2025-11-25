from typing import Dict, Any
from langchain_core.messages import HumanMessage
from src.services.file_parser import parse_file_content
from src.llm.rotating_llm import rotating_llm


async def extract_structured_data(
    base64_content: str,
    mime_type: str,
    schema: str | dict
) -> Dict[str, Any]:
    """
    Extract structured data from a file or image using LLM with a provided schema.
    
    Args:
        base64_content: Base64-encoded file/image content
        mime_type: MIME type of the file/image
        schema: JSON schema or prompt describing the expected output structure.
                If dict, will be converted to a prompt string.
    
    Returns:
        {
            "success": bool,
            "error": str | None,
            "data": dict | None  # Extracted structured data following the schema
        }
    """
    try:
        # Prepare schema prompt
        if isinstance(schema, dict):
            schema_prompt = f"Extract data following this JSON schema:\n{schema}"
        else:
            schema_prompt = schema
        
        # Handle images vs text files differently
        if mime_type.startswith("image/"):
            # For images, create a HumanMessage with multimodal content
            # First ask the LLM to describe what it sees to help with extraction
            instruction_prompt = schema_prompt
            
            print("=" * 80)
            print("IMAGE EXTRACTION - PREPARING MESSAGE")
            print("=" * 80)
            print(f"MIME Type: {mime_type}")
            print(f"Base64 length: {len(base64_content)} characters")
            print(f"Base64 preview: {base64_content[:100]}...")
            print(f"Instruction prompt length: {len(instruction_prompt)} characters")
            print("=" * 80)
            
            messages = [
                HumanMessage(
                    content=[
                        {"type": "text", "text": instruction_prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:{mime_type};base64,{base64_content}"}
                        }
                    ]
                )
            ]
            
            print(f"Created HumanMessage object: {type(messages[0])}")
            print(f"Message content type: {type(messages[0].content)}")
            print(f"Message content length: {len(messages[0].content)}")
            print(f"Message content structure: {[(item['type'], len(str(item))) for item in messages[0].content]}")
            print("=" * 80)
        else:
            # For text files, extract text first
            text_content = parse_file_content(base64_content, mime_type)
            
            # Construct extraction prompt
            messages = f"""{schema_prompt}

Extract the relevant information from the following document and return it as a JSON object.
If a field cannot be found or determined, use null for that field.

Document content:
{text_content}

Return only the JSON object, no additional text or explanation."""
        
        # Use rotating LLM to extract structured data
        result = await rotating_llm.send_message(
            messages=messages,
            temperature=0.3  # Slightly higher temperature for better extraction
        )
        
        # Debug: Print raw LLM output
        print("=" * 80)
        print("LLM EXTRACTION DEBUG")
        print("=" * 80)
        print(f"Status: {result.get('status')}")
        print(f"Model: {result.get('model')}")
        print(f"Raw text output:\n{result.get('text', 'N/A')}")
        print("=" * 80)
        
        if result["status"] != "ok":
            return {
                "success": False,
                "error": f"LLM extraction failed: {result.get('text', 'Unknown error')}",
                "data": None
            }
        
        # Extract JSON from response
        raw_text = result.get('text', '')
        
        # Try to parse JSON from response
        import re
        import json
        
        # Try try_get_json first (handles ```json``` wrapper)
        parsed_json = rotating_llm.try_get_json(raw_text)
        
        if parsed_json is None:
            # Fallback: try direct JSON parse
            try:
                parsed_json = json.loads(raw_text)
            except json.JSONDecodeError as e:
                print(f"JSON parse error: {e}")
                return {
                    "success": False,
                    "error": f"Failed to parse JSON from LLM response: {str(e)}",
                    "data": None
                }
        
        print(f"Parsed JSON successfully: {parsed_json}")
        print("=" * 80)
        
        return {
            "success": True,
            "error": None,
            "data": parsed_json
        }
        
    except ValueError as e:
        # File parsing error
        return {
            "success": False,
            "error": f"File parsing error: {str(e)}",
            "data": None
        }
    except Exception as e:
        # Unexpected error
        return {
            "success": False,
            "error": f"Extraction error: {str(e)}",
            "data": None
        }
