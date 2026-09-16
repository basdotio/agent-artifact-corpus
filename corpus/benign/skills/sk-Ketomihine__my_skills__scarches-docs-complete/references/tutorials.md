# Scarches-Docs-Complete - Tutorials

**Pages:** 2

---

## Tutorial for mvTCR - scArches documentation

**URL:** http://127.0.0.1:9180/en/latest/mvTCR_borcherding.html

**Contents:**
- Tutorial for mvTCR
- Download dataset
- Import libraries
- Set hyperparameters
- Load Data
- Train model on atlas dataset
- Finetune model on query
- Get latent representation and visualize using UMAP
- Use latent representation for downstream task

In this tutorial, we create an atlas for tumor-infiltrating lymphocytes (TIL). The dataset is collected by Borcherding and contains ~750,000 samples from 11 cancer types and 6 tissue sources. In this example we use a subsampled version of Lung cancer specific studies. We use mvTCR to build the atlas and later integrate a heldout query into it. After the data integration, we use it to infer the tissue origin from the heldout dataset using a simple kNN trained on the learned latent representation.

mvTCR is a multi-modal generative integration method for transcriptome and T-cell receptor (TCR) data. For more information on mvTCR please refer to Drost 2022

First we download the mvTCR package and the preprocessed Tumor-infiltrating Lymphocyte (TIL) dataset. The unpreprocessed dataset can be downloaded at https://github.com/ncborcherding/utility

Here the hyperparameters can be set

We load the data using scanpy

The model is initialized and trained on the atlas dataset until convergence, for early stopping we subsample 20% from the training dataset as validation dataset

To finetune the model, we load the pretrained model with best pseudo metric performance from the previous step. Then we initizalize additional embedding vectors for the query datasets and freeze all weights except the embedding layer, before further training on the query dataset

After finetuning, we take a first qualitative look on the latent representation by using UMAP to visualize them

We can now use the latent representation for downstream tasks, such as clustering, analysis or imputation. In this example we show how to use a simple kNN classifier to predict the cancer type of the holdout data.

**Examples:**

Example 1 (unknown):
```unknown
%%capture
!pip install mvtcr
```

Example 2 (python):
```python
import gdown
import os
url = 'https://drive.google.com/uc?id=1Lw9hytk3BiZ8aOucvnhRr9qyeMeNTs4v'
output = 'borcherding_subsampled.h5ad'
if not os.path.exists(output):
    gdown.download(url, output, quiet=False)
```

Example 3 (python):
```python
import torch
import scanpy as sc
from sklearn.neighbors import KNeighborsClassifier
from sklearn.metrics import f1_score
```

Example 4 (python):
```python
%%capture
import scarches as sca
```

Example 5 (unknown):
```unknown
%load_ext autoreload
%autoreload 2
```

Example 6 (unknown):
```unknown
random_seed = 42
sca.models.mvTCR.utils_training.fix_seeds(random_seed)
```

Example 7 (unknown):
```unknown
# We holdout two Cohorts out of 13
holdout_cohorts = ['GSE162500']

# maps each batch to an index, important is that the holdout cohorts are at the last positions
mapper = {'GSE176021': 0, 'GSE139555': 1, 'GSE154826': 2, 'GSE162500': 3}
```

Example 8 (python):
```python
# Parameters for model and training
params_architecture = {'batch_size': 512,
                       'learning_rate': 0.0006664047426647477,
                       'loss_weights': [1.0, 0.016182440457269676, 1.0110670042409596e-10],
                       'joint': {'activation': 'leakyrelu',
                                 'batch_norm': True,
                                 'dropout': 0.05,
                                 'hdim': 100,
                                 'losses': ['MSE', 'CE'],
                                 'num_layers': 2,
                                 'shared_hidden': [100, 100],
                                 'zdim': 50,
                                 'c_embedding_dim': 20,
                                 'use_embedding_for_cond': True,
                                 'num_conditional_labels': 11,
                                 'cond_dim': 20,
                                 'cond_input': True},
                       'rna': {'activation': 'leakyrelu',
                               'batch_norm': True,
                               'dropout': 0.05,
                               'gene_hidden': [500, 500, 500],
                               'num_layers': 3,
                               'output_activation': 'linear',
                               'xdim': 5000},
                       'tcr': {'embedding_size': 64,
                               'num_heads': 4,
                               'forward_expansion': 4,
                               'encoding_layers': 1,
                               'decoding_layers': 1,
                               'dropout': 0.25,
                               'max_tcr_length': 30,
                               'num_seq_labels': 24}
                      }

params_experiment = {
    'model_name': 'moe',
    'n_epochs': 200,
    'early_stop': 5,
    'balanced_sampling': 'clonotype',
    'kl_annealing_epochs': None,
    'metadata': ['clonotype', 'Sample', 'Type', 'Tissue', 'Tissue+Type', 'functional.cluster'],
    'save_path': 'saved_models',
    'conditional': 'Cohort'
}

params_optimization = {
    'name': 'pseudo_metric',
    'prediction_labels':
        {'clonotype': 1,
         'Tissue+Type': 10}
}
```

Example 9 (python):
```python
adata = sc.read_h5ad('borcherding_subsampled.h5ad')
adata = adata[adata.obs['Cohort'].isin(list(mapper.keys()))]
adata = adata[adata.obs['Tissue']=='Lung']
adata.obs['Cohort_id'] = adata.obs['Cohort'].map(mapper)
adata.obs['Tissue+Type'] = [f'{tissue}.{type_}' for tissue, type_ in zip(adata.obs['Tissue'], adata.obs['Type'])]
metadata = ['Tissue', 'Type', 'Tissue+Type', 'functional.cluster', 'set', 'Cohort']
```

Example 10 (python):
```python
# Split data into training and hold-out dataset
adata.obs['set'] = 'train'
adata.obs['set'][adata.obs['Cohort'].isin(holdout_cohorts)] = 'hold_out'
adata.obsm['Cohort'] = torch.nn.functional.one_hot(torch.tensor(adata.obs['Cohort_id'])).numpy()

# Stratified splitting of training into train and val. The val set is used for early stopping
adata_train = adata[~adata.obs['Cohort'].isin(holdout_cohorts)].copy()
adata_train.obsm['Cohort'] = torch.nn.functional.one_hot(torch.tensor(adata_train.obs['Cohort_id'])).numpy()
train, val = sca.models.mvTCR.utils_preprocessing.group_shuffle_split(adata_train, group_col='clonotype', val_split=0.2, random_seed=random_seed)
adata_train.obs.loc[val.obs.index, 'set'] = 'val'
```

Example 11 (python):
```python
model = sca.models.mvTCR.models.mixture_modules.moe.MoEModel(adata_train, params_architecture, params_experiment['balanced_sampling'], params_experiment['metadata'],
                                                             params_experiment['conditional'], params_optimization)
```

Example 12 (unknown):
```unknown
model.train(params_experiment['n_epochs'], params_architecture['batch_size'], params_architecture['learning_rate'],
            params_architecture['loss_weights'], params_experiment['kl_annealing_epochs'],
            params_experiment['early_stop'], params_experiment['save_path'])
```

Example 13 (unknown):
```unknown
46%|██████████████████████████████▏                                  | 93/200 [19:18<22:12, 12.45s/it]
```

Example 14 (unknown):
```unknown
Early stopped
```

Example 15 (python):
```python
# Separate holdout data and create a validation set (20%) for early stopping
adata_hold_out = adata[adata.obs['Cohort'].isin(holdout_cohorts)].copy()
adata_hold_out.obsm['Cohort'] = torch.nn.functional.one_hot(torch.tensor(adata_hold_out.obs['Cohort_id'])).numpy()
train, val = sca.models.mvTCR.utils_preprocessing.group_shuffle_split(adata_hold_out, group_col='clonotype', val_split=0.2, random_seed=random_seed)
adata_hold_out.obs['set'] = 'train'
adata_hold_out.obs.loc[val.obs.index, 'set'] = 'val'
```

Example 16 (python):
```python
# Load pretrained model
model = sca.models.mvTCR.utils_training.load_model(adata_train, f'saved_models/best_model_by_metric.pt', base_path='.')
model.add_new_embeddings(len(holdout_cohorts))  # add new cond embeddings
model.freeze_all_weights_except_cond_embeddings()
model.change_adata(adata_hold_out)  # change the adata to finetune on the holdout data
```

Example 17 (unknown):
```unknown
# Finetune model
model.train(n_epochs=200, batch_size=params_architecture['batch_size'], learning_rate=params_architecture['learning_rate'],
            loss_weights=params_architecture['loss_weights'], kl_annealing_epochs=None, early_stop=5,
            save_path=f'saved_models/finetuning/', comet=None)
```

Example 18 (unknown):
```unknown
3%|█▉                                                                | 6/200 [00:17<09:25,  2.91s/it]
```

Example 19 (unknown):
```unknown
Early stopped
```

Example 20 (python):
```python
model = sca.models.mvTCR.utils_training.load_model(adata_hold_out, f'saved_models/finetuning/best_model_by_metric.pt', base_path='.')
```

Example 21 (python):
```python
latent_adata = model.get_latent(adata, metadata=metadata, return_mean=True)
```

Example 22 (python):
```python
# For visualization purpose
latent_adata.obs['Cohort_held_out'] = latent_adata.obs['Cohort'].copy()
latent_adata.obs.loc[~latent_adata.obs['Cohort'].isin(holdout_cohorts), 'Cohort_held_out'] = None
```

Example 23 (python):
```python
sc.pp.neighbors(latent_adata)
sc.tl.umap(latent_adata)
```

Example 24 (python):
```python
from matplotlib import rcParams
rcParams['figure.figsize'] = (4, 4)
sc.pl.umap(latent_adata, color=['Type', 'functional.cluster', 'Cohort', 'Cohort_held_out'], size=1, ncols=1, legend_fontsize=5)
```

Example 25 (python):
```python
X_train = latent_adata[latent_adata.obs['set'] == 'train'].X
y_train = latent_adata[latent_adata.obs['set'] == 'train'].obs['Type']
X_test = latent_adata[latent_adata.obs['set'] == 'hold_out'].X
y_test = latent_adata[latent_adata.obs['set'] == 'hold_out'].obs['Type']
```

Example 26 (unknown):
```unknown
classifier = KNeighborsClassifier(n_neighbors=5, weights='distance', n_jobs=-1)
classifier.fit(X_train, y_train)
y_pred = classifier.predict(X_test)
```

Example 27 (python):
```python
print(f'F1-score for predicting Sample Origin: {f1_score(y_test, y_pred, average="weighted"):.3}')
```

Example 28 (unknown):
```unknown
F1-score for predicting Sample Origin: 0.744
```

---

## Unsupervised surgery pipeline with TRVAE - scArches documentation

**URL:** http://127.0.0.1:9180/en/latest/trvae_surgery_pipeline.html

**Contents:**
- Unsupervised surgery pipeline with TRVAE
- Set relevant anndata.obs labels and training length
- Download Dataset and split into reference dataset and query dataset
- Create TRVAE model and train it on reference dataset
- Create anndata file of latent representation and compute UMAP
- Perform surgery on reference model and train on query dataset
- Get latent representation of reference + query dataset and compute UMAP

Here we use the CelSeq2 and SS2 studies as query data and the other 3 studies as reference atlas. We strongly suggest to use earlystopping to avoid over-fitting. The best earlystopping criteria is the ‘val_unweighted_loss’ for TRVAE.

This line makes sure that count data is in the adata.X. Remember that count data in adata.X is necessary when using “nb” or “zinb” loss. However, when using trVAE with MSE loss normalized data is necessary in adata.X

Create the trVAE model instance with NB loss as default. Insert “recon_loss=’mse’,” or “recon_loss=’zinb’,” to change the reconstruction loss.

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


trvae_epochs = 500
surgery_epochs = 500

early_stopping_kwargs = {
    "early_stopping_metric": "val_unweighted_loss",
    "threshold": 0,
    "patience": 20,
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
To: C:\Users\sergei.rybakov\projects\notebooks\pancreas.h5ad
126MB [00:35, 3.52MB/s]
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
source_adata = adata[~adata.obs[condition_key].isin(target_conditions)]
target_adata = adata[adata.obs[condition_key].isin(target_conditions)]
source_conditions = source_adata.obs[condition_key].unique().tolist()
```

Example 10 (python):
```python
source_adata
```

Example 11 (unknown):
```unknown
View of AnnData object with n_obs × n_vars = 10294 × 1000
    obs: 'batch', 'study', 'cell_type', 'size_factors'
```

Example 12 (python):
```python
target_adata
```

Example 13 (unknown):
```unknown
View of AnnData object with n_obs × n_vars = 5387 × 1000
    obs: 'batch', 'study', 'cell_type', 'size_factors'
```

Example 14 (python):
```python
trvae = sca.models.TRVAE(
    adata=source_adata,
    condition_key=condition_key,
    conditions=source_conditions,
    hidden_layer_sizes=[128, 128],
)
```

Example 15 (unknown):
```unknown
INITIALIZING NEW NETWORK..............
Encoder Architecture:
        Input Layer in, out and cond: 1000 128 3
        Hidden Layer 1 in/out: 128 128
        Mean/Var Layer in/out: 128 10
Decoder Architecture:
        First Layer in, out and cond:  10 128 3
        Hidden Layer 1 in/out: 128 128
        Output Layer in/out:  128 1000
```

Example 16 (unknown):
```unknown
trvae.train(
    n_epochs=trvae_epochs,
    alpha_epoch_anneal=200,
    early_stopping_kwargs=early_stopping_kwargs
)
```

Example 17 (unknown):
```unknown
Trying to set attribute `.obs` of view, copying.
Trying to set attribute `.obs` of view, copying.
```

Example 18 (unknown):
```unknown
Valid_data 1029
Condition: 0 Counts in TrainData: 821
Condition: 1 Counts in TrainData: 147
Condition: 2 Counts in TrainData: 61
 |████████------------| 40.6%  - epoch_loss:    2387 - epoch_unweighted_loss:    2387 - epoch_recon_loss:    2367 - epoch_kl_loss:      18 - epoch_mmd_loss:       2 - val_loss:    1267 - val_unweighted_loss:    1267 - val_recon_loss:    1248 - val_kl_loss:      13 - val_mmd_loss:       5
ADJUSTED LR
 |█████████-----------| 47.0%  - epoch_loss:    2357 - epoch_unweighted_loss:    2357 - epoch_recon_loss:    2338 - epoch_kl_loss:      17 - epoch_mmd_loss:       2 - val_loss:    1346 - val_unweighted_loss:    1346 - val_recon_loss:    1327 - val_kl_loss:      14 - val_mmd_loss:       5
ADJUSTED LR
 |█████████-----------| 48.4%  - epoch_loss:    2371 - epoch_unweighted_loss:    2371 - epoch_recon_loss:    2352 - epoch_kl_loss:      18 - epoch_mmd_loss:       2 - val_loss:    1302 - val_unweighted_loss:    1302 - val_recon_loss:    1284 - val_kl_loss:      14 - val_mmd_loss:       5
Stopping early: no improvement of more than 0 nats in 20 epochs
If the early stopping criterion is too strong, please instantiate it with different parameters in the train method.
Saving best state of network...
Best State was in Epoch 220
```

Example 19 (python):
```python
adata_latent = sc.AnnData(trvae.get_latent())
adata_latent.obs['cell_type'] = source_adata.obs[cell_type_key].tolist()
adata_latent.obs['batch'] = source_adata.obs[condition_key].tolist()
```

Example 20 (python):
```python
sc.pp.neighbors(adata_latent, n_neighbors=8)
sc.tl.leiden(adata_latent)
sc.tl.umap(adata_latent)
sc.pl.umap(adata_latent,
           color=['batch', 'cell_type'],
           frameon=False,
           wspace=0.6,
           )
```

Example 21 (unknown):
```unknown
... storing 'cell_type' as categorical
... storing 'batch' as categorical
```

Example 22 (unknown):
```unknown
ref_path = 'reference_model/'
trvae.save(ref_path, overwrite=True)
```

Example 23 (python):
```python
new_trvae = sca.models.TRVAE.load_query_data(adata=target_adata, reference_model=ref_path)
```

Example 24 (unknown):
```unknown
INITIALIZING NEW NETWORK..............
Encoder Architecture:
        Input Layer in, out and cond: 1000 128 5
        Hidden Layer 1 in/out: 128 128
        Mean/Var Layer in/out: 128 10
Decoder Architecture:
        First Layer in, out and cond:  10 128 5
        Hidden Layer 1 in/out: 128 128
        Output Layer in/out:  128 1000
```

Example 25 (unknown):
```unknown
new_trvae.train(
    n_epochs=surgery_epochs,
    alpha_epoch_anneal=200,
    early_stopping_kwargs=early_stopping_kwargs,
    weight_decay=0
)
```

Example 26 (unknown):
```unknown
Trying to set attribute `.obs` of view, copying.
Trying to set attribute `.obs` of view, copying.
```

Example 27 (unknown):
```unknown
Valid_data 538
Condition: 0 Counts in TrainData: 0
Condition: 1 Counts in TrainData: 0
 |████████████--------| 64.0%  - epoch_loss:    2664 - epoch_unweighted_loss:    2664 - epoch_recon_loss:    2647 - epoch_kl_loss:      16 - epoch_mmd_loss:       0 - val_loss:    2606 - val_unweighted_loss:    2606 - val_recon_loss:    2589 - val_kl_loss:      16 - val_mmd_loss:       1
ADJUSTED LR
 |█████████████-------| 68.8%  - epoch_loss:    2576 - epoch_unweighted_loss:    2576 - epoch_recon_loss:    2559 - epoch_kl_loss:      16 - epoch_mmd_loss:       0 - val_loss:    2493 - val_unweighted_loss:    2493 - val_recon_loss:    2477 - val_kl_loss:      16 - val_mmd_loss:       1
ADJUSTED LR
 |██████████████------| 70.2%  - epoch_loss:    2528 - epoch_unweighted_loss:    2528 - epoch_recon_loss:    2512 - epoch_kl_loss:      16 - epoch_mmd_loss:       0 - val_loss:    2495 - val_unweighted_loss:    2495 - val_recon_loss:    2478 - val_kl_loss:      16 - val_mmd_loss:       1
Stopping early: no improvement of more than 0 nats in 20 epochs
If the early stopping criterion is too strong, please instantiate it with different parameters in the train method.
Saving best state of network...
Best State was in Epoch 329
```

Example 28 (python):
```python
adata_latent = sc.AnnData(new_trvae.get_latent())
adata_latent.obs['cell_type'] = target_adata.obs[cell_type_key].tolist()
adata_latent.obs['batch'] = target_adata.obs[condition_key].tolist()
```

Example 29 (python):
```python
sc.pp.neighbors(adata_latent, n_neighbors=8)
sc.tl.leiden(adata_latent)
sc.tl.umap(adata_latent)
sc.pl.umap(adata_latent,
           color=['batch', 'cell_type'],
           frameon=False,
           wspace=0.6,
           )
```

Example 30 (unknown):
```unknown
... storing 'cell_type' as categorical
... storing 'batch' as categorical
```

Example 31 (unknown):
```unknown
surg_path = 'surgery_model'
new_trvae.save(surg_path, overwrite=True)
```

Example 32 (python):
```python
full_latent = sc.AnnData(new_trvae.get_latent(adata.X, adata.obs[condition_key]))
full_latent.obs['cell_type'] = adata.obs[cell_type_key].tolist()
full_latent.obs['batch'] = adata.obs[condition_key].tolist()
```

Example 33 (python):
```python
sc.pp.neighbors(full_latent, n_neighbors=8)
sc.tl.leiden(full_latent)
sc.tl.umap(full_latent)
sc.pl.umap(full_latent,
           color=['batch', 'cell_type'],
           frameon=False,
           wspace=0.6,
           )
```

Example 34 (unknown):
```unknown
... storing 'cell_type' as categorical
... storing 'batch' as categorical
```

---
