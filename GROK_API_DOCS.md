# Grok API 配置与使用说明

## 1. 配置文件 (config.py)

```python
# Grok API Settings
GROK_API_KEY = "your_grok_api_key_here"
GROK_API_URL = "https://api.x.ai/v1/chat/completions"

# Analysis settings
MAX_TOKENS = 4000
TEMPERATURE = 0.2  # Low temperature for more consistent technical analysis
```

## 2. API 调用函数 (main.py)

```python
def call_grok_api(self, prompt: str) -> Optional[Dict]:
    """Call Grok API with the given prompt"""
    try:
        payload = {
            "model": "grok-3",  # Updated from deprecated "grok-beta"
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "max_tokens": MAX_TOKENS,
            "temperature": TEMPERATURE
        }
        
        response = requests.post(
            self.api_url,
            headers=self.headers,
            json=payload,
            timeout=60  # Increased to 120 for complex analysis in updated version
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"API Error: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"Error calling Grok API: {str(e)}")
        return None
```

## 3. 建筑结构分析提示词 (analyze_building_design)

```python
prompt = f"""
You are an expert structural engineer performing independent design verification of a building design.
Analyze the following building design report and provide a comprehensive assessment covering:

STRUCTURAL SYSTEM ANALYSIS:
- Primary structural system identification
- Lateral force-resisting system
- Gravity load path analysis

LOADING AND ANALYSIS:
- Dead, live, wind, and seismic loads
- Load combinations per applicable codes
- Dynamic analysis considerations

MATERIAL SPECIFICATIONS:
- Concrete grades and steel reinforcement
- Steel grade and connection types
- Material properties verification

CODE COMPLIANCE:
- Building code compliance (IBC, ASCE, ACI, AISC, etc.)
- Seismic design category and requirements
- Fire resistance ratings

CRITICAL DESIGN ELEMENTS:
- Foundation design adequacy
- Floor system performance
- Vertical element capacity
- Connection design

SAFETY AND REDUNDANCY:
- Structural redundancy evaluation
- Progressive collapse resistance
- Special inspection requirements

PROVIDE YOUR ANALYSIS IN THE FOLLOWING FORMAT:
1. EXECUTIVE SUMMARY (brief overview)
2. DETAILED ANALYSIS BY CATEGORY
3. IDENTIFIED ISSUES (critical, major, minor)
4. RECOMMENDATIONS FOR CORRECTIONS
5. OVERALL COMPLIANCE STATUS

Building Design Report Content:
{pdf_content[:3500]}  # Limit content to stay within token limits
"""
```

## 4. 临时结构分析提示词 (analyze_temporary_structure)

```python
prompt = f"""
You are an expert structural engineer specializing in temporary structures.
Analyze the following temporary work design and provide assessment covering:

TEMPORARY STRUCTURE SPECIFICS:
- Construction loads and equipment
- Installation and dismantling sequence
- Temporary bracing requirements

SAFETY CONSIDERATIONS:
- Worker safety during construction
- Public safety measures
- Emergency access and egress

WEATHER RESISTANCE:
- Wind loads during construction
- Rain and drainage considerations
- Temperature effects

DURATION AND MAINTENANCE:
- Design life vs. required duration
- Inspection requirements
- Maintenance schedule

MATERIAL AND CONNECTIONS:
- Suitable materials for temporary use
- Connection methods and safety factors
- Reusability considerations

PROVIDE YOUR ANALYSIS IN THE FOLLOWING FORMAT:
1. EXECUTIVE SUMMARY (brief overview)
2. DETAILED ANALYSIS BY CATEGORY
3. IDENTIFIED ISSUES (critical, major, minor)
4. RECOMMENDATIONS FOR IMPROVEMENTS
5. SAFETY COMPLIANCE STATUS

Temporary Structure Design Content:
{pdf_content[:3500]}
"""
```

## 5. 修改历史

- **原始版本**: 使用 "grok-beta" 模型
- **更新版本**: 已更新为 "grok-3" 模型，因为 "grok-beta" 已被弃用
- **超时设置**: 从60秒增加到120秒以适应复杂分析

## 6. API 调用流程

1. 从PDF提取文本内容
2. 根据结构类型（building/temporary）选择相应的分析提示词
3. 将PDF内容插入提示词模板
4. 调用Grok API获取分析结果
5. 生成结构化报告
