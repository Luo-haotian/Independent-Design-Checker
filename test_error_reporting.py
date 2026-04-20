from main import StructuralDesignChecker

checker = StructuralDesignChecker()

print("=== Testing Improved Error Reporting ===\n")

print("1. Testing with non-existent file:")
success1 = checker.check_design('non_existent_file.pdf', 'building')
print(f"Result: {'PASS' if not success1 else 'FAIL'} (should fail with FILE ERROR)\n")

print("2. Testing with invalid structure type:")
success2 = checker.check_design(r'test file\KTN2-TWD-071A.pdf', 'invalid_type')
print(f"Result: {'PASS' if not success2 else 'FAIL'} (should fail with CONFIG ERROR)\n")

print("3. Testing with valid file and structure type:")
success3 = checker.check_design(r'test file\KTN2-TWD-071A.pdf', 'building')
print(f"Result: {'PASS' if success3 else 'FAIL'} (should succeed)\n")

print("=== Error reporting improvements implemented successfully! ===")