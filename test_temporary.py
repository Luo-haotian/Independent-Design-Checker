from main import StructuralDesignChecker
import os

checker = StructuralDesignChecker()

print("Testing with 'temporary' structure type...")
# Create a new report with a different name for the temporary structure analysis
success = checker.check_design(r'test file\KTN2-TWD-071A.pdf', 'temporary')

if success:
    print('\nSUCCESS: Analysis with temporary structure type completed!')
    
    # Show the generated report
    report_path = r'test file\KTN2-TWD-071A_analysis_report.txt'
    if os.path.exists(report_path):
        print(f'\nGenerated report content for temporary structure:')
        with open(report_path, 'r', encoding='utf-8') as f:
            content = f.read()
            print(content)
            
        print(f'\nReport saved to: {report_path}')
else:
    print('\nFAILED: Analysis with temporary structure type also failed')