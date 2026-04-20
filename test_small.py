from main import StructuralDesignChecker

# Create a smaller test to verify functionality
checker = StructuralDesignChecker()

# Extract content from PDF
pdf_path = r'test file\KTN2-TWD-071A.pdf'
content = checker.extract_text_from_pdf(pdf_path)

if content:
    print(f"SUCCESS: PDF content extraction successful ({len(content)} chars)")
    
    # Test with a much smaller prompt to verify the API pipeline
    small_content = content[:300]  # Take only first 300 chars
    
    # Test the API call directly
    prompt = f"""
    Briefly summarize this design calculation excerpt in 2 sentences:
    {small_content}
    """
    
    result = checker.call_grok_api(prompt)
    if result and 'choices' in result:
        response = result['choices'][0]['message']['content']
        print(f"SUCCESS: API call successful!")
        print(f"Sample response: {response[:100]}...")
        
        # Now try a full analysis with shortened content
        print("\nTrying full analysis with shortened content...")
        
        # Override the method temporarily to use shorter content
        def analyze_building_design_short(self, pdf_content: str):
            # Use even less content for testing
            short_content = pdf_content[:500]
            prompt = f"""
            You are an expert structural engineer. Provide a very brief assessment of this building design excerpt:
            {short_content}
            
            Give a 2-line summary of the content.
            """
            
            result = self.call_grok_api(prompt)
            if result and 'choices' in result:
                return result['choices'][0]['message']['content']
            return None
        
        # Temporarily replace the method
        import types
        checker.analyze_building_design = types.MethodType(analyze_building_design_short, checker)
        
        # Now run the check with modified method
        success = checker.check_design(pdf_path, 'building')
        
        if success:
            print("\nSUCCESS: Full analysis pipeline working!")
        else:
            print("\nAnalysis failed")
    else:
        print("API call failed")
else:
    print("PDF content extraction failed")