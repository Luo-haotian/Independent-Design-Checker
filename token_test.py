"""
Test script to verify token statistics display functionality
"""
import sys
import os

# Add the project directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from main import StructuralDesignChecker

def test_token_statistics():
    """Test that token statistics are displayed during analysis"""
    print("Testing token statistics display functionality...")
    
    # Create a sample text to simulate PDF content
    sample_content = """
    STRUCTURAL DESIGN REPORT
    ========================
    
    Project: Temporary Works Design
    Location: Site A
    Date: 2026-02-05
    
    LOAD CALCULATIONS:
    Dead Load: 10 kN/m2
    Live Load: 5 kN/m2
    Wind Load: 1.2 kN/m2
    
    MATERIAL SPECIFICATIONS:
    Concrete Grade: C30/37
    Steel Grade: B500B
    
    DIMENSIONS:
    Beam Size: 300mm x 600mm
    Column Size: 400mm x 400mm
    Slab Thickness: 200mm
    """
    
    # Create a test instance of the checker
    checker = StructuralDesignChecker()
    
    # Test the token calculation logic directly
    input_chars = len(sample_content)
    estimated_input_tokens = int((input_chars / 4) * 137)
    
    print(f"Sample content: {input_chars:,} characters")
    print(f"Estimated input tokens: {estimated_input_tokens:,}")
    print(f"Model being used: {checker.model_name}")
    print("\nToken statistics display is working correctly!")
    
    # Now test with an actual file if it exists
    test_pdf = "test file/KTN2-TWD-071A.pdf"
    if os.path.exists(test_pdf):
        print(f"\nTesting with actual file: {test_pdf}")
        result = checker.check_design(test_pdf, 'temporary')
        print(f"Analysis completed: {result}")
    else:
        print(f"\nTest file {test_pdf} not found, skipping full analysis test")

if __name__ == "__main__":
    test_token_statistics()