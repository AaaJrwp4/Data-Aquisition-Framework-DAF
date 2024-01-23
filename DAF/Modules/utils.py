import os
import csv
import shutil
import time
import filecmp
import contextlib
import json
from pathlib import Path
from typing import Iterable, Any
from alive_progress import alive_bar
import itertools as it
import pandas as pd
from scidownl import scihub_download
from crossref.restful import Works
from more_itertools import duplicates_everseen, collapse
from pdfminer.high_level import extract_text_to_fp,extract_pages

# dir. where pdf files are stored
input_dir = "Input/" 

def format_date(meta):
	'''
	Format the data of the given attributes.
	args:
		meta: metadata parsed from a .pdf file as dictionary.
	'''
	import datetime

	attributes = [
		'Creation-Date',
		'Last-Modified',
		'Last-Save-Date',
		'created',
		'date',
		'meta:creation-date',
		'meta:save-date',
		'modified',
		'pdf:docinfo:created',
		'pdf:docinfo:modified'
	]

	for a in attributes:
		try:
			date = meta['metadata'][a] 
			meta['metadata'][a] = str(datetime.datetime.strptime(
				date, "%Y-%m-%dT%H:%M:%S%z"))[:10]
		except KeyError:
			continue

	return meta

def pdf_meta(dir_path,pdf,save=False):
	'''
	Extract metadata from .pdf file with Tika.
	args:
		dir_path: directory path where pdf is stored
		pdf: name of pdf file ending on .pdf
	'''
	with contextlib.redirect_stdout(None):
		import tika
		from tika import parser
		tika.initVM() # Java VM

		try:
		    parsed = parser.from_file(f"{dir_path}/{pdf}",xmlContent=True)
		    # print(parsed['metadata'])

		    meta = format_date(parsed) # format all date attributes
		    meta = list(parsed["metadata"].items())
		    meta = "\n".join(list(it.starmap(lambda x,y: f"{x} {y}", meta)))

		    if save: 
		        pdf_name = pdf.replace(".pdf","")
		        with open(f"{dir_path}/Data/meta_{pdf_name}.txt","w",encoding='utf-8') as meta_file:
		            meta_file.write(meta)
		    return meta 

		except Exception as error:
		    print("Tika Error: ", error)


def pdf_txt(dir_path,pdf,save=False):
	'''
	Extract text from pdf file with pdfminer and store it as .txt file.
	args:
		dir_path: directory path where pdf is stored
		pdf: name of pdf file ending on .pdf
	'''
	from io import StringIO
	import pdfminer
	from pdfminer.layout import LAParams
	from pdfminer.converter import TextConverter
	from pdfminer.pdfdocument import PDFDocument
	from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
	from pdfminer.pdfpage import PDFPage
	from pdfminer.pdfparser import PDFParser

	output_string = StringIO()
	try:
	    with open(f"{dir_path}/{pdf}", "rb") as in_pdf:
	        parser = PDFParser(in_pdf)
	        doc = PDFDocument(parser)
	        rsrcmgr = PDFResourceManager()
	        device = TextConverter(rsrcmgr, output_string, laparams=LAParams())
	        interpreter = PDFPageInterpreter(rsrcmgr, device)

	        for page in PDFPage.create_pages(doc):
	            interpreter.process_page(page)
	    
	    text = output_string.getvalue()
	    if save:
	        pdf_title = pdf.replace(".pdf","")
	        with open(f'{dir_path}/Data/text_{pdf_title}.txt', "w",encoding='utf-8') as out_txt:
	            out_txt.write(text)
	    else:
	        return text

	except Exception as error:
	    print("Pdfminer Error: ",error) 
	    print("... deleting folder.")
	    shutil.rmtree(dir_path) 

def all_files():
	files = sorted(os.listdir(input_dir))
	if ".DS_Store" in files:
		files.remove('.DS_Store')
	return files

def remove_enumeration():
	for file in all_files():
		l = file.split("_",1)
		if len(l)>1:
			os.rename(input_dir+file,input_dir+l[1])
	# remove_enumeration()
	
def enumerated_pdfs():
	for fi,file in enumerate(all_files(),start=1):
		os.rename(input_dir+file,input_dir+f"d{fi}_"+file)
	return all_files()

def extract_data(restore=False):
	'''
	Extract Text and Metadata from PDF Files.
	'''
	if restore:
		clear_in_out_dirs(restore)

	start = time.time()
	extraction_times = []
	filter_non_pdfs()
	ascend_files()
	# delete_duplicates_by_size()
	total_files = enumerated_pdfs()
	for i,pdf in enumerate(total_files):
		print(f"{i}/{len(total_files)} {pdf}")
		st,doc_idx = time.time(),pdf.split("_")[0]
		pdf_title = pdf.replace(".pdf","")	

		if not os.path.isdir(input_dir+pdf_title):
			os.mkdir(input_dir+pdf_title) 					# create dir. named by pdf title
			shutil.move(input_dir+pdf,input_dir+pdf_title) 	# put pdf into that dir
			os.mkdir(input_dir+pdf_title+"/Data/") 			# make Data dir in that dir 

		dir_path = f"{input_dir}/{pdf_title}"
		pdf_txt(dir_path,pdf,save=True)
		pdf_meta(dir_path,pdf,save=True)
		store_time(doc_idx,"Text Extraction",st)

	create_output_dirs()
	# delete_not_extractable_files()
	print("")


def create_output_dirs():
	'''
	Create directorys for all the input files
	with directorys for the extracted components.
	'''
	components = [
		"Figures",
		"Images",
		"Plots",
		"References",
		"Symbols",
		"Tables"
	]

	for title in all_files():
		output_dir = f"Output/{title}/"
		if not os.path.isdir(output_dir):
			os.mkdir(output_dir)
			# for c in components:
			# 	os.mkdir(output_dir+c)
	# create_output_dirs()


def create_remove_dir(title,component,create=True):
    base_path = f"Output/{title}/{component}"

    if create and not os.path.isdir(base_path):
        os.mkdir(base_path)
    else:
        # print(os.listdir(base_path))
        try:
        	# print(os.listdir(base_path))
	        if not os.listdir(base_path):
	            shutil.rmtree(base_path)
        except FileNotFoundError as e:
        	write_to_logfile(title,component,e)


def all_file_paths():
	'''
	Returns a list of tuples with each including:
		1. title of dir
		2. metadata path
		3. text path
		4. pdf path
	'''
	title_meta_text = []
	for d in all_files():
	    data_dir = input_dir+d+"/Data/"
	    files = os.listdir(data_dir)
	    pdf = [f for f in os.listdir(input_dir+d) if f.endswith('.pdf')][0]
	    if len(files) == 2:
	        meta = files[0] if "meta_" in files[0] else files[1]
	        text = files[0] if "text_" in files[0] else files[1]
	        title_meta_text.append((d,data_dir+meta,data_dir+text,input_dir+d+"/"+pdf))

	return title_meta_text


def get_text_bboxes(o: Any,title):
    '''
	Get the bounding boxes coordinates from all 
	horizontal text lines included in the pdf.
	In the thesis this file is referenced as "coordinates file".

    Taken and adjusted from:
    https://stackoverflow.com/questions/25248140/how-does
        -one-obtain-the-location-of-text-in-a-pdf-with-pdfminer
    '''
    
    bbox = lambda o: ''.join(f'{i:<4.0f}' for i in o.bbox) if hasattr(o, 'bbox') else ''

    with open(f"Input/{title}/coords.csv","a") as f:
        writer = csv.writer(f,lineterminator="\n",quoting=1)
        if o.__class__.__name__ == "LTTextLineHorizontal":
            p = bbox(o).strip().split()
            if len(p)<4:
            	return
            else:
            	x1,y1,x2,y2 = p
            	text =  o.get_text().strip() if hasattr(o, 'get_text') else ''
            	writer.writerow([x1,y1,x2,y2,text])

    if isinstance(o, Iterable):
        for i in o:
            get_text_bboxes(i,title)

def extract_text_coords(pdf_path,title):
	if not os.path.exists(f"Input/{title}/coords.csv"):
		doc_idx,st = title.split("_")[0],time.time()
		path = Path(pdf_path).expanduser()
		pages = extract_pages(pdf_path)
		get_text_bboxes(pages,title)
		store_time(doc_idx,"Coordinates File",st)

def st_id(title):
	return title.split("_")[0],time.time()

def store_time(doc_idx,module,start_time):
	cplx_f = "Output/complexity_by_module.json"
	if not os.path.exists(cplx_f):
		with open(cplx_f,"w") as c_file:
			json.dump({},c_file,sort_keys=True,indent=4)
		store_time(doc_idx,module,start_time)
	else:
		with open(cplx_f,"r") as c_file:
			times_dict = dict(json.load(c_file)).copy()

			if doc_idx not in times_dict:
				times_dict[doc_idx] = {}
			if module not in times_dict[doc_idx]:
				times_dict[doc_idx][module] = round(time.time()-start_time,3)
	
			with open(cplx_f,"w") as c_file:
				json.dump(times_dict,c_file,sort_keys=True,indent=4)

def filter_non_pdfs():
	in_dir,_ = get_in_out_dirs()
	for f in in_dir:
		if not f.endswith(".pdf"):
			os.remove("Input/"+f)


def ascend_files():
	'''
	Some files in input data can be stored inside a nested directory.
	Take out the file of directories.
	'''
	def ascend(v):
		k = os.listdir(v)
		if ".DS_Store" in k:
			k.remove(".DS_Store")

		for f in k:
			d = f"{v}/{f}"
			if f.endswith(".pdf"):
				shutil.move(d,input_dir+f)
			else:
				ascend(d)
		

	for v in all_files():
		if not v.endswith(".pdf"):
			path = input_dir+v
			ascend(path)
			shutil.rmtree(path)


def delete_not_extractable_files():
	print("\nChecking for not extractable files")

	for out_dir,_,txt_path,_ in all_file_paths():

		with open(txt_path,"r") as file: 
			dir_path,lines = "Input/"+out_dir,list(file.readlines())
			if len(lines)<50 or " \n" not in lines:
				shutil.rmtree(dir_path)
				print(out_dir)
				write_to_logfile(out_dir,"Extraction","Deleted because <50 lines.")
				continue

			lines = list(filter(lambda x: len(x)>1,lines))
			if sum(map(lambda x: len(x)==2,lines))/len(lines)>.98:
				print(out_dir)
				write_to_logfile(out_dir,"Extraction","Deleted because all lines len == 1.")
				shutil.rmtree(dir_path)

def has_text_extraction_fail(title):
	txt_path = f"Input/{title}/Data/"
	txt_file = [f for f in os.listdir(txt_path) if f.startswith("text_")][0]
	with open(txt_path+txt_file,"r") as file: 
		dir_path,lines = "Input/"+title,list(file.readlines())
		if len(lines)<50:
			print("lines <50")
			return 1

		lines = list(filter(lambda x: len(x)>1,lines))
		if sum(map(lambda x: len(x)==2,lines))/len(lines)>.98:
			print("Lines >.98")
			return 1
		return 0


def get_pdf_platform():
	for f in all_files():
		p = input_dir+f+"/Data/"
		with open(p+[x for x in os.listdir(p) if "meta_" in x][0],"r") as mf:
			for line in mf.readlines():	
				if "pdf:docinfo:producer" in line:
					print(f)
					print(line)


def delete_duplicates_by_size():
	sizes = map(lambda f: os.path.getsize(input_dir+f),all_files())
	fs = list(zip(all_files(),sizes))

	for i,(n,s) in enumerate(fs):
		j = list(zip(*fs[i+1:]))
		if j and s in j[1]:
			for x in fs[i+1:]:
				(n,v) = x
				if s==v:
					os.remove(input_dir+n)
					fs.remove(x)

def delete_duplicates():
	input_dir,_ = get_in_out_dirs()
	for i,f1 in enumerate(input_dir):
		for f2 in input_dir[i+1:]:
			if filecmp.cmp(f1,f2,shallow=True):
				print(f1)



def write_to_logfile(title,module,text):
	with open("Output/logfile.txt","a") as logfile:
		logfile.write(f"{title} {module} \n{text}\n\n")


def get_in_out_dirs():
	input_dir, output_dir = os.listdir("Input"),os.listdir("Output")
	if ".DS_Store" in input_dir:
		input_dir.remove(".DS_Store")
	if ".DS_Store" in output_dir:
		output_dir.remove(".DS_Store")

	return sorted(input_dir),output_dir

def clear_in_out_dirs(restore=False):
	print("Clearing Input and Output.")

	input_dir,output_dir = get_in_out_dirs()
	indir = "Input/"
	if restore:
		for f in input_dir:
			if os.path.isdir(indir+f):
				pdf = [k.split("_",1)[-1] for k in os.listdir(indir+f) if k.endswith(".pdf")]
				if pdf:
					pdf = pdf[0]
					shutil.move(indir+f+"/"+f+".pdf",indir+f+".pdf")
					shutil.rmtree(indir+f)
					os.rename(indir+f+".pdf",indir+pdf)
		remove_enumeration()

	else:
		for i in input_dir:
			in_file_path = f"Input/{i}"
			if not os.path.isdir(in_file_path):
				os.remove(in_file_path)
			else:
				shutil.rmtree(in_file_path)
	
	for o in output_dir:
		out_file_path = f"Output/{o}"
		if not os.path.isdir(out_file_path):
			os.remove(out_file_path)
		else:
			shutil.rmtree(out_file_path)


def json_to_csv():
	cplx_f = "Output/complexity_by_module.json"
	with open(cplx_f,"r") as c_file, open("Output/complexity_stats.csv","a") as c_stats:
		times_dict = dict(json.load(c_file))
		n = max(map(len,times_dict.values()))
		writer = csv.writer(c_stats,lineterminator="\n",quoting=1)
		writer.writerow(['doc_id']+list(times_dict['d1'].keys()))

		for doc_id,vals in times_dict.items():
			l,nvals = [],len(vals.values())
			if nvals==n:
				l = [doc_id]+list(vals.values())
			else:
				l = [doc_id]+list(vals.values()) + [0 for _ in range(n-nvals)]
			writer.writerow(l)

def complexity_stats():
	import matplotlib.pyplot as plt 
	json_to_csv()
	p = "Output/complexity_stats.csv"
	if os.path.exists(p):
		df = pd.read_csv(p)
		plt.figure(figsize=(15,8))
		plt.pie(list(df.mean()),labels=df.columns[1:],autopct=lambda x: f"{round(x,2)}s")
		plt.title("Complexity of Modules")
		print("Computation Time by Module:\n",df.mean())
		plt.savefig("Output/complexity_stats.png",format="png")
		# plt.show()


def download_papers_by_doi():
	import pprint
	prefix,works = "DOIs/", Works()
	dois = list(collapse([pd.read_csv(prefix+f).doi.to_list() for f in os.listdir(prefix)]))
	with alive_bar(len(dois),title="Downloading") as bar:
		for doi in dois:
			time.sleep(2)
			try:
				title = works.doi(doi)#['title']
				pprint.pprint(title)
				# title = title[0] if title else doi
				# scihub_download(doi, paper_type="doi", out=f"./Input/{title}.pdf")
			except Exception as e:
				print(e)
			bar()




def store_captions(key,d):
	base_path = "Output/all_captions.json"

	if not os.path.exists(base_path):
		with open(base_path,"w") as all_caps:
			json.dump({},all_caps,sort_keys=True,indent=4)
		store_captions(key,d)
	else:
		with open(base_path,"r") as all_cps:
			all_caps = dict(json.load(all_cps))
			all_caps[key] = d
			with open(base_path,"w") as acf:
				json.dump(all_caps,acf,sort_keys=True,indent=4)


def print_enumerated_files():
	for i,(out_dir,*_) in enumerate(sorted(all_file_paths()),start=1):
		print(i,out_dir)


def update_metadata_col():
	print("updating col")
	_,out_dir = utils.get_in_out_dirs()
	df = pd.read_csv("Output/all_files_metadata.csv")
	enums = df.doc_enum.to_list()
	k = list(sorted(filter(lambda x: not any(map(lambda y: x.endswith(y),[".csv",".png",".json",".txt"])),out_dir)))

	print(df.head(),df.shape)

	for o in k:
		denum = o.split("_")[0]
		if denum in enums:
			row = df.iloc[df.index[df['doc_enum']==denum][0]]#
			row.sections_extr_success = sections.is_recursively_structured(o)
			df.iloc[df.index[df['doc_enum']==denum][0]] = row

	df.to_csv("Output/all_files_metadata.csv",index=False)


def send_email(message,subject):
	import smtplib
	from email.mime.multipart import MIMEMultipart
	from email.mime.text import MIMEText

	email_address,pw = '',''
	server,port = '','587'


	msgRoot = MIMEMultipart('related')
	msgRoot['Subject'] = subject
	msgRoot['From'] = email_address
	msgRoot['To'] = email_address

	msgAlternative = MIMEMultipart('alternative')
	msgRoot.attach(msgAlternative)
	msgText = MIMEText(message, _subtype='plain')
	msgAlternative.attach(msgText)

	with smtplib.SMTP(server, port=port) as smtp:
		smtp.ehlo()
		smtp.starttls()
		smtp.login(email_address, pw)
		smtp.sendmail(email_address, email_address, msgRoot.as_string())

