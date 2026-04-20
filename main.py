"""
IDC - Structural Design Checker
Supports: Grok API (x.ai) or KIMI API (Moonshot)
"""

import os
import sys
import fitz
import requests
import argparse
import logging
from pathlib import Path
from typing import Optional
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('idc.log', encoding='utf-8'), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Load config
from config import (
    API_KEY, API_URL, MODEL_NAME, MODEL_CONFIGS,
    MAX_TOKENS, TEMPERATURE, API_PROVIDER
)

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


class Checker:
    def __init__(self, model_name: str = None):
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
        
        logger.info(f"Using {self.provider.upper()} API")
        logger.info(f"Model: {self.model}")
        logger.info(f"API Key: {self.api_key[:20]}...")
    
    def extract(self, pdf_path: str) -> tuple[Optional[str], int]:
        """Extract text from PDF"""
        try:
            doc = fitz.open(pdf_path)
            text = ""
            images = 0
            for page in doc:
                text += page.get_text() + "\n"
                images += len(page.get_images())
            doc.close()
            return text, images
        except Exception as e:
            logger.error(f"Extraction error: {e}")
            return None, 0
    
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
    
    def check(self, pdf_path: str, struct_type: str = 'building', output_dir: str = None) -> bool:
        """Main check"""
        print(f"\nAnalyzing: {pdf_path}")
        
        if not os.path.exists(pdf_path):
            print(f"ERROR: File not found: {pdf_path}")
            return False
        
        content, images = self.extract(pdf_path)
        if not content:
            print("ERROR: Could not extract text")
            return False
        
        print(f"Content: {len(content):,} chars, {images} images")
        print(f"Estimated: ~{estimate_tokens(len(content)):,} tokens")
        
        result = self.analyze(content, struct_type)
        if not result:
            return False
        
        # Save report
        report_dir = output_dir or os.path.dirname(pdf_path) or '.'
        os.makedirs(report_dir, exist_ok=True)
        
        report_file = os.path.join(report_dir, 
            f"{os.path.splitext(os.path.basename(pdf_path))[0]}_report.txt")
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(f"""STRUCTURAL DESIGN VERIFICATION REPORT
======================================
File: {pdf_path}
Type: {struct_type.title()}
Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Provider: {self.provider.upper()}
Model: {self.model}

{result}

---
Generated by IDC
""")
        
        print(f"\n[OK] Report saved: {report_file}")
        print(f"\nPreview:\n{result[:600]}..." if result else "")
        return True


def main():
    parser = argparse.ArgumentParser(description='IDC - Structural Design Checker')
    parser.add_argument('pdf_file', help='PDF file to analyze')
    parser.add_argument('--type', choices=['building', 'temporary'], default='building')
    parser.add_argument('--output-dir', default='./reports')
    parser.add_argument('--model', default=None)
    args = parser.parse_args()
    
    os.makedirs(args.output_dir, exist_ok=True)
    
    try:
        checker = Checker(model_name=args.model)
        success = checker.check(args.pdf_file, args.type, args.output_dir)
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
