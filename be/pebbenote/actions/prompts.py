apply_action_system_prompt = """
You are a secretary that is creating notes formated as a markdown list.
You are given a note, and an instruction how to modify it. Only output the 
modified note. Output the whole note. Do not add any details to the note that 
were not present in either the note or the instruction from the user.

Respond with a JSON object {"items": [{"text": ..., "children": [...]}]}, where
each item is one list entry and "children" holds its nested entries. Do not
include list markers like "-" in "text". Nest as needed. For example, this note:

- Topic A:
    - A is something like this
    - A needs to do:
        - foo
        - bar
- Topic B:
    - We should not do B

is represented as:

{"items": [
  {"text": "Topic A:", "children": [
    {"text": "A is something like this", "children": []},
    {"text": "A needs to do:", "children": [
      {"text": "foo", "children": []},
      {"text": "bar", "children": []}
    ]}
  ]},
  {"text": "Topic B:", "children": [
    {"text": "We should not do B", "children": []}
  ]}
]}

Below is the note you are going to modify:
""".strip()

apply_action_preamble = """
Below are the users instructions on what to add/remove/modify in the note. Find 
the place to do it on, and only modify that place. Respond with the whole new 
note in the JSON list format. Be short in your responses.
""".strip()

standing_instructions_prefix = """
These are the standing instructions I have been given by the user. I must follow
them whenever they are relevant to the note:
""".strip()

apply_instructions_preamble = """
Apply the standing instructions to the note. Only change what is necessary to
follow them. If the note already follows them, respond with the note unchanged.
Respond with the whole note in the JSON list format.
""".strip()

rewrite_instruction_system_prompt = """
The user dictated a standing instruction about how their notes should be handled.
Rewrite it as one short sentence in the first person, starting with "I should",
that keeps every detail of the instruction. Do not add anything new.
For example: "grocery list always sorted by aisle" becomes
"I should always sort the grocery list by aisle."
Respond with a JSON object {"instruction": ...}.
""".strip()
