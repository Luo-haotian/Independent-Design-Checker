# Independent Design Checker (IDC) - Structural Verification System

An AI-powered structural design verification tool that uses the Grok API to analyze building and temporary structure designs.

## Features

- PDF parsing for design reports, calculations, and drawings
- Building design verification following structural engineering standards
- Temporary structure analysis with focus on construction safety
- Automated compliance checking against building codes
- Detailed analysis reports with recommendations
- Calculation verification to ensure parameter consistency
- Image recognition for scanned documents
- Important comments section highlighting missing elements

## Requirements

- Python 3.7+
- Grok API key (get from x.ai)

## Installation

1. Clone or download this repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

## Usage

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

## Configuration

The `config.py` file contains:
- API key settings
- Analysis parameters
- File processing settings
- Model settings

## Building Executable

To create a standalone executable:
```
python build_exe.py
```

The executable will be created in the `dist/` folder.

## Supported File Types

- PDF files containing design reports, calculations, and drawings (both text and scanned)

## Analysis Categories

The system checks for:
- Calculation verification: Ensures all parameters and computations are mathematically correct
- Structural loading calculations
- Material specifications
- Safety factors
- Code compliance
- Potential structural weaknesses
- Missing critical information
- Important comments section highlighting areas for improvement

For temporary structures, additional checks include:
- Construction sequencing
- Weather resistance
- Safety measures
- Demolition planning