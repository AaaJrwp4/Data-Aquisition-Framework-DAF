from Modules import utils 
from Modules import metadata
from Modules import preprocessing
from Modules import tables
from Modules import figures
from Modules import symbols
from Modules import references
from Modules import sections
from alive_progress import alive_bar
import time
import traceback
import pprint,os
import pandas as pd



def parse_files(
		i=None,
		optics=False,
		metadata_=False,
		tables_=False,
		figures_=False,
		symbols_=False,
		sections_=False):
	
	print("Starting component extraction.")

	j = i-1 if isinstance(i,int) else None
	files = sorted(utils.all_file_paths())


	for i,(out_dir,meta_path,txt_path,pdf_path) in enumerate(files,start=1):

		print(f"{i}/{len(files)}",out_dir)
		try:
			k = pdf_path.split("_",1)[0]
			if tables_ or figures_ or symbols_:
				utils.extract_text_coords(pdf_path,out_dir)


			with open(meta_path,"r") as meta_file, open(txt_path,"r") as text_file:
				text = text_file.read()
				meta = meta_file.readlines() 

				text = preprocessing.preprocess(text)

				if optics:
					n_cols = 5 # num of cols in pages plot
					metadata.document_optics(
						out_dir,text,n_cols,file=False,save_plot=True)				

				if tables_:
					doc_idx,st = utils.st_id(out_dir)

					text,ft_idxs = metadata.get_ft_positions(
						out_dir,text,plot=False,replace_ft_lines=False)

					text,ft_captions = metadata.get_ft_captions(
						out_dir,text,save=False,replace_=False)

					if not isinstance(ft_idxs,str):
						tables.get_tables(pdf_path,out_dir,ft_captions,ft_idxs)

					utils.store_time(doc_idx,"Tables",st)

				text = preprocessing.page_header(text)
				text,pnums = preprocessing.page_numbering(text)

				text,ft_idxs = metadata.get_ft_positions(
					out_dir,text,plot=False,replace_ft_lines=True)
				# pprint.pprint(ft_idxs)

				text,ft_captions = metadata.get_ft_captions(
					out_dir,text,save=True,replace_=True)
				utils.store_captions(out_dir,ft_captions)

				text,dois      = metadata.get_doi(meta,text)
				crossref_resp  = metadata.crossref_request(dois)

				if figures_:
					doc_idx,st = utils.st_id(out_dir)
					figures.get_images(out_dir,pdf_path,crossref_resp)
					figures.get_figures(pdf_path,out_dir,ft_captions,pnums)
					utils.store_time(doc_idx,"Images/Figures",st)
				

	            ### metadata: find and delete from text
				text,copyright = metadata.get_copyright(text)
				text,url       = metadata.get_urls(text)
				text,keywords  = metadata.get_keywords(text)
				text,citation  = metadata.get_citation(text)
				text,dates     = metadata.get_pub_dates(text)
				text,ai        = metadata.get_institutions(text)
				text,authors   = metadata.get_authors(text)
				text,abstract  = metadata.get_abstract(text)
				title 		   = metadata.get_title(meta,text)


				if symbols_:
					text = symbols.extract_symbols(text,txt_path,pdf_path,out_dir)
					
					show_detections_per_page = False
					if show_detections_per_page:
						symbols.show_symbols_on_page(pdf_path,out_dir,show=True,save=False)
						symbols.transform_to_latex(out_dir)

				if sections_:

					text,references_txt = references.get_references(out_dir,text,plot=False)
					references.parse_refs(out_dir,references_txt,crossref_resp)
					sections.get_text(out_dir,text,abstract)

				if metadata_:
					doc_idx = out_dir.split("_",1)[0]
					doc_enum = doc_idx
					# pprint.pprint(crossref_resp)
					if not crossref_resp is None:
						doc_idx = crossref_resp['DOI']
						title_ = crossref_resp['title']
						title = title_[0] if title_ else title

					l = [doc_idx,doc_enum,title,doc_idx,copyright,keywords,citation,abstract]
					metadata.write_meta_to_csv(l,ft_captions,out_dir,meta_path,True)

		except Exception as e:
			message = f"Doc num.: {i} {out_dir}\n\n" + traceback.format_exc()
			# utils.send_email(message,"Error")
			print(message)
			utils.write_to_logfile(out_dir,"File Parser",str(traceback.format_exc()))

def daf(extract=False):
	if extract:
		utils.extract_data(restore=False)

	metadata.clear_metadata_file()
	parse_files(None,
		optics=True,
		metadata_=False,
		tables_=False,
		figures_=False,
		symbols_=False,
		sections_=False
	)
	# metadata.post_process_metadata()
	# utils.complexity_stats()
	# utils.send_email("","Finished Extraction")

daf(False)
# utils.clear_in_out_dirs(False)
# utils.print_enumerated_files()
# update_metadata_col() 





