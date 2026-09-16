# Liana-Py-Complete - Tutorials

**Pages:** 9

---

## Prior Knowledge — liana

**URL:** http://127.0.0.1:9050/en_latest_notebooks_prior_knowledge.html

**Contents:**
- Prior Knowledge
- Contents
- Prior Knowledge#
- Ligand-Receptor Interactions#
- Homology Mapping#
  - Obtain Mouse Homologs#
- Annotating Ligand-Receptors#
  - Pathway Annotations#
  - Disease Annotations#
- Intracellular Signaling#
  - 1) a protein-protein interaction network#
  - 2) Transcription Factor Regulons#
- Metabolite-Receptor Interactions#

LIANA+ (typically) relies heavily on prior knowledge to infer intercellular communication and the intracellular signaling pathways that are activated in response to communication. This notebook provides a brief overview of the prior knowledge typically used by LIANA+.

In the simplest case, for reproducibility purposes, LIANA+ provides a frozen set of interactions across resources. These are accessible through the select_resource function in the resource module. The resources that are currently supported are:

By default, liana uses the consensus resource, which is composed by multiple expert-curated ligand-receptor resources, including CellPhoneDB, CellChat, ICELLNET, connectomeDB2020, and CellTalkDB.

All of the ligand-receptor resource in LIANA+ were pre-generated using the OmniPath meta-database. Though any custom resource can also be passed, including those provided by the user or generated using the omnipath client package.

Via this client, in addition to ligand-receptor interactions, users can obtain the PubMed IDs of the references (references) that were used support each interaction, as well as the database that reported the interaction in the first place.

Users can also modify the resource according to their preferences, for example:

This function provides a rich list of annotations, such as the modes of action,inhibition or stimulation, the curation effort, types of signalling, etc. For a more comprehensive overview of the information that is available, please refer to the OmniPath documentation.

Similarly, LIANA+ provides on demand homology mapping beyond mouse symbols. It utilises the HCOP database to obtain homologous genes across species. Specifically, we download the resource from the frequently-updated Bulk Download FTP section of the HCOP database: https://ftp.ebi.ac.uk/pub/databases/genenames/hcop/.

The homology mapping is accessible through the resource module:

Now that we’ve obtained the homologous genes, let’s convert the resource to those genes:

4055 rows × 2 columns

If you use HCOP function, please reference the original HCOP papers:

Eyre, T.A., Wright, M.W., Lush, M.J. and Bruford, E.A., 2007. HCOP: a searchable database of human orthology predictions. Briefings in bioinformatics, 8(1), pp.2-5.

Yates, B., Gray, K.A., Jones, T.E. and Bruford, E.A., 2021. Updates to HCOP: the HGNC comparison of orthology predictions tool. Briefings in Bioinformatics, 22(6), p.bbab155.

All methods of LIANA+ accept a resource parameter that can be used to pass any custom resource, beyond such from homology conversion.

In addition to ligand-receptors, we can also obtain other annotations via OmniPath. While these can be tissue locations, TF regulons, cytokine signatures, or other types of annotations, the most common use case is to obtain the pathways that are associated with each ligand-receptor interaction.

We use commonly PROGENy pathway weights to assign interactions to certain canonical pathways, such that all members of the interactions (i.e. incl. complex subunits) are present in the same pathway with the same weight sign. This is done to ensure that the interaction is not only present in the same pathway, but also that it is likely to be active in the same direction.

Then we use the generate_lr_geneset function from liana to assign the interactions to pathways. This function takes the ligand-receptor interactions and the pathway annotations, and returns a dataframe with annotated interactions.

We can additionally performed enrichment analysis of certain ligand-receptor scores using this newly-generated dataframe. For example, see the application with Tensor-cell2cell

As another example, we can also annotate ligand-receptors to diseases in which both the ligand and the receptor are involved.

Let’s check some protein of interest:

Following similar procedures, one may annotate ligand-receptors to any of the annotations available via OmniPath.

See op.requests.Annotations.resources()

While we can obtain the pathways that are associated with each ligand-receptor interaction, we can also obtain the intracellular signaling pathways that are activated in response to the interaction. This is again done using the omnipath client package, but this time in combination with decoupler, which enables the enrichment of pathways, transcription factors, and other annotations.

One specific scenario, heavily reliant on OmniPath knowledge and enrichment analysis with decoupler is presented in the Differential Analysis Vignette.

There, to find putative causal networks between deregulated CCC interactions and transcription factors (TFs) we use:

Provided via the CollecTRI resource:

These are then linked using the a modification of the ILP problem proposed in CARNIVAL, solved using CORNETO - a Unified Omics-Driven Framework for Network Inference.

Via LIANA+ we also provide access to the MetalinksDB knowledge graph - a customisable database of metabolite-receptor interactions, part of the BioCypher ecosystem. For more information please refer to Farr et al, 2023.

Specifically, to enable light-weight access, we have converted the MetalinksDB knowledge graph into a database.

This database is queried using sqllite3 and we provide basic queries to customize according to the user’s needs - e.g. disease, pathway, location.

We can check first the values within different tables of the database:

Then we can obtain metabolite-receptor interactions, the metabolites of which have been reported to be associated with certain locations or diseases:

This database contains both ligand-receptor (lr) and production-degradation (pd) metabolite-protein interactions - note type. It can further be filtered according to the user’s needs, and can be queried as any other standard RDBMS.

For such cases, we also provide a utility function to print the database schema:

Multi-Modal Ligand-Receptor Inference

Spatially-informed Bivariate Metrics

By Daniel Dimitrov, Philipp Sven Lars Schäfer, Elias Farr, Pablo Rodriguez-Mier, Sebastian Lobentanzer, Pau Badia-i-Mompel, Aurelien Dugourd, Jovan Tanevski, Ricardo Omar Ramirez Flores, Julio Saez-Rodriguez

© Copyright 2025, Daniel Dimitrov, Philipp Sven Lars Schäfer, Elias Farr, Pablo Rodriguez-Mier, Sebastian Lobentanzer, Pau Badia-i-Mompel, Aurelien Dugourd, Jovan Tanevski, Ricardo Omar Ramirez Flores, Julio Saez-Rodriguez..

**Examples:**

Example 1 (python):
```python
import liana as li
import omnipath as op
import decoupler as dc
```

Example 2 (unknown):
```unknown
select_resource
```

Example 3 (unknown):
```unknown
li.resource.show_resources()
```

Example 4 (unknown):
```unknown
['baccin2019',
 'cellcall',
 'cellchatdb',
 'cellinker',
 'cellphonedb',
 'celltalkdb',
 'connectomedb2020',
 'consensus',
 'embrace',
 'guide2pharma',
 'hpmr',
 'icellnet',
 'italk',
 'kirouac2010',
 'lrdb',
 'mouseconsensus',
 'ramilowski2015']
```

Example 5 (unknown):
```unknown
resource = li.rs.select_resource('consensus')
resource.head()
```

Example 6 (unknown):
```unknown
ligrec = op.interactions.import_intercell_network(
    interactions_params = {'license':'commercial'},
    transmitter_params = {'database':'CellChatDB'},
    receiver_params = {'database':'CellChatDB'},
    )
ligrec.head()

ligrec = ligrec.rename(columns={'genesymbol_intercell_source':'ligand', 'genesymbol_intercell_target':'receptor'})
ligrec = ligrec[['ligand', 'receptor', 'references'] + [col for col in ligrec.columns if col not in ['ligand', 'receptor', 'references']]]
ligrec.head()
```

Example 7 (unknown):
```unknown
# let's say we are interested in zebrafish homologs of human genes
map_df = li.rs.get_hcop_orthologs(url='https://ftp.ebi.ac.uk/pub/databases/genenames/hcop/human_zebrafish_hcop_fifteen_column.txt.gz',
                                   columns=['human_symbol', 'zebrafish_symbol'],
                                   # NOTE: HCOP integrates multiple resource, so we can filter out mappings in at least 3 of them for confidence
                                   min_evidence=3
                                   )
# rename the columns to source and target, respectively for the original organism and the target organism
map_df = map_df.rename(columns={'human_symbol':'source', 'zebrafish_symbol':'target'})
map_df.tail()
```

Example 8 (unknown):
```unknown
zfish = li.rs.translate_resource(resource,
                                 map_df=map_df,
                                 columns=['ligand', 'receptor'],
                                 replace=True,
                                 # NOTE that we need to define the threshold of redundancies for the mapping
                                 # in this case, we would keep mappings as long as they don't map to more than 2 zebrafish genes
                                 one_to_many=3
                                 )
```

Example 9 (unknown):
```unknown
map_df = li.rs.get_hcop_orthologs(url='https://ftp.ebi.ac.uk/pub/databases/genenames/hcop/human_mouse_hcop_fifteen_column.txt.gz',
                                  columns=['human_symbol', 'mouse_symbol'],
                                   # NOTE: HCOP integrates multiple resource, so we can filter out mappings in at least 3 of them for confidence
                                   min_evidence=3
                                   )
# rename the columns to source and target, respectively for the original organism and the target organism
map_df = map_df.rename(columns={'human_symbol':'source', 'mouse_symbol':'target'})

# We will then translate
mouse = li.rs.translate_resource(resource,
                                 map_df=map_df,
                                 columns=['ligand', 'receptor'],
                                 replace=True,
                                 # Here, we will be harsher and only keep mappings that don't map to more than 1 mouse gene
                                 one_to_many=1
                                 )
mouse
```

Example 10 (unknown):
```unknown
# load PROGENy pathways, we use decoupler as a proxy as it formats the data in a more convenient way
progeny = dc.op.progeny(top=2500)
progeny.head()
```

Example 11 (unknown):
```unknown
# load full list of ligand-receptor pairs
lr_pairs = li.resource.select_resource('consensus')
```

Example 12 (unknown):
```unknown
generate_lr_geneset
```

Example 13 (unknown):
```unknown
# generate ligand-receptor geneset
lr_progeny = li.rs.generate_lr_geneset(lr_pairs, progeny, lr_sep="^")
lr_progeny.head()
```

Example 14 (unknown):
```unknown
diseases = op.requests.Annotations.get(
    resources = ['DisGeNet']
    )
```

Example 15 (unknown):
```unknown
diseases = diseases[['genesymbol', 'label', 'value']]
diseases = diseases.pivot_table(index='genesymbol',
                                columns='label', values='value',
                                aggfunc=lambda x: '; '.join(x)).reset_index()
diseases = diseases[['genesymbol', 'disease']]
diseases['disease'] = diseases['disease'].str.split('; ')
diseases = diseases.explode('disease')
lr_diseases = li.rs.generate_lr_geneset(lr_pairs, diseases, source='disease', target='genesymbol', weight=None, lr_sep="^")
lr_diseases.sort_values("interaction").head()
```

Example 16 (unknown):
```unknown
lr_diseases[lr_diseases['interaction'].str.contains('SPP1')]
```

Example 17 (unknown):
```unknown
op.requests.Annotations.resources()
```

Example 18 (unknown):
```unknown
ppis = op.interactions.OmniPath().get(genesymbols = True)
ppis.head()
```

Example 19 (unknown):
```unknown
dc.op.collectri(organism='human', remove_complexes=False, license='academic', verbose=False).head()
```

Example 20 (unknown):
```unknown
li.resource.get_metalinks_values(table_name='disease', column_name='disease')[0:5]
```

Example 21 (unknown):
```unknown
['Molybdenum cofactor deficiency',
 'Metastatic melanoma',
 'Schizophrenia',
 'Anoxia',
 'Colorectal cancer']
```

Example 22 (unknown):
```unknown
li.resource.get_metalinks(source=['Stich', 'CellPhoneDB', 'NeuronChat'],
                          tissue_location='Brain',
                          biospecimen_location='Cerebrospinal Fluid (CSF)',
                          disease='Schizophrenia',
                          ).head()
```

Example 23 (unknown):
```unknown
li.rs.describe_metalinks()
```

Example 24 (unknown):
```unknown
Schema of table: metabolites
============================
Column ID: 0, Name: hmdb, Type: TEXT, Primary Key: 0
Column ID: 1, Name: metabolite, Type: TEXT, Primary Key: 0
Column ID: 2, Name: pubchem, Type: TEXT, Primary Key: 0
Column ID: 3, Name: metabolite_subclass, Type: TEXT, Primary Key: 0

No Foreign Keys.
----------------------------------------
Schema of table: proteins
=========================
Column ID: 0, Name: uniprot, Type: TEXT, Primary Key: 0
Column ID: 1, Name: gene_symbol, Type: TEXT, Primary Key: 0
Column ID: 2, Name: protein_type, Type: TEXT, Primary Key: 0

No Foreign Keys.
----------------------------------------
Schema of table: edges
======================
Column ID: 0, Name: hmdb, Type: TEXT, Primary Key: 0
Column ID: 1, Name: uniprot, Type: TEXT, Primary Key: 0
Column ID: 2, Name: source, Type: TEXT, Primary Key: 0
Column ID: 3, Name: db_score, Type: REAL, Primary Key: 0
Column ID: 4, Name: experiment_score, Type: REAL, Primary Key: 0
Column ID: 5, Name: combined_score, Type: REAL, Primary Key: 0
Column ID: 6, Name: mor, Type: INTEGER, Primary Key: 0
Column ID: 7, Name: type, Type: TEXT, Primary Key: 0
Column ID: 8, Name: transport_direction, Type: TEXT, Primary Key: 0

No Foreign Keys.
----------------------------------------
Schema of table: cell_location
==============================
Column ID: 0, Name: hmdb, Type: TEXT, Primary Key: 0
Column ID: 1, Name: cell_location, Type: TEXT, Primary Key: 0

No Foreign Keys.
----------------------------------------
Schema of table: tissue_location
================================
Column ID: 0, Name: hmdb, Type: TEXT, Primary Key: 0
Column ID: 1, Name: tissue_location, Type: TEXT, Primary Key: 0

No Foreign Keys.
----------------------------------------
Schema of table: biospecimen_location
=====================================
Column ID: 0, Name: hmdb, Type: TEXT, Primary Key: 0
Column ID: 1, Name: biospecimen_location, Type: TEXT, Primary Key: 0

No Foreign Keys.
----------------------------------------
Schema of table: disease
========================
Column ID: 0, Name: hmdb, Type: TEXT, Primary Key: 0
Column ID: 1, Name: disease, Type: TEXT, Primary Key: 0

No Foreign Keys.
----------------------------------------
Schema of table: pathway
========================
Column ID: 0, Name: hmdb, Type: TEXT, Primary Key: 0
Column ID: 1, Name: pathway, Type: TEXT, Primary Key: 0

No Foreign Keys.
----------------------------------------
```

---

## Learning Spatial Relationships with MISTy — liana

**URL:** http://127.0.0.1:9050/en_latest_notebooks_misty.html

**Contents:**
- Learning Spatial Relationships with MISTy
- Contents
- Learning Spatial Relationships with MISTy#
- Environment#
  - Import generic packages#
  - Import Helper functions needed to create MISTy objects.#
  - Import Pre-defined Single view models#
- Load and Normalize Data#
  - Extract Cell type Composition#
- Funcomics#
  - Formatting & Running MISTy#
- Learn Relationships with MISTy#
  - Linear Misty#
    - Feature importances
- Build Custom Misty Views#
- Ligand-Receptor Misty#
  - Citing MISTy:#

Here, we show how to use LIANA’s implementation of MISTy, a framework presented in Tanevski et al., 2022.

MISTy is a tool that helps us better understand how different features, such as genes or cell types, interact with each other in space. MISTy does so by learning both intra- and extracellular relationships - i.e. those that occur within and between cells/spots. A major advantage of MISTy is its flexibility. It can model different perspectives, or “views,” each describing a different way markers are related to each other. Each of these views can describe a different spatial context, i.e. define a relationship among the observed expressions of the markers, such as intracellular regulation or paracrine regulation.

MISTy has only one fixed view - i.e. the intraview, which contains the target (dependent) variables. The other views we refer to as extra views, and they contain the independent variables used to predict the intra view. MISTy can fit any number of extra views, and each extra view can contain any number of variables. The extra views can thus simultaneously learn the dependencies of target variables across different modalities, such as cell type proportions, pathways, or genes, etc.

MISTy represents each view represents as a potential source of variation in the measurements of the target variables in the intra view. MISTy further analyzes each view to determine how it contributes to the overall expression or abundance of each target variable. It explains this contribution by identifying the interactions between measurements that led to the observed results.

To showcase MISTy, we use a single 10x Visium slide from Kuppe et al. (2022).

We will use an ischemic 10X Visium spatial slide from Kuppe et al., 2022. It is a tissue sample obtained from a patient with myocardial infarction, specifically focusing on the ischemic zone of the heart tissue.

The slide provides spatially-resolved information about the cellular composition and gene expression patterns within the tissue.

This slide comes with estimated cell type proportions using cell2location; See Kuppe et al., 2022. Let’s extract from .obsm them to an independent AnnData object.

Before we run MISTy, let’s estimate pathway activities as a way to make the data a bit more interpretable. We will use decoupler-py with pathways genesets from PROGENy. See this tutorial for details.

The implementation of MISTy in LIANA relies on MuData objects (Bredikhin et al., 2022) and extends them to a very simple child class we call “MistyData”. To make it easier to use, we provide functions to construct “MistyData” objects that transform the data into a format that MISTy can use.

Briefly, a “MistyData” object is just a MuData object with intra as one of the modalities - this is the view in which the (target) variables explained by all other views are stored. MISTy is flexible to any other view that is appended, provided it also contains a spatial neighbors graph.

Let’s use genericMistyData to construct a MuData object with the intra view and the cell type proportions as the first view. Then it additionally build a ‘juxta’ view for the spots that are neighbors of each other, and a ‘para’ view for all surrounding spots within a certain radius, or bandwidth.

In this case, we will use cell type compositions per spot as the intra view, and we will use the PROGENy pathway activities as the juxta and para views:

Now that we have constructed the object, let’s learn the relationships across the views.

Specifically, we will use the RandomForestModel to fit an individual random forrest model for each target in the intra view, using the juxta and para views as predictors.

MISTy returns two DataFrames:

target_metrics - the metrics that describe the target variables from the intra view, including R-squared across different views as well as the estimated contributions to the predictive performance of each view per target.

interactions - feature importances per view

if inplace is true (Default), these are appended to the MuData object.

Let’s check the variance explained when predicting each target variables in the intra view, with other variables (predictors) in the intra view itself. We can see that it explains itself relatively well (as expected).

MISTy additionally calculate gain_R2, or in other words the performance gain when we additionally consider the other views (in addition to intra). When we look at the variance explained by the other views, we see that they explain a bit less (as expected), but still there is still some gain of predictive performance:

We can also check the contribution to the predictive performance of each view per target:

Finally, using the information above we know which variables are best explained by our model, and we know which view explains them best. So, we can now also see what are the specific variables that explain each target best:

We can also use a Linear model, while a bit more simplistic is much faster and more interpretable.

Moreover, we will bypass predicting the intraview with features within the intraview features (bypass_intra). This will allow us to see how well the other views explain the intraview, excluding the intraview itself.

Let’s check the joined R-squared for views:

and their contributions per target:

Since this is a linear model, the coefficients would not be directly comparable (as are importances in a Random Forest). Thus, we use the coefficients’ t-values, as calculated by Ordinary Least Squares, which are signed and directly comparable.

Let’s explore the t-values for each target-prediction interaction:

Regardless of the model, each target is predicted independently, and the interpretation of feature importances depends on the model used. By default, we use a random forest, so the feature importances are the mean decrease in Gini impurity of the features. On the other hand, when we use a linear model, the feature importances are the t-values of the model coefficients.

As we previously mentioned, one can build any view structure that they deem relevant for their data. So, let’s explore how to build custom views. Here, we will just use two distinct prior knowledge sources to check which one achieves better predictive performance.

So, let’s also estimate Transcription Factor activities with decoupler:

In addition to the features, we also need to provide spatial weights for the spots. Here, we will use LIANA’s inbuilt radial kernel function to compute spatial weights based on the spatial coordinates of the spots. However, this can be replaced by any other spatial weights matrix, such as those calculated via squidpy.gr.spatial_neighbors.

Visualize the weights for a specific spot:

Build an object with custom views:

We can see that Cardiomyocytes and Fibroblasts are relatively well explained by TFs & Pathways.

We also see that the two views explain the targets similarly well.

Plot cell type x Trascription factor interactions

Finally, we provide a utility function that builds an object with receptors in the intra view and ligands in the para view (or in their surrounding).

For the sake of computational speed, let’s identify the highly variable genes

Build LR Misty object:

Let’s now explore the top interactions between the ligands and receptors:

In contrast to any other other functions in LIANA, misty will infer all possible interactions between ligands and receptors - i.e. not only those that were annotated specifically as ligand-receptor interactions.

While this can be seen as a limitation, it can also be seen as an advantage of MISTy, as it allows us to explore potential ligand-receptor interactions that were not previously annotated!

If you use MISTy via LIANA+, please cite MISTy’s original publication (Tanevski et al., 2022)

Integrating Multi-Modal Spatially-Resolved Technologies with LIANA+

Differential Expression Analysis for CCC & Downstream Signalling Networks

By Daniel Dimitrov, Philipp Sven Lars Schäfer, Elias Farr, Pablo Rodriguez-Mier, Sebastian Lobentanzer, Pau Badia-i-Mompel, Aurelien Dugourd, Jovan Tanevski, Ricardo Omar Ramirez Flores, Julio Saez-Rodriguez

© Copyright 2025, Daniel Dimitrov, Philipp Sven Lars Schäfer, Elias Farr, Pablo Rodriguez-Mier, Sebastian Lobentanzer, Pau Badia-i-Mompel, Aurelien Dugourd, Jovan Tanevski, Ricardo Omar Ramirez Flores, Julio Saez-Rodriguez..

**Examples:**

Example 1 (python):
```python
import scanpy as sc
import decoupler as dc
import plotnine as p9
import liana as li
```

Example 2 (python):
```python
from liana.method import MistyData, genericMistyData, lrMistyData
```

Example 3 (python):
```python
from liana.method.sp import RandomForestModel, LinearModel, RobustLinearModel
```

Example 4 (python):
```python
adata = sc.read("kuppe_heart19.h5ad", backup_url='https://figshare.com/ndownloader/files/41501073?private_link=4744950f8768d5c8f68c')
```

Example 5 (python):
```python
adata.obs.head()
```

Example 6 (python):
```python
adata.layers['counts'] = adata.X.copy()
sc.pp.normalize_total(adata, target_sum=1e4)
sc.pp.log1p(adata)
```

Example 7 (python):
```python
sc.pl.spatial(adata, color=[None, 'celltype_niche'], size=1.3, palette='Set1')
```

Example 8 (python):
```python
# Rename to more informative names
full_names = {'Adipo': 'Adipocytes',
              'CM': 'Cardiomyocytes',
              'Endo': 'Endothelial',
              'Fib': 'Fibroblasts',
              'PC': 'Pericytes',
              'prolif': 'Proliferating',
              'vSMCs': 'Vascular_SMCs',
              }
# but only for the ones that are in the data
adata.obsm['compositions'].columns = [full_names.get(c, c) for c in adata.obsm['compositions'].columns]
```

Example 9 (python):
```python
comps = li.ut.obsm_to_adata(adata, 'compositions')
```

Example 10 (python):
```python
# check key cell types
sc.pl.spatial(comps,
              color=['Vascular_SMCs','Cardiomyocytes',
                     'Endothelial', 'Fibroblasts'],
              size=1.3, ncols=2, alpha_img=0
              )
```

Example 11 (unknown):
```unknown
# obtain genesets
progeny = dc.op.progeny(organism='human', top=500)
```

Example 12 (python):
```python
# use multivariate linear model to estimate activity
dc.mt.mlm(
    adata,
    net=progeny,
    verbose=True,
    raw=False
)
```

Example 13 (python):
```python
# extract progeny activities as an AnnData object
acts_progeny = li.ut.obsm_to_adata(adata, 'score_mlm')
```

Example 14 (python):
```python
# Check how the pathway activities look like
sc.pl.spatial(acts_progeny, color=['Hypoxia', 'JAK-STAT'], cmap='RdBu_r', size=1.3)
```

Example 15 (unknown):
```unknown
genericMistyData
```

Example 16 (unknown):
```unknown
misty = genericMistyData(intra=comps, extra=acts_progeny, cutoff=0.05, bandwidth=200, n_neighs=6)
```

Example 17 (unknown):
```unknown
MuData object with n_obs × n_vars = 4113 × 39
  obs:	'in_tissue', 'array_row', 'array_col', 'sample', 'n_genes_by_counts', 'log1p_n_genes_by_counts', 'total_counts', 'log1p_total_counts', 'pct_counts_in_top_50_genes', 'pct_counts_in_top_100_genes', 'pct_counts_in_top_200_genes', 'pct_counts_in_top_500_genes', 'mt_frac', 'celltype_niche', 'molecular_niche'
  3 modalities
    intra:	4113 x 11
      obs:	'in_tissue', 'array_row', 'array_col', 'sample', 'n_genes_by_counts', 'log1p_n_genes_by_counts', 'total_counts', 'log1p_total_counts', 'pct_counts_in_top_50_genes', 'pct_counts_in_top_100_genes', 'pct_counts_in_top_200_genes', 'pct_counts_in_top_500_genes', 'mt_frac', 'celltype_niche', 'molecular_niche'
      obsm:	'spatial'
    juxta:	4113 x 14
      obsm:	'spatial'
      layers:	'weighted'
      obsp:	'spatial_connectivities'
    para:	4113 x 14
      obsm:	'spatial'
      layers:	'weighted'
      obsp:	'spatial_connectivities'
```

Example 18 (unknown):
```unknown
misty(model=RandomForestModel, n_jobs=-1, verbose = True)
```

Example 19 (unknown):
```unknown
RandomForestModel
```

Example 20 (unknown):
```unknown
target_metrics
```

Example 21 (unknown):
```unknown
interactions
```

Example 22 (unknown):
```unknown
misty.uns['target_metrics'].head()
```

Example 23 (unknown):
```unknown
li.pl.target_metrics(misty, stat='intra_R2', return_fig=True)
```

Example 24 (unknown):
```unknown
li.pl.target_metrics(misty, stat='gain_R2')
```

Example 25 (unknown):
```unknown
li.pl.contributions(misty, return_fig=True)
```

Example 26 (unknown):
```unknown
# this information is stored here:
misty.uns['interactions'].head()
```

Example 27 (unknown):
```unknown
li.pl.interactions(misty, view='juxta', return_fig=True, figure_size=(7,5))
```

Example 28 (unknown):
```unknown
bypass_intra
```

Example 29 (unknown):
```unknown
misty(model=LinearModel, k_cv=10, seed=1337, bypass_intra=True, verbose = True)
```

Example 30 (unknown):
```unknown
li.pl.target_metrics(misty, stat='gain_R2', return_fig=True)
```

Example 31 (unknown):
```unknown
li.pl.contributions(misty, return_fig=True)
```

Example 32 (unknown):
```unknown
(
    li.pl.interactions(misty, view='juxta', return_fig=True, figure_size=(7,5)) + 
    p9.scale_fill_gradient2(low = "blue", mid = "white", high = "red", midpoint = 0)
)
```

Example 33 (unknown):
```unknown
# get TF prior knowledge
net = dc.op.collectri(organism='human', remove_complexes=False, license='academic', verbose=False)
```

Example 34 (python):
```python
# Estimate activities
dc.mt.ulm(
    mat=adata,
    net=net,
    verbose=True,
    raw=False
)
```

Example 35 (python):
```python
---------------------------------------------------------------------------
TypeError                                 Traceback (most recent call last)
Cell In[30], line 2
      1 # Estimate activities
----> 2 dc.mt.ulm(
      3     mat=adata,
      4     net=net,
      5     verbose=True,
      6     raw=False
      7 )

TypeError: Method.__call__() missing 1 required positional argument: 'data'
```

Example 36 (python):
```python
# extract activities
acts_tfs = li.ut.obsm_to_adata(adata, 'score_ulm')
```

Example 37 (unknown):
```unknown
squidpy.gr.spatial_neighbors
```

Example 38 (unknown):
```unknown
# Calculate spatial neighbors
li.ut.spatial_neighbors(acts_tfs, cutoff=0.1, bandwidth=200, set_diag=False)
```

Example 39 (unknown):
```unknown
li.pl.connectivity(acts_tfs, idx=0, figure_size=(6,5))
```

Example 40 (unknown):
```unknown
# transfer spatial information to progeny activities
# NOTE: spatial connectivities can differ between views, but in this case we will use the same
acts_progeny.obsm['spatial'] = acts_tfs.obsm['spatial']
acts_progeny.obsp['spatial_connectivities'] = acts_tfs.obsp['spatial_connectivities']
```

Example 41 (unknown):
```unknown
misty = MistyData(data={"intra": comps, "TFs": acts_tfs, "Pathways": acts_progeny})
```

Example 42 (unknown):
```unknown
MuData object with n_obs × n_vars = 4113 × 719
  obs:	'in_tissue', 'array_row', 'array_col', 'sample', 'n_genes_by_counts', 'log1p_n_genes_by_counts', 'total_counts', 'log1p_total_counts', 'pct_counts_in_top_50_genes', 'pct_counts_in_top_100_genes', 'pct_counts_in_top_200_genes', 'pct_counts_in_top_500_genes', 'mt_frac', 'celltype_niche', 'molecular_niche'
  3 modalities
    intra:	4113 x 11
      obs:	'in_tissue', 'array_row', 'array_col', 'sample', 'n_genes_by_counts', 'log1p_n_genes_by_counts', 'total_counts', 'log1p_total_counts', 'pct_counts_in_top_50_genes', 'pct_counts_in_top_100_genes', 'pct_counts_in_top_200_genes', 'pct_counts_in_top_500_genes', 'mt_frac', 'celltype_niche', 'molecular_niche'
      uns:	'spatial', 'log1p', 'celltype_niche_colors'
      obsm:	'compositions', 'mt', 'spatial'
    TFs:	4113 x 694
      obs:	'in_tissue', 'array_row', 'array_col', 'sample', 'n_genes_by_counts', 'log1p_n_genes_by_counts', 'total_counts', 'log1p_total_counts', 'pct_counts_in_top_50_genes', 'pct_counts_in_top_100_genes', 'pct_counts_in_top_200_genes', 'pct_counts_in_top_500_genes', 'mt_frac', 'celltype_niche', 'molecular_niche'
      uns:	'spatial', 'log1p', 'celltype_niche_colors'
      obsm:	'compositions', 'mt', 'spatial', 'mlm_estimate', 'mlm_pvals', 'ulm_estimate', 'ulm_pvals'
      layers:	'weighted'
      obsp:	'spatial_connectivities'
    Pathways:	4113 x 14
      obs:	'in_tissue', 'array_row', 'array_col', 'sample', 'n_genes_by_counts', 'log1p_n_genes_by_counts', 'total_counts', 'log1p_total_counts', 'pct_counts_in_top_50_genes', 'pct_counts_in_top_100_genes', 'pct_counts_in_top_200_genes', 'pct_counts_in_top_500_genes', 'mt_frac', 'celltype_niche', 'molecular_niche'
      uns:	'spatial', 'log1p', 'celltype_niche_colors'
      obsm:	'compositions', 'mt', 'spatial', 'mlm_estimate', 'mlm_pvals'
      layers:	'weighted'
      obsp:	'spatial_connectivities'
```

Example 43 (unknown):
```unknown
misty(model=LinearModel, verbose=True, bypass_intra=True)
```

Example 44 (unknown):
```unknown
li.pl.target_metrics(misty, stat='gain_R2')
```

Example 45 (unknown):
```unknown
li.pl.contributions(misty, return_fig=True)
```

Example 46 (unknown):
```unknown
(
    li.pl.interactions(misty, view='TFs', top_n=20) + 
    p9.labs(x='Transcription Factor', y='Cell type') +
    p9.theme_bw(base_size=14) +
    p9.theme(axis_text_x=p9.element_text(rotation=90, size=13)) +
    # change to blue-red
    p9.scale_fill_gradient2(low='blue', mid='white', high='red')
)
```

Example 47 (python):
```python
sc.pp.highly_variable_genes(adata)
hvg = adata.var[adata.var['highly_variable']].index
```

Example 48 (python):
```python
misty = lrMistyData(adata[:, hvg], bandwidth=200, set_diag=False, cutoff=0.01, nz_threshold=0.1)
```

Example 49 (unknown):
```unknown
misty(bypass_intra=True, model=LinearModel, verbose=True)
```

Example 50 (unknown):
```unknown
(
    li.pl.interactions(misty, view='extra', return_fig=True, figure_size=(6, 5), top_n=25, key=abs) + 
    p9.scale_fill_gradient2(low = "blue", mid = "white", high = "red", midpoint = 0) +
    p9.labs(y='Receptor', x='Ligand')
)
```

---

## Multi-Modal Ligand-Receptor Inference — liana

**URL:** http://127.0.0.1:9050/en_latest_notebooks_sc_multi.html

**Contents:**
- Multi-Modal Ligand-Receptor Inference
- Contents
- Multi-Modal Ligand-Receptor Inference#
- Infer Ligand-Receptor Interactions between RNA and Proteins#
  - Download Processed CITE-seq Data#
  - Load Processed CITE-Seq Data#
  - Infer Interactions#
  - Plot Results & More#
- Metabolite-mediated CCC from Transcriptomics Data#
  - Focus on Transcriptomics Data#
  - Obtain MetalinksDB Prior Knowledge#
  - Prepare the Metabolite-Receptor Resource#
  - Prepare the Production-Degradation Network#
  - Prepare the transporter network#
  - Infer Metabolite-Receptor Interactions#
  - Explore Results#
- Next Steps#

This notebook shows how to 1. analyse single-cell cite-seq data; 2. how to infer metabolite-receptor interactions from transcriptomics data.

Here, we will use a very simple dataset to demonstrate the multi-modal ligand-receptor inference. We used a CITE-Seq dataset from 10X and followed the muon CITE-seq tutorial to process the RNA and Protein data.

Some minor differences are notable in the clustering due to the different versions of the packages used in the tutorial and the LIANA+ environment.

We see that we have two modalities, once for RNA and one for Proteins. We will next infer the ligand-receptor interactions between these two modalities.

CITE-seq data often focuses on antibody tagging of surface proteins, primarily receptors. To ensure only the protein modality is used for receptors, we append 'AB:' to receptor names in the antibody data. This step is necessary only when both RNA and antibody data have matching feature names.

While running LIANA+ with multimodal is largely analogous to when working with uni-modal data, there are a couple of things to keep in mind. Here, we need to ensure that the correct data is passed from each modality as well as to ensure that the correct modalities are used. Moreover, we need to ensure that data from the different modalities is comparable, which often requires the transformation of the data.

In this case, we use zero-inflated min-max normalization to ensure that the data from the two modalities is comparable. Essentially, a min-max normalization in which any value bellow 0.5 (by default) following normalization is set to 0. This normalization was originally introduced by the CiteFuse method, which is a ligand-receptor method for CITE-seq data.

Note that feature-wise min-max binds all features (i.e. genes and proteins) to the same limits, which essentially neglects the biological differences between features. This is typically not the case when working with untransformed data, as in that case we mostly care about cells being comparable, while features are typically with variable limits / distributions. As such, there might be some subtle differences from the interpretation of LIANA+ results, depending on the transformation of choice.

A benchmark of different normalizations for CCC are pending and alternative normalizations should also be explored. While other normalizations and subsequent transformations can also be used, the single-cell methods in LIANA+ require the data to be non-negative.

Recently, tools such as NeuronChat, MEBOCOST, scConnect, Cellinker, and CellPhoneDBv5 have proposed approaches, such as enrichment, expression average, among others, to infer metabolite-mediated CCC events from transcriptomics data. Similarly, we can use LIANA+ to infer metabolite-mediated CCC events from transcriptomics data, as described in the MetalinksDB manuscript.

Briefly, we use a univariate linear regression model to estimate metabolite abundances for each cell. To do so, we make use of production-degradation enzyme prior knowledge to infer the metabolite abundances. Optionally, we also take transporters into account. We then use these inferred metabolite abundances to infer metabolite-mediated CCC events.

Here, we will use MetalinksDB which contains prior knowledge about metabolite-receptor interactions as well as such for the production and degradation enzymes for metabolites. We will use the latter type of prior knowledge to infer the metabolite abundances for each cell.

Essentially, we now have a dataset with two modalities, one for RNA and one for Metabolites. The metabolites are estimated as t-values. Let’s visualize a couple:

We will next infer the putative ligand-receptor interactions between these two modalities.

From here on one may follow-up with any of the other LIANA+ functionalities, such as plotting the results, or cross-conditional analyses.

Steady-state Ligand-Receptor inference

By Daniel Dimitrov, Philipp Sven Lars Schäfer, Elias Farr, Pablo Rodriguez-Mier, Sebastian Lobentanzer, Pau Badia-i-Mompel, Aurelien Dugourd, Jovan Tanevski, Ricardo Omar Ramirez Flores, Julio Saez-Rodriguez

© Copyright 2025, Daniel Dimitrov, Philipp Sven Lars Schäfer, Elias Farr, Pablo Rodriguez-Mier, Sebastian Lobentanzer, Pau Badia-i-Mompel, Aurelien Dugourd, Jovan Tanevski, Ricardo Omar Ramirez Flores, Julio Saez-Rodriguez..

**Examples:**

Example 1 (python):
```python
import numpy as np
import pandas as pd
import scanpy as sc
import liana as li
import mudata as mu
from matplotlib import pyplot as plt
```

Example 2 (python):
```python
prot = sc.read('citeseq_prot.h5ad', backup_url='https://figshare.com/ndownloader/files/47625196')
rna = sc.read('citeseq_rna.h5ad', backup_url='https://figshare.com/ndownloader/files/47625193')
```

Example 3 (unknown):
```unknown
mdata = mu.MuData({'rna': rna, 'prot': prot})
# make sure that cell type is accessible
mdata.obs['celltype'] = mdata.mod['rna'].obs['celltype'].astype('category')
# inspect the object
mdata
```

Example 4 (unknown):
```unknown
MuData object with n_obs × n_vars = 3885 × 17838
  obs:	'celltype'
  var:	'gene_ids', 'feature_types', 'genome'
  2 modalities
    rna:	3885 x 17806
      obs:	'n_genes_by_counts', 'total_counts', 'total_counts_mt', 'pct_counts_mt', 'leiden', 'celltype'
      var:	'gene_ids', 'feature_types', 'genome', 'mt', 'n_cells_by_counts', 'mean_counts', 'pct_dropout_by_counts', 'total_counts', 'highly_variable', 'means', 'dispersions', 'dispersions_norm'
      uns:	'hvg', 'leiden', 'leiden_colors', 'log1p', 'neighbors', 'pca', 'rank_genes_groups', 'umap'
      obsm:	'X_pca', 'X_umap'
      obsp:	'connectivities', 'distances'
    prot:	3885 x 32
      var:	'gene_ids', 'feature_types', 'genome'
      uns:	'neighbors', 'pca', 'umap'
      obsm:	'X_pca', 'X_umap'
      varm:	'PCs'
      layers:	'counts'
      obsp:	'connectivities', 'distances'
```

Example 5 (unknown):
```unknown
# Obtain a ligand-receptor resource of interest
resource = li.rs.select_resource(resource_name='consensus')
# Append AB: to the receptor names
resource['receptor'] = 'AB:' + resource['receptor']

# Append AB: to the protein modality
mdata.mod['prot'].var_names = 'AB:' + mdata.mod['prot'].var['gene_ids']
```

Example 6 (python):
```python
li.mt.rank_aggregate(adata=mdata,
                     groupby='celltype',
                     # pass our modified resource
                     resource=resource,
                     # NOTE: Essential arguments when handling multimodal data
                     mdata_kwargs={
                     # Ligand-Receptor pairs are directed so we need to correctly pass
                     # `RNA` with ligands as `x_mod` and receptors as `y_mod`
                     'x_mod': 'rna',
                     'y_mod': 'prot',
                     # We use .X from the x_mod
                     'x_use_raw':False,
                     # We use .X from the y_mod
                     'y_use_raw':False,
                     # NOTE: we need to ensure that the modalities are correctly transformed
                     'x_transform':li.ut.zi_minmax,
                     'y_transform':li.ut.zi_minmax,
                    },
                  verbose=True
                  )
```

Example 7 (unknown):
```unknown
Using provided `resource`.
Transforming rna using zi_minmax
Transforming prot using zi_minmax
Generating ligand-receptor stats for 3885 samples and 37 features
Assuming that counts were `natural` log-normalized!
Running CellPhoneDB
Running Connectome
Running log2FC
Running NATMI
Running SingleCellSignalR
```

Example 8 (unknown):
```unknown
mdata.uns['liana_res'].head()
```

Example 9 (python):
```python
li.pl.dotplot(adata = mdata,
              colour='lr_means',
              size='specificity_rank',
              inverse_size=True, # we inverse sign since we want small p-values to have large sizes
              source_labels=['CD4+ naïve T', 'NK', 'Treg', 'CD8+ memory T'],
              target_labels=['CD14 mono', 'mature B', 'CD8+ memory T', 'CD16 mono'],
              figure_size=(9, 5),
              # finally, since cpdbv2 suggests using a filter to FPs
              # we filter the pvals column to <= 0.05
              filter_fun=lambda x: x['cellphone_pvals'] <= 0.05,
              cmap='plasma'
             )
```

Example 10 (unknown):
```unknown
<Figure Size: (900 x 500)>
```

Example 11 (python):
```python
adata = mdata.mod['rna']
```

Example 12 (unknown):
```unknown
metalinks = li.resource.get_metalinks(biospecimen_location='Blood',
                                      source=['CellPhoneDB', 'Cellinker', 'scConnect', # Ligand-Receptor resources
                                              'recon', 'hmr', 'rhea', 'hmdb' # Production-Degradation resources
                                              ],
                                      types=['pd', 'lr'], # NOTE: we obtain both ligand-receptor and production-degradation sets
                                     )
```

Example 13 (unknown):
```unknown
resource = metalinks[metalinks['type']=='lr'].copy()
resource = resource[['metabolite', 'gene_symbol']]\
    .rename(columns={'gene_symbol':'receptor'}).drop_duplicates()
resource.head()
```

Example 14 (unknown):
```unknown
pd_net = metalinks[metalinks['type'] == 'pd']
# we need to aggregate the production-degradation values
pd_net = pd_net[['metabolite', 'gene_symbol', 'mor']].groupby(['metabolite', 'gene_symbol']).agg('mean').reset_index()
pd_net.head()
```

Example 15 (python):
```python
t_net = metalinks[metalinks['type'] == 'pd']
t_net = t_net[['metabolite', 'gene_symbol', 'transport_direction']].dropna()
# Note that we treat export as positive and import as negative
t_net['mor'] = t_net['transport_direction'].apply(lambda x: 1 if x == 'out' else -1 if x == 'in' else None)
t_net = t_net[['metabolite', 'gene_symbol', 'mor']].dropna().groupby(['metabolite', 'gene_symbol']).agg('mean').reset_index()
t_net = t_net[t_net['mor']!=0]
```

Example 16 (python):
```python
meta = li.mt.fun.estimate_metalinks(adata,
                                    resource,
                                    pd_net=pd_net,
                                    t_net=t_net, # (Optional)
                                    use_raw=False, 
                                    # keyword arguments passed to decoupler-py
                                    source='metabolite', target='gene_symbol',
                                    weight='mor', min_n=3)
# pass cell type information
meta.obs['celltype'] = adata.obs['celltype']
```

Example 17 (python):
```python
with plt.rc_context({"figure.figsize": (5, 5), "figure.dpi": (100)}):
    sc.pl.umap(meta.mod['metabolite'], color=['Prostaglandin J2', 'Metanephrine', 'celltype'], cmap='coolwarm')
```

Example 18 (python):
```python
li.mt.rank_aggregate(adata=meta,
                     groupby='celltype',
                     # pass our modified resource
                     resource=resource.rename(columns={'metabolite':'ligand'}),
                     # NOTE: Essential arguments when handling multimodal data
                     mdata_kwargs={
                     'x_mod': 'metabolite',
                     'y_mod': 'receptor',
                     'x_use_raw':False,
                     'y_use_raw':False,
                     'x_transform':li.ut.zi_minmax,
                     'y_transform':li.ut.zi_minmax,
                    },
                  verbose=True
                  )
```

Example 19 (unknown):
```unknown
Using provided `resource`.
Transforming metabolite using zi_minmax
Transforming receptor using zi_minmax
Generating ligand-receptor stats for 3885 samples and 190 features
Assuming that counts were `natural` log-normalized!
Running CellPhoneDB
Running Connectome
Running log2FC
Running NATMI
Running SingleCellSignalR
```

Example 20 (unknown):
```unknown
meta.uns['liana_res'].head()
```

Example 21 (python):
```python
li.pl.dotplot(adata = meta,
              colour='lr_means',
              size='cellphone_pvals',
              inverse_size=True, # we inverse sign since we want small p-values to have large sizes
              source_labels=['CD4+ naïve T', 'NK', 'Treg', 'CD8+ memory T'],
              target_labels=['CD14 mono', 'mature B', 'CD8+ memory T', 'CD16 mono'],
              figure_size=(12, 6),
              # Filter to top 10 acc to magnitude rank
              top_n=10,
              orderby='magnitude_rank',
              orderby_ascending=True,
              cmap='plasma'
             )
```

Example 22 (unknown):
```unknown
<Figure Size: (1200 x 600)>
```

---

## Intercellular Context Factorization with MOFA — liana

**URL:** http://127.0.0.1:9050/en_latest_notebooks_mofatalk.html

**Contents:**
- Intercellular Context Factorization with MOFA
- Contents
- Intercellular Context Factorization with MOFA#
- Background#
- Load Packages#
- Load & Prep Data#
  - Basic Preparation#
  - Showcase the data#
- Ligand-Receptor Inference by Sample#
    - by_sample
- Create a Multi-View Structure#
      - View Representation
- Fitting a MOFA model#
- Exploring the MOFA model#
  - Explore Metadata Associations to the Factor Scores#
    - Explore Ligand-Receptor loadings#
  - Explore the model#
- Pathway enrichment#
- Outlook & Further Analysis#

Here, we will adapt the statistical framework of multi-omics factor analysis (MOFA) to obtain intercellular communication programmes - in the form of ligand-receptor interaction scores observed to change across samples. This application of MOFA is inspired by and is in line with the factorization proposed by Tensor-cell2cell Armingol and Baghdassarian et al., 2022 - see existing tutorial.

Such factorization approaches essentially enable us to decipher context-driven intercellular communication by simultaneously accounting for an unlimited number of “contexts” in an untargeted manner. Similarly to Tensor-cell2cell, this application of MOFA is able to handle cell-cell communication results coming from any experimental design, regardless of its complexity.

Simply put, we will use LIANA’s output by sample to build a multi-view structure represented by samples and interactions by cell type pairs (views). We will then use MOFA+ to capture the CCC patterns across samples. To do so, we combine liana with the MuData/muon infrastructure.

mofa, decoupler, omnipath, and marsilea can be installed via pip with the following commands:

As a simple example, we will look at ~25k PBMCs from 8 pooled patient lupus samples, each before and after IFN-beta stimulation (Kang et al., 2018; GSE96583). Note that by focusing on PBMCs, for the purpose of this tutorial, we assume that coordinated events occur among them.

This dataset is downloaded from a link on Figshare; preprocessed for pertpy.

Define columns of interest from .obs

Note that we use cell abbreviations because MOFA will use them as labels for the views.

Note that this data has been largely pre-processed & annotated, we refer the user to the Quality Control and other relevant chapters from the best-practices book for information about pre-processing and annotation steps.

Before we decompose the CCC patterns across contexts/samples with MOFA, we first need to run liana on each sample. To do so, liana provides a utility function called by_sample that runs each method in LIANA on each sample within the AnnData object, and returns a long-format pandas.DataFrame with the results.

In this example, we will use liana’s rank_aggregate method, which provides a robust rank consensus that combines the predictions of multiple ligand-receptor methods. Nevertheless, any other method can be used.

We see that in addition to the usual results, we also get sample as a column which corresponds to the name of the sample_key in the AnnData object.

Now that we have obtained results by sample, we can use a dotplot by sample to visualize the ligand-receptor interactions. Let’s pick arbitrarily the interactions with the highest magnitude_rank.

Even on a small subset interactions and cell types, we can see that interpretation becomes challenging. To overcome this, we can use MOFA to find the variable CCC patterns across contexts/samples.

Before we can identify the variable CCC patterns across contexts/samples, we need to create a multi-view structure. In this case, we will use the lrs_to_views function from liana to create a list of views (stored in a MuData object), where each view corresponds to a pair of potentially interacting cell types. The scores of interactions between cell type pairs represent those inferred with liana, stored by default in adata.uns['liana_res']. Here, we will use liana’s aggregate ‘magnitude_rank’.

The lr_fill parameter controls how we deal with missing interaction scores. The default is np.nan and in that case the scores would be imputed by MOFA.

Here, we fill the missing ligand-receptors with 0s because the ligand-receptor interaction missing here, i.e. those when return_all_lrs=False, are such which are not expressed above a certain proportion of cells per cell type (that is controlled via expr_prop when running liana).

Given the assumption that the ligand-receptor interactions occur at the across cell type level, we could thus assume that the genes that are not present in a sufficient proportion of cells are unlikely to be involved in interactions that are relevant to the cell type as a whole.

MOFA supports the flexible representation of views, where each view can represent a different type of features (e.g. genes, proteins, metabolites, etc.). In this case, we simply allow for different ligand-receptor to be used in each cell type pair (view).

Now that the putative ligand-receptor interactions across samples aretransformed into a multi-view representation, we can use MOFA to run an intercellular communication factor analysis.

We will attempt to capture the variability across samples and the different cell-type pairs by reducing the data into a number of factors, where each factor captures the coordinated communication events across the cell types.

For convenience, we provide simple getter function to access the model parameters, in addition to those available via the MuData API & the MOFA model itself.

Let’s check if any of the factors are associated with the sample condition:

We can see that the first factor is associated with the sample condition, let’s plot the factor scores:

Now that we have identified a factor that is associated with the sample condition, we can check the ligand-receptor loadings with the highest loadings:

Here, we can see that certain interactions from Factor 1 have high positive loadings. These are interactions that are associated with the samples with high factor scores (i.e. the stimulated samples with high scores in Factor 1).

Finally, we can also explore the MOFA model itself and we will specifically check the variance explained by each pair of cell types.

Here, we can see that views that include CD14+ Monocytes have the highest variance explained both as source and as target of intercellular communication events. In particular, we see that putative autocrine interactions that occur between CD14+ Monocytes are highly explained by Factor 1.

Let’s also perform an enrichment analysis on the ligand-receptor interactions that are associated with the factor of interest. We will use decoupler with pathway genesets from PROGENy to look for enrichments across the cell type pairs (views).

This tutorial is just a short introduction of the use of MOFA, we thus refer the users to the available MOFA & muon tutorials for more applications & details.

Similary, consider citing both muon & MOFA+ if you use them in your work!

MOFAcellular - Multicellular Factor Analysis

By Daniel Dimitrov, Philipp Sven Lars Schäfer, Elias Farr, Pablo Rodriguez-Mier, Sebastian Lobentanzer, Pau Badia-i-Mompel, Aurelien Dugourd, Jovan Tanevski, Ricardo Omar Ramirez Flores, Julio Saez-Rodriguez

© Copyright 2025, Daniel Dimitrov, Philipp Sven Lars Schäfer, Elias Farr, Pablo Rodriguez-Mier, Sebastian Lobentanzer, Pau Badia-i-Mompel, Aurelien Dugourd, Jovan Tanevski, Ricardo Omar Ramirez Flores, Julio Saez-Rodriguez..

**Examples:**

Example 1 (unknown):
```unknown
pip install "decoupler>=2.0.0"
pip install mofax
pip install muon
pip install omnipath
pip install marsilea
```

Example 2 (python):
```python
import numpy as np
import pandas as pd

import scanpy as sc

import plotnine as p9

import liana as li

# load muon and mofax
import muon as mu
import mofax as mofa

import decoupler as dc
```

Example 3 (python):
```python
adata = li.testing.datasets.kang_2018()
```

Example 4 (unknown):
```unknown
AnnData object with n_obs × n_vars = 24673 × 15706
    obs: 'nCount_RNA', 'nFeature_RNA', 'tsne1', 'tsne2', 'condition', 'cluster', 'cell_type', 'patient', 'nCount_SCT', 'nFeature_SCT', 'integrated_snn_res.0.4', 'seurat_clusters', 'sample', 'cell_abbr'
    var: 'name'
    obsm: 'X_pca', 'X_umap'
    layers: 'counts'
```

Example 5 (unknown):
```unknown
sample_key = 'sample'
condition_key = 'condition'
groupby = 'cell_abbr'
```

Example 6 (python):
```python
# filter cells and genes
sc.pp.filter_cells(adata, min_genes=200)
sc.pp.filter_genes(adata, min_cells=3)
# log1p normalize the data
sc.pp.normalize_total(adata)
sc.pp.log1p(adata)
```

Example 7 (python):
```python
# Show pre-computed UMAP
sc.pl.umap(adata, color=[condition_key, sample_key, 'cell_type', groupby], frameon=False, ncols=2)
```

Example 8 (unknown):
```unknown
pandas.DataFrame
```

Example 9 (unknown):
```unknown
rank_aggregate
```

Example 10 (python):
```python
li.mt.rank_aggregate.by_sample(
    adata,
    groupby=groupby,
    resource_name='consensus', # NOTE: uses HUMAN gene symbols!
    sample_key=sample_key, # sample key by which we which to loop
    expr_prop = 0.1,
    use_raw=False, 
    n_perms=100, # reduce permutations for speed
    return_all_lrs=False, # we don't return all LR values to utilize MOFA's flexible views
    verbose=True, # use 'full' to show all information
    )
```

Example 11 (python):
```python
adata.uns["liana_res"].sort_values("magnitude_rank").head()
```

Example 12 (python):
```python
adata.uns["liana_res"]['source'].unique()
```

Example 13 (unknown):
```unknown
array(['FGR3', 'CD14', 'NK', 'CD8T', 'B', 'DCs', 'CD4T'], dtype=object)
```

Example 14 (unknown):
```unknown
magnitude_rank
```

Example 15 (python):
```python
(li.pl.dotplot_by_sample(adata, sample_key=sample_key,
                         colour="magnitude_rank",
                         size="specificity_rank",
                         source_labels=["CD4T", "B", "FGR3"],
                         target_labels=["CD8T", 'DCs', 'CD14'],
                         ligand_complex=["B2M"],
                         inverse_colour=True,
                         inverse_size=True,
                         receptor_complex=["KLRD1", "LILRB2", "CD3D"],
                         figure_size=(12, 8),
                         size_range=(0.5, 5),
                         ) +
    # rotate facet labels
    p9.theme(strip_text=p9.element_text(size=10, colour="black", angle=90))
 )
```

Example 16 (unknown):
```unknown
lrs_to_views
```

Example 17 (python):
```python
adata.uns['liana_res']
```

Example 18 (python):
```python
adata.write_h5ad("../../test.h5ad")
```

Example 19 (python):
```python
mdata = li.multi.lrs_to_views(adata,
                              sample_key=sample_key,
                              score_key='magnitude_rank',
                              obs_keys=['patient', 'condition'], # add those to mdata.obs
                              lr_prop = 0.3, # minimum required proportion of samples to keep an LR
                              lrs_per_sample = 20, # minimum number of interactions to keep a sample in a specific view
                              lrs_per_view = 20, # minimum number of interactions to keep a view
                              samples_per_view = 5, # NOTE: minimum number of samples to keep a view
                              min_variance = 0, # minimum variance to keep an interaction
                              lr_fill = 0, # fill missing LR values across samples with this
                              verbose=True
                              )
```

Example 20 (unknown):
```unknown
return_all_lrs=False
```

Example 21 (unknown):
```unknown
MuData object with n_obs × n_vars = 16 × 1755
  obs:	'patient', 'condition'
  36 modalities
    FGR3&CD14:	16 x 75
    FGR3&DCs:	16 x 87
    CD14&CD14:	16 x 81
    FGR3&NK:	16 x 39
    DCs&NK:	16 x 43
    FGR3&FGR3:	16 x 79
    DCs&CD14:	16 x 79
    CD14&NK:	16 x 41
    NK&CD8T:	14 x 33
    CD14&DCs:	16 x 86
    FGR3&CD8T:	16 x 46
    CD8T&CD8T:	12 x 29
    DCs&DCs:	16 x 89
    CD14&FGR3:	16 x 79
    DCs&FGR3:	16 x 82
    B&CD8T:	14 x 36
    DCs&CD8T:	16 x 51
    CD4T&CD8T:	11 x 27
    CD14&CD8T:	16 x 50
    FGR3&CD4T:	12 x 33
    DCs&CD4T:	13 x 37
    CD14&CD4T:	11 x 31
    CD8T&CD14:	16 x 33
    NK&CD14:	15 x 45
    B&CD14:	14 x 40
    NK&FGR3:	16 x 43
    CD8T&FGR3:	16 x 35
    CD4T&CD14:	15 x 32
    B&FGR3:	16 x 36
    CD4T&FGR3:	16 x 37
    NK&DCs:	14 x 46
    B&DCs:	12 x 50
    CD4T&DCs:	11 x 35
    CD8T&DCs:	12 x 38
    NK&NK:	7 x 26
    B&NK:	7 x 26
```

Example 22 (unknown):
```unknown
mu.tl.mofa(mdata, 
           use_obs='union',
           convergence_mode='medium',
           outfile='models/mofatalk.h5ad',
           n_factors=4,
           )
```

Example 23 (unknown):
```unknown
#########################################################
        ###           __  __  ____  ______                    ### 
        ###          |  \/  |/ __ \|  ____/\    _             ### 
        ###          | \  / | |  | | |__ /  \ _| |_           ### 
        ###          | |\/| | |  | |  __/ /\ \_   _|          ###
        ###          | |  | | |__| | | / ____ \|_|            ###
        ###          |_|  |_|\____/|_|/_/    \_\              ###
        ###                                                   ### 
        ######################################################### 
       
 
        
Loaded view='FGR3&CD14' group='group1' with N=16 samples and D=75 features...
Loaded view='FGR3&DCs' group='group1' with N=16 samples and D=87 features...
Loaded view='CD14&CD14' group='group1' with N=16 samples and D=81 features...
Loaded view='FGR3&NK' group='group1' with N=16 samples and D=39 features...
Loaded view='DCs&NK' group='group1' with N=16 samples and D=43 features...
Loaded view='FGR3&FGR3' group='group1' with N=16 samples and D=79 features...
Loaded view='DCs&CD14' group='group1' with N=16 samples and D=79 features...
Loaded view='CD14&NK' group='group1' with N=16 samples and D=41 features...
Loaded view='NK&CD8T' group='group1' with N=16 samples and D=33 features...
Loaded view='CD14&DCs' group='group1' with N=16 samples and D=86 features...
Loaded view='FGR3&CD8T' group='group1' with N=16 samples and D=46 features...
Loaded view='CD8T&CD8T' group='group1' with N=16 samples and D=29 features...
Loaded view='DCs&DCs' group='group1' with N=16 samples and D=89 features...
Loaded view='CD14&FGR3' group='group1' with N=16 samples and D=79 features...
Loaded view='DCs&FGR3' group='group1' with N=16 samples and D=82 features...
Loaded view='B&CD8T' group='group1' with N=16 samples and D=36 features...
Loaded view='DCs&CD8T' group='group1' with N=16 samples and D=51 features...
Loaded view='CD4T&CD8T' group='group1' with N=16 samples and D=27 features...
Loaded view='CD14&CD8T' group='group1' with N=16 samples and D=50 features...
Loaded view='FGR3&CD4T' group='group1' with N=16 samples and D=33 features...
Loaded view='DCs&CD4T' group='group1' with N=16 samples and D=37 features...
Loaded view='CD14&CD4T' group='group1' with N=16 samples and D=31 features...
Loaded view='CD8T&CD14' group='group1' with N=16 samples and D=33 features...
Loaded view='NK&CD14' group='group1' with N=16 samples and D=45 features...
Loaded view='B&CD14' group='group1' with N=16 samples and D=40 features...
Loaded view='NK&FGR3' group='group1' with N=16 samples and D=43 features...
Loaded view='CD8T&FGR3' group='group1' with N=16 samples and D=35 features...
Loaded view='CD4T&CD14' group='group1' with N=16 samples and D=32 features...
Loaded view='B&FGR3' group='group1' with N=16 samples and D=36 features...
Loaded view='CD4T&FGR3' group='group1' with N=16 samples and D=37 features...
Loaded view='NK&DCs' group='group1' with N=16 samples and D=46 features...
Loaded view='B&DCs' group='group1' with N=16 samples and D=50 features...
Loaded view='CD4T&DCs' group='group1' with N=16 samples and D=35 features...
Loaded view='CD8T&DCs' group='group1' with N=16 samples and D=38 features...
Loaded view='NK&NK' group='group1' with N=16 samples and D=26 features...
Loaded view='B&NK' group='group1' with N=16 samples and D=26 features...


Model options:
- Automatic Relevance Determination prior on the factors: True
- Automatic Relevance Determination prior on the weights: True
- Spike-and-slab prior on the factors: False
- Spike-and-slab prior on the weights: True
Likelihoods:
- View 0 (FGR3&CD14): gaussian
- View 1 (FGR3&DCs): gaussian
- View 2 (CD14&CD14): gaussian
- View 3 (FGR3&NK): gaussian
- View 4 (DCs&NK): gaussian
- View 5 (FGR3&FGR3): gaussian
- View 6 (DCs&CD14): gaussian
- View 7 (CD14&NK): gaussian
- View 8 (NK&CD8T): gaussian
- View 9 (CD14&DCs): gaussian
- View 10 (FGR3&CD8T): gaussian
- View 11 (CD8T&CD8T): gaussian
- View 12 (DCs&DCs): gaussian
- View 13 (CD14&FGR3): gaussian
- View 14 (DCs&FGR3): gaussian
- View 15 (B&CD8T): gaussian
- View 16 (DCs&CD8T): gaussian
- View 17 (CD4T&CD8T): gaussian
- View 18 (CD14&CD8T): gaussian
- View 19 (FGR3&CD4T): gaussian
- View 20 (DCs&CD4T): gaussian
- View 21 (CD14&CD4T): gaussian
- View 22 (CD8T&CD14): gaussian
- View 23 (NK&CD14): gaussian
- View 24 (B&CD14): gaussian
- View 25 (NK&FGR3): gaussian
- View 26 (CD8T&FGR3): gaussian
- View 27 (CD4T&CD14): gaussian
- View 28 (B&FGR3): gaussian
- View 29 (CD4T&FGR3): gaussian
- View 30 (NK&DCs): gaussian
- View 31 (B&DCs): gaussian
- View 32 (CD4T&DCs): gaussian
- View 33 (CD8T&DCs): gaussian
- View 34 (NK&NK): gaussian
- View 35 (B&NK): gaussian




######################################
## Training the model with seed 1 ##
######################################



Converged!



#######################
## Training finished ##
#######################


Saving model in models/mofatalk.h5ad...
Saved MOFA embeddings in .obsm['X_mofa'] slot and their loadings in .varm['LFs'].
```

Example 24 (python):
```python
# Transfer to AnnData to comply with decoupler and visualise
ad = sc.AnnData(obs = mdata.obs, obsm=mdata.obsm)
```

Example 25 (python):
```python
dc.tl.rankby_obsm(
    ad,
    key='X_mofa',  # Where the PCs are stored
    uns_key='rank_obsm',  # Where the results are stored
)

dc.pl.obsm(
    ad,
    key='rank_obsm',
    names = ['patient', 'condition'], # which sample annotations to plot
    titles=['Principle component scores', 'Adjusted p-values from ANOVA'],
    figsize=(7, 5),
    nvar=10
)
```

Example 26 (unknown):
```unknown
# obtain the factor scores as a dataframe
factor_scores = li.ut.get_factor_scores(mdata, obsm_key='X_mofa', obs_keys=['patient', 'condition'])
factor_scores.head()
```

Example 27 (python):
```python
# we use a paired t-test as the samples are paired
from scipy.stats import ttest_rel
```

Example 28 (python):
```python
# split in control and stimulated
group1 = factor_scores[factor_scores['condition']=='ctrl']
group2 = factor_scores[factor_scores['condition']=='stim']

# get all columns that contain factor & loop
factors = [col for col in factor_scores.columns if 'Factor' in col]
for factor in factors:
    print(ttest_rel(group1[factor], group2[factor]))
```

Example 29 (unknown):
```unknown
TtestResult(statistic=29.57591428204321, pvalue=1.3014806912664829e-08, df=7)
TtestResult(statistic=1.033270007163286, pvalue=0.3358493133463141, df=7)
TtestResult(statistic=-1.0016733598764718, pvalue=0.3498620239382361, df=7)
TtestResult(statistic=-1.087734193220712, pvalue=0.31274022725608597, df=7)
```

Example 30 (unknown):
```unknown
# scatterplot
(p9.ggplot(factor_scores) +
 p9.aes(x='condition', colour='condition', y='Factor1') +
 p9.geom_violin() +
 p9.geom_jitter(size=4, width=0.2) +
 p9.theme_bw(base_size=16) +
 p9.theme(figure_size=(5, 4)) +
 p9.scale_colour_manual(values=['#1f77b4', '#c20019']) +
 p9.labs(x='Condition', y='Factor 1')
 )
```

Example 31 (unknown):
```unknown
variable_loadings =  li.ut.get_variable_loadings(mdata,
                                                 varm_key='LFs',
                                                 view_sep=':',
                                                 pair_sep="&",
                                                 variable_sep="^") # get loadings for factor 1
variable_loadings.head()
```

Example 32 (unknown):
```unknown
# here we will just assign the size of the dots, but this can be replace by any other statistic
variable_loadings['size'] = 4.5
```

Example 33 (unknown):
```unknown
my_plot = li.pl.dotplot(liana_res = variable_loadings,
                        size='size',
                        colour='Factor1', 
                        orderby='Factor1',
                        top_n=15,
                        source_labels=['NK', 'B', 'CD4T', 'CD8T', 'CD14'],
                        orderby_ascending=False,
                        size_range=(0.1, 5),
                        figure_size=(8, 5)
                        )
# change colour, with mid as white
my_plot + p9.scale_color_gradient2(low='#1f77b4', mid='lightgray', high='#c20019')
```

Example 34 (unknown):
```unknown
model = mofa.mofa_model("models/mofatalk.h5ad")
model
```

Example 35 (unknown):
```unknown
MOFA+ model: mofatalk.h5ad
Samples (cells): 16
Features: 1755
Groups: group1 (16)
Views: B&CD14 (40), B&CD8T (36), B&DCs (50), B&FGR3 (36), B&NK (26), CD14&CD14 (81), CD14&CD4T (31), CD14&CD8T (50), CD14&DCs (86), CD14&FGR3 (79), CD14&NK (41), CD4T&CD14 (32), CD4T&CD8T (27), CD4T&DCs (35), CD4T&FGR3 (37), CD8T&CD14 (33), CD8T&CD8T (29), CD8T&DCs (38), CD8T&FGR3 (35), DCs&CD14 (79), DCs&CD4T (37), DCs&CD8T (51), DCs&DCs (89), DCs&FGR3 (82), DCs&NK (43), FGR3&CD14 (75), FGR3&CD4T (33), FGR3&CD8T (46), FGR3&DCs (87), FGR3&FGR3 (79), FGR3&NK (39), NK&CD14 (45), NK&CD8T (33), NK&DCs (46), NK&FGR3 (43), NK&NK (26)
Factors: 4
Expectations: W, Z
```

Example 36 (unknown):
```unknown
# get variance explained by view and factor
rsq = model.get_r2()
factor1_rsq = rsq[rsq['Factor']=='Factor1']
# separate view column
factor1_rsq[['source', 'target']] = factor1_rsq['View'].str.split(pat='&', n=1, expand=True)
```

Example 37 (unknown):
```unknown
(p9.ggplot(factor1_rsq.reset_index()) + 
 p9.aes(x='target', y='source') + 
 p9.geom_tile(p9.aes(fill='R2')) + 
 p9.scale_fill_gradient2(low='white', high='#c20019') +
 p9.theme_bw(base_size=16) +
 p9.theme(figure_size=(5, 4)) +
 p9.labs(x='Target', y='Source', fill='R²')
 )
```

Example 38 (unknown):
```unknown
# load PROGENy pathways
net = dc.op.progeny(organism='human', top=5000, thr_padj=0.25)
# load full list of ligand-receptor pairs
lr_pairs = li.resource.select_resource('consensus')
```

Example 39 (unknown):
```unknown
# generate ligand-receptor geneset
lr_progeny = li.rs.generate_lr_geneset(lr_pairs, net, lr_sep="^").rename(columns = {'interaction': 'target'})
lr_progeny.head()
```

Example 40 (python):
```python
lr_loadings =  li.ut.get_variable_loadings(mdata,
                                           varm_key='LFs',
                                           view_sep=':',
                                           )
lr_loadings.set_index('variable', inplace=True)
# pivot views to wide
lr_loadings = lr_loadings.pivot(columns='view', values='Factor1')
# replace NaN with 0
lr_loadings.replace(np.nan, 0, inplace=True)
lr_loadings.head()
```

Example 41 (unknown):
```unknown
# run pathway enrichment analysis
estimate, pvals =  dc.mt.mlm(lr_loadings.transpose(), lr_progeny, raw=False, tmin=5)
# pivot columns to long
estimate = (estimate.
            melt(ignore_index=False, value_name='estimate', var_name='pathway').
            reset_index().
            rename(columns={'index':'view'})
            )
```

Example 42 (unknown):
```unknown
## p9 tile plot
(p9.ggplot(estimate) + 
 p9.aes(x='pathway', y='view') +
 p9.geom_tile(p9.aes(fill='estimate')) +
 p9.scale_fill_gradient2(low='#1f77b4', high='#c20019') +
 p9.theme_bw(base_size=14) +
 p9.theme(figure_size=(8, 8))
)
```

Example 43 (unknown):
```unknown
model.close()
```

---

## Intercellular Context Factorization with Tensor-Cell2cell — liana

**URL:** http://127.0.0.1:9050/en_latest_notebooks_liana_c2c.html

**Contents:**
- Intercellular Context Factorization with Tensor-Cell2cell
- Contents
- Intercellular Context Factorization with Tensor-Cell2cell#
- Background#
- Load Packages#
- Load & Prep Data#
  - Showcase anndata object#
  - Basic QC#
  - Show pre-computed UMAP#
- Ligand-Receptor Inference by Sample#
- Building a Tensor#
  - Running Tensor-cell2cell#
      - Optimal Rank Estimation
- Factorization Results#
- Downstream Analysis#
- Outlook & Further Analysis#

Tensor decomposition of cell-cell communication patterns, as proposed by Armingol and Baghdassarian et al., 2022, enables us to decipher context-driven intercellular communication by simultaneously accounting for an unlimited number of “contexts”. These contexts could represent samples coming from longtidinal sampling points, multiple conditions, or cellular niches.

The power of Tensor-cell2cell is in its ability to decompose latent patterns of intercellular communication in an untargeted manner, in theory being able to handle cell-cell communication results coming from any experimental design, regardless of its complexity.

Simply put, tensor_cell2cell uses LIANA’s output by sample to build a 4D tensor, represented by 1) contexts, 2) interactions, 3) sender, and 4) receiver cell types. This tensor is then decomposed into a set of factors, which can be interpreted as low-dimensionality latent variables (vectors) that capture the CCC patterns across contexts. We will combine LIANA with tensor_cell2cell to decipher potential ligand-receptor interaction changes.

Extensive tutorials combining LIANA & Tensor-cell2cell are available here.

Install required packages via pip with the following command:

As a simple example, we will look at ~25k PBMCs from 8 pooled patient lupus samples, each before and after IFN-beta stimulation (Kang et al., 2018; GSE96583). Note that by focusing on PBMCs, for the purpose of this tutorial, we assume that coordinated events occur among them.

This dataset is downloaded from a link on Figshare; preprocessed for pertpy.

Note that this data has been largely pre-processed & annotated, we refer the user to the Quality Control and other relevant chapters from the best-practices book for information about pre-processing and annotation steps.

In addition to the basic QC steps, one needs to ensure that the cell groups on which they run the analysis are well defined, and stable across samples.

Before we decompose the CCC patterns across contexts/samples with tensor_cell2cell, we need to run liana on each sample. This is because tensor_cell2cell uses LIANA’s output by sample to build a 4D tensor, that is later decomposed into CCC patterns. To do so, liana provides a utility function called by_sample that runs each method in LIANA on each sample within the AnnData object, and returns a long-format pandas.DataFrame with the results.

In this example, we will use liana’s rank_aggregate method, which provides a robust rank consensus that combines the predictions of multiple ligand-receptor methods. Nevertheless, any other method can be used.

Even on a small subset interactions and cell types, the interpretation becomes challenging. To overcome this, we can use Tensor-cell2cell to find the variable CCC patterns across contexts/samples.

Before we can decompose the tensor, we need to build it. To do so, we will use the to_tensor_c2c function from liana. This function takes as input the pandas.DataFrame with the results from liana.by_sample, and returns a cell2cell.tensor.PrebuiltTensor object. This object contains the tensor, as well as other useful utility functions.

Note that the way that we build the tensor can impact the results that we obtain. This is largely controlled by the how, lr_fill, and cell_fill parameters, but these are out of the scope of this tutorial. For more information, please refer to the tensor_cell2cell documentation, as well as the c2c.tensor.external_scores.dataframes_to_tensor function.

We can check the shape of the tensor, represented as (Contexts, Interactions, Senders, Receivers).

One can save the tensor to disk, by using the c2c.io.export_variable_with_pickle function

Let’s now run the Tensor decomposition pipeline of Tensor-cell2cell. This function includes optimal rank estimation, as well as PARAFAC decomposition of the tensor. For more information, please refer to the Tensor-cell2cell manuscript.

Here, we have omitted the optimal rank estimation step, as the optimal rank was precomputed. This can be a computationally intensive process, and we recommend using a GPU for this step.

If your machine does not have a GPU, you could use Google Colab to estimate the optimal rank. This is done automatically by setting the rank parameter to None.

Plot Tensor Decomposition results

To get a more detailed look we can access the factors and loadings of the decomposition. As expected, for each factor we get four vectors, one for each dimension of the tensor. We can access those as follows:

Here, we see clearly that Factor 6 is associated with the IFN-beta stimulation, further supported by significance testing:

The cell types associated with Factors of interest, in this case Factor 6 are CD14+ Monocytes, FCGR3A+ Monocytes, and Dendritic cells:

We can also check the loadings of each factor, which are the weights assigned to each interaction, sender, and receiver cell type. So, let’s check the ligand-receptor interactions with the highest loadings in Factor 6.

Though anecdotal, in this example we can see that within the interactions with the highest loadings in the stimulation-associated factor is CCL8->CCR1 - previously associated with IFN-beta stimulation.

Let’s also perform a basic enrichment analysis on the results above. We will use decoupler with pathway genesets from PROGENy.

Check Enrichment results for Factor 5

We can see that the most enriched PROGENy pathway in Factor 6 is the JAK-STAT signaling pathway, which is consistent with what we would expect.

There are different ways to explore these results downstream of the tensor decomposition, but these are out of scope for this tutorial.

Stay tuned for more in-depth tutorials with Tensor-cell2cell and liana! In the meantime, we refer the user to the extensive Tensor-cell2cell x LIANA tutorials

Differential Expression Analysis for CCC & Downstream Signalling Networks

MOFAcellular - Multicellular Factor Analysis

By Daniel Dimitrov, Philipp Sven Lars Schäfer, Elias Farr, Pablo Rodriguez-Mier, Sebastian Lobentanzer, Pau Badia-i-Mompel, Aurelien Dugourd, Jovan Tanevski, Ricardo Omar Ramirez Flores, Julio Saez-Rodriguez

© Copyright 2025, Daniel Dimitrov, Philipp Sven Lars Schäfer, Elias Farr, Pablo Rodriguez-Mier, Sebastian Lobentanzer, Pau Badia-i-Mompel, Aurelien Dugourd, Jovan Tanevski, Ricardo Omar Ramirez Flores, Julio Saez-Rodriguez..

**Examples:**

Example 1 (python):
```python
pip install liana cell2cell decoupler omnipath seaborn==0.11
```

Example 2 (python):
```python
import pandas as pd
import scanpy as sc
import plotnine as p9

import liana as li
import cell2cell as c2c
import decoupler as dc # needed for pathway enrichment

import warnings
warnings.filterwarnings('ignore')
from collections import defaultdict

%matplotlib inline
```

Example 3 (python):
```python
# NOTE: to use CPU instead of GPU, set use_gpu = False
use_gpu = True

if use_gpu:
    import torch
    import tensorly as tl

    device = "cuda" if torch.cuda.is_available() else "cpu"
    if device == "cuda":
        tl.set_backend('pytorch')
else:
    device = "cpu"

device
```

Example 4 (python):
```python
# load data as from CCC chapter
adata = li.testing.datasets.kang_2018()
```

Example 5 (unknown):
```unknown
AnnData object with n_obs × n_vars = 24673 × 15706
    obs: 'nCount_RNA', 'nFeature_RNA', 'tsne1', 'tsne2', 'condition', 'cluster', 'cell_type', 'patient', 'nCount_SCT', 'nFeature_SCT', 'integrated_snn_res.0.4', 'seurat_clusters', 'sample', 'cell_abbr'
    var: 'name'
    obsm: 'X_pca', 'X_umap'
    layers: 'counts'
```

Example 6 (python):
```python
adata.obs.head()
```

Example 7 (python):
```python
adata.obs["cell_type"].cat.categories
```

Example 8 (unknown):
```unknown
Index(['CD4 T cells', 'CD14+ Monocytes', 'B cells', 'NK cells', 'CD8 T cells',
       'FCGR3A+ Monocytes', 'Dendritic cells', 'Megakaryocytes'],
      dtype='object')
```

Example 9 (unknown):
```unknown
sample_key = 'sample'
condition_key = 'condition'
groupby = 'cell_type'
```

Example 10 (python):
```python
# filter cells and genes
sc.pp.filter_cells(adata, min_genes=200)
sc.pp.filter_genes(adata, min_cells=3)
# log1p normalize the data
sc.pp.normalize_total(adata)
sc.pp.log1p(adata)
```

Example 11 (python):
```python
sc.pl.umap(adata, color=[condition_key, groupby], frameon=False)
```

Example 12 (unknown):
```unknown
tensor_cell2cell
```

Example 13 (unknown):
```unknown
tensor_cell2cell
```

Example 14 (unknown):
```unknown
pandas.DataFrame
```

Example 15 (python):
```python
li.mt.rank_aggregate.by_sample(
    adata,
    groupby=groupby,
    resource_name='consensus', # NOTE: uses human gene symbols!
    sample_key=sample_key, # sample key by which we which to loop
    use_raw=False, 
    verbose=True, # use 'full' to show all verbose information
    n_perms=None, # exclude permutations for speed
    return_all_lrs=True, # return all LR values
    )
```

Example 16 (python):
```python
adata.uns["liana_res"].sort_values("magnitude_rank").head(10)
```

Example 17 (unknown):
```unknown
to_tensor_c2c
```

Example 18 (unknown):
```unknown
pandas.DataFrame
```

Example 19 (unknown):
```unknown
liana.by_sample
```

Example 20 (unknown):
```unknown
cell2cell.tensor.PrebuiltTensor
```

Example 21 (unknown):
```unknown
c2c.tensor.external_scores.dataframes_to_tensor
```

Example 22 (python):
```python
tensor = li.multi.to_tensor_c2c(adata,
                                sample_key=sample_key,
                                score_key='magnitude_rank', # can be any score from liana
                                how='outer_cells' # how to join the samples
                                )
```

Example 23 (python):
```python
tensor.tensor.shape
```

Example 24 (unknown):
```unknown
torch.Size([16, 418, 7, 7])
```

Example 25 (unknown):
```unknown
c2c.io.export_variable_with_pickle
```

Example 26 (unknown):
```unknown
c2c.io.export_variable_with_pickle(tensor, "tensor_tutorial.pkl")
```

Example 27 (unknown):
```unknown
tensor_tutorial.pkl  was correctly saved.
```

Example 28 (python):
```python
context_dict = adata.obs[[sample_key, condition_key]].drop_duplicates()
context_dict = dict(zip(context_dict[sample_key], context_dict[condition_key]))
context_dict = defaultdict(lambda: 'Unknown', context_dict)

tensor_meta = c2c.tensor.generate_tensor_metadata(interaction_tensor=tensor,
                                                  metadata_dicts=[context_dict, None, None, None],
                                                  fill_with_order_elements=True
                                                  )
```

Example 29 (python):
```python
tensor = c2c.analysis.run_tensor_cell2cell_pipeline(tensor,
                                                    tensor_meta,
                                                    copy_tensor=True, # Whether to output a new tensor or modifying the original
                                                    rank=6, # Number of factors to perform the factorization. If None, it is automatically determined by an elbow analysis. Here, it was precomuputed.
                                                    tf_optimization='regular', # To define how robust we want the analysis to be. 
                                                    random_state=0, # Random seed for reproducibility
                                                    device=device, # Device to use. If using GPU and PyTorch, use 'cuda'. For CPU use 'cpu'
                                                    elbow_metric='error', # Metric to use in the elbow analysis.
                                                    smooth_elbow=False, # Whether smoothing the metric of the elbow analysis.
                                                    upper_rank=20, # Max number of factors to try in the elbow analysis
                                                    tf_init='random', # Initialization method of the tensor factorization
                                                    tf_svd='numpy_svd', # Type of SVD to use if the initialization is 'svd'
                                                    cmaps=None, # Color palettes to use in color each of the dimensions. Must be a list of palettes.
                                                    sample_col='Element', # Columns containing the elements in the tensor metadata
                                                    group_col='Category', # Columns containing the major groups in the tensor metadata
                                                    output_fig=False, # Whether to output the figures. If False, figures won't be saved a files if a folder was passed in output_folder.
                                                    )
```

Example 30 (unknown):
```unknown
Running Tensor Factorization
```

Example 31 (python):
```python
factors, axes = c2c.plotting.tensor_factors_plot(interaction_tensor=tensor,
                                                 metadata = tensor_meta, # This is the metadata for each dimension
                                                 sample_col='Element',
                                                 group_col='Category',
                                                 meta_cmaps = ['viridis', 'Dark2_r', 'tab20', 'tab20'],
                                                 fontsize=10, # Font size of the figures generated
                                                 )
```

Example 32 (unknown):
```unknown
factors = tensor.factors
```

Example 33 (unknown):
```unknown
factors.keys()
```

Example 34 (unknown):
```unknown
odict_keys(['Contexts', 'Ligand-Receptor Pairs', 'Sender Cells', 'Receiver Cells'])
```

Example 35 (unknown):
```unknown
_ = c2c.plotting.context_boxplot(context_loadings=factors['Contexts'],
                                 metadict=context_dict,
                                 nrows=2,
                                 figsize=(8, 6),
                                 statistical_test='t-test_ind',
                                 pval_correction='fdr_bh',
                                 cmap='plasma',
                                 verbose=False,
                                )
```

Example 36 (unknown):
```unknown
c2c.plotting.ccc_networks_plot(factors,
                               included_factors=['Factor 6'],
                               network_layout='circular',
                               ccc_threshold=0.05, # Only important communication
                               nrows=1,
                               panel_size=(8, 8), # This changes the size of each figure panel.
                              )
```

Example 37 (unknown):
```unknown
(<Figure size 800x800 with 1 Axes>, <Axes: title={'center': 'Factor 6'}>)
```

Example 38 (unknown):
```unknown
lr_loadings = factors['Ligand-Receptor Pairs']
lr_loadings.sort_values("Factor 6", ascending=False).head(10)
```

Example 39 (unknown):
```unknown
# load PROGENy pathways
net = dc.op.progeny(organism='human', top=5000)
```

Example 40 (unknown):
```unknown
# load full list of ligand-receptor pairs
lr_pairs = li.resource.select_resource('consensus')
```

Example 41 (unknown):
```unknown
# generate ligand-receptor geneset
lr_progeny = li.rs.generate_lr_geneset(lr_pairs, net, lr_sep="^").rename(columns = {"interaction": "target"})
lr_progeny.head()
```

Example 42 (unknown):
```unknown
# run enrichment analysis
estimate, pvals = dc.mt.ulm(lr_loadings.transpose(), lr_progeny, raw=False)
```

Example 43 (unknown):
```unknown
dc.pl.barplot(estimate, 'Factor 6', vertical=True, cmap='coolwarm', vmin=-7, vmax=7)
```

Example 44 (unknown):
```unknown
Tensor-cell2cell
```

---

## Integrating Multi-Modal Spatially-Resolved Technologies with LIANA+ — liana

**URL:** http://127.0.0.1:9050/en_latest_notebooks_sma.html

**Contents:**
- Integrating Multi-Modal Spatially-Resolved Technologies with LIANA+
- Contents
- Integrating Multi-Modal Spatially-Resolved Technologies with LIANA+#
- Obtain and Examine the Data#
- Experimental Design#
- Multi-view Modelling Metabolite Intensities#
  - Remove features with little-to-no variation#
  - Additional processing steps#
  - Compute Spatial Proximies for the Multi-view Model#
  - Construct and Run the Multi-view model#
- Identifying Local Interactions#

Here, we apply of LIANA+ on a spatially-resolved metabolite-transcriptome dataset from a recent murine Parkinson’s disease model Vicari et al., 2023. We demonstrate LIANA+’s utility in harmonizing spatially-resolved transcriptomics and MALDI-MSI data to unravel metabolite-mediated interactions and the molecular mechanisms of dopamine regulation in the striatum.

Two particular challenges with this data are:

The unaligned spatial locations of the two omics technologies

The untargeted nature of the MALDI-MSI data, which results in a large number of features with unknown identities. Only few of which were previously identified as specific metabolites.

Here, we show untargeted modelling of known and unknown metabolite peaks and their spatial relationships with transcriptomics data. Specifically, we use a multi-view modelling strategy MISTy to decipher global spatial relationships of metabolite peaks with cell types and brain-specific receptors. Then, we use LIANA+’s local metrics to pinpoint the subregions of interaction.

We also show strategies to enable spatial multi-omics analysis from diverse omics technologies with unaligned locations and observations.

First, we obtain the a single slide from the dataset. This slide has already been preprocessed, including filtering and normalisation. We have log1p transformed the RNA-seq data and total-ion count normalised the MALDI-MSI data.

We have also pre-aligned the images from the two technologies, though the observations are not aligned - an issue that we will address in this notebook. For image and coordinate transformations, we refer the users to SpatialData or stAlign.

We have additionally deconvoluted the cell types in the RNA-seq data using Tangram.

So, in total we have three modalities: the MALDI-MSI data, the RNA-seq data, and the cell type data:

If you look closely here, you will notice that the metabolite locations are not aligned in a grid-like manner as the 10X Visium Data. We will address this in the next steps.

Of note, mice in this data were subjected to unilateral 6-hydroxydopamine-induced lesions in one hemisphere while the other remained intact. These 6-Hydroxydopamine-induced lesions selectively destroy substantia nigra-originated dopaminergic neurons, thereby impairing dopamine-mediated regulatory mechanisms of the striatum - an area of the brain crucial for movement coordination.

Along with annotations of the lesioned and intact hemispheres, we also have annotations for the striatum:

Next, we will model the metabolite intensities jointly using cell types and brain specific receptors as predictors.

Done to avoid fitting noisy readouts in our model. Ideally, one could instead use e.g. Moran’s I to identify spatially-variable features.

Note that we use simple coefficient of variation and highly-variable gene functions, but one may easily replace this step with e.g. the spatially-informed Moran’s I from Squidpy.

Scale the intensities and cap the max value

Obtain brain-specific metabolite-receptor interactions from MetalinksDB.

Convert to murine symbols using orthology knowledge from HCOP. If you use this function, please reference the original database.

Translate the Receptors to Murine symbols

Intersect the RNA modality with the receptors

We use the metabolite modality as reference to which we align the other modalities. We use the spatial_neighbors function to compute the spatial proximity from cell types and brain-specific receptors to the metabolite intensities.

We then pick 1,000 as it’s roughly equivalent to the 6 nearest neighbors from a hexagonal grid.

Compute distances for each extra modality

Specifically, we use the metabolite intensities as the intraview - i.e. targets of prediction. While the cell types and brain-specific receptors are the extraview - i.e. spatially-weighted predictors.

By using the metabolite modality as a reference, we can now predict the metabolite intensities from the spatially-weighted cell types and brain-specific receptors.

Specifically, we do so, by modelling the lesioned and intact hemispheres separately - enabled via the maskby parameter. This masking procedure, simply masks the observations according to the lesion annotations, following spatially-weighting the extra views.

We can see that in the intact hemisphere there are several metabolites peaks which are relatively well predicted (R2 > 0.5), and among them are Dopamine and 3-Methoxytyramine (3-MT). Of note, while we don’t focus on the unannotated metabolite peaks, we can see that some of them are also well predicted. This is a good indication of which metabolite peaks might be of interest for further investigation, and subsequently, identification.

On the other hand, we don’t see those peaks in the lesioned hemisphere, which is consistent with the 6-Hydroxydopamine-induced lesions, and the absence of Dopamine in this hemisphere.

Within the intact hemisphere we can see that in the top predictors of Dopamine are MSN1/2 as well as Drd1/2 receptors. MSN1/2 are Medium Spiny Neurons, which are the main cell type in the striatum, and Drd1/2 are Dopamine receptors. This is consistent with the known biology of the striatum, where Dopamine is a key neurotransmitter, and the Drd1/2 receptors are the main receptors for Dopamine in the striatum.

Focusing on Dopamine, we can next use LIANA+’s local metrics to identify the subregions of interactions with MSN1/2 cells.

While the transformation of spatial locations is done internally by MISTy, we need to transform the metabolite intensities to a grid-like manner, so that we can use the local metrics. To do so, we use the interpolate_adata function, which interpolates one modality to another. Here, we will interpolate the metabolite intensities to the RNA-seq data, so that we can use the spatial locations of the RNA-seq data to identify the local interactions.

Notice that the Metabolite observations now resemble the grid-like structure of Visium data:

Let’s rebuild a MuData object with these updated metabolite intensities

and now we can again calculate the spatial proximities, but this time without a reference as all observations within the MuData have the same spatial locations.

Define interactions of interest:

Let’s calculate the local metrics for the Dopamine intensities with and Drd1/2 receptors.

Here, we will plot the permutation-based local P-values

We see that interactions with Dopamine as largely anticipated are predominantly located within the Striatum of the intact hemisphere, and are typically absent in the lesioned hemisphere.

Spatially-informed Bivariate Metrics

Learning Spatial Relationships with MISTy

By Daniel Dimitrov, Philipp Sven Lars Schäfer, Elias Farr, Pablo Rodriguez-Mier, Sebastian Lobentanzer, Pau Badia-i-Mompel, Aurelien Dugourd, Jovan Tanevski, Ricardo Omar Ramirez Flores, Julio Saez-Rodriguez

© Copyright 2025, Daniel Dimitrov, Philipp Sven Lars Schäfer, Elias Farr, Pablo Rodriguez-Mier, Sebastian Lobentanzer, Pau Badia-i-Mompel, Aurelien Dugourd, Jovan Tanevski, Ricardo Omar Ramirez Flores, Julio Saez-Rodriguez..

**Examples:**

Example 1 (python):
```python
import numpy as np
import liana as li
import mudata as mu
import scanpy as sc

from matplotlib import pyplot as plt
from adjustText import adjust_text
```

Example 2 (unknown):
```unknown
# set global figure parameters
kwargs = {'frameon':False, 'size':1.5, 'img_key':'lowres'}
```

Example 3 (python):
```python
# let's download the data
rna = sc.read("sma_rna.h5ad", backup_url="https://figshare.com/ndownloader/files/44624974?private_link=4744950f8768d5c8f68c")
msi = sc.read("sma_msi.h5ad", backup_url="https://figshare.com/ndownloader/files/44624971?private_link=4744950f8768d5c8f68c")
ct = sc.read("sma_ct.h5ad", backup_url="https://figshare.com/ndownloader/files/44624968?private_link=4744950f8768d5c8f68c")
```

Example 4 (unknown):
```unknown
# and create a MuData object
mdata = mu.MuData({'rna':rna, 'msi':msi, 'ct':ct})
mdata
```

Example 5 (unknown):
```unknown
MuData object with n_obs × n_vars = 6041 × 17782
  3 modalities
    rna:	3036 x 16486
      obs:	'in_tissue', 'array_row', 'array_col', 'x', 'y', 'lesion', 'region', 'n_genes_by_counts', 'log1p_n_genes_by_counts', 'total_counts', 'log1p_total_counts', 'pct_counts_in_top_50_genes', 'pct_counts_in_top_100_genes', 'pct_counts_in_top_200_genes', 'pct_counts_in_top_500_genes', 'total_counts_mt', 'log1p_total_counts_mt', 'pct_counts_mt', 'n_genes', 'n_counts'
      var:	'gene_ids', 'feature_types', 'genome', 'mt', 'n_cells_by_counts', 'mean_counts', 'log1p_mean_counts', 'pct_dropout_by_counts', 'total_counts', 'log1p_total_counts', 'n_cells'
      uns:	'lesion_colors', 'log1p', 'region_colors', 'spatial'
      obsm:	'spatial'
      layers:	'counts'
    msi:	3005 x 1248
      obs:	'x', 'y', 'array_row', 'array_col', 'leiden', 'n_counts', 'index_right', 'region', 'lesion'
      var:	'mean', 'std', 'mz', 'max_intensity', 'mz_raw', 'annotated'
      uns:	'leiden', 'leiden_colors', 'log1p', 'neighbors', 'pca', 'spatial'
      obsm:	'X_pca', 'spatial'
      varm:	'PCs'
      layers:	'raw'
      obsp:	'connectivities', 'distances'
    ct:	3036 x 48
      obs:	'in_tissue', 'array_row', 'array_col', 'x', 'y', 'lesion', 'region', 'n_genes_by_counts', 'log1p_n_genes_by_counts', 'total_counts', 'log1p_total_counts', 'pct_counts_in_top_50_genes', 'pct_counts_in_top_100_genes', 'pct_counts_in_top_200_genes', 'pct_counts_in_top_500_genes', 'total_counts_mt', 'log1p_total_counts_mt', 'pct_counts_mt', 'n_genes', 'n_counts', 'uniform_density', 'rna_count_based_density'
      uns:	'lesion_colors', 'log1p', 'overlap_genes', 'region_colors', 'spatial', 'training_genes'
      obsm:	'spatial', 'tangram_ct_pred'
```

Example 6 (python):
```python
fig, axes = plt.subplots(1, 3, figsize=(12, 3))

sc.pl.spatial(rna, color='log1p_total_counts', ax=axes[0], **kwargs, show=False)
sc.pl.spatial(msi, color='Dopamine', cmap='magma', ax=axes[1], **kwargs, show=False)
sc.pl.spatial(ct, color='MSN1', cmap='viridis', ax=axes[2], **kwargs, show=False)

fig.subplots_adjust(wspace=0, hspace=0)
fig.tight_layout()
```

Example 7 (python):
```python
sc.pl.spatial(rna, color=['lesion', 'region'], **kwargs, wspace=0.25)
```

Example 8 (python):
```python
sc.pp.highly_variable_genes(rna, flavor='cell_ranger', n_top_genes=5000)
sc.pp.highly_variable_genes(msi, flavor='cell_ranger', n_top_genes=150)
ct.var['cv'] = ct.X.toarray().var(axis=0) / ct.X.toarray().mean(axis=0)
ct.var['highly_variable'] = ct.var['cv'] > np.percentile(ct.var['cv'], 20)
```

Example 9 (unknown):
```unknown
msi = msi[:, msi.var['highly_variable']]
rna = rna[:, rna.var['highly_variable']]
ct = ct[:, ct.var['highly_variable']]
```

Example 10 (python):
```python
sc.pp.scale(msi, max_value=5)
```

Example 11 (unknown):
```unknown
metalinks = li.rs.get_metalinks(tissue_location='Brain',
                                biospecimen_location='Cerebrospinal Fluid (CSF)',
                                source=['CellPhoneDB', 'NeuronChat']
                                )
metalinks.head()
```

Example 12 (unknown):
```unknown
map_df = li.rs.get_hcop_orthologs(columns=['human_symbol', 'mouse_symbol'],
                                  min_evidence=3
                                  ).rename(columns={'human_symbol':'source',
                                                   'mouse_symbol':'target'})
```

Example 13 (unknown):
```unknown
metalinks = li.rs.translate_column(resource=metalinks,
                                   map_df=map_df,
                                   column='gene_symbol',
                                   one_to_many=1)
metalinks.head()
```

Example 14 (python):
```python
receptors = np.intersect1d(metalinks['gene_symbol'].unique(), rna.var_names)
rec = rna[:, receptors].copy()
```

Example 15 (unknown):
```unknown
spatial_neighbors
```

Example 16 (unknown):
```unknown
plot, _ = li.ut.query_bandwidth(coordinates=rna.obsm['spatial'], start=0, end=1500)
plot
```

Example 17 (unknown):
```unknown
bandwidth = 500
cutoff = 0.1
# distances of metabolties to RNA
reference = mdata.mod["msi"].obsm["spatial"]
```

Example 18 (unknown):
```unknown
li.ut.spatial_neighbors(ct, bandwidth=bandwidth, cutoff=cutoff, spatial_key="spatial", reference=reference, set_diag=False, standardize=False)
li.ut.spatial_neighbors(rec, bandwidth=bandwidth, cutoff=cutoff, spatial_key="spatial", reference=reference, set_diag=False, standardize=False)
```

Example 19 (unknown):
```unknown
# MISTy
mdata.update_obs()
misty = li.mt.MistyData({"intra": msi, "receptor": rec, "ct": ct}, enforce_obs=False, obs=mdata.obs)
misty
```

Example 20 (unknown):
```unknown
MuData object with n_obs × n_vars = 6041 × 207
  obs:	'rna:in_tissue', 'rna:array_row', 'rna:array_col', 'rna:x', 'rna:y', 'rna:lesion', 'rna:region', 'rna:n_genes_by_counts', 'rna:log1p_n_genes_by_counts', 'rna:total_counts', 'rna:log1p_total_counts', 'rna:pct_counts_in_top_50_genes', 'rna:pct_counts_in_top_100_genes', 'rna:pct_counts_in_top_200_genes', 'rna:pct_counts_in_top_500_genes', 'rna:total_counts_mt', 'rna:log1p_total_counts_mt', 'rna:pct_counts_mt', 'rna:n_genes', 'rna:n_counts', 'msi:x', 'msi:y', 'msi:array_row', 'msi:array_col', 'msi:leiden', 'msi:n_counts', 'msi:index_right', 'msi:region', 'msi:lesion'
  var:	'highly_variable'
  3 modalities
    intra:	3005 x 150
      obs:	'x', 'y', 'array_row', 'array_col', 'leiden', 'n_counts', 'index_right', 'region', 'lesion'
      var:	'mean', 'std', 'mz', 'max_intensity', 'mz_raw', 'annotated', 'highly_variable', 'means', 'dispersions', 'dispersions_norm'
      uns:	'leiden', 'leiden_colors', 'log1p', 'neighbors', 'pca', 'spatial', 'hvg'
      obsm:	'X_pca', 'spatial'
      varm:	'PCs'
      layers:	'raw'
      obsp:	'connectivities', 'distances'
    receptor:	3036 x 19
      obs:	'in_tissue', 'array_row', 'array_col', 'x', 'y', 'lesion', 'region', 'n_genes_by_counts', 'log1p_n_genes_by_counts', 'total_counts', 'log1p_total_counts', 'pct_counts_in_top_50_genes', 'pct_counts_in_top_100_genes', 'pct_counts_in_top_200_genes', 'pct_counts_in_top_500_genes', 'total_counts_mt', 'log1p_total_counts_mt', 'pct_counts_mt', 'n_genes', 'n_counts'
      var:	'gene_ids', 'feature_types', 'genome', 'mt', 'n_cells_by_counts', 'mean_counts', 'log1p_mean_counts', 'pct_dropout_by_counts', 'total_counts', 'log1p_total_counts', 'n_cells', 'highly_variable', 'means', 'dispersions', 'dispersions_norm'
      uns:	'lesion_colors', 'log1p', 'region_colors', 'spatial', 'hvg'
      obsm:	'spatial', 'spatial_connectivities'
      varm:	'weighted'
      layers:	'counts'
    ct:	3036 x 38
      obs:	'in_tissue', 'array_row', 'array_col', 'x', 'y', 'lesion', 'region', 'n_genes_by_counts', 'log1p_n_genes_by_counts', 'total_counts', 'log1p_total_counts', 'pct_counts_in_top_50_genes', 'pct_counts_in_top_100_genes', 'pct_counts_in_top_200_genes', 'pct_counts_in_top_500_genes', 'total_counts_mt', 'log1p_total_counts_mt', 'pct_counts_mt', 'n_genes', 'n_counts', 'uniform_density', 'rna_count_based_density'
      var:	'cv', 'highly_variable'
      uns:	'lesion_colors', 'log1p', 'overlap_genes', 'region_colors', 'spatial', 'training_genes'
      obsm:	'spatial', 'tangram_ct_pred', 'spatial_connectivities'
      varm:	'weighted'
```

Example 21 (unknown):
```unknown
misty(model=li.mt.sp.LinearModel, verbose=True, bypass_intra=True, maskby='lesion')
```

Example 22 (unknown):
```unknown
li.pl.target_metrics(misty, stat='multi_R2', return_fig=True, top_n=20, filter_fun=lambda x: x['intra_group']=='intact')
```

Example 23 (unknown):
```unknown
li.pl.target_metrics(misty, stat='multi_R2', return_fig=True, top_n=20, filter_fun=lambda x: x['intra_group']=='lesioned')
```

Example 24 (unknown):
```unknown
interactions = misty.uns['interactions']
```

Example 25 (python):
```python
interactions = interactions[(interactions['intra_group'] == 'intact') & (interactions['target'] == 'Dopamine')]
# Create scatter plot
plt.figure(figsize=(5, 4))
# rank rank by abs importances
interactions['rank'] = interactions['importances'].rank(ascending=False)
plt.scatter(interactions['rank'], interactions['importances'], s=11,
            c=interactions['view'].map({'ct': '#008B8B', 'receptor': '#a11838'}))
            
# add for top 10
top_n = interactions[interactions['rank'] <= 10]
texts = []
for i, row in top_n.iterrows():
    texts.append(plt.text(row['rank'], row['importances'], row['predictor'], fontsize=10))
adjust_text(texts, arrowprops=dict(arrowstyle="->", color='grey', lw=1.5))
plt.tight_layout()
```

Example 26 (python):
```python
interpolate_adata
```

Example 27 (python):
```python
metabs = li.ut.interpolate_adata(target=msi, reference=rna, use_raw=False, spatial_key='spatial')
```

Example 28 (python):
```python
sc.set_figure_params(dpi=80, dpi_save=300, format='png', frameon=False, transparent=True, figsize=[5,5])
```

Example 29 (python):
```python
sc.pl.spatial(metabs, color='Dopamine', cmap='magma', **kwargs)
```

Example 30 (unknown):
```unknown
mdata = mu.MuData({'msi': metabs, 'rna':rna, 'deconv':ct}, obsm=rna.obsm, obs=rna.obs, uns=rna.uns)
```

Example 31 (unknown):
```unknown
li.ut.spatial_neighbors(mdata, bandwidth=bandwidth, cutoff=cutoff, set_diag=True)
```

Example 32 (unknown):
```unknown
interactions = metalinks[['metabolite', 'gene_symbol']].apply(tuple, axis=1).tolist()
```

Example 33 (python):
```python
lrdata = li.mt.bivariate(mdata, 
                         local_name='cosine',
                         x_mod='msi', 
                         y_mod='rna',
                         x_use_raw=False, 
                         y_use_raw=False,
                         verbose=True, 
                         mask_negatives=True, 
                         n_perms=1000,
                         interactions=interactions,
                         x_transform=sc.pp.scale,
                         y_transform=sc.pp.scale,
                        )
```

Example 34 (unknown):
```unknown
Transforming msi using scale
Transforming rna using scale
```

Example 35 (python):
```python
sc.pl.spatial(lrdata,
              color=['Dopamine^Drd1', 'Dopamine^Drd2'],
              cmap='cividis_r', vmax=1, layer='pvals',
              **kwargs)
```

---

## MOFAcellular - Multicellular Factor Analysis — liana

**URL:** http://127.0.0.1:9050/en_latest_notebooks_mofacellular.html

**Contents:**
- MOFAcellular - Multicellular Factor Analysis
- Contents
- MOFAcellular - Multicellular Factor Analysis#
- Background#
- Load Packages#
- Load & Prep Data#
  - Basic QC#
  - Showcase the data#
- Create a Multi-View Structure#
- Pre-process the pseudobulk profiles#
      - View Representation
- Fitting a MOFA model#
- Exploring the MOFA model#
  - Explore Metadata Associations to the Factor Scores#
    - Explore Feature loadings#
  - Explore the model#
- Outlook & Further Analysis#

In Ramirez et al, 2023, we recently showed a repurposed use of the statistical framework of multi-omics factor analysis (MOFA) and MOFA+ to analyse cross-condition single-cell atlases. Specifically, we represented the cross-conditional (e.g. healthy vs. diseased) single-cell transcriptomics data as a multi-view structure, where each cell type represents an individual view that contains summarized information per sample (e.g. pseudobulk). We then applied MOFA to estimate a latent space that captures the variability of the data across samples and cell types.

In this tutorial, we will guide the generation of a multi-view structure from single-cell transcriptomics data and a basic application of MOFA to capture multicellular variability. We make use of the MuData/muon infrastructure.

mofa, decoupler, omnipath, and marsilea can be installed via pip with the following commands:

As a simple example, we will look at ~25k PBMCs from 8 pooled patient lupus samples, each before and after IFN-beta stimulation (Kang et al., 2018; GSE96583). Note that by focusing on PBMCs, for the purpose of this tutorial, we assume that coordinated events occur among them.

This dataset is downloaded from a link on Figshare; preprocessed for pertpy.

Define columns of interest from .obs

Note that we use cell abbreviations because MOFA will use them as labels for the views.

Note that this data has been largely pre-processed & annotated, we refer the user to the Quality Control and other relevant chapters from the best-practices book for information about pre-processing and annotation steps.

To construct a multi-view structure, we need to define the views. In this case, we will use the adata_to_views function from liana to create a list of views (stored in a MuData object), where each view corresponds to a cell type. Simply put, we summarize the samples to pseudobulks by cell type, and then we create a view for each cell type.

We refer users to decoupler’s get_pseudobulk function for more information about filtering and aggregation options.

We see that we have 7 modalities (views) that correspond to the sufficiently abundant cell types & genes in the data.

We can also explore the statistics at the pseodobulk level, when keep_stats=True:

(Optional) Let’s remove what one would consider background marker genes. The intuition here is that marker genes from some cell types should not be deregulated across conditions in others, and thus, they should not be captured by the latent space.

Next, we will normalize each of the views independently to ensure that samples are comparable. We will also identify the highly-variable genes per view (i.e. across samples) - this is optional & dependent on our assumptions.

We will use the filter_view_markers to remove genes that are considered background.

We suggest users to also consider internal muon functions (e.g. mu.pp.filter_obs & mu.pp.filter_var) to remove cells and variables that are not informative.

MOFA supports the flexible representation of views, where each view can represent a different type of features (e.g. genes, proteins, metabolites, etc.). In this case, we simply allow for different genes to be used in each view.

Now that the single-cell data is transformed into a multi-view representation, we can use MOFA to run a multicellular factor analysis.

We will attempt to capture the variability across samples and the different cell-types by reducing the data into a number of factors, where each factor captures the coordinated gene expression across cell types.

For convenience, we provide simple getter function to access the model parameters, in addition to those available via the MuData API & the MOFA model itself.

Let’s check if any of the factors are associated with the sample condition:

We can see that the first factor is associated with the sample condition, let’s plot the factor scores:

Now that we have identified a factor that is associated with the sample condition, we can check the features with the highest loadings associated with each cell type:

We can see that some genes are present in only some of the cell type views and that some of the genes with highest (absolute) loadings tend to be cell type specific. Many genes are also be shared across views, but it’s challenging to to decipher if they are shared because they are coordinated by the same biological process or because of technical issues with the data. Thus, an essential step in the analysis is to select the genes for each cell type (view) in a way that is consistent with the biological knowledge of those cell types.

NB: the interpretation of the sign of the feature loadings is relevant only to the sign of the factor scores themselves. In other words, a negative sign would mean that the features are negatively associated with the scores of a given factor, and the contrary for positive loadings!

Finally, we can also explore the MOFA model itself and we will specifically check the variance explained by each cell type.

We can see that Factor 1 captures the majority of the variance explained, and that CD14+ Monocytes have the highest R-squared for the first factor. In other words, CD14+ Monocytes are the cell type with the highest variance explained by the model and specifically factor 1, thus this suggests that the variability within this view is mostly associated with the difference between samples from the control and condition.

This tutorial is just a short introduction of the use of MOFA, we thus refer the users to the available MOFA & muon tutorials for more applications & details.

Intercellular Context Factorization with Tensor-Cell2cell

Intercellular Context Factorization with MOFA

By Daniel Dimitrov, Philipp Sven Lars Schäfer, Elias Farr, Pablo Rodriguez-Mier, Sebastian Lobentanzer, Pau Badia-i-Mompel, Aurelien Dugourd, Jovan Tanevski, Ricardo Omar Ramirez Flores, Julio Saez-Rodriguez

© Copyright 2025, Daniel Dimitrov, Philipp Sven Lars Schäfer, Elias Farr, Pablo Rodriguez-Mier, Sebastian Lobentanzer, Pau Badia-i-Mompel, Aurelien Dugourd, Jovan Tanevski, Ricardo Omar Ramirez Flores, Julio Saez-Rodriguez..

**Examples:**

Example 1 (unknown):
```unknown
pip install "decoupler>=2.0.0"
pip install mofax
pip install muon
pip install omnipath
pip install marsilea
```

Example 2 (python):
```python
import numpy as np
import pandas as pd

import scanpy as sc

import plotnine as p9

import liana as li

# load muon and mofax
import muon as mu
import mofax as mofa

import decoupler as dc
```

Example 3 (python):
```python
adata = li.testing.datasets.kang_2018()
```

Example 4 (unknown):
```unknown
AnnData object with n_obs × n_vars = 24673 × 15706
    obs: 'nCount_RNA', 'nFeature_RNA', 'tsne1', 'tsne2', 'condition', 'cluster', 'cell_type', 'patient', 'nCount_SCT', 'nFeature_SCT', 'integrated_snn_res.0.4', 'seurat_clusters', 'sample', 'cell_abbr'
    var: 'name'
    obsm: 'X_pca', 'X_umap'
    layers: 'counts'
```

Example 5 (unknown):
```unknown
sample_key = 'sample'
condition_key = 'condition'
groupby = 'cell_abbr'
```

Example 6 (python):
```python
# filter cells and genes
sc.pp.filter_cells(adata, min_genes=200)
sc.pp.filter_genes(adata, min_cells=3)
```

Example 7 (python):
```python
# Store the counts to use them later
adata.layers["counts"] = adata.X.copy()

# Normalize and find marker genes per cell type
# We will use those to remove potential noise from the data  
sc.pp.normalize_total(adata, target_sum=1e4)
sc.pp.log1p(adata)
sc.tl.rank_genes_groups(adata, groupby=groupby)
```

Example 8 (python):
```python
# Show pre-computed UMAP
sc.pl.umap(adata, color=[condition_key, sample_key, 'cell_type', groupby], frameon=False, ncols=2)
```

Example 9 (python):
```python
adata_to_views
```

Example 10 (unknown):
```unknown
get_pseudobulk
```

Example 11 (python):
```python
mdata = li.multi.adata_to_views(adata,
                                groupby=groupby,
                                sample_key=sample_key,
                                keep_stats=True,
                                obs_keys=['condition', 'patient'], # add those to mdata.obs
                                psbulk_kwargs= {'layer': 'counts', 'verbose': False},
                                filter_samples_kwargs={'min_cells': 25, 'min_counts': 100}, # filter samples
                                filter_by_expr_kwargs={'min_count': 10, 'min_total_count': 15, 'large_n': 5}, 
                                filter_by_prop_kwargs={'min_prop': 0.05, 'min_smpls': 3}, # filter features
                                )
```

Example 12 (unknown):
```unknown
keep_stats=True
```

Example 13 (unknown):
```unknown
mdata.uns['psbulk_stats'].head()
```

Example 14 (python):
```python
# create dictionary of markers for each cell type
markers = {}
top_n = 25
for cell_type in mdata.mod.keys():
    markers[cell_type] = (sc.get.rank_genes_groups_df(adata, group=cell_type).
                          sort_values("scores", key=abs, ascending=False).
                          head(top_n)['names'].
                          tolist()
                          )
```

Example 15 (unknown):
```unknown
li.multi.filter_view_markers(mdata, markers=markers, var_column=None, inplace=True)
mdata.update()
```

Example 16 (python):
```python
for view in mdata.mod.keys():
    
    sc.pp.normalize_total(mdata.mod[view], target_sum=1e4)
    sc.pp.log1p(mdata.mod[view])
    
    sc.pp.highly_variable_genes(mdata.mod[view])
```

Example 17 (unknown):
```unknown
filter_view_markers
```

Example 18 (unknown):
```unknown
mu.pp.filter_obs
```

Example 19 (unknown):
```unknown
mu.pp.filter_var
```

Example 20 (unknown):
```unknown
mu.tl.mofa(mdata,
           use_obs='union',
           convergence_mode='medium',
           n_factors=5,
           seed=1337,
           outfile='models/mofacellx.h5ad',
           use_var='highly_variable'
           )
```

Example 21 (unknown):
```unknown
#########################################################
        ###           __  __  ____  ______                    ### 
        ###          |  \/  |/ __ \|  ____/\    _             ### 
        ###          | \  / | |  | | |__ /  \ _| |_           ### 
        ###          | |\/| | |  | |  __/ /\ \_   _|          ###
        ###          | |  | | |__| | | / ____ \|_|            ###
        ###          |_|  |_|\____/|_|/_/    \_\              ###
        ###                                                   ### 
        ######################################################### 
       
 
        
Loaded view='CD14' group='group1' with N=16 samples and D=2661 features...
Loaded view='CD4T' group='group1' with N=16 samples and D=2769 features...
Loaded view='DCs' group='group1' with N=16 samples and D=866 features...
Loaded view='NK' group='group1' with N=16 samples and D=808 features...
Loaded view='CD8T' group='group1' with N=16 samples and D=486 features...
Loaded view='B' group='group1' with N=16 samples and D=1235 features...
Loaded view='FGR3' group='group1' with N=16 samples and D=1172 features...


Model options:
- Automatic Relevance Determination prior on the factors: True
- Automatic Relevance Determination prior on the weights: True
- Spike-and-slab prior on the factors: False
- Spike-and-slab prior on the weights: True
Likelihoods:
- View 0 (CD14): gaussian
- View 1 (CD4T): gaussian
- View 2 (DCs): gaussian
- View 3 (NK): gaussian
- View 4 (CD8T): gaussian
- View 5 (B): gaussian
- View 6 (FGR3): gaussian




######################################
## Training the model with seed 1337 ##
######################################



Converged!



#######################
## Training finished ##
#######################


Output directory does not exist, creating it...
Saving model in models/mofacellx.h5ad...
Saved MOFA embeddings in .obsm['X_mofa'] slot and their loadings in .varm['LFs'].
```

Example 22 (python):
```python
adata = sc.AnnData(obs = mdata.obs, obsm=mdata.obsm)
```

Example 23 (python):
```python
dc.tl.rankby_obsm(
    adata,
    key='X_mofa',  # Where the PCs are stored
    uns_key='rank_obsm',  # Where the results are stored
)

dc.pl.obsm(
    adata,
    key='rank_obsm',
    names = ['patient', 'condition'], # which sample annotations to plot
    titles=['Principle component scores', 'Adjusted p-values from ANOVA'],
    figsize=(7, 5),
    nvar=10,
)
```

Example 24 (unknown):
```unknown
# obtain factor scores
factor_scores = li.ut.get_factor_scores(mdata, obsm_key='X_mofa', obs_keys=['condition', 'patient'])
factor_scores.head()
```

Example 25 (python):
```python
# we use a paired t-test as the samples are paired
from scipy.stats import ttest_rel
```

Example 26 (python):
```python
# split in control and stimulated
group1 = factor_scores[factor_scores['condition']=='ctrl']
group2 = factor_scores[factor_scores['condition']=='stim']

# get all columns that contain factor & loop
factors = [col for col in factor_scores.columns if 'Factor' in col]
for factor in factors:
    print(ttest_rel(group1[factor], group2[factor]))
```

Example 27 (unknown):
```unknown
TtestResult(statistic=-36.70525735749619, pvalue=2.8951763758879465e-09, df=7)
TtestResult(statistic=-0.10486959132354809, pvalue=0.9194209594623381, df=7)
TtestResult(statistic=0.24427008991619767, pvalue=0.8140268352756769, df=7)
TtestResult(statistic=0.14908407553470024, pvalue=0.8856914836182663, df=7)
TtestResult(statistic=0.37162448579080987, pvalue=0.7211660767570919, df=7)
```

Example 28 (unknown):
```unknown
# scatterplot
(p9.ggplot(factor_scores) +
 p9.aes(x='condition', colour='condition', y='Factor1') +
 p9.geom_violin() +
 p9.geom_jitter(size=4, width=0.2) +
 p9.theme_bw() +
 p9.scale_colour_manual(values=['#1f77b4', '#c20019'])
 )
```

Example 29 (unknown):
```unknown
variable_loadings =  li.ut.get_variable_loadings(mdata, varm_key='LFs', view_sep=':') # get loadings
# order features by absolute value for Factor 1
variable_loadings = variable_loadings.sort_values(by='Factor1', key=lambda x: abs(x), ascending=False)
variable_loadings.head()
```

Example 30 (unknown):
```unknown
# get top genes with highest absolute loadings across all views
top_genes = variable_loadings['variable'].head(30)
top_loadings = variable_loadings[variable_loadings['variable'].isin(top_genes)]
# ^ Note that the genes with the lowest loadings are equally interesting

# plot them
# dotplot of variable, view, loadings
(p9.ggplot(top_loadings) + 
 p9.aes(x='view', y='variable', fill='Factor1') + 
 p9.geom_tile() +
 p9.scale_fill_gradient2(low='#1f77b4', mid='lightgray', high='#c20019') + 
 p9.theme_minimal() +
 p9.theme(axis_text_x=p9.element_text(angle=90, hjust=0.5), figure_size=(5, 5))
 )
```

Example 31 (unknown):
```unknown
model = mofa.mofa_model("models/mofacellx.h5ad")
model
```

Example 32 (unknown):
```unknown
MOFA+ model: mofacellx.h5ad
Samples (cells): 16
Features: 9997
Groups: group1 (16)
Views: B (1235), CD14 (2661), CD4T (2769), CD8T (486), DCs (866), FGR3 (1172), NK (808)
Factors: 5
Expectations: W, Z
```

Example 33 (unknown):
```unknown
mofa.plot_r2(model, x='View')
```

Example 34 (unknown):
```unknown
model.close()
```

---

## Differential Expression Analysis for CCC & Downstream Signalling Networks — liana

**URL:** http://127.0.0.1:9050/en_latest_notebooks_targeted.html

**Contents:**
- Differential Expression Analysis for CCC & Downstream Signalling Networks
- Contents
- Differential Expression Analysis for CCC & Downstream Signalling Networks#
- Background#
- Load Packages#
- Load & Prep Data#
  - Basic QC#
  - Showcase the data#
- Differential Testing#
  - Differential Expression Analysis#
- DEA to Ligand-Receptor Interactions#
  - Dealing with heteromeric complexes#
- Visualize the Results#
  - Ligand-Receptor Plot#
- Intracellular Signaling Networks#
  - Import OmniPath#
  - Select Cell types of Interest#
  - Select Receptors based on interaction stats#
  - Select Transcription Factors of interest#
  - Select top TFs#
  - Generate a Prior Knowledge Network#
  - Calculate Node weights#
  - Find Causal Network#
  - Visualize the Inferred Network#
  - Describe Results#
    - Nodes#
    - Edges (interaction)#
  - Installing the Gurobi Solver: A Step-by-Step Guide#
    - 1. Download Gurobi for Your Operating System:#
    - 2. Unzip and Update Path:#
    - 3. Register for an Academic License:#
    - 4. Install Gurobi Python Interface:#
    - 5. Configure the Solver:#

Cell-cell communication (CCC) events play a critical role in diseases, often experiencing deregulation. To identify differential expression of CCC events between conditions, we can build upon standard differential expression analysis (DEA) approaches, such as DESeq2. While dimensionality reduction methods like extracting intercellular programmes with MOFA+ and Tensor-cell2cell reduce CCC into sets of loadings, hypothesis-driven DEA tests focus on individual gene changes, making them easier to understand and interpret.

In this tutorial, we perform DEA at the pseudobulk level to assess differential expression of genes between conditions. We then translate the results into deregulated complex-informed ligand-receptor interactions and analyze their connections to downstream signaling events.

For further information on pseudobulk DEA, please refer to the Differential Gene Expression chapter in the Single-cell Best Practices book, as well as Decoupler’s pseudobulk vignette. These resources provide more comprehensive details on the subject.

Install mofa, decoupler, and omnipath via pip with the following commands:

As a simple example, we will look at ~25k PBMCs from 8 pooled patient lupus samples, each before and after IFN-beta stimulation (Kang et al., 2018; GSE96583). Note that by focusing on PBMCs, for the purpose of this tutorial, we assume that coordinated events occur among them.

This dataset is downloaded from a link on Figshare; preprocessed for pertpy.

Define columns of interest from .obs

Note that we use cell abbreviations because MOFA will use them as labels for the views.

Note that this data has been largely pre-processed & annotated, we refer the user to the Quality Control and other relevant chapters from the best-practices book for information about pre-processing and annotation steps.

First, we need to generate pseudobulk profiles for each cell type, and we do so using the decoupler package.

We can plot the quality control metrics for each pseudobulk sample:

Next, now that we have generated the pseudobulk profiles, we can perform some edgeR-like filtering using decoupler-py, and then differential expression analysis using the pydeseq2 package - a re-implementation of the original DESeq2 method (Love et al., 2014).

Here, we perform DEA on the pseudobulk profiles for each cell type, for more info check this tutorial: https://decoupler-py.readthedocs.io/en/latest/notebooks/pseudobulk.html

This results in a wall of currently unavoidable verbose text and prints, as such I use %%capture to hide it. One can use quiet to some of the functions but not logfc_shrinkage

Now that we have DEA results per gene, we can combine them into statistics of potentially deregulated ligand-receptor interactions.

To do so, liana provides a simple function li.multi.df_to_lr that calculates average expression as well as proportions based on the passed adata object, and combines those with the DEA results and a ligand-receptor resource. Since in this case we want to focus on gene statics relevant to the condition (stim), let’s subset the adata to those and normalize the counts.

Let’s combine the DEA results with the ligand-receptor interactions. We need to pass the names of the statistics from the DEA table in which we are interest to li.multi.df_to_lr, here we will use the adjusted p-values and Wald test statistic.

LIANA will filter lowly-expressed interactions, i.e. those for which any of the genes are not expressed in at least 0.1 of the cells (by default) in the AnnData object. This can be adjusted with the expr_prop parameter.

Moreover, to deal with complexes for each cell type, as either source or target of the potential CCC events, LIANA will find and assign the subunit of a complex with the lowest gene expression (by default) as the subunit of interest, and will then use the stats for that subunit as the stats of the whole protein complex.

To this end, we also provide the option to provide a complex_col parameter, which will be used to assign the complex subunit of interest. This column should be a part of the stat_keys. Note that the absolute minimum value is used (i.e. the value closest to 0 is thought to be the ‘worst’ result), so this will not work for statistics with ascending values (e.g. p-values).

interaction_* columns returned by li.multi.dea_to_lr are just the mean of the ligand and receptor columns of the corresponding statistic! Please use with caution as this is just a summary of the interaction that we can use to e.g. to sort the interactions as done above. Instead, we recommend to use the ligand and receptor statistics separately to filter and visualize the interactions.

Moreover, by averaging the statistics across the ligand and receptor, we are focusing on the interactions for which both the ligand and receptor are deregulated in the same direction, i.e. both up or both down. However, this might ignore interactions in which e.g. the the ligand is deregulated while the receptor is not, or such where they are deregulated in opposite directions. These could represent potential inhibitory mechanisms, but we leave this to the user to explore.

Now that we have covered the basics, we can visualize our interactions in a few ways.

Let’s start with the top interactions according to their Wald statistic, and then plot the statistics for the ligands & receptors involved in those interactions across cell types, to do so LIANA+ provide li.pl.tileplot:

If you want to plot the expression values for ligand-receptor interactions without the DEA statistics, you can set the return_all_lrs parameter to True in the li.multi.dea_to_lr function. This will return a dataframe with all the ligand-receptor interactions, where missing DEA stats will be set as nan, while mean expression and proportions per cluster will be obtained via the AnnData object.

We can also use visualize of the stats, summarized at the level of the interaction, to prioritize the interactions, or any subunit statistics using li.pl.dotplot. For example, we can visualize the mean Wald statistic between the ligand & receptor, together with the pvalues for the ligand.

Now that we have identified a set of interactions that are potentially deregulated we can look into the downstream signalling events that they might be involved in.

Cellular signaling networks govern the behavior of cells, allowing them to respond to external signals, including various cell-cell communication events. Thus, CCC events can be thought of as upstream perturbants of intracellular signaling networks that lead to deregulations of downstream signaling events. Such deregulations are expected to be associated with various conditions and disease. Thus, understanding intracellular signaling networks is critical to model the cellular mechanisms.

Here, we will combine several tools to identify plausible signalling cascades driven by CCC events.

Our approach includes the following steps:

Select a number of potentially deregulated ligand-receptor interactions (input nodes), in terms of summarized PyDESeq2 statistics.

Select a number of potentially deregulated TFs (output nodes). This is done via the use of Transcription factor (TF) activity inference. Carried out on differential gene expression data using TF regulon knowledge with decoupler

Obtain a prior knowledge network (PKNs), with signed protein-protein interactions from OmniPath.

Generate weights for the nodes in the PKN

Use CORNETO to identify a solution in the form of a causal (smallest sign-consistent signaling) network that explains the measured inputs and outputs

For this part OmniPath is required.

One limitation of using DEA to identify interactions of interest is that it tells us little about deregulation at the level of cell types. However, from dimensionality reductions on CCC, as done with Tensor-cell2cell & MOFA on the same dataset, we can see there is a potential deregulation of CCC that involve CD14 monocytes both as sources (senders) and targets (or receivers) of intecellular communication. Thus, we will focus on the interactions and downstream signalling within that cell type.

These will be used as the input or start nodes for the network. In this case, we will use interactions potentially involved in autocrine signalling in CD14 monocytes.

Before we select the transcription factors, we need to infer their activity. We will do so using decoupler with CollecTri regulons. Specifically, we will estimate TF activities using the Wald statistics (from PyDESeq2) for the genes in the regulons.

7 rows × 7802 columns

Now that we have the potentially deregulated TFs, we focus on the top 10 TFs, based on their enrichment scores. In this case, we will look specifically at the top TFs deregulated in CD14 monocytes.

Now we will obtain protein-protein interactions from OmniPath, filter them according to curation effort to ensure we only keep those that are of high quality, and convert them into a knowledge graph.

In this section we use Prior Knowledge Networks (PKNs) from OmniPath to generate network hypotheses based on the deregulated interactions considering both sign and direction. Specifically, we focus on highly curated protein-protein interactions, which often represent hubs in the network. Since such network approaches are highly dependent on prior knowledge, for a review on prior knowledge bias and similar network inference methods, including thier limitations, see Garrido-Rodriguez et al., 2022.

Calculate gene expression proportions within the target cell type; we will use those as node weights in the network.

CORNETO (Rodriguez-Mier et al., In prep) generalizes biological network inference problems using convex and combinatorial optimization. Here, we use it to find the smallest sign-consistent network that explains the measured inputs and outputs, a network inference problem formulated in CARNIVAL.

To run CORNETO, we need to first install it; it’s very lightweight and can be installed via pip:

Now that the solution has been found, we can visualize it using the cn.methods.carnival.visualize_network function.

We can see that the network above, largely captures a potential regulatory cascade with inhibitory (–|) and stimulatory (–>) interactions, related to JAK-STAT signalling. The network, in this case, starts from a receptor (triangle), coming from the top interactions, and ends with the deregulated TFs (square). The remainder of the nodes (circles) were inferred, taking their weights into account, and were not necessarily included in the input or output nodes.

In this example, we represent the directionality of signalling such that intracellular signalling is downstream of intercellular communication events. However, in biology cellular response is an admixture of both; thus such approaches are a simplification of biological reality.

Let’s examine the result of the subnetwork search - it provides information about the predicted signs of nodes and edges.

source: source nodes in the Protein-Protein Interaction (PPI) network. Suffixes such as “_s,” “_pert_c0,” and “_meas_c0” indicate specific experimental conditions or measurement types (they are there simply because of how the ILP problem is formulated, and can be ignored).

target: target nodes in the PPI network, with suffixes similar to the source node.

source_type (unmeasured, input):

input: start nodes (provided by the users, here receptors).

output: end nodes (provides by the user, here transcription factors).

unmeasured: Nodes that are neither input nor output - i.e. those that predicted by the algorithm.

source_weight and target_weight: Inputs to the causal net method, indicating the influence of “measured” nodes within the network. Only the sign is taken into account.

source_pred_val (1, 0, -1): Regulatory state of the node:

0: No differential expression

target_pred_val (1, -1): Regulatory state of the target node:

edge_type (1, -1, 0): Type of interaction from prior knowledge:

1: Activating interaction (e.g., A -> B)

-1: Inhibitory interaction

edge_pred_val (1, -1): Predicted effect of the interaction on the target node:

While in this small example the internal scipy solver works, for larger networks we recommend using a solver such as Gurobi.

Gurobi is a powerful optimization solver used in various mathematical programming problems. Here’s how you can install it:

Visit the Gurobi download page and select the version compatible with your OS.

After downloading, unzip the file. Locate the /bin folder inside the unzipped directory and add it to your system’s $PATH variable. This step is crucial as it allows your system to recognize and run Gurobi from anywhere.

If you’re an academic user, you can obtain a free license. Register and request an academic license through the Gurobi portal. Follow the prompts to complete your registration.

Open your command prompt or terminal and run:

This command installs the necessary Python interface to interact with Gurobi.

In your code, ensure the solver parameter is set to gurobi to direct your program to use the Gurobi solver.

By following these steps, you should have Gurobi installed and ready to tackle complex optimization problems.

Learning Spatial Relationships with MISTy

Intercellular Context Factorization with Tensor-Cell2cell

By Daniel Dimitrov, Philipp Sven Lars Schäfer, Elias Farr, Pablo Rodriguez-Mier, Sebastian Lobentanzer, Pau Badia-i-Mompel, Aurelien Dugourd, Jovan Tanevski, Ricardo Omar Ramirez Flores, Julio Saez-Rodriguez

© Copyright 2025, Daniel Dimitrov, Philipp Sven Lars Schäfer, Elias Farr, Pablo Rodriguez-Mier, Sebastian Lobentanzer, Pau Badia-i-Mompel, Aurelien Dugourd, Jovan Tanevski, Ricardo Omar Ramirez Flores, Julio Saez-Rodriguez..

**Examples:**

Example 1 (unknown):
```unknown
pip install "decoupler>=0.1.4"
pip install "pydeseq2>=0.4.0"
```

Example 2 (python):
```python
import numpy as np
import pandas as pd
import scanpy as sc

import plotnine as p9

import liana as li
import decoupler as dc
import omnipath as op

# Import DESeq2
from pydeseq2.dds import DeseqDataSet
from pydeseq2.ds import DeseqStats
```

Example 3 (unknown):
```unknown
# Obtain TF regulons
net = dc.op.collectri(organism='human', remove_complexes=False, license='academic', verbose=False)
```

Example 4 (python):
```python
adata = li.testing.datasets.kang_2018()
adata
```

Example 5 (unknown):
```unknown
AnnData object with n_obs × n_vars = 24673 × 15706
    obs: 'nCount_RNA', 'nFeature_RNA', 'tsne1', 'tsne2', 'condition', 'cluster', 'cell_type', 'patient', 'nCount_SCT', 'nFeature_SCT', 'integrated_snn_res.0.4', 'seurat_clusters', 'sample', 'cell_abbr'
    var: 'name'
    obsm: 'X_pca', 'X_umap'
    layers: 'counts'
```

Example 6 (unknown):
```unknown
sample_key = 'sample'
groupby = 'cell_abbr'
condition_key = 'condition'
```

Example 7 (python):
```python
# filter cells and genes
sc.pp.filter_cells(adata, min_genes=200)
sc.pp.filter_genes(adata, min_cells=3)
```

Example 8 (python):
```python
# Show pre-computed UMAP
sc.pl.umap(adata, color=[condition_key, sample_key, 'cell_type', groupby], frameon=False, ncols=2)
```

Example 9 (python):
```python
pdata = dc.pp.pseudobulk(
    adata,
    sample_col=sample_key,
    groups_col=groupby,
    layer='counts',
    mode='sum'
)
pdata
```

Example 10 (unknown):
```unknown
AnnData object with n_obs × n_vars = 110 × 15701
    obs: 'condition', 'cell_type', 'patient', 'sample', 'cell_abbr', 'psbulk_n_cells', 'psbulk_counts'
    var: 'name', 'n_cells'
    layers: 'psbulk_props'
```

Example 11 (unknown):
```unknown
# filter samples based on number of cells and counts
dc.pp.filter_samples(pdata, min_cells = 10, min_counts=1000)
```

Example 12 (unknown):
```unknown
dc.pl.filter_samples(pdata, groupby=[sample_key, groupby], figsize=(11, 4))
```

Example 13 (python):
```python
%%capture

dea_results = {}
quiet = True

for cell_group in pdata.obs[groupby].unique():
    # Select cell profiles
    ctdata = pdata[pdata.obs[groupby] == cell_group].copy()

    # Obtain genes that pass the edgeR-like thresholds
    # NOTE: QC thresholds might differ between cell types, consider applying them by cell type
    genes = dc.pp.filter_by_expr(ctdata,
                              group=condition_key,
                              min_count=5, # a minimum number of counts in a number of samples
                              min_total_count=10 # a minimum total number of reads across samples
                              )

    # Filter by these genes
    ctdata = ctdata[:, genes].copy()
    
    # Build DESeq2 object
    # NOTE: this data is actually paired, so one could consider fitting the patient label as a confounder
    dds = DeseqDataSet(
        adata=ctdata,
        design_factors=condition_key,
        ref_level=[condition_key, 'ctrl'], # set control as reference
        refit_cooks=True,
        quiet=quiet
    )
    
    # Compute LFCs
    dds.deseq2()
    # Contrast between stim and ctrl
    stat_res = DeseqStats(dds, contrast=[condition_key, 'stim', 'ctrl'], quiet=quiet)
    stat_res.quiet = quiet
    # Compute Wald test
    stat_res.summary()
    # Shrink LFCs
    stat_res.lfc_shrink(coeff='condition_stim_vs_ctrl') # {condition_key}_cond_vs_ref
    
    dea_results[cell_group] = stat_res.results_df
```

Example 14 (python):
```python
# concat results across cell types
dea_df = pd.concat(dea_results)
dea_df = dea_df.reset_index().rename(columns={'level_0': groupby,'level_1':'index'}).set_index('index')
dea_df.head()
```

Example 15 (unknown):
```unknown
# PyDeseq Seems to intrdoce NAs for some p-values
# NOTE: there sometimes some NaN being introduced, best to double check that, in this case it's only for a single gene, but it might be a problem.
len(dea_df[dea_df.isna().any(axis=1)])
```

Example 16 (unknown):
```unknown
li.multi.df_to_lr
```

Example 17 (python):
```python
adata = adata[adata.obs[condition_key]=='stim'].copy()
```

Example 18 (python):
```python
sc.pp.normalize_total(adata, target_sum=1e4)
sc.pp.log1p(adata)
```

Example 19 (unknown):
```unknown
li.multi.df_to_lr
```

Example 20 (python):
```python
lr_res = li.multi.df_to_lr(adata,
                           dea_df=dea_df,
                           resource_name='consensus', # NOTE: uses HUMAN gene symbols!
                           expr_prop=0.1, # calculated for adata as passed - used to filter interactions
                           groupby=groupby,
                           stat_keys=['stat', 'pvalue', 'padj'],
                           use_raw=False,
                           complex_col='stat', # NOTE: we use the Wald Stat to deal with complexes
                           verbose=True,
                           return_all_lrs=False,
                           )
```

Example 21 (unknown):
```unknown
lr_res = lr_res.sort_values("interaction_stat", ascending=False, key=abs)
lr_res.head()
```

Example 22 (unknown):
```unknown
complex_col
```

Example 23 (unknown):
```unknown
interaction_*
```

Example 24 (unknown):
```unknown
li.multi.dea_to_lr
```

Example 25 (unknown):
```unknown
# Let's visualize how this looks like for all interactions  (across all cell types)
lr_res = lr_res.sort_values("interaction_stat", ascending=False)
lr_res['interaction_stat'].hist(bins=50)
```

Example 26 (unknown):
```unknown
li.pl.tileplot
```

Example 27 (python):
```python
li.pl.tileplot(liana_res=lr_res,
               fill = 'expr',
               label='padj',
               label_fun = lambda x: '*' if x < 0.05 else np.nan,
               top_n=15,
               orderby = 'interaction_stat',
               orderby_ascending = False,
               orderby_absolute = False,
               source_title='Ligand',
               target_title='Receptor',
               )
```

Example 28 (unknown):
```unknown
<Figure Size: (500 x 500)>
```

Example 29 (unknown):
```unknown
return_all_lrs
```

Example 30 (unknown):
```unknown
li.multi.dea_to_lr
```

Example 31 (unknown):
```unknown
li.pl.dotplot
```

Example 32 (unknown):
```unknown
plot = li.pl.dotplot(liana_res=lr_res,
                     colour='interaction_stat',
                     size='ligand_pvalue',
                     inverse_size=True,
                     orderby='interaction_stat',
                     orderby_ascending=False,
                     orderby_absolute=True,
                     top_n=10,
                     size_range=(0.5, 4)
                     )

# customize plot
(
    plot
    + p9.theme_bw(base_size=14)
    # fill cmap blue to red, with 0 the middle
    + p9.scale_color_cmap('RdBu_r', midpoint=0, limits=(-10, 10))
    # rotate x
    + p9.theme(axis_text_x=p9.element_text(angle=90), figure_size=(11, 6))

)
```

Example 33 (unknown):
```unknown
<Figure Size: (1100 x 600)>
```

Example 34 (python):
```python
# utily function to select top n interactions
def select_top_n(d, n=None):
    d = dict(sorted(d.items(), key=lambda item: abs(item[1]), reverse=True))
    return {k: v for i, (k, v) in enumerate(d.items()) if i < n}
```

Example 35 (unknown):
```unknown
source_label = 'CD14'
target_label = 'CD14'

# NOTE: We sort by the absolute value of the interaction stat
lr_stats = lr_res[lr_res['source'].isin([source_label]) & lr_res['target'].isin([target_label])].copy()
lr_stats = lr_stats.sort_values('interaction_stat', ascending=False, key=abs)
```

Example 36 (unknown):
```unknown
lr_dict = lr_stats.set_index('receptor')['interaction_stat'].to_dict()
input_scores = select_top_n(lr_dict, n=10)
```

Example 37 (unknown):
```unknown
input_scores
```

Example 38 (unknown):
```unknown
{'CD40': 15.213890738775456,
 'CD80': 11.672283052638337,
 'SIRPA': 9.92679527367514,
 'CCR1': 9.12729237916692,
 'HLA-DPB1': 8.625121687728944,
 'LILRB2': 8.250712282572682,
 'CCR5': 6.024106443619973,
 'PTPRC': 5.811339038637888,
 'LILRB1': 5.586746654720494,
 'CD47': 5.431274692175629}
```

Example 39 (unknown):
```unknown
# First, let's transform the DEA statistics into a DF
# we will use these to estimate deregulated TF activity
dea_wide = dea_df[[groupby, 'stat']].reset_index(names='genes').pivot(index=groupby, columns='genes', values='stat')
dea_wide = dea_wide.fillna(0)
dea_wide
```

Example 40 (unknown):
```unknown
# Run Enrichment Analysis
estimates, pvals = dc.mt.ulm(mat=dea_wide, net=net)
estimates.T.sort_values(target_label, key=abs, ascending=False).head()
```

Example 41 (unknown):
```unknown
tf_data = estimates.copy()
tf_dict = tf_data.loc[target_label].to_dict()
output_scores = select_top_n(tf_dict, n=5)
```

Example 42 (unknown):
```unknown
# obtain ppi network
ppis = op.interactions.OmniPath().get(genesymbols = True)

ppis['mor'] = ppis['is_stimulation'].astype(int) - ppis['is_inhibition'].astype(int)
ppis = ppis[(ppis['mor'] != 0) & (ppis['curation_effort'] >= 5) & ppis['consensus_direction']] 

input_pkn = ppis[['source_genesymbol', 'mor', 'target_genesymbol']]
input_pkn.columns = ['source', 'mor', 'target']
input_pkn.head()
```

Example 43 (unknown):
```unknown
# convert the PPI network into a knowledge graph
prior_graph = li.mt.build_prior_network(input_pkn, input_scores, output_scores, verbose=True)
```

Example 44 (python):
```python
temp = adata[adata.obs[groupby] == target_label].copy()
```

Example 45 (python):
```python
node_weights = pd.DataFrame(temp.X.getnnz(axis=0) / temp.n_obs, index=temp.var_names)
node_weights = node_weights.rename(columns={0: 'props'})
node_weights = node_weights['props'].to_dict()
```

Example 46 (unknown):
```unknown
pip install corneto==0.9.1-alpha.6 cvxpy cylp
```

Example 47 (python):
```python
import corneto as cn
cn.info()
```

Example 48 (unknown):
```unknown
df_res, problem = li.mt.find_causalnet(
    prior_graph, 
    input_scores, 
    output_scores, 
    node_weights,
    # penalize (max_penalty) nodes with counts in less than 0.1 of the cells
    node_cutoff=0.1, 
    max_penalty=1,
    # the penaly of those in > 0.1 prop of cells set to:
    min_penalty=0.01,
    edge_penalty=0.1,
    verbose=False,
    max_runs=50, # NOTE that this repeats the solving either until the max runs are reached
    stable_runs=10, # or until X number of consequitive stable runs are reached (i.e. no new edges are added)
    solver='gurobi' # 'scipy' is available by default, but often results in suboptimal solutions
    )
```

Example 49 (unknown):
```unknown
Set parameter Username
Academic license - for non-commercial use only - expires 2025-01-26
```

Example 50 (unknown):
```unknown
cn.methods.carnival.visualize_network
```

Example 51 (unknown):
```unknown
cn.methods.carnival.visualize_network(df_res)
```

Example 52 (unknown):
```unknown
df_res.head()
```

Example 53 (unknown):
```unknown
pip install gurobipy
```

---

## Spatially-informed Bivariate Metrics — liana

**URL:** http://127.0.0.1:9050/en_latest_notebooks_bivariate.html

**Contents:**
- Spatially-informed Bivariate Metrics
- Contents
- Spatially-informed Bivariate Metrics#
- Environement Setup#
- Load and Normalize Data#
- Background#
  - Available Local Functions#
  - How do they work?#
  - Spatial Connectivity#
- Bivariate Ligand-Receptor Relationships#
  - Global Summaries#
  - Permutation-based p-values#
  - Local Categories#
- Identify Intercellular Patterns#
- Beyond Ligand-Receptors#
  - Extract Cell type Composition#
  - Estimate Transcription Factor Activity#
    - Extract highly-variable TF activities#
  - Estimate Cosine Similarity#
    - Let’s plot the results#

This tutorial provides an overview of the local scores implemented in LIANA+. These scores are used to identify spatially co-expressed ligand-receptor pairs. However, there also applicable to other types of spatially-informed bivariate analyses.

It provides brief explanations of the mathematical formulations of the scores; these include adaptation of bivariate Moran’s R, Pearson correlation, Spearman correlation, weighted Jaccard similarity, and Cosine similarity. The tutorial also showcases interaction categories (masks) and significance testing.

To showcase LIANA’s local functions, we will use an ischemic 10X Visium spatial slide from Kuppe et al., 2022. It is a tissue sample obtained from a patient with myocardial infarction, focusing on the ischemic zone of the heart tissue.

The slide provides spatially-resolved information about the cellular composition and gene expression patterns within the tissue.

Here, we will demonstrate how to use the spatially-informed bivariate metrics to assess the spatial relationship between two variables. Specifically, we focus on local bivariate similarity metrics. In contrast to other spatial Methods, including Misty; focusing on local spatial relationships enables us to pinpoint the exact location of spatial relationships, and to identify spatial relationships that might occur only in a specific sub-region of our samples.

Following the initial concept of LIANA, and inspired by scHOT, we have natively re-implemented 6 local bivariate metrics, including scHOT’s (default) masked Spearman & SpatialDM’s local Moran’s R.

As part of the LIANA+ manuscript, we performed two distinct tasks to evaluate the ability of these metrics to preserve biological information, and saw that on average when used to identify local ligand-receptor relationships, spatially-weighted Cosine similarity did best. Thus, we will focus on it throughout this tutorial. However, we expect that other scoring functions might be better suited for other tasks, e.g. Spatially-weighted Jaccard Similarity should be well suited for categorical data; thus we encourage you to explore them.

The local functions work are quite simple, as they are simply weighted versions of well-known similarity metrics. For example, the spatially-weighted version of Cosine similarity is defined as:

where for each spot i, we perform summation over all spots n, where w​ represents the spatial connectivity weights from spot i to every other spot j; for variables x and y.

The way that spatially-informed methods usually work is by making use of weights based on the proximity (or spatial connectivity) between spots/cells. These spatial connectivities are then used to calculate the metric of interest, e.g. Cosine similarity, in a spatially-informed manner.

The spatial weights in LIANA+ are by default defined as a family of radial kernels that use the inverse Euclidean distance between cells/spots to bind the weights between 0 and 1, with spots that are closest having the highest spatial connectivity to one another (1), while those that are thought to be too far to be in contact are assigned 0.

Key parameters of spatial_neighbors include:

bandwidth controls the radius of the spatial connectivities where higher values will result in a broader area being considered (controls the radius relative to the coordinates stored in adata.obsm['spatial'])

cutoff controls the minimum value that will be considered to have a spatial relationship (anything lower than the cutoff is set to 0).

kernel controls the distribution (shape) of the weights (‘gaussian’ by default)

set_diag sets the diagonal (i.e. the weight for each spot to itself) to 1 if True. NOTE: Here we set it to True as we expect many cells to be neighbors of themselves within a visium spot

As choosing an optimal bandwidith can be tricky, we provide the query_bandwidth function which uses a set of coordinates to provide an estimate of how many cell or spot neighbors are being considered for each spot over a range of bandwidths.

Here, we can see that a bandwidth of 150-200 (pixels) roughly includes 6 neighbours i.e. the first ring of neighbours in the hexagonal grid of 10x Visium. So, we will build the spatial graph with a bandwidth of 200.

Let’s visualize the spatial weights for a single spot to all other spots in the dataset:

LIANA’s connectivities are flexible and can be defined in any way that fits the user. We have thus aligned LIANA’s spatial_neighbors function to Squidpy’s spatial_neighbors function. A perfectly viable solution would be to use Squidpy’s nearest neighbors graph, which one can use to easily replace LIANA’s radial kernel connecitivies.

Now that we have covered the basics, let’s see how these scores look for potential ligand-receptor interactions on our 10X Visium Slide. Note that LIANA+ will take the presence of heteromeric complexes into account at the individual spot-level!

In addition to the local bivariate scores, we can also get the “global” scores for each pair of variables, which we can choose the best pairs of variables to visualize:

We can also use Global bivariate Moran’s R (or Lee’s statistic) - an extension of univariate Moran’s I, as proposed by Anselin 2019 and Lee and Li, 2019; implemented in SEAGAL and SpatialDM.

Bivariate Moran’s R values near zero imply spatial independence, while positive or negative values reflect spatial co-clustering or spatial cross-dispersion, respectively.

From these Global summaries, we see that the average Cosine similarity largely represents coverage - e.g. TIMP1 & CD63 is ubiquoutesly and uniformly distributed across the slide.

On the other hand, among most variable interactions and with with the highest global morans R is e.g. VTN&ITGAV_ITGB5. This interaction is thus more likely to represent biological relationships, with distinct spatial clustering patterns.

So, let’s visualize both:

As expected, we see that the TIMP1 & CD63 interaction is uniformly distributed across the slide, while VTN&ITGAV_ITGB5 shows a clear spatial pattern.

We can also see that this is the case when we look at the individual genes:

In addition to the local scores, we also calculated permutation-based p-values based on a null distribution generated by shuffling the spot labels. Let’s see how these look for the two interactions from above:

These largely agree with what we saw above for VTN&ITGAV_ITGB1 as appears to be specific to a certain region.

Did you notice that we used mask_negatives as a parameter when first estimating the interaction? This essentially means that we mask interactions in which both members are negative (or lowly expressed) when calculating the p-values, i.e. such which occur at places in which both members of the interaction are highly expressed. The locations at which both members are highly- expressed is defined as follows:

For each interaction, we define the category of both x and y for each spot as follows:

Then we combine the categories of x and y for each spot, such that high-high are positive (1), high-low (or low-high) are -1; and low-low are 0. When working with non-negative values (i.e. gene expression); the features will be z-scaled (across observations).

Here, we can distinguish areas in which the interaction between interaction members is positive (high-high) in Red (1), while interactions in which one is high the other is low or negative (High-low) are in Blue (-1). We also see that some interactions are neither, these are predominantly interactions in which both members are lowly-expressed (i.e. low-low); we see those in white (0).

When set to mask_negatives=False, we also return interactions that are not between necessarily positive/high magnitude genes ; when set to mask_negatives=True, we mask interactions that are negative (low-low) or uncategorized; for both the p-values and the local scores.

Now that we have estimated ligand-receptor scores, we can use non-negative matrix factorization (NMF) to identify coordinated cell-cell communication signatures. This would ultimately decompose the ligand-receptor scores into a basis matrix (W) and a coefficient matrix (H). We will use a very simple utility function (around sklearn’s NMF implementation) to do so, along with a simple k (component number) selection procedure.

Basis Matrix (W): Each basis vector represents a characteristic pattern of ligand-receptor expression in the dataset. The values in W (factor score) indicate the strengths of factor in each spot; high values indicate high influence by the associated communication signature, while low values mean a weak influence.

Coefficient Matrix (H): Each row of H represents the participation of the corresponding sample in the identified factor. The elements of each basis vector indicate the contribution of different interactions to the pattern (factor).

By decomposing the ligand-receptor interactions into W and H, NMF can potentially identify underlying CCC processes, with additive and non-negative relationships between the features. This property aligns well with the biological intuition that genes work together in a coordinated manner, but assumes linearity and only captures additive effects. Thus, alternative decomposition or clustering approaches can be used to a similar end.

In this particular scenario, we chose NMF as it is a well-established method for decomposition of non-negative matrices, it is fast, and it is easy to interpret. Also, in our case the ligand-receptor local scores already encode the spatial relationships between the features, so we don’t necessarily need to use a spatial-aware decomposition methods (e.g. SpatialDE, Spatial NMF, Chrysalis, or MEFISTO).

One limitation of NMF is that it requires the number of components (factors) to be specified - a somewhat an arbitrary choice. To aid the selection of n_components, we provide a simple function that estimates an elbow based on reconstruction error. Another limitation is that it only accepts non-negative values, so it won’t work with metrics that can be negative (e.g. Pearson correlation). In this case, we use Cosine similarity with non-negative values, which results also in non-negative local scores.

Convert NMF Factor scores to an AnnData object for plotting

Wee see that Factor 2 is largely covering the ischemic areas of the side, let’s check the interactions contributing the most to it:

While protein-mediated ligand-receptor interactions are interesting, cell-cell communication is not limited to those alone. Rather it is a complex process that involves a variety of different mechanisms such as signalling pathways, metabolite-mediated signalling, and distinct cell types.

So, if such diverse mechanisms are involved in cell-cell communication, why should we limit ourselves to ligand-receptor interactions? Let’s see how we can use LIANA+ to explore other types of cell-cell communication.

One simple approach would be to check relationships e.g. between transcription factors and cell type proportions.

This slide comes with estimated cell type proportions using cell2location; See Kuppe et al., 2022. Let’s extract from .obsm them to an independent AnnData object.

While multi-omics datasets might be even more of an interest, for the sake of simplicity (and because the general lack of spatial mutli-omics data at current times), let’s instead use enrichment analysis to estimate the activity of transcription factors in each spot. We will use one of decoupler-py’s enrichment methods with CollectTRI to do so. Refer to this tutorial for more info.

To reduce the number of TFs for the sake of computational speed, we will only focus on the top 50 most variable TFs.

Note we will use the simple coefficient of variation to identify the most variable TFs, but one can also use more sophisticated or spatially-informed methods to extract those (light-weight suggestions are welcome).

Create MuData object with TF activities and cell type proportions, and transfer spatial connectivities and other information from the original AnnData object.

Define Interactions of interest:

To make the distributions comparable, we simply z-scale the TF activities and cell type proportions via the x_transform & y_transform parameters.

The type of transformation will affect the interpretation of the results, and different types of transformation might be more appropriate for different types of data. We provide zero-inflated minmax zi_minmax & neg_to_zero transformation functions via li.fun.transform.

One can explore how different transformations affect the results, to also get a better feeling how these local metrics work.

Plot variables (without transformations)

Integrating Multi-Modal Spatially-Resolved Technologies with LIANA+

By Daniel Dimitrov, Philipp Sven Lars Schäfer, Elias Farr, Pablo Rodriguez-Mier, Sebastian Lobentanzer, Pau Badia-i-Mompel, Aurelien Dugourd, Jovan Tanevski, Ricardo Omar Ramirez Flores, Julio Saez-Rodriguez

© Copyright 2025, Daniel Dimitrov, Philipp Sven Lars Schäfer, Elias Farr, Pablo Rodriguez-Mier, Sebastian Lobentanzer, Pau Badia-i-Mompel, Aurelien Dugourd, Jovan Tanevski, Ricardo Omar Ramirez Flores, Julio Saez-Rodriguez..

**Examples:**

Example 1 (python):
```python
import pandas as pd
import scanpy as sc
import decoupler as dc
import liana as li
from matplotlib import pyplot as plt
# set dpi to 50, to make the notebook smaller
plt.rcParams['figure.dpi'] = 50

from mudata import MuData
```

Example 2 (python):
```python
adata = sc.read("kuppe_heart19.h5ad", backup_url='https://figshare.com/ndownloader/files/41501073?private_link=4744950f8768d5c8f68c')
adata.layers['counts'] = adata.X.copy()
sc.pp.normalize_total(adata, target_sum=1e4)
sc.pp.log1p(adata)
```

Example 3 (python):
```python
adata.obs.head()
```

Example 4 (python):
```python
sc.pl.spatial(adata, color=[None, 'celltype_niche'], size=1.3, palette='Set1')
```

Example 5 (unknown):
```unknown
li.mt.bivariate.show_functions()
```

Example 6 (python):
```python
adata.obsm['spatial']
```

Example 7 (unknown):
```unknown
query_bandwidth
```

Example 8 (python):
```python
plot, _ = li.ut.query_bandwidth(coordinates=adata.obsm['spatial'], start=0, end=500, interval_n=20)
plot
```

Example 9 (python):
```python
li.ut.spatial_neighbors(adata, bandwidth=200, cutoff=0.1, kernel='gaussian', set_diag=True)
```

Example 10 (python):
```python
li.pl.connectivity(adata, idx=0, size=1.3, figure_size=(6, 5))
```

Example 11 (unknown):
```unknown
spatial_neighbors
```

Example 12 (unknown):
```unknown
spatial_neighbors
```

Example 13 (python):
```python
lrdata = li.mt.bivariate(adata,
                resource_name='consensus', # NOTE: uses HUMAN gene symbols!
                local_name='cosine', # Name of the function
                global_name="morans", # Name global function
                n_perms=100, # Number of permutations to calculate a p-value
                mask_negatives=False, # Whether to mask LowLow/NegativeNegative interactions
                add_categories=True, # Whether to add local categories to the results
                nz_prop=0.2, # Minimum expr. proportion for ligands/receptors and their subunits
                use_raw=False,
                verbose=True
                )
```

Example 14 (unknown):
```unknown
lrdata.var.sort_values("mean", ascending=False).head(3)
```

Example 15 (unknown):
```unknown
lrdata.var.sort_values("std", ascending=False).head(3)
```

Example 16 (unknown):
```unknown
lrdata.var.sort_values("morans", ascending=False).head()
```

Example 17 (python):
```python
# NOTE: reset params as plotnine seems to change them
sc.set_figure_params(dpi=80, dpi_save=300, format='png', frameon=False, transparent=True, figsize=[5,5])
```

Example 18 (python):
```python
sc.pl.spatial(lrdata, color=['VTN^ITGAV_ITGB5', 'TIMP1^CD63'], size=1.4, vmax=1, cmap='magma')
```

Example 19 (python):
```python
sc.pl.spatial(adata, color=['VTN', 'ITGAV', 'ITGB5', 
                            'TIMP1', 'CD63'],
              size=1.4, ncols=2)
```

Example 20 (python):
```python
sc.pl.spatial(lrdata, layer='pvals', color=['VTN^ITGAV_ITGB5', 'TIMP1^CD63'], size=1.4, cmap="magma_r")
```

Example 21 (unknown):
```unknown
mask_negatives
```

Example 22 (python):
```python
sc.pl.spatial(lrdata, layer='cats', color=['VTN^ITGAV_ITGB5', 'TIMP1^CD63'], size=1.4, cmap="coolwarm")
```

Example 23 (unknown):
```unknown
mask_negatives=False
```

Example 24 (unknown):
```unknown
mask_negatives=True
```

Example 25 (unknown):
```unknown
n_components
```

Example 26 (unknown):
```unknown
li.multi.nmf(lrdata, n_components=None, inplace=True, random_state=0, max_iter=200, verbose=True)
```

Example 27 (unknown):
```unknown
# Extract the variable loadings
lr_loadings = li.ut.get_variable_loadings(lrdata, varm_key='NMF_H').set_index('index')
```

Example 28 (unknown):
```unknown
# Extract the factor scores
factor_scores = li.ut.get_factor_scores(lrdata, obsm_key='NMF_W')
```

Example 29 (python):
```python
nmf = sc.AnnData(X=lrdata.obsm['NMF_W'],
                 obs=lrdata.obs,
                 var=pd.DataFrame(index=lr_loadings.columns),
                 uns=lrdata.uns,
                 obsm=lrdata.obsm)
```

Example 30 (python):
```python
sc.pl.spatial(nmf, color=[*nmf.var.index, None], size=1.4, ncols=2)
```

Example 31 (unknown):
```unknown
lr_loadings.sort_values("Factor2", ascending=False).head(10)
```

Example 32 (python):
```python
# let's extract those
comps = li.ut.obsm_to_adata(adata, 'compositions')
# check key cell types
sc.pl.spatial(comps, color=['vSMCs','CM', 'Endo', 'Fib'], size=1.3, ncols=2)
```

Example 33 (unknown):
```unknown
# Get transcription factor resource
net = dc.op.collectri(organism='human', remove_complexes=False, license='academic', verbose=False)
```

Example 34 (python):
```python
# run enrichment
dc.mt.ulm(adata, net=net, raw=False, verbose=True)
```

Example 35 (unknown):
```unknown
Running ulm on mat with 4113 samples and 17703 targets for 694 sources.
```

Example 36 (python):
```python
est = li.ut.obsm_to_adata(adata, 'score_ulm')
est.var['cv'] =  est.X.std(axis=0) / est.X.mean(axis=0)
top_tfs = est.var.sort_values('cv', ascending=False, key=abs).head(50).index
```

Example 37 (python):
```python
mdata = MuData({"tf":est, "comps":comps})
mdata.obsp = adata.obsp
mdata.uns = adata.uns
mdata.obsm = adata.obsm
```

Example 38 (python):
```python
from itertools import product
```

Example 39 (unknown):
```unknown
interactions = list(product(comps.var.index, top_tfs))
```

Example 40 (python):
```python
bdata = li.mt.bivariate(mdata,
                        x_mod="comps",
                        y_mod="tf",
                        x_transform=sc.pp.scale,
                        y_transform=sc.pp.scale,
                        local_name="cosine", 
                        interactions=interactions,
                        mask_negatives=True, 
                        add_categories=True,
                        x_use_raw=False,
                        y_use_raw=False,
                        xy_sep="<->",
                        x_name='celltype',
                        y_name='tf'
                        )
```

Example 41 (unknown):
```unknown
x_transform
```

Example 42 (unknown):
```unknown
y_transform
```

Example 43 (unknown):
```unknown
neg_to_zero
```

Example 44 (unknown):
```unknown
li.fun.transform
```

Example 45 (unknown):
```unknown
bdata.var.sort_values("mean", ascending=False).head(5)
```

Example 46 (python):
```python
sc.pl.spatial(bdata, color=['Myeloid<->SNAI2', 'CM<->HAND1'], size=1.4, cmap="coolwarm", vmax=1, vmin=-1)
```

Example 47 (python):
```python
sc.pl.spatial(bdata, layer='cats', color=['Myeloid<->SNAI2', 'CM<->HAND1'], cmap='coolwarm')
```

Example 48 (python):
```python
sc.pl.spatial(mdata.mod['tf'], color=['SNAI2', 'HAND1'], cmap='coolwarm', size=1.4, vcenter=0)
```

Example 49 (python):
```python
sc.pl.spatial(mdata.mod['comps'], color=['Myeloid', 'CM'], cmap='viridis', size=1.4)
```

---
