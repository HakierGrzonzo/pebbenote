"""Standing instructions as a Markdown bullet list, one instruction per item."""

BULLETS = ("- ", "* ")


def format_instructions(instructions: list[str]) -> str:
    return "".join(f"- {instruction}\n" for instruction in instructions)


def parse_instructions(text: str) -> list[str]:
    instructions: list[str] = []
    for line in text.splitlines():
        line = line.strip()
        if line in ("-", "*"):
            # An empty bullet, the lines after it start no instruction of its own
            instructions.append("")
        elif line.startswith(BULLETS):
            instructions.append(line[2:].strip())
        elif line and instructions:
            # Continuation of a wrapped instruction
            instructions[-1] = f"{instructions[-1]} {line}".strip()
        elif line:
            instructions.append(line)
    return [instruction for instruction in instructions if instruction]
