import re
import sys

def remove_adjacent_duplicate_text_lines(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        lines = file.readlines()

    def is_timecode_line(line):
        return re.match(r'^\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3}$', line)

    unique_lines = []
    previous_line = None
    
    for line in lines:
        if not line.strip() or line.strip().isdigit() or is_timecode_line(line.strip()):
            unique_lines.append(line)
        else:
            if line != previous_line:
                unique_lines.append(line)
            previous_line = line

    with open(file_path, 'w', encoding='utf-8') as file:
        file.writelines(unique_lines)
