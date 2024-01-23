import re
import functools as ft
from math import inf
from more_itertools import duplicates_everseen, first_true, unzip, map_reduce, flatten


def replace_cids(text):
    '''
    Replace cids from text.

    args:
        text: (str) document text.
    returns:
        text with replace cids.
    '''
    text = re.sub(r'\(cid:3\)', '-', text)
    text = re.sub(r'\(cid:17\)', '~', text)
    # if font in ['PEKCKE+AdvPSSym', 'PEKFPG+AdvP4C4E46']:
    text = re.sub(r'\(cid:4\)', '-', text)
    text = re.sub(r'\(cid:5\)', '~', text)
    text = re.sub(r'\(cid:2\)', '×', text)
    text = re.sub(r'\(cid:3\)', '°', text)
    text = re.sub(r'\(cid:6\)', '·', text)
        # break

    # if font in ['FBIMAF+AdvP4C4E74']:
    text = re.sub(r'\(cid:1\)', '-', text)
        # break

    # if font in ['BPDCBD+AdvP4C4E74']:
    text = re.sub(r'\(cid:5\)', '-', text)
    return text

def preprocess(text):
    '''
    Replace various characters which would only be displaced as unicode.

    args:
        text: (str) documents text.
    '''
    text = re.sub(r"\(cid:\d+\)","",text)
    text = text.replace("A R T I C L E  I N F O","")

    text = text.replace(chr(8226),"").replace(chr(9702),"")
    text = text.replace(chr(8211),"-").replace(chr(8212),"-").replace(chr(94),"-")
    text = text.replace(chr(8216),"'").replace(chr(8217),"'").replace(chr(180),"'")
    text = text.replace(chr(8221),'"').replace(chr(8220),'"').replace(chr(8222),'"').replace(chr(8223),'"')
    text = text.replace(" ","").replace(chr(184),"").replace(chr(168),"").replace(chr(184),"")
    text = text.replace(chr(169),'©').replace(chr(252),'ü').replace(chr(537),'ș')
    text = text.replace(chr(64256),"ff").replace(chr(64257),"fi").replace(chr(64258),"fl")
    text = text.replace(chr(223),"ß").replace(chr(248),'ø')

    l = [
        (177, '±'), (181, 'µ'), (188, '¼'), (214, 'Ö'), (215, '×'), 
        (223, 'ß'), (222, 'Þ'), (240, 'ð'), (241, 'ñ'), (243, 'ó'), 
        (246, 'ö'), (247, '÷'), (248, 'ø'), (252, 'ü'), (254, 'þ'), 
        (225, 'á'), (233, 'é'), (237, 'í'), (730, '˚'), (948, 'δ'), 
        (969, 'ω'), (981, 'ϕ'), (8208, '‐'), (8706, '∂'), (8722, '−'), 
        (8764, '∼'), (8804, '≤'), (9702, '◦'), (32, ' '), (64258, 'ﬂ'), 
        (32, ' '), (32, ' '), (10, '\n')
    ]

    for o,s in l:
        text = text.replace(chr(o),s)

    return text


def delete_by_idx(text,pl_idxs):
    '''
    Delete lines of the text by page and line numbers.
    args:
        text: (str) document text.
        pl_idxs: (list) list of tuples with page,line idxs of lines to set empty.
    returns:
        text with empty lines at specified page,line position.
    '''
    pages = text.split("")
    for pi,li in pl_idxs:
        page_lines = pages[pi].split("\n")
        page_lines[li] = ""
        pages[pi] = "\n".join(page_lines)

    return "".join(pages)


def page_header(text):
    '''
    Find and delete duplicate page headers from each page.

    args: 
        text: (str) document text.
    returns:
        text with page header replaced.
    '''
    pages = text.split("")

    dups = list(set(filter(lambda x:len(x)>0,
        duplicates_everseen(flatten([page.split("\n")[:4] for page in pages])))))
    if len(dups)==0:
        dups = list(set(filter(lambda x:len(x)>0,
            duplicates_everseen(flatten([page.split("\n")[-8:-1] for page in pages])))))

    for dup in dups:
        for pi,page in enumerate(pages):
            pages[pi] = page.replace(dup,"")

    text = "".join(pages)


    return text #delete_by_idx(text,to_delete)

def page_numbering(text):
    '''
    Get page numbering and delete it.

    args: 
        text: (str) document text.
    returns:
        text with page numbers replaced.

    '''
    # d20: "8 - 3", d47: at bottom (13,272), 15:d21 at bottom
    pages = text.split("")
    
    def get_pnums(pages,bw=False):
        # l%2==0 switch ?
        p_nums,pln = [],[]
        s = lambda x: re.sub(r",|\.| ","",x)
        f = lambda x: len(p_nums)==0 or (len(p_nums)>0 and p_nums[-1]==x+1)
        for pi,page in enumerate(pages):
            p_lines = page.split("\n")
            plns = p_lines[-8:-1] if bw else p_lines[:5] # footer or header
            # print(plns)
            lines = [(i,int(s(l))) for i,l in enumerate(plns) if s(l).isdigit()]
            e = first_true(lines,pred=lambda x: f(x[1]))
            if e != None:
                if bw:
                    pln.append((pi,len(p_lines)-(len(plns)-e[0]+1),e[1])) 
                else:
                    pln.append((pi,e[0],e[1]))
        return pln

    pln = get_pnums(pages)

    if len(pln)<len(pages)/2: # 10: d47
        pln = get_pnums(pages,bw=True)

    if len(pln)<len(pages)/2: # 15: d21
        p_nums,pln = [],[]
        s = lambda x: re.sub(r",|\.| ","",x)
        f = lambda x: len(p_nums)==0 or (len(p_nums)>0 and p_nums[-1]==x+1)
        for pi,page in enumerate(pages):
            plns = page.split("\n")
            footer = plns[-8:-1]
            for i,k in enumerate(footer):
                l = k.split(" ")[::-1] if pi%2==0 else k.split(" ")
                lines = [int(s(h)) for h in l if all(map(lambda x:47<x<58,map(ord,s(h)))) and s(h).isdigit()]
                e = first_true(lines,pred=lambda x: f(x)) 
                if e != None:
                    pln.append((pi,len(plns)-(len(footer)-i+1),e))  
    
    # print(pln)

    if len(pln)<len(pages)/2:
        return "".join(pages),"no page numbering"
    else:
        # check all numbers in order else clean list
        # if is_sorted(list(zip(*pln))[-1],key=int):
        if ft.reduce(lambda x,y: y if x<y else inf,list(zip(*pln))[-1])==inf:
            page_nums = "".join(list(map(str,map(len,(map(str,list(map(list,unzip(pln)))[-1]))))))
            result = map_reduce(page_nums,int,int)
            m = sorted(result.keys(), reverse=True)[0]
            temp = list(filter(lambda x: len(str(x[2]))==m,pln))
            pln = temp if len(temp)>len(pages)/2-1 else pln # why do this ?

        pis,lis,n = list(zip(*pln))
        return delete_by_idx(text,zip(pis,lis)),"-".join(map(str,[n[0],n[-1]]))


