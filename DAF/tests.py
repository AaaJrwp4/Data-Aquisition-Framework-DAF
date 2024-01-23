import unittest
import json 
import pprint
import pandas as pd 
from Modules import sections
from Modules import metadata 
from Modules import tables
from Modules import preprocessing
from Modules import figures
from Modules import references
from Modules import symbols

class TestSections(unittest.TestCase):

	def test_flatten_dict(self):
		with open("Test_Data/d1.json","r") as sec_data:
			d = dict(json.load(sec_data))
			self.assertTrue(sections.flatten_dict(d) == 41)
			d["Test Key"] = {"title":"Test the dict flatten function."}
			self.assertTrue(sections.flatten_dict(d) == 43)

	def test_insert_key(self):
		with open("Test_Data/d2.json","r") as sec_data:
			d = dict(json.load(sec_data))
			before = sections.flatten_dict(d)
			after = sections.flatten_dict(sections.insert_key(d,"312",1))
			self.assertTrue(after-before==2)

			after1 = sections.flatten_dict(sections.insert_key(d,"412",1))
			self.assertTrue(after==after1)
			after2 = sections.flatten_dict(sections.insert_key(d,"312",1))
			self.assertTrue(after==after2)
			after3 = sections.flatten_dict(sections.insert_key(d,"32",1))
			self.assertTrue(after3-after==2)
			after4 = sections.flatten_dict(sections.insert_key(d,"3111",1))
			self.assertTrue(after4-after3==2)

	def test_insert_key_from_txt(self):
		with open("Test_Data/d3.txt","r") as d_txt:
			lines,d = d_txt.read().split("\n"),{}
			for line in lines:
				d = sections.insert_key(d,line,1)

			after_insertion = sections.flatten_dict(d)
			self.assertTrue(after_insertion == 50)

	def test_insert_text(self):
		with open("Test_Data/d2.json","r") as sec_data:
			d = dict(json.load(sec_data))
			before = sections.flatten_dict(d)
			text = ["moin das ist ein test fuer text insertion"]
			d = sections.insert_text(d,"311",1,text)
			self.assertTrue(before==sections.flatten_dict(d))

	def test_has_recursive_struct(self):
		with open("Test_Data/d2.json","r") as sec_data, open("Test_Data/d3.txt","r") as d_txt:
			d = json.load(sec_data)
			self.assertTrue(sections.has_recursive_struct(d,0))
			d = sections.insert_key(d,"32",1)
			self.assertTrue(sections.has_recursive_struct(d,0))

			lines,d = d_txt.read().split("\n"),{}
			for line in lines:
				d = sections.insert_key(d,line,1)
			self.assertTrue(sections.has_recursive_struct(d,0))


class TestMetadata(unittest.TestCase):

	def test_get_ft_captions(self):
         # test data
		with open("Test_Data/test_text.txt","r") as text_f:
			text,d_ = metadata.get_ft_captions("title",text_f.read(),replace_=True)
			self.assertTrue(sections.flatten_dict(d_)==sections.flatten_dict(d_caps))
			self.assertEqual(d_caps,d_)

	def test_get_ft_captions_2(self):
        # test data 
		with open("Test_Data/ft_caps_test2.txt","r") as fcaps: 
			text = fcaps.read()
			extracted  = sections.flatten_dict(metadata.get_ft_captions("title",text)[1])
			ground_truth = sections.flatten_dict(d)
			self.assertEqual(extracted,ground_truth)

	def test_get_ft_positions(self):
		d_pos = {2: [range(7, 159), range(161, 176), range(178, 262), range(264, 344), range(374, 522)], 4: [range(7, 225)], 6: [range(62, 89)], 8: [range(7, 106)], 9: [range(0, 10)]}
		with open("Test_Data/test_text.txt","r") as text_f:
			text = text_f.read()
			_,ft_idxs = metadata.get_ft_positions("title",text,plot=False,replace_ft_lines=True)
			self.assertTrue(sections.flatten_dict(ft_idxs)==sections.flatten_dict(d_pos))
			self.assertEqual(d_pos,ft_idxs)

	def test_get_ft_positions_2(self):
		d = {1: [range(0, 109)], 3: [range(0, 11)], 5: [range(0, 10)], 7: [range(0, 13)], 8: [range(0, 11)]}
		with open("Test_Data/ft_positions_test2.txt","r") as ftp2:
			text = ftp2.read()
			_,ft_idxs = metadata.get_ft_positions("title",text,False,False)
			self.assertEqual(ft_idxs,d)

	def test_get_abstract(self):
		with open("Test_Data/groundtruth_abstract.txt","r") as abs_txt, open("Test_Data/abstract_text.txt","r") as abs_text:
			text = abs_text.read()
			abstract_ = abs_txt.read()
			_,abstract = metadata.get_abstract(text)
			self.assertTrue(abstract==abstract_)


class TestTables(unittest.TestCase):

	def test_get_table_lines_and_groups_1(self):
		df = pd.read_csv(f"Test_Data/test_coords.csv")
		*_,texts = list(zip(*list(zip(*df.iterrows()))[1]))
		texts = list(map(preprocessing.preprocess,map(str,texts)))
		_,egs = tables.get_table_lines_and_groups(texts)
		self.assertTrue(len(egs)==8)

	def test_get_table_lines_and_groups_2(self):
		df = pd.read_csv(f"Test_Data/test_coords2.csv")
		*_,texts = list(zip(*list(zip(*df.iterrows()))[1]))
		texts = list(map(preprocessing.preprocess,map(str,texts)))
		_,egs = tables.get_table_lines_and_groups(texts)
		self.assertTrue(len(egs)==6)



class TestReferences(unittest.TestCase):

	def test_ref_strt_idx(self):
		with open("Test_Data/ref_start_idx_test.txt","r") as ref_start:
			text = ref_start.read().split("")
			self.assertTrue(references.ref_strt_idx(text,False)==(5, 83))


class TestPreprocessing(unittest.TestCase):

	def test_page_numbering(self):
		with open("Test_Data/page_number_test.txt","r") as pn_text:
			text = pn_text.read()
			self.assertTrue(preprocessing.page_numbering(text)[1]=="199-211")


	def test_page_numbering_2(self):
		with open("Test_Data/page_numbering_test2.txt","r") as pn_text:
			text = pn_text.read()
			self.assertTrue(preprocessing.page_numbering(text)[1]=="2223-2234")
		

	def test_page_header(self):
		with open("Test_Data/page_numbering_test2.txt","r") as pn_text:
			text = pn_text.read()
			text = preprocessing.page_header(text)
			r = ""
			self.assertFalse(r in text.split("\n"))

	def test_page_header_2(self):
		with open("Test_Data/page_number_test.txt","r") as pn_text:
			text = pn_text.read()
			f = "../Test_Data/page_number_test.txt"
			r = ""
			text = preprocessing.page_header(text)
			self.assertFalse(r in text.split("\n"))


class TestSymbols(unittest.TestCase):

	def test_get_coords_pages(self):
		f = "Test_Data/coords_file_split.txt"
		df = pd.read_csv("Test_Data/test_coords_file_split.csv")
		self.assertTrue(len(symbols.get_coords_pages(df,f))==14)






if __name__ == "__main__":

    unittest.main()
