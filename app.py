from flask import Flask, request, jsonify
from flask_cors import CORS
from annoy import AnnoyIndex
import pickle
import os
from collections import defaultdict
from helper import load_elective


app = Flask(__name__)

# Enable CORS for API endpoints
cors = CORS(app, resources={r'/api/*': {'origins': '*'}})

# Variables
f = 9
K_MAX = 5
ANNOY = AnnoyIndex(f, 'hamming')
SUB_TO_IDX = {}
IDX_TO_SUB = {}


@app.route("/api/v1/subject-list", methods=['GET'])
def subject_list():
    subjects = SUB_TO_IDX.keys()
    return jsonify({'subjects': list(subjects)})


@app.route("/api/v1/similar-subject", methods=['POST'])
def similar_subject():
    args = parse_args(request.get_json())
    if 'error' in args.keys():
        return jsonify(args)
    recommendation = recommendation_electivewise(args)
    return jsonify(recommendation)


def parse_args(data):
    subjects = data['subjects']
    # loading index for subject
    try:
        ids = [SUB_TO_IDX[subject] for subject in subjects]
        k = data['k'] if 'k' in data.keys() else 3
    except KeyError:
        return {"error": "Sorry given subject is not in database"}
    return {'ids': ids, 'k': min(k, K_MAX), 'electives': [1, 2]}


def recommendation_electivewise(args):
    ids, electives, k = args['ids'], args['electives'], args['k']
    res = []
    for elective in electives:
        d = { "elective_{}".format(elective): electivedwise_generation(elective, ids, k) }
        res.append(d)
    return res


def electivedwise_generation(elective_id, ids, k):
    subs = load_elective(elective_id)
    dists = []
    for idx in ids:
        dists += [(s, ANNOY.get_distance(idx, SUB_TO_IDX[s])) for s in subs]
        dists = refactor_dists(sorted(dists, key=lambda x: x[1]))[:k]
    score_sum = sum([d[1] for d in dists])
    return [{ "name": d[0], "score": round((d[1]/score_sum), 2) } for d in dists]


def load_variables():
    '''
        This function loads all the variable required to make recommendations for the given
        subject through API
    '''
    global SUB_TO_IDX, IDX_TO_SUB
    # Common Path to all variables
    mid_path = [os.curdir, 'model', 'KNB_MODEL', 'ONE_HOT']

    print("LOADING ANNOY...")
    ANNOY.load(os.path.join('', *(mid_path + ['tree.ann'])))

    print("LOADING SUBJECT-TO-INDEX MAP...")
    with open(os.path.join('', *(mid_path + ['subject2idx.pkl'])), 'rb') as f:
        SUB_TO_IDX = pickle.load(f)

    print("LOADING INDEX-TO-SUBJECT MAP...")
    with open(os.path.join('', *(mid_path + ['idx2subject.pkl'])), 'rb') as f:
        IDX_TO_SUB = pickle.load(f)

def refactor_dists(dists):
    d = defaultdict(lambda: 1e10)
    for dist in dists:
        name, score = dist
        d[name] = min(d[name], score)
    return [(name, value) for name, value in d.items()]


load_variables()

if __name__ == '__main__':
    app.run()