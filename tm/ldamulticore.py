"""Run a gensim LdaMulticore model with threaded matrix operations disabled."""

import logging
logging.basicConfig(
    level=logging.DEBUG, 
    format='%(asctime)s:%(levelname)s: %(message)s'
)

import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'

import sys
sys.path.append('../../')

import gensim

from argparse import ArgumentParser
import numpy as np
import json


if __name__ == '__main__':
    parser = ArgumentParser(
        description='Run a gensim LDAMulticore model.')
    parser.add_argument('-t', metavar='TOPICS', type=int, default=10,
        help='maximum number of LDA topics')
    parser.add_argument('-w', metavar='WORKERS', type=int, default=1, 
        help='number of LDAMulticore workers (CPUs – 1)')
    parser.add_argument('-i', metavar='ITERATIONS', type=int, default=1000, 
        help='number opf corpus iterations')
    parser.add_argument('-p', metavar='PASSES', type=int, default=1, 
        help='number of passes through the entire corpus')
    parser.add_argument('-c', metavar='CHUNKSIZE', type=int, default=2048, 
        help='document chunk size')
    parser.add_argument('-s', metavar='RANDOM_SEED', type=int, default=2**10, 
        help='random state for gensim LDAMulticore')
    parser.add_argument('-e', metavar='EVAL_EVERY', type=int, default=10, 
        help='compute perplexity after this many steps')
    
    parser.add_argument('--kappa', metavar='DECAY', type=float, default=0.5, 
        help='parameter kappa from online LDA paper')
    parser.add_argument('--tau', metavar='OFFSET', type=float, default=1.0, 
        help='parameter tau from online LDA paper')
    parser.add_argument('--alpha', metavar='ALPHA', type=float, default=0.01, 
        help='prior alpha')
    parser.add_argument('--eta', metavar='ETA', type=float, default=0.01, 
        help='prior eta')

    parser.add_argument('--dict', metavar='DICTIONARY', type=str, default=None,
        help='dictionary file for word to ID mappings')

    parser.add_argument('-n', metavar='OUTPUT_NAME', type=str, required=True,
        help='output filename')
    parser.add_argument('MMCORPUS', type=str,
        help='Matrix Market .mm file')

    cli = parser.parse_args()
    
    logging.info(cli)
    logging.info('HOSTNAME: %s', os.environ['HOSTNAME'])
    logging.info('CPU_COUNT: %d', os.cpu_count())

    # Load corpus and dictionary
    logging.info('MM path = %s', {cli.MMCORPUS})
    logging.info('Dictionary path = %s', f'{cli.MMCORPUS}.dictionary.cpickle')
    
    corpus = gensim.corpora.MmCorpus(cli.MMCORPUS)

    dct = None
    if cli.dict is not None:
        dct = gensim.corpora.Dictionary.load(cli.dict)
    
    # Turn off eval_every if requested
    if cli.e < 1:
        cli.e = None

    # Log all the parameters
    logging.info('LDA param: num_topics: %d', cli.t)
    logging.info('LDA param: workers: %d', cli.w)
    logging.info('LDA param: iterations: %d', cli.i)
    logging.info('LDA param: passes: %d', cli.p)
    logging.info('LDA param: chunksize: %d', cli.c)
    logging.info('LDA param: eval_every: %s', cli.e)
    logging.info('LDA param: decay: %.3f', cli.kappa)
    logging.info('LDA param: offset: %.3f', cli.tau)
    logging.info('LDA param: alpha: %.3f', cli.alpha)
    logging.info('LDA param: eta: %.3f', cli.eta)
    logging.info('LDA param: random_state: %d', cli.s)
    logging.info('LDA param: id2word: %s', 
        'None' if cli.dict is None else 'Specified')
    
    # Train the LDA model
    logging.info('Beginning training')
    lda = gensim.models.LdaMulticore(
        corpus=corpus, num_topics=cli.t, id2word=dct, workers=cli.w, 
        iterations=cli.i, passes=cli.p, chunksize=cli.c,
        decay=cli.kappa, offset=cli.tau, per_word_topics=True,
        alpha=cli.alpha, eta=cli.eta, random_state=cli.s,
        eval_every=cli.e)
    
    logging.info('Training concluded')
    logging.info('Saving...')
    lda.save(f'{cli.n}')

    document_topics = list(lda.get_document_topics(corpus))
    document_topics_array = np.zeros((len(document_topics), cli.t))

    for i in range(len(document_topics)):
        for t in document_topics[i]:
            document_topics_array[i][t[0]] = t[1]

    average_likelihood = np.sum(document_topics_array)

    topics = []
    for i in range(cli.t):
        topics.append({})
        topic_dist = lda.show_topic(i, topn=20)

        for j in range(len(topic_dist)):
            topic_dist[j] = (topic_dist[j][0], float(topic_dist[j][1]))

        topics[i]['top_words'] = topic_dist
        average_likelihood = np.sum(document_topics_array[:, i]) / document_topics_array.shape[0]
        topics[i]['average_likelihood'] = float(average_likelihood)

    with open('topics.json', 'w') as topics_file:
        json.dump(topics, topics_file)

    np.save('document_topics.npy', document_topics_array)
