import polars as pl

from sentence_transformers import SentenceTransformer, util

from sklearn.metrics import DistanceMetric
import numpy as np

import matplotlib.pyplot as plt

df = pl.read_parquet('data/video-transcripts.parquet')
df_eval = pl.read_csv('data/eval-raw.csv')
print(df.head())

# embed titles and transcripts
# define "parameters"
column_to_embed_list = ['title', 'transcript']
model_name_list = ["all-MiniLM-L6-v2", "multi-qa-distilbert-cos-v1", "multi-qa-mpnet-base-dot-v1"]

# generate embeddings for each combination of column and model
# initialize dict to keep track of all text embeddings
text_embedding_dict = {}

for model_name in model_name_list:

    #define embedding model
    model = SentenceTransformer(model_name) 

    for column_name in column_to_embed_list:

        # define text embedding identifier
        key_name = model_name + "_" + column_name
        print(key_name)

        # generate embeddings for text under column_name
        embedding_arr = model.encode(df[column_name].to_list())
        print('')

        # append embeddings to dict
        text_embedding_dict[key_name] = embedding_arr

# embed queries
query_embedding_dict = {}

for model_name in model_name_list:

    #define embedding model
    model = SentenceTransformer(model_name)
    print(model_name)

    # embed query text
    embedding_arr = model.encode(df_eval['query'].to_list())
    print('')

    # append embedding to dict
    query_embedding_dict[model_name] = embedding_arr

# Evaluate search methods
def returnVideoID_index(df: pl.dataframe.frame.DataFrame, df_eval: pl.dataframe.frame.DataFrame, query_n: int) -> int:
    """
        Function to return the index of a dataframe corresponding to the nth row in evaluation dataframe
    """

    return [i for i in range(len(df)) if df['video_id'][i]==df_eval['video_id'][query_n]][0]

def evalTrueRankings(dist_arr_isorted: np.ndarray, df: pl.dataframe.frame.DataFrame, df_eval: pl.dataframe.frame.DataFrame) -> np.ndarray:
    """
        Function to return "true" video ID rankings for each evaluation query
    """
    
    # intialize array to store rankings of "correct" search result
    true_rank_arr = np.empty((1, dist_arr_isorted.shape[1]))
    
    # evaluate ranking of correct result for each query
    for query_n in range(dist_arr_isorted.shape[1]):
    
        # return "true" video ID's in df
        video_id_idx = returnVideoID_index(df, df_eval, query_n)
        
        # evaluate the ranking of the "true" video ID
        true_rank = np.argwhere(dist_arr_isorted[:,query_n]==video_id_idx)[0][0]
        
        # store the "true" video ID's ranking in array
        true_rank_arr[0,query_n] = true_rank

    return true_rank_arr

# initialize distance metrics to experiment
dist_name_list = ['euclidean', 'manhattan', 'chebyshev']
sim_name_list = ['cos_sim', 'dot_score']

# evaluate all possible combinations of model, columns to embed, and distance metrics

# initialize list to store results
eval_results = []

# loop through all models
for model_name in model_name_list:

    # generate query embedding
    query_embedding = query_embedding_dict[model_name]
    
    # loop through text columns
    for column_name in column_to_embed_list:

        # generate column embedding
        embedding_arr = text_embedding_dict[model_name+'_'+column_name]

        # loop through distance metrics
        for dist_name in dist_name_list:

            # compute distance between video text and query
            dist = DistanceMetric.get_metric(dist_name)
            dist_arr = dist.pairwise(embedding_arr, query_embedding)

            # sort indexes of distance array
            dist_arr_isorted = np.argsort(dist_arr, axis=0)

            # define label for search method
            method_name = "_".join([model_name, column_name, dist_name])

            # evaluate the ranking of the ground truth
            true_rank_arr = evalTrueRankings(dist_arr_isorted, df, df_eval)

            # store results
            eval_list = [method_name] + true_rank_arr.tolist()[0]
            eval_results.append(eval_list)

        # loop through sbert similarity scores
        for sim_name in sim_name_list:
            # apply similarity score from sbert
            cmd = "dist_arr = -util." + sim_name + "(embedding_arr, query_embedding)"
            exec(cmd)
    
            # sort indexes of distance array (notice minus sign in front of cosine similarity)
            dist_arr_isorted = np.argsort(dist_arr, axis=0)
    
            # define label for search method
            method_name = "_".join([model_name, column_name, sim_name.replace("_","-")])
    
            # evaluate the ranking of the ground truth
            true_rank_arr = evalTrueRankings(dist_arr_isorted, df, df_eval)
    
            # store results
            eval_list = [method_name] + true_rank_arr.tolist()[0]
            eval_results.append(eval_list)

# compute rankings for title + transcripts embedding
for model_name in model_name_list:
    
    # generate embeddings
    embedding_arr1 = text_embedding_dict[model_name+'_title']
    embedding_arr2 = text_embedding_dict[model_name+'_transcript']
    query_embedding = query_embedding_dict[model_name]

    for dist_name in dist_name_list:

        # compute distance between video text and query
        dist = DistanceMetric.get_metric(dist_name)
        dist_arr = dist.pairwise(embedding_arr1, query_embedding) + dist.pairwise(embedding_arr2, query_embedding)

        # sort indexes of distance array
        dist_arr_isorted = np.argsort(dist_arr, axis=0)

         # define label for search method
        method_name = "_".join([model_name, "title-transcript", dist_name])

        # evaluate the ranking of the ground truth
        true_rank_arr = evalTrueRankings(dist_arr_isorted, df, df_eval)

        # store results
        eval_list = [method_name] + true_rank_arr.tolist()[0]
        eval_results.append(eval_list)

    # loop through sbert similarity scores
    for sim_name in sim_name_list:
        # apply similarity score from sbert
        cmd = "dist_arr = -util." + sim_name + "(embedding_arr1, query_embedding) - util."+ sim_name + "(embedding_arr2, query_embedding)"
        exec(cmd)

        # sort indexes of distance array (notice minus sign in front of cosine similarity)
        dist_arr_isorted = np.argsort(dist_arr, axis=0)

        # define label for search method
        method_name = "_".join([model_name, "title-transcript", sim_name.replace("_","-")])

        # evaluate the ranking of the ground truth
        true_rank_arr = evalTrueRankings(dist_arr_isorted, df, df_eval)

        # store results
        eval_list = [method_name] + true_rank_arr.tolist()[0]
        eval_results.append(eval_list)

print(len(eval_results))

# define schema for results dataframe
schema_dict = {'method_name':str}
for i in range(len(eval_results[0])-1):
    schema_dict['rank_query-'+str(i)] = float

# store results in dataframe
df_results = pl.DataFrame(eval_results, schema=schema_dict)
print(df_results.head())

# compute mean rankings of ground truth search result
df_results = df_results.with_columns(new_col=pl.mean_horizontal(df_results.columns[1:])).rename({"new_col": "rank_query-mean"})

# compute number of ground truth results which appear in top 3
for i in [1,3]:
    df_results = df_results.with_columns(new_col=pl.sum_horizontal(df_results[:,1:-1]<i)).rename({"new_col": "num_in_top-"+str(i)})

# Look at top results
df_summary = df_results[['method_name', "rank_query-mean", "num_in_top-1", "num_in_top-3"]]
print(df_summary.sort('rank_query-mean').head())

df_summary.sort('rank_query-mean').head()[0,0]
print(df_summary.sort("num_in_top-1", descending=True).head())

df_summary.sort("num_in_top-1", descending=True).head()[0,0]
print(df_summary.sort("num_in_top-3", descending=True).head())

df_summary.sort("num_in_top-3", descending=True).head()[0,0]

for i in range(4):
    print(df_summary.sort("num_in_top-3", descending=True)['method_name'][i])