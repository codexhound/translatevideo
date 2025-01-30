import translatevideo.scansubtitles as scansubtitles
import translatevideo.genaisubtitles as genaisubtitles
import os
import pandas as pd
import argparse

def gensubtitles():
    parser = argparse.ArgumentParser()
    parser.add_argument("--rescan", help="rescan even if no prior scan done",action="store_true")
    parser.add_argument('--config_path', help='Config path')
    parser.add_argument('--threads', type = int, help='number of whisper batches at once (memory needed)')
    args = parser.parse_args()

    # Path to the TSV file
    config_path = 'config.tsv'
    if args.config_path != None:
        config_path = args.config_path

    threads = 1
    if args.threads != None:
        threads = args.threads

    # Read the TSV file into a DataFrame
    df_config = pd.read_csv(config_path, sep='\t')

    tempdir = ''
    englishmodel = ''
    nonenglishmodel = ''
    filepathlist = []

    # Iterate through each row and get values of each column
    for index, row in df_config.iterrows():
        configtype = row['type']
        filepath = row['filepath']
        name = row['name']
        if configtype == 'videopath':
            filepathlist.append((filepath,name))
        elif configtype == 'tempdir':
            tempdir = filepath
        elif configtype == 'nonenglishmodel':
            nonenglishmodel = filepath
        elif configtype == 'englishmodel':
            englishmodel = filepath        
        
    if tempdir == '':
        print('No temp processing directory set. Please set in config.tsv')
        return
    
    if englishmodel == '' or nonenglishmodel == '':
        print('Model is missing for audio transcription. Please set in config.tsv')
        return
    
    if len(filepathlist) == 0:
        print('No videopath set. Please add at least one video path to processes in config.tsv')
        return

    os.makedirs('GenAI_Logs', exist_ok=True)
    print(f'Temp Directory: {tempdir}')
    print(f'Video Processing Info: {filepathlist}')

    scansubtitles.scansubtitles(filepathlist,args.rescan)
    genaisubtitles.genaisubtitles(threads, tempdir, filepathlist, englishmodel, nonenglishmodel)

    return
	
# Defining main function
def main():
    gensubtitles()

# Using the special variable 
# __name__
if __name__=="__main__":
    main()
