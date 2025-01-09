import os
from subprocess import check_output
import subprocess
import json
import fnmatch
import pycountry
import pandas as pd
import csv

def find_srt_file_by_filename(video_path, directory, search_string,subtitles_df):
    for root, _, files in os.walk(directory):
        for file in fnmatch.filter(files, '*_ai.en.sdh.srt'):
            if search_string in file:
                filepath = os.path.join(root, file)
                subtitles_df.loc[len(subtitles_df)] = {
                    'filepath': video_path,
                    'has__english_subtitles': True,
                    'subtitle_language': 'English',
                    'subtitle_path': filepath,
                    'subtitle_stream': ''
                }

def check_english_subtitles(video_path,subtitles_df):
    # Run ffprobe to get subtitle track information
    video_path1=f'\"{video_path}\"'
    command = f'ffprobe -v error -show_entries stream=index:stream_tags=language -select_streams s -of json {video_path1}'
    subtitle_tracks = None
    try:
        subtitle_tracks = json.loads(subprocess.check_output(command))
    except subprocess.CalledProcessError as e:
        error = e.returncode
        print('Failed to run ffprobe command, errorcode: ' + str(error))
    
    for stream in subtitle_tracks.get('streams', []):
        language = stream['tags'].get('language', 'Unknown')
        if language == 'eng':
            subtitles_df.loc[len(subtitles_df)] = {
                'filepath': video_path,
                'has__english_subtitles': True,
                'subtitle_language': language,
                'subtitle_path': '',
                'subtitle_stream': stream['tags']
            }
        else:
            subtitles_df.loc[len(subtitles_df)] = {
                'filepath': video_path,
                'has__english_subtitles': False,
                'subtitle_language': language,
                'subtitle_path': '',
                'subtitle_stream': stream['tags']
            }


        
def process_videos(directory,table_path):
    # Recursively search through the directory for video files
    # Define the columns and create an empty DataFrame
    columns = ['filepath', 'has__english_subtitles', 'subtitle_language', 'subtitle_path']
    subtitles_df = pd.DataFrame(columns=columns)

    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(('.mp4', '.mkv', '.avi', '.mov')):
                video_path = os.path.join(root, file)
                file_name = os.path.splitext(os.path.basename(video_path))[0]
                check_english_subtitles(video_path,subtitles_df)
                find_srt_file_by_filename(video_path, root, file_name,subtitles_df)
                
                if not (subtitles_df['filepath'] == video_path).any():
                    subtitles_df.loc[len(subtitles_df)] = {
                        'filepath': video_path,
                        'has__english_subtitles': False,
                        'subtitle_language': 'None',
                        'subtitle_path': '',
                        'subtitle_stream': ''
                    }
                
    # Save the DataFrame to a tab-delimited CSV file without quotes
    subtitles_df.to_csv(f'GenAI_Logs/{table_path}', sep='\t', index=False, quoting=csv.QUOTE_NONE)
    
def scansubtitles(filepathlist):
    for file in filepathlist:
        filepath,name = file
        process_videos(filepath,f'df_{name}.tsv')
