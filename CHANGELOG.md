# IDC Project - Changelog

## v3.0 - KIMI API Migration & Security Fixes

### Major Changes
1. **API Migration**: Switched from Grok API (x.ai) to **KIMI API (Moonshot AI)**
   - New model: `moonshot-v1-8k` (configurable to 32k/128k)
   - New API endpoint: `https://api.moonshot.cn/v1/chat/completions`
   - Improved Chinese language support

2. **Security Enhancement**: API keys no longer hardcoded
   - Moved API configuration to `.env` file
   - Added `.env.example` template file
   - Added `.gitignore` to prevent accidental commits of secrets
   - Configuration validation on startup

3. **Bug Fixes**:
   - Fixed undefined `estimated_output_tokens` variable bug
   - Fixed `--output-dir` parameter not being used (now correctly saves reports to specified directory)
   - Added proper initialization of output variables

### Technical Improvements
1. **Image Processing**:
   - Added `encode_image_to_base64()` method for proper image encoding
   - Improved image handling in API calls

2. **Logging System**:
   - Added comprehensive logging to `idc.log`
   - Both file and console logging
   - Better error tracking and debugging

3. **Build System**:
   - Updated `build_exe.py` to handle `.env` files
   - Added dependency checks and warnings
   - Improved build output messages

4. **Dependencies**:
   - Added `pyinstaller` to `requirements.txt`
   - Using `python-dotenv` for environment variable management

### Configuration Changes
- `config.py` now loads from environment variables
- Added `TOKEN_MULTIPLIER = 137` constant
- Model name changed to `moonshot-v1-8k`

### Breaking Changes
⚠️ **Action Required**: Users must create a `.env` file with their KIMI API key:
```bash
# Copy the example file
cp .env.example .env

# Edit .env and add your API key from https://platform.moonshot.cn/
```

---

## v2.1 - Token Statistics Enhancement

### New Features Added
1. **Token Consumption Tracking**: Added detailed token consumption statistics with 137x multiplier
2. **Resource Cost Display**: Shows input/output token estimates
3. **Business Model Transparency**: Displays resource costs

---

## v2.0 - Enhanced Analysis

### Features
1. **Updated AI Model**: Changed from "grok-3" to "grok-4-1-fast-non-reasoning"
2. **Calculation Verification**: Added verification of numerical values
3. **Image Recognition**: Support for processing scanned documents
4. **Important Comments Section**: Highlights missing elements
5. **Enhanced Error Reporting**: More detailed error messages

---

## v1.0 - Initial Release

### Features
- PDF parsing with PyMuPDF
- Building and temporary structure analysis
- Basic GUI and CLI interfaces
- Report generation
