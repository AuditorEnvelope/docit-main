def extract_section(output: str, section: str) -> str:
    if not output:
        return ""
    start = f"<{section}_START>"
    end = f"<{section}_END>"
    if start not in output or end not in output:
        return ""
    return output.split(start)[1].split(end)[0].strip()