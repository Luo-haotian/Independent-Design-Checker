"""
Script to test the GUI with the fixed version
"""
import subprocess
import sys
import os

# Change to the project directory
os.chdir(r"C:\Users\11131\clawd\IDC_Project")

print("Launching IDC GUI to test PDF processing...")
print("Please:")
print("1. Select the PDF file: test file\\KTN2-TWD-071A.pdf")
print("2. Choose either 'Building' or 'Temporary Work' structure type")
print("3. Click 'Check Design'")
print("4. The analysis should now complete successfully!")

# Launch the GUI
subprocess.run([sys.executable, "-c", "import sys; sys.path.insert(0, '.'); from gui import main; main()"])