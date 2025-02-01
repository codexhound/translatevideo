import os
import re
from subprocess import check_output
import subprocess
import json
import pycountry
import pandas as pd
import csv
import translatevideo.utilities as utilities
import translatevideo.concatsrtfiles as concatsrtfiles
from pydub import AudioSegment
import threading
#import time

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
	

def convert_language_code(three_letter_code):
	try:
		# Get the language object from the 3-letter language code
		language = pycountry.languages.get(alpha_3=three_letter_code)
		# Return the 2-letter language code
		return language.alpha_2
	except AttributeError:
		# If the language code is not found, return None or handle the exception as needed
		return 'auto'

def remove_files_with_prefix(directory, prefix,logger=None):
	# List all files in the directory
	files = os.listdir(directory)
	# Iterate through the files
	for file in files:
		# Check if the file name starts with the specified prefix
		if file.startswith(prefix):
			file_path = os.path.join(directory, file)
			try:
				os.remove(file_path)
				if logger != None:
					logger.add_to_log(f"	Removed file: {file_path}")
			except Exception as e:
				if logger != None:
					logger.add_to_log(f"	Error removing file {file_path}: {e}")
		
# Filter out rows where any row in the group has English subtitles
def filter_groups(group):
	if (group['has__english_subtitles'] == True).any():
		return group.iloc[0:0]
	return group

def run_command(command, name = '', logger=None):
	if logger != None:
		logger.add_to_log(f'	Running {name} command: {command}')
	error = 0
	output = None
	try:
		output = subprocess.check_output(command)
	except subprocess.CalledProcessError as e:
		error = e.returncode
		if logger != None:
			logger.add_to_log(f'	Failed to run {name} command, errorcode: {error}')
	return error, output
	
class transcribe:
	def __init__(self,threads,tempdir, englishmodel, nonenglishmodel):
		os.makedirs(tempdir, exist_ok=True)
		self.threads = threads
		self.tempdir = tempdir
		self.englishmodel = englishmodel
		self.nonenglishmodel = nonenglishmodel

	def get_language_from_whisper(self):
		nonenglish_model_quotes = f'\"{self.nonenglishmodel}\"'

		command = f'whisper-cli \"{self.wav_path}\" -m {nonenglish_model_quotes} -l auto -dl --output-json-full --output-file \"{self.split_file_path}\"'
		lang_code = 'auto'
		error, output = run_command(command, name = 'whisper', logger=self.logger)
		full_json_path = f'{self.split_file_path}.json'
		if error == 0:
			# Load JSON data from a file
			with open(full_json_path, 'r', encoding='utf-8') as file:
				data = json.load(file)
			lang_code = data["result"]["language"]
		self.lang_code = lang_code
		
	def get_top_audio_stream(self):
		# Run ffprobe to get audio track information
		video_path=f'\"{self.video_path}\"'
		audio_tracks = None
		command = f'ffprobe -v error -show_entries stream=index:stream_tags=language -of json {video_path}'
		error, audio_tracks = run_command(command, name = 'ffprobe', logger=self.logger)
		audio_tracks = json.loads(audio_tracks)
		
		top_audio_stream = None
		top_audio_language = None
		first_audio_stream = None
		first_audio_language = None
		countaudio = 0
		countstream = 0
		foundfirstaudio = False
		foundtopaudio = False
		for stream in audio_tracks.get('streams', []):
			language = stream['tags'].get('language', 'Unknown')
			print(str(stream))
			if 'audio' in str(stream).lower():
				print('found audio')
				if not foundfirstaudio:
					first_audio_stream = countstream
					first_audio_language = language
					foundfirstaudio = True
				countaudio = countaudio + 1
				if language == 'eng' and not foundtopaudio:
					top_audio_stream = countstream
					top_audio_language = language
					foundtopaudio = True
			countstream = countstream + 1
		
		if top_audio_stream is None:
			top_audio_stream = first_audio_stream
			top_audio_language = first_audio_language

		if top_audio_stream is not None:
			top_audio_stream = top_audio_stream - (countstream-countaudio)
		else:
			top_audio_stream = 0
			top_audio_language = 'Unknown'
			
		self.top_audio_stream = top_audio_stream
		self.top_audio_language = top_audio_language

	def convert_audio_to_wav(self):
		# Extract the file name without extension
		self.wav_path = os.path.join(self.tempdir, f"{self.video_path_file_name}.wav")
		self.split_file_path = os.path.join(self.tempdir, f"{self.video_path_file_name}")
		self.whisper_json_path = os.path.join(self.tempdir, f"{self.video_path_file_name}.json")
		video_path1=f'\"{self.video_path}\"'
		wav_path1=f'\"{self.wav_path}\"'
		# Convert the first audio track to .wav using ffmpeg
		command = f'ffmpeg -y -i {video_path1} -map 0:a:{str(self.top_audio_stream)} -vn -acodec pcm_s16le -ac 2 -ar 16000 {wav_path1}'
		error, output = run_command(command, name = 'ffmpeg', logger=self.logger)

		if error != 0:
			return error
		
		audio = AudioSegment.from_file(self.wav_path)
		duration = len(audio) / 1000.0
		self.numfiles = utilities.roundupdiv(duration, 300)
		self.logger.add_to_log(f'	Audio runtime of file "{self.wav_path}": {duration}, numfiles: {self.numfiles}')
		
		command = f'ffmpeg -i {wav_path1} -f segment -segment_time 300 -c copy \"{self.split_file_path}_%03d.wav\"'
		error, output = run_command(command, name = 'ffmpeg', logger=self.logger)

		return error

	def move_output_file(self):
		# Move the output file from tempdir to the video file directory
		self.final_srt_path = os.path.join(self.final_directory, f"{self.video_path_file_name}_ai.en.sdh.srt")
		utilities.move_and_rename_file(self.final_srt_temp_path, self.final_srt_path,self.logger)

	def get_language(self):
		self.language = self.top_audio_language
		self.lang_code = convert_language_code(self.top_audio_language) ##top audio language is 3 char, convert from 3 char to 2 char code
		if (self.lang_code) == 'auto': ## if not found, then try try getting the language from whisper
			self.get_language_from_whisper()
		self.logger.add_to_log(f'	Found language: {self.language}, Language Code: {self.lang_code}')

	def get_filenames_split_wav(self):
		filelist = []
		for count in range(self.numfiles):
			file = self.video_path_file_name + '_' + str(count).zfill(3) + '.wav'
			filepath = os.path.join(self.tempdir, file)
			filelist.append(filepath)  
		self.wavelist = filelist

	def concat_subtitle_files(self):
		subtitle_files = []
		self.final_srt_temp_path = os.path.join(self.tempdir, f"{self.video_path_file_name}_ai.en.sdh.srt.srt")
		self.logger.add_to_log(f'	Merging Subtitle files into {self.final_srt_temp_path}')
		for count in range(self.numfiles):
			filename = os.path.join(self.tempdir, f"{self.video_path_file_name}_{str(count)}.srt")
			subtitle_files.append(filename)
		concatsrtfiles.concatenate_and_adjust_srt_files(self.final_srt_temp_path, 300000, subtitle_files)

	def process_whisper_output(self):
		error = 0
		for returnv in self.threadoutputlist:
			error, output = returnv
			if error > 0 or error < 0:
				return error, True
		return error, False

	def run_thead(self,index,command, name, logger):
		self.threadoutputlist[index] = run_command(command, name, logger)
		#self.logger.add_to_log(f'	thread index:  {index}')

	def startthreads(self):
		for thread in self.threadlist:
			thread.start()

	def jointhreads(self):
		for thread in self.threadlist:
			thread.join()

	def run_whisper_threads(self):
		self.startthreads()
		self.jointhreads()
		#time.sleep(2.5)
		#self.logger.add_to_log(f'	numOutputs: {len(self.threadoutputlist)}')
		#self.logger.add_to_log(f'	numThreads: {len(self.threadlist)}')
		error, haserror = self.process_whisper_output()
		self.threadindex = 0
		self.threadoutputlist = []
		self.threadlist = []
		return error, haserror

	def run_whisper_cli(self):
		self.get_filenames_split_wav()
		count = 0
		error = 0
		self.threadindex = 0
		self.threadoutputlist = []
		self.threadlist = []
		english_model_quotes = f'\"{self.englishmodel}\"'
		nonenglish_model_quotes = f'\"{self.nonenglishmodel}\"'
		for file in self.wavelist:

			if len(self.threadlist) >= self.threads: ## no more threads, start and wait for the ones in queue
				error, haserror = self.run_whisper_threads()
				if haserror:
					return error

			wave_file_quotes = f'\"{file}\"'
			
			command = f''
			if self.lang_code == 'en':
				command = f'whisper-cli -m {english_model_quotes} -f {wave_file_quotes} --output-srt --output-file \"{self.split_file_path}_{str(count)}\" -l {self.lang_code} -t 8 -pp -bs 8'
			else:
				command = f'whisper-cli -m {nonenglish_model_quotes} -f {wave_file_quotes} --output-srt --output-file \"{self.split_file_path}_{str(count)}\" -l {self.lang_code} -tr -t 8 -pp -bs 8'

			self.threadoutputlist.append((0,0))
			self.threadlist.append(threading.Thread(target=self.run_thead, args=(self.threadindex,command,'whisper-cli',self.logger,)))

			count = count + 1
			self.threadindex = self.threadindex + 1

		## finish running any additional threads
		error, haserror = self.run_whisper_threads()
		if haserror:
			return error
		
		self.concat_subtitle_files()
		
		final_subtile_file_quotes = f'\"{self.final_srt_temp_path}\"'
		
		self.logger.add_to_log(f'	Removing Duplicate SRT Lines in {self.final_srt_temp_path}')
		remove_adjacent_duplicate_text_lines(self.final_srt_temp_path)
		return error
	
	def process_object(self,row):
		self.clear_gen_object()
		self.video_path = row['filepath']
		self.video_path_file_name = os.path.splitext(os.path.basename(self.video_path))[0]
		self.final_directory = os.path.dirname(self.video_path)
		self.logger.add_to_log('Processing video file: ' + self.video_path)
		self.get_top_audio_stream()
		error = self.convert_audio_to_wav()
		if error == 0:
			self.get_language()
			if(self.lang_code != 'auto'):
				self.logger.add_to_log(f'	Generating subtitles for audio stream index: {self.top_audio_stream}, audio language: {self.lang_code}')
				error = self.run_whisper_cli()
				if error == 0:
					# Move the output .srt file
					self.move_output_file()
					##successfully created subtitles:
					self.subtitles_df.loc[len(self.subtitles_df)] = {
						'filepath': self.video_path,
						'has__english_subtitles': True,
						'subtitle_language': 'English',
						'subtitle_path': self.final_srt_path,
						'subtitle_stream': ''
					}
					self.subtitles_df.to_csv(self.subtitles_frame_filepath, sep='\t', index=False, quoting=csv.QUOTE_NONE)
				else:
					self.logger.add_to_log(f'	Error: {error} in Transcription / Translating File. Skipping: {self.video_path}')
			else:
				self.logger.add_to_log(f'	Language Not recognized. Skipping {self.video_path}')
		else:
			self.logger.add_to_log(f'	Error: {error} in Audio Copy. Skipping: {self.video_path}')
		remove_files_with_prefix(self.tempdir, self.video_path_file_name, self.logger)

	def init_path_object(self,dirname):
		self.clear_path_object()

		self.dirname = dirname
		log_filepath = f'GenAI_Logs/GenAILog_{self.dirname}.txt'
		self.logger = utilities.logger(log_filepath)
		self.subtitles_frame_filepath = f'GenAI_Logs/df_{self.dirname}.tsv'
		self.subtitles_df = pd.read_csv(self.subtitles_frame_filepath, sep='\t')
		grouped_df = self.subtitles_df.groupby('filepath')

		self.filtered_groups_no_subtitles = grouped_df.apply(filter_groups).reset_index(drop=True)
		self.filtered_groups_no_subtitles = self.filtered_groups_no_subtitles.groupby('filepath').nth(0).reset_index(drop=True)
		self.filtered_groups_no_subtitles.to_csv('GenAI_Logs/filtered_groups_' + dirname + '.tsv', sep='\t', index=False, quoting=csv.QUOTE_NONE)

	def clear_path_object(self):
		self.dirname = None
		self.subtitles_frame_filepath = None
		self.logger = None
		self.subtitles_df = None
		self.filtered_groups_no_subtitles = None
		self.clear_gen_object()

	def clear_gen_object(self):
		self.lang_code = None
		self.video_path = None
		self.top_audio_stream = None
		self.top_audio_language = None
		self.wav_path = None
		self.split_file_path = None
		self.whisper_json_path = None
		self.numfiles = None
		self.final_srt_path = None
		self.final_srt_temp_path = None
		self.final_directory = None
		self.language = None
		self.wavelist = None
		
	def process_videos(self,dirname):
		self.init_path_object(dirname)
		for index, row in self.filtered_groups_no_subtitles.iterrows():
			self.process_object(row)
		
def genaisubtitles(threads,tempdir, filepathlist, englishmodel, nonenglishmodel):
	transcribe_object = transcribe(threads,tempdir, englishmodel, nonenglishmodel)
	for file in filepathlist:
		filepath,dirname = file
		transcribe_object.process_videos(dirname)
