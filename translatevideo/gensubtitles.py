#import argparse
import os
from scansubtitles import *
from genaisubtitles import *
import pandas as pd

'''
parser = argparse.ArgumentParser(description='Script so useful.')
parser.add_argument("tempdir")
parser.add_argument("dirpath1")
parser.add_argument("dirname1")
parser.add_argument("dirpath2")
parser.add_argument("dirname2")
parser.add_argument("istv1")
parser.add_argument("istv2")

args = parser.parse_args()

tempdir = args.tempdir
dirpath1 = args.dirpath1
dirname1 = args.dirname1
dirpath2 = args.dirpath2
dirname2 = args.dirname2
istv1 = args.istv1
istv2 = args.istv2
'''

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
        isseries = int(row['isseries'])
        if configtype == 'videopath':
            filepathlist.append((filepath,name,isseries))
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

    scansubtitles(filepathlist)
    genaisubtitles(tempdir, filepathlist, englishmodel, nonenglishmodel)

#########################################################################  
  
gensubtitles()

#########################################################################  


