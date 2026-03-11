import sys

markdown_content = """# My Title
This is the intro.
## Section 1
This is section 1 content.
## Section 2
This is section 2 content.
"""

def parse_sections(markdown_content: str):
    lines = markdown_content.splitlines()
    sections = []
    
    current_heading = "PREAMBLE"
    current_content = []
    
    for line in lines:
        if line.startswith("## ") and not line.startswith("### "):
            if current_content or current_heading != "PREAMBLE":
                sections.append({
                    "heading": current_heading,
                    "content": "\n".join(current_content).strip()
                })
                current_content = []
            current_heading = line.strip()
        elif line.startswith("# ") and not line.startswith("## "):
            if current_content:
                sections.append({
                    "heading": current_heading,
                    "content": "\n".join(current_content).strip()
                })
                current_content = []
            current_heading = line.strip()
        else:
            current_content.append(line)
            
    if current_content:
        sections.append({
            "heading": current_heading,
            "content": "\n".join(current_content).strip()
        })
        
    return sections

print(parse_sections(markdown_content))
