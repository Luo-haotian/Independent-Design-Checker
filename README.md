# Independent Design Checker (IDC) - Structural Verification System

An AI-powered structural design verification tool that uses the **KIMI API (Moonshot AI)** to analyze building and temporary structure designs.

## Features

- PDF parsing for design reports, calculations, and drawings
- Building design verification following structural engineering standards
- Temporary structure analysis with focus on construction safety
- Automated compliance checking against building codes
- Detailed analysis reports with recommendations
- Token consumption tracking with 137x multiplier for computational resource estimation

## Requirements

- Python 3.8+
- KIMI API key (get from https://platform.moonshot.cn/)

## Installation

1. Clone or download this repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Create `.env` file from template:
   ```
   cp .env.example .env
   ```
4. Edit `.env` file and add your KIMI API key:
   ```
   KIMI_API_KEY=your_actual_api_key_here
   ```

## Usage

### GUI Version (Recommended)

Run the graphical interface:
```
python gui.py
```

Or use the compiled executable:
```
dist\IDC_GUI.exe
```

### CLI Version

Basic usage:
```
python main.py path/to/design.pdf --type building
```

For temporary structures:
```
python main.py path/to/design.pdf --type temporary
```

Specify output directory:
```
python main.py path/to/design.pdf --type building --output-dir ./my_reports
```

### Using Compiled Executable

```
dist\IDC_CLI.exe path/to/design.pdf --type building
```

## Configuration

The `config.py` file contains:
- API settings (loaded from environment variables)
- Analysis parameters
- File processing settings
- Token multiplier settings (137x for business model)

### Environment Variables

Create a `.env` file in the project root:
```
KIMI_API_KEY=your_kimi_api_key_here
```

Or set as system environment variable:
- Windows: `set KIMI_API_KEY=your_key`
- Linux/Mac: `export KIMI_API_KEY=your_key`

## Building Executable

To create a standalone executable:
```
python build_exe.py
```

The executables will be created in the `dist/` folder.

**Note**: Make sure your `.env` file with API key is in the same directory as the executable when running.

## Supported File Types

- PDF files containing design reports, calculations, and drawings

## Analysis Categories

The system checks for:
- Structural loading calculations
- Material specifications
- Safety factors
- Code compliance
- Potential structural weaknesses
- Missing critical information
- **Calculation verification** (mathematical consistency check)

For temporary structures, additional checks include:
- Construction sequencing
- Weather resistance
- Safety measures
- Demolition planning

## Token Consumption

The system displays token consumption statistics before and during analysis:
- Input tokens: (characters ÷ 4) × 137 multiplier
- Output tokens: estimated or actual from API response
- Total computational resources consumed

This helps understand the computational cost of each analysis.

## Logs

Application logs are saved to `idc.log` for debugging and monitoring.

## API Provider

This project uses **KIMI AI (Moonshot)** for structural analysis:
- Website: https://www.moonshot.cn/
- API Documentation: https://platform.moonshot.cn/docs

## Security Notes

- **Never commit your `.env` file** containing API keys to version control
- The `.gitignore` file is configured to exclude `.env` and other sensitive files
- API keys should be rotated regularly
- Keep your API keys private and do not share them

## License

[Your License Here]

## Support

For issues or questions:
1. Check the logs in `idc.log`
2. Verify your API key is valid
3. Ensure PDF files are not encrypted or corrupted
