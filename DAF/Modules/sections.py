from more_itertools import split_at, locate, first, collapse
from itertools import islice
from math import inf
import json
import functools as ft 
import re
import os
from Modules import utils

def import_spacy():  
    import spacy 
    nlp = spacy.load("en_core_web_sm")
    return nlp

def insert_key(d,k,n):
    '''
    Insert a new key in section corpus, which was 
    found by section title detection algorithm. 

    args:
        d: (dict) to insert new key for
        k: (str) new key to be inserted
        n: (int) search depth parameter
    returns:
        the dict with (maybe) a newly inserted key
    '''
    # print(d,k)
    if len(d) == 0:
        d[k] = {"text":[]}

    elif k[:n] in d.keys() and len(k)>len(list(d.keys())[list(d.keys()).index(k[:n])]):
        insert_key(d[k[:n]],k,n+1)

    x = list(d)[-1]
    if x=="text":
        if n==len(k):
            d[k] = {"text":[]}

    elif int(k[:n])-int(x)==1 and n==len(k):
        d[k] = {"text":[]}

    return d

def count_sents(d):
    return sum(map(lambda v:(len(d['sentences']) if "sentences" in d else 0) + (sum(collapse(count_sents(v))) if isinstance(v,dict) else 0),d.values()))

def flatten_dict(d):
    '''
    Get the number of all items in the dictionary.
    This method is used to check if a new key was inserted.
    Then the key in the in extraction method will be changed and
    only the current key text will be inserted.

    args:
        d:  (dict) to check the number of items
    returns:
        number of all items
    '''
    if isinstance(d,dict):
        return len(d) + sum(map(flatten_dict,d.values()))
    return 0

def insert_text(d,k,n,text):
    '''
    Append section text to a section.

    args:
        d:      (dict) sections
        k:      (str) key to section to append text to
        n:      (int) section depth
        text:   (list) text as paragraph (list of lists) to be inserted
    returns:
        sections with more text than before
    '''
    if n==len(k):
        text = " ".join(text).strip(" \n\f")
        d[k]["text"].append(text)
    elif k[:n] in d.keys():
        insert_text(d[k[:n]],k,n+1,text)
    return d

def has_recursive_struct(d,n):
    '''
    Check if the extracted sections section numbering is in order.
    ... i.e. it follows the pattern of the document enumeration.

    args:
        d: (dict) dictionary to check the keys for
        n: (int) for the current search depth the parent key
            (if all values for sec. 3 are checked, 3 is passed and multiply by 10
            to check if it's in order with 3.1. -> 30<31<32 etc.)
    returns:
        bool if it is in order
    '''
    get_digit_str = lambda x: re.sub(r"\D","",x.split(" ")[0])
    reducefunc = lambda l: ft.reduce(lambda x,y: y if 1<=(y-x)<=2 else inf,l)!=inf

    j = ['text','sentences','title']
    keys = list(filter(lambda x: x!='text',d.keys()))
    keys = list(map(lambda x: get_digit_str(x),keys))
    keys = list(map(int,filter(lambda x: x.isdigit(),keys)))
    if len(keys)>0:
        l = []
        for k,v in d.items():
            if isinstance(v,dict):
                parent_key = int(get_digit_str(k))
                l.append(has_recursive_struct(v,parent_key))
        return reducefunc([n*10]+keys if n!=0 else keys) and all(l)
    else:
        return len(keys)==0

def is_recursively_structured(o):
    if os.path.exists(f"Output/{o}/sections.json"):
        with open(f"Output/{o}/sections.json","r") as s:
            secs = json.load(s)
            N = [i for i,k in enumerate(secs.keys()) if not k.isdigit()][0]
            pure_secs = dict(islice(secs.items(), N))
            return int(has_recursive_struct(pure_secs,0) and not len(pure_secs.keys())==2)
    return 0

def insert_blank_lines(lines):
    '''
    If there is no empty line between a section title and its 
    first paragraph it is not detectable. If the this case accounts
    insert new lines between section title and its following text.

    args:
        lines: (list) text split into lines
    returns:
        lines with empty lines between section title and its first paragraph
    '''
    date_ = r"[1-9]{1,2} (Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) \d{4}"
    k = r'([1-9](\.))+ ([A-Z]|\d+)\S+ ?(\S+ ?)+'
    for li,line in enumerate(lines): 
        m,date = re.search(k,line),re.search(date_,line)
        if m and m.span()[0]==0 and not date and li<len(lines)-1:
            if lines[li+1]!="":
                lines.insert(li+1,'')
                continue

            if lines[li-1]!="":
                lines.insert(li,'')
    return lines

def append_extra_secs(d,d_):
    '''
    Append auxiliary sections like the below mentioned.

    args:
        d:  (dict) sections to parse the auxiliary sections from
        d_: (dict) sections to append the auxiliarys to 
                (at the first call of this method d equals d_)

    returns: 
        sections with the append auxiliary sections
    '''
    for _,v in d.copy().items():
        if isinstance(v,dict):
            append_extra_secs(v,d_)
        elif d['text']:
            text,del_from_text = d['text'],[]

            # if one of those key words found insert new k,v pairs in dict
            extra_secs = r'(acknowledg(e)?ments)|(data availability)|(declaration of competing interest)|(appendix [a-z](\.)?)'
            
            for line in text:
                # print(line)
                line_ = line.strip(" ,.[]()1234567890").lower()
                ms = re.search(extra_secs,line_) # check if one of the extra secs included
                # print(ms)
                if ms and ms.span()[0]==0:
                    # make new axuiliary section
                    if 'Auxiliaries' not in d_.keys():
                        d_['Auxiliaries'] = {}

                    # get line idx to delete extra section from section text
                    mi = text.index(line)
                    del_from_text.append(mi)
                    
                    # starting from idx "mi", loop through the sections text lines in order to
                    # store the extra sections text, if another extra secs title occurs, break
                    val = [line]
                    for j,t in enumerate(text[mi+1:],mi+1):
                        # if any(map(lambda p:re.search(p,text[j]),extra_secs)):
                        if re.search(extra_secs,text[j].lower()):
                            break
                        else:
                            val.append(t)

                    # add extra section to dict
                    d_['Auxiliaries'][ms.group(0).title()] = {}
                    d_['Auxiliaries'][ms.group(0).title()]['text'] = val

            if del_from_text:
                d['text'] = text[:first(del_from_text)]
    return d_

def sentence_splitting(d): 
    '''
    Split the sections text into sentences. 
    Create a title field for each section.

    args:
        d:  (dict) sections 
    returns:
        d:  (dict) sections with sentence splitting and title field
    '''
    nlp = import_spacy()
    for v in d.copy().values():
        if isinstance(v,dict):
            sentence_splitting(v)

        elif d['text']:
            # print(d['text'])
            d['title'] = d['text'][0].title().strip("0123456789 .,;-_[]").replace("\n","")
            text = " ".join(d['text'][1:])

            # split section text into sentences 
            doc = nlp(text)
            d['sentences'] = [sent.text.replace("\n","") for sent in doc.sents]
            
            # erase duplicates
            # func. ... 

            d.pop('text')
            # merge sents by patterns                
            patterns = [
                # r"(\()*(Fig|Eq|comm|spp)\.( \d{1,2}(\.)?)?(\))?",
                r"(\()?Fig\.",
                r" (Eq|comm)\."
                r" [a-z]+-",
                r"[A-Z]\S+ et al\.",
                r" sp+\."
            ]

            sents = d['sentences']
            for _ in range(2):
                # clean sentences
                for si,sent in enumerate(sents):
                    sents[si] = re.sub(r" {2,}"," ",sents[si].strip())
                    if re.search(r"\S+- \S+",sents[si]):
                        sents[si] = sents[si].replace("- ","")

                # merge sentences by pattern at ..
                for si,sent in enumerate(sents):
                    ms = sum([[m.span() for m in re.finditer(p,sent)] for p in patterns],[])
                    if ms:
                        # .. beginning of line
                        if ms[0][0]==0:
                            sents[si-1] += " " + sent
                            sents.remove(sent)
                            continue
                        # .. end of line
                        elif ms[-1][1]==len(sent) and si<len(sents)-1:
                            next_sent = sents[si+1]
                            sents[si] += " " + next_sent
                            sents.remove(next_sent)

            sents = [s.lstrip("[]1234567890 -.") for s in sents]
            sents = [s for s in sents if len(s)>1]          

            d['sentences'] = sents
    return d


def extract_sections(paragraphs,m2=False):
    '''
    Detect section titles and insert and insert the sections text.

    args:
        paragraphs: (list) text split into paragraphs (list of lists)
    returns:
        - text split into sections (dictionary)
        - if text needs to empy line insertions for getting better 
            section extraction accuracy
    '''
    d,key = {},""
    m1 = lambda x: re.search(r'([1-9](\.))+ ([A-Z]|\d+)\S+ ?(\S+ ?)+',x)
    m2 = lambda x: re.search(r'([1-9](\.)?)+ ([A-Z]|\d+)\S+ ?(\S+ ?)+',x)

    for p in paragraphs:
        match = m2(p[0]) if m2 else m1(p[0])
        if len(p)<=3 and match and match.span()[0]==0:
            k = re.sub(r"\D","",p[0].split(" ")[0])
            # print(k,p)
            d_,d = flatten_dict(d),insert_key(d,k,1)
            # print(k,d_,flatten_dict(d))
            key = k if d_<flatten_dict(d) else key
            # print(key)
            d = insert_text(d,key,1,p)

        elif len(p)>3 and match and match.span()[0]==0:
            return d,True
        else:
            d = insert_text(d,key,1,p)

    return d,False

def paragraphs(text_lines):
    '''
    Split text lines into paragraphs.

    args:
        text_lines: (list) text split into lines
    returns:
        text plitted into paragraph (list of lists)
    '''
    return list(filter(lambda x:len(x)>0,split_at(text_lines,lambda x: x=='')))

def introduction_idx(text_lines):
    '''
    Find the start index of the introduction section.

    args:
        text_lines: text splitted into lines.

    returns:
        start index of introduction section
    '''
    i = list(locate(text_lines,lambda l:"introduction" in l.lower()))
    i = first(i) if len(i)>0 else -1
    e = text_lines[i]
    if text_lines[i][:1]!="1.":
        text_lines.insert(i,"1. Introduction")
        text_lines.remove(e)

    return i


def get_sections(text):
    '''
    Apply section parsing algorithm and redo parsing if
    the parsing was not successful. Split the sections 
    text to sentences.

    args:
        text: (str) text as string

    returns:
        text splitted into sections as dictionary
    '''
    d = {}
    text_lines = text.split("\n") 
    i = introduction_idx(text_lines)
    d,s = extract_sections(paragraphs(text_lines[i:]))
    # print(d.keys())
    if not has_recursive_struct(d,0) or s:
        d.clear()
        text_lines = insert_blank_lines(text_lines)
        i = introduction_idx(text_lines)
        d,_ = extract_sections(paragraphs(text_lines[i:]))

    if not has_recursive_struct(d,0) or s:
        d.clear()
        d,_ = extract_sections(paragraphs(text_lines[i:]),m2=True)


    d = append_extra_secs(d,d)
    d = sentence_splitting(d)

    return d

def append_abstract(sections,abstract):
    sections["0"] = {}
    sections["0"]["title"] = "Abstract"
    sections["0"]["sentences"] = [sent.text.replace("\n","").strip() for sent in import_spacy()(abstract).sents]
    return sections

def get_text(title,text,abstract):
    '''
    Extract the text splitted into sections, 
    append the references and them store as json file.

    args:
        title: (str) output_dir path
        text: (str) document text as string
    '''
    doc_idx,st = utils.st_id(title)

    sections = get_sections(text)
    sections = append_abstract(sections,abstract)
    # print(sections)
    # append references
    with open(f"Output/{title}/References/refs.txt","r") as ref_file:
        sections["References"] = ref_file.readlines()

    # save sections as json file
    with open(f"Output/{title}/sections.json","w",encoding='utf-8') as sec_file:
        json.dump(sections,sec_file,sort_keys=True,indent=4)
    utils.store_time(doc_idx,"Sections",st)



