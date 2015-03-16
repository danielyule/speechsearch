from http.server import HTTPServer, SimpleHTTPRequestHandler
from nltk.corpus import inaugural, state_union
import json
import pickle
from urllib.parse import unquote
from nltk.stem.snowball import EnglishStemmer
from nltk.tokenize import word_tokenize

stemmer = EnglishStemmer()

def search_corp(corp, sa, search_text):
    docs = corp.keys()
    results = set()
    for term in word_tokenize(search_text):
        results = set()
        term = stemmer.stem(term)
        for doc in docs:
            if term in corp[doc]:
                results.add(doc)
        docs = results
    if len(results) == 0:
        return [], []
    current_term = ""
    included = set()

    dividing_terms = set()
    occurrences = 0
    for entry in sa:
        if entry.word != current_term:
            doc_count = len(included)
            if doc_count > 0:
                freq = doc_count / len(results)
                total_terms = 0
                for doc in included:
                    total_terms += doc_term_count[doc]["$TOTAL$"]
                diff = abs(freq - 0.5)
                if diff <= 0.1:
                    dividing_terms.add((current_term, occurrences / total_terms - 2 * term_count[current_term] / term_count["$TOTAL$"]))
            included = set()
            current_term = entry.word
            occurrences = 0
        if entry.doc_index in results:
            included.add(entry.doc_index)
            occurrences += 1

    return (results, dividing_terms)


class SAEntry():
    def __init__(self, index, doc_index, corp):
        self.index = index
        self.doc_index = doc_index
        self.word = corp[doc_index][index]
        self.corp = corp

    def __lt__(self, other):
        i1 = self.index
        i2 = other.index
        while i1 < len(self.corp[self.doc_index]) and i2 < len(self.corp[other.doc_index]) and \
                        self.corp[self.doc_index][i1] == self.corp[other.doc_index][i2]:
            i1 += 1
            i2 += 1
        if i1 == len(self.corp[self.doc_index]):
            return True
        elif i2 == len(self.corp[other.doc_index]):
            return False
        return self.corp[self.doc_index][i1] < self.corp[other.doc_index][i2]

def good_suggestion(suggestion):
    return len(suggestion) > 3 and not suggestion.isnumeric()

class SearchHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        path = self.path.split("?", 1)
        if path[0] == "/search":
            self.send_response(200, "OK")
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            if len(path) == 1:
                self.wfile.write(json.dumps({}).encode("UTF-8"))
            else:
                result = search_corp(corp, sa, unquote(path[1]))
                docs = [doc for doc in result[0]]
                if len(docs) > 10:
                    splits = sorted([split for split in result[1]], key=lambda item: item[1], reverse=True)
                    splits = [lookup[split[0]] for split in splits]
                    splits = [split for split in splits if good_suggestion(split)]
                else:
                    splits = []
                self.wfile.write(json.dumps({'docs': docs, 'splits': splits[:3]}).encode("UTF-8"))
        elif path[0] == '/doc':
            self.send_response(200, "OK")
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(contents[path[1]].encode("UTF-8"))
        else:
            super().do_GET()


if __name__ == "__main__":

    pk_file = open("data.dat", "rb")
    corp = pickle.load(pk_file)
    sa = pickle.load(pk_file)
    lookup = pickle.load(pk_file)
    doc_term_count = pickle.load(pk_file)
    term_count = pickle.load(pk_file)
    contents = {file_id: inaugural.raw(file_id) for file_id in inaugural.fileids()}
    contents.update({file_id: state_union.raw(file_id) for file_id in state_union.fileids()})
    pk_file.close()
    server = HTTPServer(('', 8080), SearchHandler)
    print("starting server")
    server.serve_forever()
