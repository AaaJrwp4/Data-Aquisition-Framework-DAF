import fitz
import io 
import re
import os
import pdf2image
import cv2
import shutil
import pandas as pd 
import numpy as np
from math import isnan
from PIL import Image
from Modules import utils 
from collections import Counter
from textdistance import cosine
from operator import itemgetter,eq
from Modules import preprocessing
import functools as ft
from itertools import groupby, starmap
from more_itertools import first_true, first, last


def pdf_images(title,pdf_path,pages=False):
    '''
    Extract all images from the pdf file and store them in ouput dir.
    
    args:
        title: output_dir path
        pdf_path: path to pdf file
        pages:  if to return a dict with for 
                each page the number of images on it
    '''
    base_path = f"Output/{title}/Images"
    # print(base_path)
    try:
        pdf_file = fitz.open(pdf_path)

        # return a dictionary with the page and number of imgs on that page
        if pages:
            img_pages = {} # page:img_count
            for i in range(len(pdf_file)):
                page = pdf_file[i]
                image_list = page.get_images()

                if image_list:
                    img_pages[i] = len(image_list)
            return img_pages

        # store all imgs of doc in directory
        else:
            utils.create_remove_dir(title,"Images")
            for page_i in range(len(pdf_file)): 

                page = pdf_file[page_i]

                for img_i, img in enumerate(page.get_images(), start=1): # for imgs on page

                    xref = img[0]
                    base_image = pdf_file.extract_image(xref)
                    image_bytes = base_image["image"]
                    img_ext = base_image["ext"]
                    image = Image.open(io.BytesIO(image_bytes))
                    image.save(
                        open(f"{base_path}/page_{page_i+1}_img_{img_i}.{img_ext}","wb"))

            # utils.create_remove_dir(title,"Images",create=False)
            return pdf_file.pageCount
    except Exception as e:
        utils.write_to_logfile(title.split("_")[0],"Figures",e)


def remove_small_imgs(title):
    '''
    Delete small meaningless images extracted from pdf.
    '''
    img_path = f"Output/{title}/Images"
    if os.path.exists(img_path):
        for f in os.listdir(img_path):
            file_path = img_path+"/"+f
            size = os.path.getsize(file_path)
            if size < 1024:
                os.remove(file_path)
                utils.write_to_logfile(title,"Images",f"Deleted many small (<Kb) images.")

def remove_whole_pages(title,p_count):
    img_path = f"Output/{title}/Images"
    if os.path.exists(img_path):
        files = os.listdir(img_path)
        sizes = all([Image.open(f"Output/{title}/Images/{f}").size>(2000,3000) for f in files]) # fix
        # print("whole_pages",len(files),p_count)
        if len(files) == p_count and all(map(lambda x: int(x.split(".")[0][-1]),files)):# and sizes:
            shutil.rmtree(img_path)
            utils.write_to_logfile(title,"Images",f"Deleted images, which extracted as a whole page.")

def remove_small_cutouts(title):
    img_path = f"Output/{title}/Images"
    if os.path.exists(img_path):
        files = os.listdir(img_path)
        sizes = [Image.open(f"Output/{title}/Images/{f}").size for f in files]

        # print("cutouts",len(set(sizes))/len(sizes))
        if sizes and len(set(sizes))/len(sizes)<0.07: # important param
            # print(len(sizes),len(set(sizes)))
            utils.write_to_logfile(title,"Images",f"Deleted many small cutout rectangles.")




def get_images(title,pdf_path,resp):
    p_count = 0
    if not resp is None:
        if resp['issued']['date-parts'][0][0] >= 2000:
            p_count = pdf_images(title,pdf_path)
    else:
        p_count = pdf_images(title,pdf_path)
    remove_small_imgs(title)
    remove_whole_pages(title,p_count)
    remove_small_cutouts(title)



def print_fig_groups(e,texts):
    '''
    Print the groups of figure like lines detection.
    args:
        e: figure-like line indices
        texts: text lines 
    '''
    e = e + (e[-1]+1,)
    for li,g in enumerate(filter(lambda x: x!="",itemgetter(*e)(texts)),start=first(e)):
        print(li,g)
    print()
    print()

def get_fig_lines(captions,texts,p_nums):
    '''
    Detect figure-like lines (<35 chars).

    args:
        captions: (dict) per page captions.
        texts:    (list) text lines
        p_nums:   (str)  range of page numbers
    returns:
        list of tuples with line idx and text line detect as fig-line

    '''
    p_range = p_nums.split("-")
    s,e = list(map(int,p_range)) if all([x.isdigit() for x in p_range]) else [1,0]
    p_nums = list(map(str,range(s-1,e+1))) if s<e else [None for _ in range(len(captions))]

    dups = list(zip(*filter(lambda x:len(x[0])>20 and x[1]>4,Counter(texts).items())))
    # print(dups_)
    
    # mark all lines which belong to a figure caption
    # for the case if one fig. underneath an other
    f_caps_idxs,is_cap_line = [0],[False for _ in range(len(texts))] 
    for page,v in captions.items():
        # print(page)
        for ft,cap in v.items():
            if ft[0]=="F":
                s = f_caps_idxs[-1]
                for xi,x in enumerate(texts[s:],start=s):
                    # if pagenumber is aswell ticks number, group not complete (d29)
                    # if x == p_nums[page]: # the current line is a page number 
                    #     is_cap_line[xi] = True

                    if cosine(cap[0],x)>0.95 and all([cosine(c,t)>0.95 for c,t in zip(cap,texts[xi:len(cap)])]):
                        xi_ = xi+len(cap)
                        f_caps_idxs.append(xi_)
                        is_cap_line[xi:xi_] = [True for _ in range(xi,xi_)]
                        break

    # print(texts[2881-7:2882][::-1])
    # search for fig lines
    is_fig_line,skip = [],[]
    for ti,text in enumerate(map(str,texts)):

        # skip n=len(skip) iterations
        if skip:
            skip.pop()
            continue

        # search for fig. caption 
        fm = lambda x: re.search(r"Fig(ure)?(\.)? ?\d{1,2}(\.)?",x)
        if fm(text) and fm(text).span()[0]==0:
            # print("Match ==== > ",fm(text).group(0))
            # do lookbehind search by line length
            j = ti-1
            # if two fig caps underneath this will fail (d29)
            # if len(texts[j])>=35:
            #     texts[j] = ""

            while len(texts[j])<35 and not(texts[j] in dups or is_cap_line[j]):
                is_fig_line[j] = True 
                j-=1

        # detecting vertical figure captions
        if text=="F" and fm("".join(texts[ti-8:ti+1])[::-1]):
            # print(ti,texts[ti-8:ti+1][::-1])
            # lookbehind for fig. lines
            j = ti-1
            while len(texts[j])<35 and not(texts[j] in dups or is_cap_line[j]):
                is_fig_line[j] = True 
                j-=1

            # look ahead for fig. lines
            j = ti
            while len(texts[j])<35 and not(texts[j] in dups or is_cap_line[j]):
                is_fig_line.append(True)
                j+=1

            # how many iterations to skip
            skip = list(range(ti,j))
            
        is_fig_line.append(False)



    # filter out fig lines and group them
    fig_lines = []
    for _,g in groupby(enumerate(is_fig_line),lambda l:l[1]):
        e,g = list(zip(*g))
        if g[0]:
            # print_fig_groups(e,texts)
            fig_lines.append(list(zip(e,g)))

    return fig_lines



def get_figures(pdf_path,title,captions,p_nums):
    '''
    Extract figures by their text coordinates approach.

    args:
        pdf_path:   (str) path to .pdf file
        title:      (str) output dir. path
        catpions:   (dict) captions per page
        p_nums:     (str) range of page nums
    
    '''

    utils.create_remove_dir(title,"Figures")
    
    # transform pdf pages to .png imgs
    try:
        images = pdf2image.convert_from_path(pdf_path)
    except pdf2image.exceptions.PDFPageCountError:
        return 

    if len(images)>0:
        # get the xy-span of converted pdf 
        image = np.array(images[0])
        dw,dh = len(image[0]),len(image)
        # print(dw,dh)
    else:
        return


    try:
        # get the xy-span of pdfminers bboxes coordinates
        df = pd.read_csv(f"Input/{title}/coords.csv")
        x1 = df.iloc[:, 0].min()
        y1 = df.iloc[:, 1].min()
        x2 = df.iloc[:, 2].max()
        y2 = df.iloc[:, 3].max()
        # print(x1,x2,y1,y2)
    except pd.errors.EmptyDataError as e:
        utils.write_to_logfile(title.split("_")[0],"Figures",e)
        return

    texts = list(map(preprocessing.preprocess,map(str,df.iloc[:,4]))) # preprocessing
    fig_lines = get_fig_lines(captions,texts,p_nums) # get all lines which belong to a figure
    # print(len(fig_lines))

    pm_x_span, pm_y_span = (x1+x2),(y1+y2)
    # split page into 1024 parts for xy
    page_split = 1024 
    width, heigth = (x2+x1)/page_split,(y2+y1)/page_split
    if isnan(width) or isnan(heigth):
        return
    h_ = [int(i*heigth) for i in range(1,page_split)]
    w_ = [int(i*width) for i in range(1,page_split)]
    # print("w",w_,"\n","h",h_)

    fi,f_caps_idxs = 0,[0]
    for page,v in captions.items():
        for ft,caption in v.items():
            if ft[0]=="F":
                # get line idx for fig caption
                s,appended_ = f_caps_idxs[-1],False
                for xi,x in enumerate(texts[s:],start=s):
                    if cosine(caption[0],x)>0.95:
                        appended_ = True
                        f_caps_idxs.append(xi)
                        break
                # print(f_caps_idxs)
                try:
                    e,_ = list(zip(*fig_lines[fi]))
                    start,end,f_idx = e[0],e[-1],f_caps_idxs[-1]
                except IndexError:
                    # print("Out of Groups")
                    utils.write_to_logfile(title.split("_")[0],"Figures","Out of groups.")
                    break 

                # no figure caption was found, check if it can be found in a (probably) vertical group
                if not appended_:
                    cap = "".join(caption).replace(" ","")
                    f_group = "".join(itemgetter(*e)(texts)[::-1]).split(".")
                    if any(map(lambda e:sum(starmap(lambda x,y:x==y,zip(cap,e)))/len(cap)>0.90,f_group)):
                        f_idx = end+1
                        f_caps_idxs.append(f_idx)

                # print(ft,f_idx,start,end)


                # check if caption matches group
                if f_idx-1!=end:
                    continue

                # check if fig. can be extracted
                # if not, go to next group and continue with next caption
                if end-start<5:
                    fi +=1
                    continue


                # only take this group if its not an image
                # select lines by group indixes
                fig_df = df.iloc[list(range(start,end+1))]
                x1 = fig_df.iloc[:, 0].min()
                y1 = fig_df.iloc[:, 1].min()
                x2 = fig_df.iloc[:, 2].max()
                y2 = fig_df.iloc[:, 3].max()
                # print(x1,y1,x2,y2)
                # print(first_true(enumerate(w_,start=1),pred=lambda x:x[1]>x1),x1)
                x1 = int(x1/pm_x_span*dw)
                x2 = int(x2/pm_x_span*dw)
                y1 = int(y1/pm_y_span*dh)
                y2 = int(y2/pm_y_span*dh)
                # find in which part of the 1024 page splits the borders of the fig are
                # normalize it with page_split and rescale to pdf_image coordinates
                # x1 = int((last(first_true(enumerate(w_,start=1),pred=lambda x:x[1]>x1)))/page_split * dw)
                # x2 = int((last(first_true(enumerate(w_,start=1),pred=lambda x:x[1]>x2)))/page_split * dw)
                # y1 = int((last(first_true(enumerate(h_,start=1),pred=lambda x:x[1]>y1)))/page_split * dh)
                # y2 = int((last(first_true(enumerate(h_,start=1),pred=lambda x:x[1]>y2)))/page_split * dh)
                # print(x1)
                fig_num,p = re.sub(r"\D","",ft),20
                x1,y1,x2,y2 = (x1,dh-y2,x2,dh-y1)

                # continued figures
                # if os.path.exists(f"{base_path}/Figures/fig_{fig_num}.png"):
                #     fig_num = str(fig_num)+"-1"
                try:
                    cv2.imwrite(f"Output/{title}/Figures/fig_{fig_num}.png", np.array(images[page])[y1-p:y2+p, x1-p:x2+p])
                except Exception as e:
                    utils.write_to_logfile(title.split("_")[0],"Figures",e)



                fi +=1

    utils.create_remove_dir(title,"Figures",create=False)










