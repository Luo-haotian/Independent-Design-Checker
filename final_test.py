from main import StructuralDesignChecker
import os

# Create reports directory
os.makedirs('./reports', exist_ok=True)

print("Testing with 'building' structure type...")

checker = StructuralDesignChecker()
# Using a shorter timeout and simplified analysis to test the full pipeline
success = checker.check_design(r'test file\KTN2-TWD-071A.pdf', 'building')

if success:
    print('\nSUCCESS: Analysis completed and report generated!')
    
    # Show the generated report
    report_path = r'test file\KTN2-TWD-071A_analysis_report.txt'
    if os.path.exists(report_path):
        print(f'\nGenerated report content:')
        with open(report_path, 'r', encoding='utf-8') as f:
            content = f.read()
            print(content)
            
        print(f'\nReport saved to: {report_path}')
else:
    print('\nFAILED: Analysis did not complete successfully')
    
    # Let's try with temporary structure type as well
    print("\nTrying with 'temporary' structure type...")
    success2 = checker.check_design(r'test file\KTN2-TWD-071A.pdf', 'temporary')
    if success2:
        print('SUCCESS: Analysis with temporary structure type completed!')
        temp_report_path = r'test file\KTN2-TWD-071A_analysis_report.txt'
        if os.path.exists(temp_report_path):
            print(f'\nGenerated report content:')
            with open(temp_report_path, 'r', encoding='utf-8') as f:
                content = f.read()
                print(content)
    else:
        print('FAILED: Analysis with temporary structure type also failed')