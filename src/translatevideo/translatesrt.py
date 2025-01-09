import re
from bs4 import BeautifulSoup
import argostranslate.package, argostranslate.translate
import translatehtml
import translatevideo.utilities as utilities
    
def add_tags_to_text(text, tags):
    value = text
    for tag in tags:
        value = '<' + tag + '>' + value + '</' + tag + '>'
    return value

def process_srt(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        lines = file.readlines()
    
    timecode_pattern = re.compile(r'(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})')
    sections = {}
    counter = 1
    current_text = []
    
    current_timecode = ''
    current_id = 1

    for line in lines:
        stripped_line = line.strip()
        
        if not stripped_line:
            counter = counter + 1
            continue

        # Check if the line is a timecode
        if timecode_pattern.match(stripped_line) and stripped_line:
            current_timecode = stripped_line
        # Check if the line is an ID
        elif re.match(r'^\d+$', stripped_line) and stripped_line:
            current_id = counter
        elif stripped_line and current_timecode != '': ##must be a non blank line
            soup = BeautifulSoup(stripped_line, "html.parser")
            clean_text = soup.get_text()
            tags = []
            for tag in soup.find_all():
                tags.append(tag.name)
            linetext = (current_timecode,clean_text,tags)
            utilities.append_to_key(sections, current_id, linetext)
        
    file_string = ''
    for key in sections:
        file_string = file_string + '<div>'
        for section in sections[key]:
            current_timecode,clean_text,tags = section
            file_string = file_string  + '<id' + str(key) + '>' + clean_text + '</id' + str(key) + '>'
        file_string = file_string + '</div>'
    return file_string, sections

def gen_translated_dict(soup):
    # Find all div elements
    souphtml = BeautifulSoup(str(soup),"html.parser")
    translated_subtitles = {}
    divs = souphtml.find_all('div')
    for div in divs:
        if div is not None:
            non_p_tags = div.find_all(lambda tag: tag.name != 'p')
            for tag in non_p_tags:
                if tag is not None:
                    tagid = tag.name.replace('id', '')
                    subtitleid = utilities.convert_string_to_int(tagid)
                    subtitletext = tag.get_text()
                    utilities.append_to_key(translated_subtitles, subtitleid, subtitletext.strip())
    return translated_subtitles
    
def gen_srt_file(translated_subtitles, original_formatting):
    srtlines = []
    current_text = ''
    for key in original_formatting:
        timecodelines = []
        if key in translated_subtitles:
            count = 0
            for original_entry in original_formatting[key]:
                current_timecode,clean_text,tags = original_entry
                if count < len(translated_subtitles[key]):
                    translated_text = translated_subtitles[key][count]
                    if count == 0:
                        timecodelines.append(str(key))
                        timecodelines.append(current_timecode)
                    current_text = add_tags_to_text(translated_text,tags)
                    timecodelines.append(current_text)
                count = count + 1
            srtlines.extend(timecodelines)
            srtlines.append('')
    return srtlines

# Write list to file
def write_translated_srt(output_srt,linelist):
    with open(output_srt, 'wb') as file:
        for item in linelist:
            encoded_item = item.encode('utf-8', errors='ignore') + b'\n'
            file.write(encoded_item)
            
            
def updateTranslationPackages():
    # Update the package index
    argostranslate.package.update_package_index()

    # Get the available packages
    available_packages = argostranslate.package.get_available_packages()

    # Install all available language packages
    for package in available_packages:
        argostranslate.package.install_from_path(package.download())      
            
def translate_srt(from_code,to_code, input_file, output_file, log_filepath, write_merged_language_file = False):
    file_string, original_formatting = process_srt(input_file)
    installed_languages = argostranslate.translate.get_installed_languages()
    from_lang = list(filter(lambda x: x.code == from_code, installed_languages))[0]
    to_lang = list(filter(lambda x: x.code == to_code, installed_languages))[0]
    error = 0
    try:
        translation = from_lang.get_translation(to_lang)
    except Exception as e:
        utilities.append_to_file(log_filepath, f'     Translator Error in Language lookup: {str(e)}')
        error = 1
    try:
        translated_soup = translatehtml.translate_html(translation, file_string)
    except Exception as e:
        append_to_file(log_filepath, f'     Translation Error: {str(e)}')
        error = 1
    translated_dict = gen_translated_dict(translated_soup)
    srt_file = gen_srt_file(translated_dict, original_formatting)
    write_translated_srt(output_file,srt_file)
    
    return error
    
    #if write_merged_language_file:
    #ffmpeg -i "input1.srt" -i "input2.srt" -filter_complex "[0:v][0:a][0:s][1:s]concat=n=1:v=0:a=0:s=1[out]" -map "[out]" "merged_output.srt"

        


