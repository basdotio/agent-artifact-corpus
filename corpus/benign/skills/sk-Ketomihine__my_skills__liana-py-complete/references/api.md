# Liana-Py-Complete - Api

**Pages:** 45

---

## liana.utils.obsm_to_adata — liana

**URL:** http://127.0.0.1:9050/en_latest_generated_liana.utils.obsm_to_adata.html

**Contents:**
- liana.utils.obsm_to_adata
- Contents
- liana.utils.obsm_to_adata#

Extracts a dataframe from adata.obsm and returns a new AnnData object with the values stored in X.

adata (AnnData) – Annotated data object.

obsm_key (str) – .osbm key to extract.

df (DataFrame | None (default: None)) – Dataframe with stats per cell/spot. If None, it will be extracted from adata.obsm[obsm_key].

_uns (DataFrame | None (default: None)) – Dictionary with uns data. If None, it will be extracted from adata.uns.

_obsm (DataFrame | None (default: None)) – Dictionary with obsm data. If None, it will be extracted from adata.obsm.

An AnnData object with the values stored in X.

liana.plotting.interactions

liana.utils.mdata_to_anndata

By Daniel Dimitrov, Philipp Sven Lars Schäfer, Elias Farr, Pablo Rodriguez-Mier, Sebastian Lobentanzer, Pau Badia-i-Mompel, Aurelien Dugourd, Jovan Tanevski, Ricardo Omar Ramirez Flores, Julio Saez-Rodriguez

© Copyright 2025, Daniel Dimitrov, Philipp Sven Lars Schäfer, Elias Farr, Pablo Rodriguez-Mier, Sebastian Lobentanzer, Pau Badia-i-Mompel, Aurelien Dugourd, Jovan Tanevski, Ricardo Omar Ramirez Flores, Julio Saez-Rodriguez..

**Examples:**

Example 1 (python):
```python
obsm_to_adata()
```

Example 2 (python):
```python
obsm_to_adata()
```

---

## liana.utils.neg_to_zero — liana

**URL:** http://127.0.0.1:9050/en_latest_generated_liana.utils.neg_to_zero.html

**Contents:**
- liana.utils.neg_to_zero
- Contents
- liana.utils.neg_to_zero#

Set negative values to 0.

X (array-like) – Data to be transformed.

cutoff (float) – Cutoff value for zero-inflation - values less than this are set to 0. Default is 0.

liana.utils.zi_minmax

liana.utils.spatial_neighbors

By Daniel Dimitrov, Philipp Sven Lars Schäfer, Elias Farr, Pablo Rodriguez-Mier, Sebastian Lobentanzer, Pau Badia-i-Mompel, Aurelien Dugourd, Jovan Tanevski, Ricardo Omar Ramirez Flores, Julio Saez-Rodriguez

© Copyright 2025, Daniel Dimitrov, Philipp Sven Lars Schäfer, Elias Farr, Pablo Rodriguez-Mier, Sebastian Lobentanzer, Pau Badia-i-Mompel, Aurelien Dugourd, Jovan Tanevski, Ricardo Omar Ramirez Flores, Julio Saez-Rodriguez..

**Examples:**

Example 1 (unknown):
```unknown
neg_to_zero()
```

Example 2 (unknown):
```unknown
neg_to_zero()
```

---

## liana.multi.to_tensor_c2c — liana

**URL:** http://127.0.0.1:9050/en_latest_generated_liana.multi.to_tensor_c2c.html

**Contents:**
- liana.multi.to_tensor_c2c
- Contents
- liana.multi.to_tensor_c2c#

Function to convert a LIANA result to a tensor for cell2cell analysis.

adata (AnnData (default: None)) – Annotated data object.

sample_key (str (default: None)) – key in adata.obs to use for grouping by sample or context.

score_key (str (default: None)) – Column name of the score in liana_res. If None, the score is inferred from the method.

liana_res (DataFrame (default: None)) – A dataframe with the LIANA results. If None, it will be taken from adata.uns[uns_key].

source_key (str (default: 'source')) – Column name of the sender/source cell types in liana_res.

target_key (str (default: 'target')) – Column name of the receiver/target cell types in liana_res.

ligand_key (str (default: 'ligand_complex')) – Column name of the ligand in liana_res.

receptor_key (str (default: 'receptor_complex')) – Column name of the receptor in liana_res.

uns_key (str (default: 'liana_res')) – Key in adata.uns that contains the LIANA results. Default is 'liana_res'.

inverse_fun (callable (default: <function DefaultValues.inverse_fun at 0x715ae615d300>)) – Function that is applied to the scores before building the views. Default is lambda x: 1 - x which is used to invert the scores reflect probabilities (e.g. magnitude_rank), i.e. such for which lower values reflect higher relevance. This is handled automatically for the scores in liana.

non_expressed_fill (float, optional (default: None)) – Value to fill for non-expressed ligand-receptor pairs.

non_negative (bool, optional (default: True)) – Whether to make the tensor non-negative.

return_dict (bool, optional (default: False)) – Whether to return a dictionary of tensors.

**kwargs (keyword arguments to pass to Tensor-cell2cell’s cell2cell.tensor.external_scores.dataframes_to_tensor function.)

Returns a tensor of shape (n_samples, n_senders, n_receivers, n_interactions) or a dictionary of tensors if return_dict is True.

liana.multi.adata_to_views

By Daniel Dimitrov, Philipp Sven Lars Schäfer, Elias Farr, Pablo Rodriguez-Mier, Sebastian Lobentanzer, Pau Badia-i-Mompel, Aurelien Dugourd, Jovan Tanevski, Ricardo Omar Ramirez Flores, Julio Saez-Rodriguez

© Copyright 2025, Daniel Dimitrov, Philipp Sven Lars Schäfer, Elias Farr, Pablo Rodriguez-Mier, Sebastian Lobentanzer, Pau Badia-i-Mompel, Aurelien Dugourd, Jovan Tanevski, Ricardo Omar Ramirez Flores, Julio Saez-Rodriguez..

**Examples:**

Example 1 (unknown):
```unknown
to_tensor_c2c()
```

Example 2 (python):
```python
adata.uns[uns_key]
```

Example 3 (unknown):
```unknown
'ligand_complex'
```

Example 4 (unknown):
```unknown
'receptor_complex'
```

Example 5 (unknown):
```unknown
'liana_res'
```

Example 6 (unknown):
```unknown
'liana_res'
```

Example 7 (unknown):
```unknown
<function DefaultValues.inverse_fun at 0x715ae615d300>
```

Example 8 (unknown):
```unknown
lambda x: 1 - x
```

Example 9 (unknown):
```unknown
cell2cell.tensor.external_scores.dataframes_to_tensor
```

Example 10 (unknown):
```unknown
return_dict
```

Example 11 (unknown):
```unknown
to_tensor_c2c()
```

---

## liana.method.connectome.__call__ — liana

**URL:** http://127.0.0.1:9050/en_latest_generated_liana.method.connectome.__call__.html

**Contents:**
- liana.method.connectome.__call__
- Contents
- liana.method.connectome.__call__#

Run a ligand-receptor method.

adata (AnnData | MuData) – Annotated data object.

groupby (str) – Key to be used for grouping.

resource_name (str (default: 'consensus')) – Name of the resource to be used for ligand-receptor inference. See li.rs.show_resources() for available resources.

expr_prop (float (default: 0.1)) – Minimum expression proportion for the ligands and receptors (+ their subunits) in the corresponding cell identities. Set to 0 to return unfiltered results.

min_cells (int (default: 5)) – Minimum cells (per cell identity if grouped by groupby) to be considered for downstream analysis.

groupby_pairs (DataFrame | None (default: None)) – A DataFrame with columns source and target to be used to subset the possible combinations of interacting cell types. If None, all possible combinations are used.

base (float (default: np.float64(2.718281828459045))) – Exponent base used to reverse the log-transformation of the matrix. Relevant only for the logfc method.

supp_columns (list | None (default: None)) – Additional columns to be added from any of the methods implemented in liana, or any of the columns returned by scanpy.tl.rank_genes_groups, each starting with ligand_* or receptor_*. For example, ['ligand_pvals', 'receptor_pvals']. None by default.

return_all_lrs (bool (default: False)) – Bool whether to return all ligand-receptor pairs, or only those that surpass the expr_prop threshold. Ligand-receptor pairs that do not pass the expr_prop threshold will be assigned to the worst score of the ones that do. False by default.

key_added (str (default: 'liana_res')) – Key under which the results will be stored in adata.uns if inplace is True.

use_raw (bool | None (default: True)) – Use raw attribute of adata if present.

layer (str | None (default: None)) – Layer in anndata.AnnData.layers to use. If None, use anndata.AnnData.X.

de_method (str (default: 't-test')) – Differential expression method. scanpy.tl.rank_genes_groups is used to rank genes according to 1vsRest. The default method is ‘t-test’.

verbose (bool | None (default: False)) – Verbosity flag.

n_perms (int (default: 1000)) – Number of permutations for the permutation test. Relevant only for permutation-based methods (e.g., CellPhoneDB). If None is passed, no permutation testing is performed.

seed (int (default: 1337)) – Random seed for reproducibility.

n_jobs (int (default: 1)) – Number of jobs to run in parallel.

resource (DataFrame | None (default: None)) – A pandas dataframe with [ligand, receptor] columns. If provided will overrule the resource requested via resource_name

interactions (list | None (default: None)) – List of tuples with ligand-receptor pairs [(ligand, receptor), ...] to be used for the analysis. If passed, it will overrule the resource requested via resource and resource_name.

mdata_kwargs (dict | None (default: None)) – Keyword arguments to be passed to li.fun.mdata_to_anndata if adata is an instance of MuData. If an AnnData object is passed, these arguments are ignored.

inplace (bool (default: True)) – Whether to store results in place, or else to return them.

If inplace = False, returns a DataFrame with ligand-receptor results Otherwise, modifies the adata object with the following key: - anndata.AnnData.uns [`key_added`] with the aforementioned DataFrame

liana.method.cellphonedb.__call__

liana.method.logfc.__call__

By Daniel Dimitrov, Philipp Sven Lars Schäfer, Elias Farr, Pablo Rodriguez-Mier, Sebastian Lobentanzer, Pau Badia-i-Mompel, Aurelien Dugourd, Jovan Tanevski, Ricardo Omar Ramirez Flores, Julio Saez-Rodriguez

© Copyright 2025, Daniel Dimitrov, Philipp Sven Lars Schäfer, Elias Farr, Pablo Rodriguez-Mier, Sebastian Lobentanzer, Pau Badia-i-Mompel, Aurelien Dugourd, Jovan Tanevski, Ricardo Omar Ramirez Flores, Julio Saez-Rodriguez..

**Examples:**

Example 1 (unknown):
```unknown
connectome.__call__()
```

Example 2 (unknown):
```unknown
'consensus'
```

Example 3 (unknown):
```unknown
li.rs.show_resources()
```

Example 4 (python):
```python
np.float64(2.718281828459045)
```

Example 5 (unknown):
```unknown
scanpy.tl.rank_genes_groups
```

Example 6 (unknown):
```unknown
['ligand_pvals', 'receptor_pvals']
```

Example 7 (unknown):
```unknown
'liana_res'
```

Example 8 (unknown):
```unknown
scanpy.tl.rank_genes_groups
```

Example 9 (unknown):
```unknown
CellPhoneDB
```

Example 10 (unknown):
```unknown
resource_name
```

Example 11 (unknown):
```unknown
[(ligand, receptor), ...]
```

Example 12 (unknown):
```unknown
resource_name
```

Example 13 (unknown):
```unknown
li.fun.mdata_to_anndata
```

Example 14 (unknown):
```unknown
inplace = False
```

Example 15 (unknown):
```unknown
anndata.AnnData.uns
```

Example 16 (unknown):
```unknown
[`key_added`]
```

Example 17 (unknown):
```unknown
connectome.__call__()
```

---

## liana.plotting.contributions — liana

**URL:** http://127.0.0.1:9050/en_latest_generated_liana.plotting.contributions.html

**Contents:**
- liana.plotting.contributions
- Contents
- liana.plotting.contributions#

Plot view contributions per target.

misty (default: None) – MistyData object with modelling results

target_metrics (default: None) – A target_metrics DataFrame

view_names (list (default: None)) – A list of view names to plot

aggregate_fun (callable (default: None)) – A function used to aggregate the results to be plotted.

figure_size (tuple (default: (5, 5))) – Figure x,y size

return_fig (bool (default: True)) – bool whether to return the fig object.

liana.plotting.target_metrics

liana.plotting.interactions

By Daniel Dimitrov, Philipp Sven Lars Schäfer, Elias Farr, Pablo Rodriguez-Mier, Sebastian Lobentanzer, Pau Badia-i-Mompel, Aurelien Dugourd, Jovan Tanevski, Ricardo Omar Ramirez Flores, Julio Saez-Rodriguez

© Copyright 2025, Daniel Dimitrov, Philipp Sven Lars Schäfer, Elias Farr, Pablo Rodriguez-Mier, Sebastian Lobentanzer, Pau Badia-i-Mompel, Aurelien Dugourd, Jovan Tanevski, Ricardo Omar Ramirez Flores, Julio Saez-Rodriguez..

**Examples:**

Example 1 (unknown):
```unknown
contributions()
```

Example 2 (unknown):
```unknown
contributions()
```

---

## liana.method.natmi.__call__ — liana

**URL:** http://127.0.0.1:9050/en_latest_generated_liana.method.natmi.__call__.html

**Contents:**
- liana.method.natmi.__call__
- Contents
- liana.method.natmi.__call__#

Run a ligand-receptor method.

adata (AnnData | MuData) – Annotated data object.

groupby (str) – Key to be used for grouping.

resource_name (str (default: 'consensus')) – Name of the resource to be used for ligand-receptor inference. See li.rs.show_resources() for available resources.

expr_prop (float (default: 0.1)) – Minimum expression proportion for the ligands and receptors (+ their subunits) in the corresponding cell identities. Set to 0 to return unfiltered results.

min_cells (int (default: 5)) – Minimum cells (per cell identity if grouped by groupby) to be considered for downstream analysis.

groupby_pairs (DataFrame | None (default: None)) – A DataFrame with columns source and target to be used to subset the possible combinations of interacting cell types. If None, all possible combinations are used.

base (float (default: np.float64(2.718281828459045))) – Exponent base used to reverse the log-transformation of the matrix. Relevant only for the logfc method.

supp_columns (list | None (default: None)) – Additional columns to be added from any of the methods implemented in liana, or any of the columns returned by scanpy.tl.rank_genes_groups, each starting with ligand_* or receptor_*. For example, ['ligand_pvals', 'receptor_pvals']. None by default.

return_all_lrs (bool (default: False)) – Bool whether to return all ligand-receptor pairs, or only those that surpass the expr_prop threshold. Ligand-receptor pairs that do not pass the expr_prop threshold will be assigned to the worst score of the ones that do. False by default.

key_added (str (default: 'liana_res')) – Key under which the results will be stored in adata.uns if inplace is True.

use_raw (bool | None (default: True)) – Use raw attribute of adata if present.

layer (str | None (default: None)) – Layer in anndata.AnnData.layers to use. If None, use anndata.AnnData.X.

de_method (str (default: 't-test')) – Differential expression method. scanpy.tl.rank_genes_groups is used to rank genes according to 1vsRest. The default method is ‘t-test’.

verbose (bool | None (default: False)) – Verbosity flag.

n_perms (int (default: 1000)) – Number of permutations for the permutation test. Relevant only for permutation-based methods (e.g., CellPhoneDB). If None is passed, no permutation testing is performed.

seed (int (default: 1337)) – Random seed for reproducibility.

n_jobs (int (default: 1)) – Number of jobs to run in parallel.

resource (DataFrame | None (default: None)) – A pandas dataframe with [ligand, receptor] columns. If provided will overrule the resource requested via resource_name

interactions (list | None (default: None)) – List of tuples with ligand-receptor pairs [(ligand, receptor), ...] to be used for the analysis. If passed, it will overrule the resource requested via resource and resource_name.

mdata_kwargs (dict | None (default: None)) – Keyword arguments to be passed to li.fun.mdata_to_anndata if adata is an instance of MuData. If an AnnData object is passed, these arguments are ignored.

inplace (bool (default: True)) – Whether to store results in place, or else to return them.

If inplace = False, returns a DataFrame with ligand-receptor results Otherwise, modifies the adata object with the following key: - anndata.AnnData.uns [`key_added`] with the aforementioned DataFrame

liana.method.logfc.__call__

liana.method.singlecellsignalr.__call__

By Daniel Dimitrov, Philipp Sven Lars Schäfer, Elias Farr, Pablo Rodriguez-Mier, Sebastian Lobentanzer, Pau Badia-i-Mompel, Aurelien Dugourd, Jovan Tanevski, Ricardo Omar Ramirez Flores, Julio Saez-Rodriguez

© Copyright 2025, Daniel Dimitrov, Philipp Sven Lars Schäfer, Elias Farr, Pablo Rodriguez-Mier, Sebastian Lobentanzer, Pau Badia-i-Mompel, Aurelien Dugourd, Jovan Tanevski, Ricardo Omar Ramirez Flores, Julio Saez-Rodriguez..

**Examples:**

Example 1 (unknown):
```unknown
natmi.__call__()
```

Example 2 (unknown):
```unknown
'consensus'
```

Example 3 (unknown):
```unknown
li.rs.show_resources()
```

Example 4 (python):
```python
np.float64(2.718281828459045)
```

Example 5 (unknown):
```unknown
scanpy.tl.rank_genes_groups
```

Example 6 (unknown):
```unknown
['ligand_pvals', 'receptor_pvals']
```

Example 7 (unknown):
```unknown
'liana_res'
```

Example 8 (unknown):
```unknown
scanpy.tl.rank_genes_groups
```

Example 9 (unknown):
```unknown
CellPhoneDB
```

Example 10 (unknown):
```unknown
resource_name
```

Example 11 (unknown):
```unknown
[(ligand, receptor), ...]
```

Example 12 (unknown):
```unknown
resource_name
```

Example 13 (unknown):
```unknown
li.fun.mdata_to_anndata
```

Example 14 (unknown):
```unknown
inplace = False
```

Example 15 (unknown):
```unknown
anndata.AnnData.uns
```

Example 16 (unknown):
```unknown
[`key_added`]
```

Example 17 (unknown):
```unknown
natmi.__call__()
```

---

## liana.method.rank_aggregate.__call__ — liana

**URL:** http://127.0.0.1:9050/en_latest_generated_liana.method.rank_aggregate.__call__.html

**Contents:**
- liana.method.rank_aggregate.__call__
- Contents
- liana.method.rank_aggregate.__call__#

Get an aggregate of ligand-receptor scores from multiple methods.

adata (AnnData | MuData) – Annotated data object.

groupby (str) – Key to be used for grouping.

resource_name (str (default: 'consensus')) – Name of the resource to be used for ligand-receptor inference. See li.rs.show_resources() for available resources.

expr_prop (float (default: 0.1)) – Minimum expression proportion for the ligands and receptors (+ their subunits) in the corresponding cell identities. Set to 0 to return unfiltered results.

min_cells (int (default: 5)) – Minimum cells (per cell identity if grouped by groupby) to be considered for downstream analysis.

groupby_pairs (DataFrame | None (default: None)) – A DataFrame with columns source and target to be used to subset the possible combinations of interacting cell types. If None, all possible combinations are used.

base (float (default: np.float64(2.718281828459045))) – Exponent base used to reverse the log-transformation of the matrix. Relevant only for the logfc method.

aggregate_method (str (default: 'rra')) – Method aggregation approach, one of [‘mean’, ‘rra’], where mean represents the mean rank, while ‘rra’ is the RobustRankAggregate (Kolde et al., 2014) of the interactions

consensus_opts (list | None (default: None)) – Strategies to aggregate interactions across methods. Default is None - i.e. [‘Specificity’, ‘Magnitude’] and both specificity and magnitude are aggregated.

return_all_lrs (bool (default: False)) – Bool whether to return all ligand-receptor pairs, or only those that surpass the expr_prop threshold. Ligand-receptor pairs that do not pass the expr_prop threshold will be assigned to the worst score of the ones that do. False by default.

key_added (str (default: 'liana_res')) – Key under which the results will be stored in adata.uns if inplace is True.

use_raw (bool | None (default: True)) – Use raw attribute of adata if present.

layer (str | None (default: None)) – Layer in anndata.AnnData.layers to use. If None, use anndata.AnnData.X.

de_method (str (default: 't-test')) – Differential expression method. scanpy.tl.rank_genes_groups is used to rank genes according to 1vsRest. The default method is ‘t-test’.

verbose (bool | None (default: False)) – Verbosity flag.

n_perms (int (default: 1000)) – Number of permutations for the permutation test. Relevant only for permutation-based methods (e.g., CellPhoneDB). If None is passed, no permutation testing is performed.

seed (int (default: 1337)) – Random seed for reproducibility.

n_jobs (int (default: 1)) – Number of jobs to run in parallel.

resource (DataFrame | None (default: None)) – A pandas dataframe with [ligand, receptor] columns. If provided will overrule the resource requested via resource_name

interactions (list | None (default: None)) – List of tuples with ligand-receptor pairs [(ligand, receptor), ...] to be used for the analysis. If passed, it will overrule the resource requested via resource and resource_name.

mdata_kwargs (dict | None (default: None)) – Keyword arguments to be passed to li.fun.mdata_to_anndata if adata is an instance of MuData. If an AnnData object is passed, these arguments are ignored.

inplace (bool (default: True)) – Whether to store results in place, or else to return them.

If inplace = False, returns a DataFrame with ligand-receptor results Otherwise, modifies the adata object with the following key: anndata.AnnData.uns ['liana_res'] with the aforementioned DataFrame

If inplace = False, returns a DataFrame with ligand-receptor results Otherwise, modifies the adata object with the following key:

anndata.AnnData.uns ['liana_res'] with the aforementioned DataFrame

liana.method.geometric_mean.__call__

liana.method.bivariate.__call__

By Daniel Dimitrov, Philipp Sven Lars Schäfer, Elias Farr, Pablo Rodriguez-Mier, Sebastian Lobentanzer, Pau Badia-i-Mompel, Aurelien Dugourd, Jovan Tanevski, Ricardo Omar Ramirez Flores, Julio Saez-Rodriguez

© Copyright 2025, Daniel Dimitrov, Philipp Sven Lars Schäfer, Elias Farr, Pablo Rodriguez-Mier, Sebastian Lobentanzer, Pau Badia-i-Mompel, Aurelien Dugourd, Jovan Tanevski, Ricardo Omar Ramirez Flores, Julio Saez-Rodriguez..

**Examples:**

Example 1 (unknown):
```unknown
rank_aggregate.__call__()
```

Example 2 (unknown):
```unknown
'consensus'
```

Example 3 (unknown):
```unknown
li.rs.show_resources()
```

Example 4 (python):
```python
np.float64(2.718281828459045)
```

Example 5 (unknown):
```unknown
'liana_res'
```

Example 6 (unknown):
```unknown
scanpy.tl.rank_genes_groups
```

Example 7 (unknown):
```unknown
CellPhoneDB
```

Example 8 (unknown):
```unknown
resource_name
```

Example 9 (unknown):
```unknown
[(ligand, receptor), ...]
```

Example 10 (unknown):
```unknown
resource_name
```

Example 11 (unknown):
```unknown
li.fun.mdata_to_anndata
```

Example 12 (unknown):
```unknown
inplace = False
```

Example 13 (unknown):
```unknown
anndata.AnnData.uns
```

Example 14 (unknown):
```unknown
['liana_res']
```

Example 15 (unknown):
```unknown
rank_aggregate.__call__()
```

---

## liana.multi.adata_to_views — liana

**URL:** http://127.0.0.1:9050/en_latest_generated_liana.multi.adata_to_views.html

**Contents:**
- liana.multi.adata_to_views
- Contents
- liana.multi.adata_to_views#

Converts an AnnData object to a MuData object with views that represent an aggregate for each entity in adata.obs[groupby].

adata (AnnData) – Annotated data object.

groupby (str) – Key to be used for grouping.

sample_key (str) – key in adata.obs to use for grouping by sample or context.

obs_keys (list (default: None)) – Column names in adata.obs to merge with the MuData object

view_sep (str (default: ':')) – Separator to use when assigning adata.var_names to views

min_count – Minimum number of counts per gene per sample to be included in the pseudobulk.

min_total_count – Minimum number of counts per sample to be included in the pseudobulk.

large_n – Number of samples per group that is considered to be “large”.

min_prop – Minimum proportion of samples that must have a count for a gene to be included in the pseudobulk.

keep_stats (bool (default: False)) – If True, keep the pseudobulk statistics in mdata.uns['psbulk_stats']. Default is False.

verbose (bool (default: False)) – Verbosity flag.

psbulk_kwargs (dict (default: None)) – Arguments to pass to dc.pp.pseudobulk for pseudobulking. See decoupler documentation for more details.

filter_samples_kwargs (dict (default: None)) – Arguments to pass to dc.pp.filter_samples for filtering samples. See decoupler documentation for more details. If None, won’t filter.

filter_by_expr_kwargs (dict (default: None)) – Optional mapping of arguments to pass to dc.pp.filter_by_expr for gene filtering by expression. If None, won’t filter.

filter_by_prop_kwargs (dict (default: None)) – Optional mapping of arguments to pass to dc.pp.filter_by_prop for gene filtering by proportion of cells that express the gene. If None, won’t filter.

Returns a MuData object with views that represent an aggregate for each entity in adata.obs[groupby].

liana.multi.to_tensor_c2c

liana.multi.lrs_to_views

By Daniel Dimitrov, Philipp Sven Lars Schäfer, Elias Farr, Pablo Rodriguez-Mier, Sebastian Lobentanzer, Pau Badia-i-Mompel, Aurelien Dugourd, Jovan Tanevski, Ricardo Omar Ramirez Flores, Julio Saez-Rodriguez

© Copyright 2025, Daniel Dimitrov, Philipp Sven Lars Schäfer, Elias Farr, Pablo Rodriguez-Mier, Sebastian Lobentanzer, Pau Badia-i-Mompel, Aurelien Dugourd, Jovan Tanevski, Ricardo Omar Ramirez Flores, Julio Saez-Rodriguez..

**Examples:**

Example 1 (python):
```python
adata_to_views()
```

Example 2 (python):
```python
adata.obs[groupby]
```

Example 3 (python):
```python
adata.var_names
```

Example 4 (unknown):
```unknown
mdata.uns['psbulk_stats']
```

Example 5 (unknown):
```unknown
dc.pp.pseudobulk
```

Example 6 (unknown):
```unknown
dc.pp.filter_samples
```

Example 7 (unknown):
```unknown
dc.pp.filter_by_expr
```

Example 8 (unknown):
```unknown
dc.pp.filter_by_prop
```

Example 9 (python):
```python
adata.obs[groupby]
```

Example 10 (python):
```python
adata_to_views()
```

---

## liana.plotting.target_metrics — liana

**URL:** http://127.0.0.1:9050/en_latest_generated_liana.plotting.target_metrics.html

**Contents:**
- liana.plotting.target_metrics
- Contents
- liana.plotting.target_metrics#

misty (default: None) – MistyData object with modelling results

stat (str) – Statistic to plot

target_metrics (default: None) – A target_metrics DataFrame

top_n (default: None) – top_n entities to plot.

ascending (bool) – Whether to sort in ascending order

key (callable) – Function to use to sort the dataframe

filter_fun (callable (default: None)) – A function, applied along the columns (axis=1), used to filter the results to be plotted.

aggregate_fun (default: None) – A function used to aggregate the results to be plotted.

figure_size (tuple (default: (5, 5))) – Figure x,y size

return_fig (bool (default: True)) – bool whether to return the fig object.

Returns a plotnine plot.

liana.plotting.connectivity

liana.plotting.contributions

By Daniel Dimitrov, Philipp Sven Lars Schäfer, Elias Farr, Pablo Rodriguez-Mier, Sebastian Lobentanzer, Pau Badia-i-Mompel, Aurelien Dugourd, Jovan Tanevski, Ricardo Omar Ramirez Flores, Julio Saez-Rodriguez

© Copyright 2025, Daniel Dimitrov, Philipp Sven Lars Schäfer, Elias Farr, Pablo Rodriguez-Mier, Sebastian Lobentanzer, Pau Badia-i-Mompel, Aurelien Dugourd, Jovan Tanevski, Ricardo Omar Ramirez Flores, Julio Saez-Rodriguez..

**Examples:**

Example 1 (unknown):
```unknown
target_metrics()
```

Example 2 (unknown):
```unknown
target_metrics()
```

---

## liana.plotting.dotplot_by_sample — liana

**URL:** http://127.0.0.1:9050/en_latest_generated_liana.plotting.dotplot_by_sample.html

**Contents:**
- liana.plotting.dotplot_by_sample
- Contents
- liana.plotting.dotplot_by_sample#

A dotplot of interactions by sample

adata (AnnData (default: None))

object. (Annotated data)

uns_key (str (default: 'liana_res'))

'liana_res'. (Key in adata.uns that contains the LIANA results. Default is)

liana_res (DataFrame (default: None))

format. (liana_res a DataFrame in liana's)

sample_key (str (default: 'sample')) – sample_key used to group different samples/contexts from liana_res. Defaults to ‘sample’.

colour (str (default: None))

dots. (column in liana_res to define the size of the)

inverse_colour (bool (default: False))

default. (Whether to -log10 the size column for plotting. False by)

inverse_size (bool (default: False))

source_labels (str | None (default: None))

source (List of labels to use as)

out. (the rest are filtered)

target_labels (str | None (default: None))

target (List of labels to use as)

ligand_complex (list | str | None (default: None))

None. (list of receptor complexes to filter the interactions to be plotted. Defaults to)

receptor_complex (list | str | None (default: None))

size_range (tuple (default: (2, 9)))

(min (Define size range. Tuple of)

cmap (str (default: 'viridis'))

plotting. (Colour map to use for)

figure_size (tuple (default: (8, 6)))

Returns a ggplot for the specified interactions by sample.

liana.plotting.dotplot

liana.plotting.tileplot

By Daniel Dimitrov, Philipp Sven Lars Schäfer, Elias Farr, Pablo Rodriguez-Mier, Sebastian Lobentanzer, Pau Badia-i-Mompel, Aurelien Dugourd, Jovan Tanevski, Ricardo Omar Ramirez Flores, Julio Saez-Rodriguez

© Copyright 2025, Daniel Dimitrov, Philipp Sven Lars Schäfer, Elias Farr, Pablo Rodriguez-Mier, Sebastian Lobentanzer, Pau Badia-i-Mompel, Aurelien Dugourd, Jovan Tanevski, Ricardo Omar Ramirez Flores, Julio Saez-Rodriguez..

**Examples:**

Example 1 (unknown):
```unknown
dotplot_by_sample()
```

Example 2 (unknown):
```unknown
'liana_res'
```

Example 3 (unknown):
```unknown
dotplot_by_sample()
```

---

## liana.plotting.interactions — liana

**URL:** http://127.0.0.1:9050/en_latest_generated_liana.plotting.interactions.html

**Contents:**
- liana.plotting.interactions
- Contents
- liana.plotting.interactions#

Plot interaction importances.

misty (default: None) – MistyData object with modelling results

view (str) – A view to plot

top_n (default: None) – top_n entities to plot.

ascending (bool) – Whether to sort interactions in ascending order

key (str) – Key to use when sorting interactions

filter_fun (callable (default: None)) – A function, applied along the columns (axis=1), used to filter the results to be plotted.

aggregate_fun (callable (default: None)) – A function used to aggregate the results to be plotted.

figure_size (tuple (default: (5, 5))) – Figure x,y size

return_fig (bool (default: True)) – bool whether to return the fig object.

liana.plotting.contributions

liana.utils.obsm_to_adata

By Daniel Dimitrov, Philipp Sven Lars Schäfer, Elias Farr, Pablo Rodriguez-Mier, Sebastian Lobentanzer, Pau Badia-i-Mompel, Aurelien Dugourd, Jovan Tanevski, Ricardo Omar Ramirez Flores, Julio Saez-Rodriguez

© Copyright 2025, Daniel Dimitrov, Philipp Sven Lars Schäfer, Elias Farr, Pablo Rodriguez-Mier, Sebastian Lobentanzer, Pau Badia-i-Mompel, Aurelien Dugourd, Jovan Tanevski, Ricardo Omar Ramirez Flores, Julio Saez-Rodriguez..

**Examples:**

Example 1 (unknown):
```unknown
interactions()
```

Example 2 (unknown):
```unknown
interactions()
```

---

## liana.method.logfc.__call__ — liana

**URL:** http://127.0.0.1:9050/en_latest_generated_liana.method.logfc.__call__.html

**Contents:**
- liana.method.logfc.__call__
- Contents
- liana.method.logfc.__call__#

Run a ligand-receptor method.

adata (AnnData | MuData) – Annotated data object.

groupby (str) – Key to be used for grouping.

resource_name (str (default: 'consensus')) – Name of the resource to be used for ligand-receptor inference. See li.rs.show_resources() for available resources.

expr_prop (float (default: 0.1)) – Minimum expression proportion for the ligands and receptors (+ their subunits) in the corresponding cell identities. Set to 0 to return unfiltered results.

min_cells (int (default: 5)) – Minimum cells (per cell identity if grouped by groupby) to be considered for downstream analysis.

groupby_pairs (DataFrame | None (default: None)) – A DataFrame with columns source and target to be used to subset the possible combinations of interacting cell types. If None, all possible combinations are used.

base (float (default: np.float64(2.718281828459045))) – Exponent base used to reverse the log-transformation of the matrix. Relevant only for the logfc method.

supp_columns (list | None (default: None)) – Additional columns to be added from any of the methods implemented in liana, or any of the columns returned by scanpy.tl.rank_genes_groups, each starting with ligand_* or receptor_*. For example, ['ligand_pvals', 'receptor_pvals']. None by default.

return_all_lrs (bool (default: False)) – Bool whether to return all ligand-receptor pairs, or only those that surpass the expr_prop threshold. Ligand-receptor pairs that do not pass the expr_prop threshold will be assigned to the worst score of the ones that do. False by default.

key_added (str (default: 'liana_res')) – Key under which the results will be stored in adata.uns if inplace is True.

use_raw (bool | None (default: True)) – Use raw attribute of adata if present.

layer (str | None (default: None)) – Layer in anndata.AnnData.layers to use. If None, use anndata.AnnData.X.

de_method (str (default: 't-test')) – Differential expression method. scanpy.tl.rank_genes_groups is used to rank genes according to 1vsRest. The default method is ‘t-test’.

verbose (bool | None (default: False)) – Verbosity flag.

n_perms (int (default: 1000)) – Number of permutations for the permutation test. Relevant only for permutation-based methods (e.g., CellPhoneDB). If None is passed, no permutation testing is performed.

seed (int (default: 1337)) – Random seed for reproducibility.

n_jobs (int (default: 1)) – Number of jobs to run in parallel.

resource (DataFrame | None (default: None)) – A pandas dataframe with [ligand, receptor] columns. If provided will overrule the resource requested via resource_name

interactions (list | None (default: None)) – List of tuples with ligand-receptor pairs [(ligand, receptor), ...] to be used for the analysis. If passed, it will overrule the resource requested via resource and resource_name.

mdata_kwargs (dict | None (default: None)) – Keyword arguments to be passed to li.fun.mdata_to_anndata if adata is an instance of MuData. If an AnnData object is passed, these arguments are ignored.

inplace (bool (default: True)) – Whether to store results in place, or else to return them.

If inplace = False, returns a DataFrame with ligand-receptor results Otherwise, modifies the adata object with the following key: - anndata.AnnData.uns [`key_added`] with the aforementioned DataFrame

liana.method.connectome.__call__

liana.method.natmi.__call__

By Daniel Dimitrov, Philipp Sven Lars Schäfer, Elias Farr, Pablo Rodriguez-Mier, Sebastian Lobentanzer, Pau Badia-i-Mompel, Aurelien Dugourd, Jovan Tanevski, Ricardo Omar Ramirez Flores, Julio Saez-Rodriguez

© Copyright 2025, Daniel Dimitrov, Philipp Sven Lars Schäfer, Elias Farr, Pablo Rodriguez-Mier, Sebastian Lobentanzer, Pau Badia-i-Mompel, Aurelien Dugourd, Jovan Tanevski, Ricardo Omar Ramirez Flores, Julio Saez-Rodriguez..

**Examples:**

Example 1 (unknown):
```unknown
logfc.__call__()
```

Example 2 (unknown):
```unknown
'consensus'
```

Example 3 (unknown):
```unknown
li.rs.show_resources()
```

Example 4 (python):
```python
np.float64(2.718281828459045)
```

Example 5 (unknown):
```unknown
scanpy.tl.rank_genes_groups
```

Example 6 (unknown):
```unknown
['ligand_pvals', 'receptor_pvals']
```

Example 7 (unknown):
```unknown
'liana_res'
```

Example 8 (unknown):
```unknown
scanpy.tl.rank_genes_groups
```

Example 9 (unknown):
```unknown
CellPhoneDB
```

Example 10 (unknown):
```unknown
resource_name
```

Example 11 (unknown):
```unknown
[(ligand, receptor), ...]
```

Example 12 (unknown):
```unknown
resource_name
```

Example 13 (unknown):
```unknown
li.fun.mdata_to_anndata
```

Example 14 (unknown):
```unknown
inplace = False
```

Example 15 (unknown):
```unknown
anndata.AnnData.uns
```

Example 16 (unknown):
```unknown
[`key_added`]
```

Example 17 (unknown):
```unknown
logfc.__call__()
```

---

## liana.resource.show_resources — liana

**URL:** http://127.0.0.1:9050/en_latest_generated_liana.resource.show_resources.html

**Contents:**
- liana.resource.show_resources
- Contents
- liana.resource.show_resources#

Show available resources.

A list of resource names available via liana.resource.select_resource

liana.resource.select_resource

liana.resource.generate_lr_geneset

By Daniel Dimitrov, Philipp Sven Lars Schäfer, Elias Farr, Pablo Rodriguez-Mier, Sebastian Lobentanzer, Pau Badia-i-Mompel, Aurelien Dugourd, Jovan Tanevski, Ricardo Omar Ramirez Flores, Julio Saez-Rodriguez

© Copyright 2025, Daniel Dimitrov, Philipp Sven Lars Schäfer, Elias Farr, Pablo Rodriguez-Mier, Sebastian Lobentanzer, Pau Badia-i-Mompel, Aurelien Dugourd, Jovan Tanevski, Ricardo Omar Ramirez Flores, Julio Saez-Rodriguez..

**Examples:**

Example 1 (unknown):
```unknown
show_resources()
```

Example 2 (unknown):
```unknown
liana.resource.select_resource
```

Example 3 (unknown):
```unknown
show_resources()
```

---

## liana.utils.get_factor_scores — liana

**URL:** http://127.0.0.1:9050/en_latest_generated_liana.utils.get_factor_scores.html

**Contents:**
- liana.utils.get_factor_scores
- Contents
- liana.utils.get_factor_scores#

Extract factor scores from an AnnData object.

adata (AnnData | MuData) – Annotated data object.

obsm_key (str) – Key to use when extracting factor scores from adata.obsm

obs_keys (list) – List of keys to use when extracting metadata from adata.obs If None, no metadata is extracted. Default is None.

Returns a pandas DataFrame with the factor scores.

liana.utils.spatial_neighbors

liana.utils.get_variable_loadings

By Daniel Dimitrov, Philipp Sven Lars Schäfer, Elias Farr, Pablo Rodriguez-Mier, Sebastian Lobentanzer, Pau Badia-i-Mompel, Aurelien Dugourd, Jovan Tanevski, Ricardo Omar Ramirez Flores, Julio Saez-Rodriguez

© Copyright 2025, Daniel Dimitrov, Philipp Sven Lars Schäfer, Elias Farr, Pablo Rodriguez-Mier, Sebastian Lobentanzer, Pau Badia-i-Mompel, Aurelien Dugourd, Jovan Tanevski, Ricardo Omar Ramirez Flores, Julio Saez-Rodriguez..

**Examples:**

Example 1 (unknown):
```unknown
get_factor_scores()
```

Example 2 (unknown):
```unknown
get_factor_scores()
```

---

## liana.method.lrMistyData — liana

**URL:** http://127.0.0.1:9050/en_latest_generated_liana.method.lrMistyData.html

**Contents:**
- liana.method.lrMistyData
- Contents
- liana.method.lrMistyData#

Generate a MistyData object from an AnnData object in ligand-receptor format.

adata (anndata.AnnData) – AnnData object

resource_name (str, optional (default: ‘consensus’)) – The name of the resource to use. See show_resources for available resources.

resource (pandas.DataFrame, optional (default: None)) – A resource in the form of a pandas DataFrame. If None, the resource is selected using select_resource.

nz_threshold (float, optional (default: 0.1)) – The threshold for the number of non-zero entries in each view.

use_raw (bool, optional (default: False)) – Whether to use the raw data of the AnnData object.

layer (str, optional (default: None)) – The layer of the AnnData object to use.

spatial_key (str, optional (default: ‘spatial’)) – The key in adata.obsm where the spatial coordinates are stored.

kernel (str, optional (default: ‘misty_rbf’)) – A radial basis function kernel to use for the generation of the connectivity matrix for the extra view. Default is ‘misty_rbf’, a kernel derivative of a Gaussian kernel.

bandwidth (float, optional (default: 100)) – The bandwidth of the kernel.

set_diag (bool, optional (default: True)) – Whether to set the diagonal of the connectivity matrix to 1.

cutoff (float, optional (default: 0.1)) – The minimum value cutoff for the connectivity matrix.

zoi (float, optional (default: 0)) – Zone of indifference of the kernel, i.e. the kernel is set to 0 for distances smaller than zoi.

verbose (bool, optional (default: False)) – Whether to print progress.

A MistyData object with receptors in the intra view & ligands in the extra view.

liana.method.genericMistyData

By Daniel Dimitrov, Philipp Sven Lars Schäfer, Elias Farr, Pablo Rodriguez-Mier, Sebastian Lobentanzer, Pau Badia-i-Mompel, Aurelien Dugourd, Jovan Tanevski, Ricardo Omar Ramirez Flores, Julio Saez-Rodriguez

© Copyright 2025, Daniel Dimitrov, Philipp Sven Lars Schäfer, Elias Farr, Pablo Rodriguez-Mier, Sebastian Lobentanzer, Pau Badia-i-Mompel, Aurelien Dugourd, Jovan Tanevski, Ricardo Omar Ramirez Flores, Julio Saez-Rodriguez..

**Examples:**

Example 1 (unknown):
```unknown
lrMistyData()
```

Example 2 (unknown):
```unknown
anndata.AnnData
```

Example 3 (unknown):
```unknown
show_resources
```

Example 4 (unknown):
```unknown
pandas.DataFrame
```

Example 5 (unknown):
```unknown
select_resource
```

Example 6 (unknown):
```unknown
lrMistyData()
```

---

## liana.resource.select_resource — liana

**URL:** http://127.0.0.1:9050/en_latest_generated_liana.resource.select_resource.html

**Contents:**
- liana.resource.select_resource
- Contents
- liana.resource.select_resource#

Read resource of choice from the pre-generated resources in LIANA.

resource_name (str (default: 'consensus')) – Name of the resource to be loaded and use for ligand-receptor inference.

A dataframe with ['ligand', 'receptor'] columns

liana.utils.interpolate_adata

liana.resource.show_resources

By Daniel Dimitrov, Philipp Sven Lars Schäfer, Elias Farr, Pablo Rodriguez-Mier, Sebastian Lobentanzer, Pau Badia-i-Mompel, Aurelien Dugourd, Jovan Tanevski, Ricardo Omar Ramirez Flores, Julio Saez-Rodriguez

© Copyright 2025, Daniel Dimitrov, Philipp Sven Lars Schäfer, Elias Farr, Pablo Rodriguez-Mier, Sebastian Lobentanzer, Pau Badia-i-Mompel, Aurelien Dugourd, Jovan Tanevski, Ricardo Omar Ramirez Flores, Julio Saez-Rodriguez..

**Examples:**

Example 1 (unknown):
```unknown
select_resource()
```

Example 2 (unknown):
```unknown
'consensus'
```

Example 3 (unknown):
```unknown
['ligand', 'receptor']
```

Example 4 (unknown):
```unknown
select_resource()
```

---

## liana.plotting.connectivity — liana

**URL:** http://127.0.0.1:9050/en_latest_generated_liana.plotting.connectivity.html

**Contents:**
- liana.plotting.connectivity
- Contents
- liana.plotting.connectivity#

Plot spatial connectivity weights.

adata (AnnData) – Annotated data object.

spatial_key (default: 'spatial') – Key in adata.obsm that contains the spatial coordinates. Default is 'spatial'.

connectivity_key (default: 'spatial_connectivities') – Key in adata.obsp that contains the spatial connectivity matrix. Default is 'spatial_connectivity'.

size (default: 1) – Size of the points

figure_size (default: (5.4, 5)) – Figure x,y size

return_fig (bool (default: True)) – bool whether to return the fig object.

A plotnine.ggplot instance

liana.plotting.tileplot

liana.plotting.target_metrics

By Daniel Dimitrov, Philipp Sven Lars Schäfer, Elias Farr, Pablo Rodriguez-Mier, Sebastian Lobentanzer, Pau Badia-i-Mompel, Aurelien Dugourd, Jovan Tanevski, Ricardo Omar Ramirez Flores, Julio Saez-Rodriguez

© Copyright 2025, Daniel Dimitrov, Philipp Sven Lars Schäfer, Elias Farr, Pablo Rodriguez-Mier, Sebastian Lobentanzer, Pau Badia-i-Mompel, Aurelien Dugourd, Jovan Tanevski, Ricardo Omar Ramirez Flores, Julio Saez-Rodriguez..

**Examples:**

Example 1 (unknown):
```unknown
connectivity()
```

Example 2 (unknown):
```unknown
'spatial_connectivities'
```

Example 3 (unknown):
```unknown
'spatial_connectivity'
```

Example 4 (unknown):
```unknown
plotnine.ggplot
```

Example 5 (unknown):
```unknown
connectivity()
```

---

## liana.utils.mdata_to_anndata — liana

**URL:** http://127.0.0.1:9050/en_latest_generated_liana.utils.mdata_to_anndata.html

**Contents:**
- liana.utils.mdata_to_anndata
- Contents
- liana.utils.mdata_to_anndata#

Convert a MultiData object to an AnnData object.

mdata – MuData object.

x_mod – Name of the modality to be used as x.

y_mod – Name of the modality to be used as y.

x_layer (default: None) – Layer to be used for modality x.

y_layer (default: None) – Layer to be used for modality y.

x_use_raw (default: False) – Whether to use raw counts for modality x.

y_use_raw (default: False) – Whether to use raw counts for modality y.

x_transform (default: None) – Transformation function to be applied to modality x.

y_transform (default: None) – Transformation function to be applied to modality y.

verbose (default: True) – Verbosity flag.

An AnnData object with the two modalities concatenated. Information related to observations (obs, obsp, obsm) and .uns are copied from the original MuData object.

liana.utils.obsm_to_adata

liana.utils.zi_minmax

By Daniel Dimitrov, Philipp Sven Lars Schäfer, Elias Farr, Pablo Rodriguez-Mier, Sebastian Lobentanzer, Pau Badia-i-Mompel, Aurelien Dugourd, Jovan Tanevski, Ricardo Omar Ramirez Flores, Julio Saez-Rodriguez

© Copyright 2025, Daniel Dimitrov, Philipp Sven Lars Schäfer, Elias Farr, Pablo Rodriguez-Mier, Sebastian Lobentanzer, Pau Badia-i-Mompel, Aurelien Dugourd, Jovan Tanevski, Ricardo Omar Ramirez Flores, Julio Saez-Rodriguez..

**Examples:**

Example 1 (unknown):
```unknown
mdata_to_anndata()
```

Example 2 (unknown):
```unknown
mdata_to_anndata()
```

---

## liana.method.genericMistyData — liana

**URL:** http://127.0.0.1:9050/en_latest_generated_liana.method.genericMistyData.html

**Contents:**
- liana.method.genericMistyData
- Contents
- liana.method.genericMistyData#

Construct a MistyData object from an AnnData object with views as presented in the manuscript.

intra (anndata.AnnData) – AnnData object with the intraview

intra_use_raw (bool, optional (default: False)) – Whether to use the raw data of the intraview.

intra_layer (str, optional (default: None)) – The layer of the intraview to use.

extra (anndata.AnnData, optional (default: None)) – AnnData object with the extraview(s). If None, the extraview is set to be the same as the intraview.

extra_use_raw (bool, optional (default: False)) – Whether to use the raw data of the extraview.

extra_layer (str, optional (default: None)) – The layer of the extraview(s) to use.

nz_threshold (float, optional (default: 0.1)) – The threshold for the number of non-zero entries in each view.

add_para (bool, optional (default: True)) – Whether to add the paraview.

spatial_key (str, optional (default: ‘spatial’)) – The key in adata.obsm where the spatial coordinates are stored.

set_diag (bool, optional (default: True)) – Whether to set the diagonal of the connectivity matrix to 1.

kernel (str, optional (default: ‘misty_rbf’)) – A radial basis function kernel to use for the generation of the connectivity matrix for the paraview. Default is ‘misty_rbf’, a kernel derivative of a Gaussian kernel.

bandwidth (float, optional (default: 100)) – The bandwidth of the kernel.

zoi (float, optional (default: 0)) – The zone of indifference of the kernel, i.e. the kernel is set to 0 for distances smaller than zoi.

cutoff (float, optional (default: 0.1)) – The cutoff for the connectivity matrix.

add_juxta (bool, optional (default: True)) – Whether to add the juxtaview. The juxtaview is constructed using only the nearest neighbors. A bandwidth of 5 times the bandwidth of the paraview is used to ensure that the nearest neighbors within the radius.

n_neighs (int, optional (default: 6)) – The number of neighbors to consider when constructing the juxtaview.

max_neighs (int, optional (default: 18)) – The maximum number of neighbors to consider when constructing the Paraview.

verbose (bool, optional (default: False)) – Whether to print progress.

MistyData object with the intra view, and two fixed extra view(s): para and juxta.

liana.method.MistyData

liana.method.lrMistyData

By Daniel Dimitrov, Philipp Sven Lars Schäfer, Elias Farr, Pablo Rodriguez-Mier, Sebastian Lobentanzer, Pau Badia-i-Mompel, Aurelien Dugourd, Jovan Tanevski, Ricardo Omar Ramirez Flores, Julio Saez-Rodriguez

© Copyright 2025, Daniel Dimitrov, Philipp Sven Lars Schäfer, Elias Farr, Pablo Rodriguez-Mier, Sebastian Lobentanzer, Pau Badia-i-Mompel, Aurelien Dugourd, Jovan Tanevski, Ricardo Omar Ramirez Flores, Julio Saez-Rodriguez..

**Examples:**

Example 1 (unknown):
```unknown
genericMistyData()
```

Example 2 (unknown):
```unknown
anndata.AnnData
```

Example 3 (unknown):
```unknown
anndata.AnnData
```

Example 4 (unknown):
```unknown
genericMistyData()
```

---

## liana.multi.lrs_to_views — liana

**URL:** http://127.0.0.1:9050/en_latest_generated_liana.multi.lrs_to_views.html

**Contents:**
- liana.multi.lrs_to_views
- Contents
- liana.multi.lrs_to_views#

Converts a LIANA result to a MuData object with views that represent an aggregate for each entity in adata.obs[groupby].

adata (AnnData) – Annotated data object.

score_key (str (default: None)) – Column name of the score in liana_res. If None, the score is inferred from the method.

inverse_fun (callable (default: <function DefaultValues.inverse_fun at 0x715ae615d300>)) – Function that is applied to the scores before building the views. Default is lambda x: 1 - x which is used to invert the scores reflect probabilities (e.g. magnitude_rank), i.e. such for which lower values reflect higher relevance. This is handled automatically for the scores in liana.

obs_keys (list (default: None)) – List of keys in adata.obs that should be included in the MuData object. These columns should correspond to the number of samples in adata.obs[sample_key].

lr_prop (float (default: 0.5)) – Reflects the minimum required proportion of samples for an interaction to be considered for building the views.

lr_fill (nan (default: nan)) – Value to fill in for interactions that are not present in a view. Default is np.nan.

lrs_per_sample (int (default: 10)) – Reflects the minimum required number of interactions in a sample to be considered when building a specific view.

lrs_per_view (int (default: 20)) – Reflects the minimum required number of interactions in a view to be considered for building the views.

samples_per_view (int (default: 3)) – Reflects the minimum required samples to keep a view.

min_variance (int (default: 0)) – Reflects the minimum required variance across samples for each interaction in each view. NaNs are ignored when computing the variance.

batch_key (default: None) – Key in adata.obs that represents the batch information. Used solely when computing the variance. If batch_key is not None, the variance is computed per batch, and the ``

min_var_nbatches (default: 1) – Reflect the minimum number of batches (>=) that must have a variance above min_variance for an interaction to be included in the view.

lr_sep (str (default: '^')) – Separator to use when joining ligand and receptor names into interactions.

cell_sep (str (default: '&')) – Separator to use for the cell names in the views.

var_sep (str (default: ':')) – Separator to use for the variable names in the views.

uns_key (str (default: 'liana_res')) – Key in adata.uns that contains the LIANA results. Default is 'liana_res'.

sample_key (str (default: 'sample')) – key in adata.obs to use for grouping by sample or context.

source_key (str (default: 'source')) – Column name of the sender/source cell types in liana_res.

target_key (str (default: 'target')) – Column name of the receiver/target cell types in liana_res.

ligand_key (str (default: 'ligand_complex')) – Column name of the ligand in liana_res.

receptor_key (str (default: 'receptor_complex')) – Column name of the receptor in liana_res.

verbose (bool (default: False)) – Verbosity flag.

Returns a MuData object with views that represent an aggregate for each entity in adata.obs[groupby].

liana.multi.adata_to_views

By Daniel Dimitrov, Philipp Sven Lars Schäfer, Elias Farr, Pablo Rodriguez-Mier, Sebastian Lobentanzer, Pau Badia-i-Mompel, Aurelien Dugourd, Jovan Tanevski, Ricardo Omar Ramirez Flores, Julio Saez-Rodriguez

© Copyright 2025, Daniel Dimitrov, Philipp Sven Lars Schäfer, Elias Farr, Pablo Rodriguez-Mier, Sebastian Lobentanzer, Pau Badia-i-Mompel, Aurelien Dugourd, Jovan Tanevski, Ricardo Omar Ramirez Flores, Julio Saez-Rodriguez..

**Examples:**

Example 1 (unknown):
```unknown
lrs_to_views()
```

Example 2 (python):
```python
adata.obs[groupby]
```

Example 3 (unknown):
```unknown
<function DefaultValues.inverse_fun at 0x715ae615d300>
```

Example 4 (unknown):
```unknown
lambda x: 1 - x
```

Example 5 (python):
```python
adata.obs[sample_key]
```

Example 6 (unknown):
```unknown
min_variance
```

Example 7 (unknown):
```unknown
'liana_res'
```

Example 8 (unknown):
```unknown
'liana_res'
```

Example 9 (unknown):
```unknown
'ligand_complex'
```

Example 10 (unknown):
```unknown
'receptor_complex'
```

Example 11 (python):
```python
adata.obs[groupby]
```

Example 12 (unknown):
```unknown
lrs_to_views()
```

---

## liana.method.bivariate.__call__ — liana

**URL:** http://127.0.0.1:9050/en_latest_generated_liana.method.bivariate.__call__.html

**Contents:**
- liana.method.bivariate.__call__
- Contents
- liana.method.bivariate.__call__#

A method for bivariate local spatial metrics.

mdata (MuData | AnnData) – MuData (multimodal) data object.

local_name (str | None (default: 'cosine')) – Name of the local function to use for the analysis. Passing None will return only the Global scores.

global_name (None | str | list (default: None)) – Name or names (list) of the global function(s) to use for the analysis. Passing None will not calculate any global scores

interactions (list (default: None)) – List of tuples with ligand-receptor pairs [(ligand, receptor), ...] to be used for the analysis. If passed, it will overrule the resource requested via resource and resource_name.

resource (DataFrame | None (default: None)) – A pandas dataframe with [ligand, receptor] columns. If provided will overrule the resource requested via resource_name

resource_name (str (default: None)) – Name of the resource to be used for ligand-receptor inference. See li.rs.show_resources() for available resources.

connectivity_key (str (default: 'spatial_connectivities')) – Key in adata.obsp that contains the spatial connectivity matrix. Default is 'spatial_connectivity'.

mask_negatives (bool (default: False)) – Whether to mask negative-negative (low-low) or uncategorized interactions.

add_categories (bool (default: False)) – Whether to add categories about the local scores.

n_perms (int (default: None)) – Number of permutations for the permutation test. If None, no p-values are computed.

seed (int (default: 1337)) – Random seed for reproducibility.

nz_prop (float) – Minimum proportion of non-zero values for each features. For example, if working with gene expression data, this would be the proportion of cells expressing a gene. Both features must have a proportion greater than nz_prop to be considered in the analysis.

complex_sep (str) – Separator to use for complex names.

xy_sep (str) – Separator to use for interaction names.

remove_self_interactions (bool) – Whether to remove self-interactions. True by default.

verbose (bool (default: False)) – Verbosity flag.

**kwargs (dict, optional) – Additional keyword arguments: - For AnnData: x_name Name of the x-variable. If passing a resource dataframe, this should match the first column. By default: ‘ligand’.y_name Name of the y-variable. If passing a resource dataframe, this should match the second column. By default: ‘receptor’. For MuData:x_mod Name of the modality to use for the x-axis.y_mod Name of the modality to use for the y-axis.x_name Name of the x-variable. If passing a resource dataframe, this should match the first column. By default: ‘x’.y_name Name of the y-variable. If passing a resource dataframe, this should match the second column. By default: ‘y’. x_use_raw: boolWhether to use the raw counts for the x-mod. y_use_raw: boolWhether to use the raw counts for y-mod. x_layer: strLayer to use for x-mod. y_layer: strLayer to use for y-mod. x_transform: boolFunction to transform the x-mod. y_transform: boolFunction to transform the y-mod.

Additional keyword arguments: - For AnnData:

Name of the y-variable. If passing a resource dataframe, this should match the second column. By default: ‘receptor’.

Whether to use the raw counts for the x-mod.

Whether to use the raw counts for y-mod.

Layer to use for x-mod.

Layer to use for y-mod.

Function to transform the x-mod.

Function to transform the y-mod.

AnnData | DataFrame | None

An AnnData object, (optionally) with multiple layers which correspond categories/p-values, and the actual scores are stored in .X. Moreover, global stats are stored in .var.

liana.method.rank_aggregate.__call__

liana.method.MistyData

By Daniel Dimitrov, Philipp Sven Lars Schäfer, Elias Farr, Pablo Rodriguez-Mier, Sebastian Lobentanzer, Pau Badia-i-Mompel, Aurelien Dugourd, Jovan Tanevski, Ricardo Omar Ramirez Flores, Julio Saez-Rodriguez

© Copyright 2025, Daniel Dimitrov, Philipp Sven Lars Schäfer, Elias Farr, Pablo Rodriguez-Mier, Sebastian Lobentanzer, Pau Badia-i-Mompel, Aurelien Dugourd, Jovan Tanevski, Ricardo Omar Ramirez Flores, Julio Saez-Rodriguez..

**Examples:**

Example 1 (unknown):
```unknown
bivariate.__call__()
```

Example 2 (unknown):
```unknown
[(ligand, receptor), ...]
```

Example 3 (unknown):
```unknown
resource_name
```

Example 4 (unknown):
```unknown
resource_name
```

Example 5 (unknown):
```unknown
li.rs.show_resources()
```

Example 6 (unknown):
```unknown
'spatial_connectivities'
```

Example 7 (unknown):
```unknown
'spatial_connectivity'
```

Example 8 (unknown):
```unknown
bivariate.__call__()
```

---

## liana.utils.spatial_neighbors — liana

**URL:** http://127.0.0.1:9050/en_latest_generated_liana.utils.spatial_neighbors.html

**Contents:**
- liana.utils.spatial_neighbors
- Contents
- liana.utils.spatial_neighbors#

Generate spatial connectivity weights using Euclidean distance.

adata (AnnData) – Annotated data object.

bandwidth (default: None) – Denotes signaling length (l) and controls the maximum distance at which two spots are considered. Corresponds to the units in which spatial coordinates are expressed.

cutoff (default: 0.1) – Values below this cutoff will be set to 0.

max_neighbours (default: 100) – Maximum nearest neighbours to be considered when generating spatial connectivity weights. Essentially, the maximum number of edges in the spatial connectivity graph.

kernel (default: 'gaussian') – Kernel function used to generate connectivity weights. It controls the shape of the connectivity weights. The following options are available: [‘gaussian’, ‘exponential’, ‘linear’, ‘misty_rbf’]

set_diag (default: False) – Logical, sets connectivity diagonal to 0 if False. Default is True.

zoi (default: 0) – Zone of indifference. Values below this cutoff will be set to np.inf.

standardize (default: False) – Whether to (l1) standardize spatial proximities (connectivities) so that they sum to 1. This plays a role when weighing border regions prior to downstream methods, as the number of spots in the border region (and hence the sum of proximities) is smaller than the number of spots in the center. Relevant for methods with unstandardized scores (e.g. product). Default is False.

reference (default: None) – Reference coordinates to use when generating spatial connectivity weights. If None, uses the spatial coordinates in adata.obsm[spatial_key]. This is only relevant if you want to use a different set of coordinates to generate spatial connectivity weights.

spatial_key (default: 'spatial') – Key in adata.obsm that contains the spatial coordinates. Default is 'spatial'.

key_added (default: 'spatial') – Key to add to adata.obsp if inplace = True. If reference is not None, key will be added to adata.obsm.

inplace (default: True) – Whether to store results in place, or else to return them.

This function is adapted from mistyR, and is set to be consistent with the squidpy.gr.spatial_neighbors function in the squidpy package.

If inplace = False, returns an np.array with spatial connectivity weights. Otherwise, modifies the adata object with the following key: anndata.AnnData.obsp ['{key_added}_connectivities'] with the aforementioned array

If inplace = False, returns an np.array with spatial connectivity weights. Otherwise, modifies the adata object with the following key:

anndata.AnnData.obsp ['{key_added}_connectivities'] with the aforementioned array

liana.utils.neg_to_zero

liana.utils.get_factor_scores

By Daniel Dimitrov, Philipp Sven Lars Schäfer, Elias Farr, Pablo Rodriguez-Mier, Sebastian Lobentanzer, Pau Badia-i-Mompel, Aurelien Dugourd, Jovan Tanevski, Ricardo Omar Ramirez Flores, Julio Saez-Rodriguez

© Copyright 2025, Daniel Dimitrov, Philipp Sven Lars Schäfer, Elias Farr, Pablo Rodriguez-Mier, Sebastian Lobentanzer, Pau Badia-i-Mompel, Aurelien Dugourd, Jovan Tanevski, Ricardo Omar Ramirez Flores, Julio Saez-Rodriguez..

**Examples:**

Example 1 (unknown):
```unknown
spatial_neighbors()
```

Example 2 (python):
```python
adata.obsm[spatial_key]
```

Example 3 (unknown):
```unknown
inplace = True
```

Example 4 (unknown):
```unknown
squidpy.gr.spatial_neighbors
```

Example 5 (unknown):
```unknown
inplace = False
```

Example 6 (unknown):
```unknown
anndata.AnnData.obsp
```

Example 7 (unknown):
```unknown
['{key_added}_connectivities']
```

Example 8 (unknown):
```unknown
spatial_neighbors()
```

---

## liana.multi.estimate_elbow — liana

**URL:** http://127.0.0.1:9050/en_latest_generated_liana.multi.estimate_elbow.html

**Contents:**
- liana.multi.estimate_elbow
- Contents
- liana.multi.estimate_elbow#

liana.plotting.dotplot

By Daniel Dimitrov, Philipp Sven Lars Schäfer, Elias Farr, Pablo Rodriguez-Mier, Sebastian Lobentanzer, Pau Badia-i-Mompel, Aurelien Dugourd, Jovan Tanevski, Ricardo Omar Ramirez Flores, Julio Saez-Rodriguez

© Copyright 2025, Daniel Dimitrov, Philipp Sven Lars Schäfer, Elias Farr, Pablo Rodriguez-Mier, Sebastian Lobentanzer, Pau Badia-i-Mompel, Aurelien Dugourd, Jovan Tanevski, Ricardo Omar Ramirez Flores, Julio Saez-Rodriguez..

**Examples:**

Example 1 (unknown):
```unknown
estimate_elbow()
```

Example 2 (unknown):
```unknown
estimate_elbow()
```

---

## liana.method.cellphonedb.__call__ — liana

**URL:** http://127.0.0.1:9050/en_latest_generated_liana.method.cellphonedb.__call__.html

**Contents:**
- liana.method.cellphonedb.__call__
- Contents
- liana.method.cellphonedb.__call__#

Run a ligand-receptor method.

adata (AnnData | MuData) – Annotated data object.

groupby (str) – Key to be used for grouping.

resource_name (str (default: 'consensus')) – Name of the resource to be used for ligand-receptor inference. See li.rs.show_resources() for available resources.

expr_prop (float (default: 0.1)) – Minimum expression proportion for the ligands and receptors (+ their subunits) in the corresponding cell identities. Set to 0 to return unfiltered results.

min_cells (int (default: 5)) – Minimum cells (per cell identity if grouped by groupby) to be considered for downstream analysis.

groupby_pairs (DataFrame | None (default: None)) – A DataFrame with columns source and target to be used to subset the possible combinations of interacting cell types. If None, all possible combinations are used.

base (float (default: np.float64(2.718281828459045))) – Exponent base used to reverse the log-transformation of the matrix. Relevant only for the logfc method.

supp_columns (list | None (default: None)) – Additional columns to be added from any of the methods implemented in liana, or any of the columns returned by scanpy.tl.rank_genes_groups, each starting with ligand_* or receptor_*. For example, ['ligand_pvals', 'receptor_pvals']. None by default.

return_all_lrs (bool (default: False)) – Bool whether to return all ligand-receptor pairs, or only those that surpass the expr_prop threshold. Ligand-receptor pairs that do not pass the expr_prop threshold will be assigned to the worst score of the ones that do. False by default.

key_added (str (default: 'liana_res')) – Key under which the results will be stored in adata.uns if inplace is True.

use_raw (bool | None (default: True)) – Use raw attribute of adata if present.

layer (str | None (default: None)) – Layer in anndata.AnnData.layers to use. If None, use anndata.AnnData.X.

de_method (str (default: 't-test')) – Differential expression method. scanpy.tl.rank_genes_groups is used to rank genes according to 1vsRest. The default method is ‘t-test’.

verbose (bool | None (default: False)) – Verbosity flag.

n_perms (int (default: 1000)) – Number of permutations for the permutation test. Relevant only for permutation-based methods (e.g., CellPhoneDB). If None is passed, no permutation testing is performed.

seed (int (default: 1337)) – Random seed for reproducibility.

n_jobs (int (default: 1)) – Number of jobs to run in parallel.

resource (DataFrame | None (default: None)) – A pandas dataframe with [ligand, receptor] columns. If provided will overrule the resource requested via resource_name

interactions (list | None (default: None)) – List of tuples with ligand-receptor pairs [(ligand, receptor), ...] to be used for the analysis. If passed, it will overrule the resource requested via resource and resource_name.

mdata_kwargs (dict | None (default: None)) – Keyword arguments to be passed to li.fun.mdata_to_anndata if adata is an instance of MuData. If an AnnData object is passed, these arguments are ignored.

inplace (bool (default: True)) – Whether to store results in place, or else to return them.

If inplace = False, returns a DataFrame with ligand-receptor results Otherwise, modifies the adata object with the following key: - anndata.AnnData.uns [`key_added`] with the aforementioned DataFrame

liana.method.cellchat.__call__

liana.method.connectome.__call__

By Daniel Dimitrov, Philipp Sven Lars Schäfer, Elias Farr, Pablo Rodriguez-Mier, Sebastian Lobentanzer, Pau Badia-i-Mompel, Aurelien Dugourd, Jovan Tanevski, Ricardo Omar Ramirez Flores, Julio Saez-Rodriguez

© Copyright 2025, Daniel Dimitrov, Philipp Sven Lars Schäfer, Elias Farr, Pablo Rodriguez-Mier, Sebastian Lobentanzer, Pau Badia-i-Mompel, Aurelien Dugourd, Jovan Tanevski, Ricardo Omar Ramirez Flores, Julio Saez-Rodriguez..

**Examples:**

Example 1 (unknown):
```unknown
cellphonedb.__call__()
```

Example 2 (unknown):
```unknown
'consensus'
```

Example 3 (unknown):
```unknown
li.rs.show_resources()
```

Example 4 (python):
```python
np.float64(2.718281828459045)
```

Example 5 (unknown):
```unknown
scanpy.tl.rank_genes_groups
```

Example 6 (unknown):
```unknown
['ligand_pvals', 'receptor_pvals']
```

Example 7 (unknown):
```unknown
'liana_res'
```

Example 8 (unknown):
```unknown
scanpy.tl.rank_genes_groups
```

Example 9 (unknown):
```unknown
CellPhoneDB
```

Example 10 (unknown):
```unknown
resource_name
```

Example 11 (unknown):
```unknown
[(ligand, receptor), ...]
```

Example 12 (unknown):
```unknown
resource_name
```

Example 13 (unknown):
```unknown
li.fun.mdata_to_anndata
```

Example 14 (unknown):
```unknown
inplace = False
```

Example 15 (unknown):
```unknown
anndata.AnnData.uns
```

Example 16 (unknown):
```unknown
[`key_added`]
```

Example 17 (unknown):
```unknown
cellphonedb.__call__()
```

---

## API — liana

**URL:** http://127.0.0.1:9050/en_latest_api.html

**Contents:**
- API
- Contents
- API#
- Single-cell#
  - Callable Ligand-Receptor Method instances#
- Spatial#
  - Local bivariate metrics#
  - Learn Spatial Relationships#
- Multi-Sample#
- Visualization#
- Utility#
- Prior knowledge#
- Intracellular#

Ligand-receptor method instances provide helper functions and consistent attributes, to describe each method instance, and are callable:

cellchat.__call__(groupby[, resource_name, ...])

Run a ligand-receptor method.

cellphonedb.__call__(groupby[, ...])

Run a ligand-receptor method.

connectome.__call__(groupby[, ...])

Run a ligand-receptor method.

logfc.__call__(groupby[, resource_name, ...])

Run a ligand-receptor method.

natmi.__call__(groupby[, resource_name, ...])

Run a ligand-receptor method.

singlecellsignalr.__call__(groupby[, ...])

Run a ligand-receptor method.

geometric_mean.__call__(groupby[, ...])

Run a ligand-receptor method.

rank_aggregate.__call__(groupby[, ...])

Get an aggregate of ligand-receptor scores from multiple methods.

bivariate.__call__([local_name, ...])

A method for bivariate local spatial metrics.

MistyData(data[, obs, spatial_key, enforce_obs])

MistyData Class used to construct multi-view objects

genericMistyData(intra[, intra_use_raw, ...])

Construct a MistyData object from an AnnData object with views as presented in the manuscript.

lrMistyData(adata[, resource_name, ...])

Generate a MistyData object from an AnnData object in ligand-receptor format.

df_to_lr(adata, dea_df, groupby, stat_keys)

Convert DEA results to ligand-receptor pairs.

to_tensor_c2c([adata, sample_key, ...])

Function to convert a LIANA result to a tensor for cell2cell analysis.

adata_to_views(adata, groupby, sample_key[, ...])

Converts an AnnData object to a MuData object with views that represent an aggregate for each entity in adata.obs[groupby].

lrs_to_views(adata[, score_key, ...])

Converts a LIANA result to a MuData object with views that represent an aggregate for each entity in adata.obs[groupby].

nmf([adata, df, n_components, k_range, ...])

Fits NMF to an AnnData object.

estimate_elbow(X, k_range[, verbose])

dotplot([adata, uns_key, liana_res, colour, ...])

Dotplot interactions by source and target cells

dotplot_by_sample([adata, uns_key, ...])

A dotplot of interactions by sample

tileplot([adata, liana_res, fill, label, ...])

Tileplot interactions by source and target cells

connectivity(adata, idx[, spatial_key, ...])

Plot spatial connectivity weights.

target_metrics([misty, stat, ...])

contributions([misty, target_metrics, ...])

Plot view contributions per target.

interactions([misty, interactions, view, ...])

Plot interaction importances.

obsm_to_adata(adata, obsm_key[, df, _uns, ...])

Extracts a dataframe from adata.obsm and returns a new AnnData object with the values stored in X.

mdata_to_anndata(mdata, x_mod, y_mod[, ...])

Convert a MultiData object to an AnnData object.

zi_minmax(X[, cutoff])

Zero-inflated min-max scaling, adopted from CiteFuse (Kim et al., 2020; https://academic.oup.com/bioinformatics/article/36/14/4137/5827474).

neg_to_zero(X[, cutoff])

Set negative values to 0.

spatial_neighbors(adata[, bandwidth, ...])

Generate spatial connectivity weights using Euclidean distance.

get_factor_scores(adata[, obsm_key, obs_keys])

Extract factor scores from an AnnData object.

get_variable_loadings(adata[, varm_key, ...])

Extract variable loadings from an AnnData object.

interpolate_adata(target, reference, spatial_key)

Interpolates spatial data from a target AnnData object to a reference AnnData object based on spatial coordinates.

select_resource([resource_name])

Read resource of choice from the pre-generated resources in LIANA.

Show available resources.

generate_lr_geneset(resource, net[, ...])

Generate a ligand-receptor gene set from a resource and a network.

explode_complexes(resource[, SOURCE, TARGET])

Function to explode ligand-receptor complexes

get_metalinks([db_path, types, ...])

Fetches edges of metabolite-proteins with specified annotations, applying filters if they are not None.

describe_metalinks([db_path, return_output])

Prints the schema information and foreign key details for all tables in the specified SQLite database.

get_metalinks_values(table_name, column_name)

Fetches distinct values from a specified column in a specified table.

find_causalnet(prior_graph, ...[, ...])

Find the causal network that best explains the input/output node scores.

build_prior_network(ppis, input_nodes, ...)

Build Prior Network from PPIs and input/output nodes.

estimate_metalinks(adata, resource, pd_net)

Estimate Metabolites from anndata object, and return a MuData object of metabolites and receptors.

LIANA+: an all-in-one cell-cell communication framework

liana.method.cellchat.__call__

By Daniel Dimitrov, Philipp Sven Lars Schäfer, Elias Farr, Pablo Rodriguez-Mier, Sebastian Lobentanzer, Pau Badia-i-Mompel, Aurelien Dugourd, Jovan Tanevski, Ricardo Omar Ramirez Flores, Julio Saez-Rodriguez

© Copyright 2025, Daniel Dimitrov, Philipp Sven Lars Schäfer, Elias Farr, Pablo Rodriguez-Mier, Sebastian Lobentanzer, Pau Badia-i-Mompel, Aurelien Dugourd, Jovan Tanevski, Ricardo Omar Ramirez Flores, Julio Saez-Rodriguez..

**Examples:**

Example 1 (python):
```python
import liana as li
```

Example 2 (unknown):
```unknown
cellchat.__call__
```

Example 3 (unknown):
```unknown
cellphonedb.__call__
```

Example 4 (unknown):
```unknown
connectome.__call__
```

Example 5 (unknown):
```unknown
logfc.__call__
```

Example 6 (unknown):
```unknown
natmi.__call__
```

Example 7 (unknown):
```unknown
singlecellsignalr.__call__
```

Example 8 (unknown):
```unknown
geometric_mean.__call__
```

Example 9 (unknown):
```unknown
rank_aggregate.__call__
```

Example 10 (unknown):
```unknown
bivariate.__call__
```

Example 11 (unknown):
```unknown
genericMistyData
```

Example 12 (unknown):
```unknown
lrMistyData
```

Example 13 (unknown):
```unknown
to_tensor_c2c
```

Example 14 (python):
```python
adata_to_views
```

Example 15 (python):
```python
adata.obs[groupby]
```

Example 16 (unknown):
```unknown
lrs_to_views
```

Example 17 (python):
```python
adata.obs[groupby]
```

Example 18 (unknown):
```unknown
estimate_elbow
```

Example 19 (unknown):
```unknown
dotplot_by_sample
```

Example 20 (unknown):
```unknown
connectivity
```

Example 21 (unknown):
```unknown
target_metrics
```

Example 22 (unknown):
```unknown
contributions
```

Example 23 (unknown):
```unknown
interactions
```

Example 24 (python):
```python
obsm_to_adata
```

Example 25 (unknown):
```unknown
mdata_to_anndata
```

Example 26 (unknown):
```unknown
neg_to_zero
```

Example 27 (unknown):
```unknown
spatial_neighbors
```

Example 28 (unknown):
```unknown
get_factor_scores
```

Example 29 (unknown):
```unknown
get_variable_loadings
```

Example 30 (python):
```python
interpolate_adata
```

Example 31 (unknown):
```unknown
select_resource
```

Example 32 (unknown):
```unknown
show_resources
```

Example 33 (unknown):
```unknown
generate_lr_geneset
```

Example 34 (unknown):
```unknown
explode_complexes
```

Example 35 (unknown):
```unknown
get_metalinks
```

Example 36 (unknown):
```unknown
describe_metalinks
```

Example 37 (unknown):
```unknown
get_metalinks_values
```

Example 38 (unknown):
```unknown
find_causalnet
```

Example 39 (unknown):
```unknown
build_prior_network
```

Example 40 (unknown):
```unknown
estimate_metalinks
```

---

## liana.multi.df_to_lr — liana

**URL:** http://127.0.0.1:9050/en_latest_generated_liana.multi.df_to_lr.html

**Contents:**
- liana.multi.df_to_lr
- Contents
- liana.multi.df_to_lr#

Convert DEA results to ligand-receptor pairs.

adata – Annotated data object.

dea_df (pd.DataFrame) – DEA results. Index must match adata.var_names

groupby – Key to be used for grouping.

stat_keys (list) – List of statistics to be used for ligand-receptor pairs

resource_name (default: 'consensus') – Name of the resource to be used for ligand-receptor inference. See li.rs.show_resources() for available resources.

resource (default: None) – A pandas dataframe with [ligand, receptor] columns. If provided will overrule the resource requested via resource_name

interactions (default: None) – List of tuples with ligand-receptor pairs [(ligand, receptor), ...] to be used for the analysis. If passed, it will overrule the resource requested via resource and resource_name.

layer (default: None) – Layer in anndata.AnnData.layers to use. If None, use anndata.AnnData.X.

use_raw (default: None) – Use raw attribute of adata if present.

expr_prop (default: 0.1) – Minimum expression proportion for the ligands and receptors (+ their subunits) in the corresponding cell identities. Set to 0 to return unfiltered results.

min_cells (default: 5) – Minimum cells (per cell identity if grouped by groupby) to be considered for downstream analysis.

complex_col (str, optional) – Column in dea_df to use for complex expression. Default is None. If None, will use mean expression (‘expr’) calculated per group in groupby.

return_all_lrs (default: False) – Bool whether to return all ligand-receptor pairs, or only those that surpass the expr_prop threshold. Ligand-receptor pairs that do not pass the expr_prop threshold will be assigned to the worst score of the ones that do. False by default.

source_labels (default: None) – List of labels to use as source, the rest are filtered out.

target_labels (default: None) – List of labels to use as target, the rest are filtered out.

lr_sep (default: '^') – Separator to use when joining ligand and receptor names into interactions.

verbose (default: False) – Verbosity flag.

Returns a pd.DataFrame with joined ligand-receptor pairs and statistics.

liana.method.lrMistyData

liana.multi.to_tensor_c2c

By Daniel Dimitrov, Philipp Sven Lars Schäfer, Elias Farr, Pablo Rodriguez-Mier, Sebastian Lobentanzer, Pau Badia-i-Mompel, Aurelien Dugourd, Jovan Tanevski, Ricardo Omar Ramirez Flores, Julio Saez-Rodriguez

© Copyright 2025, Daniel Dimitrov, Philipp Sven Lars Schäfer, Elias Farr, Pablo Rodriguez-Mier, Sebastian Lobentanzer, Pau Badia-i-Mompel, Aurelien Dugourd, Jovan Tanevski, Ricardo Omar Ramirez Flores, Julio Saez-Rodriguez..

**Examples:**

Example 1 (unknown):
```unknown
'consensus'
```

Example 2 (unknown):
```unknown
li.rs.show_resources()
```

Example 3 (unknown):
```unknown
resource_name
```

Example 4 (unknown):
```unknown
[(ligand, receptor), ...]
```

Example 5 (unknown):
```unknown
resource_name
```

---

## liana.utils.interpolate_adata — liana

**URL:** http://127.0.0.1:9050/en_latest_generated_liana.utils.interpolate_adata.html

**Contents:**
- liana.utils.interpolate_adata
- Contents
- liana.utils.interpolate_adata#

Interpolates spatial data from a target AnnData object to a reference AnnData object based on spatial coordinates.

The function creates a new AnnData object where the .X attribute is filled with interpolated data using the specified method.

target (AnnData) – The AnnData object to be interpolated.

reference (AnnData) – The AnnData object to be used as reference.

spatial_key (str) – Key in adata.obsm that contains the spatial coordinates. Default is 'spatial'.

layer (default: None) – Layer in anndata.AnnData.layers to use. If None, use anndata.AnnData.X.

use_raw (default: True) – Use raw attribute of adata if present.

method (str (default: 'linear')) – Interpolation method. See scipy.interpolate.griddata for more information.

fill_value (float (default: 0)) – Value to fill in for points outside of the convex hull of the input points.

verbose (default: False) – Verbosity flag.

AnnData: A new AnnData object with the same metadata as the reference but with interpolated spatial data in .X.

liana.utils.get_variable_loadings

liana.resource.select_resource

By Daniel Dimitrov, Philipp Sven Lars Schäfer, Elias Farr, Pablo Rodriguez-Mier, Sebastian Lobentanzer, Pau Badia-i-Mompel, Aurelien Dugourd, Jovan Tanevski, Ricardo Omar Ramirez Flores, Julio Saez-Rodriguez

© Copyright 2025, Daniel Dimitrov, Philipp Sven Lars Schäfer, Elias Farr, Pablo Rodriguez-Mier, Sebastian Lobentanzer, Pau Badia-i-Mompel, Aurelien Dugourd, Jovan Tanevski, Ricardo Omar Ramirez Flores, Julio Saez-Rodriguez..

**Examples:**

Example 1 (python):
```python
interpolate_adata()
```

Example 2 (unknown):
```unknown
scipy.interpolate.griddata
```

Example 3 (python):
```python
interpolate_adata()
```

---

## liana.method.singlecellsignalr.__call__ — liana

**URL:** http://127.0.0.1:9050/en_latest_generated_liana.method.singlecellsignalr.__call__.html

**Contents:**
- liana.method.singlecellsignalr.__call__
- Contents
- liana.method.singlecellsignalr.__call__#

Run a ligand-receptor method.

adata (AnnData | MuData) – Annotated data object.

groupby (str) – Key to be used for grouping.

resource_name (str (default: 'consensus')) – Name of the resource to be used for ligand-receptor inference. See li.rs.show_resources() for available resources.

expr_prop (float (default: 0.1)) – Minimum expression proportion for the ligands and receptors (+ their subunits) in the corresponding cell identities. Set to 0 to return unfiltered results.

min_cells (int (default: 5)) – Minimum cells (per cell identity if grouped by groupby) to be considered for downstream analysis.

groupby_pairs (DataFrame | None (default: None)) – A DataFrame with columns source and target to be used to subset the possible combinations of interacting cell types. If None, all possible combinations are used.

base (float (default: np.float64(2.718281828459045))) – Exponent base used to reverse the log-transformation of the matrix. Relevant only for the logfc method.

supp_columns (list | None (default: None)) – Additional columns to be added from any of the methods implemented in liana, or any of the columns returned by scanpy.tl.rank_genes_groups, each starting with ligand_* or receptor_*. For example, ['ligand_pvals', 'receptor_pvals']. None by default.

return_all_lrs (bool (default: False)) – Bool whether to return all ligand-receptor pairs, or only those that surpass the expr_prop threshold. Ligand-receptor pairs that do not pass the expr_prop threshold will be assigned to the worst score of the ones that do. False by default.

key_added (str (default: 'liana_res')) – Key under which the results will be stored in adata.uns if inplace is True.

use_raw (bool | None (default: True)) – Use raw attribute of adata if present.

layer (str | None (default: None)) – Layer in anndata.AnnData.layers to use. If None, use anndata.AnnData.X.

de_method (str (default: 't-test')) – Differential expression method. scanpy.tl.rank_genes_groups is used to rank genes according to 1vsRest. The default method is ‘t-test’.

verbose (bool | None (default: False)) – Verbosity flag.

n_perms (int (default: 1000)) – Number of permutations for the permutation test. Relevant only for permutation-based methods (e.g., CellPhoneDB). If None is passed, no permutation testing is performed.

seed (int (default: 1337)) – Random seed for reproducibility.

n_jobs (int (default: 1)) – Number of jobs to run in parallel.

resource (DataFrame | None (default: None)) – A pandas dataframe with [ligand, receptor] columns. If provided will overrule the resource requested via resource_name

interactions (list | None (default: None)) – List of tuples with ligand-receptor pairs [(ligand, receptor), ...] to be used for the analysis. If passed, it will overrule the resource requested via resource and resource_name.

mdata_kwargs (dict | None (default: None)) – Keyword arguments to be passed to li.fun.mdata_to_anndata if adata is an instance of MuData. If an AnnData object is passed, these arguments are ignored.

inplace (bool (default: True)) – Whether to store results in place, or else to return them.

If inplace = False, returns a DataFrame with ligand-receptor results Otherwise, modifies the adata object with the following key: - anndata.AnnData.uns [`key_added`] with the aforementioned DataFrame

liana.method.natmi.__call__

liana.method.geometric_mean.__call__

By Daniel Dimitrov, Philipp Sven Lars Schäfer, Elias Farr, Pablo Rodriguez-Mier, Sebastian Lobentanzer, Pau Badia-i-Mompel, Aurelien Dugourd, Jovan Tanevski, Ricardo Omar Ramirez Flores, Julio Saez-Rodriguez

© Copyright 2025, Daniel Dimitrov, Philipp Sven Lars Schäfer, Elias Farr, Pablo Rodriguez-Mier, Sebastian Lobentanzer, Pau Badia-i-Mompel, Aurelien Dugourd, Jovan Tanevski, Ricardo Omar Ramirez Flores, Julio Saez-Rodriguez..

**Examples:**

Example 1 (unknown):
```unknown
singlecellsignalr.__call__()
```

Example 2 (unknown):
```unknown
'consensus'
```

Example 3 (unknown):
```unknown
li.rs.show_resources()
```

Example 4 (python):
```python
np.float64(2.718281828459045)
```

Example 5 (unknown):
```unknown
scanpy.tl.rank_genes_groups
```

Example 6 (unknown):
```unknown
['ligand_pvals', 'receptor_pvals']
```

Example 7 (unknown):
```unknown
'liana_res'
```

Example 8 (unknown):
```unknown
scanpy.tl.rank_genes_groups
```

Example 9 (unknown):
```unknown
CellPhoneDB
```

Example 10 (unknown):
```unknown
resource_name
```

Example 11 (unknown):
```unknown
[(ligand, receptor), ...]
```

Example 12 (unknown):
```unknown
resource_name
```

Example 13 (unknown):
```unknown
li.fun.mdata_to_anndata
```

Example 14 (unknown):
```unknown
inplace = False
```

Example 15 (unknown):
```unknown
anndata.AnnData.uns
```

Example 16 (unknown):
```unknown
[`key_added`]
```

Example 17 (unknown):
```unknown
singlecellsignalr.__call__()
```

---

## liana.plotting.dotplot — liana

**URL:** http://127.0.0.1:9050/en_latest_generated_liana.plotting.dotplot.html

**Contents:**
- liana.plotting.dotplot
- Contents
- liana.plotting.dotplot#

Dotplot interactions by source and target cells

adata (AnnData (default: None)) – Annotated data object.

uns_key (default: 'liana_res') – Key in adata.uns that contains the LIANA results. Default is 'liana_res'.

liana_res (DataFrame (default: None)) – liana_res a DataFrame in liana’s format.

colour (str (default: None)) – column in liana_res to define the colours of the dots.

size (str (default: None)) – column in liana_res to define the size of the dots.

source_labels (list (default: None)) – List of labels to use as source, the rest are filtered out.

target_labels (list (default: None)) – List of labels to use as target, the rest are filtered out.

top_n (int (default: None)) – top_n entities to plot.

orderby (str | None (default: None)) – If top_n is not None, order the interactions by this column

orderby_ascending (bool | None (default: None)) – If top_n is not None, specify how to order the interactions

orderby_absolute (bool (default: False)) – If top_n is not None, whether to order by the absolute value of the orderby column.

filter_fun (callable (default: None)) – A function, applied along the columns (axis=1), used to filter the results to be plotted.

ligand_complex (str | None (default: None)) – list of ligand complexes to filter the interactions to be plotted. Defaults to None.

receptor_complex (str | None (default: None)) – list of receptor complexes to filter the interactions to be plotted. Defaults to None.

inverse_colour (bool (default: False)) – Whether to -log10 the colour column for plotting. False by default.

inverse_size (bool (default: False)) – Whether to -log10 the size column for plotting. False by default.

cmap (str (default: 'viridis')) – Colour map to use for plotting.

size_range (tuple (default: (2, 9))) – Define size range. Tuple of (min, max) integers.

figure_size (tuple (default: (8, 6))) – Figure x,y size

A plotnine.ggplot instance

liana.multi.estimate_elbow

liana.plotting.dotplot_by_sample

By Daniel Dimitrov, Philipp Sven Lars Schäfer, Elias Farr, Pablo Rodriguez-Mier, Sebastian Lobentanzer, Pau Badia-i-Mompel, Aurelien Dugourd, Jovan Tanevski, Ricardo Omar Ramirez Flores, Julio Saez-Rodriguez

© Copyright 2025, Daniel Dimitrov, Philipp Sven Lars Schäfer, Elias Farr, Pablo Rodriguez-Mier, Sebastian Lobentanzer, Pau Badia-i-Mompel, Aurelien Dugourd, Jovan Tanevski, Ricardo Omar Ramirez Flores, Julio Saez-Rodriguez..

**Examples:**

Example 1 (unknown):
```unknown
'liana_res'
```

Example 2 (unknown):
```unknown
'liana_res'
```

Example 3 (unknown):
```unknown
plotnine.ggplot
```

Example 4 (unknown):
```unknown
plotnine.ggplot
```

---

## liana.method.find_causalnet — liana

**URL:** http://127.0.0.1:9050/en_latest_generated_liana.method.find_causalnet.html

**Contents:**
- liana.method.find_causalnet
- Contents
- liana.method.find_causalnet#

Find the causal network that best explains the input/output node scores.

prior_graph (corneto.Graph) – The prior graph to use for the search.

input_node_scores (dict) – A dictionary of input node scores.

output_node_scores (dict) – A dictionary of output node scores.

node_weights (dict, optional) – A dictionary of node weights. The keys are the node names, the values are the weights. If None, all nodes will have the same weight.

node_cutoff (float) – The cutoff to use for the node weights. Nodes with a weight below this cutoff will be assigned the max_penalty, nodes with a weight above this cutoff will be assigned the min_penalty. Only used if node_weights is not None. Default: 0.1

min_penalty (float) – The minimum penalty to assign to nodes with a weight above the cutoff. Only used if node_weights is not None. Default: 0.01

max_penalty (float) – The maximum penalty to assign to nodes with a weight below the cutoff Only used if node_weights is not None. Default: 1.0

missing_penalty (float) – The penalty to assign to nodes that are not measured. Default: 10

edge_penalty (float) – The penalty to assign to edges. Default: 0.01

solver (str, optional) – The solver to use. If None, the default solver will be used. Default: None It will default to the solver included in SCIPY, if no other solver is available.

seed (int, optional) – The seed to use for the random number generator. Default: 1337

max_runs (int, optional) – The maximum number of runs to perform. Consider increasing this value if the solver does not converge. In each run, the noise added to the edge and node penalties is perturbed slightly (iterating over the seed). By default, only 1 run is performed.

stable_runs (int, optional) – The number of consecutive stable solutions requires to interrupt the iteration over max_runs. Only used if max_runs is not == 1. Default: 5

verbose (bool, optional) – Whether to print progress information. Default: True

**kwargs (dict, optional) – Additional arguments to pass to the solver.

liana.resource.get_metalinks_values

liana.method.build_prior_network

By Daniel Dimitrov, Philipp Sven Lars Schäfer, Elias Farr, Pablo Rodriguez-Mier, Sebastian Lobentanzer, Pau Badia-i-Mompel, Aurelien Dugourd, Jovan Tanevski, Ricardo Omar Ramirez Flores, Julio Saez-Rodriguez

© Copyright 2025, Daniel Dimitrov, Philipp Sven Lars Schäfer, Elias Farr, Pablo Rodriguez-Mier, Sebastian Lobentanzer, Pau Badia-i-Mompel, Aurelien Dugourd, Jovan Tanevski, Ricardo Omar Ramirez Flores, Julio Saez-Rodriguez..

**Examples:**

Example 1 (unknown):
```unknown
find_causalnet()
```

Example 2 (unknown):
```unknown
find_causalnet()
```

---

## References — liana

**URL:** http://127.0.0.1:9050/en_latest_references.html

**Contents:**
- References
- References#

Isaac Virshup, Danila Bredikhin, Lukas Heumos, Giovanni Palla, Gregor Sturm, Adam Gayoso, Ilia Kats, Mikaela Koutrouli, Philipp Angerer, Volker Bergen, Pierre Boyeau, Maren Büttner, Gokcen Eraslan, David Fischer, Max Frank, Justin Hong, Michal Klein, Marius Lange, Romain Lopez, Mohammad Lotfollahi, Malte D. Luecken, Fidel Ramirez, Jeffrey Regier, Sergei Rybakov, Anna C. Schaar, Valeh Valiollah Pour Amiri, Philipp Weiler, Galen Xing, Bonnie Berger, Dana Pe'er, Aviv Regev, Sarah A. Teichmann, Francesca Finotello, F. Alexander Wolf, Nir Yosef, Oliver Stegle, and Fabian J. Theis and. The scverse project provides a computational ecosystem for single-cell omics data analysis. Nature Biotechnology, apr 2023. URL: https://doi.org/10.1038%2Fs41587-023-01733-8, doi:10.1038/s41587-023-01733-8.

By Daniel Dimitrov, Philipp Sven Lars Schäfer, Elias Farr, Pablo Rodriguez-Mier, Sebastian Lobentanzer, Pau Badia-i-Mompel, Aurelien Dugourd, Jovan Tanevski, Ricardo Omar Ramirez Flores, Julio Saez-Rodriguez

© Copyright 2025, Daniel Dimitrov, Philipp Sven Lars Schäfer, Elias Farr, Pablo Rodriguez-Mier, Sebastian Lobentanzer, Pau Badia-i-Mompel, Aurelien Dugourd, Jovan Tanevski, Ricardo Omar Ramirez Flores, Julio Saez-Rodriguez..

---

## liana.resource.generate_lr_geneset — liana

**URL:** http://127.0.0.1:9050/en_latest_generated_liana.resource.generate_lr_geneset.html

**Contents:**
- liana.resource.generate_lr_geneset
- Contents
- liana.resource.generate_lr_geneset#

Generate a ligand-receptor gene set from a resource and a network.

Specifically, it works with weighted bipartite networks, where the weight represents the importance of the genes to a given geneset. The function will assign a weight to each ligand-receptor interaction, based on the mean. It does so by first assigning a weight to each ligand-receptor subunit, checking for sign coherence and completeness of the ligand-receptor complex.

resource – A pandas dataframe with [ligand, receptor] columns.

net – Prior knowledge network in bipartite or decoupler format.

ligand (str, optional) – Name of the ligand column in the resource

receptor (str, optional) – Name of the receptor column in the resource

lr_sep (default: '^') – Separator to use when joining ligand and receptor names into interactions.

source (str, optional) – Name of the source column in the network.

weight (str, optional) – Name of the weight column in the network. If None, all weights are set to 1.

Returns ligand-receptor geneset resource as a pandas.DataFrame with the following columns: - interaction: ligand-receptor interaction - weight: mean weight of the interaction - source: source of the interaction

liana.resource.show_resources

liana.resource.explode_complexes

By Daniel Dimitrov, Philipp Sven Lars Schäfer, Elias Farr, Pablo Rodriguez-Mier, Sebastian Lobentanzer, Pau Badia-i-Mompel, Aurelien Dugourd, Jovan Tanevski, Ricardo Omar Ramirez Flores, Julio Saez-Rodriguez

© Copyright 2025, Daniel Dimitrov, Philipp Sven Lars Schäfer, Elias Farr, Pablo Rodriguez-Mier, Sebastian Lobentanzer, Pau Badia-i-Mompel, Aurelien Dugourd, Jovan Tanevski, Ricardo Omar Ramirez Flores, Julio Saez-Rodriguez..

**Examples:**

Example 1 (unknown):
```unknown
generate_lr_geneset()
```

Example 2 (unknown):
```unknown
generate_lr_geneset()
```

---

## liana.utils.zi_minmax — liana

**URL:** http://127.0.0.1:9050/en_latest_generated_liana.utils.zi_minmax.html

**Contents:**
- liana.utils.zi_minmax
- Contents
- liana.utils.zi_minmax#

Zero-inflated min-max scaling, adopted from CiteFuse (Kim et al., 2020; https://academic.oup.com/bioinformatics/article/36/14/4137/5827474).

This function scales the data to the range [0, 1] and sets values below a specified cutoff to 0.

X (array-like) – Data to be scaled.

cutoff (float) – Cutoff value for zero-inflation - values less than this are set to 0. Default is 0.5.

liana.utils.mdata_to_anndata

liana.utils.neg_to_zero

By Daniel Dimitrov, Philipp Sven Lars Schäfer, Elias Farr, Pablo Rodriguez-Mier, Sebastian Lobentanzer, Pau Badia-i-Mompel, Aurelien Dugourd, Jovan Tanevski, Ricardo Omar Ramirez Flores, Julio Saez-Rodriguez

© Copyright 2025, Daniel Dimitrov, Philipp Sven Lars Schäfer, Elias Farr, Pablo Rodriguez-Mier, Sebastian Lobentanzer, Pau Badia-i-Mompel, Aurelien Dugourd, Jovan Tanevski, Ricardo Omar Ramirez Flores, Julio Saez-Rodriguez..

**Examples:**

Example 1 (unknown):
```unknown
zi_minmax()
```

Example 2 (unknown):
```unknown
zi_minmax()
```

---

## liana.method.cellchat.__call__ — liana

**URL:** http://127.0.0.1:9050/en_latest_generated_liana.method.cellchat.__call__.html

**Contents:**
- liana.method.cellchat.__call__
- Contents
- liana.method.cellchat.__call__#

Run a ligand-receptor method.

adata (AnnData | MuData) – Annotated data object.

groupby (str) – Key to be used for grouping.

resource_name (str (default: 'consensus')) – Name of the resource to be used for ligand-receptor inference. See li.rs.show_resources() for available resources.

expr_prop (float (default: 0.1)) – Minimum expression proportion for the ligands and receptors (+ their subunits) in the corresponding cell identities. Set to 0 to return unfiltered results.

min_cells (int (default: 5)) – Minimum cells (per cell identity if grouped by groupby) to be considered for downstream analysis.

groupby_pairs (DataFrame | None (default: None)) – A DataFrame with columns source and target to be used to subset the possible combinations of interacting cell types. If None, all possible combinations are used.

base (float (default: np.float64(2.718281828459045))) – Exponent base used to reverse the log-transformation of the matrix. Relevant only for the logfc method.

supp_columns (list | None (default: None)) – Additional columns to be added from any of the methods implemented in liana, or any of the columns returned by scanpy.tl.rank_genes_groups, each starting with ligand_* or receptor_*. For example, ['ligand_pvals', 'receptor_pvals']. None by default.

return_all_lrs (bool (default: False)) – Bool whether to return all ligand-receptor pairs, or only those that surpass the expr_prop threshold. Ligand-receptor pairs that do not pass the expr_prop threshold will be assigned to the worst score of the ones that do. False by default.

key_added (str (default: 'liana_res')) – Key under which the results will be stored in adata.uns if inplace is True.

use_raw (bool | None (default: True)) – Use raw attribute of adata if present.

layer (str | None (default: None)) – Layer in anndata.AnnData.layers to use. If None, use anndata.AnnData.X.

de_method (str (default: 't-test')) – Differential expression method. scanpy.tl.rank_genes_groups is used to rank genes according to 1vsRest. The default method is ‘t-test’.

verbose (bool | None (default: False)) – Verbosity flag.

n_perms (int (default: 1000)) – Number of permutations for the permutation test. Relevant only for permutation-based methods (e.g., CellPhoneDB). If None is passed, no permutation testing is performed.

seed (int (default: 1337)) – Random seed for reproducibility.

n_jobs (int (default: 1)) – Number of jobs to run in parallel.

resource (DataFrame | None (default: None)) – A pandas dataframe with [ligand, receptor] columns. If provided will overrule the resource requested via resource_name

interactions (list | None (default: None)) – List of tuples with ligand-receptor pairs [(ligand, receptor), ...] to be used for the analysis. If passed, it will overrule the resource requested via resource and resource_name.

mdata_kwargs (dict | None (default: None)) – Keyword arguments to be passed to li.fun.mdata_to_anndata if adata is an instance of MuData. If an AnnData object is passed, these arguments are ignored.

inplace (bool (default: True)) – Whether to store results in place, or else to return them.

If inplace = False, returns a DataFrame with ligand-receptor results Otherwise, modifies the adata object with the following key: - anndata.AnnData.uns [`key_added`] with the aforementioned DataFrame

liana.method.cellphonedb.__call__

By Daniel Dimitrov, Philipp Sven Lars Schäfer, Elias Farr, Pablo Rodriguez-Mier, Sebastian Lobentanzer, Pau Badia-i-Mompel, Aurelien Dugourd, Jovan Tanevski, Ricardo Omar Ramirez Flores, Julio Saez-Rodriguez

© Copyright 2025, Daniel Dimitrov, Philipp Sven Lars Schäfer, Elias Farr, Pablo Rodriguez-Mier, Sebastian Lobentanzer, Pau Badia-i-Mompel, Aurelien Dugourd, Jovan Tanevski, Ricardo Omar Ramirez Flores, Julio Saez-Rodriguez..

**Examples:**

Example 1 (unknown):
```unknown
cellchat.__call__()
```

Example 2 (unknown):
```unknown
'consensus'
```

Example 3 (unknown):
```unknown
li.rs.show_resources()
```

Example 4 (python):
```python
np.float64(2.718281828459045)
```

Example 5 (unknown):
```unknown
scanpy.tl.rank_genes_groups
```

Example 6 (unknown):
```unknown
['ligand_pvals', 'receptor_pvals']
```

Example 7 (unknown):
```unknown
'liana_res'
```

Example 8 (unknown):
```unknown
scanpy.tl.rank_genes_groups
```

Example 9 (unknown):
```unknown
CellPhoneDB
```

Example 10 (unknown):
```unknown
resource_name
```

Example 11 (unknown):
```unknown
[(ligand, receptor), ...]
```

Example 12 (unknown):
```unknown
resource_name
```

Example 13 (unknown):
```unknown
li.fun.mdata_to_anndata
```

Example 14 (unknown):
```unknown
inplace = False
```

Example 15 (unknown):
```unknown
anndata.AnnData.uns
```

Example 16 (unknown):
```unknown
[`key_added`]
```

Example 17 (unknown):
```unknown
cellchat.__call__()
```

---

## liana.method.MistyData — liana

**URL:** http://127.0.0.1:9050/en_latest_generated_liana.method.MistyData.html

**Contents:**
- liana.method.MistyData
- Contents
- liana.method.MistyData#
- Attributes table#
- Methods table#
- Attributes#
- Methods#

MistyData Class used to construct multi-view objects

Filename of the MuData object.

Whether the MuData object is backed.

Names of modalities (alias for list(mdata.mod.keys()))

Number of modalities in the MuData object.

Total number of observations

Total number of variables

Total number of variables

Annotation of observation

Names of variables (alias for .obs.index)

Multi-dimensional annotation of observation

Mapping of observation index in the MuData to indices in individual modalities.

Pairwise annotatation of observations

Shape of data, all variables and observations combined (n_obs, n_var).

Unstructured annotation (ordered dictionary).

Annotation of variables

Names of variables (alias for .var.index)

Multi-dimensional annotation of variables

Mapping of feature index in the MuData to indices in individual modalities.

Pairwise annotatation of variables

get_weighted_matrix(view_name[, predictors])

List keys of observation annotation obs.

obs_names_make_unique()

Call .obs_names_make_unique() method on each AnnData object.

obs_vector(key[, layer])

Return an array of values for the requested key of length n_obs

List keys of observation annotation obsm.

pull_obs([columns, mods, common, ...])

Copy the data from the modalities to the global .obs, existing columns to be overwritten or updated

pull_var([columns, mods, common, ...])

Copy the data from the modalities to the global .var, existing columns to be overwritten or updated

push_obs([columns, mods, common, prefixed, ...])

Copy the data from the mdata.obs to the modalities, existing columns to be overwritten

push_var([columns, mods, common, prefixed, ...])

Copy the data from the mdata.var to the modalities, existing columns to be overwritten

strings_to_categoricals([df])

Transform string columns in .var and .obs slots of MuData to categorical as well as of .var and .obs slots in each AnnData object

Convert MuData to AnnData

List keys of unstructured annotation.

Update both .obs and .var indices of MuData with the data from all the modalities

Update global .obs_names according to the .obs_names of all the modalities.

Update global .var_names according to the .var_names of all the modalities.

List keys of variable annotation var.

var_names_make_unique()

Call .var_names_make_unique() method on each AnnData object.

var_vector(key[, layer])

Return an array of values for the requested key of length n_var

List keys of variable annotation varm.

Write MuData object to an HDF5 file

write_h5mu([filename])

Write MuData object to an HDF5 file

write_zarr(store, **kwargs)

Write MuData object to a Zarr store

Filename of the MuData object.

Path | None: The path to the file if backed, None otherwise.

Whether the MuData object is backed.

bool: True if the object is backed, False otherwise.

Names of modalities (alias for list(mdata.mod.keys()))

This property is read-only.

Number of modalities in the MuData object.

int: The number of modalities.

Total number of observations

Total number of variables

Total number of variables

Annotation of observation

Names of variables (alias for .obs.index)

Multi-dimensional annotation of observation

Mapping of observation index in the MuData to indices in individual modalities.

1-based, 0 indicates that the corresponding observation is missing in the respective modality.

Pairwise annotatation of observations

Shape of data, all variables and observations combined (n_obs, n_var).

Unstructured annotation (ordered dictionary).

Annotation of variables

Names of variables (alias for .var.index)

Multi-dimensional annotation of variables

Mapping of feature index in the MuData to indices in individual modalities.

1-based, 0 indicates that the corresponding observation is missing in the respective modality.

Pairwise annotatation of variables

filename (PathLike | None (default: None)) – If the object is backed, copy the object to a new file.

List keys of observation annotation obs.

Call .obs_names_make_unique() method on each AnnData object.

If there are obs_names, which are the same for multiple modalities, append modality name to all obs_names.

Return an array of values for the requested key of length n_obs

List keys of observation annotation obsm.

Copy the data from the modalities to the global .obs, existing columns to be overwritten or updated

columns (list[str] | None (default: None)) – List of columns to pull from the modalities’ .obs tables

common (bool | None (default: None)) – If True, pull common columns. Common columns do not have modality prefixes. Pull from all modalities. Cannot be used with columns. True by default.

mods (list[str] | None (default: None)) – List of modalities to pull from.

join_common (bool | None (default: None)) – If True, attempt to join common columns. Common columns are present in all modalities. True for MuData wth axis=1 (shared var). False for MuData with axis=0 and axis=-1. Cannot be used with mods, or for shared attr.

nonunique (bool | None (default: None)) – If True, pull columns that have a modality prefix such that there are multiple columns with the same name and different prefix. Cannot be used with columns or mods. True by default.

join_nonunique (bool | None (default: None)) – If True, attempt to join non-unique columns. Intended usage is the same as for join_common. Cannot be used with mods, or for shared attr. False by default.

unique (bool | None (default: None)) – If True, pull columns that have a modality prefix such that there is no other column with the same name and a different modality prefix. Cannot be used with columns or mods. True by default.

prefix_unique (bool | None (default: True)) – If True, prefix unique column names with modname (default). No prefix when False.

drop (bool (default: False)) – If True, drop the columns from the modalities after pulling.

only_drop (bool (default: False)) – If True, drop the columns but do not actually pull them. Forces drop=True.

Copy the data from the modalities to the global .var, existing columns to be overwritten or updated

columns (list[str] | None (default: None)) – List of columns to pull from the modalities’ .var tables

common (bool | None (default: None)) – If True, pull common columns. Common columns do not have modality prefixes. Pull from all modalities. Cannot be used with columns. True by default.

mods (list[str] | None (default: None)) – List of modalities to pull from.

join_common (bool | None (default: None)) – If True, attempt to join common columns. Common columns are present in all modalities. True for MuData with axis=0 (shared obs). False for MuData with axis=1 and axis=-1. Cannot be used with mods, or for shared attr.

nonunique (bool | None (default: None)) – If True, pull columns that have a modality prefix such that there are multiple columns with the same name and different prefix. Cannot be used with columns or mods. True by default.

join_nonunique (bool | None (default: None)) – If True, attempt to join non-unique columns. Intended usage is the same as for join_common. Cannot be used with mods, or for shared attr. False by default.

unique (bool | None (default: None)) – If True, pull columns that have a modality prefix such that there is no other column with the same name and a different modality prefix. Cannot be used with columns or mods. True by default.

prefix_unique (bool | None (default: True)) – If True, prefix unique column names with modname (default). No prefix when False.

drop (bool (default: False)) – If True, drop the columns from the modalities after pulling.

only_drop (bool (default: False)) – If True, drop the columns but do not actually pull them. Forces drop=True.

Copy the data from the mdata.obs to the modalities, existing columns to be overwritten

columns (list[str] | None (default: None)) – List of columns to push

mods (list[str] | None (default: None)) – List of modalities to push to

common (bool | None (default: None)) – If True, push common columns. Common columns do not have modality prefixes. Push to each modality unless all values for a modality are null. Cannot be used with columns. True by default.

prefixed (bool | None (default: None)) – If True, push columns that have a modality prefix. which are prefixed by modality names. Only push to the respective modality names. Cannot be used with columns. True by default.

drop (bool (default: False)) – If True, drop the columns from the global .obs after pushing. False by default.

only_drop (bool (default: False)) – If True, drop the columns but do not actually pull them. Forces drop=True. False by default.

Copy the data from the mdata.var to the modalities, existing columns to be overwritten

columns (list[str] | None (default: None)) – List of columns to push

mods (list[str] | None (default: None)) – List of modalities to push to

common (bool | None (default: None)) – If True, push common columns. Common columns do not have modality prefixes. Push to each modality unless all values for a modality are null. Cannot be used with columns. True by default.

prefixed (bool | None (default: None)) – If True, push columns that have a modality prefix. which are prefixed by modality names. Only push to the respective modality names. Cannot be used with columns. True by default.

drop (bool (default: False)) – If True, drop the columns from the global .var after pushing. False by default.

only_drop (bool (default: False)) – If True, drop the columns but do not actually pull them. Forces drop=True. False by default.

Transform string columns in .var and .obs slots of MuData to categorical as well as of .var and .obs slots in each AnnData object

This keeps it compatible with AnnData.strings_to_categoricals() method.

Convert MuData to AnnData

If mdata.axis == 0 (shared observations), concatenate modalities along axis 1 (anndata.concat(axis=1)). If mdata.axis == 1 (shared variables), concatenate datasets along axis 0 (anndata.concat(axis=0)).

See anndata.concat() documentation for more details.

data (MuData) – MuData object to convert to AnnData

kwargs (dict) – Keyword arguments passed to anndata.concat()

List keys of unstructured annotation.

Update both .obs and .var indices of MuData with the data from all the modalities

NOTE: From v0.4, it will not pull columns from modalities by default.

Update global .obs_names according to the .obs_names of all the modalities.

Update global .var_names according to the .var_names of all the modalities.

List keys of variable annotation var.

Call .var_names_make_unique() method on each AnnData object.

If there are var_names, which are the same for multiple modalities, append modality name to all var_names.

Return an array of values for the requested key of length n_var

List keys of variable annotation varm.

Write MuData object to an HDF5 file

Write MuData object to an HDF5 file

Write MuData object to a Zarr store

liana.method.bivariate.__call__

liana.method.genericMistyData

By Daniel Dimitrov, Philipp Sven Lars Schäfer, Elias Farr, Pablo Rodriguez-Mier, Sebastian Lobentanzer, Pau Badia-i-Mompel, Aurelien Dugourd, Jovan Tanevski, Ricardo Omar Ramirez Flores, Julio Saez-Rodriguez

© Copyright 2025, Daniel Dimitrov, Philipp Sven Lars Schäfer, Elias Farr, Pablo Rodriguez-Mier, Sebastian Lobentanzer, Pau Badia-i-Mompel, Aurelien Dugourd, Jovan Tanevski, Ricardo Omar Ramirez Flores, Julio Saez-Rodriguez..

**Examples:**

Example 1 (unknown):
```unknown
MistyData.axis
```

Example 2 (unknown):
```unknown
MistyData.filename
```

Example 3 (unknown):
```unknown
MistyData.isbacked
```

Example 4 (unknown):
```unknown
MistyData.mod_names
```

Example 5 (unknown):
```unknown
MistyData.n_mod
```

Example 6 (unknown):
```unknown
MistyData.n_obs
```

Example 7 (unknown):
```unknown
MistyData.n_var
```

Example 8 (unknown):
```unknown
MistyData.n_vars
```

Example 9 (unknown):
```unknown
MistyData.obs
```

Example 10 (unknown):
```unknown
MistyData.obs_names
```

Example 11 (unknown):
```unknown
MistyData.obsm
```

Example 12 (unknown):
```unknown
MistyData.obsmap
```

Example 13 (unknown):
```unknown
MistyData.obsp
```

Example 14 (python):
```python
MistyData.shape
```

Example 15 (unknown):
```unknown
MistyData.uns
```

Example 16 (unknown):
```unknown
MistyData.var
```

Example 17 (unknown):
```unknown
MistyData.var_names
```

Example 18 (unknown):
```unknown
MistyData.varm
```

Example 19 (unknown):
```unknown
MistyData.varmap
```

Example 20 (unknown):
```unknown
MistyData.varp
```

Example 21 (unknown):
```unknown
MistyData.copy()
```

Example 22 (unknown):
```unknown
MistyData.get_weighted_matrix()
```

Example 23 (unknown):
```unknown
MistyData.getdoc()
```

Example 24 (unknown):
```unknown
MistyData.obs_keys()
```

Example 25 (unknown):
```unknown
MistyData.obs_names_make_unique()
```

Example 26 (unknown):
```unknown
MistyData.obs_vector()
```

Example 27 (unknown):
```unknown
MistyData.obsm_keys()
```

Example 28 (unknown):
```unknown
MistyData.pull_obs()
```

Example 29 (unknown):
```unknown
MistyData.pull_var()
```

Example 30 (unknown):
```unknown
MistyData.push_obs()
```

Example 31 (unknown):
```unknown
MistyData.push_var()
```

Example 32 (unknown):
```unknown
MistyData.strings_to_categoricals()
```

Example 33 (unknown):
```unknown
MistyData.to_anndata()
```

Example 34 (unknown):
```unknown
MistyData.uns_keys()
```

Example 35 (unknown):
```unknown
MistyData.update()
```

Example 36 (unknown):
```unknown
MistyData.update_obs()
```

Example 37 (unknown):
```unknown
MistyData.update_var()
```

Example 38 (unknown):
```unknown
MistyData.var_keys()
```

Example 39 (unknown):
```unknown
MistyData.var_names_make_unique()
```

Example 40 (unknown):
```unknown
MistyData.var_vector()
```

Example 41 (unknown):
```unknown
MistyData.varm_keys()
```

Example 42 (unknown):
```unknown
MistyData.write()
```

Example 43 (unknown):
```unknown
MistyData.write_h5mu()
```

Example 44 (unknown):
```unknown
MistyData.write_zarr()
```

Example 45 (unknown):
```unknown
list(mdata.mod.keys())
```

Example 46 (unknown):
```unknown
get_weighted_matrix
```

Example 47 (unknown):
```unknown
obs_names_make_unique
```

Example 48 (unknown):
```unknown
strings_to_categoricals
```

Example 49 (unknown):
```unknown
var_names_make_unique
```

Example 50 (unknown):
```unknown
list(mdata.mod.keys())
```

Example 51 (unknown):
```unknown
anndata.concat(axis=1)
```

Example 52 (unknown):
```unknown
anndata.concat(axis=0)
```

Example 53 (unknown):
```unknown
anndata.concat()
```

Example 54 (unknown):
```unknown
anndata.concat()
```

Example 55 (unknown):
```unknown
MistyData.axis
```

Example 56 (unknown):
```unknown
MistyData.filename
```

Example 57 (unknown):
```unknown
MistyData.isbacked
```

Example 58 (unknown):
```unknown
MistyData.mod_names
```

Example 59 (unknown):
```unknown
MistyData.n_mod
```

Example 60 (unknown):
```unknown
MistyData.n_obs
```

Example 61 (unknown):
```unknown
MistyData.n_var
```

Example 62 (unknown):
```unknown
MistyData.n_vars
```

Example 63 (unknown):
```unknown
MistyData.obs
```

Example 64 (unknown):
```unknown
MistyData.obs_names
```

Example 65 (unknown):
```unknown
MistyData.obsm
```

Example 66 (unknown):
```unknown
MistyData.obsmap
```

Example 67 (unknown):
```unknown
MistyData.obsp
```

Example 68 (python):
```python
MistyData.shape
```

Example 69 (unknown):
```unknown
MistyData.uns
```

Example 70 (unknown):
```unknown
MistyData.var
```

Example 71 (unknown):
```unknown
MistyData.var_names
```

Example 72 (unknown):
```unknown
MistyData.varm
```

Example 73 (unknown):
```unknown
MistyData.varmap
```

Example 74 (unknown):
```unknown
MistyData.varp
```

Example 75 (unknown):
```unknown
MistyData.copy()
```

Example 76 (unknown):
```unknown
MistyData.get_weighted_matrix()
```

Example 77 (unknown):
```unknown
MistyData.getdoc()
```

Example 78 (unknown):
```unknown
MistyData.obs_keys()
```

Example 79 (unknown):
```unknown
MistyData.obs_names_make_unique()
```

Example 80 (unknown):
```unknown
MistyData.obs_vector()
```

Example 81 (unknown):
```unknown
MistyData.obsm_keys()
```

Example 82 (unknown):
```unknown
MistyData.pull_obs()
```

Example 83 (unknown):
```unknown
MistyData.pull_var()
```

Example 84 (unknown):
```unknown
MistyData.push_obs()
```

Example 85 (unknown):
```unknown
MistyData.push_var()
```

Example 86 (unknown):
```unknown
MistyData.strings_to_categoricals()
```

Example 87 (unknown):
```unknown
MistyData.to_anndata()
```

Example 88 (unknown):
```unknown
MistyData.uns_keys()
```

Example 89 (unknown):
```unknown
MistyData.update()
```

Example 90 (unknown):
```unknown
MistyData.update_obs()
```

Example 91 (unknown):
```unknown
MistyData.update_var()
```

Example 92 (unknown):
```unknown
MistyData.var_keys()
```

Example 93 (unknown):
```unknown
MistyData.var_names_make_unique()
```

Example 94 (unknown):
```unknown
MistyData.var_vector()
```

Example 95 (unknown):
```unknown
MistyData.varm_keys()
```

Example 96 (unknown):
```unknown
MistyData.write()
```

Example 97 (unknown):
```unknown
MistyData.write_h5mu()
```

Example 98 (unknown):
```unknown
MistyData.write_zarr()
```

---

## liana.plotting.tileplot — liana

**URL:** http://127.0.0.1:9050/en_latest_generated_liana.plotting.tileplot.html

**Contents:**
- liana.plotting.tileplot
- Contents
- liana.plotting.tileplot#

Tileplot interactions by source and target cells

adata (AnnData (default: None)) – Annotated data object.

liana_res (DataFrame (default: None)) – liana_res a DataFrame in liana’s format.

fill (str (default: None)) – column in liana_res to define the fill of the tiles

label (str (default: None)) – column in liana_res to define the label of the tiles

label_fun (callable (default: None)) – callable to apply to the label column

source_labels (str | list[str] (default: None)) – List of labels to use as source, the rest are filtered out.

target_labels (str | list[str] (default: None)) – List of labels to use as target, the rest are filtered out.

ligand_complex (str | list[str] (default: None)) – list of ligand complexes to filter the interactions to be plotted. Defaults to None.

receptor_complex (str | list[str] (default: None)) – list of receptor complexes to filter the interactions to be plotted. Defaults to None.

uns_key (str (default: 'liana_res')) – Key in adata.uns that contains the LIANA results. Default is 'liana_res'.

top_n (int (default: None)) – top_n entities to plot.

orderby (str (default: None)) – If top_n is not None, order the interactions by this column

orderby_ascending (bool (default: False)) – If top_n is not None, specify how to order the interactions

orderby_absolute (bool (default: True)) – If top_n is not None, whether to order by the absolute value of the orderby column.

filter_fun (callable (default: None)) – A function, applied along the columns (axis=1), used to filter the results to be plotted.

source_title (default: None) – Title for the source facet. Default is ‘Source’

target_title (default: None) – Title for the target facet. Default is ‘Target’

cmap (str (default: 'viridis')) – Colour map to use for plotting.

label_size (int (default: 12)) – Size of the label text

figure_size (tuple[float, float] (default: (5, 5))) – Figure x,y size

return_fig (bool (default: True)) – bool whether to return the fig object.

A plotnine.ggplot instance

liana.plotting.dotplot_by_sample

liana.plotting.connectivity

By Daniel Dimitrov, Philipp Sven Lars Schäfer, Elias Farr, Pablo Rodriguez-Mier, Sebastian Lobentanzer, Pau Badia-i-Mompel, Aurelien Dugourd, Jovan Tanevski, Ricardo Omar Ramirez Flores, Julio Saez-Rodriguez

© Copyright 2025, Daniel Dimitrov, Philipp Sven Lars Schäfer, Elias Farr, Pablo Rodriguez-Mier, Sebastian Lobentanzer, Pau Badia-i-Mompel, Aurelien Dugourd, Jovan Tanevski, Ricardo Omar Ramirez Flores, Julio Saez-Rodriguez..

**Examples:**

Example 1 (unknown):
```unknown
'liana_res'
```

Example 2 (unknown):
```unknown
'liana_res'
```

Example 3 (unknown):
```unknown
plotnine.ggplot
```

---

## liana.resource.get_metalinks — liana

**URL:** http://127.0.0.1:9050/en_latest_generated_liana.resource.get_metalinks.html

**Contents:**
- liana.resource.get_metalinks
- Contents
- liana.resource.get_metalinks#

Fetches edges of metabolite-proteins with specified annotations, applying filters if they are not None.

Allows filtering by lists of hmdb and uniprot IDs and avoids duplicate column names, and returns the results as a pandas DataFrame. Filters are applied using INNER JOINs and WHERE clauses - i.e. the results are the intersection of the filters.

db_path (str | None (default: None)) – Path to the SQLite database file. If None, the database will be downloaded to the current working directory.

types (list[str] | None (default: None)) – Desired edge types. Options are: [‘lr’, ‘pd’], where ‘lr’ stands for ‘ligand-receptor’ and ‘pd’ stands for ‘production-degradation’.

cell_location (list[str] | None (default: None)) – Desired metabolite cell locations.

tissue_location (list[str] | None (default: None)) – Desired metabolite tissue locations.

biospecimen_location (list[str] | None (default: None)) – Desired metabolite biospecimen locations.

disease (list[str] | None (default: None)) – Desired metabolite diseases.

pathway (list[str] | None (default: None)) – Desired metabolite pathways.

hmdb_ids (list[str] | None (default: None)) – Desired HMDB IDs.

uniprot_ids (list[str] | None (default: None)) – Desired UniProt IDs.

A pandas DataFrame containing the query results without the source column.

liana.resource.explode_complexes

liana.resource.describe_metalinks

By Daniel Dimitrov, Philipp Sven Lars Schäfer, Elias Farr, Pablo Rodriguez-Mier, Sebastian Lobentanzer, Pau Badia-i-Mompel, Aurelien Dugourd, Jovan Tanevski, Ricardo Omar Ramirez Flores, Julio Saez-Rodriguez

© Copyright 2025, Daniel Dimitrov, Philipp Sven Lars Schäfer, Elias Farr, Pablo Rodriguez-Mier, Sebastian Lobentanzer, Pau Badia-i-Mompel, Aurelien Dugourd, Jovan Tanevski, Ricardo Omar Ramirez Flores, Julio Saez-Rodriguez..

**Examples:**

Example 1 (unknown):
```unknown
get_metalinks()
```

Example 2 (unknown):
```unknown
get_metalinks()
```

---

## liana.method.estimate_metalinks — liana

**URL:** http://127.0.0.1:9050/en_latest_generated_liana.method.estimate_metalinks.html

**Contents:**
- liana.method.estimate_metalinks
- Contents
- liana.method.estimate_metalinks#

Estimate Metabolites from anndata object, and return a MuData object of metabolites and receptors.

adata – Annotated data matrix.

resource – Resource to use for ligand-receptor inference.

pd_net – Metabolic production-degradation network to use.

t_net (default: None) – Transport set to use.

x_name (default: 'metabolite') – Name of the metabolite modality.

y_name (default: 'receptor') – Name of the receptor modality. Must be present as a column in the resource.

**kwargs – Additional arguments to pass to the decoupler-py functions. Method-specific arguments are not supported.

A MuData object with metabolite & receptor assays.

liana.method.build_prior_network

By Daniel Dimitrov, Philipp Sven Lars Schäfer, Elias Farr, Pablo Rodriguez-Mier, Sebastian Lobentanzer, Pau Badia-i-Mompel, Aurelien Dugourd, Jovan Tanevski, Ricardo Omar Ramirez Flores, Julio Saez-Rodriguez

© Copyright 2025, Daniel Dimitrov, Philipp Sven Lars Schäfer, Elias Farr, Pablo Rodriguez-Mier, Sebastian Lobentanzer, Pau Badia-i-Mompel, Aurelien Dugourd, Jovan Tanevski, Ricardo Omar Ramirez Flores, Julio Saez-Rodriguez..

**Examples:**

Example 1 (unknown):
```unknown
estimate_metalinks()
```

Example 2 (unknown):
```unknown
'metabolite'
```

Example 3 (unknown):
```unknown
estimate_metalinks()
```

---

## liana.resource.describe_metalinks — liana

**URL:** http://127.0.0.1:9050/en_latest_generated_liana.resource.describe_metalinks.html

**Contents:**
- liana.resource.describe_metalinks
- Contents
- liana.resource.describe_metalinks#

Prints the schema information and foreign key details for all tables in the specified SQLite database.

db_path (str) – Path to the SQLite database file. If None, the database will be downloaded to the current working directory.

liana.resource.get_metalinks

liana.resource.get_metalinks_values

By Daniel Dimitrov, Philipp Sven Lars Schäfer, Elias Farr, Pablo Rodriguez-Mier, Sebastian Lobentanzer, Pau Badia-i-Mompel, Aurelien Dugourd, Jovan Tanevski, Ricardo Omar Ramirez Flores, Julio Saez-Rodriguez

© Copyright 2025, Daniel Dimitrov, Philipp Sven Lars Schäfer, Elias Farr, Pablo Rodriguez-Mier, Sebastian Lobentanzer, Pau Badia-i-Mompel, Aurelien Dugourd, Jovan Tanevski, Ricardo Omar Ramirez Flores, Julio Saez-Rodriguez..

**Examples:**

Example 1 (unknown):
```unknown
describe_metalinks()
```

Example 2 (unknown):
```unknown
describe_metalinks()
```

---

## liana.method.build_prior_network — liana

**URL:** http://127.0.0.1:9050/en_latest_generated_liana.method.build_prior_network.html

**Contents:**
- liana.method.build_prior_network
- Contents
- liana.method.build_prior_network#

Build Prior Network from PPIs and input/output nodes.

ppis (list of tuples or pandas DataFrame) – The PPIs to use for the prior network. If a pandas DataFrame is provided, it must have the columns

input_nodes (dict) – A dictionary of input nodes. The keys are the node names, the values are the node scores.

output_nodes (dict) – A dictionary of output nodes. The keys are the node names, the values are the node scores.

lr_sep (str, optional) – The separator to use to split the input nodes into ligand and receptor. If None, the input nodes will be used as is.

verbose (bool, optional) – Whether to print progress information. Default: True

liana.method.find_causalnet

liana.method.estimate_metalinks

By Daniel Dimitrov, Philipp Sven Lars Schäfer, Elias Farr, Pablo Rodriguez-Mier, Sebastian Lobentanzer, Pau Badia-i-Mompel, Aurelien Dugourd, Jovan Tanevski, Ricardo Omar Ramirez Flores, Julio Saez-Rodriguez

© Copyright 2025, Daniel Dimitrov, Philipp Sven Lars Schäfer, Elias Farr, Pablo Rodriguez-Mier, Sebastian Lobentanzer, Pau Badia-i-Mompel, Aurelien Dugourd, Jovan Tanevski, Ricardo Omar Ramirez Flores, Julio Saez-Rodriguez..

**Examples:**

Example 1 (unknown):
```unknown
build_prior_network()
```

Example 2 (unknown):
```unknown
build_prior_network()
```

---

## liana.multi.nmf — liana

**URL:** http://127.0.0.1:9050/en_latest_generated_liana.multi.nmf.html

**Contents:**
- liana.multi.nmf
- Contents
- liana.multi.nmf#

Fits NMF to an AnnData object.

adata (AnnData (default: None)) – Annotated data object.

n_components (int, None) – Number of components to use. If None, the number of components is estimated using the elbow method.

k_range (range) – Range of components to test. Default: range(1, 10).

use_raw (bool (default: False)) – Use raw attribute of adata if present.

layer (str (default: None)) – Layer in anndata.AnnData.layers to use. If None, use anndata.AnnData.X.

inplace (bool (default: True)) – Whether to store results in place, or else to return them.

**kwargs (dict) – Keyword arguments to pass to sklearn.decomposition.NMF.

If inplace is True, it will add NMF_W and NMF_H to the adata.obsm and adata.varm. If n_components is None, it will also add nfm_errors and nfm_rank to adata.uns. If inplace is False, it will return W and H, and if n_components is None, it will also return errors and n_components. If n_components is None and inplace, errors and n_components will be assigned to adata.uns. If df is provided, inplace is always False.

If inplace is True, it will add NMF_W and NMF_H to the adata.obsm and adata.varm. If n_components is None, it will also add nfm_errors and nfm_rank to adata.uns.

If inplace is False, it will return W and H, and if n_components is None, it will also return errors and n_components. If n_components is None and inplace, errors and n_components will be assigned to adata.uns. If df is provided, inplace is always False.

liana.multi.lrs_to_views

liana.multi.estimate_elbow

By Daniel Dimitrov, Philipp Sven Lars Schäfer, Elias Farr, Pablo Rodriguez-Mier, Sebastian Lobentanzer, Pau Badia-i-Mompel, Aurelien Dugourd, Jovan Tanevski, Ricardo Omar Ramirez Flores, Julio Saez-Rodriguez

© Copyright 2025, Daniel Dimitrov, Philipp Sven Lars Schäfer, Elias Farr, Pablo Rodriguez-Mier, Sebastian Lobentanzer, Pau Badia-i-Mompel, Aurelien Dugourd, Jovan Tanevski, Ricardo Omar Ramirez Flores, Julio Saez-Rodriguez..

**Examples:**

Example 1 (unknown):
```unknown
sklearn.decomposition.NMF
```

Example 2 (unknown):
```unknown
n_components
```

Example 3 (unknown):
```unknown
n_components
```

---

## liana.resource.get_metalinks_values — liana

**URL:** http://127.0.0.1:9050/en_latest_generated_liana.resource.get_metalinks_values.html

**Contents:**
- liana.resource.get_metalinks_values
- Contents
- liana.resource.get_metalinks_values#

Fetches distinct values from a specified column in a specified table.

db_path (str) – Path to the SQLite database file. If None, the database will be downloaded to the current working directory.

table_name (str) – Name of the table from which to fetch distinct values.

column_name (str) – Name of the column from which to fetch distinct values.

list A list of distinct values from the specified column.

liana.resource.describe_metalinks

liana.method.find_causalnet

By Daniel Dimitrov, Philipp Sven Lars Schäfer, Elias Farr, Pablo Rodriguez-Mier, Sebastian Lobentanzer, Pau Badia-i-Mompel, Aurelien Dugourd, Jovan Tanevski, Ricardo Omar Ramirez Flores, Julio Saez-Rodriguez

© Copyright 2025, Daniel Dimitrov, Philipp Sven Lars Schäfer, Elias Farr, Pablo Rodriguez-Mier, Sebastian Lobentanzer, Pau Badia-i-Mompel, Aurelien Dugourd, Jovan Tanevski, Ricardo Omar Ramirez Flores, Julio Saez-Rodriguez..

**Examples:**

Example 1 (unknown):
```unknown
get_metalinks_values()
```

Example 2 (unknown):
```unknown
get_metalinks_values()
```

---

## liana.method.geometric_mean.__call__ — liana

**URL:** http://127.0.0.1:9050/en_latest_generated_liana.method.geometric_mean.__call__.html

**Contents:**
- liana.method.geometric_mean.__call__
- Contents
- liana.method.geometric_mean.__call__#

Run a ligand-receptor method.

adata (AnnData | MuData) – Annotated data object.

groupby (str) – Key to be used for grouping.

resource_name (str (default: 'consensus')) – Name of the resource to be used for ligand-receptor inference. See li.rs.show_resources() for available resources.

expr_prop (float (default: 0.1)) – Minimum expression proportion for the ligands and receptors (+ their subunits) in the corresponding cell identities. Set to 0 to return unfiltered results.

min_cells (int (default: 5)) – Minimum cells (per cell identity if grouped by groupby) to be considered for downstream analysis.

groupby_pairs (DataFrame | None (default: None)) – A DataFrame with columns source and target to be used to subset the possible combinations of interacting cell types. If None, all possible combinations are used.

base (float (default: np.float64(2.718281828459045))) – Exponent base used to reverse the log-transformation of the matrix. Relevant only for the logfc method.

supp_columns (list | None (default: None)) – Additional columns to be added from any of the methods implemented in liana, or any of the columns returned by scanpy.tl.rank_genes_groups, each starting with ligand_* or receptor_*. For example, ['ligand_pvals', 'receptor_pvals']. None by default.

return_all_lrs (bool (default: False)) – Bool whether to return all ligand-receptor pairs, or only those that surpass the expr_prop threshold. Ligand-receptor pairs that do not pass the expr_prop threshold will be assigned to the worst score of the ones that do. False by default.

key_added (str (default: 'liana_res')) – Key under which the results will be stored in adata.uns if inplace is True.

use_raw (bool | None (default: True)) – Use raw attribute of adata if present.

layer (str | None (default: None)) – Layer in anndata.AnnData.layers to use. If None, use anndata.AnnData.X.

de_method (str (default: 't-test')) – Differential expression method. scanpy.tl.rank_genes_groups is used to rank genes according to 1vsRest. The default method is ‘t-test’.

verbose (bool | None (default: False)) – Verbosity flag.

n_perms (int (default: 1000)) – Number of permutations for the permutation test. Relevant only for permutation-based methods (e.g., CellPhoneDB). If None is passed, no permutation testing is performed.

seed (int (default: 1337)) – Random seed for reproducibility.

n_jobs (int (default: 1)) – Number of jobs to run in parallel.

resource (DataFrame | None (default: None)) – A pandas dataframe with [ligand, receptor] columns. If provided will overrule the resource requested via resource_name

interactions (list | None (default: None)) – List of tuples with ligand-receptor pairs [(ligand, receptor), ...] to be used for the analysis. If passed, it will overrule the resource requested via resource and resource_name.

mdata_kwargs (dict | None (default: None)) – Keyword arguments to be passed to li.fun.mdata_to_anndata if adata is an instance of MuData. If an AnnData object is passed, these arguments are ignored.

inplace (bool (default: True)) – Whether to store results in place, or else to return them.

If inplace = False, returns a DataFrame with ligand-receptor results Otherwise, modifies the adata object with the following key: - anndata.AnnData.uns [`key_added`] with the aforementioned DataFrame

liana.method.singlecellsignalr.__call__

liana.method.rank_aggregate.__call__

By Daniel Dimitrov, Philipp Sven Lars Schäfer, Elias Farr, Pablo Rodriguez-Mier, Sebastian Lobentanzer, Pau Badia-i-Mompel, Aurelien Dugourd, Jovan Tanevski, Ricardo Omar Ramirez Flores, Julio Saez-Rodriguez

© Copyright 2025, Daniel Dimitrov, Philipp Sven Lars Schäfer, Elias Farr, Pablo Rodriguez-Mier, Sebastian Lobentanzer, Pau Badia-i-Mompel, Aurelien Dugourd, Jovan Tanevski, Ricardo Omar Ramirez Flores, Julio Saez-Rodriguez..

**Examples:**

Example 1 (unknown):
```unknown
geometric_mean.__call__()
```

Example 2 (unknown):
```unknown
'consensus'
```

Example 3 (unknown):
```unknown
li.rs.show_resources()
```

Example 4 (python):
```python
np.float64(2.718281828459045)
```

Example 5 (unknown):
```unknown
scanpy.tl.rank_genes_groups
```

Example 6 (unknown):
```unknown
['ligand_pvals', 'receptor_pvals']
```

Example 7 (unknown):
```unknown
'liana_res'
```

Example 8 (unknown):
```unknown
scanpy.tl.rank_genes_groups
```

Example 9 (unknown):
```unknown
CellPhoneDB
```

Example 10 (unknown):
```unknown
resource_name
```

Example 11 (unknown):
```unknown
[(ligand, receptor), ...]
```

Example 12 (unknown):
```unknown
resource_name
```

Example 13 (unknown):
```unknown
li.fun.mdata_to_anndata
```

Example 14 (unknown):
```unknown
inplace = False
```

Example 15 (unknown):
```unknown
anndata.AnnData.uns
```

Example 16 (unknown):
```unknown
[`key_added`]
```

Example 17 (unknown):
```unknown
geometric_mean.__call__()
```

---

## liana.resource.explode_complexes — liana

**URL:** http://127.0.0.1:9050/en_latest_generated_liana.resource.explode_complexes.html

**Contents:**
- liana.resource.explode_complexes
- Contents
- liana.resource.explode_complexes#

Function to explode ligand-receptor complexes

resource (DataFrame) – Ligand-receptor resource

SOURCE (default: 'ligand') – Name of the source (typically ligand) column

TARGET (default: 'receptor') – Name of the target (typically receptor) column

A resource with exploded complexes

liana.resource.generate_lr_geneset

liana.resource.get_metalinks

By Daniel Dimitrov, Philipp Sven Lars Schäfer, Elias Farr, Pablo Rodriguez-Mier, Sebastian Lobentanzer, Pau Badia-i-Mompel, Aurelien Dugourd, Jovan Tanevski, Ricardo Omar Ramirez Flores, Julio Saez-Rodriguez

© Copyright 2025, Daniel Dimitrov, Philipp Sven Lars Schäfer, Elias Farr, Pablo Rodriguez-Mier, Sebastian Lobentanzer, Pau Badia-i-Mompel, Aurelien Dugourd, Jovan Tanevski, Ricardo Omar Ramirez Flores, Julio Saez-Rodriguez..

**Examples:**

Example 1 (unknown):
```unknown
explode_complexes()
```

Example 2 (unknown):
```unknown
explode_complexes()
```

---

## liana.utils.get_variable_loadings — liana

**URL:** http://127.0.0.1:9050/en_latest_generated_liana.utils.get_variable_loadings.html

**Contents:**
- liana.utils.get_variable_loadings
- Contents
- liana.utils.get_variable_loadings#

Extract variable loadings from an AnnData object.

adata (AnnData | MuData) – Annotated data object.

varm_key (str) – Key to use when extracting variable loadings from mdata.varm

view_sep (str) – Separator to use when splitting view:variable names into view and variable

variable_sep (str) – Separator to use when splitting variable names into var_names (‘ligand_complex’ and ‘receptor_complex’ by default)

pair_sep (str) – Separator to use when splitting view names into pair_names (‘source’ and ‘target’ by default)

drop_columns (bool) – If True, drop the view:variable column

Returns a pandas DataFrame with the variable loadings for the specified index.

liana.utils.get_factor_scores

liana.utils.interpolate_adata

By Daniel Dimitrov, Philipp Sven Lars Schäfer, Elias Farr, Pablo Rodriguez-Mier, Sebastian Lobentanzer, Pau Badia-i-Mompel, Aurelien Dugourd, Jovan Tanevski, Ricardo Omar Ramirez Flores, Julio Saez-Rodriguez

© Copyright 2025, Daniel Dimitrov, Philipp Sven Lars Schäfer, Elias Farr, Pablo Rodriguez-Mier, Sebastian Lobentanzer, Pau Badia-i-Mompel, Aurelien Dugourd, Jovan Tanevski, Ricardo Omar Ramirez Flores, Julio Saez-Rodriguez..

**Examples:**

Example 1 (unknown):
```unknown
get_variable_loadings()
```

Example 2 (unknown):
```unknown
view:variable
```

Example 3 (unknown):
```unknown
get_variable_loadings()
```

---
