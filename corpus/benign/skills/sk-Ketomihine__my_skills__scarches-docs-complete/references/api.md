# Scarches-Docs-Complete - Api

**Pages:** 21

---

## Zenodo - scArches documentation

**URL:** http://127.0.0.1:9180/en/latest/api/zenodo.html

**Contents:**
- Zenodo
- Deposition helpers
- File Helpers

Downloads the zip file of the model in the link and saves it in save_path and extracts.

link (str) – Direct downloadable link.

save_path (str) – Directory path for downloaded file

make_dir (bool) – Whether to make the save_path if it does not exist in the system.

extract_dir – Full path to the folder of the model.

Uploads trained model to Zenodo.

model (TRVAE, SCVI, SCANVI, TOTALVI, str) – An instance of one of classes defined in scarches.models module or a path to a saved model.

deposition_id (str) – ID of a deposition in your Zenodo account.

access_token (str) – Your Zenodo access token.

model_name (str) – An optional name of the model to upload

download_link – Generated direct download link for the uploaded model in the deposition. Please Note that the link is usable after your published your deposition.

Creates a deposition in your Zenodo account.

access_token (str) – Your Zenodo access token.

deposition_id – ID of the created deposition.

Deletes the existing deposition with deposition_id in your Zenodo account.

deposition_id (str) – ID of a deposition in your Zenodo account.

access_token (str) – Your Zenodo Access token.

Gets list of all of deposition IDs existed in your Zenodo account.

access_token (str) – Your Zenodo access token.

deposition_ids – List of deposition IDs.

Publishes the existing deposition with deposition_id in your Zenodo account.

deposition_id (str) – ID of a deposition in your Zenodo account.

access_token (str) – Your Zenodo access token.

download_link – Generated direct download link for the uploaded model in the deposition. Please Note that the link is usable after your published your deposition.

Updates the existing deposition with deposition_id in your Zenodo account.

deposition_id (str) – ID of a deposition in your Zenodo account.

access_token (str) – Your Zenodo access token.

Downloads the file in the link and saves it in save_path.

link (str) – Direct downloadable link.

save_path (str) – Path with the name and extension of downloaded file.

make_dir (bool) – Whether to make the save_path if it does not exist in the system.

file_path (str) – Full path with name and extension of downloaded file. http_response (HTTPMessage) – HttpMessage object containing status code and information about the http request.

file_path (str) – Full path with name and extension of downloaded file.

http_response (HTTPMessage) – HttpMessage object containing status code and information about the http request.

Downloads the file in the link and saves it in save_path.

file_path (str) – Full path with the name and extension of the file you want to upload.

deposition_id (str) – ID of a deposition in your Zenodo account.

access_token (str) – Your Zenodo Access token.

file_path (str) – Full path with name and extension of downloaded file. http_response (HTTPMessage) – HttpMessage object containing status code and information about the http request.

file_path (str) – Full path with name and extension of downloaded file.

http_response (HTTPMessage) – HttpMessage object containing status code and information about the http request.

**Examples:**

Example 1 (unknown):
```unknown
scarches.models
```

Example 2 (unknown):
```unknown
deposition_id
```

Example 3 (unknown):
```unknown
deposition_id
```

Example 4 (unknown):
```unknown
deposition_id
```

Example 5 (unknown):
```unknown
HTTPMessage
```

Example 6 (unknown):
```unknown
HttpMessage
```

Example 7 (unknown):
```unknown
HTTPMessage
```

Example 8 (unknown):
```unknown
HttpMessage
```

Example 9 (unknown):
```unknown
download_model()
```

Example 10 (unknown):
```unknown
upload_model()
```

Example 11 (unknown):
```unknown
create_deposition()
```

Example 12 (unknown):
```unknown
delete_deposition()
```

Example 13 (unknown):
```unknown
get_all_deposition_ids()
```

Example 14 (unknown):
```unknown
publish_deposition()
```

Example 15 (unknown):
```unknown
update_deposition()
```

Example 16 (unknown):
```unknown
download_file()
```

Example 17 (unknown):
```unknown
upload_file()
```

---

## Integration, label transfer and multi-scale analysis with scPoli - scArches documentation

**URL:** http://127.0.0.1:9180/en/latest/scpoli_surgery_pipeline.html

**Contents:**
- Integration, label transfer and multi-scale analysis with scPoli
- Data download
- Reference - query split
- Train reference scPoli model on fully labeled reference data
- Reference mapping of unlabeled query datasets
- Label transfer from reference to query
- Inspect uncertainty
- Inspect prototypes
- Sample embeddings

In this notebook we demonstrate an example workflow of data integration, reference mapping, label transfer and multi-scale analysis of sample and cell embeddings using scPoli. We integrate pancreas data obtained from the scArches reproducibility repository. The data can be downloaded from figshare.

We split our data in a group of reference datasets to be used for reference building, and a group of query datasets that we will map.

In order to simulate an unknown cell type scenario, we manually remove beta cells from the reference.

Explanation of scPoli parameters:

condition_keys: obs column names of the covariate(s) you want to use for integration, if a list of names is passed, the model will use independent embeddings for each covariate

cell_type_keys: obs column names of the cell type annotation(s) to use for prototype learning, if a list is passed, the model will compute the prototype loss in parallel for each set of annotations passed

embedding_dims: embedding dimensionality, if an integer is passed, the model will use embeddings of the same dimensionality for each covariate, if the user wishes to define different dimensionalities for each covariate, a list needs to be provided

pretraining_epochs: number of epochs for which the model is trained in an unsupervised fashion

n_epochs: total number of training epochs, finetuning epochs therefore will be (n_epochs - pretraining_epochs)

eta: weight of the prototype loss

prototype_training: flag that can be used to turn off prototype training

unlabeled_prototype_training: flag that can be used to skip unlabeled prototype computation. This step involves Louvain clustering and can be time-consuming on big datasets. Unlabeled prototypes can be useful for downstream analyses but are not used at training time.

We recommend using a pretraining/training epoch ratio of approximately 80 or 90%. If you train for more total epochs you should use a higher ratio, whereas if you’re training for only a few epochs, this ratio can be smaller. If the model is trained withthe prototype loss for too many epochs it can lead to very concentrated clusters in latent space.

The uncertainties returned by the model consist of the distance between the cell in the latent space and the labeled prototypes closest to it. This distance does not have an upper bound, and the scale of the distance can provide information on the heterogeneity of the dataset. We also offer the option to scale the uncertainties between 0 and 1.

Let’s check the label transfer performance we achieved.

We can look at the uncertainty of each prediction and either select a threshold after visual inspection or by looking at the percentiles of the uncertainties distribution.

After inspecting the prototypes we can observe that unlabeled prototype 4, 5, 7, 8, 11 and 13 fall into the region of high uncertainty. With this knowledge, we can add a new labeled prototype.

We can now see that the alpha cell cluster is correctly classified.

We can extract the conditional embeddings learnt by scPoli and analyse them.

**Examples:**

Example 1 (python):
```python
import numpy as np
import scanpy as sc
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import classification_report
from scarches.models.scpoli import scPoli

import warnings
warnings.filterwarnings('ignore')
%load_ext autoreload
%autoreload 2
```

Example 2 (unknown):
```unknown
WARNING:root:In order to use the mouse gastrulation seqFISH datsets, please install squidpy (see https://github.com/scverse/squidpy).
INFO:lightning_fabric.utilities.seed:Global seed set to 0
WARNING:root:In order to use sagenet models, please install pytorch geometric (see https://pytorch-geometric.readthedocs.io) and
 captum (see https://github.com/pytorch/captum).
WARNING:root:mvTCR is not installed. To use mvTCR models, please install it first using "pip install mvtcr"
WARNING:root:multigrate is not installed. To use multigrate models, please install it first using "pip install multigrate".
```

Example 3 (python):
```python
sc.settings.set_figure_params(dpi=100, frameon=False)
sc.set_figure_params(dpi=100)
sc.set_figure_params(figsize=(3, 3))
plt.rcParams['figure.dpi'] = 100
plt.rcParams['figure.figsize'] = (3, 3)
```

Example 4 (unknown):
```unknown
!mkdir tmp
!wget -O tmp/pancreas.h5ad https://figshare.com/ndownloader/files/41581626
```

Example 5 (javascript):
```javascript
mkdir: tmp: File exists
--2023-07-17 12:47:23--  https://figshare.com/ndownloader/files/41581626
Resolving figshare.com (figshare.com)... 34.250.148.102, 34.242.105.80
Connecting to figshare.com (figshare.com)|34.250.148.102|:443... connected.
HTTP request sent, awaiting response... 302 Found
Location: https://s3-eu-west-1.amazonaws.com/pfigshare-u-files/41581626/pancreas_sparse.h5ad?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=AKIAIYCQYOYV5JSSROOA/20230717/eu-west-1/s3/aws4_request&X-Amz-Date=20230717T104723Z&X-Amz-Expires=10&X-Amz-SignedHeaders=host&X-Amz-Signature=88c2fa94548ab7326e567ed762e1b9275fb98b77b8c56b3bbf838213c24f1db7 [following]
--2023-07-17 12:47:23--  https://s3-eu-west-1.amazonaws.com/pfigshare-u-files/41581626/pancreas_sparse.h5ad?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=AKIAIYCQYOYV5JSSROOA/20230717/eu-west-1/s3/aws4_request&X-Amz-Date=20230717T104723Z&X-Amz-Expires=10&X-Amz-SignedHeaders=host&X-Amz-Signature=88c2fa94548ab7326e567ed762e1b9275fb98b77b8c56b3bbf838213c24f1db7
Resolving s3-eu-west-1.amazonaws.com (s3-eu-west-1.amazonaws.com)... 52.218.122.88, 52.218.116.136, 52.92.37.0, ...
Connecting to s3-eu-west-1.amazonaws.com (s3-eu-west-1.amazonaws.com)|52.218.122.88|:443... connected.
HTTP request sent, awaiting response... 200 OK
Length: 83620692 (80M) [application/octet-stream]
Saving to: ‘tmp/pancreas.h5ad’

tmp/pancreas.h5ad   100%[===================>]  79.75M  4.80MB/s    in 16s

2023-07-17 12:47:40 (4.86 MB/s) - ‘tmp/pancreas.h5ad’ saved [83620692/83620692]
```

Example 6 (python):
```python
adata = sc.read('tmp/pancreas.h5ad')
adata
```

Example 7 (unknown):
```unknown
AnnData object with n_obs × n_vars = 16382 × 4000
    obs: 'study', 'cell_type'
```

Example 8 (python):
```python
sc.pp.neighbors(adata)
sc.tl.umap(adata)
```

Example 9 (python):
```python
WARNING: You’re trying to run this on 4000 dimensions of `.X`, if you really want this, set `use_rep='X'`.
         Falling back to preprocessing with `sc.pp.pca` and default params.
```

Example 10 (unknown):
```unknown
OMP: Info #276: omp_set_nested routine deprecated, please use omp_set_max_active_levels instead.
```

Example 11 (python):
```python
sc.pl.umap(adata, color=['study', 'cell_type'], wspace=0.5, frameon=False)
```

Example 12 (unknown):
```unknown
early_stopping_kwargs = {
    "early_stopping_metric": "val_prototype_loss",
    "mode": "min",
    "threshold": 0,
    "patience": 20,
    "reduce_lr": True,
    "lr_patience": 13,
    "lr_factor": 0.1,
}

condition_key = 'study'
cell_type_key = 'cell_type'
reference = [
    'inDrop1',
    'inDrop2',
    'inDrop3',
    'inDrop4',
    'fluidigmc1',
    'smartseq2',
    'smarter'
]
query = ['celseq', 'celseq2']
```

Example 13 (python):
```python
adata.obs['query'] = adata.obs[condition_key].isin(query)
adata.obs['query'] = adata.obs['query'].astype('category')
source_adata = adata[adata.obs.study.isin(reference)].copy()
source_adata = source_adata[~source_adata.obs.cell_type.str.contains('alpha')].copy()
target_adata = adata[adata.obs.study.isin(query)].copy()
```

Example 14 (python):
```python
source_adata, target_adata
```

Example 15 (unknown):
```unknown
(AnnData object with n_obs × n_vars = 8634 × 4000
     obs: 'study', 'cell_type', 'query'
     uns: 'neighbors', 'umap', 'study_colors', 'cell_type_colors'
     obsm: 'X_pca', 'X_umap'
     obsp: 'distances', 'connectivities',
 AnnData object with n_obs × n_vars = 3289 × 4000
     obs: 'study', 'cell_type', 'query'
     uns: 'neighbors', 'umap', 'study_colors', 'cell_type_colors'
     obsm: 'X_pca', 'X_umap'
     obsp: 'distances', 'connectivities')
```

Example 16 (python):
```python
scpoli_model = scPoli(
    adata=source_adata,
    condition_keys=condition_key,
    cell_type_keys=cell_type_key,
    embedding_dims=5,
    recon_loss='nb',
)
scpoli_model.train(
    n_epochs=50,
    pretraining_epochs=40,
    early_stopping_kwargs=early_stopping_kwargs,
    eta=5,
)
```

Example 17 (unknown):
```unknown
Embedding dictionary:
        Num conditions: [7]
        Embedding dim: [5]
Encoder Architecture:
        Input Layer in, out and cond: 4000 64 5
        Mean/Var Layer in/out: 64 10
Decoder Architecture:
        First Layer in, out and cond:  10 64 5
        Output Layer in/out:  64 4000

Initializing dataloaders
Starting training
 |████████████████████| 100.0%  - val_loss: 1088.52 - val_cvae_loss: 1076.07 - val_prototype_loss:   12.45 - val_labeled_loss:    2.49
```

Example 18 (python):
```python
scpoli_query = scPoli.load_query_data(
    adata=target_adata,
    reference_model=scpoli_model,
    labeled_indices=[],
)
```

Example 19 (unknown):
```unknown
Embedding dictionary:
        Num conditions: [9]
        Embedding dim: [5]
Encoder Architecture:
        Input Layer in, out and cond: 4000 64 5
        Mean/Var Layer in/out: 64 10
Decoder Architecture:
        First Layer in, out and cond:  10 64 5
        Output Layer in/out:  64 4000
```

Example 20 (unknown):
```unknown
scpoli_query.train(
    n_epochs=50,
    pretraining_epochs=40,
    eta=10
)
```

Example 21 (python):
```python
Warning: Labels in adata.obs[cell_type] is not a subset of label-encoder!
The missing labels are: {'alpha'}
Therefore integer value of those labels is set to -1
Warning: Labels in adata.obs[cell_type] is not a subset of label-encoder!
The missing labels are: {'alpha'}
Therefore integer value of those labels is set to -1
Initializing dataloaders
Starting training
 |████████████████----| 80.0%  - val_loss: 1768.56 - val_cvae_loss: 1768.56
Initializing unlabeled prototypes with Leiden with an unknown number of  clusters.
Clustering succesful. Found 20 clusters.
 |████████████████████| 100.0%  - val_loss: 1759.32 - val_cvae_loss: 1759.32 - val_prototype_loss:    0.00 - val_unlabeled_loss:    0.76
```

Example 22 (python):
```python
results_dict = scpoli_query.classify(target_adata, scale_uncertainties=True)
```

Example 23 (python):
```python
for i in range(len(cell_type_key)):
    preds = results_dict[cell_type_key]["preds"]
    results_dict[cell_type_key]["uncert"]
    classification_df = pd.DataFrame(
        classification_report(
            y_true=target_adata.obs[cell_type_key],
            y_pred=preds,
            output_dict=True,
        )
    ).transpose()
print(classification_df)
```

Example 24 (unknown):
```unknown
precision    recall  f1-score      support
acinar               0.958416  0.964143  0.961271   502.000000
activated_stellate   0.908333  1.000000  0.951965   109.000000
alpha                0.000000  0.000000  0.000000  1034.000000
beta                 0.946288  0.988449  0.966909   606.000000
delta                0.759259  0.972332  0.852686   253.000000
ductal               0.959322  0.967521  0.963404   585.000000
endothelial          1.000000  1.000000  1.000000    26.000000
epsilon              0.018519  1.000000  0.036364     5.000000
gamma                0.163265  1.000000  0.280702   128.000000
macrophage           0.882353  0.937500  0.909091    16.000000
mast                 1.000000  0.714286  0.833333     7.000000
quiescent_stellate   1.000000  0.692308  0.818182    13.000000
schwann              1.000000  1.000000  1.000000     5.000000
t_cell               0.000000  0.000000  0.000000     0.000000
accuracy             0.667984  0.667984  0.667984     0.667984
macro avg            0.685411  0.802610  0.683850  3289.000000
weighted avg         0.605955  0.667984  0.623204  3289.000000
```

Example 25 (python):
```python
#get latent representation of reference data
scpoli_query.model.eval()
data_latent_source = scpoli_query.get_latent(
    source_adata,
    mean=True
)

adata_latent_source = sc.AnnData(data_latent_source)
adata_latent_source.obs = source_adata.obs.copy()

#get latent representation of query data
data_latent= scpoli_query.get_latent(
    target_adata,
    mean=True
)

adata_latent = sc.AnnData(data_latent)
adata_latent.obs = target_adata.obs.copy()

#get label annotations
adata_latent.obs['cell_type_pred'] = results_dict['cell_type']['preds'].tolist()
adata_latent.obs['cell_type_uncert'] = results_dict['cell_type']['uncert'].tolist()
adata_latent.obs['classifier_outcome'] = (
    adata_latent.obs['cell_type_pred'] == adata_latent.obs['cell_type']
)

#get prototypes
labeled_prototypes = scpoli_query.get_prototypes_info()
labeled_prototypes.obs['study'] = 'labeled prototype'
unlabeled_prototypes = scpoli_query.get_prototypes_info(prototype_set='unlabeled')
unlabeled_prototypes.obs['study'] = 'unlabeled prototype'

#join adatas
adata_latent_full = adata_latent_source.concatenate(
    [adata_latent, labeled_prototypes, unlabeled_prototypes],
    batch_key='query'
)
adata_latent_full.obs['cell_type_pred'][adata_latent_full.obs['query'].isin(['0'])] = np.nan
sc.pp.neighbors(adata_latent_full, n_neighbors=15)
sc.tl.umap(adata_latent_full)
```

Example 26 (python):
```python
#get adata without prototypes
adata_no_prototypes = adata_latent_full[adata_latent_full.obs['query'].isin(['0', '1'])]
```

Example 27 (python):
```python
sc.pl.umap(
    adata_no_prototypes,
    color='cell_type_pred',
    show=False,
    frameon=False,
)
```

Example 28 (unknown):
```unknown
<Axes: title={'center': 'cell_type_pred'}, xlabel='UMAP1', ylabel='UMAP2'>
```

Example 29 (python):
```python
sc.pl.umap(
    adata_no_prototypes,
    color='study',
    show=False,
    frameon=False,
)
```

Example 30 (unknown):
```unknown
<Axes: title={'center': 'study'}, xlabel='UMAP1', ylabel='UMAP2'>
```

Example 31 (python):
```python
sc.pl.umap(
    adata_no_prototypes,
    color='cell_type_uncert',
    show=False,
    frameon=False,
    cmap='magma',
    vmax=1
)
```

Example 32 (unknown):
```unknown
<Axes: title={'center': 'cell_type_uncert'}, xlabel='UMAP1', ylabel='UMAP2'>
```

Example 33 (python):
```python
fig, ax = plt.subplots(1, 1, figsize=(6, 5))
adata_labeled_prototypes = adata_latent_full[adata_latent_full.obs['query'].isin(['2'])]
adata_unlabeled_prototypes = adata_latent_full[adata_latent_full.obs['query'].isin(['3'])]
adata_labeled_prototypes.obs['cell_type_pred'] = adata_labeled_prototypes.obs['cell_type_pred'].astype('category')
adata_unlabeled_prototypes.obs['cell_type_pred'] = adata_unlabeled_prototypes.obs['cell_type_pred'].astype('category')
adata_unlabeled_prototypes.obs['cell_type'] = adata_unlabeled_prototypes.obs['cell_type'].astype('category')

sc.pl.umap(
    adata_no_prototypes,
    alpha=0.2,
    show=False,
    ax=ax
)
ax.legend([])
# plot labeled prototypes
sc.pl.umap(
    adata_labeled_prototypes,
    size=200,
    color=f'{cell_type_key}_pred',
    ax=ax,
    show=False,
    frameon=False,
)
cell_types = adata_labeled_prototypes.obs[f'{cell_type_key}_pred'].cat.categories
color_ct = adata_labeled_prototypes.uns[f'{cell_type_key}_pred_colors']
color_dict = dict(zip(cell_types, color_ct))
# plot labeled prototypes
sc.pl.umap(
    adata_unlabeled_prototypes,
    size=100,
    color=f'{cell_type_key}_pred',
    palette=color_dict,
    ax=ax,
    show=False,
    frameon=False,
    alpha=0.5,
)
sc.pl.umap(
    adata_unlabeled_prototypes,
    size=0,
    color=cell_type_key,
    #palette=color_dict,
    frameon=False,
    show=False,
    ax=ax,
    legend_loc='on data',
    legend_fontsize=5,
)
ax.set_title('Landmarks')
h, l = ax.get_legend_handles_labels()
ax.legend().remove()
ax.legend(handles=h[:13], labels= l[:13], frameon=False, bbox_to_anchor=(1, 1))
fig.tight_layout()
```

Example 34 (unknown):
```unknown
scpoli_query.add_new_cell_type(
    "alpha",
    cell_type_key,
    [3, 4, 5, 12, 13, 15, 19]
)
```

Example 35 (python):
```python
results_dict = scpoli_query.classify(target_adata)
```

Example 36 (python):
```python
#get latent representation of reference data
scpoli_query.model.eval()
data_latent_source = scpoli_query.get_latent(
    source_adata,
    mean=True
)

adata_latent_source = sc.AnnData(data_latent_source)
adata_latent_source.obs = source_adata.obs.copy()

#get latent representation of query data
data_latent= scpoli_query.get_latent(
    target_adata,
    mean=True
)

adata_latent = sc.AnnData(data_latent)
adata_latent.obs = target_adata.obs.copy()

#get label annotations
adata_latent.obs['cell_type_pred'] = results_dict['cell_type']['preds'].tolist()
adata_latent.obs['cell_type_uncert'] = results_dict['cell_type']['uncert'].tolist()
adata_latent.obs['classifier_outcome'] = (
    adata_latent.obs['cell_type_pred'] == adata_latent.obs['cell_type']
)

#join adatas
adata_latent_full = adata_latent_source.concatenate(
    [adata_latent, labeled_prototypes, unlabeled_prototypes],
    batch_key='query'
)
adata_latent_full.obs['cell_type_pred'][adata_latent_full.obs['query'].isin(['0'])] = np.nan
sc.pp.neighbors(adata_latent_full, n_neighbors=15)
sc.tl.umap(adata_latent_full)
```

Example 37 (python):
```python
sc.pl.umap(
    adata_latent_full,
    color='cell_type_pred',
    show=False,
    frameon=False,
)
```

Example 38 (unknown):
```unknown
<Axes: title={'center': 'cell_type_pred'}, xlabel='UMAP1', ylabel='UMAP2'>
```

Example 39 (python):
```python
adata_emb = scpoli_query.get_conditional_embeddings()
```

Example 40 (python):
```python
from sklearn.decomposition import KernelPCA
pca = KernelPCA(n_components=2, kernel='linear')
emb_pca = pca.fit_transform(adata_emb.X)
conditions = scpoli_query.conditions_['study']
fig, ax = plt.subplots(1, 1, figsize=(5, 5))
sns.scatterplot(x=emb_pca[:, 0], y=emb_pca[:, 1], hue=conditions, ax=ax)
ax.legend(bbox_to_anchor=(1.05, 1), loc=2, borderaxespad=0.)
for i, c in enumerate(conditions):
    ax.plot([0, emb_pca[i, 0]], [0, emb_pca[i, 1]])
    ax.text(emb_pca[i, 0], emb_pca[i, 1], c)
sns.despine()
```

---

## Utils - scArches documentation

**URL:** http://127.0.0.1:9180/en/latest/api/utils.html

**Contents:**
- Utils

Add annotations to an AnnData object from files.

adata – Annotated data matrix.

files – Paths to text files with annotations. The function considers rows to be gene sets with name of a gene set in the first column followed by names of genes.

min_genes – Only include gene sets which have the total number of genes in adata greater than this value.

max_genes – Only include gene sets which have the total number of genes in adata less than this value.

varm_key – Store the binary array I of size n_vars x number of annotated terms in files in adata.varm[varm_key]. if I[i,j]=1 then the gene i is present in the annotation j.

uns_key – Sore gene sets’ names in adata.uns[uns_key].

clean – If ‘True’, removes the word before the first underscore for each term name (like ‘REACTOME_’) and cuts the name to the first thirty symbols.

genes_use_upper – if ‘True’, converts genes’ names from files and adata to uppercase for comparison.

Trains a weighted KNN classifier on train_adata. :param train_adata: Annotated dataset to be used to train KNN classifier with label_key as the target variable. :type train_adata: AnnData :param train_adata_emb: Name of the obsm layer to be used for calculation of neighbors. If set to “X”, anndata.X will be

n_neighbors (int) – Number of nearest neighbors in KNN classifier.

Annotates query_adata cells with an input trained weighted KNN classifier. :param query_adata: Annotated dataset to be used to queryate KNN classifier. Embedding to be used :type query_adata: AnnData :param query_adata_emb: Name of the obsm layer to be used for label transfer. If set to “X”,

query_adata.X will be used

ref_adata_obs (pd.DataFrame) – obs of ref Anndata

label_keys (str) – Names of the columns to be used as target variables (e.g. cell_type) in query_adata.

knn_model (KNeighborsTransformer) – knn model trained on reference adata with weighted_knn_trainer function

threshold (float) – Threshold of uncertainty used to annotating cells as “Unknown”. cells with uncertainties higher than this value will be annotated as “Unknown”. Set to 1 to keep all predictions. This enables one to later on play with thresholds.

pred_unknown (bool) – False by default. Whether to annotate any cell as “unknown” or not. If False, threshold will not be used and each cell will be annotated with the label which is the most common in its n_neighbors nearest cells.

mode (str) – Has to be one of “paper” or “package”. If mode is set to “package”, uncertainties will be 1 - P(pred_label), otherwise it will be 1 - P(true_label).

**Examples:**

Example 1 (python):
```python
train_adata
```

Example 2 (python):
```python
query_adata
```

Example 3 (python):
```python
pd.DataFrame
```

Example 4 (python):
```python
query_adata
```

Example 5 (unknown):
```unknown
KNeighborsTransformer
```

Example 6 (unknown):
```unknown
n_neighbors
```

Example 7 (unknown):
```unknown
add_annotations()
```

Example 8 (unknown):
```unknown
weighted_knn_trainer()
```

Example 9 (unknown):
```unknown
weighted_knn_transfer()
```

---

## Basic tutorial for query to reference maping using expiMap - scArches documentation

**URL:** http://127.0.0.1:9180/en/latest/expimap_surgery_pipeline_basic.html

**Contents:**
- Basic tutorial for query to reference maping using expiMap
- Download reference and do preprocessing
- Create expiMap model and train it on reference dataset
- Downaload the query dataset for reference mapping
- Initlizling the model for query training
- Get latent representation of reference + query dataset

Also see the advanced tutorial to learn about adding constrained and unconstrained extension nodes to the query to capture new sources of variation, that is new and de novo gene programs, not in the reference dataset.

.X should contain raw counts.

Read the Reactome annotations, make a binary matrix where rows represent gene symbols and columns represent the terms, and add the annotations matrix to the reference dataset. The binary matrix of annotations is stored in adata.varm['I']. Note that only terms with minimum of 12 genes in the reference dataset are retained.

Remove all genes which are not present in the Reactome annotations.

For a better model performance it is necessary to select HVGs. We are doing this by applying the scanpy.pp function highly_variable_genes(). The n_top_genes is set to 2000 here. However, for more complicated datasets you might have to increase number of genes to capture more diversity in the data.

Filter out all annotations (terms) with less than 12 genes.

Filter out genes not present in any of the terms after selection of HVGs.

Put the counts data back to adata.X.

Set the alpha hyperparameter. This regulates the strength of group lasso regularization of annotations (terms). Higher value means that a larger number of latent variables corresponding to annotations will be deactivated during training depending on their contribution to the reconstruction loss.

See also https://docs.scarches.org/en/latest/training_tips.html for the recommendation on hyperparameter choice.

Plot the latent space of the reference.

The Kang dataset contains control and IFN-beta stimulated cells. We use this as the query dataset.

Calculate directions of upregulation for each latent score and put them to kang_pbmc.uns['directions'].

Do gene set enrichment test for condition in reference + query using Bayes Factors.

As expected, INTERFERON_ALPHA_BETA_SIGNALING is the top differential program in stimulated compared to control cells.

Plot the latent variables for query + reference corresponding to the annotations ‘INTERFERON_SIGNALING’, ‘SIGNALING_BY_THE_B_CELL_RECEPTOR’, ‘INTERFERON_ALPHA_BETA_SIGNALING’.

Multiplying the latent varibales by the calculated directons to ensure positive latent scores corresponf to upregulation.

**Examples:**

Example 1 (python):
```python
import warnings
warnings.simplefilter(action='ignore')
```

Example 2 (python):
```python
import scanpy as sc
import torch
import scarches as sca
import numpy as np
import gdown
```

Example 3 (unknown):
```unknown
Global seed set to 0
```

Example 4 (python):
```python
sc.set_figure_params(frameon=False)
sc.set_figure_params(dpi=200)
sc.set_figure_params(figsize=(4, 4))
torch.set_printoptions(precision=3, sci_mode=False, edgeitems=7)
```

Example 5 (unknown):
```unknown
url = 'https://drive.google.com/uc?id=1Rnm-XKEqPLdOq3lpa3ka2aV4bOXVCLP0'
output = 'pbmc_tutorial.h5ad'
gdown.download(url, output, quiet=False)
```

Example 6 (unknown):
```unknown
Downloading...
From: https://drive.google.com/uc?id=1Rnm-XKEqPLdOq3lpa3ka2aV4bOXVCLP0
To: C:\Users\sergei.rybakov\projects\notebooks\pbmc_tutorial.h5ad
100%|███████████████████████████████████████████████████████████████████████████████| 231M/231M [00:42<00:00, 5.39MB/s]
```

Example 7 (unknown):
```unknown
'pbmc_tutorial.h5ad'
```

Example 8 (python):
```python
adata = sc.read('pbmc_tutorial.h5ad')
```

Example 9 (python):
```python
adata.X = adata.layers["counts"].copy()
```

Example 10 (python):
```python
adata.varm['I']
```

Example 11 (unknown):
```unknown
url = 'https://drive.google.com/uc?id=1136LntaVr92G1MphGeMVcmpE0AqcqM6c'
output = 'reactome.gmt'
gdown.download(url, output, quiet=False)
```

Example 12 (python):
```python
sca.utils.add_annotations(adata, 'reactome.gmt', min_genes=12, clean=True)
```

Example 13 (python):
```python
adata._inplace_subset_var(adata.varm['I'].sum(1)>0)
```

Example 14 (unknown):
```unknown
highly_variable_genes()
```

Example 15 (unknown):
```unknown
n_top_genes
```

Example 16 (python):
```python
sc.pp.normalize_total(adata)
```

Example 17 (python):
```python
sc.pp.log1p(adata)
```

Example 18 (python):
```python
sc.pp.highly_variable_genes(
    adata,
    n_top_genes=2000,
    batch_key="batch",
    subset=True)
```

Example 19 (python):
```python
select_terms = adata.varm['I'].sum(0)>12
```

Example 20 (python):
```python
adata.uns['terms'] = np.array(adata.uns['terms'])[select_terms].tolist()
```

Example 21 (python):
```python
adata.varm['I'] = adata.varm['I'][:, select_terms]
```

Example 22 (python):
```python
adata._inplace_subset_var(adata.varm['I'].sum(1)>0)
```

Example 23 (python):
```python
adata.X = adata.layers["counts"].copy()
```

Example 24 (python):
```python
intr_cvae = sca.models.EXPIMAP(
    adata=adata,
    condition_key='study',
    hidden_layer_sizes=[256, 256, 256],
    recon_loss='nb'
)
```

Example 25 (unknown):
```unknown
INITIALIZING NEW NETWORK..............
Encoder Architecture:
        Input Layer in, out and cond: 1972 256 4
        Hidden Layer 1 in/out: 256 256
        Hidden Layer 2 in/out: 256 256
        Mean/Var Layer in/out: 256 282
Decoder Architecture:
        Masked linear layer in, ext_m, ext, cond, out:  282 0 0 4 1972
        with hard mask.
Last Decoder layer: softmax
```

Example 26 (unknown):
```unknown
ALPHA = 0.7
```

Example 27 (unknown):
```unknown
early_stopping_kwargs = {
    "early_stopping_metric": "val_unweighted_loss", # val_unweighted_loss
    "threshold": 0,
    "patience": 50,
    "reduce_lr": True,
    "lr_patience": 13,
    "lr_factor": 0.1,
}
intr_cvae.train(
    n_epochs=400,
    alpha_epoch_anneal=100,
    alpha=ALPHA,
    alpha_kl=0.5,
    weight_decay=0.,
    early_stopping_kwargs=early_stopping_kwargs,
    use_early_stopping=True,
    monitor_only_val=False,
    seed=2020,
)
```

Example 28 (unknown):
```unknown
Init the group lasso proximal operator for the main terms.
 |████████------------| 41.8%  - epoch_loss: 875.0875513335 - epoch_recon_loss: 849.8969689248 - epoch_kl_loss: 50.3811637679 - val_loss: 938.5590139536 - val_recon_loss: 912.9722806490 - val_kl_loss: 51.17346543531427418
ADJUSTED LR
 |█████████-----------| 46.0%  - epoch_loss: 867.2534920638 - epoch_recon_loss: 842.2286955321 - epoch_kl_loss: 50.0495922638 - val_loss: 939.3953810472 - val_recon_loss: 913.6503906250 - val_kl_loss: 51.4899893541
ADJUSTED LR
 |██████████----------| 50.5%  - epoch_loss: 868.1691942506 - epoch_recon_loss: 843.1531918455 - epoch_kl_loss: 50.0320032611 - val_loss: 937.6233802209 - val_recon_loss: 911.8207420936 - val_kl_loss: 51.6052835905
ADJUSTED LR
 |████████████--------| 60.2%  - epoch_loss: 874.0884924476 - epoch_recon_loss: 848.9184943453 - epoch_kl_loss: 50.3399958715 - val_loss: 938.2763272799 - val_recon_loss: 912.5495535044 - val_kl_loss: 51.4535569411
ADJUSTED LR
 |████████████--------| 63.5%  - epoch_loss: 871.6074394659 - epoch_recon_loss: 846.5056099038 - epoch_kl_loss: 50.2036596073 - val_loss: 938.8283644456 - val_recon_loss: 913.1071777344 - val_kl_loss: 51.4423753298
ADJUSTED LR
 |█████████████-------| 66.8%  - epoch_loss: 872.8487410233 - epoch_recon_loss: 847.7790292798 - epoch_kl_loss: 50.1394200054 - val_loss: 938.3776691143 - val_recon_loss: 912.6276245117 - val_kl_loss: 51.5000856840
ADJUSTED LR
 |█████████████-------| 69.5%  - epoch_loss: 872.2917062018 - epoch_recon_loss: 847.1418017258 - epoch_kl_loss: 50.2998066532 - val_loss: 943.0606759878 - val_recon_loss: 917.2311988244 - val_kl_loss: 51.6589726668
Stopping early: no improvement of more than 0 nats in 50 epochs
If the early stopping criterion is too strong, please instantiate it with different parameters in the train method.
Saving best state of network...
Best State was in Epoch 226
```

Example 29 (unknown):
```unknown
MEAN = False
```

Example 30 (python):
```python
adata.obsm['X_cvae'] = intr_cvae.get_latent(mean=MEAN, only_active=True)
```

Example 31 (python):
```python
sc.pp.neighbors(adata, use_rep='X_cvae')
```

Example 32 (python):
```python
sc.tl.umap(adata)
```

Example 33 (python):
```python
sc.pl.umap(adata, color=['study', 'cell_type'], frameon=False)
```

Example 34 (unknown):
```unknown
url = 'https://drive.google.com/uc?id=1t3oMuUfueUz_caLm5jmaEYjBxVNSsfxG'
output = 'kang_tutorial.h5ad'
gdown.download(url, output, quiet=False)
```

Example 35 (python):
```python
kang = sc.read('kang_tutorial.h5ad')[:, adata.var_names].copy()
```

Example 36 (unknown):
```unknown
kang.obs['study'] = 'Kang'
```

Example 37 (python):
```python
kang.uns['terms'] = adata.uns['terms']
```

Example 38 (unknown):
```unknown
q_intr_cvae = sca.models.EXPIMAP.load_query_data(kang, intr_cvae)
```

Example 39 (unknown):
```unknown
INITIALIZING NEW NETWORK..............
Encoder Architecture:
        Input Layer in, out and cond: 1972 256 5
        Hidden Layer 1 in/out: 256 256
        Hidden Layer 2 in/out: 256 256
        Mean/Var Layer in/out: 256 282
Decoder Architecture:
        Masked linear layer in, ext_m, ext, cond, out:  282 0 0 5 1972
        with hard mask.
Last Decoder layer: softmax
```

Example 40 (unknown):
```unknown
q_intr_cvae.train(n_epochs=400, alpha_epoch_anneal=100, weight_decay=0., alpha_kl=0.1, seed=2020, use_early_stopping=True)
```

Example 41 (unknown):
```unknown
|████████------------| 41.2%  - val_loss: 519.4205793901 - val_recon_loss: 512.4798778187 - val_kl_loss: 69.40706010300
ADJUSTED LR
 |████████------------| 43.0%  - val_loss: 520.2541309703 - val_recon_loss: 513.2979486639 - val_kl_loss: 69.5618133545
Stopping early: no improvement of more than 0 nats in 20 epochs
If the early stopping criterion is too strong, please instantiate it with different parameters in the train method.
Saving best state of network...
Best State was in Epoch 150
```

Example 42 (unknown):
```unknown
q_intr_cvae.save('query_kang_tutorial')
```

Example 43 (python):
```python
kang_pbmc = sc.AnnData.concatenate(adata, kang, batch_key='batch_join', uns_merge='same')
```

Example 44 (unknown):
```unknown
kang_pbmc.obsm['X_cvae'] = q_intr_cvae.get_latent(kang_pbmc.X, kang_pbmc.obs['study'], mean=MEAN, only_active=True)
```

Example 45 (python):
```python
sc.pp.neighbors(kang_pbmc, use_rep='X_cvae')
sc.tl.umap(kang_pbmc)
```

Example 46 (unknown):
```unknown
kang_pbmc.obs['condition_joint'] = kang_pbmc.obs.condition.astype(str)
kang_pbmc.obs['condition_joint'][kang_pbmc.obs['condition_joint'].astype(str)=='nan']='control'
```

Example 47 (python):
```python
sc.pl.umap(kang_pbmc, color=['study', 'cell_type'], frameon=False, wspace=0.6)
```

Example 48 (unknown):
```unknown
... storing 'batch' as categorical
... storing 'chemistry' as categorical
... storing 'data_type' as categorical
... storing 'final_annotation' as categorical
... storing 'sample_ID' as categorical
... storing 'species' as categorical
... storing 'study' as categorical
... storing 'tissue' as categorical
... storing 'cell_type' as categorical
... storing 'orig.ident' as categorical
... storing 'stim' as categorical
... storing 'seurat_annotations' as categorical
... storing 'condition' as categorical
... storing 'condition_joint' as categorical
```

Example 49 (python):
```python
sc.pl.umap(kang_pbmc, color='condition_joint', frameon=False, wspace=0.6)
```

Example 50 (unknown):
```unknown
kang_pbmc.uns['directions']
```

Example 51 (python):
```python
q_intr_cvae.latent_directions(adata=kang_pbmc)
```

Example 52 (python):
```python
q_intr_cvae.latent_enrich(groups='condition_joint', comparison='control', use_directions=True, adata=kang_pbmc)
```

Example 53 (unknown):
```unknown
fig = sca.plotting.plot_abs_bfs(kang_pbmc, yt_step=0.8, scale_y=2.5, fontsize=7)
```

Example 54 (unknown):
```unknown
INTERFERON_ALPHA_BETA_SIGNALING
```

Example 55 (unknown):
```unknown
terms = kang_pbmc.uns['terms']
select_terms = ['INTERFERON_SIGNALING', 'INTERFERON_ALPHA_BETA_SIGNALIN', 'SIGNALING_BY_THE_B_CELL_RECEPT']
idx = [terms.index(term) for term in select_terms]
```

Example 56 (unknown):
```unknown
latents = (q_intr_cvae.get_latent(kang_pbmc.X, kang_pbmc.obs['study'], mean=MEAN) * kang_pbmc.uns['directions'])[:, idx]
```

Example 57 (unknown):
```unknown
kang_pbmc.obs['INTERFERON_SIGNALING'] = latents[:, 0]
kang_pbmc.obs['INTERFERON_ALPHA_BETA_SIGNALIN'] = latents[:, 1]

kang_pbmc.obs['SIGNALING_BY_THE_B_CELL_RECEPT'] = latents[:, 2]
```

Example 58 (python):
```python
sc.pl.scatter(kang_pbmc, x='INTERFERON_ALPHA_BETA_SIGNALIN', y='SIGNALING_BY_THE_B_CELL_RECEPT', color='condition_joint', size=10)
```

Example 59 (python):
```python
sc.pl.scatter(kang_pbmc, x='INTERFERON_SIGNALING', y='SIGNALING_BY_THE_B_CELL_RECEPT', color='condition_joint', size=10)
```

Example 60 (python):
```python
sc.pl.scatter(kang_pbmc, x='INTERFERON_ALPHA_BETA_SIGNALIN', y='SIGNALING_BY_THE_B_CELL_RECEPT', color='cell_type', size=10)
```

---

## scArches (PyTorch) - single-cell architecture surgery - scArches documentation

**URL:** http://127.0.0.1:9180/en/latest/about.html

**Contents:**
- scArches (PyTorch) - single-cell architecture surgery
- What can you do with scArches?
- What are the different models?
- Where to start?
- Reference

scArches is a package to integrate newly produced single-cell datasets into integrated reference atlases. Our method can facilitate large collaborative projects with decentralized training and integration of multiple datasets by different groups. scArches is compatible with scanpy. and hosts efficient implementations of all conditional generative models for single-cell data.

expiMap has been added to scArches code base. It allows interpretable representation learning from scRNA-seq data and also reference mapping. Try it in the tutorial section.

Construct single or multi-modal (CITE-seq) reference atlases and share the trained model and the data (if possible).

Download a pre-trained model for your atlas of interest, update it with new datasets and share with your collaborators.

Project and integrate query datasets on the top of a reference and use latent representation for downstream tasks, e.g.:diff testing, clustering, classification

scArches is itself an algorithm to map to project query on the top of reference datasets and applies to different models. Here we provide a short explanation and hints on when to use which model. Our models are:

scVI (Lopez et al., 2018): Requires access to raw counts values for data integration and assumes count distribution on the data (NB, ZINB, Poisson).

trVAE (Lotfollahi et al.,2020): It supports both normalized log-transformed or count data as input and applies additional MMD loss to have better merging in the latent space.

scANVI (Xu et al., 2019): It needs cell type labels for reference data. Your query data can be either unlabeled or labeled. In the case of unlabeled query data, you can use this method also to classify your query cells using reference labels.

scGen (Lotfollahi et al., 2019): This method requires cell-type labels for both reference building and Mapping. The reference mapping for this method solely relies on the integrated reference and requires no fine-tuning.

expiMap (Lotfollahi*, Rybakov* et al., 2023): This method takes prior knowledge from gene sets databases or users allowing to analyze your query data in the context of known gene programs.

totalVI (Gayoso al., 2019): This model can be used to build multi-modal CITE-seq reference atalses.

treeArches (Michielsen*, Lotfollahi* et al., 2022): This model builds a hierarchical tree for cell-types in the reference atlas and when mapping the query data can annotate and also identify novel cell-states and populations present in the query data.

SageNet (Heidari et al., 2022): This model allows constrcution of a spatial atlas by mapping query dissociated single cells/spots (e.g., from scRNAseq or visium datasets) into a common coordinate framework using one or more spatially resolved reference datasets.

mvTCR (Drost et al., 2022): Using this model you will be able to integrate T-cell receptor (TCR, treated as a sequence) and scRNA-seq dataset across multiple donors into a joint representation capturing information from both modalities.

scPoli (De Donno et al., 2022): This model allows data integration of scRNA-seq dataset, prototype-based label transfer and reference mapping. scPoli learns both sample embeddings and integrated cell embeddings, thus providing the user with a multi-scale view of the data, especially useful in the case of many samples to integrate.

To get a sense of how the model works please go through this tutorial. To find out how to construct and share or use pre-trained models example sections.

If scArches is useful in your research, please consider citing the paper.

---

## Reference maping using scGen - scArches documentation

**URL:** http://127.0.0.1:9180/en/latest/scgen_map_query.html

**Contents:**
- Reference maping using scGen
- set relevant anndata.obs labels and training hyperparameters
- Download Dataset and split into reference dataset and query dataset
- original uncorrected data UMAP
- Create scGen model and train it on reference dataset
  - Correct batches in reference data
- Project query on top of the reference
- Plot the latent space of integrated query and reference
- Plot corrected gene expression space of integrated query and reference

In this tutorial, we are going to build a reference atlas using scGen and also map two new query datasets on the top of the reference atlas.

Note: scGen requires cell-type labels for data integration. The method outputs both corrected gene expression and also latent space.

Imortant note : scGen requires normalized and log-transformed data in ``adata.X``

As observed above these Pancreas studies are seperated accroding to source of study

Here we use the CelSeq2 and SS2 studies as query data and the other 3 studies to build as reference atlas.

Create the scgen model instance

This function returns corrected gene expression in adata.X, raw uncorrected data in adata.obsm["original_data"]. Also it returns uncorrected data in adata.layers["original_data"].

The low-dimensional corrected latent space in adata.obsm["latent_corrected"]

Corrected gene expression

We an also use low-dim corrected reference data

After training, the model can be saved for later use and projection of new query studies

query data needs to be preprocessed same way as reference data with same genes

This function need pretrained reference model, corrected gene expression from reference data and incorrected query data

**Examples:**

Example 1 (python):
```python
import os
import sys
sys.path.insert(0, "../")

import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)
warnings.simplefilter(action='ignore', category=UserWarning)
```

Example 2 (python):
```python
import scanpy as sc
import scarches as sca
from scarches.dataset.trvae.data_handling import remove_sparsity
import matplotlib.pyplot as plt
import numpy as np
import gdown
```

Example 3 (python):
```python
sc.settings.set_figure_params(dpi=200, frameon=False)
sc.set_figure_params(dpi=200)
sc.set_figure_params(figsize=(4, 4))
```

Example 4 (unknown):
```unknown
condition_key = 'study'
cell_type_key = 'cell_type'
target_conditions = ['Pancreas CelSeq2', 'Pancreas SS2']


epoch = 50

early_stopping_kwargs = {
    "early_stopping_metric": "val_loss",
    "patience": 20,
    "threshold": 0,
    "reduce_lr": True,
    "lr_patience": 13,
    "lr_factor": 0.1,
}
```

Example 5 (unknown):
```unknown
url = 'https://drive.google.com/uc?id=1ehxgfHTsMZXy6YzlFKGJOsBKQ5rrvMnd'
output = 'pancreas.h5ad'
gdown.download(url, output, quiet=False)
```

Example 6 (unknown):
```unknown
Downloading...
From: https://drive.google.com/uc?id=1ehxgfHTsMZXy6YzlFKGJOsBKQ5rrvMnd
To: /home/mo/projects/scarches/notebooks/pancreas.h5ad
126MB [00:01, 102MB/s]
```

Example 7 (unknown):
```unknown
'pancreas.h5ad'
```

Example 8 (python):
```python
adata = sc.read('pancreas.h5ad')
```

Example 9 (python):
```python
sc.pp.neighbors(adata)
```

Example 10 (python):
```python
WARNING: You’re trying to run this on 1000 dimensions of `.X`, if you really want this, set `use_rep='X'`.
         Falling back to preprocessing with `sc.pp.pca` and default params.
```

Example 11 (python):
```python
sc.tl.umap(adata)
```

Example 12 (python):
```python
sc.pl.umap(adata, color=['study', 'cell_type'],
           frameon=False, wspace=0.6)
```

Example 13 (python):
```python
adata = remove_sparsity(adata) # remove sparsity
source_adata = adata[~adata.obs[condition_key].isin(target_conditions)].copy()
target_adata = adata[adata.obs[condition_key].isin(target_conditions)].copy()
```

Example 14 (python):
```python
network = sca.models.scgen(adata = source_adata,
                           hidden_layer_sizes=[256,128])
```

Example 15 (unknown):
```unknown
INITIALIZING NEW NETWORK..............
Encoder Architecture:
        Input Layer in, out: 1000 256
        Hidden Layer 1 in/out: 256 128
        Mean/Var Layer in/out: 128 10
Decoder Architecture:
        First Layer in, out 10 128
        Hidden Layer 1 in/out: 128 256
        Output Layer in/out:  256 1000
```

Example 16 (unknown):
```unknown
network.train(n_epochs=epoch, early_stopping_kwargs = early_stopping_kwargs)
```

Example 17 (unknown):
```unknown
|████████████████████| 100.0%  - epoch_loss: 1.9351395184 - val_loss: 1.8963928728
Saving best state of network...
Best State was in Epoch 87
```

Example 18 (python):
```python
adata.obsm["original_data"]
```

Example 19 (python):
```python
adata.layers["original_data"]
```

Example 20 (python):
```python
adata.obsm["latent_corrected"]
```

Example 21 (python):
```python
corrected_reference_adata = network.batch_removal(source_adata, batch_key="study", cell_label_key="cell_type",return_latent=True)
```

Example 22 (python):
```python
sc.pp.neighbors(corrected_reference_adata)
sc.tl.umap(corrected_reference_adata)
sc.pl.umap(corrected_reference_adata, color=["study", "cell_type"], wspace=.5, frameon=False)
```

Example 23 (python):
```python
WARNING: You’re trying to run this on 1000 dimensions of `.X`, if you really want this, set `use_rep='X'`.
         Falling back to preprocessing with `sc.pp.pca` and default params.
... storing 'cell_type' as categorical
```

Example 24 (python):
```python
sc.pp.neighbors(corrected_reference_adata, use_rep="latent_corrected")
sc.tl.umap(corrected_reference_adata)
sc.pl.umap(corrected_reference_adata,
           color=['study', 'cell_type'],
           frameon=False,
           wspace=0.6,
           )
```

Example 25 (unknown):
```unknown
ref_path = './ref_model/'
network.save(ref_path, overwrite=True)
```

Example 26 (unknown):
```unknown
os.getcwd()
```

Example 27 (unknown):
```unknown
'/home/mo/projects/scarches/notebooks'
```

Example 28 (python):
```python
# here we pass the saved model from a file to the map query
integrated_query = sca.models.scgen.map_query_data(reference_model = network,
                                                   corrected_reference = corrected_reference_adata,
                                                   query = target_adata,
                                                   batch_key = 'study',
                                                   return_latent=True)
```

Example 29 (unknown):
```unknown
INITIALIZING NEW NETWORK..............
Encoder Architecture:
        Input Layer in, out: 1000 256
        Hidden Layer 1 in/out: 256 128
        Mean/Var Layer in/out: 128 10
Decoder Architecture:
        First Layer in, out 10 128
        Hidden Layer 1 in/out: 128 256
        Output Layer in/out:  256 1000
```

Example 30 (python):
```python
sc.pp.neighbors(integrated_query, use_rep="latent_corrected")
sc.tl.umap(integrated_query)
sc.pl.umap(
    integrated_query,
    color=["study", "cell_type"],
    frameon=False,
    wspace=0.6)
```

Example 31 (unknown):
```unknown
... storing 'batch' as categorical
... storing 'study' as categorical
... storing 'cell_type' as categorical
... storing 'original_batch' as categorical
```

Example 32 (python):
```python
sc.pp.neighbors(integrated_query)
sc.tl.umap(integrated_query)
sc.pl.umap(
    integrated_query,
    color=["study", "cell_type"],
    frameon=False,
    wspace=0.6)
```

Example 33 (python):
```python
WARNING: You’re trying to run this on 1000 dimensions of `.X`, if you really want this, set `use_rep='X'`.
         Falling back to preprocessing with `sc.pp.pca` and default params.
```

---

## Plotting - scArches documentation

**URL:** http://127.0.0.1:9180/en/latest/api/plotting.html

**Contents:**
- Plotting

plot_latent([show, save, dir_path, ...])

get_classification_accuracy

name = ‘scanvi_latent.png’

name = f’{dir_path}.png’

Plot the absolute bayes scores rankings.

Draws Sankey diagram for the given data. :param data: array with 2 columns. One for predictions and another for true values. :type data: ndarray :param save_path: Path to save the drawn Sankey diagram. if None, the diagram will not be saved. :type save_path: str :param show: if True will show the diagram. :type show: bool :param kwargs: additional arguments for diagram configuration. See _alluvial.plot function.

**Examples:**

Example 1 (unknown):
```unknown
plot_latent
```

Example 2 (unknown):
```unknown
_alluvial.plot
```

Example 3 (unknown):
```unknown
SCVI_EVAL.get_asw()
```

Example 4 (unknown):
```unknown
SCVI_EVAL.get_classification_accuracy()
```

Example 5 (unknown):
```unknown
SCVI_EVAL.get_ebm()
```

Example 6 (unknown):
```unknown
SCVI_EVAL.get_f1_score()
```

Example 7 (unknown):
```unknown
SCVI_EVAL.get_knn_purity()
```

Example 8 (unknown):
```unknown
SCVI_EVAL.get_latent_score()
```

Example 9 (unknown):
```unknown
SCVI_EVAL.get_model_arch()
```

Example 10 (unknown):
```unknown
SCVI_EVAL.get_nmi()
```

Example 11 (unknown):
```unknown
SCVI_EVAL.latent_as_anndata()
```

Example 12 (unknown):
```unknown
SCVI_EVAL.plot_history()
```

Example 13 (unknown):
```unknown
SCVI_EVAL.plot_latent()
```

Example 14 (unknown):
```unknown
TRVAE_EVAL.get_asw()
```

Example 15 (unknown):
```unknown
TRVAE_EVAL.get_ebm()
```

Example 16 (unknown):
```unknown
TRVAE_EVAL.get_knn_purity()
```

Example 17 (unknown):
```unknown
TRVAE_EVAL.get_latent_score()
```

Example 18 (unknown):
```unknown
TRVAE_EVAL.get_model_arch()
```

Example 19 (unknown):
```unknown
TRVAE_EVAL.get_nmi()
```

Example 20 (unknown):
```unknown
TRVAE_EVAL.latent_as_anndata()
```

Example 21 (unknown):
```unknown
TRVAE_EVAL.plot_history()
```

Example 22 (unknown):
```unknown
TRVAE_EVAL.plot_latent()
```

Example 23 (unknown):
```unknown
plot_abs_bfs()
```

Example 24 (unknown):
```unknown
sankey_diagram()
```

---

## API - scArches documentation

**URL:** http://127.0.0.1:9180/en/latest/api/index.html

**Contents:**
- API

The API reference contains detailed descriptions of the different end-user classes, functions, methods, etc.

This API reference only contains end-user documentation. If you are looking to hack away at scArches’ internals, you will find more detailed comments in the source code.

After reading the data (sca.data.read), you can you can instantiate one of the implemented models from sca.models module (currently we support trVAE, scVI, scANVI, and TotalVI) and train it on your dataset.

**Examples:**

Example 1 (python):
```python
import scarches as sca
```

Example 2 (unknown):
```unknown
sca.data.read
```

Example 3 (unknown):
```unknown
label_encoder()
```

Example 4 (unknown):
```unknown
remove_sparsity()
```

Example 5 (unknown):
```unknown
trVAEDataset
```

Example 6 (unknown):
```unknown
plot_abs_bfs()
```

Example 7 (unknown):
```unknown
sankey_diagram()
```

Example 8 (unknown):
```unknown
add_annotations()
```

Example 9 (unknown):
```unknown
weighted_knn_trainer()
```

Example 10 (unknown):
```unknown
weighted_knn_transfer()
```

Example 11 (unknown):
```unknown
download_model()
```

Example 12 (unknown):
```unknown
upload_model()
```

---

## Advanced tutorial for query to reference mapping using expiMap with de novo learned gene programs - scArches documentation

**URL:** http://127.0.0.1:9180/en/latest/expimap_surgery_pipeline_advanced.html

**Contents:**
- Advanced tutorial for query to reference mapping using expiMap with de novo learned gene programs
- Download reference and do preprocessing
- Example with constrained and unconstrained extension nodes
- Train the reference.
- Referece mapping while learning new varation from query data with extension nodes
- Analysis of the extension nodes for reference + query dataset

.X should contain raw counts.

Read the Reactome annotations, make a binary matrix where rows represent gene symbols and columns represent the terms, and add the annotations matrix to the reference dataset. The binary matrix of annotations is stored in adata.varm['I']. Note that only terms with minimum of 12 genes in the reference dataset are retained.

Remove all genes which are not present in the Reactome annotations.

For a better model performance it is necessary to select HVGs. We are doing this by applying the scanpy.pp function highly_variable_genes(). The n_top_genes is set to 2000 here. However, for more complicated datasets you might have to increase number of genes to capture more diversity in the data.

Filter out any annotations (terms) with less than 12 genes.

Filter out genes not present in any retained terms after selection of HVGs.

Put the count data back to adata.X.

Later, we will use a query dataset that contains IFN-beta stimulated and unstimulated PBMC cells.

Here, we remove some Interferon beta and B cell specific signals from the reference by dropping some related terms from the annotation matrix. The signals corresponding to these terms will be recovered later with the extension nodes added in the query at the surgery step.

Select the interferon beta annotations from the loaded Reactome pathway database for removal.

Select the annotations related to B cells for removal.

Store the ‘SIGNALING_BY_THE_B_CELL_RECEPT’ annotation separately.

Remove the selected annotations.

Remove B cells from the reference.

See https://docs.scarches.org/en/latest/training_tips.html for the recommendation on hyperparameter choice.

The Kang dataset contains control and IFN-beta stimulated cells. We use this as the query dataset.

Add 3 unconstrained (to capture de novo programs) and one constrained nodes, where the constrain represents the ‘SIGNALING_BY_THE_B_CELL_RECEPT’ term. Note that this term was dropped when the reference model was learned. Also use HSIC regularization for the unconstrained nodes to encourge independence of learned de novo gene programs.

Train with hypeparameters:

gamma_ext - L1 regularization coefficient for the new unconstrained nodes. Specifies the strength of sparcity enforcement for these nodes.

gamma_epoch_anneal - number of epochs for gamma_ext annealing.

alpha_l1 - L1 regularization coefficient for the soft mask of the new constrained node.

beta - HSIC regularization coefficient for the unconstrained nodes, enforces their independence from the old reference nodes and from each other if hsic_one_vs_all=True.

This adds extension nodes’ names to kang_pbmc.uns['terms'].

Do gene set enrichment test for condition in reference + query using Bayes Factors.

Do gene set enrichment test for cell types in reference + query control using Bayes Factors.

Plot the latent variables for query + reference corresponding to the constrained and unconstrained extension nodes.

Note that the signal associated with the program learned by unconstrained_2 was enriched in stimulated condition compared to control. Here, the cells are separated by their latent scores for unconstrained_2, which suggests that this node is indeed capturing the variation induced by IFN-beta stimulation.

Recall that unconstrained_1 was differentially enriched in CD14+ Monocytes. Therefore, this node is capturing the CD14+ Monocyte cell type variation.

Get genes from extension nodes sorted by their absolute weights in the decoder. Higher absolute value of the weight means that this gene is affected more by the gene program.

Note that unconstrained_2 was capturing the variation induced by IFN-beta stimulation. Here, the genes from the Interferon Induced Protein gene family have the largest absolute weights in the program captured by this unconstrained node, certifying that the learned program is indeed capturing variations in gene expression due to activity of the inteferon signalling, which was induced by IFN-beta stimulation.

**Examples:**

Example 1 (python):
```python
import warnings
warnings.simplefilter(action='ignore')
```

Example 2 (python):
```python
import scanpy as sc
import torch
import scarches as sca
import numpy as np
import gdown
```

Example 3 (unknown):
```unknown
Global seed set to 0
```

Example 4 (python):
```python
sc.set_figure_params(frameon=False)
sc.set_figure_params(dpi=200)
sc.set_figure_params(figsize=(4, 4))
torch.set_printoptions(precision=3, sci_mode=False, edgeitems=7)
```

Example 5 (unknown):
```unknown
url = 'https://drive.google.com/uc?id=1Rnm-XKEqPLdOq3lpa3ka2aV4bOXVCLP0'
output = 'pbmc_tutorial.h5ad'
gdown.download(url, output, quiet=False)
```

Example 6 (unknown):
```unknown
Downloading...
From: https://drive.google.com/uc?id=1Rnm-XKEqPLdOq3lpa3ka2aV4bOXVCLP0
To: C:\Users\sergei.rybakov\projects\notebooks\pbmc_tutorial.h5ad
100%|███████████████████████████████████████████████████████████████████████████████| 231M/231M [00:42<00:00, 5.39MB/s]
```

Example 7 (unknown):
```unknown
'pbmc_tutorial.h5ad'
```

Example 8 (python):
```python
adata = sc.read('pbmc_tutorial.h5ad')
```

Example 9 (python):
```python
adata.X = adata.layers["counts"].copy()
```

Example 10 (python):
```python
adata.varm['I']
```

Example 11 (unknown):
```unknown
url = 'https://drive.google.com/uc?id=1136LntaVr92G1MphGeMVcmpE0AqcqM6c'
output = 'reactome.gmt'
gdown.download(url, output, quiet=False)
```

Example 12 (python):
```python
sca.utils.add_annotations(adata, 'reactome.gmt', min_genes=12, clean=True)
```

Example 13 (python):
```python
adata._inplace_subset_var(adata.varm['I'].sum(1)>0)
```

Example 14 (unknown):
```unknown
highly_variable_genes()
```

Example 15 (unknown):
```unknown
n_top_genes
```

Example 16 (python):
```python
sc.pp.normalize_total(adata)
```

Example 17 (python):
```python
sc.pp.log1p(adata)
```

Example 18 (python):
```python
sc.pp.highly_variable_genes(
    adata,
    n_top_genes=2000,
    batch_key="batch",
    subset=True)
```

Example 19 (python):
```python
select_terms = adata.varm['I'].sum(0)>12
```

Example 20 (python):
```python
adata.uns['terms'] = np.array(adata.uns['terms'])[select_terms].tolist()
```

Example 21 (python):
```python
adata.varm['I'] = adata.varm['I'][:, select_terms]
```

Example 22 (python):
```python
adata._inplace_subset_var(adata.varm['I'].sum(1)>0)
```

Example 23 (python):
```python
adata.X = adata.layers["counts"].copy()
```

Example 24 (unknown):
```unknown
rm_terms = ['INTERFERON_SIGNALING', 'INTERFERON_ALPHA_BETA_SIGNALIN',
            'CYTOKINE_SIGNALING_IN_IMMUNE_S', 'ANTIVIRAL_MECHANISM_BY_IFN_STI']
```

Example 25 (unknown):
```unknown
rm_terms += ['SIGNALING_BY_THE_B_CELL_RECEPT', 'MHC_CLASS_II_ANTIGEN_PRESENTAT']
```

Example 26 (python):
```python
ix_f = []
for t in rm_terms:
    ix_f.append(adata.uns['terms'].index(t))
```

Example 27 (python):
```python
query_mask = adata.varm['I'][:, ix_f[4]][:, None].copy()
```

Example 28 (python):
```python
adata.varm['I'] = np.delete(adata.varm['I'], ix_f, axis=1)
```

Example 29 (python):
```python
adata.uns['terms'] = [term for term in adata.uns['terms'] if term not in rm_terms]
```

Example 30 (unknown):
```unknown
rm_b = ["B", "CD10+ B cells"]
```

Example 31 (python):
```python
adata = adata[~adata.obs['cell_type'].isin(rm_b)].copy()
```

Example 32 (python):
```python
intr_cvae = sca.models.EXPIMAP(
    adata=adata,
    condition_key='study',
    hidden_layer_sizes=[300, 300, 300],
    recon_loss='nb'
)
```

Example 33 (unknown):
```unknown
INITIALIZING NEW NETWORK..............
Encoder Architecture:
        Input Layer in, out and cond: 1972 300 4
        Hidden Layer 1 in/out: 300 300
        Hidden Layer 2 in/out: 300 300
        Mean/Var Layer in/out: 300 276
Decoder Architecture:
        Masked linear layer in, ext_m, ext, cond, out:  276 0 0 4 1972
        with hard mask.
Last Decoder layer: softmax
```

Example 34 (unknown):
```unknown
ALPHA = 0.7
```

Example 35 (unknown):
```unknown
early_stopping_kwargs = {
    "early_stopping_metric": "val_unweighted_loss",
    "threshold": 0,
    "patience": 50,
    "reduce_lr": True,
    "lr_patience": 13,
    "lr_factor": 0.1,
}
intr_cvae.train(
    n_epochs=400,
    alpha_epoch_anneal=100,
    alpha=ALPHA,
    alpha_kl=0.5,
    weight_decay=0.,
    early_stopping_kwargs=early_stopping_kwargs,
    use_early_stopping=True,
    seed=2020
)
```

Example 36 (unknown):
```unknown
Init the group lasso proximal operator for the main terms.
 |██████████████------| 72.2%  - val_loss: 935.2109799592 - val_recon_loss: 909.6967879586 - val_kl_loss: 51.0283828404208
ADJUSTED LR
 |███████████████-----| 76.8%  - val_loss: 934.3165150518 - val_recon_loss: 908.9699786642 - val_kl_loss: 50.6930810680
ADJUSTED LR
 |████████████████----| 80.2%  - val_loss: 934.5560806938 - val_recon_loss: 909.1601987092 - val_kl_loss: 50.7917618130
ADJUSTED LR
 |████████████████----| 83.5%  - val_loss: 934.7631597104 - val_recon_loss: 909.4011548913 - val_kl_loss: 50.7240132871
ADJUSTED LR
 |█████████████████---| 86.8%  - val_loss: 934.5707238239 - val_recon_loss: 909.2114868164 - val_kl_loss: 50.7184793224
ADJUSTED LR
 |█████████████████---| 89.5%  - val_loss: 934.3915139903 - val_recon_loss: 909.0323433254 - val_kl_loss: 50.7183265686
Stopping early: no improvement of more than 0 nats in 50 epochs
If the early stopping criterion is too strong, please instantiate it with different parameters in the train method.
Saving best state of network...
Best State was in Epoch 306
```

Example 37 (unknown):
```unknown
url = 'https://drive.google.com/uc?id=1t3oMuUfueUz_caLm5jmaEYjBxVNSsfxG'
output = 'kang_tutorial.h5ad'
gdown.download(url, output, quiet=False)
```

Example 38 (python):
```python
kang = sc.read('kang_tutorial.h5ad')[:, adata.var_names].copy()
```

Example 39 (unknown):
```unknown
kang.obs['study'] = 'Kang'
```

Example 40 (python):
```python
kang.uns['terms'] = adata.uns['terms']
```

Example 41 (unknown):
```unknown
q_intr_cvae = sca.models.EXPIMAP.load_query_data(kang, intr_cvae,
                                                 unfreeze_ext=True,
                                                 new_n_ext=3,
                                                 new_n_ext_m=1,
                                                 new_ext_mask=query_mask.T,
                                                 new_soft_ext_mask=True,
                                                 use_hsic=True,
                                                 hsic_one_vs_all=True
                                                )
```

Example 42 (unknown):
```unknown
INITIALIZING NEW NETWORK..............
Encoder Architecture:
        Input Layer in, out and cond: 1972 300 5
        Hidden Layer 1 in/out: 300 300
        Hidden Layer 2 in/out: 300 300
        Mean/Var Layer in/out: 300 276
        Expanded Mean/Var Layer in/out: 300 4
Decoder Architecture:
        Masked linear layer in, ext_m, ext, cond, out:  276 1 3 5 1972
        with hard mask.
Last Decoder layer: softmax
```

Example 43 (unknown):
```unknown
gamma_epoch_anneal
```

Example 44 (unknown):
```unknown
hsic_one_vs_all=True
```

Example 45 (unknown):
```unknown
q_intr_cvae.train(
    n_epochs=250,
    alpha_epoch_anneal=120,
    alpha_kl=0.22,
    weight_decay=0.,
    alpha_l1=0.96,
    gamma_ext=0.7,
    gamma_epoch_anneal=50,
    beta=3.,
    seed=2020,
    use_early_stopping=False
)
```

Example 46 (unknown):
```unknown
Init the L1 proximal operator for the unannotated extension.
Init the soft mask proximal operator for the annotated extension.
 |████████████████████| 100.0%  - val_hsic_loss: 0.2133808624 - val_loss: 517.5771179199 - val_recon_loss: 501.4962740811 - val_kl_loss: 70.1850114302
```

Example 47 (python):
```python
kang_pbmc = sc.AnnData.concatenate(adata, kang, batch_key='batch_join', uns_merge='same')
```

Example 48 (unknown):
```unknown
kang_pbmc.obs['condition_joint'] = kang_pbmc.obs.condition.astype(str)
kang_pbmc.obs['condition_joint'][kang_pbmc.obs['condition_joint'].astype(str)=='nan']='control'
```

Example 49 (unknown):
```unknown
kang_pbmc.uns['terms']
```

Example 50 (python):
```python
q_intr_cvae.update_terms(adata=kang_pbmc)
```

Example 51 (python):
```python
q_intr_cvae.latent_directions(adata=kang_pbmc)
```

Example 52 (python):
```python
q_intr_cvae.latent_enrich(groups='condition_joint', comparison='control', use_directions=True, adata=kang_pbmc)
```

Example 53 (unknown):
```unknown
fig = sca.plotting.plot_abs_bfs(kang_pbmc, yt_step=0.8, scale_y=2.5, fontsize=7)
```

Example 54 (python):
```python
kang_pbmc_control = kang_pbmc[kang_pbmc.obs['condition_joint']=='control'].copy()

q_intr_cvae.latent_enrich(groups='cell_type', use_directions=True, adata=kang_pbmc_control, n_sample=10000)
```

Example 55 (unknown):
```unknown
fig = sca.plotting.plot_abs_bfs(kang_pbmc_control, n_cols=3, scale_y=2.6, yt_step=0.6)
```

Example 56 (unknown):
```unknown
fig.set_size_inches(16, 34)
```

Example 57 (unknown):
```unknown
terms = kang_pbmc.uns['terms']
select_terms = ['constrained_0', 'unconstrained_0', 'unconstrained_1', 'unconstrained_2']
idx = [terms.index(term) for term in select_terms]
```

Example 58 (unknown):
```unknown
latents = (q_intr_cvae.get_latent(kang_pbmc.X, kang_pbmc.obs['study'], mean=False) * kang_pbmc.uns['directions'])[:, idx]
```

Example 59 (unknown):
```unknown
kang_pbmc.obs['constrained_0'] = latents[:, 0]

kang_pbmc.obs['unconstrained_0'] = latents[:, 1]
kang_pbmc.obs['unconstrained_1'] = latents[:, 2]
kang_pbmc.obs['unconstrained_2'] = latents[:, 3]
```

Example 60 (python):
```python
sc.pl.scatter(kang_pbmc, x='unconstrained_2', y='constrained_0', color='condition_joint', size=10)
```

Example 61 (unknown):
```unknown
unconstrained_2
```

Example 62 (unknown):
```unknown
unconstrained_2
```

Example 63 (python):
```python
sc.pl.scatter(kang_pbmc, x='unconstrained_2', y='constrained_0', color='cell_type', size=10)
```

Example 64 (python):
```python
sc.pl.scatter(kang_pbmc, x='unconstrained_1', y='unconstrained_0', color='cell_type', size=10)
```

Example 65 (unknown):
```unknown
unconstrained_1
```

Example 66 (unknown):
```unknown
q_intr_cvae.term_genes('constrained_0', terms=kang_pbmc.uns['terms'])
```

Example 67 (unknown):
```unknown
q_intr_cvae.term_genes('unconstrained_1', terms=kang_pbmc.uns['terms'])
```

Example 68 (unknown):
```unknown
q_intr_cvae.term_genes('unconstrained_2', terms=kang_pbmc.uns['terms'])
```

Example 69 (unknown):
```unknown
unconstrained_2
```

---

## Spatial reconstruction of the mouse embryo with SageNet - scArches documentation

**URL:** http://127.0.0.1:9180/en/latest/SageNet_mouse_embryo.html

**Contents:**
- Spatial reconstruction of the mouse embryo with SageNet
- Setup
  - Install scArches
  - Install pytorch geometric
  - Other auxilary packages
  - Import libraries
  - Cell type colours
    - Setting the torch device
- Training and Mapping
- The spatial and scRNAseq mouse gastrulation datasets
  - Training with one reference dataset
    - Building the gene interaction network
    - Spatial partitioning of the reference
    - Training the model
    - Saving the trained model
  - Mapping the query dataset
  - Training with multiple spatial references
    - Mapping the query dataset

In this notebook present spatial reconstruction of the mouse embryo with SageNet. We use the seqFISH dataset collected by Lohoff et al. (2022) as the spatial reference. This Spatial Mouse Atlas dataset contains barcoded gene expression measurements for 351 genes in three distinct mouse embryo sagittal sections. We also use combination of a subset of this dataset and the dissociated scRNAseq mouse gastrulation atlas by Pijuan-Sala et al. (2019) as the query dataset. For both spatial and scRNAseq datasets, we focus on embryonic day (E)8.5.

We specifically show how to aggeregate multiple spatial references and build an ensemble SageNet model.

SageNet is now implemented as a model in the scarches code base. In order to get the latest developments, we recommend installing the package via github.

SageNet employs pytroch geometric (PyG) to implement graph neural networks (GGNs). We install pytorch geometric and its requirments as instructed here.

PyG’s requirements to be installed depend on the torch and cuda versions:

We use squidpy for preprocessing spatial data and captum for interpreting our GGNs.

We set the torch device to cuda if it’s available.

Lohoff et al. (2022) carried out a SeqFISH experiment on sagittal sections from three mouse embryos corresponding to embryonic day (E)8.5–8.75 to quantify spatial gene expression at single cell resolution of a pre-selected set of 387 genes. For each embryo section, they captured two 2D planes, 12um apart, yielding a total of 6 spatially-resolved sections. The authors performed cell segmentation, quantified gene expression log-counts, and assigned cell type identities to each cell using a large-scale single cell study of mouse gastrulation Pijuan-Sala et al. (2019) as a reference. These two datasets are known as spatial and single-cell mouse gastrulation atlases (MGAs).

This dataset is ideal for evaluating SageNet’s performance, since we have access to ground truth spatial coordinates for individual cells over multiple biological replicates, and the tissue structure observed across mouse embryos are varied and complex. We downloaded the gene expression matrix and cell type and spatial location metadata from https://content.cruk.cam.ac.uk/jmlab/SpatialMouseAtlas2020/.

Prior to analysis, we removed cells that were annotated as “Low quality” by the authors. And we subseted the scRNAseq so that all datasets have the same set of genes. No further preprocessing was performed on the datasets. The filtered seqFISH datsets could be simply downloaded and loaded in the environment by calling scarches.dataset.MGA_data.seqFISH{embryo}_{layer}(). The single-cell RNAseq dataset is loaded using scarches.dataset.MGA_data.scRNAseq()

As the basic functionality of SageNet, we start with training the model on only one spatial reference. We take embryo 1 layer 1 (seqFISH1_1) as the spatial reference.

SageNet model uses a gene interaction network (across all cells in the reference dataset) to train the GNN (see the preprint). We use a utility fuction impelemented in the package for the graphical LASSO (GLASSO) algorithm to estimate the gene interaction network. The funciton takes a grid of regulatrization parameters and does a cross validation to find the optimal parameter (see this).

The adjacency matrix of the built graph has added under the name adj to the varm section of the annData object.

The spatial reference should be partinitioned into distinct spatial neighborhood. The GGNs learn to map the dissociated query cells to those partitions. We use the `leiden <https://www.nature.com/articles/s41598-019-41695-z>`__ algorithm on the spatial graph created by `squidpy <https://squidpy.readthedocs.io/en/stable/>`__. We run the partitioning at 3 different resolutions. The idea is to capture different granularities in space.

The partitionings have been added to the obs section.

We now define the SageNet model object:

Finally, we train the model by feeding in the reference mode and specefying the obs columns containing the partitionings. The model trains one GNN for each partitioning:

By setting importance = True we compute the feature (here gene) importances in training. A column specifying these importance values has been added to the adata. This gives us the Spatially Informative Genes (SIGs):

We can save the trained model as a folder:

The function above saves the torch neural networks as well as the adjancency matrices used for training the model in a folder. For reusing the model, one can load the model into another SageNet object:

We can now feed the query dataset into the trained model to get the predicted cell-cell spatial distances. Here, we take the single-cell dataset as the query dataset:

The predicted cell-cell distance matrix has been added to the query adata in the obsm section under the name dist_map. We use t-SNE to map the cells based on this distance matrix in 2 dimensions:

Now we can look at the expression of the SIGs (introduced above) at the 2D reconstructed space:

The model outputs a confidence score for each of the cells per GGN (namely per partitioning). This score is between 0 and 1, and higher the less confident is the model to map the corresponding query cell. Therfore, one can summarize the confidence scores from all trained GGNs:

Now we add 2 other spatial references to the model. These are seqFISH datasets from other mouse embryos, seqFISH2_1 and seqFISH3_1. We first perform the same preprocessing steps:

The sagenet model object now includes more models added corresponding to the new spatial references.

Now let’s map the query dataset once again with the new ensemble model:

**Examples:**

Example 1 (unknown):
```unknown
!git clone https://github.com/theislab/scarches
%cd scarches
!pip install .
```

Example 2 (python):
```python
import torch; print(torch.__version__)
import torch; print(torch.version.cuda)
```

Example 3 (unknown):
```unknown
1.12.1+cu113
11.3
```

Example 4 (unknown):
```unknown
!pip install -q torch-scatter -f https://data.pyg.org/whl/torch-1.12.1+cu113.html
!pip install -q torch-sparse -f https://data.pyg.org/whl/torch-1.12.1+cu113.html
!pip install -q git+https://github.com/pyg-team/pytorch_geometric.git
```

Example 5 (unknown):
```unknown
|████████████████████████████████| 7.9 MB 1.1 MB/s
     |████████████████████████████████| 3.5 MB 1.2 MB/s
  Building wheel for torch-geometric (setup.py) ... done
```

Example 6 (unknown):
```unknown
!pip install squidpy
!pip install captum
!pip install patchworklib
```

Example 7 (python):
```python
import scarches as sca
import scanpy as sc # for plotting
import anndata as ad # for handling the spatial and single-cell datasets
import random # for setting a random seed
import numpy as np
import copy
import squidpy as sq
import pandas as pd
from scarches.models.sagenet.utils import glasso
from matplotlib import *
import patchworklib as pw
import functools
```

Example 8 (python):
```python
celltype_colours = {
  "Epiblast" : "#635547",
  "Primitive Streak" : "#DABE99",
  "Caudal epiblast" : "#9e6762",
  "PGC" : "#FACB12",
  "Anterior Primitive Streak" : "#c19f70",
  "Notochord" : "#0F4A9C",
  "Def. endoderm" : "#F397C0",
  "Definitive endoderm" : "#F397C0",
  "Gut" : "#EF5A9D",
  "Gut tube" : "#EF5A9D",
  "Nascent mesoderm" : "#C594BF",
  "Mixed mesoderm" : "#DFCDE4",
  "Intermediate mesoderm" : "#139992",
  "Caudal Mesoderm" : "#3F84AA",
  "Paraxial mesoderm" : "#8DB5CE",
  "Somitic mesoderm" : "#005579",
  "Pharyngeal mesoderm" : "#C9EBFB",
  "Splanchnic mesoderm" : "#C9EBFB",
  "Cardiomyocytes" : "#B51D8D",
  "Allantois" : "#532C8A",
  "ExE mesoderm" : "#8870ad",
  "Lateral plate mesoderm" : "#8870ad",
  "Mesenchyme" : "#cc7818",
  "Mixed mesenchymal mesoderm" : "#cc7818",
  "Haematoendothelial progenitors" : "#FBBE92",
  "Endothelium" : "#ff891c",
  "Blood progenitors 1" : "#f9decf",
  "Blood progenitors 2" : "#c9a997",
  "Erythroid1" : "#C72228",
  "Erythroid2" : "#f79083",
  "Erythroid3" : "#EF4E22",
  "Erythroid" : "#f79083",
  "Blood progenitors" : "#f9decf",
  "NMP" : "#8EC792",
  "Rostral neurectoderm" : "#65A83E",
  "Caudal neurectoderm" : "#354E23",
  "Neural crest" : "#C3C388",
  "Forebrain/Midbrain/Hindbrain" : "#647a4f",
  "Spinal cord" : "#CDE088",
  "Surface ectoderm" : "#f7f79e",
  "Visceral endoderm" : "#F6BFCB",
  "ExE endoderm" : "#7F6874",
  "ExE ectoderm" : "#989898",
  "Parietal endoderm" : "#1A1A1A",
  "Unknown" : "#FFFFFF",
  "Low quality" : "#e6e6e6",
  # somitic and paraxial types
  # colour from T chimera paper Guibentif et al Developmental Cell 2021
  "Cranial mesoderm" : "#77441B",
  "Anterior somitic tissues" : "#F90026",
  "Sclerotome" : "#A10037",
  "Dermomyotome" : "#DA5921",
  "Posterior somitic tissues" : "#E1C239",
  "Presomitic mesoderm" : "#9DD84A"
}
```

Example 9 (python):
```python
import torch
if torch.cuda.is_available():
  dev = "cuda:0"
else:
  dev = "cpu"
device = torch.device(dev)
print(device)
```

Example 10 (unknown):
```unknown
scarches.dataset.MGA_data.seqFISH{embryo}_{layer}()
```

Example 11 (unknown):
```unknown
scarches.dataset.MGA_data.scRNAseq()
```

Example 12 (python):
```python
adata_seqFISH1_1 = sca.dataset.MGA_data.seqFISH1_1()
adata_seqFISH2_1 = sca.dataset.MGA_data.seqFISH2_1()
adata_seqFISH3_1 = sca.dataset.MGA_data.seqFISH3_1()
adata_seqFISH1_2 = sca.dataset.MGA_data.seqFISH1_2()
adata_seqFISH2_2 = sca.dataset.MGA_data.seqFISH2_2()
adata_seqFISH3_2 = sca.dataset.MGA_data.seqFISH3_2()
adata_scRNAseq   = sca.dataset.scRNAseq()
```

Example 13 (python):
```python
sc.set_figure_params(figsize=(2, 2), fontsize=6)
import functools
adata_seqFISH_list = [adata_seqFISH1_1, adata_seqFISH2_1, adata_seqFISH3_1, adata_seqFISH1_2, adata_seqFISH2_2, adata_seqFISH3_2]
axs = []
for i in range(len(adata_seqFISH_list)):
  axs.append(pw.Brick())
  adata = adata_seqFISH_list[i]
  adata.obsm['spatial'] = np.array(adata.obs[['x','y']])
  sq.gr.spatial_neighbors(adata, coord_type="generic")
  # with rc_context({'figure.figsize': (2, 2)}):
  if(i != len(adata_seqFISH_list)-1):
    sc.pl.spatial(adata, color='cell_type', palette=celltype_colours, frameon=False, spot_size=.1, title=pd.unique(adata.obs['embryo']), ax=axs[i], legend_loc=None)
  else:
    sc.pl.spatial(adata, color='cell_type', palette=celltype_colours, frameon=False, spot_size=.1, title=pd.unique(adata.obs['embryo']), ax=axs[i])
plots = functools.reduce(lambda a, b: a+b, axs)
plots.savefig()
#
```

Example 14 (python):
```python
glasso(adata_seqFISH1_1, [0.25, 0.5])
adata_seqFISH1_1
```

Example 15 (unknown):
```unknown
AnnData object with n_obs × n_vars = 10045 × 350
    obs: 'cell_id', 'embryo', 'x', 'y', 'UMAP1', 'UMAP2', 'cell_type', 'res_0.05', 'class_'
    uns: 'X_name', 'celltype_colours', 'spatial_neighbors', 'cell_type_colors'
    obsm: 'spatial'
    varm: 'adj'
    obsp: 'spatial_connectivities', 'spatial_distances'
```

Example 16 (python):
```python
sc.set_figure_params(figsize=(4, 4), fontsize=15)
sc.tl.leiden(adata_seqFISH1_1, resolution=.05, random_state=0, key_added='leiden_0.05', adjacency=adata_seqFISH1_1.obsp["spatial_connectivities"])
sc.tl.leiden(adata_seqFISH1_1, resolution=.1, random_state=0, key_added='leiden_0.1', adjacency=adata_seqFISH1_1.obsp["spatial_connectivities"])
sc.tl.leiden(adata_seqFISH1_1, resolution=.5, random_state=0, key_added='leiden_0.5', adjacency=adata_seqFISH1_1.obsp["spatial_connectivities"])
# with rc_context({'figure.figsize': (2, 2)}):
sc.pl.spatial(adata_seqFISH1_1, color=['leiden_0.05', 'leiden_0.1', 'leiden_0.5'], frameon=False, ncols=3, spot_size=.1, title=['leiden_0.05', 'leiden_0.1', 'leiden_0.5'],  legend_loc=None)
adata_seqFISH1_1
```

Example 17 (unknown):
```unknown
AnnData object with n_obs × n_vars = 10045 × 350
    obs: 'cell_id', 'embryo', 'x', 'y', 'UMAP1', 'UMAP2', 'cell_type', 'res_0.05', 'class_', 'leiden_0.05', 'leiden_0.1', 'leiden_0.5'
    uns: 'X_name', 'celltype_colours', 'spatial_neighbors', 'cell_type_colors', 'leiden', 'leiden_0.05_colors', 'leiden_0.1_colors', 'leiden_0.5_colors'
    obsm: 'spatial'
    varm: 'adj'
    obsp: 'spatial_connectivities', 'spatial_distances'
```

Example 18 (unknown):
```unknown
sg_obj = sca.models.sagenet(device=device)
```

Example 19 (python):
```python
import torch_geometric.data as geo_dt
```

Example 20 (python):
```python
sg_obj.train(adata_seqFISH1_1, comm_columns=['leiden_0.05', 'leiden_0.1', 'leiden_0.5'], tag='seqFISH_ref1', epochs=15, verbose = False, importance=True)
```

Example 21 (unknown):
```unknown
importance = True
```

Example 22 (python):
```python
sc.set_figure_params(figsize=(3, 3), fontsize=10)
from copy import copy
ind   = np.where(adata_seqFISH1_1.var['seqFISH_ref1_importance'] == 0)[0]
SIGs1 = list(adata_seqFISH1_1.var_names[ind])
adata_r = copy(adata_seqFISH1_1)
sc.pp.subsample(adata_r, fraction=0.25)
# with rc_context({'figure.figsize': (2, 2)}):
sc.pl.spatial(adata_r, color=SIGs1, ncols=4, spot_size=0.2, legend_loc=None, frameon=False)
```

Example 23 (unknown):
```unknown
!mkdir models
!mkdir models/seqFISH_ref
sg_obj.save_as_folder('models/seqFISH_ref')
%ls -l models/seqFISH_ref
```

Example 24 (unknown):
```unknown
mkdir: cannot create directory ‘models’: File exists
mkdir: cannot create directory ‘models/seqFISH_ref’: File exists
total 2228
-rw-r--r-- 1 root root 533016 Sep 14 14:22 seqFISH_ref1_leiden_0.05.h5ad
-rw-r--r-- 1 root root 108999 Sep 14 14:22 seqFISH_ref1_leiden_0.05.pickle
-rw-r--r-- 1 root root 533016 Sep 14 14:22 seqFISH_ref1_leiden_0.1.h5ad
-rw-r--r-- 1 root root 176199 Sep 14 14:22 seqFISH_ref1_leiden_0.1.pickle
-rw-r--r-- 1 root root 533016 Sep 14 14:22 seqFISH_ref1_leiden_0.5.h5ad
-rw-r--r-- 1 root root 377927 Sep 14 14:22 seqFISH_ref1_leiden_0.5.pickle
```

Example 25 (unknown):
```unknown
sg_obj_load = sca.models.sagenet(device=device)
sg_obj_load.load_from_folder('models/seqFISH_ref')
```

Example 26 (python):
```python
sg_obj_load.load_query_data(adata_scRNAseq)
```

Example 27 (python):
```python
adata_scRNAseq
```

Example 28 (unknown):
```unknown
AnnData object with n_obs × n_vars = 16909 × 350
    obs: 'cell_id', 'barcode', 'sample', 'pool', 'stage', 'sequencing.batch', 'theiler', 'doub.density', 'doublet', 'cluster', 'cluster.sub', 'cluster.stage', 'cluster.theiler', 'stripped', 'celltype', 'colour', 'sizeFactor', 'cell_type', 'class_', 'pred_seqFISH_ref1_leiden_0.5', 'ent_seqFISH_ref1_leiden_0.5', 'pred_seqFISH_ref1_leiden_0.1', 'ent_seqFISH_ref1_leiden_0.1', 'pred_seqFISH_ref1_leiden_0.05', 'ent_seqFISH_ref1_leiden_0.05'
    uns: 'X_name', 'cell_types', 'celltype_colours'
    obsm: 'dist_map'
```

Example 29 (python):
```python
dist_adata = ad.AnnData(adata_scRNAseq.obsm['dist_map'], obs = adata_scRNAseq.obs)
knn_indices, knn_dists, forest = sc.neighbors.compute_neighbors_umap(dist_adata.X, n_neighbors=50, metric='precomputed')
dist_adata.obsp['distances'], dist_adata.obsp['connectivities'] = sc.neighbors._compute_connectivities_umap(
    knn_indices,
    knn_dists,
    dist_adata.shape[0],
    50 # change to neighbors you plan to use
)
sc.pp.neighbors(dist_adata, metric='precomputed', use_rep='X')
sc.tl.tsne(dist_adata)
```

Example 30 (python):
```python
WARNING: You’re trying to run this on 16909 dimensions of `.X`, if you really want this, set `use_rep='X'`.
         Falling back to preprocessing with `sc.pp.pca` and default params.
```

Example 31 (python):
```python
sc.set_figure_params(figsize=(5, 5), fontsize=15)
sc.pl.tsne(dist_adata, color=['cell_type'], palette=celltype_colours, frameon=False)
```

Example 32 (python):
```python
cluster_counts = adata_scRNAseq.obs['cell_type'].value_counts()
adata_scRNAseq = adata_scRNAseq[adata_scRNAseq.obs['cell_type'].isin( cluster_counts[cluster_counts>50].index)]
dist_adata = dist_adata[dist_adata.obs['cell_type'].isin( cluster_counts[cluster_counts>50].index)]
```

Example 33 (python):
```python
adata_scRNAseq.obsm['tsne'] = dist_adata.obsm['X_tsne']
sc.set_figure_params(figsize=(3, 3), fontsize=15)
sc.pl.tsne(adata_scRNAseq, color=SIGs1, ncols=5, legend_loc=None, frameon=False)
```

Example 34 (python):
```python
sc.set_figure_params(figsize=(5, 5), fontsize=15)
sc.pl.dotplot(adata_scRNAseq, SIGs1, groupby='cell_type', dendrogram=True)
```

Example 35 (python):
```python
WARNING: dendrogram data not found (using key=dendrogram_cell_type). Running `sc.tl.dendrogram` with default parameters. For fine tuning it is recommended to run `sc.tl.dendrogram` independently.
WARNING: You’re trying to run this on 350 dimensions of `.X`, if you really want this, set `use_rep='X'`.
         Falling back to preprocessing with `sc.pp.pca` and default params.
```

Example 36 (python):
```python
sc.set_figure_params(figsize=(8, 4), fontsize=10)
adata_scRNAseq.obs['confidence_score'] = (3 - (adata_scRNAseq.obs['ent_seqFISH_ref1_leiden_0.05'] + adata_scRNAseq.obs['ent_seqFISH_ref1_leiden_0.1'] + adata_scRNAseq.obs['ent_seqFISH_ref1_leiden_0.5']))/3
# with rc_context({'figure.figsize': (4, 2)}):
sc.pl.violin(adata_scRNAseq, ['confidence_score'], groupby='cell_type', palette=celltype_colours, stripplot=False, inner='box', rotation=90)
```

Example 37 (python):
```python
glasso(adata_seqFISH2_1, [0.25, 0.5])
sc.tl.leiden(adata_seqFISH2_1, resolution=.05, random_state=0, key_added='leiden_0.05', adjacency=adata_seqFISH2_1.obsp["spatial_connectivities"])
sc.tl.leiden(adata_seqFISH2_1, resolution=.1, random_state=0, key_added='leiden_0.1', adjacency=adata_seqFISH2_1.obsp["spatial_connectivities"])
sc.tl.leiden(adata_seqFISH2_1, resolution=.5, random_state=0, key_added='leiden_0.5', adjacency=adata_seqFISH2_1.obsp["spatial_connectivities"])

glasso(adata_seqFISH3_1, [0.25, 0.5])
sc.tl.leiden(adata_seqFISH3_1, resolution=.05, random_state=0, key_added='leiden_0.05', adjacency=adata_seqFISH3_1.obsp["spatial_connectivities"])
sc.tl.leiden(adata_seqFISH3_1, resolution=.1, random_state=0, key_added='leiden_0.1', adjacency=adata_seqFISH3_1.obsp["spatial_connectivities"])
sc.tl.leiden(adata_seqFISH3_1, resolution=.5, random_state=0, key_added='leiden_0.5', adjacency=adata_seqFISH3_1.obsp["spatial_connectivities"])
sc.set_figure_params(figsize=(4, 4), fontsize=15)
sc.pl.spatial(adata_seqFISH2_1, color=['leiden_0.05', 'leiden_0.1', 'leiden_0.5'], frameon=False, ncols=3, spot_size=.1, title=['leiden_0.05', 'leiden_0.1', 'leiden_0.5'],  legend_loc=None)
sc.pl.spatial(adata_seqFISH3_1, color=['leiden_0.05', 'leiden_0.1', 'leiden_0.5'], frameon=False, ncols=3, spot_size=.1, title=['leiden_0.05', 'leiden_0.1', 'leiden_0.5'],  legend_loc=None)
```

Example 38 (unknown):
```unknown
# !mkdir models
# !mkdir models/seqFISH_ref
sg_obj.save_as_folder('models/seqFISH_ref')
%ls -l models/seqFISH_ref
```

Example 39 (unknown):
```unknown
total 2228
-rw-r--r-- 1 root root 533016 Sep 14 14:28 seqFISH_ref1_leiden_0.05.h5ad
-rw-r--r-- 1 root root 108999 Sep 14 14:28 seqFISH_ref1_leiden_0.05.pickle
-rw-r--r-- 1 root root 533016 Sep 14 14:28 seqFISH_ref1_leiden_0.1.h5ad
-rw-r--r-- 1 root root 176199 Sep 14 14:28 seqFISH_ref1_leiden_0.1.pickle
-rw-r--r-- 1 root root 533016 Sep 14 14:28 seqFISH_ref1_leiden_0.5.h5ad
-rw-r--r-- 1 root root 377927 Sep 14 14:28 seqFISH_ref1_leiden_0.5.pickle
```

Example 40 (python):
```python
sc.set_figure_params(figsize=(5, 5), fontsize=15)
sg_obj_load.load_query_data(adata_scRNAseq)

dist_adata = ad.AnnData(adata_scRNAseq.obsm['dist_map'], obs = adata_scRNAseq.obs)
knn_indices, knn_dists, forest = sc.neighbors.compute_neighbors_umap(dist_adata.X, n_neighbors=50, metric='precomputed')
dist_adata.obsp['distances'], dist_adata.obsp['connectivities'] = sc.neighbors._compute_connectivities_umap(
    knn_indices,
    knn_dists,
    dist_adata.shape[0],
    50 # change to neighbors you plan to use
)
sc.pp.neighbors(dist_adata, metric='precomputed', use_rep='X')
sc.tl.tsne(dist_adata)

sc.pl.tsne(dist_adata, color=['cell_type'], palette=celltype_colours, frameon=False)
```

Example 41 (python):
```python
WARNING: You’re trying to run this on 16861 dimensions of `.X`, if you really want this, set `use_rep='X'`.
         Falling back to preprocessing with `sc.pp.pca` and default params.
```

---

## treeArches: learning and updating a cell-type hierarchy (basic tutorial) - scArches documentation

**URL:** http://127.0.0.1:9180/en/latest/treeArches_pbmc.html

**Contents:**
- treeArches: learning and updating a cell-type hierarchy (basic tutorial)
- Download raw Dataset
- Create scVI model and train it on reference dataset
- Construct hierarchy for the reference using scHPL
- Use pretrained reference model and apply surgery with a new query dataset to get a bigger reference atlas
- Updating the hierarchy using scHPL
- Predicting cell-type labels using scHPL

In this tutorial, we explain the different functionalities of treeArches. We show how to:

Step 1: Integrate reference datasets using scVI

Step 2: Match the cell-types in the reference datasets to learn the cell-type hierarchy of the reference datasets using scHPL

Step 3: Apply architural surgery to extend the reference dataset using scArches

Step 4a: Update the learned hierarchy with the cell-types from the query dataset using scHPL (useful when the query dataset is labeled)

Step 4b: Predict the labels of the cells in the query dataset using scHPL (useful when the query dataset is unlabeled)

We now split the data into reference and query dataset to simulate the building process. Here we use the ‘10X’ batch as query data.

For a better model performance it is necessary to select HVGs. We are doing this by applying the function scanpy.pp.highly_variable_genes(). The parameter n_top_genes is set to 2000 here. However, for more complicated datasets you might have to increase number of genes to capture more diversity in the data.

For consistency we set adata.X to be raw counts. In other datasets that may be already the case

Remember: The adata object has to have count data in adata.X for scVI/scANVI if not further specified.

The scVI model uses the zero-inflated negative binomial (ZINB) loss by default. Insert gene_likelihood='nb' to change the reconstruction loss to negative binomial (NB) loss.

The resulting latent representation of the data can then be visualized with UMAP

The colorblind color map only contains 10 different colors. To visualize the different cell-types, we rename some cells to a lower resolution.

We can also visualize the cell-types per dataset.

After pretraining the model can be saved for later use or also be uploaded for other researchers with via Zenodo. For the second option please also have a look at the Zenodo notebook.

First, we concatenate all cell type labels with the study labels. This way, we ensure that the cell types of the different studies are seen as unique.

Warning: Always ensure that the cell type labels of each dataset are unique!

Now, we are ready to learn the cell-type hierarchy. In this example we use the classifier='knn', this can be changed to either a linear SVM ('svm') or a one-class SVM ('svm_occ'). We recommend to use the kNN classifier when the dimensionality is low since the cell-types are not linearly separable anymore.

The option dynamic_neighbors=True implies that the number of neighbors changes depending on the number of cells in the dataset. If a cell-type is small, the number of neighbors used will also be lower. The number of neighbors can also be set manually using n_neighbors.

During each step of scHPL, a classifier is trained on the datasets we want to match and the labels are cross-predicted. If you’re interested in the confusion matrices used for the matching, set print_conf=True. The confusion matrices are also saved to .csv files then.

For more details about other parameters, take a look at the scHPL GitHub

Since the model requires the datasets to have the same genes we also filter the query dataset to have the same genes as the reference dataset.

We then can apply the model surgery with the new query dataset:

And again we can save or upload the retrained model for later use or additional extensions.

Get latent representation of reference + query dataset and compute UMAP

If the cells in the query dataset are labeled, we can update the hierarchy using scHPL. If the cells are unlabeled, we can predict their label (see section below).

Again, we first have to ensure that the labels of the cell-types are unique

Now, we are ready to update the cell-type hierarchy. It is important to use the same classifier settings here as used before. Furthermore, it is important to indicate which batches are already in the tree (batch_added) and which you want to add to the tree (batch_order).

If the cells in the query dataset are unlabeled or if you’re interested in comparing the transferred labels to your own annotations without updating the hierarchy, you can predict the labels with scHPL.

Using the evaluate.heatmap() function, the predictions can be compared to other annotations

**Examples:**

Example 1 (python):
```python
import os
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)
warnings.simplefilter(action='ignore', category=UserWarning)
```

Example 2 (python):
```python
import scanpy as sc
import torch
import scarches as sca
from scarches.dataset.trvae.data_handling import remove_sparsity
import matplotlib.pyplot as plt
import numpy as np
import gdown
import copy as cp
import seaborn as sns
```

Example 3 (unknown):
```unknown
WARNING:root:In order to use the mouse gastrulation seqFISH datsets, please install squidpy (see https://github.com/scverse/squidpy).
WARNING:root:In order to use sagenet models, please install pytorch geometric (see https://pytorch-geometric.readthedocs.io) and
 captum (see https://github.com/pytorch/captum).
WARNING:root:mvTCR is not installed. To use mvTCR models, please install it first using "pip install mvtcr"
WARNING:root:multigrate is not installed. To use multigrate models, please install it first using "pip install multigrate".
```

Example 4 (python):
```python
sc.settings.set_figure_params(dpi=1000, frameon=False)
sc.set_figure_params(dpi=1000)
sc.set_figure_params(figsize=(7,7))
torch.set_printoptions(precision=3, sci_mode=False, edgeitems=7)

import matplotlib
matplotlib.rcParams['pdf.fonttype'] = 42
```

Example 5 (unknown):
```unknown
url = 'https://drive.google.com/uc?id=1LaYOadbotGC6gXAlo-aKfHz-spoFnawk'
output = 'pbmc.h5ad'
gdown.download(url, output, quiet=False)
```

Example 6 (unknown):
```unknown
Downloading...
From: https://drive.google.com/uc?id=1LaYOadbotGC6gXAlo-aKfHz-spoFnawk
To: /Users/chelseaalexandra.bright/theislab/scarches/notebooks/pbmc.h5ad
100%|██████████| 2.06G/2.06G [00:41<00:00, 49.6MB/s]
```

Example 7 (unknown):
```unknown
'pbmc.h5ad'
```

Example 8 (python):
```python
adata = sc.read('pbmc.h5ad')
```

Example 9 (python):
```python
adata.X = adata.layers["counts"].copy()
```

Example 10 (python):
```python
adata = adata[adata.obs.study != "Villani"]
```

Example 11 (python):
```python
target_conditions = ["10X"]
source_adata = adata[~adata.obs.study.isin(target_conditions)].copy()
target_adata = adata[adata.obs.study.isin(target_conditions)].copy()
print(source_adata)
print(target_adata)
```

Example 12 (unknown):
```unknown
AnnData object with n_obs × n_vars = 21757 × 12303
    obs: 'batch', 'chemistry', 'data_type', 'dpt_pseudotime', 'final_annotation', 'mt_frac', 'n_counts', 'n_genes', 'sample_ID', 'size_factors', 'species', 'study', 'tissue'
    layers: 'counts'
AnnData object with n_obs × n_vars = 10727 × 12303
    obs: 'batch', 'chemistry', 'data_type', 'dpt_pseudotime', 'final_annotation', 'mt_frac', 'n_counts', 'n_genes', 'sample_ID', 'size_factors', 'species', 'study', 'tissue'
    layers: 'counts'
```

Example 13 (unknown):
```unknown
scanpy.pp.highly_variable_genes()
```

Example 14 (unknown):
```unknown
n_top_genes
```

Example 15 (python):
```python
source_adata.raw = source_adata
```

Example 16 (python):
```python
source_adata
```

Example 17 (unknown):
```unknown
AnnData object with n_obs × n_vars = 21757 × 12303
    obs: 'batch', 'chemistry', 'data_type', 'dpt_pseudotime', 'final_annotation', 'mt_frac', 'n_counts', 'n_genes', 'sample_ID', 'size_factors', 'species', 'study', 'tissue'
    layers: 'counts'
```

Example 18 (python):
```python
sc.pp.normalize_total(source_adata)
```

Example 19 (python):
```python
sc.pp.log1p(source_adata)
```

Example 20 (python):
```python
sc.pp.highly_variable_genes(
    source_adata,
    n_top_genes=2000,
    batch_key="study",
    subset=True)
```

Example 21 (python):
```python
source_adata.X = source_adata.raw[:, source_adata.var_names].X
```

Example 22 (python):
```python
sca.models.SCVI.setup_anndata(source_adata, batch_key="batch")
```

Example 23 (unknown):
```unknown
gene_likelihood='nb'
```

Example 24 (python):
```python
vae = sca.models.SCVI(
    source_adata,
    n_layers=2,
    encode_covariates=True,
    deeply_inject_covariates=True,
    use_layer_norm="both",
    use_batch_norm="none",
)
```

Example 25 (unknown):
```unknown
vae.train(max_epochs=80)
```

Example 26 (unknown):
```unknown
GPU available: True, used: True
TPU available: False, using: 0 TPU cores
IPU available: False, using: 0 IPUs
LOCAL_RANK: 0 - CUDA_VISIBLE_DEVICES: [0]
```

Example 27 (unknown):
```unknown
Epoch 80/80: 100%|██████████████████| 80/80 [01:34<00:00,  1.18s/it, loss=565, v_num=1]
```

Example 28 (python):
```python
reference_latent = sc.AnnData(vae.get_latent_representation())
reference_latent.obs["cell_type"] = source_adata.obs["final_annotation"].tolist()
reference_latent.obs["batch"] = source_adata.obs["batch"].tolist()
reference_latent.obs["study"] = source_adata.obs["study"].tolist()
```

Example 29 (python):
```python
sc.pp.neighbors(reference_latent, n_neighbors=8)
sc.tl.leiden(reference_latent)
sc.tl.umap(reference_latent)
```

Example 30 (unknown):
```unknown
reference_latent.obs['study'] = reference_latent.obs['study'].astype('category')

# Reorder categories, so smallest dataset is plotted on top
reference_latent.obs['study'].cat.reorder_categories(['Oetjen', 'Sun', 'Freytag'], inplace=True)
```

Example 31 (python):
```python
sc.pl.umap(reference_latent,
           color=['study'],
           frameon=False,
           wspace=0.6, s=25,
           palette=sns.color_palette('colorblind', as_cmap=True)[:3]
           )
```

Example 32 (unknown):
```unknown
reference_latent.obs['ct_low'] = 0

idx = ((reference_latent.obs.cell_type == 'CD4+ T cells') |
       (reference_latent.obs.cell_type == 'CD8+ T cells'))
reference_latent.obs['ct_low'][idx] = 'T cells'

idx = ((reference_latent.obs.cell_type == 'CD10+ B cells') |
       (reference_latent.obs.cell_type == 'CD20+ B cells'))
reference_latent.obs['ct_low'][idx] = 'B cells'

idx = ((reference_latent.obs.cell_type == 'CD14+ Monocytes') |
       (reference_latent.obs.cell_type == 'CD16+ Monocytes') |
       (reference_latent.obs.cell_type == 'Monocyte progenitors'))
reference_latent.obs['ct_low'][idx] = 'Monocytes'

idx = ((reference_latent.obs.cell_type == 'Erythrocytes') |
       (reference_latent.obs.cell_type == 'Erythroid progenitors'))
reference_latent.obs['ct_low'][idx] = 'Erythrocytes'

idx = ((reference_latent.obs.cell_type == 'Monocyte-derived dendritic cells') |
       (reference_latent.obs.cell_type == 'Plasmacytoid dendritic cells'))
reference_latent.obs['ct_low'][idx] = 'Dendritic cells'

idx = reference_latent.obs.cell_type == 'HSPCs'
reference_latent.obs['ct_low'][idx] = 'HSPCs'

idx = reference_latent.obs.cell_type == 'Megakaryocyte progenitors'
reference_latent.obs['ct_low'][idx] = 'Megakaryocyte progenitors'

idx = reference_latent.obs.cell_type == 'NK cells'
reference_latent.obs['ct_low'][idx] = 'NK cells'

idx = reference_latent.obs.cell_type == 'NKT cells'
reference_latent.obs['ct_low'][idx] = 'NKT cells'

idx = reference_latent.obs.cell_type == 'Plasma cells'
reference_latent.obs['ct_low'][idx] = 'Plasma cells'
```

Example 33 (python):
```python
/tmp/ipykernel_1063462/4260835584.py:5: SettingWithCopyWarning:
A value is trying to be set on a copy of a slice from a DataFrame

See the caveats in the documentation: https://pandas.pydata.org/pandas-docs/stable/user_guide/indexing.html#returning-a-view-versus-a-copy
  reference_latent.obs['ct_low'][idx] = 'T cells'
```

Example 34 (python):
```python
sc.pl.umap(reference_latent,
           color=['ct_low'],
           frameon=False,
           wspace=0.6, s=60,
           palette=sns.color_palette('colorblind', as_cmap=True)
           )
```

Example 35 (python):
```python
for s in np.unique(reference_latent.obs.study):
    ref_s = cp.deepcopy(reference_latent)
    ref_s.obs.ct_low[reference_latent.obs.study != s] = np.nan

    sc.pl.umap(ref_s,
               color=['ct_low'],
               frameon=False,
               wspace=0.6, s=60,
               palette=sns.color_palette('colorblind', as_cmap=True), title=s,
               save=s+'.pdf'
               )
```

Example 36 (unknown):
```unknown
WARNING: saving figure to file figures/umapFreytag.pdf
```

Example 37 (unknown):
```unknown
WARNING: saving figure to file figures/umapOetjen.pdf
```

Example 38 (unknown):
```unknown
WARNING: saving figure to file figures/umapSun.pdf
```

Example 39 (unknown):
```unknown
ref_path = 'ref_model/'
vae.save(ref_path, overwrite=True)
reference_latent.write(ref_path + 'ref_latent.h5ad')
```

Example 40 (python):
```python
reference_latent.obs['celltype_batch'] = np.char.add(np.char.add(np.array(reference_latent.obs['cell_type'], dtype= str), '-'),
                                             np.array(reference_latent.obs['study'], dtype=str))
```

Example 41 (unknown):
```unknown
classifier='knn'
```

Example 42 (unknown):
```unknown
dynamic_neighbors=True
```

Example 43 (unknown):
```unknown
n_neighbors
```

Example 44 (unknown):
```unknown
print_conf=True
```

Example 45 (unknown):
```unknown
tree_ref, mp_ref = sca.classifiers.scHPL.learn_tree(data = reference_latent,
                batch_key = 'study',
                batch_order = ['Freytag', 'Oetjen', 'Sun'],
                cell_type_key='celltype_batch',
                classifier = 'knn', dynamic_neighbors=True,
                dimred = False, print_conf= False)
```

Example 46 (unknown):
```unknown
Starting tree:
```

Example 47 (unknown):
```unknown
Adding dataset Oetjen to the tree

Updated tree:
```

Example 48 (unknown):
```unknown
Adding dataset Sun to the tree

Updated tree:
```

Example 49 (python):
```python
target_adata = target_adata[:, source_adata.var_names]
target_adata
```

Example 50 (unknown):
```unknown
View of AnnData object with n_obs × n_vars = 10727 × 2000
    obs: 'batch', 'chemistry', 'data_type', 'dpt_pseudotime', 'final_annotation', 'mt_frac', 'n_counts', 'n_genes', 'sample_ID', 'size_factors', 'species', 'study', 'tissue'
    layers: 'counts'
```

Example 51 (python):
```python
target_adata = target_adata.copy()
```

Example 52 (python):
```python
model = sca.models.SCVI.load_query_data(
    target_adata,
    ref_path,
    freeze_dropout = True,
)
```

Example 53 (unknown):
```unknown
INFO     File ref_model/model.pt already downloaded
```

Example 54 (unknown):
```unknown
model.train(max_epochs=50)
```

Example 55 (unknown):
```unknown
GPU available: True, used: True
TPU available: False, using: 0 TPU cores
IPU available: False, using: 0 IPUs
LOCAL_RANK: 0 - CUDA_VISIBLE_DEVICES: [0]
```

Example 56 (unknown):
```unknown
Epoch 50/50: 100%|██████████████████| 50/50 [00:26<00:00,  1.89it/s, loss=975, v_num=1]
```

Example 57 (python):
```python
query_latent = sc.AnnData(model.get_latent_representation())
query_latent.obs['cell_type'] = target_adata.obs["final_annotation"].tolist()
query_latent.obs['batch'] = target_adata.obs["batch"].tolist()
```

Example 58 (unknown):
```unknown
surgery_path = 'surgery_model'
model.save(surgery_path, overwrite=True)
query_latent.write('query_latent.h5ad')
```

Example 59 (python):
```python
target_adata.obs.study = "10X"
```

Example 60 (python):
```python
target_adata
```

Example 61 (unknown):
```unknown
AnnData object with n_obs × n_vars = 10727 × 2000
    obs: 'batch', 'chemistry', 'data_type', 'dpt_pseudotime', 'final_annotation', 'mt_frac', 'n_counts', 'n_genes', 'sample_ID', 'size_factors', 'species', 'study', 'tissue', '_scvi_batch', '_scvi_labels'
    uns: '_scvi_uuid', '_scvi_manager_uuid'
    layers: 'counts'
```

Example 62 (python):
```python
adata_full = source_adata.concatenate(target_adata, batch_key="ref_query")
adata_full
```

Example 63 (unknown):
```unknown
AnnData object with n_obs × n_vars = 32484 × 2000
    obs: 'batch', 'chemistry', 'data_type', 'dpt_pseudotime', 'final_annotation', 'mt_frac', 'n_counts', 'n_genes', 'sample_ID', 'size_factors', 'species', 'study', 'tissue', '_scvi_batch', '_scvi_labels', 'ref_query'
    var: 'highly_variable-0', 'means-0', 'dispersions-0', 'dispersions_norm-0', 'highly_variable_nbatches-0', 'highly_variable_intersection-0'
    layers: 'counts'
```

Example 64 (python):
```python
full_latent = sc.AnnData(model.get_latent_representation(adata=adata_full))
full_latent.obs['cell_type'] = adata_full.obs["final_annotation"].tolist()
full_latent.obs['batch'] = adata_full.obs["batch"].tolist()
full_latent.obs['study'] = adata_full.obs["study"].tolist()
```

Example 65 (unknown):
```unknown
INFO     Input AnnData not setup with scvi-tools. attempting to transfer AnnData setup
```

Example 66 (python):
```python
sc.pp.neighbors(full_latent)
sc.tl.leiden(full_latent)
sc.tl.umap(full_latent)
```

Example 67 (python):
```python
full_latent.obs['study'] = full_latent.obs['study'].astype('category')
full_latent.obs['study'].cat.add_categories(['0'], inplace=True)
full_latent.obs['study'].cat.reorder_categories(['Oetjen', 'Sun', 'Freytag', '0', '10X'], inplace=True)

sc.pl.umap(full_latent,
           color=['study'],
           frameon=False,
           wspace=0.6, s=25,
           palette=sns.color_palette('colorblind', as_cmap=True)[:5],
           save='study_query.pdf'
           )
```

Example 68 (unknown):
```unknown
WARNING: saving figure to file figures/umapstudy_query.pdf
```

Example 69 (unknown):
```unknown
full_latent.obs['ct_low'] = 0

idx = ((full_latent.obs.cell_type == 'CD4+ T cells') |
       (full_latent.obs.cell_type == 'CD8+ T cells'))
full_latent.obs['ct_low'][idx] = 'T cells'

idx = ((full_latent.obs.cell_type == 'CD10+ B cells') |
       (full_latent.obs.cell_type == 'CD20+ B cells'))
full_latent.obs['ct_low'][idx] = 'B cells'

idx = ((full_latent.obs.cell_type == 'CD14+ Monocytes') |
       (full_latent.obs.cell_type == 'CD16+ Monocytes') |
       (full_latent.obs.cell_type == 'Monocyte progenitors'))
full_latent.obs['ct_low'][idx] = 'Monocytes'

idx = ((full_latent.obs.cell_type == 'Erythrocytes') |
       (full_latent.obs.cell_type == 'Erythroid progenitors'))
full_latent.obs['ct_low'][idx] = 'Erythrocytes'

idx = ((full_latent.obs.cell_type == 'Monocyte-derived dendritic cells') |
       (full_latent.obs.cell_type == 'Plasmacytoid dendritic cells'))
full_latent.obs['ct_low'][idx] = 'Dendritic cells'

idx = full_latent.obs.cell_type == 'HSPCs'
full_latent.obs['ct_low'][idx] = 'HSPCs'

idx = full_latent.obs.cell_type == 'Megakaryocyte progenitors'
full_latent.obs['ct_low'][idx] = 'Megakaryocyte progenitors'

idx = full_latent.obs.cell_type == 'NK cells'
full_latent.obs['ct_low'][idx] = 'NK cells'

idx = full_latent.obs.cell_type == 'NKT cells'
full_latent.obs['ct_low'][idx] = 'NKT cells'

idx = full_latent.obs.cell_type == 'Plasma cells'
full_latent.obs['ct_low'][idx] = 'Plasma cells'
```

Example 70 (python):
```python
/tmp/ipykernel_1063462/1546695568.py:5: SettingWithCopyWarning:
A value is trying to be set on a copy of a slice from a DataFrame

See the caveats in the documentation: https://pandas.pydata.org/pandas-docs/stable/user_guide/indexing.html#returning-a-view-versus-a-copy
  full_latent.obs['ct_low'][idx] = 'T cells'
```

Example 71 (python):
```python
sc.pl.umap(full_latent,
           color=['ct_low'],
           frameon=False,
           wspace=0.6, s=60,
           palette=sns.color_palette('colorblind', as_cmap=True),
           save='cp_query.pdf'
           )
```

Example 72 (unknown):
```unknown
WARNING: saving figure to file figures/umapcp_query.pdf
```

Example 73 (python):
```python
for s in np.unique(full_latent.obs.study):
    ref_s = cp.deepcopy(full_latent)
    ref_s.obs.ct_low[full_latent.obs.study != s] = np.nan

    sc.pl.umap(ref_s,
               color=['ct_low'],
               frameon=False,
               wspace=0.6, s=60,
               palette=sns.color_palette('colorblind', as_cmap=True), title=s,
               save=s+'_query.pdf'
               )
```

Example 74 (unknown):
```unknown
WARNING: saving figure to file figures/umap10X_query.pdf
```

Example 75 (unknown):
```unknown
WARNING: saving figure to file figures/umapFreytag_query.pdf
```

Example 76 (unknown):
```unknown
WARNING: saving figure to file figures/umapOetjen_query.pdf
```

Example 77 (unknown):
```unknown
WARNING: saving figure to file figures/umapSun_query.pdf
```

Example 78 (python):
```python
full_latent.obs['celltype_batch'] = np.char.add(np.char.add(np.array(full_latent.obs['cell_type'], dtype= str), '-'),
                                             np.array(full_latent.obs['study'], dtype=str))
```

Example 79 (unknown):
```unknown
batch_added
```

Example 80 (unknown):
```unknown
batch_order
```

Example 81 (unknown):
```unknown
# First make a deep copy of the original classifier to ensure we do not overwrite it
tree_rq = cp.deepcopy(tree_ref)

tree_rq, mp_rq = sca.classifiers.scHPL.learn_tree(data = full_latent, batch_key = 'study',
                 batch_order = ['10X'],
                 batch_added = ['Oetjen', 'Freytag', 'Sun'],
                 cell_type_key='celltype_batch',
                 tree = tree_rq, retrain = False,
                classifier = 'knn',
                dimred = False)
```

Example 82 (unknown):
```unknown
Starting tree:
```

Example 83 (unknown):
```unknown
Adding dataset 10X to the tree

Updated tree:
```

Example 84 (unknown):
```unknown
query_pred = sca.classifiers.scHPL.predict_labels(query_latent.X, tree=tree_ref)
```

Example 85 (unknown):
```unknown
evaluate.heatmap()
```

Example 86 (unknown):
```unknown
sca.classifiers.scHPL.evaluate.heatmap(query_latent.obs['cell_type'], query_pred, shape=[8,5])
```

---

## A few tips on training models - scArches documentation

**URL:** http://127.0.0.1:9180/en/latest/training_tips.html

**Contents:**
- A few tips on training models

We recommend you to set recon_loss = nb or zinb. These loss functions require access to count data. You need to have raw count data in adata.raw.X.

If you don’t have access to count data and have normalized log-transformed data then set recon_loss to mse.

trVAE relies on an extra MMD term to force further integration of data sets. There is a parameter called beta (default=1) which regulates MMD effect in training. Higher values of beta will force extra mixing (might remove biological variation if too big!) while smaller values might result in less mixing (still batch effect). If you set beta = 0 the model reduces to a Vanilla CVAE, but it is better to set ‘use_mmd’ to ‘False’ when MMD should not be used.

It is important to use highly variable genes for training. We recommend to use at least 2000 HVGs and if you have more complicated datasets, conditions then try to increase it to 5000 or so to include enough information for the model.

Regarding architecture always try with the default one ([128,128], z_dimension`=10) and check the results. If you have more complicated data sets with many datasets and conditions and etc then you can increase the depth ([128,128,128] or [128,128,128,128]). According to our experiments, small values of `z_dimension between 10 (default) and 20 are good.

scVI require access to raw count data.

scVI already has a default good parameter the only thing you might change is n_layers which we suggest increasing to 2 (min) and max 4-5 for more

complicated datasets.

It requires access to raw count data.

If you have query data the query data should be treated as unlabelled (Unknown) or have the same set of cell-types labels as reference. If you have a new cell-type label that is in the query data but not in reference and you want to use this in the training query you will get an error! We will fix this in future releases.

The main hyperparameter that affects the quality of integration for the reference training is alpha_kl, the value of which is multiplied by the kl divergence term in the total loss.

If the visualized latent space looks like a single blob after the reference training, we recommend to decrease the value of alpha_kl. If the visualized latent space shows bad integration quality, we recommend to increase the value of alpha_kl. The good default value in most cases is alpha_kl = 0.5.

The required strength of group lasso regularization (alpha) depends on the number of used GPs and the size of the dataset. For 300–500 GPs, we recommend to use alpha = 0.7 and increase for larger numbers of GPs.

If soft mask in the reference training is used (soft_ext_mask=True in the model initialization), it is better to start with alpha_l1=0.5 (higher value means more constraints on how many genes are added to the gene sets) and use print_stats=True in the training for monitoring to check the reported “Share of deactivated inactive genes: ​__” is around 95% (0.95) at the end and stays so at the final 10 epochs of training. If it is much smaller, alpha_l1 should be increased by a small value (around 0.05), and if it is 100% (1.) then alpha_l1 should be decreased.

Using new terms (n_ext) in the reference training is not recommended.

---

## Build reference atlas from scratch - scArches documentation

**URL:** http://127.0.0.1:9180/en/latest/reference_building_from_scratch.html

**Contents:**
- Build reference atlas from scratch
- Download raw Dataset
- Create SCVI model and train it on reference dataset
- Use pretrained reference model and apply surgery with a new query dataset to get a bigger reference atlas
- Get latent representation of reference + query dataset and compute UMAP

We now split the data into reference and query dataset to simulate the building process. Here we use the ‘10X’ batch as query data.

For a better model performance it is necessary to select HVGs. We are doing this by applying the scanpy.pp function highly_variable_genes(). The n_top_genes is set to 2000 here. However, if you have more complicated datasets you might have to increase number of genes to capture more diversity in the data.

For consistency we set adata.X to be raw counts. In other datasets that may be already the case

Remember that the adata file has to have count data in adata.X for SCVI/SCANVI if not further specified.

Create the SCVI model instance with ZINB loss as default. Insert “gene_likelihood=’nb’,” to change the reconstruction loss to NB loss.

The resulting latent representation of the data can then be visualized with UMAP

After pretraining the model can be saved for later use or also be uploaded for other researchers with via Zenodo. For the second option please also have a look at the Zenodo notebook.

Since the model requires the datasets to have the same genes we also filter the query dataset to have the same genes as the reference dataset.

We then can apply the model surgery with the new query dataset:

And again we can save or upload the retrained model for later use or additional extensions.

**Examples:**

Example 1 (python):
```python
import os
os.chdir('../')
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)
warnings.simplefilter(action='ignore', category=UserWarning)
```

Example 2 (python):
```python
import scanpy as sc
import torch
import scarches as sca
from scarches.dataset.trvae.data_handling import remove_sparsity
import matplotlib.pyplot as plt
import numpy as np
import gdown
```

Example 3 (unknown):
```unknown
WARNING:root:In order to use the mouse gastrulation seqFISH datsets, please install squidpy (see https://github.com/scverse/squidpy).
WARNING:root:In order to use sagenet models, please install pytorch geometric (see https://pytorch-geometric.readthedocs.io) and
 captum (see https://github.com/pytorch/captum).
WARNING:root:mvTCR is not installed. To use mvTCR models, please install it first using "pip install mvtcr"
WARNING:root:multigrate is not installed. To use multigrate models, please install it first using "pip install multigrate".
```

Example 4 (python):
```python
sc.settings.set_figure_params(dpi=200, frameon=False)
sc.set_figure_params(dpi=200)
sc.set_figure_params(figsize=(4, 4))
torch.set_printoptions(precision=3, sci_mode=False, edgeitems=7)
```

Example 5 (unknown):
```unknown
url = 'https://drive.google.com/uc?id=1LaYOadbotGC6gXAlo-aKfHz-spoFnawk'
output = 'pbmc.h5ad'
gdown.download(url, output, quiet=False)
```

Example 6 (unknown):
```unknown
Downloading...
From: https://drive.google.com/uc?id=1LaYOadbotGC6gXAlo-aKfHz-spoFnawk
To: /Users/chelseaalexandra.bright/theislab/scarches/pbmc.h5ad
100%|██████████| 2.06G/2.06G [01:13<00:00, 28.0MB/s]
```

Example 7 (unknown):
```unknown
'pbmc.h5ad'
```

Example 8 (python):
```python
adata = sc.read('pbmc.h5ad')
```

Example 9 (python):
```python
adata.X = adata.layers["counts"].copy()
```

Example 10 (python):
```python
target_conditions = ["10X"]
source_adata = adata[~adata.obs.study.isin(target_conditions)].copy()
target_adata = adata[adata.obs.study.isin(target_conditions)].copy()
print(source_adata)
print(target_adata)
```

Example 11 (unknown):
```unknown
AnnData object with n_obs × n_vars = 22779 × 12303
    obs: 'batch', 'chemistry', 'data_type', 'dpt_pseudotime', 'final_annotation', 'mt_frac', 'n_counts', 'n_genes', 'sample_ID', 'size_factors', 'species', 'study', 'tissue'
    layers: 'counts'
AnnData object with n_obs × n_vars = 10727 × 12303
    obs: 'batch', 'chemistry', 'data_type', 'dpt_pseudotime', 'final_annotation', 'mt_frac', 'n_counts', 'n_genes', 'sample_ID', 'size_factors', 'species', 'study', 'tissue'
    layers: 'counts'
```

Example 12 (python):
```python
source_adata.raw = source_adata
```

Example 13 (python):
```python
source_adata
```

Example 14 (unknown):
```unknown
AnnData object with n_obs × n_vars = 22779 × 12303
    obs: 'batch', 'chemistry', 'data_type', 'dpt_pseudotime', 'final_annotation', 'mt_frac', 'n_counts', 'n_genes', 'sample_ID', 'size_factors', 'species', 'study', 'tissue'
    layers: 'counts'
```

Example 15 (python):
```python
sc.pp.normalize_total(source_adata)
```

Example 16 (python):
```python
sc.pp.log1p(source_adata)
```

Example 17 (python):
```python
sc.pp.highly_variable_genes(
    source_adata,
    n_top_genes=2000,
    batch_key="batch",
    subset=True)
```

Example 18 (python):
```python
source_adata.X = source_adata.raw[:, source_adata.var_names].X
```

Example 19 (python):
```python
source_adata
```

Example 20 (unknown):
```unknown
AnnData object with n_obs × n_vars = 22779 × 2000
    obs: 'batch', 'chemistry', 'data_type', 'dpt_pseudotime', 'final_annotation', 'mt_frac', 'n_counts', 'n_genes', 'sample_ID', 'size_factors', 'species', 'study', 'tissue'
    var: 'highly_variable', 'means', 'dispersions', 'dispersions_norm', 'highly_variable_nbatches', 'highly_variable_intersection'
    uns: 'log1p', 'hvg'
    layers: 'counts'
```

Example 21 (python):
```python
sca.models.SCVI.setup_anndata(source_adata, batch_key="batch")
```

Example 22 (python):
```python
INFO     Using batches from adata.obs["batch"]
INFO     No label_key inputted, assuming all cells have same label
INFO     Using data from adata.X
INFO     Computing library size prior per batch
INFO     Successfully registered anndata object containing 22779 cells, 2000 vars, 9 batches,
         1 labels, and 0 proteins. Also registered 0 extra categorical covariates and 0 extra
         continuous covariates.
INFO     Please do not further modify adata until model is trained.
```

Example 23 (python):
```python
vae = sca.models.SCVI(
    source_adata,
    n_layers=2,
    encode_covariates=True,
    deeply_inject_covariates=False,
    use_layer_norm="both",
    use_batch_norm="none",
)
```

Example 24 (unknown):
```unknown
early_stopping_kwargs = {
    "early_stopping_metric": "elbo",
    "save_best_state_metric": "elbo",
    "patience": 10,
    "threshold": 0,
    "reduce_lr_on_plateau": True,
    "lr_patience": 8,
    "lr_factor": 0.1,
}
vae.train(n_epochs=500, frequency=1, early_stopping_kwargs=early_stopping_kwargs)
```

Example 25 (unknown):
```unknown
INFO     Training for 500 epochs
INFO     KL warmup for 400 epochs
Training...:  19%|█▊        | 93/500 [02:04<09:08,  1.35s/it]INFO     Reducing LR on epoch 93.
Training...:  27%|██▋       | 133/500 [02:58<08:23,  1.37s/it]INFO     Reducing LR on epoch 133.
Training...:  38%|███▊      | 188/500 [04:13<06:59,  1.34s/it]INFO     Reducing LR on epoch 188.
Training...:  40%|███▉      | 198/500 [04:26<06:41,  1.33s/it]INFO     Reducing LR on epoch 198.
Training...:  42%|████▏     | 208/500 [04:39<06:31,  1.34s/it]INFO     Reducing LR on epoch 208.
Training...:  42%|████▏     | 210/500 [04:42<06:25,  1.33s/it]INFO    
         Stopping early: no improvement of more than 0 nats in 10 epochs
INFO     If the early stopping criterion is too strong, please instantiate it with different
         parameters in the train method.
Training...:  42%|████▏     | 210/500 [04:43<06:32,  1.35s/it]
INFO     Training is still in warming up phase. If your applications rely on the posterior
         quality, consider training for more epochs or reducing the kl warmup.
INFO     Training time:  201 s. / 500 epochs
```

Example 26 (python):
```python
reference_latent = sc.AnnData(vae.get_latent_representation())
reference_latent.obs["cell_type"] = source_adata.obs["final_annotation"].tolist()
reference_latent.obs["batch"] = source_adata.obs["batch"].tolist()
```

Example 27 (python):
```python
sc.pp.neighbors(reference_latent, n_neighbors=8)
sc.tl.leiden(reference_latent)
sc.tl.umap(reference_latent)
sc.pl.umap(reference_latent,
           color=['batch', 'cell_type'],
           frameon=False,
           wspace=0.6,
           )
```

Example 28 (unknown):
```unknown
... storing 'cell_type' as categorical
... storing 'batch' as categorical
```

Example 29 (unknown):
```unknown
ref_path = 'ref_model/'
vae.save(ref_path, overwrite=True)
```

Example 30 (python):
```python
target_adata
```

Example 31 (unknown):
```unknown
AnnData object with n_obs × n_vars = 10727 × 12303
    obs: 'batch', 'chemistry', 'data_type', 'dpt_pseudotime', 'final_annotation', 'mt_frac', 'n_counts', 'n_genes', 'sample_ID', 'size_factors', 'species', 'study', 'tissue'
    layers: 'counts'
```

Example 32 (python):
```python
target_adata = target_adata[:, source_adata.var_names]
target_adata
```

Example 33 (unknown):
```unknown
View of AnnData object with n_obs × n_vars = 10727 × 2000
    obs: 'batch', 'chemistry', 'data_type', 'dpt_pseudotime', 'final_annotation', 'mt_frac', 'n_counts', 'n_genes', 'sample_ID', 'size_factors', 'species', 'study', 'tissue'
    layers: 'counts'
```

Example 34 (python):
```python
model = sca.models.SCVI.load_query_data(
    target_adata,
    ref_path,
    freeze_dropout = True,
)
```

Example 35 (unknown):
```unknown
Trying to set attribute `.uns` of view, copying.
```

Example 36 (python):
```python
INFO     .obs[_scvi_labels] not found in target, assuming every cell is same category
INFO     Using data from adata.X
INFO     Computing library size prior per batch
INFO     Registered keys:['X', 'batch_indices', 'local_l_mean', 'local_l_var', 'labels']
INFO     Successfully registered anndata object containing 10727 cells, 2000 vars, 10
         batches, 1 labels, and 0 proteins. Also registered 0 extra categorical covariates
         and 0 extra continuous covariates.
```

Example 37 (unknown):
```unknown
model.train(n_epochs=500, frequency=1, early_stopping_kwargs=early_stopping_kwargs, weight_decay=0)
```

Example 38 (unknown):
```unknown
INFO     Training for 500 epochs
INFO     KL warmup for 400 epochs
Training...:  12%|█▏        | 61/500 [00:33<04:03,  1.80it/s]INFO     Reducing LR on epoch 61.
Training...:  14%|█▍        | 72/500 [00:39<03:52,  1.84it/s]INFO     Reducing LR on epoch 72.
Training...:  15%|█▍        | 74/500 [00:40<03:52,  1.83it/s]INFO    
         Stopping early: no improvement of more than 0 nats in 10 epochs
INFO     If the early stopping criterion is too strong, please instantiate it with different
         parameters in the train method.
Training...:  15%|█▍        | 74/500 [00:41<03:58,  1.79it/s]
INFO     Training is still in warming up phase. If your applications rely on the posterior
         quality, consider training for more epochs or reducing the kl warmup.
INFO     Training time:  26 s. / 500 epochs
```

Example 39 (python):
```python
query_latent = sc.AnnData(model.get_latent_representation())
query_latent.obs['cell_type'] = target_adata.obs["final_annotation"].tolist()
query_latent.obs['batch'] = target_adata.obs["batch"].tolist()
```

Example 40 (python):
```python
sc.pp.neighbors(query_latent)
sc.tl.leiden(query_latent)
sc.tl.umap(query_latent)
plt.figure()
sc.pl.umap(
    query_latent,
    color=["batch", "cell_type"],
    frameon=False,
    wspace=0.6,
)
```

Example 41 (unknown):
```unknown
... storing 'cell_type' as categorical
... storing 'batch' as categorical
```

Example 42 (unknown):
```unknown
<Figure size 320x320 with 0 Axes>
```

Example 43 (unknown):
```unknown
surgery_path = 'surgery_model'
model.save(surgery_path, overwrite=True)
```

Example 44 (python):
```python
adata_full = source_adata.concatenate(target_adata, batch_key="ref_query")
adata_full
```

Example 45 (unknown):
```unknown
AnnData object with n_obs × n_vars = 33506 × 2000
    obs: 'batch', 'chemistry', 'data_type', 'dpt_pseudotime', 'final_annotation', 'mt_frac', 'n_counts', 'n_genes', 'sample_ID', 'size_factors', 'species', 'study', 'tissue', '_scvi_batch', '_scvi_labels', '_scvi_local_l_mean', '_scvi_local_l_var', 'ref_query'
    var: 'highly_variable-0', 'means-0', 'dispersions-0', 'dispersions_norm-0', 'highly_variable_nbatches-0', 'highly_variable_intersection-0'
    layers: 'counts'
```

Example 46 (python):
```python
full_latent = sc.AnnData(model.get_latent_representation(adata=adata_full))
full_latent.obs['cell_type'] = adata_full.obs["final_annotation"].tolist()
full_latent.obs['batch'] = adata_full.obs["batch"].tolist()
```

Example 47 (python):
```python
INFO     Input adata not setup with scvi. attempting to transfer anndata setup
INFO     Using data from adata.X
INFO     Computing library size prior per batch
INFO     Registered keys:['X', 'batch_indices', 'local_l_mean', 'local_l_var', 'labels']
INFO     Successfully registered anndata object containing 33506 cells, 2000 vars, 10
         batches, 1 labels, and 0 proteins. Also registered 0 extra categorical covariates
         and 0 extra continuous covariates.
```

Example 48 (python):
```python
sc.pp.neighbors(full_latent)
sc.tl.leiden(full_latent)
sc.tl.umap(full_latent)
plt.figure()
sc.pl.umap(
    full_latent,
    color=["batch", "cell_type"],
    frameon=False,
    wspace=0.6,
)
```

Example 49 (unknown):
```unknown
... storing 'cell_type' as categorical
... storing 'batch' as categorical
```

Example 50 (unknown):
```unknown
<Figure size 320x320 with 0 Axes>
```

---

## Unsupervised surgery pipeline with SCVI - scArches documentation

**URL:** http://127.0.0.1:9180/en/latest/scvi_surgery_pipeline.html

**Contents:**
- Unsupervised surgery pipeline with SCVI
- Set relevant anndata.obs labels and training length
- Download Dataset and split into reference dataset and query dataset
- Create SCVI model and train it on reference dataset
- Create anndata file of latent representation and compute UMAP
- Perform surgery on reference model and train on query dataset
- Get latent representation of reference + query dataset and compute UMAP

Here we use the CelSeq2 and SS2 studies as query data and the other 3 studies as reference atlas.

This line makes sure that count data is in the adata.X. Remember that count data in adata.X is necessary when using “nb” or “zinb” loss.

Preprocess reference dataset. Remember that the adata file has to have count data in adata.X for SCVI/SCANVI if not further specified

Create the SCVI model instance with ZINB loss as default. Insert “gene_likelihood=’nb’,” to change the reconstruction loss to NB loss.

After pretraining the model can be saved for later use

**Examples:**

Example 1 (python):
```python
import os
os.chdir('../')
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)
warnings.simplefilter(action='ignore', category=UserWarning)
```

Example 2 (python):
```python
import scanpy as sc
import torch
import scarches as sca
from scarches.dataset.trvae.data_handling import remove_sparsity
import matplotlib.pyplot as plt
import numpy as np
import gdown
```

Example 3 (python):
```python
sc.settings.set_figure_params(dpi=200, frameon=False)
sc.set_figure_params(dpi=200)
sc.set_figure_params(figsize=(4, 4))
torch.set_printoptions(precision=3, sci_mode=False, edgeitems=7)
```

Example 4 (unknown):
```unknown
condition_key = 'study'
cell_type_key = 'cell_type'
target_conditions = ['Pancreas CelSeq2', 'Pancreas SS2']
```

Example 5 (unknown):
```unknown
url = 'https://drive.google.com/uc?id=1ehxgfHTsMZXy6YzlFKGJOsBKQ5rrvMnd'
output = 'pancreas.h5ad'
gdown.download(url, output, quiet=False)
```

Example 6 (unknown):
```unknown
Downloading...
From: https://drive.google.com/uc?id=1ehxgfHTsMZXy6YzlFKGJOsBKQ5rrvMnd
To: /home/marco/Documents/git_repos/scarches/pancreas.h5ad
126MB [00:03, 32.0MB/s]
```

Example 7 (unknown):
```unknown
'pancreas.h5ad'
```

Example 8 (python):
```python
adata_all = sc.read('pancreas.h5ad')
```

Example 9 (python):
```python
adata = adata_all.raw.to_adata()
adata = remove_sparsity(adata)
source_adata = adata[~adata.obs[condition_key].isin(target_conditions)].copy()
target_adata = adata[adata.obs[condition_key].isin(target_conditions)].copy()
```

Example 10 (python):
```python
source_adata
```

Example 11 (unknown):
```unknown
AnnData object with n_obs × n_vars = 10294 × 1000
    obs: 'batch', 'study', 'cell_type', 'size_factors'
```

Example 12 (python):
```python
target_adata
```

Example 13 (unknown):
```unknown
AnnData object with n_obs × n_vars = 5387 × 1000
    obs: 'batch', 'study', 'cell_type', 'size_factors'
```

Example 14 (python):
```python
sca.models.SCVI.setup_anndata(source_adata, batch_key=condition_key)
```

Example 15 (python):
```python
INFO     Using batches from adata.obs["study"]
INFO     No label_key inputted, assuming all cells have same label
INFO     Using data from adata.X
INFO     Computing library size prior per batch
INFO     Successfully registered anndata object containing 10294 cells, 1000 vars, 3 batches,
         1 labels, and 0 proteins. Also registered 0 extra categorical covariates and 0 extra
         continuous covariates.
INFO     Please do not further modify adata until model is trained.
```

Example 16 (python):
```python
vae = sca.models.SCVI(
    source_adata,
    n_layers=2,
    encode_covariates=True,
    deeply_inject_covariates=False,
    use_layer_norm="both",
    use_batch_norm="none",
)
```

Example 17 (unknown):
```unknown
vae.train()
```

Example 18 (unknown):
```unknown
GPU available: True, used: True
TPU available: False, using: 0 TPU cores
LOCAL_RANK: 0 - CUDA_VISIBLE_DEVICES: [0]
```

Example 19 (unknown):
```unknown
Epoch 400/400: 100%|███████| 400/400 [03:31<00:00,  1.89it/s, loss=502, v_num=1]
```

Example 20 (python):
```python
reference_latent = sc.AnnData(vae.get_latent_representation())
reference_latent.obs["cell_type"] = source_adata.obs[cell_type_key].tolist()
reference_latent.obs["batch"] = source_adata.obs[condition_key].tolist()
```

Example 21 (python):
```python
sc.pp.neighbors(reference_latent, n_neighbors=8)
sc.tl.leiden(reference_latent)
sc.tl.umap(reference_latent)
sc.pl.umap(reference_latent,
           color=['batch', 'cell_type'],
           frameon=False,
           wspace=0.6,
           )
```

Example 22 (unknown):
```unknown
... storing 'cell_type' as categorical
... storing 'batch' as categorical
```

Example 23 (unknown):
```unknown
ref_path = 'ref_model/'
vae.save(ref_path, overwrite=True)
```

Example 24 (python):
```python
model = sca.models.SCVI.load_query_data(
    target_adata,
    ref_path,
    freeze_dropout = True,
)
```

Example 25 (python):
```python
INFO     .obs[_scvi_labels] not found in target, assuming every cell is same category
INFO     Using data from adata.X
INFO     Computing library size prior per batch
INFO     Registered keys:['X', 'batch_indices', 'local_l_mean', 'local_l_var', 'labels']
INFO     Successfully registered anndata object containing 5387 cells, 1000 vars, 5 batches,
         1 labels, and 0 proteins. Also registered 0 extra categorical covariates and 0 extra
         continuous covariates.
```

Example 26 (unknown):
```unknown
model.train(max_epochs=200, plan_kwargs=dict(weight_decay=0.0))
```

Example 27 (unknown):
```unknown
GPU available: True, used: True
TPU available: False, using: 0 TPU cores
LOCAL_RANK: 0 - CUDA_VISIBLE_DEVICES: [0]
```

Example 28 (unknown):
```unknown
Epoch 200/200: 100%|██| 200/200 [00:45<00:00,  4.37it/s, loss=1.16e+03, v_num=1]
```

Example 29 (python):
```python
query_latent = sc.AnnData(model.get_latent_representation())
query_latent.obs['cell_type'] = target_adata.obs[cell_type_key].tolist()
query_latent.obs['batch'] = target_adata.obs[condition_key].tolist()
```

Example 30 (python):
```python
sc.pp.neighbors(query_latent)
sc.tl.leiden(query_latent)
sc.tl.umap(query_latent)
plt.figure()
sc.pl.umap(
    query_latent,
    color=["batch", "cell_type"],
    frameon=False,
    wspace=0.6,
)
```

Example 31 (unknown):
```unknown
... storing 'cell_type' as categorical
... storing 'batch' as categorical
```

Example 32 (unknown):
```unknown
<Figure size 320x320 with 0 Axes>
```

Example 33 (unknown):
```unknown
surgery_path = 'surgery_model'
model.save(surgery_path, overwrite=True)
```

Example 34 (python):
```python
adata_full = source_adata.concatenate(target_adata)
full_latent = sc.AnnData(model.get_latent_representation(adata=adata_full))
full_latent.obs['cell_type'] = adata_full.obs[cell_type_key].tolist()
full_latent.obs['batch'] = adata_full.obs[condition_key].tolist()
```

Example 35 (python):
```python
INFO     Input adata not setup with scvi. attempting to transfer anndata setup
INFO     Using data from adata.X
INFO     Computing library size prior per batch
INFO     Registered keys:['X', 'batch_indices', 'local_l_mean', 'local_l_var', 'labels']
INFO     Successfully registered anndata object containing 15681 cells, 1000 vars, 5 batches,
         1 labels, and 0 proteins. Also registered 0 extra categorical covariates and 0 extra
         continuous covariates.
```

Example 36 (python):
```python
sc.pp.neighbors(full_latent)
sc.tl.leiden(full_latent)
sc.tl.umap(full_latent)
plt.figure()
sc.pl.umap(
    full_latent,
    color=["batch", "cell_type"],
    frameon=False,
    wspace=0.6,
)
```

Example 37 (unknown):
```unknown
... storing 'cell_type' as categorical
... storing 'batch' as categorical
```

Example 38 (unknown):
```unknown
<Figure size 320x320 with 0 Axes>
```

---

## Multi-Modal Surgery Pipeline with TOTALVI - scArches documentation

**URL:** http://127.0.0.1:9180/en/latest/totalvi_surgery_pipeline.html

**Contents:**
- Multi-Modal Surgery Pipeline with TOTALVI
- Data loading and preprocessing
- Create TOTALVI model and train it on CITE-seq reference dataset
- Save Latent representation and visualize RNA data
- Save trained reference model
- Perform surgery on reference model and train on query dataset without protein data
- Impute protein data for the query dataset and visualize
- Get latent representation of reference + query dataset and compute UMAP

For totalVI, we will treat two CITE-seq PBMC datasets from 10X Genomics as the reference. These datasets were already filtered for outliers like doublets, as described in the totalVI manuscript. There are 14 proteins in the reference.

Now to concatenate the objects, which intersects the genes properly.

And split them back up into reference and query (but now genes are properly aligned between objects).

We run gene selection on the reference, because that’s all that will be avaialble to us at first.

Finally, we use these selected genes for the query dataset as well.

Impute the proteins that were observed in the reference, using the transform_batch parameter.

**Examples:**

Example 1 (python):
```python
import os
os.chdir('../')
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)
warnings.simplefilter(action='ignore', category=UserWarning)
```

Example 2 (python):
```python
import scanpy as sc
import anndata
import torch
import scarches as sca
import matplotlib.pyplot as plt
import numpy as np
import scvi as scv
import pandas as pd
```

Example 3 (python):
```python
sc.settings.set_figure_params(dpi=200, frameon=False)
sc.set_figure_params(dpi=200)
sc.set_figure_params(figsize=(4, 4))
torch.set_printoptions(precision=3, sci_mode=False, edgeitems=7)
```

Example 4 (python):
```python
adata_ref = scv.data.pbmcs_10x_cite_seq(run_setup_anndata=False)
```

Example 5 (unknown):
```unknown
INFO     Downloading file at data/pbmc_10k_protein_v3.h5ad
Downloading...: 24938it [00:00, 31923.71it/s]
INFO     Downloading file at data/pbmc_5k_protein_v3.h5ad
Downloading...: 100%|█████████████████| 18295/18295.0 [00:05<00:00, 3198.56it/s]
```

Example 6 (unknown):
```unknown
Observation names are not unique. To make them unique, call `.obs_names_make_unique`.
```

Example 7 (python):
```python
adata_query = scv.data.dataset_10x("pbmc_10k_v3")
adata_query.obs["batch"] = "PBMC 10k (RNA only)"
# put matrix of zeros for protein expression (considered missing)
pro_exp = adata_ref.obsm["protein_expression"]
data = np.zeros((adata_query.n_obs, pro_exp.shape[1]))
adata_query.obsm["protein_expression"] = pd.DataFrame(columns=pro_exp.columns, index=adata_query.obs_names, data = data)
```

Example 8 (unknown):
```unknown
INFO     Downloading file at data/10X/pbmc_10k_v3/filtered_feature_bc_matrix.h5
Downloading...: 37492it [00:02, 13500.06it/s]
```

Example 9 (unknown):
```unknown
Variable names are not unique. To make them unique, call `.var_names_make_unique`.
Variable names are not unique. To make them unique, call `.var_names_make_unique`.
```

Example 10 (python):
```python
adata_full = anndata.concat([adata_ref, adata_query])
```

Example 11 (unknown):
```unknown
Observation names are not unique. To make them unique, call `.obs_names_make_unique`.
```

Example 12 (python):
```python
adata_ref = adata_full[np.logical_or(adata_full.obs.batch == "PBMC5k", adata_full.obs.batch == "PBMC10k")].copy()
adata_query = adata_full[adata_full.obs.batch == "PBMC 10k (RNA only)"].copy()
```

Example 13 (unknown):
```unknown
Observation names are not unique. To make them unique, call `.obs_names_make_unique`.
```

Example 14 (python):
```python
sc.pp.highly_variable_genes(
    adata_ref,
    n_top_genes=4000,
    flavor="seurat_v3",
    batch_key="batch",
    subset=True,
)
```

Example 15 (unknown):
```unknown
Observation names are not unique. To make them unique, call `.obs_names_make_unique`.
Observation names are not unique. To make them unique, call `.obs_names_make_unique`.
```

Example 16 (python):
```python
adata_query = adata_query[:, adata_ref.var_names].copy()
```

Example 17 (python):
```python
sca.models.TOTALVI.setup_anndata(
    adata_ref,
    batch_key="batch",
    protein_expression_obsm_key="protein_expression"
)
```

Example 18 (python):
```python
INFO     Using batches from adata.obs["batch"]
INFO     No label_key inputted, assuming all cells have same label
INFO     Using data from adata.X
INFO     Computing library size prior per batch
INFO     Using protein expression from adata.obsm['protein_expression']
INFO     Using protein names from columns of adata.obsm['protein_expression']
INFO     Successfully registered anndata object containing 10849 cells, 4000 vars, 2 batches,
         1 labels, and 14 proteins. Also registered 0 extra categorical covariates and 0
         extra continuous covariates.
INFO     Please do not further modify adata until model is trained.
```

Example 19 (python):
```python
arches_params = dict(
    use_layer_norm="both",
    use_batch_norm="none",
)
vae_ref = sca.models.TOTALVI(
    adata_ref,
    **arches_params
)
```

Example 20 (unknown):
```unknown
vae_ref.train()
```

Example 21 (unknown):
```unknown
GPU available: True, used: True
TPU available: False, using: 0 TPU cores
LOCAL_RANK: 0 - CUDA_VISIBLE_DEVICES: [0]
```

Example 22 (unknown):
```unknown
Epoch 323/400:  81%|█▌| 323/400 [03:08<00:43,  1.76it/s, loss=1.23e+03, v_num=1]Epoch   323: reducing learning rate of group 0 to 2.4000e-03.
Epoch 358/400:  90%|█▊| 358/400 [03:28<00:24,  1.74it/s, loss=1.23e+03, v_num=1]Epoch   358: reducing learning rate of group 0 to 1.4400e-03.
Epoch 395/400:  99%|█▉| 395/400 [03:50<00:02,  1.71it/s, loss=1.22e+03, v_num=1]Epoch   395: reducing learning rate of group 0 to 8.6400e-04.
Epoch 400/400: 100%|██| 400/400 [03:53<00:00,  1.71it/s, loss=1.22e+03, v_num=1]
```

Example 23 (python):
```python
adata_ref.obsm["X_totalVI"] = vae_ref.get_latent_representation()
sc.pp.neighbors(adata_ref, use_rep="X_totalVI")
sc.tl.umap(adata_ref, min_dist=0.4)
```

Example 24 (python):
```python
sc.pl.umap(
    adata_ref,
    color=["batch"],
    frameon=False,
    ncols=1,
    title="Reference"
)
```

Example 25 (unknown):
```unknown
/home/marco/.pyenv/versions/scarches/lib/python3.7/site-packages/anndata/_core/anndata.py:1220: FutureWarning: The `inplace` parameter in pandas.Categorical.reorder_categories is deprecated and will be removed in a future version. Removing unused categories will always return a new Categorical object.
  c.reorder_categories(natsorted(c.categories), inplace=True)
... storing 'batch' as categorical
```

Example 26 (unknown):
```unknown
dir_path = "saved_model/"
vae_ref.save(dir_path, overwrite=True)
```

Example 27 (python):
```python
vae_q = sca.models.TOTALVI.load_query_data(
    adata_query,
    dir_path,
    freeze_expression=True
)
```

Example 28 (python):
```python
INFO     .obs[_scvi_labels] not found in target, assuming every cell is same category
INFO     Found batches with missing protein expression
INFO     Using data from adata.X
INFO     Computing library size prior per batch
INFO     Registered keys:['X', 'batch_indices', 'local_l_mean', 'local_l_var', 'labels',
         'protein_expression']
INFO     Successfully registered anndata object containing 11769 cells, 4000 vars, 3 batches,
         1 labels, and 14 proteins. Also registered 0 extra categorical covariates and 0
         extra continuous covariates.
```

Example 29 (unknown):
```unknown
/home/marco/.pyenv/versions/scarches/lib/python3.7/site-packages/scvi/model/base/_archesmixin.py:96: UserWarning: Query integration should be performed using models trained with version >= 0.8
  "Query integration should be performed using models trained with version >= 0.8"
```

Example 30 (unknown):
```unknown
vae_q.train(200, plan_kwargs=dict(weight_decay=0.0))
```

Example 31 (unknown):
```unknown
GPU available: True, used: True
TPU available: False, using: 0 TPU cores
LOCAL_RANK: 0 - CUDA_VISIBLE_DEVICES: [0]
```

Example 32 (unknown):
```unknown
Epoch 200/200: 100%|███████| 200/200 [02:56<00:00,  1.13it/s, loss=744, v_num=1]
```

Example 33 (python):
```python
adata_query.obsm["X_totalVI"] = vae_q.get_latent_representation()
sc.pp.neighbors(adata_query, use_rep="X_totalVI")
sc.tl.umap(adata_query, min_dist=0.4)
```

Example 34 (unknown):
```unknown
transform_batch
```

Example 35 (python):
```python
_, imputed_proteins = vae_q.get_normalized_expression(
    adata_query,
    n_samples=25,
    return_mean=True,
    transform_batch=["PBMC10k", "PBMC5k"],
)
```

Example 36 (python):
```python
adata_query.obs = pd.concat([adata_query.obs, imputed_proteins], axis=1)

sc.pl.umap(
    adata_query,
    color=imputed_proteins.columns,
    frameon=False,
    ncols=3,
)
```

Example 37 (unknown):
```unknown
/home/marco/.pyenv/versions/scarches/lib/python3.7/site-packages/anndata/_core/anndata.py:1220: FutureWarning: The `inplace` parameter in pandas.Categorical.reorder_categories is deprecated and will be removed in a future version. Removing unused categories will always return a new Categorical object.
  c.reorder_categories(natsorted(c.categories), inplace=True)
... storing 'batch' as categorical
```

Example 38 (python):
```python
adata_full_new = adata_query.concatenate(adata_ref, batch_key="none")
```

Example 39 (unknown):
```unknown
Observation names are not unique. To make them unique, call `.obs_names_make_unique`.
Observation names are not unique. To make them unique, call `.obs_names_make_unique`.
Observation names are not unique. To make them unique, call `.obs_names_make_unique`.
```

Example 40 (python):
```python
adata_full_new.obsm["X_totalVI"] = vae_q.get_latent_representation(adata_full_new)
sc.pp.neighbors(adata_full_new, use_rep="X_totalVI")
sc.tl.umap(adata_full_new, min_dist=0.3)
```

Example 41 (python):
```python
INFO     Input adata not setup with scvi. attempting to transfer anndata setup
INFO     Found batches with missing protein expression
INFO     Using data from adata.X
INFO     Computing library size prior per batch
INFO     Registered keys:['X', 'batch_indices', 'local_l_mean', 'local_l_var', 'labels',
         'protein_expression']
INFO     Successfully registered anndata object containing 22618 cells, 4000 vars, 3 batches,
         1 labels, and 14 proteins. Also registered 0 extra categorical covariates and 0
         extra continuous covariates.
```

Example 42 (python):
```python
_, imputed_proteins_all = vae_q.get_normalized_expression(
    adata_full_new,
    n_samples=25,
    return_mean=True,
    transform_batch=["PBMC10k", "PBMC5k"],
)

for i, p in enumerate(imputed_proteins_all.columns):
    adata_full_new.obs[p] = imputed_proteins_all[p].to_numpy().copy()
```

Example 43 (python):
```python
perm_inds = np.random.permutation(np.arange(adata_full_new.n_obs))
sc.pl.umap(
    adata_full_new[perm_inds],
    color=["batch"],
    frameon=False,
    ncols=1,
    title="Reference and query"
)
```

Example 44 (unknown):
```unknown
/home/marco/.pyenv/versions/scarches/lib/python3.7/site-packages/anndata/_core/anndata.py:1220: FutureWarning: The `inplace` parameter in pandas.Categorical.reorder_categories is deprecated and will be removed in a future version. Removing unused categories will always return a new Categorical object.
  c.reorder_categories(natsorted(c.categories), inplace=True)
/home/marco/.pyenv/versions/scarches/lib/python3.7/site-packages/anndata/_core/anndata.py:1229: ImplicitModificationWarning: Initializing view as actual.
  "Initializing view as actual.", ImplicitModificationWarning
Trying to set attribute `.obs` of view, copying.
Observation names are not unique. To make them unique, call `.obs_names_make_unique`.
Observation names are not unique. To make them unique, call `.obs_names_make_unique`.
... storing 'batch' as categorical
```

Example 45 (python):
```python
ax = sc.pl.umap(
    adata_full_new,
    color="batch",
    groups=["PBMC 10k (RNA only)"],
    frameon=False,
    ncols=1,
    title="Reference and query",
    alpha=0.4
)
```

Example 46 (unknown):
```unknown
/home/marco/.pyenv/versions/scarches/lib/python3.7/site-packages/anndata/_core/anndata.py:1220: FutureWarning: The `inplace` parameter in pandas.Categorical.reorder_categories is deprecated and will be removed in a future version. Removing unused categories will always return a new Categorical object.
  c.reorder_categories(natsorted(c.categories), inplace=True)
... storing 'batch' as categorical
```

Example 47 (python):
```python
sc.pl.umap(
    adata_full_new,
    color=imputed_proteins_all.columns,
    frameon=False,
    ncols=3,
    vmax="p99"
)
```

---

## Models - scArches documentation

**URL:** http://127.0.0.1:9180/en/latest/api/models.html

**Contents:**
- Models
- trVAE
- expiMap
- scPoli
- scVI
- scANVI
- TotalVI

Bases: BaseMixin, SurgeryMixin, CVAELatentsMixin

Model for scArches class. This class contains the implementation of Conditional Variational Auto-encoder.

adata (: ~anndata.AnnData) – Annotated data matrix. Has to be count data for ‘nb’ and ‘zinb’ loss and normalized log transformed data for ‘mse’ loss.

condition_key (String) – column name of conditions in adata.obs data frame.

conditions (List) – List of Condition names that the used data will contain to get the right encoding when used after reloading.

hidden_layer_sizes (List) – A list of hidden layer sizes for encoder network. Decoder network will be the reversed order.

latent_dim (Integer) – Bottleneck layer (z) size.

dr_rate (Float) – Dropput rate applied to all layers, if `dr_rate`==0 no dropout will be applied.

use_mmd (Boolean) – If ‘True’ an additional MMD loss will be calculated on the latent dim. ‘z’ or the first decoder layer ‘y’.

mmd_on (String) – Choose on which layer MMD loss will be calculated on if ‘use_mmd=True’: ‘z’ for latent dim or ‘y’ for first decoder layer.

mmd_boundary (Integer or None) – Choose on how many conditions the MMD loss should be calculated on. If ‘None’ MMD will be calculated on all conditions.

recon_loss (String) – Definition of Reconstruction-Loss-Method, ‘mse’, ‘nb’ or ‘zinb’.

beta (Float) – Scaling Factor for MMD loss

use_bn (Boolean) – If True batch normalization will be applied to layers.

use_ln (Boolean) – If True layer normalization will be applied to layers.

get_latent([x, c, mean, mean_var])

Map x in to the latent space. This function will feed data in encoder and return z for each sample in data. :param x: Numpy nd-array to be mapped to latent space. x has to be in shape [n_obs, input_dim]. If None, then self.adata.X is used. :param c: numpy nd-array of original (unencoded) desired labels for each sample. :param mean: return mean instead of random sample from the latent space :param mean_var: return mean and variance instead of random sample from the latent space if mean=False.

Map x in to the latent space.

load(dir_path[, adata, map_location])

Instantiate a model from the saved output. :param dir_path: Path to saved outputs. :param adata: AnnData object. If None, will check for and load anndata saved with the model. :param map_location: a function, torch.device, string or a dict specifying how to remap storage locations.

load_query_data(adata, reference_model[, ...])

Transfer Learning function for new data.

save(dir_path[, overwrite, save_anndata])

Save the state of the model. Neither the trainer optimizer state nor the trainer history are saved. :param dir_path: Path to a directory. :param overwrite: Overwrite existing data or not. If False and directory already exists at dir_path, error will be raised. :param save_anndata: If True, also saves the anndata :param anndata_write_kwargs: Kwargs for anndata write function.

train([n_epochs, lr, eps])

n_epochs – Number of epochs for training the model.

lr – Learning rate for training the model.

eps – torch.optim.Adam eps parameter

kwargs – kwargs for the TrVAE trainer.

Bases: BaseMixin, SurgeryMixin, CVAELatentsMixin

Model for scArches class. This class contains the implementation of Conditional Variational Auto-encoder.

adata (: ~anndata.AnnData) – Annotated data matrix. Has to be count data for ‘nb’ and ‘zinb’ loss and normalized log transformed data for ‘mse’ loss.

condition_key (String) – column name of conditions in adata.obs data frame.

conditions (List) – List of Condition names that the used data will contain to get the right encoding when used after reloading.

hidden_layer_sizes (List) – A list of hidden layer sizes for encoder network. Decoder network will be the reversed order.

latent_dim (Integer) – Bottleneck layer (z) size.

dr_rate (Float) – Dropput rate applied to all layers, if `dr_rate`==0 no dropout will be applied.

recon_loss (String) – Definition of Reconstruction-Loss-Method, ‘mse’ or ‘nb’.

use_l_encoder (Boolean) – If True and `decoder_last_layer`=’softmax’, libary size encoder is used.

use_bn (Boolean) – If True batch normalization will be applied to layers.

use_ln (Boolean) – If True layer normalization will be applied to layers.

mask (Array or List) – if not None, an array of 0s and 1s from utils.add_annotations to create VAE with a masked linear decoder.

mask_key (String) – A key in adata.varm for the mask if the mask is not provided.

decoder_last_layer (String or None) – The last layer of the decoder. Must be ‘softmax’ (default for ‘nb’ loss), identity(default for ‘mse’ loss), ‘softplus’, ‘exp’ or ‘relu’.

soft_mask (Boolean) – Use soft mask option. If True, the model will enforce mask with L1 regularization instead of multipling weight of the linear decoder by the binary mask.

n_ext (Integer) – Number of unconstarined extension terms. Used for query mapping.

n_ext_m (Integer) – Number of constrained extension terms. Used for query mapping.

use_hsic (Boolean) – If True, add HSIC regularization for unconstarined extension terms. Used for query mapping.

hsic_one_vs_all (Boolean) – If True, calculates the sum of HSIC losses for each unconstarined term vs the other terms. If False, calculates HSIC for all unconstarined terms vs the other terms. Used for query mapping.

ext_mask (Array or List) – Mask (similar to the mask argument) for unconstarined extension terms. Used for query mapping.

soft_ext_mask (Boolean) – Use the soft mask mode for training with the constarined extension terms. Used for query mapping.

get_latent([x, c, only_active, mean, mean_var])

Map x in to the latent space.

Map x in to the latent space.

latent_directions([method, get_confidence, ...])

Get directions of upregulation for each latent dimension.

latent_enrich(groups[, comparison, ...])

Gene set enrichment test for the latent space.

load(dir_path[, adata, map_location])

Instantiate a model from the saved output. :param dir_path: Path to saved outputs. :param adata: AnnData object. If None, will check for and load anndata saved with the model. :param map_location: a function, torch.device, string or a dict specifying how to remap storage locations.

load_query_data(adata, reference_model[, ...])

Transfer Learning function for new data.

Return lists of genes belonging to the terms in the mask.

Return indices of active terms.

save(dir_path[, overwrite, save_anndata])

Save the state of the model. Neither the trainer optimizer state nor the trainer history are saved. :param dir_path: Path to a directory. :param overwrite: Overwrite existing data or not. If False and directory already exists at dir_path, error will be raised. :param save_anndata: If True, also saves the anndata :param anndata_write_kwargs: Kwargs for anndata write function.

term_genes(term[, terms])

Return the dataframe with genes belonging to the term after training sorted by absolute weights in the decoder.

train([n_epochs, lr, eps, alpha, omega])

update_terms([terms, adata])

Add extension terms' names to the terms.

Map x in to the latent space. This function will feed data in encoder and return z for each sample in data.

x – Numpy nd-array to be mapped to latent space. x has to be in shape [n_obs, input_dim]. If None, then self.adata.X is used.

c – numpy nd-array of original (unencoded) desired labels for each sample.

only_active – Return only the latent variables which correspond to active terms, i.e terms that were not deactivated by the group lasso regularization.

mean – return mean instead of random sample from the latent space

mean_var – return mean and variance instead of random sample from the latent space if mean=False.

Returns array containing latent space encoding of ‘x’.

Get directions of upregulation for each latent dimension. Multipling this by raw latent scores ensures positive latent scores correspond to upregulation.

method (String) – Method of calculation, it should be ‘sum’ or ‘counts’.

get_confidence (Boolean) – Only for method=’counts’. If ‘True’, also calculate confidence of the directions.

adata (AnnData) – An AnnData object to store dimensions. If ‘None’, self.adata is used.

key_added (String) – key of adata.uns where to put the dimensions.

Gene set enrichment test for the latent space. Test the hypothesis that latent scores for each term in one group (z_1) is bigger than in the other group (z_2).

Puts results to adata.uns[key_added]. Results are a dictionary with p_h0 - probability that z_1 > z_2, p_h1 = 1-p_h0 and bf - bayes factors equal to log(p_h0/p_h1).

groups (String or Dict) – A string with the key in adata.obs to look for categories or a dictionary with categories as keys and lists of cell names as values.

comparison (String) – The category name to compare against. If ‘rest’, then compares each category against all others.

n_sample (Integer) – Number of random samples to draw for each category.

use_directions (Boolean) – If ‘True’, multiplies the latent scores by directions in adata.

directions_key (String) – The key in adata.uns for directions.

select_terms (Array) – If not ‘None’, then an index of terms to select for the test. Only does the test for these terms.

adata (AnnData) – An AnnData object to use. If ‘None’, uses self.adata.

exact (Boolean) – Use exact probabilities for comparisons.

key_added (String) – key of adata.uns where to put the results of the test.

Transfer Learning function for new data. Uses old trained model and expands it for new conditions.

adata – Query anndata object.

reference_model – A model to expand or a path to a model folder.

freeze (Boolean) – If ‘True’ freezes every part of the network except the first layers of encoder/decoder.

freeze_expression (Boolean) – If ‘True’ freeze every weight in first layers except the condition weights.

remove_dropout (Boolean) – If ‘True’ remove Dropout for Transfer Learning.

unfreeze_ext (Boolean) – If ‘True’ do not freeze weights for new constrained and unconstrained extension terms.

new_n_ext (Integer) – Number of new unconstarined extension terms to add to the reference model. Used for query mapping.

new_n_ext_m (Integer) – Number of new constrained extension terms to add to the reference model. Used for query mapping.

new_ext_mask (Array or List) – Mask (similar to the mask argument) for new unconstarined extension terms.

new_soft_ext_mask (Boolean) – Use the soft mask mode for training with the constarined extension terms.

kwargs – kwargs for the initialization of the EXPIMAP class for the query model.

New (query) model to train on query data.

Return lists of genes belonging to the terms in the mask.

Return indices of active terms. Active terms are the terms which were not deactivated by the group lasso regularization.

Return the dataframe with genes belonging to the term after training sorted by absolute weights in the decoder.

n_epochs (Integer) – Number of epochs for training the model.

lr (Float) – Learning rate for training the model.

eps (Float) – torch.optim.Adam eps parameter

alpha_kl (Float) – Multiplies the KL divergence part of the loss. Set to 0.35 by default.

alpha_epoch_anneal (Integer or None) – If not ‘None’, the KL Loss scaling factor (alpha_kl) will be annealed from 0 to 1 every epoch until the input integer is reached. By default is set to 130 epochs or to n_epochs if n_epochs < 130.

alpha (Float) – Group Lasso regularization coefficient

omega (Tensor or None) – If not ‘None’, vector of coefficients for each group

alpha_l1 (Float) – L1 regularization coefficient for the soft mask of reference (old) and new constrained terms. Specifies the strength for deactivating the genes which are not in the corresponding annotations groups in the mask.

alpha_l1_epoch_anneal (Integer) – If not ‘None’, the alpha_l1 scaling factor will be annealed from 0 to 1 every ‘alpha_l1_anneal_each’ epochs until the input integer is reached.

alpha_l1_anneal_each (Integer) – Anneal alpha_l1 every alpha_l1_anneal_each’th epoch, i.e. for 5 (default) do annealing every 5th epoch.

gamma_ext (Float) – L1 regularization coefficient for the new unconstrained terms. Specifies the strength of sparcity enforcement.

gamma_epoch_anneal (Integer) – If not ‘None’, the gamma_ext scaling factor will be annealed from 0 to 1 every ‘gamma_anneal_each’ epochs until the input integer is reached.

gamma_anneal_each (Integer) – Anneal gamma_ext every gamma_anneal_each’th epoch, i.e. for 5 (default) do annealing every 5th epoch.

beta (Float) – HSIC regularization coefficient for the unconstrained terms. Multiplies the HSIC loss terms if not ‘None’.

kwargs – kwargs for the expiMap trainer.

Add extension terms’ names to the terms.

Model for scPoli class. This class contains the methods and functionalities for label transfer and prototype training.

adata (: ~anndata.AnnData) – Annotated data matrix.

share_metadata (Bool) – Whether or not to share metadata associated with samples. The metadata is aggregated using the condition_keys. First element is taken. Consider manually adding an .obs_metadata attribute if you need more flexibility.

condition_keys (String) – column name of conditions in adata.obs data frame.

conditions (List) – List of Condition names that the used data will contain to get the right encoding when used after reloading.

cell_type_keys (List or str) – List or string of obs columns to use as cell type annotation for prototypes.

cell_types (Dictionary) – Dictionary of cell types. Keys are cell types and values are cell_type_keys. Needed for surgery.

unknown_ct_names (List) – List of strings with the names of cell clusters to be ignored for prototypes computation.

labeled_indices (List) – List of integers with the indices of the labeled cells.

prototypes_labeled (Dictionary) – Dictionary with keys mean, cov and the respective mean or covariate matrices for prototypes.

prototypes_unlabeled (Dictionary) – Dictionary with keys mean and the respective mean for unlabeled prototypes.

hidden_layer_sizes (List) – A list of hidden layer sizes for encoder network. Decoder network will be the reversed order.

latent_dim (Integer) – Bottleneck layer (z) size.

embedding_dim (Integer) – Conditional embedding size.

embedding_max_norm – Max norm allowed for conditional embeddings.

dr_rate (Float) – Dropput rate applied to all layers, if `dr_rate`==0 no dropout will be applied.

use_mmd (Boolean) – If ‘True’ an additional MMD loss will be calculated on the latent dim. ‘z’ or the first decoder layer ‘y’.

mmd_on (String) – Choose on which layer MMD loss will be calculated on if ‘use_mmd=True’: ‘z’ for latent dim or ‘y’ for first decoder layer.

mmd_boundary (Integer or None) – Choose on how many conditions the MMD loss should be calculated on. If ‘None’ MMD will be calculated on all conditions.

recon_loss (String) – Definition of Reconstruction-Loss-Method, ‘mse’, ‘nb’ or ‘zinb’.

beta (Float) – Scaling Factor for MMD loss

use_bn (Boolean) – If True batch normalization will be applied to layers.

use_ln (Boolean) – If True layer normalization will be applied to layers.

add_new_cell_type(cell_type_name, obs_key, ...)

Function used to add new annotation for a novel cell type.

classify(adata[, prototype, p, get_prob, ...])

Classifies unlabeled cells using the prototypes obtained during training.

get_conditional_embeddings()

Returns anndata object of the conditional embeddings

get_latent(adata[, mean])

Map x in to the latent space.

get_prototypes_info([prototype_set])

Generates anndata file with prototype features and annotations.

load(dir_path[, adata, map_location])

Instantiate a model from the saved output. :param dir_path: Path to saved outputs. :param adata: AnnData object. If None, will check for and load anndata saved with the model. :param map_location: a function, torch.device, string or a dict specifying how to remap storage locations.

load_query_data(adata, reference_model[, ...])

Transfer Learning function for new data.

save(dir_path[, overwrite, save_anndata])

Save the state of the model. Neither the trainer optimizer state nor the trainer history are saved. :param dir_path: Path to a directory. :param overwrite: Overwrite existing data or not. If False and directory already exists at dir_path, error will be raised. :param save_anndata: If True, also saves the anndata :param anndata_write_kwargs: Kwargs for anndata write function.

train([n_epochs, pretraining_epochs, eta, ...])

Function used to add new annotation for a novel cell type.

cell_type_name (str) – Name of the new cell type

obs_key (str) – Obs column key to define the hierarchy level of celltype annotation.

prototypes (list) – List of indices of the unlabeled prototypes that correspond to the new cell type

x (np.ndarray) – Features to be classified. If None the stored model’s adata is used.

c (np.ndarray) – Condition vector. If None the stored model’s condition vector is used.

Classifies unlabeled cells using the prototypes obtained during training. Data handling before call to model’s classify method.

Features to be classified. If None the stored model’s adata is used.

Condition vector, or dictionary when the model is conditioned on multiple batch covariates.

Boolean whether to classify the gene features or prototypes stored stored in the model.

Returns anndata object of the conditional embeddings

Map x in to the latent space. This function will feed data in encoder and return z for each sample in data.

Numpy nd-array to be mapped to latent space. x has to be in shape [n_obs, input_dim].

numpy nd-array of original (unencoded) desired labels for each sample.

return mean instead of random sample from the latent space

Generates anndata file with prototype features and annotations.

cell_type_name (str) – Name of the new cell type

prototypes (list) – List of indices of the unlabeled prototypes that correspond to the new cell type

Transfer Learning function for new data. Uses old trained model and expands it for new conditions.

adata – Query anndata object.

reference_model – SCPOLI model to expand or a path to SCPOLI model folder.

labeled_indices (List) – List of integers with the indices of the labeled cells.

unknown_ct_names (List) – List of strings with the names of cell clusters to be ignored for prototypes computation.

freeze (Boolean) – If ‘True’ freezes every part of the network except the first layers of encoder/decoder.

freeze_expression (Boolean) – If ‘True’ freeze every weight in first layers except the condition weights.

remove_dropout (Boolean) – If ‘True’ remove Dropout for Transfer Learning.

map_location – map_location to remap storage locations (as in ‘.load’) of ‘reference_model’. Only taken into account if ‘reference_model’ is a path to a model on disk.

new_model – New SCPOLI model to train on query data.

n_epochs – Number of epochs for training the model.

lr – Learning rate for training the model.

eps – torch.optim.Adam eps parameter

kwargs – kwargs for the scPoli trainer.

Bases: RNASeqMixin, VAEMixin, ArchesMixin, UnsupervisedTrainingMixin, BaseMinifiedModeModelClass

single-cell Variational Inference :cite:p:`Lopez18`.

adata – AnnData object that has been registered via setup_anndata(). If None, then the underlying module will not be initialized until training, and a LightningDataModule must be passed in during training (EXPERIMENTAL).

n_hidden – Number of nodes per hidden layer.

n_latent – Dimensionality of the latent space.

n_layers – Number of hidden layers used for encoder and decoder NNs.

dropout_rate – Dropout rate for neural networks.

dispersion – One of the following: 'gene' - dispersion parameter of NB is constant per gene across cells 'gene-batch' - dispersion can differ between different batches 'gene-label' - dispersion can differ between different labels 'gene-cell' - dispersion can differ for every gene in every cell

One of the following:

'gene' - dispersion parameter of NB is constant per gene across cells

'gene-batch' - dispersion can differ between different batches

'gene-label' - dispersion can differ between different labels

'gene-cell' - dispersion can differ for every gene in every cell

gene_likelihood – One of: 'nb' - Negative binomial distribution 'zinb' - Zero-inflated negative binomial distribution 'poisson' - Poisson distribution

'nb' - Negative binomial distribution

'zinb' - Zero-inflated negative binomial distribution

'poisson' - Poisson distribution

latent_distribution – One of: 'normal' - Normal distribution 'ln' - Logistic normal distribution (Normal(0, I) transformed by softmax)

'normal' - Normal distribution

'ln' - Logistic normal distribution (Normal(0, I) transformed by softmax)

**kwargs – Additional keyword arguments for VAE.

See further usage examples in the following tutorials:

/tutorials/notebooks/quick_start/api_overview

/tutorials/notebooks/scrna/harmonization

/tutorials/notebooks/scrna/scarches_scvi_tools

/tutorials/notebooks/scrna/scvi_in_R

Data attached to model instance.

Manager instance associated with self.adata.

The current device that the module’s params are on.

Returns computed metrics during training.

Whether the model has been trained.

The type of minified data associated with this model, if applicable.

Summary string of the model.

Observations that are in test set.

Observations that are in train set.

Observations that are in validation set.

convert_legacy_save(dir_path, output_dir_path)

Converts a legacy saved model (<v0.15.0) to the updated save format.

deregister_manager([adata])

Deregisters the AnnDataManager instance associated with adata.

differential_expression([adata, groupby, ...])

A unified method for differential expression analysis.

get_anndata_manager(adata[, required])

Retrieves the AnnDataManager for a given AnnData object.

get_elbo([adata, indices, batch_size])

Return the ELBO for the data.

get_feature_correlation_matrix([adata, ...])

Generate gene-gene correlation matrix using scvi uncertainty and expression.

get_from_registry(adata, registry_key)

Returns the object in AnnData associated with the key in the data registry.

get_latent_library_size([adata, indices, ...])

Returns the latent library size for each cell.

get_latent_representation([adata, indices, ...])

Return the latent representation for each cell.

get_likelihood_parameters([adata, indices, ...])

Estimates for the parameters of the likelihood \(p(x \mid z)\).

get_marginal_ll([adata, indices, ...])

Return the marginal LL for the data.

get_normalized_expression([adata, indices, ...])

Returns the normalized (decoded) gene expression.

get_reconstruction_error([adata, indices, ...])

Return the reconstruction error for the data.

load(dir_path[, adata, accelerator, device, ...])

Instantiate a model from the saved output.

load_query_data(adata, reference_model[, ...])

Online update of a reference model with scArches algorithm :cite:p:`Lotfollahi21`.

load_registry(dir_path[, prefix])

Return the full registry saved with the model.

minify_adata([minified_data_type, ...])

Minifies the model's adata.

posterior_predictive_sample([adata, ...])

Generate predictive samples from the posterior predictive distribution.

prepare_query_anndata(adata, reference_model)

Prepare data for query integration.

register_manager(adata_manager)

Registers an AnnDataManager instance with this model class.

save(dir_path[, prefix, overwrite, ...])

Save the state of the model.

setup_anndata(adata[, layer, batch_key, ...])

Sets up the AnnData object for this model.

Move model to device.

train([max_epochs, accelerator, devices, ...])

view_anndata_setup([adata, ...])

Print summary of the setup for the initial AnnData or a given AnnData object.

view_setup_args(dir_path[, prefix])

Print args used to setup a saved model.

Minifies the model’s adata.

Minifies the adata, and registers new anndata fields: latent qzm, latent qzv, adata uns containing minified-adata type, and library size. This also sets the appropriate property on the module to indicate that the adata is minified.

minified_data_type – How to minify the data. Currently only supports latent_posterior_parameters. If minified_data_type == latent_posterior_parameters: the original count data is removed (adata.X, adata.raw, and any layers) the parameters of the latent representation of the original data is stored everything else is left untouched

How to minify the data. Currently only supports latent_posterior_parameters. If minified_data_type == latent_posterior_parameters:

the original count data is removed (adata.X, adata.raw, and any layers)

the parameters of the latent representation of the original data is stored

everything else is left untouched

use_latent_qzm_key – Key to use in adata.obsm where the latent qzm params are stored

use_latent_qzv_key – Key to use in adata.obsm where the latent qzv params are stored

The modification is not done inplace – instead the model is assigned a new (minified) version of the adata.

Sets up the AnnData object for this model.

A mapping will be created between data fields used by this model to their respective locations in adata. None of the data in adata are modified. Only adds fields to adata.

adata – AnnData object. Rows represent cells, columns represent features.

layer – if not None, uses this as the key in adata.layers for raw count data.

batch_key – key in adata.obs for batch information. Categories will automatically be converted into integer categories and saved to adata.obs[‘_scvi_batch’]. If None, assigns the same batch to all the data.

labels_key – key in adata.obs for label information. Categories will automatically be converted into integer categories and saved to adata.obs[‘_scvi_labels’]. If None, assigns the same label to all the data.

size_factor_key – key in adata.obs for size factor information. Instead of using library size as a size factor, the provided size factor column will be used as offset in the mean of the likelihood. Assumed to be on linear scale.

categorical_covariate_keys – keys in adata.obs that correspond to categorical data. These covariates can be added in addition to the batch covariate and are also treated as nuisance factors (i.e., the model tries to minimize their effects on the latent space). Thus, these should not be used for biologically-relevant factors that you do _not_ want to correct for.

continuous_covariate_keys – keys in adata.obs that correspond to continuous data. These covariates can be added in addition to the batch covariate and are also treated as nuisance factors (i.e., the model tries to minimize their effects on the latent space). Thus, these should not be used for biologically-relevant factors that you do _not_ want to correct for.

Bases: RNASeqMixin, VAEMixin, ArchesMixin, BaseMinifiedModeModelClass

Single-cell annotation using variational inference :cite:p:`Xu21`.

Inspired from M1 + M2 model, as described in (https://arxiv.org/pdf/1406.5298.pdf).

adata – AnnData object that has been registered via setup_anndata().

n_hidden – Number of nodes per hidden layer.

n_latent – Dimensionality of the latent space.

n_layers – Number of hidden layers used for encoder and decoder NNs.

dropout_rate – Dropout rate for neural networks.

dispersion – One of the following: 'gene' - dispersion parameter of NB is constant per gene across cells 'gene-batch' - dispersion can differ between different batches 'gene-label' - dispersion can differ between different labels 'gene-cell' - dispersion can differ for every gene in every cell

One of the following:

'gene' - dispersion parameter of NB is constant per gene across cells

'gene-batch' - dispersion can differ between different batches

'gene-label' - dispersion can differ between different labels

'gene-cell' - dispersion can differ for every gene in every cell

gene_likelihood – One of: 'nb' - Negative binomial distribution 'zinb' - Zero-inflated negative binomial distribution 'poisson' - Poisson distribution

'nb' - Negative binomial distribution

'zinb' - Zero-inflated negative binomial distribution

'poisson' - Poisson distribution

linear_classifier – If True, uses a single linear layer for classification instead of a multi-layer perceptron.

**model_kwargs – Keyword args for SCANVAE

See further usage examples in the following tutorials:

/tutorials/notebooks/scrna/harmonization

/tutorials/notebooks/scrna/scarches_scvi_tools

/tutorials/notebooks/scrna/seed_labeling

Data attached to model instance.

Manager instance associated with self.adata.

The current device that the module’s params are on.

Returns computed metrics during training.

Whether the model has been trained.

The type of minified data associated with this model, if applicable.

Summary string of the model.

Observations that are in test set.

Observations that are in train set.

Observations that are in validation set.

convert_legacy_save(dir_path, output_dir_path)

Converts a legacy saved model (<v0.15.0) to the updated save format.

deregister_manager([adata])

Deregisters the AnnDataManager instance associated with adata.

differential_expression([adata, groupby, ...])

A unified method for differential expression analysis.

from_scvi_model(scvi_model, unlabeled_category)

Initialize scanVI model with weights from pretrained SCVI model.

get_anndata_manager(adata[, required])

Retrieves the AnnDataManager for a given AnnData object.

get_elbo([adata, indices, batch_size])

Return the ELBO for the data.

get_feature_correlation_matrix([adata, ...])

Generate gene-gene correlation matrix using scvi uncertainty and expression.

get_from_registry(adata, registry_key)

Returns the object in AnnData associated with the key in the data registry.

get_latent_library_size([adata, indices, ...])

Returns the latent library size for each cell.

get_latent_representation([adata, indices, ...])

Return the latent representation for each cell.

get_likelihood_parameters([adata, indices, ...])

Estimates for the parameters of the likelihood \(p(x \mid z)\).

get_marginal_ll([adata, indices, ...])

Return the marginal LL for the data.

get_normalized_expression([adata, indices, ...])

Returns the normalized (decoded) gene expression.

get_reconstruction_error([adata, indices, ...])

Return the reconstruction error for the data.

load(dir_path[, adata, accelerator, device, ...])

Instantiate a model from the saved output.

load_query_data(adata, reference_model[, ...])

Online update of a reference model with scArches algorithm :cite:p:`Lotfollahi21`.

load_registry(dir_path[, prefix])

Return the full registry saved with the model.

minify_adata([minified_data_type, ...])

Minifies the model's adata.

posterior_predictive_sample([adata, ...])

Generate predictive samples from the posterior predictive distribution.

predict([adata, indices, soft, batch_size, ...])

Return cell label predictions.

prepare_query_anndata(adata, reference_model)

Prepare data for query integration.

register_manager(adata_manager)

Registers an AnnDataManager instance with this model class.

save(dir_path[, prefix, overwrite, ...])

Save the state of the model.

setup_anndata(adata, labels_key, ...[, ...])

Sets up the AnnData object for this model.

Move model to device.

train([max_epochs, n_samples_per_label, ...])

view_anndata_setup([adata, ...])

Print summary of the setup for the initial AnnData or a given AnnData object.

view_setup_args(dir_path[, prefix])

Print args used to setup a saved model.

Initialize scanVI model with weights from pretrained SCVI model.

scvi_model – Pretrained scvi model

labels_key – key in adata.obs for label information. Label categories can not be different if labels_key was used to setup the SCVI model. If None, uses the labels_key used to setup the SCVI model. If that was None, and error is raised.

unlabeled_category – Value used for unlabeled cells in labels_key used to setup AnnData with scvi.

adata – AnnData object that has been registered via setup_anndata().

scanvi_kwargs – kwargs for scANVI model

Minifies the model’s adata.

Minifies the adata, and registers new anndata fields: latent qzm, latent qzv, adata uns containing minified-adata type, and library size. This also sets the appropriate property on the module to indicate that the adata is minified.

minified_data_type – How to minify the data. Currently only supports latent_posterior_parameters. If minified_data_type == latent_posterior_parameters: the original count data is removed (adata.X, adata.raw, and any layers) the parameters of the latent representation of the original data is stored everything else is left untouched

How to minify the data. Currently only supports latent_posterior_parameters. If minified_data_type == latent_posterior_parameters:

the original count data is removed (adata.X, adata.raw, and any layers)

the parameters of the latent representation of the original data is stored

everything else is left untouched

use_latent_qzm_key – Key to use in adata.obsm where the latent qzm params are stored

use_latent_qzv_key – Key to use in adata.obsm where the latent qzv params are stored

The modification is not done inplace – instead the model is assigned a new (minified) version of the adata.

Return cell label predictions.

adata – AnnData object that has been registered via setup_anndata().

indices – Return probabilities for each class label.

soft – If True, returns per class probabilities

batch_size – Minibatch size for data loading into model. Defaults to scvi.settings.batch_size.

use_posterior_mean – If True, uses the mean of the posterior distribution to predict celltype labels. Otherwise, uses a sample from the posterior distribution - this means that the predictions will be stochastic.

Sets up the AnnData object for this model.

A mapping will be created between data fields used by this model to their respective locations in adata. None of the data in adata are modified. Only adds fields to adata.

adata – AnnData object. Rows represent cells, columns represent features.

labels_key – key in adata.obs for label information. Categories will automatically be converted into integer categories and saved to adata.obs[‘_scvi_labels’]. If None, assigns the same label to all the data.

unlabeled_category – value in adata.obs[labels_key] that indicates unlabeled observations.

layer – if not None, uses this as the key in adata.layers for raw count data.

batch_key – key in adata.obs for batch information. Categories will automatically be converted into integer categories and saved to adata.obs[‘_scvi_batch’]. If None, assigns the same batch to all the data.

size_factor_key – key in adata.obs for size factor information. Instead of using library size as a size factor, the provided size factor column will be used as offset in the mean of the likelihood. Assumed to be on linear scale.

categorical_covariate_keys – keys in adata.obs that correspond to categorical data. These covariates can be added in addition to the batch covariate and are also treated as nuisance factors (i.e., the model tries to minimize their effects on the latent space). Thus, these should not be used for biologically-relevant factors that you do _not_ want to correct for.

continuous_covariate_keys – keys in adata.obs that correspond to continuous data. These covariates can be added in addition to the batch covariate and are also treated as nuisance factors (i.e., the model tries to minimize their effects on the latent space). Thus, these should not be used for biologically-relevant factors that you do _not_ want to correct for.

max_epochs – Number of passes through the dataset for semisupervised training.

n_samples_per_label – Number of subsamples for each label class to sample per epoch. By default, there is no label subsampling.

check_val_every_n_epoch – Frequency with which metrics are computed on the data for validation set for both the unsupervised and semisupervised trainers. If you’d like a different frequency for the semisupervised trainer, set check_val_every_n_epoch in semisupervised_train_kwargs.

train_size – Size of training set in the range [0.0, 1.0].

validation_size – Size of the test set. If None, defaults to 1 - train_size. If train_size + validation_size < 1, the remaining cells belong to a test set.

shuffle_set_split – Whether to shuffle indices before splitting. If False, the val, train, and test set are split in the sequential order of the data according to validation_size and train_size percentages.

batch_size – Minibatch size to use during training.

accelerator – Supports passing different accelerator types (“cpu”, “gpu”, “tpu”, “ipu”, “hpu”, “mps, “auto”) as well as custom accelerator instances.

devices – The devices to use. Can be set to a non-negative index (int or str), a sequence of device indices (list or comma-separated str), the value -1 to indicate all available devices, or “auto” for automatic selection based on the chosen accelerator. If set to “auto” and accelerator is not determined to be “cpu”, then devices will be set to the first available device.

datasplitter_kwargs – Additional keyword arguments passed into SemiSupervisedDataSplitter.

plan_kwargs – Keyword args for SemiSupervisedTrainingPlan. Keyword arguments passed to train() will overwrite values present in plan_kwargs, when appropriate.

**trainer_kwargs – Other keyword args for Trainer.

Bases: RNASeqMixin, VAEMixin, ArchesMixin, BaseModelClass

total Variational Inference :cite:p:`GayosoSteier21`.

adata – AnnData object that has been registered via setup_anndata().

n_latent – Dimensionality of the latent space.

gene_dispersion – One of the following: 'gene' - genes_dispersion parameter of NB is constant per gene across cells 'gene-batch' - genes_dispersion can differ between different batches 'gene-label' - genes_dispersion can differ between different labels

One of the following:

'gene' - genes_dispersion parameter of NB is constant per gene across cells

'gene-batch' - genes_dispersion can differ between different batches

'gene-label' - genes_dispersion can differ between different labels

protein_dispersion – One of the following: 'protein' - protein_dispersion parameter is constant per protein across cells 'protein-batch' - protein_dispersion can differ between different batches NOT TESTED 'protein-label' - protein_dispersion can differ between different labels NOT TESTED

One of the following:

'protein' - protein_dispersion parameter is constant per protein across cells

'protein-batch' - protein_dispersion can differ between different batches NOT TESTED

'protein-label' - protein_dispersion can differ between different labels NOT TESTED

gene_likelihood – One of: 'nb' - Negative binomial distribution 'zinb' - Zero-inflated negative binomial distribution

'nb' - Negative binomial distribution

'zinb' - Zero-inflated negative binomial distribution

latent_distribution – One of: 'normal' - Normal distribution 'ln' - Logistic normal distribution (Normal(0, I) transformed by softmax)

'normal' - Normal distribution

'ln' - Logistic normal distribution (Normal(0, I) transformed by softmax)

empirical_protein_background_prior – Set the initialization of protein background prior empirically. This option fits a GMM for each of 100 cells per batch and averages the distributions. Note that even with this option set to True, this only initializes a parameter that is learned during inference. If False, randomly initializes. The default (None), sets this to True if greater than 10 proteins are used.

override_missing_proteins – If True, will not treat proteins with all 0 expression in a particular batch as missing.

**model_kwargs – Keyword args for TOTALVAE

See further usage examples in the following tutorials:

/tutorials/notebooks/multimodal/totalVI

/tutorials/notebooks/multimodal/cite_scrna_integration_w_totalVI

/tutorials/notebooks/scrna/scarches_scvi_tools

Data attached to model instance.

Manager instance associated with self.adata.

The current device that the module’s params are on.

Returns computed metrics during training.

Whether the model has been trained.

Summary string of the model.

Observations that are in test set.

Observations that are in train set.

Observations that are in validation set.

convert_legacy_save(dir_path, output_dir_path)

Converts a legacy saved model (<v0.15.0) to the updated save format.

deregister_manager([adata])

Deregisters the AnnDataManager instance associated with adata.

differential_expression([adata, groupby, ...])

A unified method for differential expression analysis.

get_anndata_manager(adata[, required])

Retrieves the AnnDataManager for a given AnnData object.

get_elbo([adata, indices, batch_size])

Return the ELBO for the data.

get_feature_correlation_matrix([adata, ...])

Generate gene-gene correlation matrix using scvi uncertainty and expression.

get_from_registry(adata, registry_key)

Returns the object in AnnData associated with the key in the data registry.

get_latent_library_size([adata, indices, ...])

Returns the latent library size for each cell.

get_latent_representation([adata, indices, ...])

Return the latent representation for each cell.

get_likelihood_parameters([adata, indices, ...])

Estimates for the parameters of the likelihood \(p(x, y \mid z)\).

get_marginal_ll([adata, indices, ...])

Return the marginal LL for the data.

get_normalized_expression([adata, indices, ...])

Returns the normalized gene expression and protein expression.

get_protein_background_mean(adata, indices, ...)

Get protein background mean.

get_protein_foreground_probability([adata, ...])

Returns the foreground probability for proteins.

get_reconstruction_error([adata, indices, ...])

Return the reconstruction error for the data.

load(dir_path[, adata, accelerator, device, ...])

Instantiate a model from the saved output.

load_query_data(adata, reference_model[, ...])

Online update of a reference model with scArches algorithm :cite:p:`Lotfollahi21`.

load_registry(dir_path[, prefix])

Return the full registry saved with the model.

posterior_predictive_sample([adata, ...])

Generate observation samples from the posterior predictive distribution.

prepare_query_anndata(adata, reference_model)

Prepare data for query integration.

register_manager(adata_manager)

Registers an AnnDataManager instance with this model class.

save(dir_path[, prefix, overwrite, ...])

Save the state of the model.

setup_anndata(adata, protein_expression_obsm_key)

Sets up the AnnData object for this model.

setup_mudata(mdata[, rna_layer, ...])

Sets up the MuData object for this model.

Move model to device.

train([max_epochs, lr, accelerator, ...])

Trains the model using amortized variational inference.

view_anndata_setup([adata, ...])

Print summary of the setup for the initial AnnData or a given AnnData object.

view_setup_args(dir_path[, prefix])

Print args used to setup a saved model.

A unified method for differential expression analysis.

Implements “vanilla” DE :cite:p:`Lopez18`. and “change” mode DE :cite:p:`Boyeau19`.

adata – AnnData object with equivalent structure to initial AnnData. If None, defaults to the AnnData object used to initialize the model.

groupby – The key of the observations grouping to consider.

group1 – Subset of groups, e.g. [‘g1’, ‘g2’, ‘g3’], to which comparison shall be restricted, or all groups in groupby (default).

group2 – If None, compare each group in group1 to the union of the rest of the groups in groupby. If a group identifier, compare with respect to this group.

idx1 – idx1 and idx2 can be used as an alternative to the AnnData keys. Custom identifier for group1 that can be of three sorts: (1) a boolean mask, (2) indices, or (3) a string. If it is a string, then it will query indices that verifies conditions on adata.obs, as described in pandas.DataFrame.query() If idx1 is not None, this option overrides group1 and group2.

idx2 – Custom identifier for group2 that has the same properties as idx1. By default, includes all cells not specified in idx1.

mode – Method for differential expression. See user guide for full explanation.

delta – specific case of region inducing differential expression. In this case, we suppose that \(R \setminus [-\delta, \delta]\) does not induce differential expression (change model default case).

batch_size – Minibatch size for data loading into model. Defaults to scvi.settings.batch_size.

all_stats – Concatenate count statistics (e.g., mean expression group 1) to DE results.

batch_correction – Whether to correct for batch effects in DE inference.

batchid1 – Subset of categories from batch_key registered in setup_anndata, e.g. [‘batch1’, ‘batch2’, ‘batch3’], for group1. Only used if batch_correction is True, and by default all categories are used.

batchid2 – Same as batchid1 for group2. batchid2 must either have null intersection with batchid1, or be exactly equal to batchid1. When the two sets are exactly equal, cells are compared by decoding on the same batch. When sets have null intersection, cells from group1 and group2 are decoded on each group in group1 and group2, respectively.

fdr_target – Tag features as DE based on posterior expected false discovery rate.

silent – If True, disables the progress bar. Default: False.

protein_prior_count – Prior count added to protein expression before LFC computation

scale_protein – Force protein values to sum to one in every single cell (post-hoc normalization)

sample_protein_mixing – Sample the protein mixture component, i.e., use the parameter to sample a Bernoulli that determines if expression is from foreground/background.

include_protein_background – Include the protein background component as part of the protein expression

**kwargs – Keyword args for scvi.model.base.DifferentialComputation.get_bayes_factors()

Differential expression DataFrame.

Generate gene-gene correlation matrix using scvi uncertainty and expression.

adata – AnnData object with equivalent structure to initial AnnData. If None, defaults to the AnnData object used to initialize the model.

indices – Indices of cells in adata to use. If None, all cells are used.

n_samples – Number of posterior samples to use for estimation.

batch_size – Minibatch size for data loading into model. Defaults to scvi.settings.batch_size.

rna_size_factor – size factor for RNA prior to sampling gamma distribution

transform_batch – Batches to condition on. If transform_batch is: None, then real observed batch is used int, then batch transform_batch is used list of int, then values are averaged over provided batches.

Batches to condition on. If transform_batch is:

None, then real observed batch is used

int, then batch transform_batch is used

list of int, then values are averaged over provided batches.

correlation_type – One of “pearson”, “spearman”.

log_transform – Whether to log transform denoised values prior to correlation calculation.

Gene-protein-gene-protein correlation matrix

Returns the latent library size for each cell.

This is denoted as \(\ell_n\) in the totalVI paper.

adata – AnnData object with equivalent structure to initial AnnData. If None, defaults to the AnnData object used to initialize the model.

indices – Indices of cells in adata to use. If None, all cells are used.

give_mean – Return the mean or a sample from the posterior distribution.

batch_size – Minibatch size for data loading into model. Defaults to scvi.settings.batch_size.

Estimates for the parameters of the likelihood \(p(x, y \mid z)\).

adata – AnnData object with equivalent structure to initial AnnData. If None, defaults to the AnnData object used to initialize the model.

indices – Indices of cells in adata to use. If None, all cells are used.

n_samples – Number of posterior samples to use for estimation.

give_mean – Return expected value of parameters or a samples

batch_size – Minibatch size for data loading into model. Defaults to scvi.settings.batch_size.

Returns the normalized gene expression and protein expression.

This is denoted as \(\rho_n\) in the totalVI paper for genes, and TODO for proteins, \((1-\pi_{nt})\alpha_{nt}\beta_{nt}\).

adata – AnnData object with equivalent structure to initial AnnData. If None, defaults to the AnnData object used to initialize the model.

indices – Indices of cells in adata to use. If None, all cells are used.

n_samples_overall – Number of samples to use in total

transform_batch – Batch to condition on. If transform_batch is: None, then real observed batch is used int, then batch transform_batch is used List[int], then average over batches in list

Batch to condition on. If transform_batch is:

None, then real observed batch is used

int, then batch transform_batch is used

List[int], then average over batches in list

gene_list – Return frequencies of expression for a subset of genes. This can save memory when working with large datasets and few genes are of interest.

protein_list – Return protein expression for a subset of genes. This can save memory when working with large datasets and few genes are of interest.

library_size – Scale the expression frequencies to a common library size. This allows gene expression levels to be interpreted on a common scale of relevant magnitude.

n_samples – Get sample scale from multiple samples.

sample_protein_mixing – Sample mixing bernoulli, setting background to zero

scale_protein – Make protein expression sum to 1

include_protein_background – Include background component for protein expression

batch_size – Minibatch size for data loading into model. Defaults to scvi.settings.batch_size.

return_mean – Whether to return the mean of the samples.

return_numpy – Return a np.ndarray instead of a pd.DataFrame. Includes gene names as columns. If either n_samples=1 or return_mean=True, defaults to False. Otherwise, it defaults to True.

- **gene_normalized_expression* - normalized expression for RNA* - **protein_normalized_expression* - normalized expression for proteins* If n_samples > 1 and return_mean is False, then the shape is (samples, cells, genes). Otherwise, shape is (cells, genes). Return type is pd.DataFrame unless return_numpy is True.

- **gene_normalized_expression* - normalized expression for RNA*

- **protein_normalized_expression* - normalized expression for proteins*

If n_samples > 1 and return_mean is False, then the shape is

(samples, cells, genes). Otherwise, shape is (cells, genes). Return type is

pd.DataFrame unless return_numpy is True.

Get protein background mean.

Returns the foreground probability for proteins.

This is denoted as \((1 - \pi_{nt})\) in the totalVI paper.

adata – AnnData object with equivalent structure to initial AnnData. If None, defaults to the AnnData object used to initialize the model.

indices – Indices of cells in adata to use. If None, all cells are used.

transform_batch – Batch to condition on. If transform_batch is: None, then real observed batch is used int, then batch transform_batch is used List[int], then average over batches in list

Batch to condition on. If transform_batch is:

None, then real observed batch is used

int, then batch transform_batch is used

List[int], then average over batches in list

protein_list – Return protein expression for a subset of genes. This can save memory when working with large datasets and few genes are of interest.

n_samples – Number of posterior samples to use for estimation.

batch_size – Minibatch size for data loading into model. Defaults to scvi.settings.batch_size.

return_mean – Whether to return the mean of the samples.

return_numpy – Return a ndarray instead of a DataFrame. DataFrame includes gene names as columns. If either n_samples=1 or return_mean=True, defaults to False. Otherwise, it defaults to True.

- **foreground_probability* - probability foreground for each protein* If n_samples > 1 and return_mean is False, then the shape is (samples, cells, genes). Otherwise, shape is (cells, genes). In this case, return type is DataFrame unless return_numpy is True.

- **foreground_probability* - probability foreground for each protein*

If n_samples > 1 and return_mean is False, then the shape is (samples, cells, genes).

Otherwise, shape is (cells, genes). In this case, return type is

DataFrame unless return_numpy is True.

Generate observation samples from the posterior predictive distribution.

The posterior predictive distribution is written as \(p(\hat{x}, \hat{y} \mid x, y)\).

adata – AnnData object with equivalent structure to initial AnnData. If None, defaults to the AnnData object used to initialize the model.

indices – Indices of cells in adata to use. If None, all cells are used.

n_samples – Number of required samples for each cell

batch_size – Minibatch size for data loading into model. Defaults to scvi.settings.batch_size.

gene_list – Names of genes of interest

protein_list – Names of proteins of interest

x_new – tensor with shape (n_cells, n_genes, n_samples)

Sets up the AnnData object for this model.

A mapping will be created between data fields used by this model to their respective locations in adata. None of the data in adata are modified. Only adds fields to adata.

adata – AnnData object. Rows represent cells, columns represent features.

protein_expression_obsm_key – key in adata.obsm for protein expression data.

protein_names_uns_key – key in adata.uns for protein names. If None, will use the column names of adata.obsm[protein_expression_obsm_key] if it is a DataFrame, else will assign sequential names to proteins.

batch_key – key in adata.obs for batch information. Categories will automatically be converted into integer categories and saved to adata.obs[‘_scvi_batch’]. If None, assigns the same batch to all the data.

layer – if not None, uses this as the key in adata.layers for raw count data.

size_factor_key – key in adata.obs for size factor information. Instead of using library size as a size factor, the provided size factor column will be used as offset in the mean of the likelihood. Assumed to be on linear scale.

categorical_covariate_keys – keys in adata.obs that correspond to categorical data. These covariates can be added in addition to the batch covariate and are also treated as nuisance factors (i.e., the model tries to minimize their effects on the latent space). Thus, these should not be used for biologically-relevant factors that you do _not_ want to correct for.

continuous_covariate_keys – keys in adata.obs that correspond to continuous data. These covariates can be added in addition to the batch covariate and are also treated as nuisance factors (i.e., the model tries to minimize their effects on the latent space). Thus, these should not be used for biologically-relevant factors that you do _not_ want to correct for.

None. Adds the following fields .uns[‘_scvi’] – scvi setup dictionary .obs[‘_scvi_labels’] – labels encoded as integers .obs[‘_scvi_batch’] – batch encoded as integers

None. Adds the following fields

.uns[‘_scvi’] – scvi setup dictionary

.obs[‘_scvi_labels’] – labels encoded as integers

.obs[‘_scvi_batch’] – batch encoded as integers

Sets up the MuData object for this model.

A mapping will be created between data fields used by this model to their respective locations in adata. None of the data in adata are modified. Only adds fields to adata.

mdata – MuData object. Rows represent cells, columns represent features.

rna_layer – RNA layer key. If None, will use .X of specified modality key.

protein_layer – Protein layer key. If None, will use .X of specified modality key.

batch_key – key in adata.obs for batch information. Categories will automatically be converted into integer categories and saved to adata.obs[‘_scvi_batch’]. If None, assigns the same batch to all the data.

size_factor_key – key in adata.obs for size factor information. Instead of using library size as a size factor, the provided size factor column will be used as offset in the mean of the likelihood. Assumed to be on linear scale.

categorical_covariate_keys – keys in adata.obs that correspond to categorical data. These covariates can be added in addition to the batch covariate and are also treated as nuisance factors (i.e., the model tries to minimize their effects on the latent space). Thus, these should not be used for biologically-relevant factors that you do _not_ want to correct for.

continuous_covariate_keys – keys in adata.obs that correspond to continuous data. These covariates can be added in addition to the batch covariate and are also treated as nuisance factors (i.e., the model tries to minimize their effects on the latent space). Thus, these should not be used for biologically-relevant factors that you do _not_ want to correct for.

modalities – Dictionary mapping parameters to modalities.

Trains the model using amortized variational inference.

max_epochs – Number of passes through the dataset.

lr – Learning rate for optimization.

accelerator – Supports passing different accelerator types (“cpu”, “gpu”, “tpu”, “ipu”, “hpu”, “mps, “auto”) as well as custom accelerator instances.

devices – The devices to use. Can be set to a non-negative index (int or str), a sequence of device indices (list or comma-separated str), the value -1 to indicate all available devices, or “auto” for automatic selection based on the chosen accelerator. If set to “auto” and accelerator is not determined to be “cpu”, then devices will be set to the first available device.

train_size – Size of training set in the range [0.0, 1.0].

validation_size – Size of the test set. If None, defaults to 1 - train_size. If train_size + validation_size < 1, the remaining cells belong to a test set.

shuffle_set_split – Whether to shuffle indices before splitting. If False, the val, train, and test set are split in the sequential order of the data according to validation_size and train_size percentages.

batch_size – Minibatch size to use during training.

early_stopping – Whether to perform early stopping with respect to the validation set.

check_val_every_n_epoch – Check val every n train epochs. By default, val is not checked, unless early_stopping is True or reduce_lr_on_plateau is True. If either of the latter conditions are met, val is checked every epoch.

reduce_lr_on_plateau – Reduce learning rate on plateau of validation metric (default is ELBO).

n_steps_kl_warmup – Number of training steps (minibatches) to scale weight on KL divergences from 0 to 1. Only activated when n_epochs_kl_warmup is set to None. If None, defaults to floor(0.75 * adata.n_obs).

n_epochs_kl_warmup – Number of epochs to scale weight on KL divergences from 0 to 1. Overrides n_steps_kl_warmup when both are not None.

adversarial_classifier – Whether to use adversarial classifier in the latent space. This helps mixing when there are missing proteins in any of the batches. Defaults to True is missing proteins are detected.

datasplitter_kwargs – Additional keyword arguments passed into DataSplitter.

plan_kwargs – Keyword args for AdversarialTrainingPlan. Keyword arguments passed to train() will overwrite values present in plan_kwargs, when appropriate.

**kwargs – Other keyword args for Trainer.

**Examples:**

Example 1 (unknown):
```unknown
SurgeryMixin
```

Example 2 (unknown):
```unknown
CVAELatentsMixin
```

Example 3 (unknown):
```unknown
load_query_data
```

Example 4 (unknown):
```unknown
SurgeryMixin
```

Example 5 (unknown):
```unknown
CVAELatentsMixin
```

Example 6 (unknown):
```unknown
latent_directions
```

Example 7 (unknown):
```unknown
latent_enrich
```

Example 8 (unknown):
```unknown
load_query_data
```

Example 9 (unknown):
```unknown
nonzero_terms
```

Example 10 (unknown):
```unknown
update_terms
```

Example 11 (unknown):
```unknown
add_new_cell_type
```

Example 12 (unknown):
```unknown
get_conditional_embeddings
```

Example 13 (unknown):
```unknown
get_prototypes_info
```

Example 14 (unknown):
```unknown
load_query_data
```

Example 15 (unknown):
```unknown
RNASeqMixin
```

Example 16 (unknown):
```unknown
ArchesMixin
```

Example 17 (unknown):
```unknown
UnsupervisedTrainingMixin
```

Example 18 (unknown):
```unknown
BaseMinifiedModeModelClass
```

Example 19 (unknown):
```unknown
setup_anndata()
```

Example 20 (unknown):
```unknown
LightningDataModule
```

Example 21 (unknown):
```unknown
EXPERIMENTAL
```

Example 22 (unknown):
```unknown
'gene-batch'
```

Example 23 (unknown):
```unknown
'gene-label'
```

Example 24 (unknown):
```unknown
'gene-cell'
```

Example 25 (python):
```python
>>> adata = anndata.read_h5ad(path_to_anndata)
>>> scvi.model.SCVI.setup_anndata(adata, batch_key="batch")
>>> vae = scvi.model.SCVI(adata)
>>> vae.train()
>>> adata.obsm["X_scVI"] = vae.get_latent_representation()
>>> adata.obsm["X_normalized_scVI"] = vae.get_normalized_expression()
```

Example 26 (python):
```python
adata_manager
```

Example 27 (unknown):
```unknown
minified_data_type
```

Example 28 (unknown):
```unknown
summary_string
```

Example 29 (unknown):
```unknown
test_indices
```

Example 30 (unknown):
```unknown
train_indices
```

Example 31 (unknown):
```unknown
validation_indices
```

Example 32 (unknown):
```unknown
convert_legacy_save
```

Example 33 (unknown):
```unknown
deregister_manager
```

Example 34 (unknown):
```unknown
AnnDataManager
```

Example 35 (unknown):
```unknown
differential_expression
```

Example 36 (unknown):
```unknown
get_anndata_manager
```

Example 37 (unknown):
```unknown
AnnDataManager
```

Example 38 (unknown):
```unknown
get_feature_correlation_matrix
```

Example 39 (unknown):
```unknown
get_from_registry
```

Example 40 (unknown):
```unknown
get_latent_library_size
```

Example 41 (unknown):
```unknown
get_latent_representation
```

Example 42 (unknown):
```unknown
get_likelihood_parameters
```

Example 43 (unknown):
```unknown
get_marginal_ll
```

Example 44 (unknown):
```unknown
get_normalized_expression
```

Example 45 (unknown):
```unknown
get_reconstruction_error
```

Example 46 (unknown):
```unknown
load_query_data
```

Example 47 (unknown):
```unknown
load_registry
```

Example 48 (python):
```python
minify_adata
```

Example 49 (unknown):
```unknown
posterior_predictive_sample
```

Example 50 (unknown):
```unknown
prepare_query_anndata
```

Example 51 (unknown):
```unknown
register_manager
```

Example 52 (unknown):
```unknown
AnnDataManager
```

Example 53 (unknown):
```unknown
setup_anndata
```

Example 54 (unknown):
```unknown
view_anndata_setup
```

Example 55 (unknown):
```unknown
view_setup_args
```

Example 56 (unknown):
```unknown
RNASeqMixin
```

Example 57 (unknown):
```unknown
ArchesMixin
```

Example 58 (unknown):
```unknown
BaseMinifiedModeModelClass
```

Example 59 (unknown):
```unknown
setup_anndata()
```

Example 60 (unknown):
```unknown
'gene-batch'
```

Example 61 (unknown):
```unknown
'gene-label'
```

Example 62 (unknown):
```unknown
'gene-cell'
```

Example 63 (python):
```python
>>> adata = anndata.read_h5ad(path_to_anndata)
>>> scvi.model.SCANVI.setup_anndata(adata, batch_key="batch", labels_key="labels")
>>> vae = scvi.model.SCANVI(adata, "Unknown")
>>> vae.train()
>>> adata.obsm["X_scVI"] = vae.get_latent_representation()
>>> adata.obs["pred_label"] = vae.predict()
```

Example 64 (python):
```python
adata_manager
```

Example 65 (unknown):
```unknown
minified_data_type
```

Example 66 (unknown):
```unknown
summary_string
```

Example 67 (unknown):
```unknown
test_indices
```

Example 68 (unknown):
```unknown
train_indices
```

Example 69 (unknown):
```unknown
validation_indices
```

Example 70 (unknown):
```unknown
convert_legacy_save
```

Example 71 (unknown):
```unknown
deregister_manager
```

Example 72 (unknown):
```unknown
AnnDataManager
```

Example 73 (unknown):
```unknown
differential_expression
```

Example 74 (unknown):
```unknown
from_scvi_model
```

Example 75 (unknown):
```unknown
get_anndata_manager
```

Example 76 (unknown):
```unknown
AnnDataManager
```

Example 77 (unknown):
```unknown
get_feature_correlation_matrix
```

Example 78 (unknown):
```unknown
get_from_registry
```

Example 79 (unknown):
```unknown
get_latent_library_size
```

Example 80 (unknown):
```unknown
get_latent_representation
```

Example 81 (unknown):
```unknown
get_likelihood_parameters
```

Example 82 (unknown):
```unknown
get_marginal_ll
```

Example 83 (unknown):
```unknown
get_normalized_expression
```

Example 84 (unknown):
```unknown
get_reconstruction_error
```

Example 85 (unknown):
```unknown
load_query_data
```

Example 86 (unknown):
```unknown
load_registry
```

Example 87 (python):
```python
minify_adata
```

Example 88 (unknown):
```unknown
posterior_predictive_sample
```

Example 89 (unknown):
```unknown
prepare_query_anndata
```

Example 90 (unknown):
```unknown
register_manager
```

Example 91 (unknown):
```unknown
AnnDataManager
```

Example 92 (unknown):
```unknown
setup_anndata
```

Example 93 (unknown):
```unknown
view_anndata_setup
```

Example 94 (unknown):
```unknown
view_setup_args
```

Example 95 (unknown):
```unknown
setup_anndata()
```

Example 96 (unknown):
```unknown
setup_anndata()
```

Example 97 (unknown):
```unknown
SemiSupervisedDataSplitter
```

Example 98 (unknown):
```unknown
SemiSupervisedTrainingPlan
```

Example 99 (unknown):
```unknown
RNASeqMixin
```

Example 100 (unknown):
```unknown
ArchesMixin
```

Example 101 (unknown):
```unknown
BaseModelClass
```

Example 102 (unknown):
```unknown
setup_anndata()
```

Example 103 (unknown):
```unknown
'gene-batch'
```

Example 104 (unknown):
```unknown
'gene-label'
```

Example 105 (unknown):
```unknown
'protein-batch'
```

Example 106 (unknown):
```unknown
'protein-label'
```

Example 107 (python):
```python
>>> adata = anndata.read_h5ad(path_to_anndata)
>>> scvi.model.TOTALVI.setup_anndata(
        adata, batch_key="batch", protein_expression_obsm_key="protein_expression"
    )
>>> vae = scvi.model.TOTALVI(adata)
>>> vae.train()
>>> adata.obsm["X_totalVI"] = vae.get_latent_representation()
```

Example 108 (python):
```python
adata_manager
```

Example 109 (unknown):
```unknown
summary_string
```

Example 110 (unknown):
```unknown
test_indices
```

Example 111 (unknown):
```unknown
train_indices
```

Example 112 (unknown):
```unknown
validation_indices
```

Example 113 (unknown):
```unknown
convert_legacy_save
```

Example 114 (unknown):
```unknown
deregister_manager
```

Example 115 (unknown):
```unknown
AnnDataManager
```

Example 116 (unknown):
```unknown
differential_expression
```

Example 117 (unknown):
```unknown
get_anndata_manager
```

Example 118 (unknown):
```unknown
AnnDataManager
```

Example 119 (unknown):
```unknown
get_feature_correlation_matrix
```

Example 120 (unknown):
```unknown
get_from_registry
```

Example 121 (unknown):
```unknown
get_latent_library_size
```

Example 122 (unknown):
```unknown
get_latent_representation
```

Example 123 (unknown):
```unknown
get_likelihood_parameters
```

Example 124 (unknown):
```unknown
get_marginal_ll
```

Example 125 (unknown):
```unknown
get_normalized_expression
```

Example 126 (unknown):
```unknown
get_protein_background_mean
```

Example 127 (unknown):
```unknown
get_protein_foreground_probability
```

Example 128 (unknown):
```unknown
get_reconstruction_error
```

Example 129 (unknown):
```unknown
load_query_data
```

Example 130 (unknown):
```unknown
load_registry
```

Example 131 (unknown):
```unknown
posterior_predictive_sample
```

Example 132 (unknown):
```unknown
prepare_query_anndata
```

Example 133 (unknown):
```unknown
register_manager
```

Example 134 (unknown):
```unknown
AnnDataManager
```

Example 135 (unknown):
```unknown
setup_anndata
```

Example 136 (unknown):
```unknown
setup_mudata
```

Example 137 (unknown):
```unknown
view_anndata_setup
```

Example 138 (unknown):
```unknown
view_setup_args
```

Example 139 (unknown):
```unknown
pandas.DataFrame.query()
```

Example 140 (unknown):
```unknown
setup_anndata
```

Example 141 (unknown):
```unknown
scvi.model.base.DifferentialComputation.get_bayes_factors()
```

Example 142 (unknown):
```unknown
return_mean
```

Example 143 (unknown):
```unknown
(samples, cells, genes)
```

Example 144 (unknown):
```unknown
(cells, genes)
```

Example 145 (python):
```python
pd.DataFrame
```

Example 146 (unknown):
```unknown
return_numpy
```

Example 147 (unknown):
```unknown
>>> mdata = muon.read_10x_h5("pbmc_10k_protein_v3_filtered_feature_bc_matrix.h5")
>>> scvi.model.TOTALVI.setup_mudata(
        mdata, modalities={"rna_layer": "rna": "protein_layer": "prot"}
    )
>>> vae = scvi.model.TOTALVI(mdata)
```

Example 148 (unknown):
```unknown
DataSplitter
```

Example 149 (unknown):
```unknown
AdversarialTrainingPlan
```

Example 150 (unknown):
```unknown
TRVAE.train()
```

Example 151 (unknown):
```unknown
EXPIMAP.get_latent()
```

Example 152 (unknown):
```unknown
EXPIMAP.latent_directions()
```

Example 153 (unknown):
```unknown
EXPIMAP.latent_enrich()
```

Example 154 (unknown):
```unknown
EXPIMAP.load_query_data()
```

Example 155 (unknown):
```unknown
EXPIMAP.mask_genes()
```

Example 156 (unknown):
```unknown
EXPIMAP.nonzero_terms()
```

Example 157 (unknown):
```unknown
EXPIMAP.term_genes()
```

Example 158 (unknown):
```unknown
EXPIMAP.train()
```

Example 159 (unknown):
```unknown
EXPIMAP.update_terms()
```

Example 160 (unknown):
```unknown
scPoli.add_new_cell_type()
```

Example 161 (unknown):
```unknown
scPoli.classify()
```

Example 162 (unknown):
```unknown
scPoli.get_conditional_embeddings()
```

Example 163 (unknown):
```unknown
scPoli.get_latent()
```

Example 164 (unknown):
```unknown
scPoli.get_prototypes_info()
```

Example 165 (unknown):
```unknown
scPoli.get_recon_loss()
```

Example 166 (unknown):
```unknown
scPoli.load_query_data()
```

Example 167 (unknown):
```unknown
scPoli.shot_surgery()
```

Example 168 (unknown):
```unknown
scPoli.train()
```

Example 169 (python):
```python
SCVI.minify_adata()
```

Example 170 (unknown):
```unknown
SCVI.setup_anndata()
```

Example 171 (unknown):
```unknown
SCANVI.from_scvi_model()
```

Example 172 (python):
```python
SCANVI.minify_adata()
```

Example 173 (unknown):
```unknown
SCANVI.predict()
```

Example 174 (unknown):
```unknown
SCANVI.setup_anndata()
```

Example 175 (unknown):
```unknown
SCANVI.train()
```

Example 176 (unknown):
```unknown
TOTALVI.differential_expression()
```

Example 177 (unknown):
```unknown
TOTALVI.get_feature_correlation_matrix()
```

Example 178 (unknown):
```unknown
TOTALVI.get_latent_library_size()
```

Example 179 (unknown):
```unknown
TOTALVI.get_likelihood_parameters()
```

Example 180 (unknown):
```unknown
TOTALVI.get_normalized_expression()
```

Example 181 (unknown):
```unknown
TOTALVI.get_protein_background_mean()
```

Example 182 (unknown):
```unknown
TOTALVI.get_protein_foreground_probability()
```

Example 183 (unknown):
```unknown
TOTALVI.posterior_predictive_sample()
```

Example 184 (unknown):
```unknown
TOTALVI.setup_anndata()
```

Example 185 (unknown):
```unknown
TOTALVI.setup_mudata()
```

Example 186 (unknown):
```unknown
TOTALVI.train()
```

---

## Semi-supervised surgery pipeline with SCANVI - scArches documentation

**URL:** http://127.0.0.1:9180/en/latest/scanvi_surgery_pipeline.html

**Contents:**
- Semi-supervised surgery pipeline with SCANVI
- Set relevant anndata.obs labels and training length
- Download Dataset and split into reference dataset and query dataset
- Create SCANVI model and train it on fully labelled reference dataset
- Create anndata file of latent representation and compute UMAP
- Perform surgery on reference model and train on query dataset without cell type labels
- Compute Accuracy of model classifier for query dataset and compare predicted and observed cell types
- Get latent representation of reference + query dataset and compute UMAP
- Comparison of observed and predicted celltypes for reference + query dataset

Here we use the CelSeq2 and SS2 studies as query data and the other 3 studies as reference atlas.

This line makes sure that count data is in the adata.X. Remember that count data in adata.X is necessary when using “nb” or “zinb” loss.

Preprocess reference dataset. Remember that the adata file has to have count data in adata.X for SCVI/SCANVI if not further specified

Create the SCANVI model instance with ZINB loss as default. Insert “gene_likelihood=’nb’,” to change the reconstruction loss to NB loss.

One can also compute the accuracy of the learned classifier

After pretraining the model can be saved for later use

If the cell types in ‘target_adata’ are equal to or a subset of the reference data cell types, one can just pass the adata without further preprocessing. It is also possible then to do semi-supervised training with scArches.

However if there are new cell types in ‘target_adata’ or if there is no ‘.obs’ in the anndata for cell type labels (e.g. the data is unlabeled), one can only use scANVI in an unsupervised manner during surgery due to the nature of the classifier.

In addition one has to preprocess ‘target_adata’ in the following way:

If there are new celltypes in there, save the original labels in other column and replace all labels with unlabeled category:

If there is no ‘.obs’ column for cell types:

If ‘target_adata’ is in the right format, one can proceed with the surgery pipeline. Here we do the surgery unsupervised, but due to the overlapping cell types in query and reference data, one could also do supervised or semi-supervised surgery by setting the indices accordingly.

**Examples:**

Example 1 (python):
```python
try:
    from nbproject import header
    header()
except ModuleNotFoundError:
    print("If you want to see the header with dependencies, please install nbproject - pip install nbproject")
```

Example 2 (python):
```python
import os
os.chdir('../')
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)
warnings.simplefilter(action='ignore', category=UserWarning)
```

Example 3 (python):
```python
import scanpy as sc
import torch
import scarches as sca
from scarches.dataset.trvae.data_handling import remove_sparsity
import matplotlib.pyplot as plt
import numpy as np
import gdown
```

Example 4 (unknown):
```unknown
Global seed set to 0
```

Example 5 (python):
```python
sc.settings.set_figure_params(dpi=200, frameon=False)
sc.set_figure_params(dpi=200)
sc.set_figure_params(figsize=(4, 4))
torch.set_printoptions(precision=3, sci_mode=False, edgeitems=7)
```

Example 6 (unknown):
```unknown
condition_key = 'study'
cell_type_key = 'cell_type'
target_conditions = ['Pancreas CelSeq2', 'Pancreas SS2']
```

Example 7 (unknown):
```unknown
url = 'https://drive.google.com/uc?id=1ehxgfHTsMZXy6YzlFKGJOsBKQ5rrvMnd'
output = 'pancreas.h5ad'
gdown.download(url, output, quiet=False)
```

Example 8 (unknown):
```unknown
Downloading...
From: https://drive.google.com/uc?id=1ehxgfHTsMZXy6YzlFKGJOsBKQ5rrvMnd
To: C:\Users\sergei.rybakov\Projects\scarches\pancreas.h5ad
100%|██████████████████████████████████████████████████████████████████████████████████████████| 126M/126M [00:20<00:00, 6.32MB/s]
```

Example 9 (unknown):
```unknown
'pancreas.h5ad'
```

Example 10 (python):
```python
adata_all = sc.read('pancreas.h5ad')
```

Example 11 (python):
```python
adata = adata_all.raw.to_adata()
adata = remove_sparsity(adata)
source_adata = adata[~adata.obs[condition_key].isin(target_conditions)].copy()
target_adata = adata[adata.obs[condition_key].isin(target_conditions)].copy()
```

Example 12 (python):
```python
source_adata
```

Example 13 (unknown):
```unknown
AnnData object with n_obs × n_vars = 10294 × 1000
    obs: 'batch', 'study', 'cell_type', 'size_factors'
```

Example 14 (python):
```python
target_adata
```

Example 15 (unknown):
```unknown
AnnData object with n_obs × n_vars = 5387 × 1000
    obs: 'batch', 'study', 'cell_type', 'size_factors'
```

Example 16 (python):
```python
sca.models.SCVI.setup_anndata(source_adata, batch_key=condition_key, labels_key=cell_type_key)
```

Example 17 (python):
```python
INFO     Using batches from adata.obs["study"]
INFO     Using labels from adata.obs["cell_type"]
INFO     Using data from adata.X
INFO     Successfully registered anndata object containing 10294 cells, 1000 vars, 3 batches,
         8 labels, and 0 proteins. Also registered 0 extra categorical covariates and 0 extra
         continuous covariates.
INFO     Please do not further modify adata until model is trained.
```

Example 18 (python):
```python
vae = sca.models.SCVI(
    source_adata,
    n_layers=2,
    encode_covariates=True,
    deeply_inject_covariates=False,
    use_layer_norm="both",
    use_batch_norm="none",
)
```

Example 19 (unknown):
```unknown
vae.train()
```

Example 20 (unknown):
```unknown
GPU available: True, used: True
TPU available: False, using: 0 TPU cores
LOCAL_RANK: 0 - CUDA_VISIBLE_DEVICES: [0]
```

Example 21 (unknown):
```unknown
Epoch 400/400: 100%|█████████████████████████████████████████████████████████| 400/400 [14:41<00:00,  2.20s/it, loss=502, v_num=1]
```

Example 22 (unknown):
```unknown
scanvae = sca.models.SCANVI.from_scvi_model(vae, unlabeled_category = "Unknown")
```

Example 23 (python):
```python
print("Labelled Indices: ", len(scanvae._labeled_indices))
print("Unlabelled Indices: ", len(scanvae._unlabeled_indices))
```

Example 24 (unknown):
```unknown
Labelled Indices:  10294
Unlabelled Indices:  0
```

Example 25 (unknown):
```unknown
scanvae.train(max_epochs=20)
```

Example 26 (unknown):
```unknown
INFO     Training for 20 epochs.
```

Example 27 (unknown):
```unknown
GPU available: True, used: True
TPU available: False, using: 0 TPU cores
LOCAL_RANK: 0 - CUDA_VISIBLE_DEVICES: [0]
```

Example 28 (unknown):
```unknown
Epoch 20/20: 100%|█████████████████████████████████████████████████████████████| 20/20 [01:38<00:00,  4.90s/it, loss=533, v_num=1]
```

Example 29 (python):
```python
reference_latent = sc.AnnData(scanvae.get_latent_representation())
reference_latent.obs["cell_type"] = source_adata.obs[cell_type_key].tolist()
reference_latent.obs["batch"] = source_adata.obs[condition_key].tolist()
```

Example 30 (python):
```python
sc.pp.neighbors(reference_latent, n_neighbors=8)
sc.tl.leiden(reference_latent)
sc.tl.umap(reference_latent)
sc.pl.umap(reference_latent,
           color=['batch', 'cell_type'],
           frameon=False,
           wspace=0.6,
           )
```

Example 31 (python):
```python
reference_latent.obs['predictions'] = scanvae.predict()
print("Acc: {}".format(np.mean(reference_latent.obs.predictions == reference_latent.obs.cell_type)))
```

Example 32 (unknown):
```unknown
Acc: 0.9435593549640567
```

Example 33 (unknown):
```unknown
ref_path = 'ref_model/'
scanvae.save(ref_path, overwrite=True)
```

Example 34 (python):
```python
model = sca.models.SCANVI.load_query_data(
    target_adata,
    ref_path,
    freeze_dropout = True,
)
model._unlabeled_indices = np.arange(target_adata.n_obs)
model._labeled_indices = []
print("Labelled Indices: ", len(model._labeled_indices))
print("Unlabelled Indices: ", len(model._unlabeled_indices))
```

Example 35 (python):
```python
INFO     Using data from adata.X
INFO     Registered keys:['X', 'batch_indices', 'labels']
INFO     Successfully registered anndata object containing 5387 cells, 1000 vars, 5 batches,
         8 labels, and 0 proteins. Also registered 0 extra categorical covariates and 0 extra
         continuous covariates.
Labelled Indices:  0
Unlabelled Indices:  5387
```

Example 36 (unknown):
```unknown
model.train(
    max_epochs=100,
    plan_kwargs=dict(weight_decay=0.0),
    check_val_every_n_epoch=10,
)
```

Example 37 (unknown):
```unknown
INFO     Training for 100 epochs.
```

Example 38 (unknown):
```unknown
GPU available: True, used: True
TPU available: False, using: 0 TPU cores
LOCAL_RANK: 0 - CUDA_VISIBLE_DEVICES: [0]
```

Example 39 (unknown):
```unknown
Epoch 100/100: 100%|████████████████████████████████████████████████████| 100/100 [04:23<00:00,  2.63s/it, loss=1.24e+03, v_num=1]
```

Example 40 (python):
```python
query_latent = sc.AnnData(model.get_latent_representation())
query_latent.obs['cell_type'] = target_adata.obs[cell_type_key].tolist()
query_latent.obs['batch'] = target_adata.obs[condition_key].tolist()
```

Example 41 (python):
```python
sc.pp.neighbors(query_latent)
sc.tl.leiden(query_latent)
sc.tl.umap(query_latent)
plt.figure()
sc.pl.umap(
    query_latent,
    color=["batch", "cell_type"],
    frameon=False,
    wspace=0.6,
)
```

Example 42 (unknown):
```unknown
<Figure size 320x320 with 0 Axes>
```

Example 43 (unknown):
```unknown
surgery_path = 'surgery_model'
model.save(surgery_path, overwrite=True)
```

Example 44 (python):
```python
query_latent.obs['predictions'] = model.predict()
print("Acc: {}".format(np.mean(query_latent.obs.predictions == query_latent.obs.cell_type)))
```

Example 45 (unknown):
```unknown
Acc: 0.8815667347317616
```

Example 46 (python):
```python
df = query_latent.obs.groupby(["cell_type", "predictions"]).size().unstack(fill_value=0)
norm_df = df / df.sum(axis=0)

plt.figure(figsize=(8, 8))
_ = plt.pcolor(norm_df)
_ = plt.xticks(np.arange(0.5, len(df.columns), 1), df.columns, rotation=90)
_ = plt.yticks(np.arange(0.5, len(df.index), 1), df.index)
plt.xlabel("Predicted")
plt.ylabel("Observed")
```

Example 47 (python):
```python
<ipython-input-27-218c373f617f>:5: MatplotlibDeprecationWarning: Auto-removal of grids by pcolor() and pcolormesh() is deprecated since 3.5 and will be removed two minor releases later; please call grid(False) first.
  _ = plt.pcolor(norm_df)
```

Example 48 (unknown):
```unknown
Text(0, 0.5, 'Observed')
```

Example 49 (python):
```python
adata_full = source_adata.concatenate(target_adata)
full_latent = sc.AnnData(model.get_latent_representation(adata=adata_full))
full_latent.obs['cell_type'] = adata_full.obs[cell_type_key].tolist()
full_latent.obs['batch'] = adata_full.obs[condition_key].tolist()
```

Example 50 (python):
```python
INFO     Input adata not setup with scvi. attempting to transfer anndata setup
INFO     Using data from adata.X
INFO     Registered keys:['X', 'batch_indices', 'labels']
INFO     Successfully registered anndata object containing 15681 cells, 1000 vars, 5 batches,
         8 labels, and 0 proteins. Also registered 0 extra categorical covariates and 0 extra
         continuous covariates.
```

Example 51 (python):
```python
sc.pp.neighbors(full_latent)
sc.tl.leiden(full_latent)
sc.tl.umap(full_latent)
plt.figure()
sc.pl.umap(
    full_latent,
    color=["batch", "cell_type"],
    frameon=False,
    wspace=0.6,
)
```

Example 52 (unknown):
```unknown
<Figure size 320x320 with 0 Axes>
```

Example 53 (python):
```python
full_latent.obs['predictions'] = model.predict(adata=adata_full)
print("Acc: {}".format(np.mean(full_latent.obs.predictions == full_latent.obs.cell_type)))
```

Example 54 (unknown):
```unknown
Acc: 0.9222626108028825
```

Example 55 (python):
```python
sc.pp.neighbors(full_latent)
sc.tl.leiden(full_latent)
sc.tl.umap(full_latent)
plt.figure()
sc.pl.umap(
    full_latent,
    color=["predictions", "cell_type"],
    frameon=False,
    wspace=0.6,
)
```

Example 56 (unknown):
```unknown
<Figure size 320x320 with 0 Axes>
```

---

## Integration and reference mapping with multigrate - scArches documentation

**URL:** http://127.0.0.1:9180/en/latest/multigrate.html

**Contents:**
- Integration and reference mapping with multigrate
- Data preprocessing
  - RNA preprocessing
  - ADT preprocessing
  - ATAC preprocessing
  - Add harmonized cell type labels
  - Subset to reference and query
- Prep the input AnnData object
- Initialize the model
- Train the model
- Inference
- Query mapping

In this notebook, we demonstrate how to use Multigrate with scArches: we build a trimodal reference atlas with Multigrate by integrating CITE-seq and multiome data, and map unimodal as well as multimodal queries onto the reference. We use publically available datasets from NeurIPS 2021 workshop https://openproblems.bio/neurips_2021/.

First, we download the datasets and split them into AnnData objects corresponding to individual modalities: gene expression (RNA) and protein abundance (ADT) for CITE-seq, and gene expression (RNA) and chromatin opennes (ATAC) for multiome.

Multigrate model can work with raw counts modelled with negative binomial (NB loss) distribution or normalized counts modelled with Gaussian (MSE loss). We also subset the genes to the top 4000 highly variable genes to speed up calculations. Hence, we need concatenate both RNA objects, normalize the counts per cell, subset the genes to the batch-aware highly variable genes and split the object back into two, correpsonding to the two experiments. Note that in this notebook we will work with raw counts for RNA-seq data but we need normalized counts to select highly variable genes.

For ADT modality, Multigrate requires normalized counts, so we normalize the raw counts using the CLR transformation.

We recommend log-normalized or tf-idf transformed ATAC counts with Multigrate. Similarly to RNA-seq, we subset the features to the top 20,000 highly variable features to speed up integration.

Since the cell type annotations are not harmonized in the original data, we rename some of the cell types so they align between CITE-seq and multiome datasets.

We split the dataset into a reference (3 batches) and a query (2 batches).

First, we need to organize AnnData objects correspoding to different datasets and modalities into 1 AnnData object. In this example we have 1 CITE-seq dataset and 1 multiome dataset, hence we input 4 anndata objects: 2 (RNA and ADT) for CITE-seq and 2 (RNA and ATAC) for multiome.

paired datasets have to have the same .obs_names, i.e. index;

each sublist in adatas, layers parameters corresponds to one modality. If you have multiple objects per modality, append them to the corresponding list;

objects in each sublist have to have the same set of features: if you want to integrate multiple RNA objects, we recommend first concatenating full objects and then subsetting to 2000-4000 highly variable genes; for ADT modality, we take the intersection of available proteins (double check the naming conventions, as that can vary a lot from one dataset to another, so .var_names can have almost no intersection but if you align the protein names, then there is an overlap);

layers parameter specifies which layer the model should take the counts from. If None, then defaults to .X. The distribution of the input data should be the same within a modality, e.g. here we use raw counts for RNA-seq modality.

From now on, we work with one concatenated anndata object adata.

If using raw counts for scRNA, we recommend using NB loss (or ZINB), thus we need to calculate size_factors by specifying the rna_indices_end parameter. If using normalized counts and MSE for scRNA, rna_indices_end does not need to be specified. Here we also want to correct for batch effects, so we specify Samplename as a categorical covariate. Since we want to integrate 2 different modalities, we need to register Modality as an additional covariate.

Next, we initialize the model. If using raw counts for RNA-seq, use NB loss, if normalized counts, use MSE. For ADT we use CLR-normalized counts and MSE loss. We need to specify mmd='marginal' and set the coeficient to the integration loss if we want to later map unimodal data onto this reference.

You can specify the number of epochs by setting max_epochs parameter, default is 200. The default batch size is set to batch_size = 256, adjust if needed.

Next, we get the latent representation for all the cells and save them in .obsm['latent_ref'] as .obsm['latent'] will be later overwritten when we fine-tune the model on the query.

Visualize the integrated latent embedding.

We repeat the same steps for the setting up the query as for the reference before.

We imitate a unimodal RNA-seq query by masking with zeros the ADT part of one CITE-seq batch and RNA part of one multiome batch.

We update the model by adding new weights to the new batches in the query and fine-tune those weights.

We obtain the latent representation for the query and the reference from the updated model. Note that the representation of the reference is the same as before up to sampling noise.

Finally, we concatentae the reference and the query, and visualize both on a UMAP.

We also can take a look at separate multimodal and unimodal queries.

**Examples:**

Example 1 (python):
```python
import scarches as sca
import scanpy as sc
import anndata as ad
import numpy as np
import muon
import gdown
import json

import warnings
warnings.filterwarnings("ignore")

sc.set_figure_params(figsize=(4, 4), fontsize=8)
```

Example 2 (python):
```python
WARNING:root:In order to use the mouse gastrulation seqFISH datsets, please install squidpy (see https://github.com/scverse/squidpy).
WARNING:root:In order to use sagenet models, please install pytorch geometric (see https://pytorch-geometric.readthedocs.io) and
 captum (see https://github.com/pytorch/captum).
INFO:pytorch_lightning.utilities.seed:Global seed set to 0
/lustre/groups/ml01/workspace/anastasia.litinetskaya/miniconda3/envs/scarches/lib/python3.9/site-packages/pytorch_lightning/utilities/warnings.py:53: LightningDeprecationWarning: pytorch_lightning.utilities.warnings.rank_zero_deprecation has been deprecated in v1.6 and will be removed in v1.8. Use the equivalent function from the pytorch_lightning.utilities.rank_zero module instead.
  new_rank_zero_deprecation(
/lustre/groups/ml01/workspace/anastasia.litinetskaya/miniconda3/envs/scarches/lib/python3.9/site-packages/pytorch_lightning/utilities/warnings.py:58: LightningDeprecationWarning: The `pytorch_lightning.loggers.base.rank_zero_experiment` is deprecated in v1.7 and will be removed in v1.9. Please use `pytorch_lightning.loggers.logger.rank_zero_experiment` instead.
  return new_rank_zero_deprecation(*args, **kwargs)
WARNING:root:mvTCR is not installed. To use mvTCR models, please install it first using "pip install mvtcr"
```

Example 3 (unknown):
```unknown
# download
!wget 'ftp://ftp.ncbi.nlm.nih.gov/geo/series/GSE194nnn/GSE194122/suppl/GSE194122_openproblems_neurips2021_cite_BMMC_processed.h5ad.gz'
!wget 'ftp://ftp.ncbi.nlm.nih.gov/geo/series/GSE194nnn/GSE194122/suppl/GSE194122_openproblems_neurips2021_multiome_BMMC_processed.h5ad.gz'
# unzip
!gzip -d GSE194122_openproblems_neurips2021_cite_BMMC_processed.h5ad.gz
!gzip -d GSE194122_openproblems_neurips2021_multiome_BMMC_processed.h5ad.gz
```

Example 4 (javascript):
```javascript
--2022-11-24 18:09:53--  ftp://ftp.ncbi.nlm.nih.gov/geo/series/GSE194nnn/GSE194122/suppl/GSE194122_openproblems_neurips2021_cite_BMMC_processed.h5ad.gz
           => 'GSE194122_openproblems_neurips2021_cite_BMMC_processed.h5ad.gz'
Resolving ftp.ncbi.nlm.nih.gov (ftp.ncbi.nlm.nih.gov)... 165.112.9.228, 165.112.9.229, 2607:f220:41e:250::11, ...
Connecting to ftp.ncbi.nlm.nih.gov (ftp.ncbi.nlm.nih.gov)|165.112.9.228|:21... connected.
Logging in as anonymous ... Logged in!
==> SYST ... done.    ==> PWD ... done.
==> TYPE I ... done.  ==> CWD (1) /geo/series/GSE194nnn/GSE194122/suppl ... done.
==> SIZE GSE194122_openproblems_neurips2021_cite_BMMC_processed.h5ad.gz ... 615842052
==> PASV ... done.    ==> RETR GSE194122_openproblems_neurips2021_cite_BMMC_processed.h5ad.gz ... done.
Length: 615842052 (587M) (unauthoritative)

100%[======================================>] 615,842,052 10.2MB/s   in 75s

2022-11-24 18:11:10 (7.81 MB/s) - 'GSE194122_openproblems_neurips2021_cite_BMMC_processed.h5ad.gz' saved [615842052]

--2022-11-24 18:11:11--  ftp://ftp.ncbi.nlm.nih.gov/geo/series/GSE194nnn/GSE194122/suppl/GSE194122_openproblems_neurips2021_multiome_BMMC_processed.h5ad.gz
           => 'GSE194122_openproblems_neurips2021_multiome_BMMC_processed.h5ad.gz'
Resolving ftp.ncbi.nlm.nih.gov (ftp.ncbi.nlm.nih.gov)... 165.112.9.228, 165.112.9.229, 2607:f220:41e:250::11, ...
Connecting to ftp.ncbi.nlm.nih.gov (ftp.ncbi.nlm.nih.gov)|165.112.9.228|:21... connected.
Logging in as anonymous ... Logged in!
==> SYST ... done.    ==> PWD ... done.
==> TYPE I ... done.  ==> CWD (1) /geo/series/GSE194nnn/GSE194122/suppl ... done.
==> SIZE GSE194122_openproblems_neurips2021_multiome_BMMC_processed.h5ad.gz ... 2917117242
==> PASV ... done.    ==> RETR GSE194122_openproblems_neurips2021_multiome_BMMC_processed.h5ad.gz ... done.
Length: 2917117242 (2.7G) (unauthoritative)

100%[====================================>] 2,917,117,242 7.98MB/s   in 5m 52s

2022-11-24 18:17:04 (7.91 MB/s) - 'GSE194122_openproblems_neurips2021_multiome_BMMC_processed.h5ad.gz' saved [2917117242]
```

Example 5 (python):
```python
cite = sc.read('GSE194122_openproblems_neurips2021_cite_BMMC_processed.h5ad')
cite
```

Example 6 (unknown):
```unknown
AnnData object with n_obs × n_vars = 90261 × 14087
    obs: 'GEX_n_genes_by_counts', 'GEX_pct_counts_mt', 'GEX_size_factors', 'GEX_phase', 'ADT_n_antibodies_by_counts', 'ADT_total_counts', 'ADT_iso_count', 'cell_type', 'batch', 'ADT_pseudotime_order', 'GEX_pseudotime_order', 'Samplename', 'Site', 'DonorNumber', 'Modality', 'VendorLot', 'DonorID', 'DonorAge', 'DonorBMI', 'DonorBloodType', 'DonorRace', 'Ethnicity', 'DonorGender', 'QCMeds', 'DonorSmoker', 'is_train'
    var: 'feature_types', 'gene_id'
    uns: 'dataset_id', 'genome', 'organism'
    obsm: 'ADT_X_pca', 'ADT_X_umap', 'ADT_isotype_controls', 'GEX_X_pca', 'GEX_X_umap'
    layers: 'counts'
```

Example 7 (python):
```python
rna_cite = cite[:, cite.var['feature_types'] == 'GEX'].copy()
adt = cite[:, cite.var['feature_types'] == 'ADT'].copy()
rna_cite.shape, adt.shape
```

Example 8 (unknown):
```unknown
((90261, 13953), (90261, 134))
```

Example 9 (python):
```python
multiome = sc.read('GSE194122_openproblems_neurips2021_multiome_BMMC_processed.h5ad')
multiome
```

Example 10 (unknown):
```unknown
AnnData object with n_obs × n_vars = 69249 × 129921
    obs: 'GEX_pct_counts_mt', 'GEX_n_counts', 'GEX_n_genes', 'GEX_size_factors', 'GEX_phase', 'ATAC_nCount_peaks', 'ATAC_atac_fragments', 'ATAC_reads_in_peaks_frac', 'ATAC_blacklist_fraction', 'ATAC_nucleosome_signal', 'cell_type', 'batch', 'ATAC_pseudotime_order', 'GEX_pseudotime_order', 'Samplename', 'Site', 'DonorNumber', 'Modality', 'VendorLot', 'DonorID', 'DonorAge', 'DonorBMI', 'DonorBloodType', 'DonorRace', 'Ethnicity', 'DonorGender', 'QCMeds', 'DonorSmoker'
    var: 'feature_types', 'gene_id'
    uns: 'ATAC_gene_activity_var_names', 'dataset_id', 'genome', 'organism'
    obsm: 'ATAC_gene_activity', 'ATAC_lsi_full', 'ATAC_lsi_red', 'ATAC_umap', 'GEX_X_pca', 'GEX_X_umap'
    layers: 'counts'
```

Example 11 (python):
```python
rna_multiome = multiome[:, multiome.var['feature_types'] == 'GEX'].copy()
atac = multiome[:, multiome.var['feature_types'] == 'ATAC'].copy()
rna_multiome.shape, atac.shape
```

Example 12 (unknown):
```unknown
((69249, 13431), (69249, 116490))
```

Example 13 (python):
```python
# concat
rna = ad.concat([rna_cite, rna_multiome])
# normalize
rna.X = rna.layers['counts'].copy()
sc.pp.normalize_total(rna, target_sum=1e4)
sc.pp.log1p(rna)
# subset to hvg
sc.pp.highly_variable_genes(rna, n_top_genes=4000, batch_key='Samplename')
rna = rna[:, rna.var.highly_variable].copy()
# split again
rna_cite = rna[rna.obs['Modality'] == 'cite'].copy()
rna_multiome = rna[rna.obs['Modality'] == 'multiome'].copy()
rna_multiome.shape, rna_cite.shape
```

Example 14 (unknown):
```unknown
((69249, 4000), (90261, 4000))
```

Example 15 (unknown):
```unknown
adt.X = adt.layers['counts'].copy()
muon.prot.pp.clr(adt)
adt.layers['clr'] = adt.X.copy()
adt
```

Example 16 (unknown):
```unknown
AnnData object with n_obs × n_vars = 90261 × 134
    obs: 'GEX_n_genes_by_counts', 'GEX_pct_counts_mt', 'GEX_size_factors', 'GEX_phase', 'ADT_n_antibodies_by_counts', 'ADT_total_counts', 'ADT_iso_count', 'cell_type', 'batch', 'ADT_pseudotime_order', 'GEX_pseudotime_order', 'Samplename', 'Site', 'DonorNumber', 'Modality', 'VendorLot', 'DonorID', 'DonorAge', 'DonorBMI', 'DonorBloodType', 'DonorRace', 'Ethnicity', 'DonorGender', 'QCMeds', 'DonorSmoker', 'is_train'
    var: 'feature_types', 'gene_id'
    uns: 'dataset_id', 'genome', 'organism'
    obsm: 'ADT_X_pca', 'ADT_X_umap', 'ADT_isotype_controls', 'GEX_X_pca', 'GEX_X_umap'
    layers: 'counts', 'clr'
```

Example 17 (python):
```python
atac.X = atac.layers['counts'].copy()
sc.pp.normalize_total(atac, target_sum=1e4)
sc.pp.log1p(atac)
atac.layers['log-norm'] = atac.X.copy()
atac
```

Example 18 (unknown):
```unknown
AnnData object with n_obs × n_vars = 69249 × 116490
    obs: 'GEX_pct_counts_mt', 'GEX_n_counts', 'GEX_n_genes', 'GEX_size_factors', 'GEX_phase', 'ATAC_nCount_peaks', 'ATAC_atac_fragments', 'ATAC_reads_in_peaks_frac', 'ATAC_blacklist_fraction', 'ATAC_nucleosome_signal', 'cell_type', 'batch', 'ATAC_pseudotime_order', 'GEX_pseudotime_order', 'Samplename', 'Site', 'DonorNumber', 'Modality', 'VendorLot', 'DonorID', 'DonorAge', 'DonorBMI', 'DonorBloodType', 'DonorRace', 'Ethnicity', 'DonorGender', 'QCMeds', 'DonorSmoker'
    var: 'feature_types', 'gene_id'
    uns: 'ATAC_gene_activity_var_names', 'dataset_id', 'genome', 'organism', 'log1p'
    obsm: 'ATAC_gene_activity', 'ATAC_lsi_full', 'ATAC_lsi_red', 'ATAC_umap', 'GEX_X_pca', 'GEX_X_umap'
    layers: 'counts', 'log-norm'
```

Example 19 (python):
```python
sc.pp.highly_variable_genes(atac, n_top_genes=20000, batch_key='batch')
atac = atac[:, atac.var.highly_variable].copy()
atac
```

Example 20 (unknown):
```unknown
AnnData object with n_obs × n_vars = 69249 × 20000
    obs: 'GEX_pct_counts_mt', 'GEX_n_counts', 'GEX_n_genes', 'GEX_size_factors', 'GEX_phase', 'ATAC_nCount_peaks', 'ATAC_atac_fragments', 'ATAC_reads_in_peaks_frac', 'ATAC_blacklist_fraction', 'ATAC_nucleosome_signal', 'cell_type', 'batch', 'ATAC_pseudotime_order', 'GEX_pseudotime_order', 'Samplename', 'Site', 'DonorNumber', 'Modality', 'VendorLot', 'DonorID', 'DonorAge', 'DonorBMI', 'DonorBloodType', 'DonorRace', 'Ethnicity', 'DonorGender', 'QCMeds', 'DonorSmoker'
    var: 'feature_types', 'gene_id', 'highly_variable', 'means', 'dispersions', 'dispersions_norm', 'highly_variable_nbatches', 'highly_variable_intersection'
    uns: 'ATAC_gene_activity_var_names', 'dataset_id', 'genome', 'organism', 'log1p', 'hvg'
    obsm: 'ATAC_gene_activity', 'ATAC_lsi_full', 'ATAC_lsi_red', 'ATAC_umap', 'GEX_X_pca', 'GEX_X_umap'
    layers: 'counts', 'log-norm'
```

Example 21 (unknown):
```unknown
gdown.download("https://drive.google.com/u/1/uc?id=1D54P3jURwkdA3goPqYuby0qx6RzKqcP2")
```

Example 22 (unknown):
```unknown
Downloading...
From: https://drive.google.com/u/1/uc?id=1D54P3jURwkdA3goPqYuby0qx6RzKqcP2
To: /lustre/groups/ml01/workspace/anastasia.litinetskaya/code/scarches/notebooks/cellttype_harmonize.json
100%|██████████| 4.77k/4.77k [00:00<00:00, 3.71MB/s]
```

Example 23 (unknown):
```unknown
'cellttype_harmonize.json'
```

Example 24 (unknown):
```unknown
with open('cellttype_harmonize.json', 'r') as f:
    harmonized_celltypes = json.load(f)
harmonized_celltypes.keys()
```

Example 25 (unknown):
```unknown
dict_keys(['cite_ct_l1_map', 'cite_ct_l2_map', 'multi_ct_l1_map', 'multi_ct_l2_map'])
```

Example 26 (unknown):
```unknown
rna_multiome.obs['l1_cell_type'] = rna_multiome.obs['cell_type'].map(harmonized_celltypes['multi_ct_l1_map'])
rna_multiome.obs['l2_cell_type'] = rna_multiome.obs['cell_type'].map(harmonized_celltypes['multi_ct_l2_map'])

atac.obs['l1_cell_type'] = atac.obs['cell_type'].map(harmonized_celltypes['multi_ct_l1_map'])
atac.obs['l2_cell_type'] = atac.obs['cell_type'].map(harmonized_celltypes['multi_ct_l2_map'])

rna_cite.obs['l1_cell_type'] = rna_cite.obs['cell_type'].map(harmonized_celltypes['cite_ct_l1_map'])
rna_cite.obs['l2_cell_type'] = rna_cite.obs['cell_type'].map(harmonized_celltypes['cite_ct_l2_map'])

adt.obs['l1_cell_type'] = adt.obs['cell_type'].map(harmonized_celltypes['cite_ct_l1_map'])
adt.obs['l2_cell_type'] = adt.obs['cell_type'].map(harmonized_celltypes['cite_ct_l2_map'])
```

Example 27 (unknown):
```unknown
# define the reference and the query batches
cite_reference_batches = ['s1d1', 's1d2', 's1d3']
multiome_reference_batches = ['s1d1', 's1d2', 's1d3']
cite_query_batches = ['s2d1', 's2d4']
multiome_query_batches = ['s2d1', 's2d4']
# query
rna_multiome_query = rna_multiome[rna_multiome.obs['batch'].isin(multiome_query_batches)].copy()
atac_query = atac[atac.obs['batch'].isin(multiome_query_batches)].copy()
rna_cite_query = rna_cite[rna_cite.obs['batch'].isin(cite_query_batches)].copy()
adt_query = adt[adt.obs['batch'].isin(cite_query_batches)].copy()
# reference
rna_multiome = rna_multiome[rna_multiome.obs['batch'].isin(multiome_reference_batches)].copy()
atac = atac[atac.obs['batch'].isin(multiome_reference_batches)].copy()
rna_cite = rna_cite[rna_cite.obs['batch'].isin(cite_reference_batches)].copy()
adt = adt[adt.obs['batch'].isin(cite_reference_batches)].copy()
```

Example 28 (python):
```python
adata = sca.models.organize_multiome_anndatas(
    adatas = [[rna_cite, rna_multiome], [None, atac], [adt, None]],    # a list of anndata objects per modality, RNA-seq always goes first
    layers = [['counts', 'counts'], [None, 'log-norm'], ['clr', None]], # if need to use data from .layers, if None use .X
)
adata
```

Example 29 (unknown):
```unknown
AnnData object with n_obs × n_vars = 33554 × 24134
    obs: 'GEX_pct_counts_mt', 'GEX_size_factors', 'GEX_phase', 'cell_type', 'batch', 'GEX_pseudotime_order', 'Samplename', 'Site', 'DonorNumber', 'Modality', 'VendorLot', 'DonorID', 'DonorAge', 'DonorBMI', 'DonorBloodType', 'DonorRace', 'Ethnicity', 'DonorGender', 'QCMeds', 'DonorSmoker', 'l1_cell_type', 'l2_cell_type', 'group', 'ADT_iso_count', 'ADT_n_antibodies_by_counts', 'ADT_pseudotime_order', 'ADT_total_counts', 'GEX_n_genes_by_counts', 'is_train', 'ATAC_atac_fragments', 'ATAC_blacklist_fraction', 'ATAC_nCount_peaks', 'ATAC_nucleosome_signal', 'ATAC_pseudotime_order', 'ATAC_reads_in_peaks_frac', 'GEX_n_counts', 'GEX_n_genes'
    var: 'modality'
    uns: 'modality_lengths'
    layers: 'counts'
```

Example 30 (unknown):
```unknown
size_factors
```

Example 31 (unknown):
```unknown
rna_indices_end
```

Example 32 (unknown):
```unknown
rna_indices_end
```

Example 33 (python):
```python
sca.models.MultiVAE.setup_anndata(
    adata,
    categorical_covariate_keys=['Modality', 'Samplename'],
    rna_indices_end=4000,
)
```

Example 34 (unknown):
```unknown
WARNING:jax._src.lib.xla_bridge:No GPU/TPU found, falling back to CPU. (Set TF_CPP_MIN_LOG_LEVEL=0 and rerun for more info.)
```

Example 35 (unknown):
```unknown
mmd='marginal'
```

Example 36 (python):
```python
model = sca.models.MultiVAE(
    adata,
    losses=['nb', 'mse', 'mse'],
    loss_coefs={'kl': 1e-1,
               'integ': 3000,
               },
    integrate_on='Modality',
    mmd='marginal',
)
```

Example 37 (unknown):
```unknown
batch_size = 256
```

Example 38 (unknown):
```unknown
model.train()
```

Example 39 (unknown):
```unknown
INFO:pytorch_lightning.utilities.rank_zero:GPU available: True (cuda), used: True
INFO:pytorch_lightning.utilities.rank_zero:TPU available: False, using: 0 TPU cores
INFO:pytorch_lightning.utilities.rank_zero:IPU available: False, using: 0 IPUs
INFO:pytorch_lightning.utilities.rank_zero:HPU available: False, using: 0 HPUs
INFO:pytorch_lightning.accelerators.cuda:LOCAL_RANK: 0 - CUDA_VISIBLE_DEVICES: [0]
```

Example 40 (unknown):
```unknown
Epoch 200/200: 100%|██████████| 200/200 [27:27<00:00,  8.04s/it, loss=1.88e+03, v_num=1]
```

Example 41 (unknown):
```unknown
INFO:pytorch_lightning.utilities.rank_zero:`Trainer.fit` stopped: `max_epochs=200` reached.
```

Example 42 (unknown):
```unknown
Epoch 200/200: 100%|██████████| 200/200 [27:28<00:00,  8.24s/it, loss=1.88e+03, v_num=1]
```

Example 43 (unknown):
```unknown
.obsm['latent_ref']
```

Example 44 (unknown):
```unknown
.obsm['latent']
```

Example 45 (python):
```python
model.get_latent_representation()
adata.obsm['latent_ref'] = adata.obsm['latent'].copy()
adata
```

Example 46 (unknown):
```unknown
AnnData object with n_obs × n_vars = 33554 × 24134
    obs: 'GEX_pct_counts_mt', 'GEX_size_factors', 'GEX_phase', 'cell_type', 'batch', 'GEX_pseudotime_order', 'Samplename', 'Site', 'DonorNumber', 'Modality', 'VendorLot', 'DonorID', 'DonorAge', 'DonorBMI', 'DonorBloodType', 'DonorRace', 'Ethnicity', 'DonorGender', 'QCMeds', 'DonorSmoker', 'l1_cell_type', 'l2_cell_type', 'group', 'ADT_iso_count', 'ADT_n_antibodies_by_counts', 'ADT_pseudotime_order', 'ADT_total_counts', 'GEX_n_genes_by_counts', 'is_train', 'ATAC_atac_fragments', 'ATAC_blacklist_fraction', 'ATAC_nCount_peaks', 'ATAC_nucleosome_signal', 'ATAC_pseudotime_order', 'ATAC_reads_in_peaks_frac', 'GEX_n_counts', 'GEX_n_genes', 'size_factors', '_scvi_batch'
    var: 'modality'
    uns: 'modality_lengths', '_scvi_uuid', '_scvi_manager_uuid'
    obsm: '_scvi_extra_categorical_covs', 'latent', 'latent_ref'
    layers: 'counts'
```

Example 47 (python):
```python
sc.pp.neighbors(adata, use_rep='latent')
sc.tl.umap(adata)
```

Example 48 (python):
```python
sc.pl.umap(adata, color=['l1_cell_type', 'l2_cell_type', 'Modality', 'Samplename'], frameon=False, ncols=1)
```

Example 49 (python):
```python
query = sca.models.organize_multiome_anndatas(
    adatas = [[rna_cite_query, rna_multiome_query], [None, atac_query], [adt_query, None]],
    layers = [['counts', 'counts'], [None, 'log-norm'], ['clr', None]],
)
```

Example 50 (unknown):
```unknown
sca.models.MultiVAE.setup_anndata(
    query,
    categorical_covariate_keys=['Modality', 'Samplename'],
    rna_indices_end=4000,
)
```

Example 51 (python):
```python
idx_atac_query = query.obs['Samplename'] == 'site2_donor4_multiome'
idx_scrna_query = query.obs['Samplename'] == 'site2_donor1_cite'

idx_mutiome_query = query.obs['Samplename'] == 'site2_donor1_multiome'
idx_cite_query = query.obs['Samplename'] == 'site2_donor4_cite'

np.sum(idx_atac_query), np.sum(idx_scrna_query), np.sum(idx_mutiome_query), np.sum(idx_cite_query)
```

Example 52 (unknown):
```unknown
(6111, 10465, 4220, 5584)
```

Example 53 (unknown):
```unknown
query[idx_atac_query, :4000].X = 0
query[idx_scrna_query, 4000:].X = 0
```

Example 54 (unknown):
```unknown
q_model = sca.models.MultiVAE.load_query_data(query, model)
```

Example 55 (unknown):
```unknown
q_model.train(weight_decay=0)
```

Example 56 (unknown):
```unknown
INFO:pytorch_lightning.utilities.rank_zero:GPU available: True (cuda), used: True
INFO:pytorch_lightning.utilities.rank_zero:TPU available: False, using: 0 TPU cores
INFO:pytorch_lightning.utilities.rank_zero:IPU available: False, using: 0 IPUs
INFO:pytorch_lightning.utilities.rank_zero:HPU available: False, using: 0 HPUs
INFO:pytorch_lightning.accelerators.cuda:LOCAL_RANK: 0 - CUDA_VISIBLE_DEVICES: [0]
```

Example 57 (unknown):
```unknown
Epoch 200/200: 100%|██████████| 200/200 [20:35<00:00,  6.21s/it, loss=1.38e+03, v_num=1]
```

Example 58 (unknown):
```unknown
INFO:pytorch_lightning.utilities.rank_zero:`Trainer.fit` stopped: `max_epochs=200` reached.
```

Example 59 (unknown):
```unknown
Epoch 200/200: 100%|██████████| 200/200 [20:35<00:00,  6.18s/it, loss=1.38e+03, v_num=1]
```

Example 60 (python):
```python
q_model.get_latent_representation(adata=query)
q_model.get_latent_representation(adata=adata)
```

Example 61 (unknown):
```unknown
INFO     Input AnnData not setup with scvi-tools. attempting to transfer AnnData setup
```

Example 62 (python):
```python
adata.obs['reference'] = 'reference'
query.obs['reference'] = 'query'

adata.obs['type_of_query'] = 'reference'
query.obs.loc[idx_atac_query, 'type_of_query'] = 'ATAC query'
query.obs.loc[idx_scrna_query, 'type_of_query'] = 'scRNA query'
query.obs.loc[idx_mutiome_query, 'type_of_query'] = 'multiome query'
query.obs.loc[idx_cite_query, 'type_of_query'] = 'CITE-seq query'
```

Example 63 (python):
```python
adata_both = ad.concat([adata, query])
```

Example 64 (python):
```python
sc.pp.neighbors(adata_both, use_rep='latent')
sc.tl.umap(adata_both)
```

Example 65 (python):
```python
sc.pl.umap(adata_both, color=['l1_cell_type', 'l2_cell_type', 'reference', 'Modality', 'Samplename'], ncols=1, frameon=False)
```

Example 66 (python):
```python
sc.pl.umap(
    adata_both,
    color='type_of_query',
    ncols=1,
    frameon=False,
    groups=['CITE-seq query']
)
```

Example 67 (python):
```python
sc.pl.umap(
    adata_both,
    color='type_of_query',
    ncols=1,
    frameon=False,
    groups=['multiome query']
)
```

Example 68 (python):
```python
sc.pl.umap(
    adata_both,
    color='type_of_query',
    ncols=1,
    frameon=False,
    groups=['scRNA query']
)
```

Example 69 (python):
```python
sc.pl.umap(
    adata_both,
    color='type_of_query',
    ncols=1,
    frameon=False,
    groups=['ATAC query']
)
```

---

## treeArches: identifying new cell types (advanced tutorial) - scArches documentation

**URL:** http://127.0.0.1:9180/en/latest/treeArches_identifying_new_ct.html

**Contents:**
- treeArches: identifying new cell types (advanced tutorial)
- Load reference and cell type hierarchy
- Load query embedding and annotations
- Updating the cell type hierarchy
- Predict cell type labels

In this more advanced tutorial, we will show how to use a reference atlas and corresponding cell type hierarchy to detect new cell types in your query dataset. Here, we assume that the query dataset is labeled. If the query dataset is unlabeled, you can just predict the labels of the cells (see previous basic tutorial) and check which cells are rejected. Here, we’ll focus more on complete cell types or clusters instead of individual cells.

In this tutorial we’ll show two ways to detect new (sub)types:

Option 1: detecting a complete new cell type. We will update the reference cell type hierarchy with the query labels. A new cell type is detected if a cell type from the query is not matched to a cell type in the reference hierarchy.

Option 2: detecting a new subtype. Sometimes a query cell type matches a cell type in the hierarchy, but still a lot of cells are rejected. This could indicate that part of that query cell type is a different subtype that is not detected yet. We will show that you can detect this by comparing the updated hierarchy to the predictions made.

In this tutorial, we will use the human lung cell atlas (HLCA) as reference. The embeddings for the reference and IPF (query) data we use, can be downloaded here. These embeddings were created with scArches. The trained classifier can be downloaded from Zenodo. There are two classifier here: one trained with the FAISS library and one without. The FAISS library makes the model faster but only works on Linux and with a gpu. More information about installation can be found here.

If you want to train the classifier for the cell type hierarchy yourself, you can find a tutorial here.

We will use a dataset consisting of healthy and IPF (Idiopathic Pulmonary Fibrosis) cells as query dataset. The query embeddings can be downloaded here. The data with annotations can be downloaded here.

Before we can update the cell-type hierarchy. We have to preprocess the reference and query embeddings a bit. First, we concatenate the cell type labels with the condition labels. This way, we ensure that we can differentiate between the healthy and IPF cells.

Prepare query embeddings

Prepare reference embeddings

Concatenate the reference and query data

Remove cell types that are smaller than 10 cells from the data.

Before updating the hierarchy, we subsample the data (otherwise it takes long to run) and make a UMAP.

In the UMAP, we can for instance see where the healthy and IPF cells are with respect to the reference

The reference data contains many cell types. Therefore, we visualize the second annotation level here instead of the most detailed level.

Update the cell type hierarchy with the query cell types. In the updated hierarchy, we see that for instance the ‘Transitioning epithelial cells’ are added as a new cell type to the tree. This cell type was indeed not in the reference and thus correctly discovered as new.

In this part, we will show how to detect a subtype. First, we use the original tree to predict the labels of the query data.

Here, we will zoom in on the macrophages to see how they are predicted. Since, we’re also interested in marker genes, we need the count data. The count data for the reference can be downloaded here.

We normalize the IPF data

Select the macrophages

treeArches contains three types of rejection options (based on the distance, posterior probability and the reconstruction error). Here, we will rename these different types all to ‘Rejected’.

Here, we visualize the predictions for the IPF and healthy data separately using a Sankey diagram. The python function can be found here. An alternative would be to visualize the predictions using scHPL.evaluate.heatmap() (see the treeArches basic tutorial).

In the Sankey plot, we notice that many of the Md-M fibrosis IPF cells are rejected, but that this is not the case for the healthy cells.

Next, we show how to verify the results by doing some downstream analysis. We split the Md-M fibrosis IPF cells in two groups: the rejected and not rejected cells, and we find differentially expression genes between the two.

When we visualize this marker gene, we see that it is only expressed in the Md-M IPF rejected cells. According to literature, SPP1 is known to be a hallmark for IPF pathogenesis 1, 2.

**Examples:**

Example 1 (python):
```python
import scanpy as sc
import scHPL
import numpy as np
import pickle
import time as tm
import copy as cp
import pandas as pd
import matplotlib
import seaborn as sns
```

Example 2 (python):
```python
sc.settings.set_figure_params(dpi=1000, frameon=False)
sc.set_figure_params(dpi=1000)
sc.set_figure_params(figsize=(7,7))

matplotlib.rcParams['pdf.fonttype'] = 42
```

Example 3 (python):
```python
LCA = sc.read('HLCA_emb_and_metadata.h5ad')
file_to_read = open("tree_HCLA_FAISS_withRE.pickle", "rb")
HLCA_tree = pickle.load(file_to_read)
file_to_read.close()
```

Example 4 (python):
```python
emb_ipf = sc.read('HLCA_extended_models_and_embs/surgery_output_embeddings/Sheppard_2020_emb_LCAv2.h5ad')
```

Example 5 (python):
```python
data_IPF = sc.read('Sheppard_2020_noSC_finalAnno.h5ad')
```

Example 6 (python):
```python
data_IPF.obs['ct-batch'] = np.char.add(np.char.add(np.array(data_IPF.obs['anno_final'], dtype=str), '-'), np.array(data_IPF.obs['condition']))
```

Example 7 (unknown):
```unknown
emb_ipf = emb_ipf[data_IPF.obs_names]
emb_ipf.obs['ct-batch'] = data_IPF.obs['ct-batch']
emb_ipf.obs['batch'] = 'Query'
emb_ipf.obs['batch2'] = data_IPF.obs['condition']
```

Example 8 (unknown):
```unknown
/tmp/ipykernel_2427513/1399860873.py:2: ImplicitModificationWarning: Trying to modify attribute `.obs` of view, initializing view as actual.
  emb_ipf.obs['ct-batch'] = data_IPF.obs['ct-batch']
```

Example 9 (unknown):
```unknown
LCA.obs['ct-batch'] = LCA.obs['ann_finest_level']
LCA.obs['batch'] = 'Reference'
LCA.obs['batch2'] = 'Reference'
```

Example 10 (python):
```python
LCA_IPF = sc.concat([LCA, emb_ipf])
LCA_IPF.obs['ct-batch'] = LCA_IPF.obs['ct-batch'].str.replace('_',' ')
```

Example 11 (python):
```python
xx = LCA_IPF.obs.groupby(['ct-batch']).count()
cp_toremove = xx[xx['batch'] < 10].index
idx_tokeep = np.isin(LCA_IPF.obs['ct-batch'], cp_toremove) == False
LCA_IPF = LCA_IPF[idx_tokeep]
LCA_IPF
```

Example 12 (unknown):
```unknown
View of AnnData object with n_obs × n_vars = 646445 × 30
    obs: 'ct-batch', 'batch', 'batch2'
```

Example 13 (python):
```python
LCA_IPF_subs = sc.pp.subsample(LCA_IPF, fraction=0.25, copy=True)

sc.pp.neighbors(LCA_IPF_subs)
sc.tl.leiden(LCA_IPF_subs)
sc.tl.umap(LCA_IPF_subs)
```

Example 14 (python):
```python
sc.pl.umap(LCA_IPF_subs,
           color=['batch2'], groups = ['Healthy', 'IPF'],
           frameon=False,
           wspace=0.6, s=10, palette=sns.color_palette('colorblind', as_cmap=True)
           )
```

Example 15 (python):
```python
/exports/humgen/lmichielsen/miniconda3_v2/envs/scarches2/lib/python3.8/site-packages/scanpy/plotting/_tools/scatterplots.py:1171: FutureWarning: Categorical.replace is deprecated and will be removed in a future version. Use Series.replace directly instead.
  values = values.replace(values.categories.difference(groups), np.nan)
```

Example 16 (python):
```python
LCA_IPF_subs.obs['ann_level_2'] = LCA.obs.ann_level_2

sc.pl.umap(LCA_IPF_subs, color=['ann_level_2'],
           groups = ['Airway epithelium', 'Alveolar epithelium',
                     'Blood vessels', 'Fibroblast lineage', 'Lymphatic EC',
                     'Lymphoid', 'Mesothelium', 'Myeloid', 'Smooth muscle',
                     'Submucosal Gland'],
           frameon=False,
           wspace=0.6, s=10, palette=sns.color_palette('colorblind', as_cmap=True)
           )
```

Example 17 (python):
```python
/exports/humgen/lmichielsen/miniconda3_v2/envs/scarches2/lib/python3.8/site-packages/scanpy/plotting/_tools/scatterplots.py:1171: FutureWarning: Categorical.replace is deprecated and will be removed in a future version. Use Series.replace directly instead.
  values = values.replace(values.categories.difference(groups), np.nan)
```

Example 18 (unknown):
```unknown
## Since the data contains >600.000 cells, this step can take a while to run (~1 hour)
HLCA_tree = scHPL.learn.learn_tree(LCA_IPF,
                                     batch_key = 'batch',
                                     batch_order = ['Query'],
                                     cell_type_key = 'ct-batch',
                                     tree = HLCA_tree,
                                     retrain = False, useRE=True,
                                     batch_added = ['Reference']
                                    )
```

Example 19 (unknown):
```unknown
Starting tree:
```

Example 20 (python):
```python
Adding dataset Query to the tree
These populations are missing from the tree:
['2 Smooth muscle-Healthy']

Updated tree:
```

Example 21 (unknown):
```unknown
file_to_read = open("tree_HCLA_FAISS_withRE.pickle", "rb")
HLCA_ref = pickle.load(file_to_read)
file_to_read.close()

y_pred = scHPL.predict.predict_labels(emb_ipf.X,
               tree = HLCA_ref,
               threshold = 0.5)

emb_ipf.obs['scHPL_pred'] = y_pred
```

Example 22 (python):
```python
data_LCA = sc.read_h5ad('local.h5ad')
data_LCA.var_names = np.asarray(data_LCA.var['feature_name'], dtype=str)
```

Example 23 (python):
```python
sc.pp.normalize_total(data_IPF)
sc.pp.log1p(data_IPF)
```

Example 24 (python):
```python
data_all = sc.concat([data_LCA, data_IPF])
data_all
```

Example 25 (unknown):
```unknown
/exports/humgen/lmichielsen/miniconda3_v2/envs/scarches2/lib/python3.8/site-packages/anndata/_core/merge.py:942: UserWarning: Only some AnnData objects have `.raw` attribute, not concatenating `.raw` attributes.
  warn(
```

Example 26 (unknown):
```unknown
AnnData object with n_obs × n_vars = 646487 × 1897
    obs: 'sample', 'study', 'subject_ID', 'smoking_status', 'BMI', 'condition', 'sample_type', 'dataset', 'age', 'original_ann_level_1', 'original_ann_level_2', 'original_ann_level_3', 'original_ann_level_4', 'original_ann_level_5', 'original_ann_nonharmonized', 'sex', 'ethnicity'
    obsm: 'X_scanvi_emb'
```

Example 27 (unknown):
```unknown
data_all.obs['ann_level_3'] = data_LCA.obs.ann_level_3
data_all.obs['ann_finest_level'] = data_LCA.obs.ann_finest_level
data_all.obs['anno_final'] = data_IPF.obs.anno_final
data_all.obs['scHPL_pred'] = data_IPF.obs.scHPL_pred
data_all.obs['condition'] = data_IPF.obs.condition
```

Example 28 (python):
```python
idx_macro = ((data_all.obs['ann_level_3'] == 'Macrophages') |
             np.isin(data_all.obs.anno_final, ['4_Alveolar macrophages', 'Alveolar Mφ CCL3+',
                                               'Alveolar Mφ proliferating',
                                                'Interstitial Mφ perivascular', 'Md-M (fibrosis)']))
data_macro = data_all[idx_macro]
data_macro
```

Example 29 (unknown):
```unknown
View of AnnData object with n_obs × n_vars = 117425 × 1897
    obs: 'sample', 'study', 'subject_ID', 'smoking_status', 'BMI', 'condition', 'sample_type', 'dataset', 'age', 'original_ann_level_1', 'original_ann_level_2', 'original_ann_level_3', 'original_ann_level_4', 'original_ann_level_5', 'original_ann_nonharmonized', 'sex', 'ethnicity', 'ann_level_3', 'anno_final', 'scHPL_pred', 'ann_finest_level'
    obsm: 'X_scanvi_emb'
```

Example 30 (python):
```python
idx_rej = ((data_macro.obs['scHPL_pred'] == 'Rejection (dist)') | (data_macro.obs['scHPL_pred'] == 'Rejected (RE)'))
data_macro.obs['scHPL_pred'] = data_macro.obs['scHPL_pred'].cat.add_categories('Rejected')
data_macro.obs['scHPL_pred'].values[idx_rej] = 'Rejected'
```

Example 31 (unknown):
```unknown
/tmp/ipykernel_2427513/617128616.py:2: ImplicitModificationWarning: Trying to modify attribute `.obs` of view, initializing view as actual.
  data_macro.obs['scHPL_pred'] = data_macro.obs['scHPL_pred'].cat.add_categories('Rejected')
```

Example 32 (unknown):
```unknown
scHPL.evaluate.heatmap()
```

Example 33 (python):
```python
import sankey

idx1 = (data_macro.obs.study == 'Sheppard_2020') & (data_macro.obs.condition == 'IPF')
idx2 = (data_macro.obs.study == 'Sheppard_2020') & (data_macro.obs.condition == 'Healthy')

x = sankey.sankey( data_macro.obs['anno_final'][idx1],
                  data_macro.obs['scHPL_pred'][idx1], save=True,
                  name_file='sankey_IPF', title="IPF", title_left="Annotated",
                  title_right="Predicted", alpha=0.7,
                  left_order=['Md-M (fibrosis)',
                             '4_Alveolar macrophages',
                              'Alveolar Mφ CCL3+',
                              'Alveolar Mφ MT-positive',
                              'Alveolar Mφ proliferating',
                              'Interstitial Mφ perivascular'
                             ], fontsize='medium')

x = sankey.sankey( data_macro.obs['anno_final'][idx2],
                  data_macro.obs['scHPL_pred'][idx2], save=True,
                  name_file='sankey_NML', title="Healthy", title_left="Annotated",
                  title_right="Predicted", alpha=0.7,
                  left_order=['Md-M (fibrosis)',
                             '4_Alveolar macrophages',
                              'Alveolar Mφ CCL3+',
                              'Alveolar Mφ MT-positive',
                              'Alveolar Mφ proliferating',
                              'Interstitial Mφ perivascular'
                             ], fontsize='medium')
```

Example 34 (python):
```python
### Do DE
# Group 1: anno_final = Md-M (fibrosis), scHPL_pred = Monocyte-derived macro, condition=IPF
# Group 2: anno_final = Md-M (fibrosis), scHPL_pred = Rejected, condition=IPF
MdM = (data_macro.obs.condition == 'IPF') & (data_macro.obs.anno_final == 'Md-M (fibrosis)') & ((data_macro.obs.scHPL_pred == 'Rejected') | (data_macro.obs.scHPL_pred == 'Monocyte-derived Mφ'))
data_MdM = data_macro[MdM]

sc.pp.normalize_total(data_MdM)
sc.pp.log1p(data_MdM)

sc.tl.rank_genes_groups(data_MdM, 'scHPL_pred', method='t-test')
sc.pl.rank_genes_groups(data_MdM, n_genes=25, sharey=False)
```

Example 35 (python):
```python
/exports/humgen/lmichielsen/miniconda3_v2/envs/scarches2/lib/python3.8/site-packages/scanpy/preprocessing/_normalization.py:170: UserWarning: Received a view of an AnnData. Making a copy.
  view_to_actual(adata)
```

Example 36 (python):
```python
data_macro.obs['ann_toplot'] = np.char.add(np.array(data_macro.obs.ann_finest_level, dtype=str),'-Reference')
data_macro.obs.ann_toplot[data_macro.obs.study == 'Sheppard_2020'] = np.char.add(np.char.add(np.array(data_macro.obs.anno_final, dtype=str), '-'), np.array(data_macro.obs.condition, dtype=str))
idx = (data_macro.obs.ann_toplot == 'Md-M (fibrosis)-IPF') & (data_macro.obs.scHPL_pred == 'Rejected')
data_macro.obs['ann_toplot'][idx] = 'Md-M (fibrosis)-IPF-(Rejected)'
```

Example 37 (python):
```python
/tmp/ipykernel_2427513/3849917173.py:2: SettingWithCopyWarning:
A value is trying to be set on a copy of a slice from a DataFrame

See the caveats in the documentation: https://pandas.pydata.org/pandas-docs/stable/user_guide/indexing.html#returning-a-view-versus-a-copy
  data_macro.obs.ann_toplot[data_macro.obs.study == 'Sheppard_2020'] = np.char.add(np.char.add(np.array(data_macro.obs.anno_final, dtype=str), '-'), np.array(data_macro.obs.condition, dtype=str))
/tmp/ipykernel_2427513/3849917173.py:4: SettingWithCopyWarning:
A value is trying to be set on a copy of a slice from a DataFrame

See the caveats in the documentation: https://pandas.pydata.org/pandas-docs/stable/user_guide/indexing.html#returning-a-view-versus-a-copy
  data_macro.obs['ann_toplot'][idx] = 'Md-M (fibrosis)-IPF-(Rejected)'
```

Example 38 (python):
```python
sc.pl.dotplot(data_macro, ['SPP1'], groupby='ann_toplot',
             categories_order=[
                 'Alveolar macrophages-Reference',
                 'Alveolar Mφ CCL3+-Reference',
                 'Alveolar Mφ MT-positive-Reference',
                 'Alveolar Mφ proliferating-Reference',
                 'Interstitial Mφ perivascular-Reference',
                 'Monocyte-derived Mφ-Reference',

                 '4_Alveolar macrophages-Healthy',
                 'Alveolar Mφ CCL3+-Healthy',
                 'Alveolar Mφ proliferating-Healthy',
                 'Interstitial Mφ perivascular-Healthy',
                 'Md-M (fibrosis)-Healthy',

                 '4_Alveolar macrophages-IPF',
                 'Alveolar Mφ CCL3+-IPF',
                 'Alveolar Mφ proliferating-IPF',
                 'Interstitial Mφ perivascular-IPF',
                 'Md-M (fibrosis)-IPF',
                 'Md-M (fibrosis)-IPF-(Rejected)'
             ], figsize=(2,5), save='_IPF_SPP1.pdf')
```

Example 39 (unknown):
```unknown
WARNING: saving figure to file figures/dotplot__IPF_SPP1.pdf
```

---

## Data Processing - scArches documentation

**URL:** http://127.0.0.1:9180/en/latest/api/dataset.html

**Contents:**
- Data Processing

Encode labels of Annotated adata matrix. :param adata: Annotated data matrix. :type adata: : ~anndata.AnnData :param encoder: dictionary of encoded labels. :type encoder: Dict :param condition_key: column name of conditions in adata.obs data frame. :type condition_key: String

labels (~numpy.ndarray) – Array of encoded labels label_encoder (Dict) – dictionary with labels and encoded labels as key, value pairs.

labels (~numpy.ndarray) – Array of encoded labels

label_encoder (Dict) – dictionary with labels and encoded labels as key, value pairs.

If adata.X is a sparse matrix, this will convert it in to normal matrix. :param adata: Annotated data matrix. :type adata: AnnData

adata – Annotated dataset.

alias of AnnotatedDataset

**Examples:**

Example 1 (unknown):
```unknown
AnnotatedDataset
```

Example 2 (unknown):
```unknown
label_encoder()
```

Example 3 (unknown):
```unknown
remove_sparsity()
```

Example 4 (unknown):
```unknown
trVAEDataset
```

---

## scArches documentation

**URL:** http://127.0.0.1:9180/en/latest/index.html

**Contents:**
- What is scArches?

scArches allows your single-cell query data to be analyzed by integrating it into a reference atlas. To map your data, you need an integrated atlas using one of the reference-building methods for different applications that are supported by scArches which are, including:

Annotating a single-cell dataset using a reference atlas: You can check following models/tutorials using scPoli (De Donno et al., 2022) or scANVI (Xu et al., 2019 ).

Identify novel cell states present in your data by mapping to an atlas: If you want to detect cell-states affected by disease or novel subpopulations see treeArches (Michielsen*, Lotfollahi* et al., 2022) and also similar use case by mapping to Human Lung cell atlas.

Multimodal single-cell atlases: You can check the tutorial for Multigrate (Litinetskaya*, Lotfollahi* et al., 2022) to work with CITE-seq + Multiome (ATAC+ RNA). Additionally, you can check mvTCR (Drost et al., 2022) for joint analysis of T-cell Receptor (TCR) and scRNAseq data. To impute missing surface proteins for your query single-cell RNAseq data using a CITE-seq reference, see totalVI (Gayoso et al., 2019).

Data integration/batch correction: For integration of multiple scRNAseq datasets see scVI (Lopez et al, 2018) or trVAE (Lotfollahi et al, 2020). In case of strong batch effect and access to cell-type labels, consider using scGen (Lotfollahi et al., 2019).

Spatial transcriptomics: To map scRNAseq data to a spatial reference and infer spatial locations check SageNet (Heidari et al., 2022).

Querying gene programs in single-cell atlases: Using gene programs (GPs), you can embed your datasets into known subspaces (e.g., interferon signaling) and see the activity of your query dataset within desired GPs. You can use available GP databases (e.g, GO pathways) or your curated GPs, see expiMap (Lotfollahi*, Rybakov* et al., 2023). One can also learn novel GPs as shown here.

Links to the papers can be found here.

---
