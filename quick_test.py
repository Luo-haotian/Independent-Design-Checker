import os
import sys
sys.path.insert(0, '.')

from main import StructuralDesignChecker
from config import TEMPERATURE

# Create a shorter prompt for quick testing
def quick_analyze():
    checker = StructuralDesignChecker()
    
    # Extract content from PDF
    pdf_path = r'test file\KTN2-TWD-071A.pdf'
    content = checker.extract_text_from_pdf(pdf_path)
    
    if content:
        print(f"Successfully extracted {len(content)} characters from PDF")
        
        # Test API with a very short prompt to see if connection works
        short_prompt = f"Summarize this in 10 words: {content[:500]}"
        
        try:
            payload = {
                "model": "grok-3",
                "messages": [
                    {"role": "user", "content": short_prompt}
                ],
                "max_tokens": 50,
                "temperature": TEMPERATURE
            }
            
            import requests
            headers = {
                "Authorization": f"Bearer {checker.api_key}",
                "Content-Type": "application/json"
            }
            
            print("Making API call to test connection...")
            response = requests.post(
                checker.api_url,
                headers=headers,
                json=payload,
                timeout=10  # Short timeout for testing
            )
            
            print(f"Response status: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                if 'choices' in result:
                    print("API call successful!")
                    print(f"Response: {result['choices'][0]['message']['content'][:100]}...")
                    return True
                else:
                    print(f"Unexpected response format: {result}")
            else:
                print(f"API Error: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"Exception during API call: {str(e)}")
    else:
        print("Failed to extract content from PDF")
    
    return False

if __name__ == "__main__":
    quick_analyze()