import matplotlib.pyplot as plt
from more_itertools import flatten, collapse, is_sorted, unzip, duplicates_everseen, first_true, map_reduce, first, split_at, split_before, split_after, sliced, islice_extended, locate, first, last
from itertools import accumulate, groupby, repeat, starmap
import re
import os
import csv
import json
import pandas as pd 
import nltk 
from crossref.restful import Works
from Modules import preprocessing
from Modules import utils
from Modules import sections
from Modules import tables

def document_optics(title,text,n_cols,file=True,save_plot=False):
    '''
    Show OPTICS-ish plot for file/pages line lengths.

    args:
        title:  (str) file title to create base path to store doc data in
        text:   (str) text lines
        n_cols: (int) number of columns for the per page plot
    '''
    base_path = f"Output/{title}/Plots"
    if save_plot and not os.path.exists(base_path):
        os.mkdir(base_path)

    if file:
        lines = text.split("\n")
        plt.plot(range(len(lines)),list(map(len,lines)))
        plt.xlabel("line number")
        plt.ylabel("number of characters in line")
        plt.title(f"{title[:60]}-\n{title[60:]}." if len(title)>30 else title)

        if save_plot:

            plt.savefig(f"{base_path}/file_plot.png",format="png")
            # plt.savefig(f"{base_path}/file_plot.pdf",format="pdf")
        else:
            plt.show()

    else:
        text = re.sub(r"\(cid:\d+\)","",text).strip()
        pages = text.split("")
        n_pages = len(pages)
        
        # n_cols = 8 # change number of columns in pages plot
        n_rows = int(n_pages/n_cols) if n_pages%n_cols==0 else int(n_pages/n_cols)+1
        line_enumeration = []
        # print(n_rows,n_cols)
        _,ax = plt.subplots(n_rows,n_cols,figsize=(20,10))
        for row in range(n_rows):
            for col,page in enumerate(list(sliced(pages,n_cols))[row]):
                page_lines = page.split("\n")
                # print(row,col,len(page_lines))
                # print(ax[0][0])
                a = list(accumulate(line_enumeration))[-1] if line_enumeration else 0
                # ax[row][col].plot(range(len(page_lines)),list(it.repeat(txt_avg,len(page_lines))),color="red")
                ax[row][col].plot(range(a,a+len(page_lines)),list(map(len,page_lines)))
                ax[row][col].set_xlabel("Line number in txt file")
                ax[row][col].set_ylabel("Number of characters in line")
                ax[row][col].set_title(f"Page: {pages.index(page)+1}")
                line_enumeration.append(len(page_lines))

        t = "Basin-wide estimates of the input of methane from seeps and clathrates to the Black Sea"
        plt.suptitle(t,fontsize="xx-large")
        plt.subplots_adjust(left=0.1,bottom=0.1, right=0.9, top=0.9, wspace=0.4, hspace=0.4)

        if save_plot:
            # print(f"{base_path}/pages_plot.png")
            # utils.create_remove_dir(title,"Plots")
            # plt.savefig(f"{base_path}/pages_plot.png",format="png")
            plt.savefig(f"{base_path}/pages_plot.pdf",format="pdf")

        else:
            plt.show()


def plot_ft_positions(title,ft_idxs,pages):
    '''
    Plots a bar chart showing the amount 
    of table/figures-like lines for each page.

    args:
        title:      (str)   title of pdf
        ft_idxs:    (dict)  per page line indices of ft-like lines
        pages:      (list)  text split into pages
    '''
    x,y = list(zip(*[(pi,0) if not pi in ft_idxs.keys() else (pi,sum(map(len,ft_idxs[pi]))) for pi in range(len(pages))]))
    plt.bar(x,y)
    plt.xticks(range(len(pages)), range(1, len(pages)+1))
    plt.xlabel("page num.")
    plt.ylabel("num. of lines fitting table criteria")
    plt.title(f"{title[:3]}")
    plt.show()

def fts_match(l):
    '''
    Check if the line is a figure/table caption or a section title.
    args:
        l: (str) text line
    returns:
        if it is a f,t,s match: bool
    '''
    figure = lambda x: re.search(r"Fig\S{1,3} \d{1,2}(\.)*",x)
    table  = lambda x: re.search(r"Table \d{1,2}(\.)*",x)
    section = lambda x: re.search(r'([1-9](\.))+ ([A-Z]|\d+)\S+ ?(\S+ ?)+',x)
    return not (figure(l) or table(l) or section(l) or ("introduction" in l.lower()))

def get_ft_positions(title,text,plot=False,replace_ft_lines=False):
    '''
    Detect table- and figure-like lines from txt document by it their line lengths
    Important Notice!
        -it matters when the ft_positions will be detected by this algorithm, since every single
         extraction method will set lines to "" and therefore influence the outcome of this alg.
    args:
        title:  (str)   title of pdf
        text:   (str)   text unjoined
        plot:   (bool)  plot line detections
        replace_ft_lines: (bool) replace lines with "" from text
    returns:
        text: text with (or not) replaced lines
        ft_idxs: dictionary with for each page a list with 
                            ranges of line numbers ft-like lines
    '''

    pages = text.split("")
    avg = 60

    ft_idxs = {}
    # ft_caption = lambda s: re.search(r"Fig\S{1,3} \d{1,2}(\.)*",s) or re.search(r"Table \d{1,2}(\.)*",s)
    for pi,page in enumerate(pages):

        # text_lines = enumerate([(len(l)<avg/2 + 5) and not ft_caption(l) for l in page.split("\n")])
        text_lines = enumerate([(len(l)<avg/2 + 5) and fts_match(l) for l in page.split("\n")])
        # group by true or false
        # if pi == 6:
        #     print("================",list(text_lines))

        # filter out lines which possibly belong to table
        for _,g in groupby(text_lines,lambda x:x[1]):
            group = list(g)
            # this value mostly decides about if it's a table or not
            # maybe lower for better accuracy regarding table extraction
            if len(group)>10 and group[0][1]: 
                if pi not in ft_idxs:
                    ft_idxs[pi] = [range(group[0][0],group[-1][0])]
                else:
                    ft_idxs[pi].append(range(group[0][0],group[-1][0]))
    
    if plot:
        plot_ft_positions(title,ft_idxs,pages)

    if len(ft_idxs)>0:
        # pprint.pprint(ft_idxs)
        to_delete = sum(map(list,starmap(lambda v,k:zip(repeat(v),sum(map(list,k),[])),ft_idxs.items())),[])
        return (preprocessing.delete_by_idx(text,to_delete) if replace_ft_lines else text), ft_idxs
    else:
        return text,"no ft like lines found"

def get_ft_captions(title,text,save=False,replace_=False):
    '''
    Extract all the table and figure captions.
    args:
        title: (str) title of pdf
        text: (str) text unjoined
        save: (bool) save file as json
        replace_: (bool) replace lines with "" from text
    returns:
        text: text with (or not) replaced lines
        ft_captions: dictionary for each page with all table/figure captions
    '''
    pages = text.split("")
    page_lens = list(accumulate(map(len,[page.split("\n") for page in pages])))
    
    
    ft_captions,fig_idxs = {},[]
    for pi,page in enumerate(pages):
        page_lines = page.split("\n")
        # print(page_lines[:10])

        if pi not in ft_captions:
            ft_captions[pi] = {}

        blocks = list(enumerate(filter(lambda x:len(x)>0,split_at(enumerate(page_lines),lambda x: x[1]==''))))
        for bi,block in blocks:
            frst = first(block)[1] 
            
            # match different kinds of grafical data displayment
            fm = lambda x: re.search(r"Fig\S{1,3} {1,2}\d{1,2}(\.)?",x)
            tm = lambda x: re.search(r"Table(\.)? {1,2}([A-Z])?\d{1,2}(\.)*",x)
            pm = lambda x: re.search(r"Plate \d\.",x)
            # print(frst)
            if fm(frst) or tm(frst) or pm(frst):
                #sec_m.span()[0]==0
                # A table caption shouldnt have more than 9 lines
                # this might also produce some fails, be careful!!
                if tm(frst) and len(block)>9:
                    # idea: check whether after this block a table will begin
                    continue
                
                ft_name = fm(frst).group(0) if fm(frst) else (tm(frst).group(0) if tm(frst) else pm(frst).group(0))
                # maybe do this with the .span() method of the match object
                if ft_name in frst[:10] and not ")" in frst[:10] and ft_name not in ft_captions[pi]:
                    li,ft_caption = list(zip(*block))
                    # print(ft_caption)
                    ft_captions[pi][ft_name[0]+re.sub(r"\D","",ft_name)] = list(ft_caption) #" ".join(ft_caption).replace(ft_name,"").strip()
                    fig_idxs.append(list(zip(repeat(pi),li)))
            
                    # print(colored(ft_name,"red"))

            # vertical aligned tables
            # print(block)
            if all(starmap(lambda _,y:len(y)==1,block)):
                t_kw_li,t_kw = list(zip(*block)) # get word - possible "Table"
                t_kw = "".join(t_kw)[::-1].strip(" .") # join text block and reverse it
                # print(t_kw)
                if bi>0 and (t_kw=="Table" or t_kw=="Figure"):

                    # print(page_lens[pi-1]+t_kw_li[0])
                    # if t_kw = table, block before is its number
                    tn_li,t_num = list(zip(*blocks[bi-1][1])) 
                    t_num = "".join(t_num[::-1]).strip()
                    # print(t_num)

                    t_name = t_kw+" "+t_num 
                    if tm(t_name) or fm(t_name):
                        # print(colored(t_name,"green"))
                        
                        # search for caption (maximum 17 words now)
                        t_caption = []
                        for i in range(2,20):
                            if bi-i<0:
                                break

                            t_cap = "".join(list(zip(*blocks[bi-i][1]))[1]).strip()[::-1]
                            # old criteria, dont understand the reason for this
                            # t_cap = t_cap[::-1] if t_cap not in page_lines else "69" 
                            if sum(map(lambda x:x.isdigit(),t_cap))>1:
                                break

                            if t_cap=="(continued)":
                                t_caption.append(t_cap)
                                break

                            t_caption.append(t_cap)

                        if t_name not in ft_captions[pi]:
                            tn = re.sub(r"\D","",t_name)
                            ft_captions[pi]["VT"+tn if tm(t_name) else "F"+tn] = [" ".join(t_caption)]
    
    if save:
        with open(f"Output/{title}/captions.json","w",encoding='utf-8') as cap_file:
            json.dump(ft_captions,cap_file,sort_keys=True,indent=4)

    return (preprocessing.delete_by_idx(text,sum(fig_idxs,[])) if replace_ else text),ft_captions

def get_doi(meta,text):
    '''
    Extract DOI from metadata or text file.

    args:
        meta: (str) metadata as text
        text: (str) text of document
    returns:
        - text with replaced doi
        - doi
    '''
    t = lambda x: list(dict.fromkeys(x))
    re_doi = r"(10\.\d{4,5}\/[\S]+[^;,.\s])$"

    # find dois in meta data file
    meta_dois = [re.search(re_doi,line).group(0) for line in meta if re.search(re_doi,line)]
    
    # find and delete dois from text
    text_dois = []
    for pi,page in enumerate(text.split("")[:1]):
        for li,line in enumerate(page.split("\n")):
            doi_match = re.search(re_doi,line)
            if doi_match:
                # print(doi_match.group(0))
                text_dois.append((pi,li,doi_match.group(0)))
    
    r = list(zip(*text_dois))
    if len(r)>0:
        pi,li,text_dois = r[0],r[1],r[2]
        dois = max(t(meta_dois),t(text_dois))

        return preprocessing.delete_by_idx(text,zip(pi,li)),dois
    else:
        return text,t(meta_dois) if len(meta_dois)>0 else "no dois found"


def get_title(meta,text):
    '''
    Find the title in the metadata file or on first page of text file.

    args:
        meta: (str) metadata as text
        text: (str) text of document
    returns:
        title as str.
    '''
    titles = []
    res = [
        r"(10\.\d{4,5}\/[\S]+[^;,.\s])$",
        r"PII: S\d{4}-\d{4}\(\d{2}\)\d{5}-\d"
    ]

    jdf = pd.read_csv("Modules/journals.csv",delimiter=";")
    journals,sources = jdf.journal.to_list(),jdf.source.astype(str).to_list()

    for line in meta:
        if ":title" in line:
            title_idx = line.index("title") + 6
            title = line[title_idx:].strip()
            if not any(map(lambda x: re.search(x,title),res)) and len(title)>0:
                titles.append(title)
                # print(title)

    if not titles:
        blacklist = [
            "pii:",
            "mattilanew.indd",
            "abstract",
            "revised",
            "accepted:",
            "published online:",
            "universität",
            "doi",
            "available online"
        ]

        first_lines = text.split("\n")[:20]
        # print(first_lines)
        for fli,fl in enumerate(first_lines):
            line = fl.lower().replace("-"," ")
            # print(line)
            for j,s in zip(journals,sources):
                fl_ = fl.replace(" ","")
                # if re.search(r"PII: S\d{4}-\d{4}\(\d{2}\)\d{5}-\d",fl):
                #     print(fl)
                if j in line or s.lower() in line or any(map(lambda x:x in line,blacklist)) or sum(map(lambda x: x.isupper() or x.isdigit(),fl_))/len(fl_)>2/3 if len(fl_)>0 else len(fl_)==0:
                    # print(fl)
                    first_lines[fli] = ""
                    break

        filtered_lines = [l for l in list(filter(lambda x:len(x)>0,split_at(first_lines,lambda x: x==""))) if len(l[0])>10]
        if filtered_lines:
            return " ".join(filtered_lines[0])
        else:  
            return "no title found"

    return first(set(titles))


def get_keywords(text):
    '''
    Search for keywords like "keywords:",
    "index terms:" on first page of document.

    args:
        text: (str) document text.
    returns:
        - text with replaced keywords
        - extracted keywords
    '''
    pages = text.split("")
    first_page = pages[0].split("\n")
    keywords = []

    for block in filter(lambda x: len(x)>0,split_at(enumerate(first_page),lambda x: x[1]=='')):
        tbl = block[0][1].lower()[:10]
        if "keywords" in tbl or "key words" in tbl:
            keywords.append(block)

        for l in block:
            if "index terms:" in l[1][:13].lower():
                keywords.append(block[block.index(l):])
                break

    kws = list(zip(*sum(keywords,[])))
    if len(kws)>0:
        kw_idxs,kws = kws[0],kws[1]
        return preprocessing.delete_by_idx(text,zip(repeat(0),kw_idxs))," ".join(kws)
    else:
        return text, "no keywords found"

def get_citation(text):
    '''
    Search for citation on first page of document.

    args:
        text: (str) document text.
    returns:
        - text with replaced citations
        - citations as str.
    '''
    pages = text.split("")
    first_page = pages[0].split("\n")
    citation = []
    for block in filter(lambda x: len(x)>0,split_at(enumerate(first_page),lambda x: x[1]=='')):
        if "citation:" in block[0][1].lower()[:10]:
            citation.append(block)
        
        for l in block:
            if "citation:" in l[1][:13].lower():
                citation.append(block[block.index(l):])
                break

    cite = list(map(list,unzip(sum(citation,[]))))
    if len(cite)>0:
        cite_idxs,cite = cite[0],cite[1]
        return preprocessing.delete_by_idx(text,zip(repeat(0),cite_idxs)), " ".join(cite)
    else:
        return text, "no citation found"



def get_pub_dates(text):
    '''
    Search publication dates on first page of document.

    args:
        text: (str) text of document.
    returns:
        - text with replaced dates
        - extracted dates as str.
    '''
    pages = text.split("")
    first_page = pages[0].split("\n")
    x = []

    re_pub = r"(\()*(Received|Accepted|accepted) ([A-Z]\S{2,8} \d{1,2}|\d{1,2} [A-Z]\S{2,8})+(,)* \d{4}"
    for block in filter(lambda x: len(x)>0,split_at(enumerate(first_page),lambda x: x[1]=='')):
        if re.search(re_pub,block[0][1]):
            x.append(block)

    r = list(map(list,unzip(sum(x,[]))))
    if len(r)>0:
        idxs,result = r[0],r[1]
        return preprocessing.delete_by_idx(text,zip(repeat(0),idxs))," ".join(result)
    else:
        return text,"no pub dates found"

def get_copyright(text):
    '''
    Detect copyright (publisher) from first page of document.

    args:
        text: (str) text of document.
    returns:
        - text with replaced copyright
        - copyright as str.
    '''
    pages = text.split("")
    first_page = pages[0].split("\n")
    a = lambda l: "all rights reserved" in l.lower()
    b = lambda l: chr(169) in l.lower()
    # c = lambda l: f"copyright {chr(169)}" in l.lower()

    copyright = []
    for li,line in enumerate(first_page):
        if a(line):
            copyright.append((li,line))
        if b(line):
            # this will probably delete sentence from abstract
            copyright.append((li,line[line.index(chr(169)):]))

    r = list(zip(*copyright))
    if len(r)>0:
        return preprocessing.delete_by_idx(text,zip(repeat(0),r[0])),list(set(r[1]))
    else:
        return text,"no copyright found"

def get_authors(text):
    '''
    Detect authors by NER with spacy models.

    args:
        text: (str) text of document.
    returns:
        - text with replaced author names
        - authors names as str.
    '''
    import spacy
    nlp_en = spacy.load("en_core_web_sm")
    nlp_zh = spacy.load("zh_core_web_sm")

    to_delete, authors = [],[]
    for li,l in enumerate(text.split("")[0].split("\n")[:30]):
        if "abstract" in l.lower():
            # print("breaked")
            break

        if any([ent.label_ == "PERSON" for ent in nlp_en(l).ents]):
            # print(li,l)
            to_delete.append((0,li))
            authors.append(l)

        if any([ent.label_ == "PERSON" for ent in nlp_zh(l).ents]):
            # print(li,l)
            to_delete.append((0,li))
            authors.append(l)

    return preprocessing.delete_by_idx(text,to_delete), " ".join(authors)




def get_institutions(text):
    '''
    Detect the cooperating institutions from text.

    args:
        text: (str) text of document.
    returns:
        - text with replaced institution names
        - institution names as str.

    '''
    pages = text.split("")
    first_page = pages[0].split("\n")

    email = r"([-!#-'*+/-9=?A-Z^-~]+(\.[-!#-'*+/-9=?A-Z^-~]+)*|\"([]!#-[^-~ \t]|(\\[\t -~]))+\")@([-!#-'*+/-9=?A-Z^-~]+(\.[-!#-'*+/-9=?A-Z^-~]+)*|\[[\t -Z^-~]*])"
    names = r"([A-Z]\S+ [A-Z]. [A-Z]\S+,)+"
    editor = r"((A|a)ssociate)* editor:" 
    institution = r"(Institute|School|Universit(y|é|ät)|D(e|é)part(e)*ment|Laborato(ire|ry))+ (of|de|d'|for)"
    regexes = [email,names,editor,institution]

    blocks = []
    for block in filter(lambda x: len(x)>0,split_at(enumerate(first_page),lambda x: x[1]=='')):
        for li,line in block:
            if any(map(lambda regex: re.search(regex,line),regexes)):
                blocks.append(block)
                break

    r = list(zip(*sum(blocks,[])))
    if len(r)>0:
        return preprocessing.delete_by_idx(text,zip(repeat(0),r[0])),r[1]
    else:
        return text,"no authors or institutions found"

def get_urls(text):
    '''
    Extract any urls from the first page.

    args:
        text: (str) text of document.
    returns:
        - text with replaced urls
        - urls as str.
    '''
    pages = text.split("")
    first_page = pages[0].split("\n")

    url = r"((http[s]?:\/\/)|(www\.))[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()!@:%_\+.~#?&\/\/=]*)"
    blocks = []
    for block in filter(lambda x: len(x)>0,split_at(enumerate(first_page),lambda x: x[1]=='')):
        for li,line in block:
            if re.search(url,line):#any(map(lambda regex: re.search(regex,line),regexes)):
                blocks.append(block)
                break

    r = list(zip(*sum(blocks,[])))
    if len(r)>0:
        return preprocessing.delete_by_idx(text,zip(repeat(0),r[0])),r[1]
    else:
        return text,"no urls found"



def get_abstract(text):
    '''
    Extract the abstract from the first page.

    args:
        text: (str) text of document.
    returns:
        - text with replaced urls
        - abstract as str.
    '''
    first_page = text.split("")[0].split("\n")

    # do some preprocessing
    for li,line in enumerate(first_page):

        # if "abstract" embedded like this "Abstract - Science ..."
        # put it into seperate string in order to split lists more efficient
        if "abstract" in line.lower() and not all(map(lambda x: x=="",line.lower().split("abstract"))):
            split_list = line.lower().split("abstract")
            first_page.insert(li,"abstract")
            first_page.insert(li+1,split_list[-1])
            first_page.remove(line)
            break

        if "a b s t r a c t"==line.lower().strip():
            first_page.insert(li,"abstract")
            first_page.remove(line)
            break

    # get everything after abstract
    lines = list(split_at(enumerate(first_page), lambda x: 'abstract' in x[1].lower()))[-1]
    # get everything before introduction
    lines = list(split_at(lines,lambda x: 'introduction' in x[1].lower()))[0]
    
    t,abstr = 0,[]
    for block in filter(lambda x:len(x)>0,split_at(lines,lambda x:x[1]=='')):
        if t <= 600 and sum(map(lambda line:len(line[1])>80,block))/len(block)>=2/3:
            # append this block to abstract
            t += len(nltk.word_tokenize(" ".join(list(map(list,unzip(block)))[-1])))
            abstr.append(block)

    if len(list(map(list,unzip(sum(abstr,[])))))==0:
        t,abstr = 0,[]
        for block in filter(lambda x:len(x)>0,split_at(lines,lambda x:x[1]=='')):
            if t <= 600 and sum(map(lambda line:30<len(line[1])<=65,block))/len(block)>=2/3:
                # append this block to abstract
                t += len(nltk.word_tokenize(" ".join(list(map(list,unzip(block)))[-1])))
                abstr.append(block)

    abstr = list(zip(*sum(abstr,[])))
    if len(abstr)>0:
        nums, abstract = abstr[0], " ".join(abstr[1]).lstrip(" -.[]1234567890")
        return preprocessing.delete_by_idx(text,zip(repeat(0),nums)),abstract
    else:
        return text, "no abstract found"

def clear_metadata_file():
    metadata_path = "Output/all_files_metadata.csv"
    if os.path.exists(metadata_path):
        os.remove(metadata_path)

def write_meta_to_csv(m,ft_captions,out_dir,meta_path,clear_metadata=False):
    '''
    Write all the extracted metadata into a csv file.

    args:
        m: (list) with all the metadata attributes per document
    '''
    # write the extracted metadata list "m" to csv file
    metadata_path = "Output/all_files_metadata.csv"

    components = parse_component_dirs(out_dir)
    num_ft_caps = get_num_ft_caps(ft_captions)
    num_pages = get_num_pages(meta_path)
    num_sents = get_num_sents(out_dir)
    num_table_fails = tables.detect_wrongly_extracted_tables(out_dir)
    is_rec_struct  = sections.is_recursively_structured(out_dir)
    text_extr_fail = int(utils.has_text_extraction_fail(out_dir))
    # print(list(zip(*num_ft_caps)))
    # print(list(list(zip(*sorted(num_ft_caps)))[1]))
    m += list(list(zip(*sorted(num_ft_caps)))[1]) + components + [num_table_fails,num_pages,num_sents,is_rec_struct,text_extr_fail] 
    if not os.path.exists(metadata_path):
        with open(metadata_path,"w",encoding='utf-8') as fmd:
            writer = csv.writer(fmd,lineterminator="\n",quoting=1)
            writer.writerow([
                "doc_idx",
                "doc_enum",
                "title",
                "dois",
                "copyright",
                "keywords",
                "citation",
                "abstract",
                "figure_captions",
                "table_captions",
                "figures_extracted",
                "images_extracted",
                "tables_extracted",
                "table_fails",
                "pages",
                "sentences",
                "sections_extr_success", # some false negatives included, need to be checked
                "text_extraction_fail"
            ])
            writer.writerow(m)
    else:
        with open(metadata_path,"a",encoding='utf-8') as fmd:
            writer = csv.writer(fmd,lineterminator="\n",quoting=1)
            writer.writerow(m)


def parse_component_dirs(out_dir):
    '''
    Check in the output dir if and how many data were extracted for a data component.
    '''
    components = [
        "Figures",
        "Images",
        "Tables"
    ]
    num_files = lambda p: len(os.listdir(p)) if os.path.exists(p) else 0
    return list(map(num_files,[f"Output/{out_dir}/{c}" for c in components]))


def get_num_ft_caps(ft_captions):
    all_caps,keyfunc = [re.sub(r"\d","",k) for v in ft_captions.values() for k in v.keys()], lambda x: x.upper()
    mr = map_reduce("".join(all_caps),keyfunc).items()
    res = list(starmap(lambda x,y: (x,len(y)),mr))
    if not res:
        return [-1,-1]
    elif len(res)==1:
            return [('F',0),res[0]] if res[0][0] == 'T' else [res[0],('T',0)]
    elif len(res)>2:
        return res[-2:]
    return res



def get_num_pages(meta_path):
    with open(meta_path,"r") as meta_file:
        for line in list(meta_file.readlines()):
            if "xmpTPg:NPages" in line: 
                return int(re.sub(r"\D","",line.split(" ")[-1]))

        return -1


def get_num_sents(out_dir):
    p = f"Output/{out_dir}/sections.json"
    if os.path.exists(p):
        with open(p,"r") as sections_file:
            return sections.count_sents(json.load(sections_file))
    else:
        return -1



def crossref_request(dois):
    import requests
    if dois:
        try:
            return Works().doi(dois[0])
        except requests.exceptions.JSONDecodeError as e:
            print(e)

def post_process_metadata():
    path = "Output/all_files_metadata.csv"
    if os.path.exists(path):
        try:
            df = pd.read_csv(path)
            df.fillna(0,inplace=True)
            df['text_extraction_fail'] = df['text_extraction_fail'].astype(int)
            df.to_csv(path,index=False)
        except Exception as e:
            import traceback
            print(traceback.format_exc())

























