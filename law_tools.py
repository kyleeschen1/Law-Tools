
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

class CompoundQuery:

    def __init__(self):
        pass

    def parse_args(self, args):
        self.args = list(map(ast_to_predicate_obj, args))

    def display(self):
        print("Or")
        for arg in self.args:
           arg.display()

class And(CompoundQuery):

    def run(self, query_state):
        result = True
        for arg in self.args:
            if result:
                result = arg.run(query_state)
        return result

class Or(CompoundQuery): 

    def run(self, query_state):
        result = False
        for arg in self.args:
            if not result:
                result = arg.run(query_state)
        return result
            

class Not(CompoundQuery):
    pass

import re
class Is:
    def __init__(self):
        pass

    def parse_args(self, args):
        pattern = args[0]
        self.source = re.compile(f'\*{pattern}\*')
        #self.source = args[0]

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
        self.current = self.next_words.pop(0)

class QueryState:

    def __init__(self):
        self.successes = []

    def log_success(self, filename, num, cursor):
        snapshot = {"file" : filename,
                    "page" : num,
                    "word" : cursor.current,
                    "context before" : format_word_ctx(cursor.previous_words[-10:]),
                    "context after" : format_word_ctx(cursor.next_words[:10])}
        self.successes.append(snapshot)

def format_word_ctx(ls):
    try:
        return ' '.join(ls)
    except:
        return ls

import time
import os
import PyPDF2
import glob

def run_query(env):
   
    predicate = compile_predicate_from_string("(or (= Unix) (within 5 command line) (= e))")

    pdf_list = glob.glob(env.path + "*.pdf")
    query_state = QueryState()
    text_cursor = TextCursor()
   
    n_files = len(pdf_list)
    start_time = time.time()

    for fileno, filepath in enumerate(pdf_list, 1):

        pdf_reader = PyPDF2.PdfReader(filepath)
        text_cursor.clear_previous_words()

        filename = filepath.split("/").pop()
        n_pages = len(pdf_reader.pages)
        
        for num, page in enumerate(pdf_reader.pages, 1):

            text = page.extract_text().split()
            text_cursor.append_to_stream(text)

            seconds_elapsed = round(time.time() - start_time, 2)
            #print(chr(27) + "[2J")
            #print("\33[2K")
            print("\033c", end ="")
            red = "\u001b[31m"
            white = "\u001b[37m"
            reset = "\u001b[0m"
            print(f'Currently On: {filename}')
            print(f'File: [{red}{fileno}{reset}/{n_files}]') 
            print(f'Page: [{num}/{n_pages}]') 
            print(f'Time Elapsed: {seconds_elapsed} seconds')

            while text_cursor.continue_running():

                try:
                    text_cursor.shift_cursor_right()

                    if predicate.run(text_cursor):

                        query_state.log_success(filename, num, text_cursor)
                        
                except:
                    pass
    return query_state
                    
import csv

def write_dict_to_csv(dictionary, fields, filename):
    "Writes dictionary to csv file. Modified from https://www.tutorialspoint.com/How-to-save-a-Python-Dictionary-to-CSV-file"
    try:
        with open(filename, 'w') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fields)
            writer.writeheader()
            for data in dictionary:
                writer.writerow(data)
    except IOError:
        print("I/O error")

def report_successes(query_result, env):

    n = len(query_result.successes)
    print(f'total matches : {n}')
    dictionary = query_result.successes
    if dictionary:
        fields = dictionary[0].keys()
        filename = env.path + "matches.csv"

        write_dict_to_csv(dictionary, fields, filename)

class Env:

    def __init__(self):
        home = os.path.expanduser('~')
        self.path = f"{home}/Desktop/Unix/"

def main():
    env = Env()
    query_result = run_query(env)
    report_successes(query_result, env)

main()

