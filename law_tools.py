
def tokenize_sexp(predicate_string):
    "Parse string representation of sexp into a list of tokens (https://norvig.com/lispy.html)"
    return predicate_string.replace('(', '( ').replace(')', ' )').split()

def parse_tokens_to_ast(tokens):
    current_branch = []
    parent_stack = []
    expected_closing_delimiter = []
    for token in tokens:
        if token == "(":
            expected_closing_delimiter.append(")")
            parent_stack.append(current_branch)
            current_branch = []
        elif token == ")":
            # TODO: Add in closing delimiter check and raise error
            parent_branch = parent_stack.pop()
            parent_branch.append(current_branch)
            current_branch = parent_branch
        else:
            current_branch.append(token)
            
    return current_branch[0]

class CompoundPredicate:

    def __init__(self):
        pass

    def parse_args(self, args):
        self.args = list(map(ast_to_predicate_obj, args))

    def display(self):
        print("Or")
        for arg in self.args:
           arg.display()

class And(CompoundPredicate):

    def run(self, query_state):
        result = True
        for arg in self.args:
            if result:
                result = arg.run(query_state)
        return result

class Or(CompoundPredicate): 

    def run(self, query_state):
        result = False
        for arg in self.args:
            if not result:
                result = arg.run(query_state)
        return result
            

class Not(CompoundPredicate):
    pass

import re
class Is:
    def __init__(self):
        pass

    def parse_args(self, args):
        self.source = re.compile(args[0])

    def display(self):
        print("Is")
        print(self.source)

    def run(self, query_state):
        #return (self.source == query_state.get_current_cursor())
        return bool(re.match(self.source, query_state.get_current_focus()))

class Within:

    def __init__(self):
        pass

    def parse_args(self, args):
        self.range = int(args[0])
        self.word1 = args[1]
        self.word2 = args[2]

    def run(self, cursor):
        if (self.word1 == cursor.get_current_focus()):
            in_range = ((self.word2 in cursor.get_n_previous_words(self.range))
                        or
                        (self.word2 in cursor.get_n_next_words(self.range) ))
            return in_range
        else:
            return False

class Other:

    def __init__(self, form):
        self.form = form

    def display(self):
        print(self.form)

    def run(self, query_state):
        return True
        
string_to_obj = {"or" : Or,
                 "and" : And,
                 "not" : Not,
                 "within" : Within,
                 "=" : Is}

def ast_to_predicate_obj(query_ast):
   if isinstance(query_ast, list): 
       op, args = query_ast[0], query_ast[1:]
       obj = string_to_obj[op]()
       obj.parse_args(args)
       return obj
   else:
       return Other(query_ast)

def compile_predicate_from_string(predicate_string):
    tokens = tokenize_sexp(predicate_string)
    predicate_ast = parse_tokens_to_ast(tokens)
    predicate_object = ast_to_predicate_obj(predicate_ast)
    return predicate_object

class TextCursor:

    def __init__(self):
        self.current = False
        self.previous_words = []
        self.next_words = []

    def stream(self):
        while self.next_words:
            yield self
            
    def continue_running(self):
        return self.next_words

    def clear_previous_words(self):
        self.previous_words = []

    def append_to_stream(self, words_as_ls):
        self.next_words = words_as_ls

    def get_current_focus(self):
        return self.current

    def get_n_previous_words(self, n):
        return self.previous_words[(-1 * n):]
        
    def get_n_next_words(self, n):
        return self.next_words[:n]
        
    def shift_cursor_right(self):
        if self.current:
            self.previous_words.append(self.current)
        if self.next_words:
            self.current = self.next_words.pop(0)


def format_word_ctx(ls):
    try:
        return ' '.join(ls)
    except:
        return ls

import time
import os
import PyPDF2
import glob

class QueryRunner:

    def __init__(self):
        self.start_time = time.time()
        self.n_matches = 0
        self.matches = []

    def stream_files(self, list_of_filenames):

        self.files = list_of_filenames
        self.n_files = len(self.files)
        self.n_total_files = len(self.files)
        self.tokens = TextCursor()

        for i, file in enumerate(self.files):
            self.file_text = file
            self.file_number = i
            yield file

    def stream_pages(self, list_of_pages):
        self.pages = list_of_pages
        self.n_pages = len(list_of_pages)
        for i, page in enumerate(self.pages):
            self.page_number = i
            yield page
            
    def stream_tokens(self, tokens):
        self.tokens.append_to_stream(tokens)
        self.tokens.shift_cursor_right()
        yield self.tokens

    def record_match(self):
        cursor = self.tokens
        snapshot = {"file" : self.file_text,
                    "page" : self.page_number,
                    "word" : cursor.current,
                    "context before" : format_word_ctx(cursor.previous_words[-10:]),
                    "context after" : format_word_ctx(cursor.next_words[:10])}
        self.n_matches =+ 1
        self.matches.append(snapshot)

def report_progress(self):
    seconds_elapsed = round(time.time() - self.start_time, 2)
    print(chr(27) + "[2J")
    print("\033c", end ="")
    red = "\u001b[31m"
    white = "\u001b[37m"
    reset = "\u001b[0m"
    print(f'Currently On: {self.file_text}')
    print(f'File: [{red}{self.file_number}{reset}/{self.n_files}]') 
    print(f'Page: [{self.page_number}/{self.n_pages}]') 
    print(f'Time Elapsed: {seconds_elapsed} seconds')
    print(f'Number of Matches: {self.n_matches}')

    
def apply_predicate(predicate, token):
    return predicate.run(token)
    
def run_query(env):
   
    path = input("Give me the folder name!\n")
    pred = input("Give me a query!\n")
    #predicate = compile_predicate_from_string(pred)
    path = "Unix"
    predicate = compile_predicate_from_string("(or (= Unix) (within 5 command line) (= e))")
   
    env.set_folder_path(path)
    pdf_list = env.get_names_of_all_pdfs_in_folder()

    qr = QueryRunner()

    for file in qr.stream_files(pdf_list):

        pdf_reader = PyPDF2.PdfReader(file)
        pages = pdf_reader.pages

        for page in qr.stream_pages(pages):

            text = page.extract_text().split()

            for token in qr.stream_tokens(text):

                if apply_predicate(predicate, token):

                    qr.record_match()
            
                report_progress(qr)

    return qr
                    
import csv

def write_ls_to_csv(dictionary, fields, filename):
    "Writes ls to csv file. Modified from https://www.tutorialspoint.com/How-to-save-a-Python-Dictionary-to-CSV-file"
    try:
        with open(filename, 'w') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fields)
            writer.writeheader()
            for data in dictionary:
                writer.writerow(data)
    except IOError:
        print("I/O error")

def report_matches(query_result, env):

    ls = query_result.matches
    if ls:
        fields = ls[0].keys()
        filename = env.path + "matches.csv"
        write_ls_to_csv(ls, fields, filename)

class Env:

    def __init__(self):
        home = os.path.expanduser('~')
        self.path = f"{home}/Desktop/"

    def set_folder_path(self, folder_name):
        self.folder_name = folder_name
        self.folder_path = self.path + folder_name + "/"

    def get_names_of_all_pdfs_in_folder(self):
        return glob.glob(self.folder_path + "*.pdf")

class ListZipper:

    def __init__(self, ls):
        self.left = []
        self.focus = ls[0]
        self.right = ls[0:]
        self.count = 0

    def __iter__(self):
        return self
        
    def __next__(self):
        if self.right:
            self.count += 1
            self.left.append(self.focus)
            self.focus = self.right.pop()
            return self.focus
        else:
           raise StopIteration

    def move_left(self, n = 1):
        print("invocation: " + str(self.count))
        for i in range(n):
            self.right.append(self.focus)
            self.focus = self.left.pop()
        return self.focus
       

def main(run = True):
    if run:
        env = Env()
        query_result = run_query(env)
        report_matches(query_result, env)
    else:
        t = ListZipper([1, 2, 3, 4, 5, 6, 7])
        for i in t:
            print(i)
        print(t.move_left(3))

main(True)

