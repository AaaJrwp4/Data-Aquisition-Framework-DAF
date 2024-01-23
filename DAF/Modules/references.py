import re
import json
import matplotlib.pyplot as plt
from itertools import starmap, accumulate, repeat
from more_itertools import split_at, first, locate, flatten
from Modules import preprocessing
from Modules import utils

def merge_refs(refs):
    '''
    Merge references lines based on patterns.
    args:
        refs: (list) references.
    returns:
        merged refs

    '''

    m = re.search(r"(R|r)eferences",refs[0])
    if m:
        refs[0] = refs[0].replace(m.group(0),"")

    # merge by ..             
    for ri,ref in enumerate(refs):
        if not ri<len(refs)-1:
            break 

        # ... ending of sentence (page nums or doi)
        pnums = r"(\d+ ?- ?\d+|p\. \d+)\."
        doi = r"(doi:)?(10\.\d{4,5}\/[\S]+[^;,.\s])(\.)*$"
        m = lambda x: re.search(rf"{pnums}|{doi}",x)
        next_ref = refs[ri+1]
        if not m(ref) and m(next_ref):
            refs[ri] += next_ref
            refs.remove(next_ref)
            continue

        # ... if two refs together, split 'em
        if m(ref):  
            b,e = m(ref).span()
            if b>0 and e!=len(ref)-1:
                refs[ri] = ref[:e].strip()
                refs.insert(ri+1,ref[e+1:].strip())
                continue

    return refs


def ref_strt_idx(pages,plot):
    '''
    Find the start index of the references section when the references 
    section could no be located by the "refernces" keyword.
    
    args:
        pages:  (list) text split into pages
        plot:   (bool) if detection indices should be plotted.

    returns:
        page index and line index of references section start
    '''
    # 14:d21; 25:d27 .. still have problems
    # detect references pattern 
    res = []
    styles = [
        r"(\d{1,3})? [A-Z]\S+ ([A-Z] ?)+,",
        r", et al\. \(\d{4}\)"
        r"\d{1,3}. [A-Z]\S+ [A-Z],",
        r"[A-Z]\S+ [A-Z]+ \(\d{4}\)",
        r"([A-Z]\S+, ([A-Z]\.)+,)+ ((\()*\d{4}(\))*.)*"
    ]

    for pi,page in enumerate(pages):
        page_lines = page.split("\n")
        for li,line in enumerate(page_lines):
            res.append((pi,li,any(map(lambda style: re.search(style,line), styles))))


    ref_idxs = list(filter(lambda x: x[0]>=len(pages)*2/3 and x[2]==1, res))
    if len(ref_idxs)>0:
        pi,li,_ = first(ref_idxs) 


        if plot:
            pns = list(accumulate([len(page.split("\n")) for page in pages]))
            plot_data = list(zip(*list(starmap(lambda pi,li,b: (pns[pi-1]+li,b),res))))

            plt.plot(plot_data[0],plot_data[1]) 
            plt.xlabel("line number")
            plt.ylabel("has pattern")
            plt.title("References Pattern Detection")
            plt.show()

        return pi,li
    else:
        return -1,-1


def get_references(title,text,plot=False):
    '''
    Extract the references section from text.

    args:
        title:  (str) dir_title in output folder.
        text:   (str) text of document
        plot:   (bool) if references like detections should be plotted

    returns:
        - text with the references deleted from it
        - references as list
    '''
    utils.create_remove_dir(title,"References")

    pages = text.split("")
    np = len(pages)
    all_ref_idxs = []
    for pi,page in enumerate(pages):
        page_lines = page.split("\n")
        idxs = list(locate(enumerate(page_lines),lambda line: "references" == line[1].lower().strip()))
        if len(idxs)>0:
            for idx in idxs:
                all_ref_idxs.append((pi,idx))


    pi,li = all_ref_idxs[-1] if len(all_ref_idxs)>0 else ref_strt_idx(pages,plot)
    article_strt = r"( *\S+,* (( |-)*[A-Z]\.)+,*)+ ((\()*\d{4}(\))*\.)*" 
    article_end = r"\d+-\d+\."
    # r = lambda l: l.replace(chr(8211),"-").replace(chr(94),"-")
    if pi!=-1:
        # idxs do delete in the end
        idxs = sum([list(zip(repeat(i+pi),range(li,len(page.split("\n"))) if i==0 else range(len(page.split("\n"))))) for i,page in enumerate(pages[pi:])],[])
        # print(idxs)

        references = {}
        for i,page in enumerate(pages[pi:]):
            if not i+pi in references:
                references[i+pi] = {}

            page_lines = list(enumerate(page.split("\n")))
            page_lines = page_lines[li:] if i==0 else page_lines

            text_blocks = list(filter(lambda x:len(x)>0,split_at(page_lines,lambda x: x[1]=='')))
            # do some replacements
            # text_blocks = list(map(lambda block:list(map(lambda l: (l[0],r(l[1])),block)),text_blocks))
            for bi,block in enumerate(text_blocks):

                ### cleaning the references

                # merge splitted article references
                if bi<len(text_blocks)-1 and len(block)==1 and re.search(article_strt,block[0][1]):
                    next_block = text_blocks[bi+1]
                    if re.search(article_end,next_block[-1][1]):
                        text_blocks.insert(bi,sum([next_block],block))
                        text_blocks.remove(block)
                        text_blocks.remove(next_block)
                        # print(text_blocks[bi])
                
                if not bi in references[i+pi]:
                    references[i+pi][bi] = block

        # get refs and line numbers
        idxs2, ref = [],[]
        for pi,refs in references.items():
            for v in refs.values():
                li,r = list(map(list,zip(*v)))
                idxs2.append(list(zip(repeat(pi),li)))
                ref.append(" ".join(r))

        
        idxs2 = sum(idxs2,[])

        # print(idxs)

        references = merge_refs("\n".join(ref))

        base_path = f"Output/{title}/References"
        with open(f"{base_path}/refs.txt","w",encoding='utf-8') as ref_file:
            ref_file.write(references)

        return preprocessing.delete_by_idx(text,idxs),references
    else:
        with open(f"Output/{title}/References/refs.txt","w",encoding='utf-8') as ref_file:
            ref_file.write("")

        return text,"no references found"


def parse_refs(dir_title,refs,crossref_resp):
    '''
    Parse the references for components listed below.

    args:
        dir_title:  (str) dir_title of pdf in output folder.
        refs:       (list) references as list
    '''
    # with open("d12_refs.txt","r") as f:
    #     refs = f.readlines()
    #     refs = merge_refs(list(refs))

    r = {}
    if not crossref_resp is None and 'reference' in crossref_resp:
        for ref in crossref_resp['reference']:
            r[ref['key']] = ref
    else:
        refs = refs.split("\n")
        refs = merge_refs(refs)

        # parse references
        for ri,ref in enumerate(refs): 
            r[ri] = {
                "authors":[],
                "editors":[],
                "year":"",
                "title":"",
                "magazine":"",
                "publisher":"",
                "citys":[],
                "volume":"",
                "pages":"",
                "doi":""
            }

            # book is cited in refs
            eds = re.search(r"(\()(E|e)ds\.",ref)
            if eds:
                e1 = r"(( [A-Z]\.)+ ([A-Z]\S+|[A-Z]\S+ [a-z]+) ?(,|and|\)))(\.)*"
                editors = [x.group(0) for x in re.finditer(rf"{e1}",ref[eds.span()[1]:])]
                if editors:
                    for editor in editors:
                        # print(editor)
                        ref = ref.replace(editor,"")
                        r[ri]['editors'].append(editor.replace(" and","").strip(" .)"))
                ref = ref.replace(eds.group(0),"")


            a1 = r"[A-Z]\S+, ([A-Z]\.)+,"
            a2 = r"(([A-Z]\S+|[A-Z]\S+ [a-z]+) ([A-Z]\. ?)+(and|,| ))"
            authors = [x.group(0) for x in re.finditer(rf"{a1}|{a2}",ref)]
            if authors:
                for a in authors:
                    ref = ref.replace(a,"").strip()
                    r[ri]['authors'].append(a.replace(" and",""))


            year = re.search(r"(\()?(19|20)\d{2}(\))?(\.)?",ref)
            if year:
                ref = ref.replace(year.group(0),"").strip()
                r[ri]['year'] = re.sub(r"\(|\)","",year.group(0).strip())

            title = re.search(r"^[^.]*",ref)
            if title:
                ref = ref.replace(title.group(0)+".","").strip()
                r[ri]['title'] = title.group(0).strip(" )").replace("- ","")

            # get publisher
            for pub in flatten([h.split(".") for h in ref.split(",")]):
                p = ["Press","Verlag","Springer"]
                if any(map(lambda x: x in pub,p)):
                    r[ri]['publisher'] = pub.strip()
                    ref = ref.replace(pub,"")

            # extract citys
            # for ent in nlp(ref).ents:
            #     if ent.label_ == "GPE" and gc.get_cities_by_name(ent.text.strip()):
            #         r[ri]['citys'].append(ent.text)
            #         ref = ref.replace(ent.text,"")



            magazine = list(re.finditer(r"[^.\d\W]+",ref))
            if magazine:
                for m in magazine:
                    ref = ref.replace(m.group(0)+".","").strip()
                r[ri]['magazine'] = " ".join([m.group(0) for m in magazine]).strip() + "."

            volume = re.search(r"\d+,",ref)
            if volume:
                ref = ref.replace(volume.group(0),"").strip()
                r[ri]['volume'] = volume.group(0).strip(" ,")

            pages = re.search(r"\d+ ?- ?\d+\.",ref)
            if pages:
                ref = ref.replace(pages.group(0),"").strip()
                r[ri]['pages'] = re.sub(r" ","",pages.group(0).strip(" ."))

            doi = re.search(r"(doi:)?(10\.\d{4,5}\/[\S]+[^;,.\s])$",ref.rstrip(" ."))
            if doi:
                # print(doi)
                ref = ref.replace(doi.group(0),"")
                r[ri]['doi'] = doi.group(0).strip(" .").replace("doi:","")

    with open(f"Output/{dir_title}/References/refs.json","w",encoding='utf-8') as ref_file:
        json.dump(r,ref_file,indent=4)

