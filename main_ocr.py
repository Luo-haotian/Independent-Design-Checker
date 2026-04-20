"""
IDC - Structural Design Checker with OCR Support
Supports: Grok API (x.ai) or KIMI API (Moonshot)
OCR Engine: pytesseract (requires Tesseract installed)
"""

import os
import sys
import fitz
import requests
import argparse
import logging
from pathlib import Path
from typing import Optional, Tuple
from datetime import datetime
from PIL import Image
import io
import numpy as np

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('idc_ocr.log', encoding='utf-8'), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Load config
from config import (
    API_KEY, API_URL, MODEL_NAME, MODEL_CONFIGS,
    MAX_TOKENS, TEMPERATURE, API_PROVIDER, check_api_key
)

# Try to import OCR libraries
try:
    import pytesseract
    PYTESSERACT_AVAILABLE = True
except ImportError:
    PYTESSERACT_AVAILABLE = False
    logger.warning("pytesseract not installed.")

# Check if Tesseract is installed and configure path
def check_tesseract():
    """Check if Tesseract is installed and set path"""
    if not PYTESSERACT_AVAILABLE:
        return False
    
    # Common Tesseract installation paths
    possible_paths = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        r"C:\Users\{}\AppData\Local\Tesseract-OCR\tesseract.exe".format(os.environ.get('USERNAME', '')),
    ]
    
    # Check if tesseract is in PATH
    try:
        version = pytesseract.get_tesseract_version()
        logger.info(f"Tesseract found in PATH, version: {version}")
        return True
    except:
        # Not in PATH, check common locations
        for path in possible_paths:
            if os.path.exists(path):
                pytesseract.pytesseract.tesseract_cmd = path
                try:
                    version = pytesseract.get_tesseract_version()
                    logger.info(f"Tesseract found at: {path}, version: {version}")
                    return True
                except:
                    continue
        
        logger.warning("Tesseract not found in PATH or common locations")
        return False

TESSERACT_AVAILABLE = check_tesseract()

# Prompts (English for Grok, Chinese for KIMI)
if API_PROVIDER == 'grok':
    BUILDING_PROMPT = """You are an expert structural engineer. Analyze this building design:

Check: Calculations, Structural System, Loading, Materials, Code Compliance, Safety

Output format:
1. Executive Summary
2. Detailed Analysis by Category
3. Calculation Verification Results
4. Issues (Critical/Major/Minor)
5. Overall Compliance Status
6. Recommendations

Design Content:
{content}"""

    TEMPORARY_PROMPT = """You are an expert temporary structure engineer. Analyze this temporary work design:

Check: Calculations, Construction Loads, Safety Measures, Weather Resistance, Duration, Materials

Output format:
1. Executive Summary
2. Detailed Analysis by Category
3. Calculation Verification Results
4. Issues (Critical/Major/Minor)
5. Safety Compliance Status
6. Recommendations

Design Content:
{content}"""
else:
    # KIMI Chinese prompts
    BUILDING_PROMPT = """作为结构工程师，审查建筑设计：

检查：计算验证、结构体系、荷载分析、材料规格、规范符合性、关键构件、安全冗余

输出：1.执行摘要 2.详细分析 3.计算验证结果 4.问题清单 5.总体评价 6.改进建议

设计内容：
{content}"""

    TEMPORARY_PROMPT = """作为临时结构工程师，审查临时工程设计：

检查：计算验证、施工荷载、安全措施、抗风防雨、使用期限、材料连接

输出：1.执行摘要 2.详细分析 3.计算验证结果 4.问题清单 5.安全评价 6.改进建议

设计内容：
{content}"""


def estimate_tokens(text_length: int) -> int:
    """Estimate tokens (English: ~4 chars/token, Chinese: ~1.5 chars/token)"""
    if API_PROVIDER == 'grok':
        return int(text_length / 4)
    else:
        return int(text_length / 1.5)


def get_safe_length(text: str, max_tokens: int, prompt: str) -> int:
    """Calculate safe content length"""
    system_tokens = estimate_tokens(len(prompt.replace('{content}', '')))
    available = max_tokens - system_tokens - 4000
    if available <= 1000:
        return 0
    ratio = 4 if API_PROVIDER == 'grok' else 1.5
    return min(len(text), int(available * ratio))


class OCRExtractor:
    """OCR Extractor using Tesseract"""
    
    def __init__(self):
        self.available = TESSERACT_AVAILABLE
        if self.available:
            print(f"Tesseract OCR initialized (lang: chi_sim+eng)")
        else:
            print("WARNING: Tesseract not available. Install from: https://github.com/UB-Mannheim/tesseract/wiki")
    
    def extract_text_from_image(self, image: Image.Image) -> str:
        """Extract text from PIL Image using Tesseract"""
        if not self.available:
            return ""
        
        try:
            # Use both Chinese and English
            text = pytesseract.image_to_string(image, lang='chi_sim+eng')
            return text
        except Exception as e:
            logger.error(f"OCR error: {e}")
            return ""


class CheckerOCR:
    """Checker with OCR support for scanned documents"""
    
    def __init__(self, model_name: str = None, use_ocr: bool = True):
        # Check API key first
        check_api_key()
        
        self.api_key = API_KEY
        self.api_url = API_URL
        self.model = model_name or MODEL_NAME
        self.provider = API_PROVIDER
        
        config = MODEL_CONFIGS.get(self.model, MODEL_CONFIGS.get("grok-2-1212") or MODEL_CONFIGS["moonshot-v1-32k"])
        self.max_context = config["max_context"]
        self.max_output = config["max_output"]
        
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Initialize OCR
        self.ocr_extractor = None
        if use_ocr:
            self.ocr_extractor = OCRExtractor()
        
        logger.info(f"Using {self.provider.upper()} API")
        logger.info(f"Model: {self.model}")
        logger.info(f"OCR Enabled: {self.ocr_extractor is not None and self.ocr_extractor.available}")
    
    def extract(self, pdf_path: str, force_ocr: bool = False) -> Tuple[Optional[str], int, bool]:
        """
        Extract text from PDF with OCR fallback for scanned documents
        
        Returns:
            tuple: (text_content, num_images, used_ocr)
        """
        try:
            doc = fitz.open(pdf_path)
            text = ""
            images = 0
            used_ocr = False
            total_pages = len(doc)
            
            print(f"Processing {total_pages} pages...")
            
            for page_num, page in enumerate(doc, 1):
                # Try to extract text layer first
                page_text = page.get_text()
                
                # Check if page has meaningful text or if force_ocr is enabled
                should_use_ocr = force_ocr or len(page_text.strip()) < 50
                
                if should_use_ocr and self.ocr_extractor and self.ocr_extractor.available:
                    # Use OCR for this page
                    print(f"  Page {page_num}/{total_pages}: Using OCR...")
                    
                    # Render page to image at 2x resolution for better OCR
                    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                    
                    # OCR the image
                    ocr_text = self.ocr_extractor.extract_text_from_image(img)
                    
                    if ocr_text.strip():
                        text += f"\n--- Page {page_num} (OCR) ---\n" + ocr_text + "\n"
                        used_ocr = True
                    images += 1
                else:
                    # Use text layer
                    if page_text.strip():
                        text += f"\n--- Page {page_num} ---\n" + page_text + "\n"
                    print(f"  Page {page_num}/{total_pages}: Text extracted ({len(page_text)} chars)")
                
                # Also count embedded images
                images += len(page.get_images())
            
            doc.close()
            
            if used_ocr:
                print(f"OCR was used for some pages.")
            
            return text if text.strip() else None, images, used_ocr
            
        except Exception as e:
            logger.error(f"Extraction error: {e}")
            return None, 0, False
    
    def call_api(self, prompt: str) -> Optional[str]:
        """Call API (Grok or KIMI)"""
        try:
            estimated = estimate_tokens(len(prompt))
            print(f"Provider: {self.provider.upper()}")
            print(f"Model: {self.model}")
            print(f"Max context: {self.max_context:,} tokens")
            print(f"Estimated: {estimated:,} tokens")
            
            if estimated > self.max_context:
                print(f"ERROR: Too large ({estimated:,} > {self.max_context:,})")
                return None
            
            payload = {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": self.max_output,
                "temperature": TEMPERATURE
            }
            
            print(f"Calling {self.provider.upper()} API...")
            response = requests.post(
                self.api_url,
                headers=self.headers,
                json=payload,
                timeout=180
            )
            
            if response.status_code == 200:
                result = response.json()
                if 'usage' in result:
                    print(f"Tokens used: {result['usage'].get('total_tokens', 0):,}")
                return result['choices'][0]['message']['content']
            elif response.status_code == 401:
                print(f"ERROR 401: Invalid API Key for {self.provider.upper()}")
                print(f"Key used: {self.api_key[:25]}...")
                return None
            else:
                print(f"API Error {response.status_code}: {response.text[:200]}")
                return None
        except Exception as e:
            print(f"API error: {e}")
            return None
    
    def analyze(self, content: str, struct_type: str) -> Optional[str]:
        """Analyze content"""
        prompt = BUILDING_PROMPT if struct_type == 'building' else TEMPORARY_PROMPT
        
        safe_len = get_safe_length(content, self.max_context, prompt)
        if safe_len <= 0:
            print("ERROR: Content too large")
            return None
        
        truncated = content[:safe_len]
        if len(content) > safe_len:
            print(f"Truncated: {len(content):,} -> {safe_len:,} chars")
        
        return self.call_api(prompt.format(content=truncated))
    
    def check(self, pdf_path: str, struct_type: str = 'building', 
              output_dir: str = None, force_ocr: bool = False) -> bool:
        """Main check with OCR support"""
        print(f"\nAnalyzing: {pdf_path}")
        
        if not os.path.exists(pdf_path):
            print(f"ERROR: File not found: {pdf_path}")
            return False
        
        content, images, used_ocr = self.extract(pdf_path, force_ocr)
        if not content:
            print("ERROR: Could not extract text (tried both text layer and OCR)")
            return False
        
        print(f"Content: {len(content):,} chars, {images} images")
        print(f"OCR Used: {used_ocr}")
        print(f"Estimated: ~{estimate_tokens(len(content)):,} tokens")
        
        result = self.analyze(content, struct_type)
        if not result:
            return False
        
        # Save report
        report_dir = output_dir or os.path.dirname(pdf_path) or '.'
        os.makedirs(report_dir, exist_ok=True)
        
        report_file = os.path.join(report_dir, 
            f"{os.path.splitext(os.path.basename(pdf_path))[0]}_OCR_report.txt")
        
        ocr_note = " (OCR enabled)" if used_ocr else ""
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(f"""STRUCTURAL DESIGN VERIFICATION REPORT{ocr_note}
{'='*50}
File: {pdf_path}
Type: {struct_type.title()}
Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Provider: {self.provider.upper()}
Model: {self.model}
OCR Used: {used_ocr}

{result}

---
Generated by IDC with OCR Support
""")
        
        print(f"\n[OK] Report saved: {report_file}")
        print(f"\nPreview:\n{result[:600]}...")
        return True


def main():
    parser = argparse.ArgumentParser(
        description='IDC - Structural Design Checker with OCR Support',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Normal mode (auto-detect scanned pages)
  IDC_CLI_OCR.exe "design.pdf" --type building
  
  # Force OCR for all pages
  IDC_CLI_OCR.exe "scanned.pdf" --type building --force-ocr
  
  # Specify output directory
  IDC_CLI_OCR.exe "design.pdf" --type temporary --output-dir ./reports

Note: OCR requires Tesseract installed:
  https://github.com/UB-Mannheim/tesseract/wiki
        """
    )
    parser.add_argument('pdf_file', help='PDF file to analyze')
    parser.add_argument('--type', choices=['building', 'temporary'], default='building',
                       help='Type of structure (default: building)')
    parser.add_argument('--output-dir', default='./reports',
                       help='Output directory for reports (default: ./reports)')
    parser.add_argument('--model', default=None,
                       help='Model to use (overrides config)')
    parser.add_argument('--force-ocr', action='store_true',
                       help='Force OCR for all pages (useful for scanned documents)')
    parser.add_argument('--no-ocr', action='store_true',
                       help='Disable OCR (text layer only)')
    
    args = parser.parse_args()
    
    if not TESSERACT_AVAILABLE and not args.no_ocr:
        print("="*60)
        print("WARNING: OCR not available!")
        print("="*60)
        print("To use OCR, install Tesseract:")
        print("  https://github.com/UB-Mannheim/tesseract/wiki")
        print("\nContinuing with text-layer extraction only...\n")
    
    os.makedirs(args.output_dir, exist_ok=True)
    
    try:
        checker = CheckerOCR(
            model_name=args.model,
            use_ocr=not args.no_ocr
        )
        success = checker.check(
            args.pdf_file, 
            args.type, 
            args.output_dir,
            force_ocr=args.force_ocr
        )
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
