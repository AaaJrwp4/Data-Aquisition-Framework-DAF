from Modules.MathFormApp import Inference_Math_Detection as MD
from more_itertools import locate, first_true
from itertools import starmap
from textdistance import cosine
from PIL import Image
from Modules import utils
import pdf2image
import cv2
import csv 
import pandas as pd 
import numpy as np
import os 

model_path = "./Modules/MathFormApp/Models/MathDetector.ts"

def show_symbols_on_page(pdf_path,title,show=True,save=False):
    '''
    Detect all symbols/formulas on a page of a pdf and show it.
    args:
        pdf_path: (str) path to pdf file
        title: (str) title of the dir. where pdf data is stored
        show: (bool) to show pdf
        save: (bool) to save pdf
    '''

    out_path = f"Output/{title}/Symbols"
    utils.create_remove_dir(title,"Symbols")

    pages = pdf2image.convert_from_path(pdf_path)
    for pi,page_image in enumerate(pages):
        save_path = out_path+f"/page-{pi}"
        if not os.path.exists(save_path):
            os.mkdir(save_path)

        page_image = np.array(page_image)

        # detect (math) symbols
        math_model = MD.initialize_model(model_path) # init model
        formula_rects = MD.predict_formulas(page_image, math_model) # get predictions
        rects = list(map(lambda x: list(map(lambda p: int(p), x[:-2])), formula_rects))

        # extract the detections from the pdf image
        p = 0 # padding
        rects_ = starmap(lambda x1,y1,x2,y2:(x1-p,y1-p,x2+p,y2+p),rects)
        for img_i,(x1,y1,x2,y2) in enumerate(rects_):
            print("page",pi,",",img_i,(x1,y1,x2,y2))
            cv2.imwrite(
                f"{save_path}/img-{img_i}.png",
                page_image[y1:y2, x1:x2])


        # draw rects on page
        for x1,y1,x2,y2 in rects:
            green = (0, 255, 0)
            cv2.rectangle(page_image, (x1, y1), (x2, y2),green, 3)
        
        if show:
            cv2.imshow(f"page-{pi}-detections", page_image)
            cv2.waitKey()
        if save:
            cv2.imwrite(f"{save_path}/page-{pi}-detections.png",page_image)


def transform_all_symbols_to_latex(title):
    '''
    Transform all the detections to LaTeX code and
    store them for each page in a dictionary.
    args:
        title: (str) title of pdf output folder.
    '''
    from pix2tex import cli as pix2tex
    model = pix2tex.LatexOCR()
    utils.create_remove_dir(title,"Symbols")
    out_path = f"Output/{title}/Symbols"

    formulas = {}
    files = filter(lambda x:x!=".DS_Store",os.listdir(out_path))
    pages = list(map(lambda f: os.path.join(out_path, f), files))
    for pi,page_path in enumerate(pages):
        # if pi > 0:
        #     break
        formulas[pi] = {}

        imgs = os.listdir(page_path)
        latex = [model(Image.open(page_path+"/"+img)) for img in imgs]
        for fi,f in enumerate(latex):
            formulas[pi][fi] = f

    with open(f"{out_path}/latex.json","w",encoding='utf-8') as l:
        json.dump(formulas,l,indent=4)



def get_coords_pages(df,txt):
    '''
    Split the coords files in to pages
    args:
        df: (pandas dataframe) dataframe with the coordinates file
        txt: (str) path to docs. txt file
    '''

    # rename cols
    df.columns = ["x1","y1","x2","y2","text"]

    # get text lines
    with open(txt,"r") as tf:
        text = list(filter(lambda x:x!="",tf.read().split("\n")))
    text = text[:len(text)-(len(text)-df.shape[0])]

    # locate all indixes where there is a page split 
    p_idxs = [0]+list(locate(text,lambda x:"" in x))+[len(text)]
    # lists pairwise tuples
    p_ranges = [(p,p_idxs[pi]) for pi,p in enumerate(p_idxs,start=1) if pi<len(p_idxs)-1] 

    pages = [df.iloc[list(range(*p_range))] for p_range in p_ranges]
    return pages 


def symbol_stats(title,p,line,img_coords,latex,latex_txt,inserted):
    '''
    Collect some stats from the symbols detection.
    args:
        title:      (str) title of output dir. for pdf
        p:          (int) page number
        line:       (str) text line without inserted latex
        img_coords: (tuple) coordinates of detected formula rectangle
        latex:      (str) latex command for image
        latex_txt:  (str) latex commands as text
        inserted:   (bool) if latex command was inserted into the line 
    '''
    stats_file = f"Output/{title}/Symbols/symbol_stats.csv"
    if not os.path.exists(stats_file):
        with open(stats_file,'w',encoding='utf-8') as sf:
            pass 

    with open(stats_file,"a",encoding="utf-8") as symbol_stats:
        writer = csv.writer(symbol_stats,lineterminator="\n",quoting=1)
        writer.writerow([title,p,img_coords,line,latex,latex_txt,inserted])


def extract_symbols(text,txt_path,pdf_path,title,stats=False):
    '''
    Detect symbol on page and insert its latex 
        into the corresponding paragraph line.

    args:
        text:      (str) text lines of pdf file (already cleaned 
                        from f/t captions, f/t lines, metadata ...)
        txt_path:  (str) path to txt file
        pdf_path:  (str) path to .pdf file
        title:     (str) key for document data dir.
    '''
    from pylatexenc.latex2text import LatexNodes2Text
    from pix2tex import cli as pix2tex
    model = pix2tex.LatexOCR()

    doc_idx,st = utils.st_id(title)
    out_path = f"Output/{title}/Symbols"
    utils.create_remove_dir(title,"Symbols")
    d_num = title.split("_")[0]
    try:
        df = pd.read_csv(f"Input/{title}/coords.csv")
        pm_x1 = df.iloc[:, 0].min()
        pm_y1 = df.iloc[:, 1].min()
        pm_x2 = df.iloc[:, 2].max()
        pm_y2 = df.iloc[:, 3].max()
    except pd.errors.EmptyDataError as e:
        # print(e)
        utils.write_to_logfile(title.split("_")[0],"Symbols",e)        
        return

    span_x,span_y = pm_x1+pm_x2,pm_y1+pm_y2
    coord_pages = get_coords_pages(df,txt_path)

    pages = pdf2image.convert_from_path(pdf_path) # .pdfs pages as .png images
    # get span of pdf. doc. image
    image = np.array(pages[1])
    dw,dh = len(image[0]),len(image)
    # print(dw,dh)


    # the page num where the references section begin
    ref_pi = list(locate(enumerate(text.split("")),
            pred=lambda x: any(map(lambda h:len(h)<13 and "references" in h.lower(),x[1].split("\n")))))

    # enumerated text lines
    text_ = [(ti,t) for ti,t in enumerate(text.split("\n")) if t!=""]
    # s = 0  # var to specify line to start from to search
    for pi,page_image in enumerate(pages[:ref_pi[0] if ref_pi else len(coord_pages)]):

        page_image = np.array(page_image)

        # detect (math) symbols
        math_model = MD.initialize_model(model_path) # init model
        formula_rects = MD.predict_formulas(page_image, math_model) # get predictions
        rects = list(map(lambda x: list(map(lambda p: int(p), x[:-2])), formula_rects))

        # extract the detections from the pdf image
        p = 0 # padding
        rects_ = starmap(lambda x1,y1,x2,y2:(x1-p,y1-p,x2+p,y2+p),rects)
        for img_i,(x1,y1,x2,y2) in enumerate(rects_):
            # rescale .png coordinates to pdfminer bboxes coordinates with "3-Satz"
            x1_ = int((x1/dw)*span_x)
            y1_ = int(span_y-(y2/dh)*span_y)
            x2_ = int((x2/dw)*span_x)
            y2_ = int(span_y-(y1/dh)*span_y)

            # line which fits the detected coordinates on page num. pi
            p_df = coord_pages[pi]
            line = p_df[
                    ((p_df.x1<x1_)|(abs(p_df.x1-x1_)<=5)) & 
                    ((p_df.x2>x2_)|(abs(p_df.x2-x2_)<=5)) & 
                    (abs(p_df.y1-y1_)<=5) & 
                    (abs(p_df.y2-y2_)<=5)
                ].text.to_list()


            print("Page:",pi, "img:",img_i)
            inserted = False
            if line:
                line_og = line[0]
                line = line[0]
                # check if it is really a paragraph line
                m = first_true(text_,pred=lambda x:cosine(x[1],line)>0.85)
                if m is not None: 
                    li,l = m 
                    print(line)
                    p = 3 # padding param for cutting out img from .png file

                    # extract the img, transform to latex and then to unicode string
                    cv2.imwrite(f"{out_path}/temp_img.png", page_image[y1-p:y2+p, x1-p:x2+p])
                    latex = model(Image.open(f"{out_path}/temp_img.png"))
                    latex_txt = LatexNodes2Text().latex_to_text(latex)
                    print(latex,latex_txt)

                    # check if there's a match for extracted latex unicode
                    # insert latex command into the line and delete og. line from text
                    line = line.split(" ")
                    for si,s in enumerate(line):
                        if cosine(s,latex_txt)>0.5:
                            line[si] = "$"+latex+"$"
                            inserted = True 

                            text = text.split("\n")
                            text.pop(li) # delete og. line from text
                            text.insert(li-1," ".join(line)) # insert line with latex
                            text = "\n".join(text)
                            print("Line: ",li,line)
                            print()
                            break
                    print()
                    if stats:
                        symbol_stats(title,pi,line_og,f"{x1},{y1},{x2},{y2}",latex,latex_txt,inserted)
            elif stats:
                symbol_stats(title,pi,"no line match found",f"{x1},{y1},{x2},{y2}","","",inserted)

    os.remove(f"{out_path}/temp_img.png")
    utils.create_remove_dir(title,"Symbols",create=False)
    utils.store_time(doc_idx,"Symbols",st)
    return text




