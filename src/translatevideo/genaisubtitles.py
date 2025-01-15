import os
from subprocess import check_output
import subprocess
import json
import pycountry
import pandas as pd
import csv
import translatevideo.utilities as utilities
import translatevideo.concatsrtfiles as concatsrtfiles
import translatevideo.removeduplicatelinessrt as removeduplicatelinessrt
import translatevideo.translatesrt as translatesrt
import json

def convert_language_code(three_letter_code):
    try:
        # Get the language object from the 3-letter language code
        language = pycountry.languages.get(alpha_3=three_letter_code)
        # Return the 2-letter language code
        return language.alpha_2
    except AttributeError:
        # If the language code is not found, return None or handle the exception as needed
        return 'auto'

# Function to get the 2-character language code
def get_language_code(language_name):
    try:
        language = pycountry.languages.get(name=language_name)
        return language.alpha_2
    except AttributeError:
        return 'auto'
        
def get_top_audio_stream(video_path,log_filepath):
    # Run ffprobe to get audio track information
    video_path=f'\"{video_path}\"'
    command = f'ffprobe -v error -show_entries stream=index:stream_tags=language -select_streams a -of json {video_path}'
    utilities.append_to_file(log_filepath, '      Running ffprobe command: ' + str(command))
    audio_tracks = None
    try:
        audio_tracks = json.loads(subprocess.check_output(command))
    except subprocess.CalledProcessError as e:
        error = e.returncode
        utilities.append_to_file(log_filepath, '      Failed to run ffprobe command, errorcode: ' + str(error))
    top_audio_stream = None
    top_audio_language = None
    for stream in audio_tracks.get('streams', []):
        language = stream['tags'].get('language', 'Unknown')
        if language == 'eng':
            top_audio_stream = stream['index'] - 1
            top_audio_language = language
            break
    
    if top_audio_stream is None and audio_tracks.get('streams'):
        top_audio_stream = audio_tracks['streams'][0]['index'] - 1
        top_audio_language = audio_tracks['streams'][0]['tags'].get('language', 'Unknown')
    
    return top_audio_stream, top_audio_language
    
def get_filenames_split_wav(directory,video_path):
    # Define the directory and filename pattern
    file_name = os.path.splitext(os.path.basename(video_path))[0]
    filename_pattern = file_name + '_'

    # Get the list of files in the directory
    files = os.listdir(directory)

    # Filter the files that match the pattern
    output_files = [f for f in files if f.startswith(filename_pattern) and f.endswith('.wav')]
    
    filelist = []
    
    for file in output_files:
        filepath = os.path.join(directory, file)
        filelist.append(filepath)
        
    return filelist

def get_language_from_whisper(output_dir, video_path,nonenglishmodel,log_filepath):
    nonenglish_model_quotes = f'\"{nonenglishmodel}\"'
    file_name = os.path.splitext(os.path.basename(video_path))[0]
    wav_path = os.path.join(output_dir, f"{file_name}.wav")
    split_wav_path = os.path.join(output_dir, f"{file_name}")
    full_json_path = os.path.join(output_dir, f"{file_name}.json")
    
    command = f'whisper-cli \"{wav_path}\" -m {nonenglish_model_quotes} -l auto -dl --output-json-full --output-file \"{split_wav_path}\"'
    utilities.append_to_file(log_filepath, '      Running whisper command: ' + str(command))
    lang_code = 'auto'
    error = 0
    try:
        language = subprocess.check_output(command)
    except subprocess.CalledProcessError as e:
        error = e.returncode
        utilities.append_to_file(log_filepath, '      Failed to run whisper command, errorcode: ' + str(error))
    if error == 0:
        # Load JSON data from a file
        with open(full_json_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
        lang_code = data["result"]["language"]
    return lang_code
    
def convert_audio_to_wav(video_path, output_dir,top_audio_stream,log_filepath):
    # Extract the file name without extension
    file_name = os.path.splitext(os.path.basename(video_path))[0]
    wav_path = os.path.join(output_dir, f"{file_name}.wav")
    split_wav_path = os.path.join(output_dir, f"{file_name}")
    whisper_json_path = os.path.join(output_dir, f"{file_name}.json")
    video_path=f'\"{video_path}\"'
    wav_path=f'\"{wav_path}\"'
    # Convert the first audio track to .wav using ffmpeg
    command = f'ffmpeg -y -i {video_path} -map 0:a:{str(top_audio_stream)} -vn -acodec pcm_s16le -ac 1 -ar 16000 {wav_path}'
    utilities.append_to_file(log_filepath, '      Running ffmpeg command: ' + str(command))
    error = 0
    try:
        subprocess.check_output(command)
    except subprocess.CalledProcessError as e:
        error = e.returncode
        utilities.append_to_file(log_filepath, '      Failed to run ffpmeg command, errorcode: ' + str(error))
    
    command = f'ffmpeg -i {wav_path} -f segment -segment_time 900 -c copy \"{split_wav_path}_%03d.wav\"'
    utilities.append_to_file(log_filepath, '      Running ffmpeg command: ' + str(command))
    try:
        subprocess.check_output(command)
    except subprocess.CalledProcessError as e:
        error = e.returncode
        utilities.append_to_file(log_filepath, '      Failed to run ffpmeg command, errorcode: ' + str(error))
    return error

def remove_files_with_prefix(directory, prefix,log_filepath):
    # List all files in the directory
    files = os.listdir(directory)
    # Iterate through the files
    for file in files:
        # Check if the file name starts with the specified prefix
        if file.startswith(prefix):
            file_path = os.path.join(directory, file)
            try:
                os.remove(file_path)
                utilities.append_to_file(log_filepath,f"      Removed file: {file_path}")
            except Exception as e:
                utilities.append_to_file(log_filepath,f"      Error removing file {file_path}: {e}")
    
def concat_subtitle_files(output_dir,file_name,wavelist):
    subtitle_files = []
    count = 0
    final_subtile_file = os.path.join(output_dir, f"{file_name}1.srt")
    for x in range(len(wavelist)):
        filename = os.path.join(output_dir, f"{file_name}_{str(count)}.srt")
        subtitle_files.append(filename)
        count = count + 1
    concatsrtfiles.concatenate_and_adjust_srt_files(final_subtile_file, 900000, subtitle_files)
    
def get_language(output_dir, nonenglishmodel, video_path, top_audio_language, log_filepath):
    language = top_audio_language
    lang_code = convert_language_code(top_audio_language) ##top audio language is 3 char, convert from 3 char to 2 char code
    if (lang_code) == 'auto': ## if not found, then try try getting the language from whisper
        lang_code = get_language_from_whisper(output_dir, video_path,nonenglishmodel,log_filepath)
    utilities.append_to_file(log_filepath, f'      Found language: {language}, Language Code: {lang_code}')
    return language, lang_code

def run_whisper_cli(englishmodel, nonenglishmodel,video_path, output_dir,lang_code,log_filepath):
    # Run the whisper-cli command
    wavelist = get_filenames_split_wav(output_dir,video_path)
    file_name = os.path.splitext(os.path.basename(video_path))[0]
    srt_path = os.path.join(output_dir, f"{file_name}")
    
    count = 0
    error = 0

    for file in wavelist:
        wave_file_quotes = f'\"{file}\"'
        english_model_quotes = f'\"{englishmodel}\"'
        nonenglish_model_quotes = f'\"{nonenglishmodel}\"'
        if lang_code == 'en':
            command = f'whisper-cli -m {english_model_quotes} -f {wave_file_quotes} --output-srt --output-file \"{srt_path}_{str(count)}\" --language {lang_code}'
            utilities.append_to_file(log_filepath, '      Running Whisper Command: ' + str(command))
            try:
                subprocess.check_output(command)
            except subprocess.CalledProcessError as e:
                error = e.returncode
                utilities.append_to_file(log_filepath, '      Failed to run ai gen command, errorcode: ' + str(error))
        else:
            command = f'whisper-cli -m {nonenglish_model_quotes} -f {wave_file_quotes} --output-srt --output-file \"{srt_path}_{str(count)}\" --language {lang_code} --translate'
            utilities.append_to_file(log_filepath, '      Running Whisper Command: ' + str(command))
            try:
                subprocess.check_output(command)
            except subprocess.CalledProcessError as e:
                error = e.returncode
                utilities.append_to_file(log_filepath, '      Failed to run ai gen command, errorcode: ' + str(error))
        count = count + 1
    
    utilities.append_to_file(log_filepath, f'      Merging Subtitle files into {file_name}1.srt')
    concat_subtitle_files(output_dir,file_name,wavelist)
    
    final_subtile_file = os.path.join(output_dir, f"{file_name}1.srt")
    final_subtile_file_quotes = f'\"{final_subtile_file}\"'
    srt_path_full = os.path.join(output_dir, f"{file_name}_ai.en.sdh.srt")
    srt_path_full_quotes = f'\"{srt_path_full}\"'
    
    if lang_code == 'en':
        utilities.append_to_file(log_filepath, f'      Placing Merged srt file into final path: {srt_path_full}')
        utilities.move_and_rename_file(final_subtile_file, srt_path_full,log_filepath)
    elif lang_code != 'auto': ##need to translate the subtitle file if it's not english
        utilities.append_to_file(log_filepath, f'      Translating {lang_code} into english. Placing into {srt_path_full}')
        error = translatesrt.translate_srt(lang_code,'en', final_subtile_file, srt_path_full, log_filepath)
    utilities.append_to_file(log_filepath, f'      Removing Duplicate SRT Lines in {srt_path_full}')
    try:
        removeduplicatelinessrt.remove_adjacent_duplicate_text_lines(srt_path_full)
    except Exception as e:
        utilities.append_to_file(log_filepath, f'      Error Removing Adjacent Duplicate Text Lines: {str(e)}')
        error = 1
    return error

def move_output_file(video_dir, temp_directory, video_file_name,log_filepath):
    # Move the output file from tempwavefiles to the video file directory
    final_path = os.path.join(video_dir, f"{video_file_name}_ai.en.sdh.srt")
    output_file = os.path.join(temp_directory, f"{video_file_name}_ai.en.sdh.srt")
    utilities.move_and_rename_file(output_file, final_path,log_filepath)
        
# Filter out rows where any row in the group has English subtitles
def filter_groups(group):
    if (group['has__english_subtitles'] == True).any():
        return group.iloc[0:0]
    return group
        
def process_videos(tempwavefiles,dirname,englishmodel, nonenglishmodel):
    # Read the tab-delimited file
    log_filepath = f'GenAI_Logs/GenAILog_{dirname}.txt'
    utilities.remove_file(log_filepath)
    subtitles_frame_filepath = f'GenAI_Logs/df_{dirname}.tsv'
    subtitles_df = pd.read_csv(subtitles_frame_filepath, sep='\t')
    grouped_df = subtitles_df.groupby('filepath')

    filtered_groups_no_subtitles = grouped_df.apply(filter_groups).reset_index(drop=True)
    filtered_groups_no_subtitles = filtered_groups_no_subtitles.groupby('filepath').nth(0).reset_index(drop=True)
    filtered_groups_no_subtitles.to_csv('GenAI_Logs/filtered_groups_' + dirname + '.tsv', sep='\t', index=False, quoting=csv.QUOTE_NONE)

    for index, row in filtered_groups_no_subtitles.iterrows():
        video_path = row['filepath']
        video_ID = row['ID']
        video_path_file_name = os.path.splitext(os.path.basename(video_path))[0]
        utilities.append_to_file(log_filepath, 'Processing video file: ' + video_path)
        top_audio_stream, top_audio_language = get_top_audio_stream(video_path,log_filepath)
        convert_audio_to_wav(video_path, tempwavefiles,top_audio_stream,log_filepath)
        language, lang_code = get_language(tempwavefiles, nonenglishmodel,video_path, top_audio_language, log_filepath)
        if lang_code != 'auto':
            utilities.append_to_file(log_filepath, '      Generating subtitles for audio stream index: ' + str(top_audio_stream) + ', audio language: ' + str(lang_code))
            error = run_whisper_cli(englishmodel, nonenglishmodel,video_path, tempwavefiles,lang_code,log_filepath)
            if(error == 0):
                # Move the output .srt file
                directory = os.path.dirname(video_path)
                move_output_file(directory,tempwavefiles,video_path_file_name,log_filepath)
                output_file = os.path.join(directory, f"{video_path_file_name}_ai.en.sdh.srt")
                ##successfully created subtitles:
                subtitles_df.loc[len(subtitles_df)] = {
                    'filepath': video_path,
                    'has__english_subtitles': True,
                    'subtitle_language': 'English',
                    'subtitle_path': output_file,
                    'subtitle_stream': ''
                }
                subtitles_df.to_csv(subtitles_frame_filepath, sep='\t', index=False, quoting=csv.QUOTE_NONE)
            else:
                utilities.append_to_file(log_filepath, f'      Error: {error} in Transcription / Translating File. Skipping: {video_path}')
        else:
            utilities.append_to_file(log_filepath, f'      Language Not recognized. Skipping {video_path}')
        remove_files_with_prefix(tempwavefiles, video_path_file_name,log_filepath)
        
def genaisubtitles(tempdir, filepathlist, englishmodel, nonenglishmodel):
    # Create the temp directory if it doesn't exist
    translatesrt.updateTranslationPackages()
    os.makedirs(tempdir, exist_ok=True)
    for file in filepathlist:
        filepath,name = file
        process_videos(tempdir,name,englishmodel, nonenglishmodel)
