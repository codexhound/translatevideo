import translatevideo.scansubtitles as scansubtitles
import translatevideo.genaisubtitles as genaisubtitles
import os
import pandas as pd

def gensubtitles():
    # Path to the TSV file
    config_path = 'config.tsv'

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
        exit
    
    if englishmodel == '' or nonenglishmodel == '':
        print('Model is missing for audio transcription. Please set in config.tsv')
    
    if len(filepathlist) == 0:
        print('No videopath set. Please add at least one video path to processes in config.tsv')
        exit

    os.makedirs('GenAI_Logs', exist_ok=True)
    print(f'Temp Directory: {tempdir}')
    print(f'Video Processing Info: {filepathlist}')

    scansubtitles.scansubtitles(filepathlist)
    genaisubtitles.genaisubtitles(tempdir, filepathlist, englishmodel, nonenglishmodel)
	
# Defining main function
def main():
    gensubtitles()

# Using the special variable 
# __name__
if __name__=="__main__":
    main()
