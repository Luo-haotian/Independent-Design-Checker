"""
Simple test to verify that the PDF handling fix works correctly
"""

import sys
import os
sys.path.insert(0, '.')

from main import StructuralDesignChecker

def test_pdf_handling():
    """Test that the PDF handling works correctly"""
    print("Testing PDF handling fix...")
    
    # Path to test PDF
    test_pdf = os.path.join("test file", "KTN2-TWD-071A.pdf")
    
    if not os.path.exists(test_pdf):
        print(f"Test PDF not found: {test_pdf}")
        return False
    
    print(f"Testing with PDF: {test_pdf}")
    
    # Create checker instance
    checker = StructuralDesignChecker()
    
    # Test PDF text extraction
    print("Testing PDF text extraction...")
    content = checker.extract_text_from_pdf(test_pdf)
    
    if content:
        print(f"SUCCESS: Extracted {len(content)} characters from PDF")
        print(f"First 500 chars: {content[:500] if len(content) > 500 else content}")
        return True
    else:
        print("ERROR: Failed to extract content from PDF")
        return False

if __name__ == "__main__":
    success = test_pdf_handling()
    if success:
        print("\nPDF handling fix appears to be working correctly!")
        print("You should now be able to use the GUI to process PDF files.")
    else:
        print("\nThere may still be issues with PDF handling.")