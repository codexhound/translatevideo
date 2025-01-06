import re

def adjust_time(offset, time_str):
    """Adjust the time by the given offset (in milliseconds)."""
    h, m, s, ms = map(int, re.split('[:,]', time_str))
    total_ms = (h * 3600 + m * 60 + s) * 1000 + ms + offset
    h, ms = divmod(total_ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"

def adjust_srt_content(srt_content, offset):
    """Adjust the times in the SRT content by the given offset."""
    adjusted_lines = []
    time_re = re.compile(r'(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})')
    for line in srt_content.splitlines():
        match = time_re.match(line)
        if match:
            start_time, end_time = match.groups()
            adjusted_start = adjust_time(offset, start_time)
            adjusted_end = adjust_time(offset, end_time)
            adjusted_lines.append(f"{adjusted_start} --> {adjusted_end}")
        else:
            adjusted_lines.append(line)
    return '\n'.join(adjusted_lines)

def concatenate_and_adjust_srt_files(output_file, offset_in_ms, input_files):
    count = 1
    filenum = 1
    current_offset = offset_in_ms
    with open(output_file, 'w', encoding='utf-8', errors='ignore') as outfile:
        for file in input_files:
            print(file)
            with open(file, 'r', encoding='utf-8', errors='ignore') as infile:
                srt_content = infile.read()
                if filenum > 1: ##if file is not the first file then we need to adjust by offset
                    current_offset = offset_in_ms * count ##calculate current offset
                    adjusted_content = adjust_srt_content(srt_content, current_offset)
                    count = count + 1
                else:
                    adjusted_content = srt_content
                outfile.write(adjusted_content)
                outfile.write('\n\n')
            filenum = filenum + 1

# Example usage
#concatenate_and_adjust_srt_files('combined_subtitles.srt', 'subtitle1.srt', 'subtitle2.srt', 'subtitle3.srt')
