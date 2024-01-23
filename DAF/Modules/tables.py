import camelot
import fitz 
import pandas as pd 
import pprint
import re
import os
from math import isnan
from Modules import preprocessing
from Modules import utils
from collections import Counter
from operator import itemgetter
from itertools import accumulate, groupby, repeat, starmap
from more_itertools import first,last
import warnings
warnings.filterwarnings("ignore")

def rotate_page(path,page_n,degrees):
    '''
    Rotate a page in a pdf.
    args:
        path:  (str) path of the pdf to rotate a page in
        page_n : (int) number of the page which has to be rotated
        degrees: (int) number of rotation degrees
    '''
    doc = fitz.open(path) # open pdf file
    page = doc[page_n]   # get page_n
    page.set_rotation(degrees)      
    doc.save(doc.name,incremental=True,encryption=0) 
    doc.close()

def csv_postprocessing(base_path):
    '''
    Postprocess the extracted table:
        - replace cids
        - drop empty rows and cols
    args:
        base_path: (str) path to the tables directory.
    '''
    base_path = base_path+"Tables/"
    if os.path.exists(base_path):
        files = filter(lambda x:x!=".DS_Store",os.listdir(base_path))

        for file in files:
            try:
                df = pd.read_csv(f"{base_path}/{file}")
                df = df.applymap(lambda x: preprocessing.replace_cids(str(x))) # replacing cids in every table cell
                df = df.fillna("").reset_index(drop=True)

                # process df
                # df = df.applymap(lambda x: "" if len(str(x))>35 else x) # filter non-table values
                df = df.drop([i for i,row in df.iterrows() if all([x=="" for x in list(row)])]) # drop empty rows
                df = df.drop(df.columns[[i for i,(_,col) in enumerate(df.iteritems()) 
                    if len(col)>0 and len(list(filter(lambda x:x!="",col)))/len(col)<0.1]],axis=1) # drop "empty" cols
                
                df.to_csv(f"{base_path}/{file}",index=False,header=False)
            except pd.errors.EmptyDataError as e:
                utils.write_to_logfile(title.split("_")[0],"Tables",e) 
                os.remove(f"{base_path}/{file}")

def print_lines_and_groups(is_tl,texts,egs):
    '''
    Print captions and ft-like lines.
    Print side by side if a line was detected an t-like and the line.
    Print group-idx and group-length and group.

    args:
        is_tl: (list) list of bools for table-like lines detection
        texts: (list) text lines
        egs: (list) table groups
    '''
    pprint.pprint(ft_captions)
    pprint.pprint(ft_idxs)
    # print lines and groups
    for i in range(len(is_tl)):
        print(int(is_tl[i]),texts[i])#, re.search(r"[1-9](\.) ([A-Z]\S+ ?)(\S+ ?)+",texts[i]))

    for egi,eg in enumerate(egs,start=1):
        print(egi,"len",len(eg))
        print(eg)
        print()
    # print(word_count[0][0])

def get_table_lines_and_groups(texts):
    '''
    Detect and group table-like lines.

    args:
        texts: (list) text lines.
    returns:
        - bool mapping list if lines is table line
        - grouping of table like lines
    '''
    # !!! with this approach 3:d35 got worse, pls check it out
    # common problem: single lines can be >30 due to wrong extraction or just authors did this
    # check if line after or before belongs to table
    # check if next line not equal Table \d and is <30 
    is_table_line = []
    word_count = list(filter(lambda x:len(str(x[0]))>1,Counter(texts).items()))
    word_count.sort(key=lambda x: x[1], reverse=True)
    p_header = word_count[0][0]
    ph = lambda l:True# l!=p_header and not p_header.isdigit() # is not page header
    f = lambda _:False

    for li,line in enumerate(texts):

        if "introduction" == line.lower() or re.search(r"1\. (I|i)ntroduction",line):
            is_table_line = list(map(f,is_table_line))

        if "references" == line.lower() and li/len(texts)>0.8:
            for _ in range(len(texts)-li):
                is_table_line.append(False)
            break



        # if fig caption set all before to false
        # fm = lambda l: re.search(r"Fig(ure)*\. \d{1,2}(\.)?",l)
        # if fm(line) and fm(line).span()[0]==0:
        #     j = li-1
        #     while is_table_line[j]:
        #         is_table_line[j] = False 
        #         j-=1

        if li<len(texts)-1:
            before,after = texts[li-1],texts[li+1]
            tm = lambda x: re.search(r"Table \d",x)
            sm = lambda x: re.search(r"[1-9](\.) ([A-Z]\S+ ?)(\S+ ?)+",x)
            not_tm = not tm(after) # b or a is not table caption
            not_sm = not(sm(line) and sm(line).span()[0]==0)
            if len(line)<35:
                # check if line not table caption amtch
                is_table_line.append(ph(line) and not_tm)

            else:
                cl = lambda l,x:len(x)<35 or l==x

                ### the conditions here determine whether the extraction will be accurate or not
                ba_len = cl(line,before) and cl(line,after) # line b or a is <35 or duplicate
                # is not followed by a line of vertical table
                not_vt = not any(map(lambda i:len(texts[i])==1,range(li,li+3))) if li<len(texts)-4 else True
                is_table_line.append(ba_len and not_vt and not_tm and not_sm)

    # create groups by line length for the file with text boxes coordinates
    egs = [] # list of lists with (line_idx,text) as elem in each list
    for _,g in groupby(enumerate(is_table_line),lambda t:t[1]):
        enum,group = list(zip(*g))
        # take line which has been detected a table line and there are more than 10 table lines
        if first(group) and len(group)>10:
            eg = zip(enum,itemgetter(*enum)(texts))
            eg = list(filter(lambda x:len(x[1])<35,eg))
            # eg = list(filter(lambda x:not re.search(r"Table \d",x[1]),eg))

            # for vertical table:
            # check if its at least 75% of lines which have length 1 and its more than 100
            if sum(map(lambda x:len(x[1])==1,eg))/len(eg)>0.75:
                if len(eg)>100:
                    # print("moin")
                    # print(len(eg))
                    egs.append(eg)
                continue 
            elif len(eg)>14:
                eg = list(filter(lambda x:len(x[1])>1 and x[1]!="Ž",eg))
                egs.append(eg)

    return is_table_line,egs

# def extract_with_camelot(pdf_path,base_path,k,ti,x_1,x_2,y_2,y_2):
#     table = camelot.read_pdf(pdf_path, pages=f'{k+1}',flavor='stream', 
#         strip_text='\n', table_areas=[f"{x_1},{y_1},{x_2},{y_2-10}"])
#     table.export(f"{base_path}/table{ti}.csv",f="csv")


#### extract tables by xy1,xy2 coordinates
def extract_tables(path,ft_captions,ft_idxs,base_path,title):
    '''
    Main table extraction function. 
    - call table-like lines detection
    - find table caption indices 
    - get table coordinates
    - extract with camelot and save

    args:
        path: (str) path to .pdf file
        ft_captions: (dict) per page captions
        ft_idxs: (dict) per page ft-like lines line indices ranges
        base_path: (str) path to general output directory

    '''

    ti = 0 # count var to select current table group
    # base_path = f"Document_Data/{title}/Tables"#"Table_Extraction/{f_name}/"
    df = pd.read_csv(f"Input/{title}/coords.csv")
    x1,y1,x2,y2,texts = list(zip(*list(zip(*df.iterrows()))[1]))
    texts = list(map(preprocessing.preprocess,map(str,texts)))
    is_table_line,egs = get_table_lines_and_groups(texts)
    base_path = base_path+"/Tables/"

    # print_lines_and_groups(is_table_line,texts,egs)


    # if not os.path.isdir(base_path):
    #     os.mkdir(base_path)

    table_xy = []
    padding = 10
    for k,v in ft_captions.items():

        # if no caption for this page but the page idx ist still in the dictionary
        # which stores the pages and their corresponding table lines 
        if len(v)==0 and k in ft_idxs.keys():
            # is there >X lines which look like table lines on this page ?
            if sum(map(lambda x: last(x)-first(x),ft_idxs[k]))>380:
                try:
                    table = camelot.read_pdf(path, pages=f'{k+1}',flavor='stream',strip_text='\n')
                    table.export(f"{base_path}/no_caption.csv",f="csv")
                except Exception as e:
                    # print(e)
                    utils.write_to_logfile(title.split("_")[0],"Tables",e) 

        # if no table like lines were found skip the for loop
        # and just pass every page to camelot and maybe extract a table
        if not egs:
            continue

        for ft,caption in sorted(v.items()):
            # horizontal aligned table
            if ft[0]=="T":
                
                ### get xy1 by table caption
                try:
                    i1 = texts.index(f"Table {ft[-1]}")
                except ValueError:
                    try:
                        i1 = texts.index(caption[0].strip())
                    except ValueError:
                        # print("Horizontal-Vertical Layout fail for table:",ft)
                        table = camelot.read_pdf(path, pages=f'{k+1}',flavor='stream',strip_text='\n')
                        table.export(f"{base_path}/table{ft[-1]}.csv",f="csv")
                        continue

                # select group by table caption line idx
                while True:
                    try:
                        enum, group = list(zip(*egs[ti])) 
                        # print(group,type(group))
                        # if caption index is greater than last group line, it is the wrong group
                        # table caps are always before the table
                        if i1 > enum[-1]:
                            ti+=1
                        else:
                            break
                    except IndexError as e:
                        # print(f"Error: ti={ti} {e}")
                        utils.write_to_logfile(title.split("_")[0],"Tables",f"Error: ti={ti} {e}") 
                        break

                ### get xy2 by last line of table
                # this will fail or produce distorted results if 
                # a) table wrongly extracted or b) last line not unique in table
                i2 = 0
                eval_line = lambda l: len(re.findall(r"\d",l))/len(l)>=2/3
                for i in range(1,10):
                    t = group[-i].strip()
                    if len(t)==0:
                        continue
                    if eval_line(t) or (t.isalpha() and len(t)<30):
                        i2 = enum[-i]
                        break

                # x_1,y_1 = x1[i1],y1[i1] # bottom left
                x_1,y_1 = x1[i1],y2[i1] # top left
                try:
                    # x_2,y_2 = x2[i2],y2[i2]
                    x_2,y_2 = max(itemgetter(*enum)(x2)),min(itemgetter(*enum)(y2)) # xy2 table span
                    # print(f"page {k}",ft,f"{x_1},{y_1},{x_2},{y_2}",i1, "ti:",ti)
                    # table_xy.append((x_1,y_1,x_2,y_2))
                    table = camelot.read_pdf(path, pages=f'{k+1}',flavor='stream', 
                        strip_text='\n', table_areas=[f"{x_1},{y_1},{x_2},{y_2-padding}"])
                    table.export(f"{base_path}/table{ft[-1]}.csv",f="csv")


                except (ZeroDivisionError,ValueError):
                    # fall back option: get xy2 from last line of table group
                    try:
                        x_2,y_2 = x2[i2],y2[i2]
                        # x_2,y_2 = max(itemgetter(*enum)(x2)),min(itemgetter(*enum)(y2))
                        table = camelot.read_pdf(path, pages=f'{k+1}',flavor='stream', 
                            strip_text='\n', table_areas=[f"{x_1},{y_1},{x_2},{y_2}"])
                        table.export(f"{base_path}/table{ft[-1]}.csv",f="csv")
                    except (ZeroDivisionError,ValueError):
                        # print("error for ", ft)
                        try:
                            # pass page without any region specifications
                            table = camelot.read_pdf(path, pages=f'{k+1}',flavor='stream',strip_text='\n')
                            table.export(f"{base_path}/table{ft[-1]}.csv",f="csv")
                        except Exception as e:
                            # print(e)
                            utils.write_to_logfile(title.split("_")[0],"Tables",e)


                ti+=1


            # vertical aligned table
            if ft[0]=="V":
                # print(ft,caption)
                x_1,y_1,x_2,y_2 = 0,0,0,0
                t_cap = f"Table{ft[-1]}." + "".join(caption).replace(" ","") # replace all whitespace in caption (due to vertical layout)
                for txti,text in enumerate(texts):
                    # if "T" found, lookbehind if its table caption match
                    if text=="T" and all([texts[txti-i]==c for i,c in zip(range(len(t_cap)),t_cap)]):
                        x_1,y_1 = itemgetter(txti)(list(zip(x1,y1))) # select xy1 via idx of "T"

                        # search if any group includes the idx of "T"
                        for eg in egs:
                            enum,group = list(zip(*eg))
                            if txti in enum:
                                enum,group = list(zip(*filter(lambda x:len(x[1])==1,eg)))
                                x_2,y_2 = 750,max(itemgetter(*enum)(x2))
                                break

                        break

                rotate_page(path,k,90)
                try:
                    if (x_1,y_1,x_2,y_2) == (0,0,0,0):
                        raise ZeroDivisionError
                    table = camelot.read_pdf(path, pages=f'{k+1}',flavor='stream', 
                        strip_text='\n', table_regions=[f"{x_1},{y_1},{x_2},{y_2}"])
                    table.export(f"{base_path}/table{ft[-1]}.csv",f="csv")
                except ZeroDivisionError:
                    # pass page without any region specifications
                    table = camelot.read_pdf(path, pages=f'{k+1}',flavor='stream',strip_text='\n')
                    table.export(f"{base_path}/table{ft[-1]}.csv",f="csv")
                rotate_page(path,k,0)

                ti+=1

         
def detect_wrongly_extracted_tables(title):
    fails = 0
    base_path = f"Output/{title}/Tables/"
    if os.path.exists(base_path):
        for t in filter(lambda x:x.endswith(".csv"),os.listdir(base_path)):
            try:    
                df = pd.read_csv(base_path+t)
            except pd.errors.EmptyDataError as e:
                fails +=1
                utils.write_to_logfile(title,"Tables",f"Detected table fail for {t}.")
                continue

            nr,nc = df.shape
            rows = [list(row)[0]for _,row in df.iterrows()]
            if nc<=2 and nr>0 and sum(map(lambda r: r>30,map(lambda x: len(str(x)),rows)))/nr>0.9:
                fails += 1
                utils.write_to_logfile(title,"Tables",f"Detected table fail for {t}.")
    return fails


def get_tables(pdf_path,title,ft_captions,ft_idxs):
    '''
    Extract tables from the pdf file.
    args:
        pdf_path:      (str) path to dir. where .pdf file is stored
        title:         (str) the title of the pdf file -> key to dir
        ft_captions:   (dict) all figure/table captions of the document
        ft_idxs:       (dict) for every page and every table/figure on that page, 
                            a range(x,y) is stored with the line indices for the lines which fit the <35 condition
    '''

    base_path = f"Output/{title}/"

    # get tables

    utils.create_remove_dir(title,"Tables")
    extract_tables(pdf_path,ft_captions,ft_idxs,base_path,title)
    # csv cleaning algorithm
    csv_postprocessing(base_path)
    utils.create_remove_dir(title,"Tables",create=False)

    





