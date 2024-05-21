# Create video index
import polars as pl
from sentence_transformers import SentenceTransformer

df = pl.read_parquet('data/video-transcripts.parquet')
print(df.head())

# embed titles and transcipts
model_name = 'all-MiniLM-L6-v2'
column_name_list = ['title', 'transcript']

model = SentenceTransformer(model_name)

for column_name in column_name_list:
    # generate embeddings
    embedding_arr = model.encode(df[column_name].to_list())

    # store embeddings in a dataframe
    schema_dict = {column_name+'_embedding-'+str(i): float for i in range(embedding_arr.shape[1])}
    df_embedding = pl.DataFrame(embedding_arr, schema=schema_dict)

    # append embeddings to video index
    df = pl.concat([df, df_embedding], how='horizontal')

print(df.shape)
print(df.head())

#save index to file
df.write_parquet('data/video-index.parquet')