# Monocle3-Truly-Complete - Getting Started

**Pages:** 17

---

## Monocle 3

**URL:** http://127.0.0.1:9130/monocle3/docs/projection/index.html

**Contents:**
- Project a query data set onto a reference data set
  - Load the reference and query data sets
  - Remove genes that are not in both data sets
  - Apply a common UMI cutoff
  - Estimate size factors
  - Process the reference data set
  - Project the query data set into the reference space
  - Plot the combined data sets
  - Plot the combined data sets
  - Transfer the reference cell labels to the query data set

Co-embedding is used to compare similar data sets in order to identify similarities and differences and transfer annotations between cells. When the data sets are large and there are many sets to compare, the memory and run time requirements for processing co-embedded data can become impediments. Monocle3's solution is to save the models that transform a reference data set to low-dimensional PCA and UMAP space, and then use the models to transform query data sets to the low-dimensional reference space where one can plot them for comparison or annotate query cells by finding similar reference cells.

We begin by loading the reference and query data sets into Monocle3. To simplify this example, we load both data sets together; however, one can process them independently.

It is essential that the query cds has the same genes in the same order as the reference cds, so we identify the shared genes and sort them.

We filter the cells by applying the same UMI cutoff to our data sets. For these data sets, we applied a cutoff of 1000 to reduce their sizes but we show how to find these cutoffs.

After applying the gene and UMI filters, we re-calculate the size factors of both data sets.

We are ready to process the reference data set by transforming it into PCA and and UMAP low dimension spaces. By setting the build_nn_index to TRUE, we build a nearest neighbor index in the UMAP space, which we will use to transfer the reference annotations to the query. After processing, we save the transform models and nearest neighbor index so that we can use them to transform the query data set into the reference space.

We loaded and filtered the query data into cds_qry earlier in this example so now we load the reference transform models into cds_qry using the load_transform_models() function. load_transform_models() can read reference models stored in a directory created using either store_transform_models() or save_monocle_objects(). Either way, load_transform_models() loads only the transform models into cds_qry. We project the query data into the reference space using the preprocess_transform() and reduce_dimension_transform() functions.

First we plot the reference and query cells in UMAP space.

Now we label the cells in the reference and query cdses, combine the cdses, and plot the combined cells.

Now we transfer the cell type annotations from the reference to the query data set using the nearest neighbor index that we made in the reference UMAP space.

**Examples:**

Example 1 (python):
```python
library(monocle3)
library(Matrix)

# Load the reference data set.
matrix_ref <- readMM(gzcon(url("https://depts.washington.edu:/trapnell-lab/software/monocle3/mouse/data/cao.mouse_embryo.sample.mtx.gz")))
cell_ann_ref <- read.csv(gzcon(url("https://depts.washington.edu:/trapnell-lab/software/monocle3/mouse/data/cao.mouse_embryo.sample.coldata.txt.gz"), text=TRUE), sep='\t')
gene_ann_ref <- read.csv(gzcon(url("https://depts.washington.edu:/trapnell-lab/software/monocle3/mouse/data/cao.mouse_embryo.sample.rowdata.txt.gz"), text=TRUE), sep='\t')

cds_ref <- new_cell_data_set(matrix_ref,
                             cell_metadata = cell_ann_ref,
                             gene_metadata = gene_ann_ref)

# Load the query data set.
matrix_qry <- readMM(gzcon(url("https://depts.washington.edu:/trapnell-lab/software/monocle3/mouse/data/srivatsan.mouse_embryo_scispace.sample.mtx.gz")))
cell_ann_qry <- read.csv(gzcon(url("https://depts.washington.edu:/trapnell-lab/software/monocle3/mouse/data/srivatsan.mouse_embryo_scispace.sample.coldata.txt.gz"), text=TRUE), sep='\t')
gene_ann_qry <- read.csv(gzcon(url("https://depts.washington.edu:/trapnell-lab/software/monocle3/mouse/data/srivatsan.mouse_embryo_scispace.sample.rowdata.txt.gz"), text=TRUE), sep='\t')

cds_qry <- new_cell_data_set(matrix_qry,
                             cell_metadata = cell_ann_qry,
                             gene_metadata = gene_ann_qry)
```

Example 2 (r):
```r
library(monocle3)
library(Matrix)

# Load the reference data set.
matrix_ref <- readMM(gzcon(url("https://depts.washington.edu:/trapnell-lab/software/monocle3/mouse/data/cao.mouse_embryo.sample.mtx.gz")))
cell_ann_ref <- read.csv(gzcon(url("https://depts.washington.edu:/trapnell-lab/software/monocle3/mouse/data/cao.mouse_embryo.sample.coldata.txt.gz"), text=TRUE), sep='\t')
gene_ann_ref <- read.csv(gzcon(url("https://depts.washington.edu:/trapnell-lab/software/monocle3/mouse/data/cao.mouse_embryo.sample.rowdata.txt.gz"), text=TRUE), sep='\t')

cds_ref <- new_cell_data_set(matrix_ref,
                             cell_metadata = cell_ann_ref,
                             gene_metadata = gene_ann_ref)

# Load the query data set.
matrix_qry <- readMM(gzcon(url("https://depts.washington.edu:/trapnell-lab/software/monocle3/mouse/data/srivatsan.mouse_embryo_scispace.sample.mtx.gz")))
cell_ann_qry <- read.csv(gzcon(url("https://depts.washington.edu:/trapnell-lab/software/monocle3/mouse/data/srivatsan.mouse_embryo_scispace.sample.coldata.txt.gz"), text=TRUE), sep='\t')
gene_ann_qry <- read.csv(gzcon(url("https://depts.washington.edu:/trapnell-lab/software/monocle3/mouse/data/srivatsan.mouse_embryo_scispace.sample.rowdata.txt.gz"), text=TRUE), sep='\t')

cds_qry <- new_cell_data_set(matrix_qry,
                             cell_metadata = cell_ann_qry,
                             gene_metadata = gene_ann_qry)
```

Example 3 (unknown):
```unknown
# Genes in reference.
genes_ref <- row.names(cds_ref)

# Genes in query.
genes_qry <- row.names(cds_qry)

# Shared genes.
genes_shared <- intersect(genes_ref, genes_qry)

# Remove non-shared genes.
cds_ref <- cds_ref[genes_shared,]
cds_qry <- cds_qry[genes_shared,]
```

Example 4 (r):
```r
# Genes in reference.
genes_ref <- row.names(cds_ref)

# Genes in query.
genes_qry <- row.names(cds_qry)

# Shared genes.
genes_shared <- intersect(genes_ref, genes_qry)

# Remove non-shared genes.
cds_ref <- cds_ref[genes_shared,]
cds_qry <- cds_qry[genes_shared,]
```

Example 5 (unknown):
```unknown
# Reference data set UMI cutoff.
numi_ref <- min(colData(cds_ref)[['Total_mRNAs']])
# numi_ref is 1001
numi_qry <- min(colData(cds_qry)[['n.umi']])
# numi_qry is 1000
```

Example 6 (r):
```r
# Reference data set UMI cutoff.
numi_ref <- min(colData(cds_ref)[['Total_mRNAs']])
# numi_ref is 1001
numi_qry <- min(colData(cds_qry)[['n.umi']])
# numi_qry is 1000
```

Example 7 (unknown):
```unknown
cds_ref <- estimate_size_factors(cds_ref)
cds_qry <- estimate_size_factors(cds_qry)
```

Example 8 (r):
```r
cds_ref <- estimate_size_factors(cds_ref)
cds_qry <- estimate_size_factors(cds_qry)
```

Example 9 (unknown):
```unknown
build_nn_index
```

Example 10 (unknown):
```unknown
cds_ref <- preprocess_cds(cds_ref, num_dim=100)
cds_ref <- reduce_dimension(cds_ref, build_nn_index=TRUE)
# Save the PCA and UMAP transform models for use with projection.
save_transform_models(cds_ref, 'cds_ref_test_models')
```

Example 11 (r):
```r
cds_ref <- preprocess_cds(cds_ref, num_dim=100)
cds_ref <- reduce_dimension(cds_ref, build_nn_index=TRUE)
# Save the PCA and UMAP transform models for use with projection.
save_transform_models(cds_ref, 'cds_ref_test_models')
```

Example 12 (unknown):
```unknown
load_transform_models()
```

Example 13 (unknown):
```unknown
load_transform_models()
```

Example 14 (unknown):
```unknown
store_transform_models()
```

Example 15 (unknown):
```unknown
save_monocle_objects()
```

Example 16 (unknown):
```unknown
load_transform_models()
```

Example 17 (unknown):
```unknown
preprocess_transform()
```

Example 18 (unknown):
```unknown
reduce_dimension_transform()
```

Example 19 (unknown):
```unknown
# Load the reference transform models into the query cds.
cds_qry <- load_transform_models(cds_qry, 'cds_ref_test_models')
# Apply the reference transform models to the query cds.
cds_qry <- preprocess_transform(cds_qry)
cds_qry <- reduce_dimension_transform(cds_qry)
```

Example 20 (r):
```r
# Load the reference transform models into the query cds.
cds_qry <- load_transform_models(cds_qry, 'cds_ref_test_models')
# Apply the reference transform models to the query cds.
cds_qry <- preprocess_transform(cds_qry)
cds_qry <- reduce_dimension_transform(cds_qry)
```

Example 21 (unknown):
```unknown
plot_cells(cds_ref)
plot_cells(cds_qry)
```

Example 22 (r):
```r
plot_cells(cds_ref)
plot_cells(cds_qry)
```

Example 23 (unknown):
```unknown
# Label the data sets.
colData(cds_ref)[['data_set']] <- 'reference'
colData(cds_qry)[['data_set']] <- 'query'
# Combine the reference and query data sets.
cds_combined <- combine_cds(list(cds_ref, cds_qry),  keep_all_genes=TRUE, cell_names_unique=TRUE, keep_reduced_dims=TRUE)
plot_cells(cds_combined, color_cells_by='data_set')
```

Example 24 (r):
```r
# Label the data sets.
colData(cds_ref)[['data_set']] <- 'reference'
colData(cds_qry)[['data_set']] <- 'query'
# Combine the reference and query data sets.
cds_combined <- combine_cds(list(cds_ref, cds_qry),  keep_all_genes=TRUE, cell_names_unique=TRUE, keep_reduced_dims=TRUE)
plot_cells(cds_combined, color_cells_by='data_set')
```

Example 25 (unknown):
```unknown
cds_qry_lab_xfr <- transfer_cell_labels(cds_qry, reduction_method='UMAP', ref_coldata=colData(cds_ref), ref_column_name='Main_cell_type', query_column_name='cell_type_xfr', transform_models_dir='cds_ref_test_models')
cds_qry_lab_fix <- fix_missing_cell_labels(cds_qry_lab_xfr, reduction_method='UMAP', from_column_name='cell_type_xfr', to_column_name='cell_type_fix')
```

Example 26 (r):
```r
cds_qry_lab_xfr <- transfer_cell_labels(cds_qry, reduction_method='UMAP', ref_coldata=colData(cds_ref), ref_column_name='Main_cell_type', query_column_name='cell_type_xfr', transform_models_dir='cds_ref_test_models')
cds_qry_lab_fix <- fix_missing_cell_labels(cds_qry_lab_xfr, reduction_method='UMAP', from_column_name='cell_type_xfr', to_column_name='cell_type_fix')
```

---

## Monocle 3

**URL:** http://127.0.0.1:9130/monocle3/docs/installation/index.html

**Contents:**
- Installing Monocle 3
  - Required software
  - Testing the installation
  - Installation troubleshooting
    - Errors involving Gdal:
      - Example error messages:
      - Solution:
    - Errors involving Xcode:
      - Solution:
    - Errors involving gfortran:
      - Example error messages:
      - Solution:
    - Errors involving reticulate:
      - Example error messages:
      - Solution:

Monocle 3 runs in the R statistical computing environment. You will need R version 4.4.1 or higher, Bioconductor version 3.21, and monocle3 1.4.25 or higher to have access to the latest features.

To install Bioconductor, open R and run:

Next, install a few Bioconductor dependencies that aren't automatically installed:

Install the devtools and BPCells packages:

More information is available at BPCells.

Now, install monocle3 through the cole-trapnell-lab GitHub, execute:

If you wish to install the develop branch of monocle3, execute:

To ensure that Monocle 3 was installed correctly, start a new R session and run:

Below are a few of the most common errors that users encounter when installing Monocle 3. If you discover new difficulties, please open an issue on Github describing the problem.

One of Monocle 3's dependencies requires a package called gdal. For information on how to install it on your system, see the sf installation instructions here.

For Mac users only, Xcode command line tools is required. To install, open terminal and type xcode-select --install and then follow the prompts. When it has completed installation, restart the Monocle 3 installation instructions.

The above error indicates that you need to install gfortran on your computer (for Mac users only). In order to do so, Make sure that you have Xcode command line tools installed on your computer. Remove other gfortran installations if they exist. For this, you can launch a terminal window and type "which gfortran". If you see a path returned (e.g. /usr/local/bin/gfortran) you have a previous installation of gfortran that needs to be removed. Download new gfortran binaries for your operating system from here and decompress the folder (eg: gunzip gfortran-8.3-bin.tar.gz). Then run, sudo tar -xvf gfortran-8.3-bin.tar -C / which will install everything in /usr/local/bin/gfortran.

Many users report issues configuring 'reticulate' to find their Python installation. These issues seem to be particularly problematic for Windows users. Because of this, we have rewritten the functions that required Python so that Reticulate and Python are no longer required for installation. If you are still getting errors relating to Python or Reticulate, please make sure you are attempting to install Monocle 3 version 0.2.0 or later.

**Examples:**

Example 1 (unknown):
```unknown
if (!requireNamespace("BiocManager", quietly = TRUE))
install.packages("BiocManager")
BiocManager::install(version = "3.21")
```

Example 2 (r):
```r
if (!requireNamespace("BiocManager", quietly = TRUE))
install.packages("BiocManager")
BiocManager::install(version = "3.21")
```

Example 3 (unknown):
```unknown
BiocManager::install(c('BiocGenerics', 'DelayedArray', 'DelayedMatrixStats',
                       'limma', 'lme4', 'S4Vectors', 'SingleCellExperiment',
                       'SummarizedExperiment', 'batchelor', 'HDF5Array',
                       'ggrastr'))
```

Example 4 (r):
```r
BiocManager::install(c('BiocGenerics', 'DelayedArray', 'DelayedMatrixStats',
                       'limma', 'lme4', 'S4Vectors', 'SingleCellExperiment',
                       'SummarizedExperiment', 'batchelor', 'HDF5Array',
                       'ggrastr'))
```

Example 5 (unknown):
```unknown
install.packages("devtools")
remotes::install_github("bnprks/BPCells/r")
```

Example 6 (r):
```r
install.packages("devtools")
remotes::install_github("bnprks/BPCells/r")
```

Example 7 (unknown):
```unknown
devtools::install_github('cole-trapnell-lab/monocle3')
```

Example 8 (r):
```r
devtools::install_github('cole-trapnell-lab/monocle3')
```

Example 9 (unknown):
```unknown
devtools::install_github('cole-trapnell-lab/monocle3', ref="develop")
```

Example 10 (r):
```r
devtools::install_github('cole-trapnell-lab/monocle3', ref="develop")
```

Example 11 (unknown):
```unknown
library(monocle3)
```

Example 12 (r):
```r
library(monocle3)
```

Example 13 (unknown):
```unknown
configure: error: gdal-config not found or not executable.
ERROR: configuration failed for package ‘sf’
* removing ‘/Library/Frameworks/R.framework/Versions/3.4/Resources/library/sf’
Warning in install.packages :
installation of package ‘sf’ had non-zero exit status
```

Example 14 (bash):
```bash
configure: error: gdal-config not found or not executable.
ERROR: configuration failed for package ‘sf’
* removing ‘/Library/Frameworks/R.framework/Versions/3.4/Resources/library/sf’
Warning in install.packages :
installation of package ‘sf’ had non-zero exit status
```

Example 15 (unknown):
```unknown
xcode-select --install
```

Example 16 (unknown):
```unknown
make: gfortran: No such file or directory
make: *** [cigraph/src/AMD/Source/amd.o] Error 1
ERROR: compilation failed for package 'leidenbase'
```

Example 17 (bash):
```bash
make: gfortran: No such file or directory
make: *** [cigraph/src/AMD/Source/amd.o] Error 1
ERROR: compilation failed for package 'leidenbase'
```

Example 18 (unknown):
```unknown
Error in system("which python", intern = TRUE) : 'which' not found
```

Example 19 (bash):
```bash
Error in system("which python", intern = TRUE) : 'which' not found
```

---

## Monocle 3

**URL:** http://127.0.0.1:9130/monocle3/docs/trajectories/index.html

**Contents:**
- Constructing single-cell trajectories
  - Pre-process the data
  - Reduce dimensionality and visualize the results
  - Cluster your cells
  - Learn the trajectory graph
  - Order the cells in pseudotime
  - What is pseudotime?
  - Subset cells by branch
  - Working with 3D trajectories

During development, in response to stimuli, and throughout life, cells transition from one functional "state" to another. Cells in different states express different sets of genes, producing a dynamic repetoire of proteins and metabolites that carry out their work. As cells move between states, they undergo a process of transcriptional re-configuration, with some genes being silenced and others newly activated. These transient states are often hard to characterize because purifying cells in between more stable endpoint states can be difficult or impossible. Single-cell RNA-Seq can enable you to see these states without the need for purification. However, to do so, we must determine where each cell is in the range of possible states.

Monocle introduced the strategy of using RNA-Seq for single-cell trajectory analysis. Rather than purifying cells into discrete states experimentally, Monocle uses an algorithm to learn the sequence of gene expression changes each cell must go through as part of a dynamic biological process. Once it has learned the overall "trajectory" of gene expression changes, Monocle can place each cell at its proper position in the trajectory. You can then use Monocle's differential analysis toolkit to find genes regulated over the course of the trajectory, as described in the section Finding genes that change as a function of pseudotime . If there are multiple outcomes for the process, Monocle will reconstruct a "branched" trajectory. These branches correspond to cellular "decisions", and Monocle provides powerful tools for identifying the genes affected by them and involved in making them. You can see how to analyze branches in the section Analyzing branches in single-cell trajectories .

The workflow for reconstructing trajectories is very similar to the workflow for clustering, but it has a few additional steps. To illustrate the workflow, we will use another C. elegans data set, this one from Packer & Zhu et al. Their study includes a time series analysis of whole developing embyros. We will examine a small subset of the data which includes most of the neurons. We will load it as we did with the L2 data:

Pre-processing works exactly as in clustering analysis. This time, we will use a different strategy for batch correction, which includes what Packer & Zhu et al did in their original analysis:

Note: Your data will not have the loading batch information demonstrated here, you will correct batch using your own batch information.

Note that in addition to using the alignment_group argument to align_cds(), which aligns groups of cells (i.e. batches), we are also using residual_model_formula_str. This argument is for subtracting continuous effects. You can use this to control for things like the fraction of mitochondrial reads in each cell, which is sometimes used as a QC metric for each cell. In this experiment (as in many scRNA-seq experiments), some cells spontanously lyse, releasing their mRNAs into the cell suspension immediately prior to loading into the single-cell library prep. This "supernatant RNA" contaminates each cells' transcriptome profile to a certain extent. Fortunately, it is fairly straightforward to estimate the level of background contamination in each batch of cells and subtract it, which is what Packer et al did in the original study. Each of the columns bg.300.loading, bg.400.loading, corresponds to a background signal that a cell might be contaminated with. Passing these colums as terms in the residual_model_formula_str tells align_cds() to subtract these signals prior to dimensionality reduction, clustering, and trajectory inference. Note that you can call align_cds() with alignment_group, residual_model_formula, or both. Reduce dimensionality and visualize the results Next, we reduce the dimensionality of the data. However, unlike clustering, which works well with both UMAP and t-SNE, here we strongly urge you to use UMAP, the default method: cds <- reduce_dimension(cds) plot_cells(cds, label_groups_by_cluster=FALSE, color_cells_by = "cell.type") As you can see, despite the fact that we are only looking at a small slice of this dataset, Monocle reconstructs a trajectory with numerous branches. Overlaying the manual annotations on the UMAP reveals that these branches are principally occupied by one cell type. As with clustering analysis, you can use plot_cells() to visualize how individual genes vary along the trajectory. Let's look at some genes with interesting patterns of expression in ciliated neurons: ciliated_genes <- c("che-1", "hlh-17", "nhr-6", "dmd-6", "ceh-36", "ham-1") plot_cells(cds, genes=ciliated_genes, label_cell_groups=FALSE, show_trajectory_graph=FALSE) We will learn how to identify the genes that are restricted to each outcome of the trajectory later on in the section Finding genes that change as a function of pseudotime. Cluster your cells Although cells may continuously transition from one state to the next with no discrete boundary between them, Monocle does not assume that all cells in the dataset descend from a common transcriptional "ancestor". In many experiments, there might in fact be multiple distinct trajectories. For example, in a tissue responding to an infection, tissue resident immune cells and stromal cells will have very different initial transcriptomes, and will respond to infection quite differently, so they should be a part of the same trajectory. Monocle is able to learn when cells should be placed in the same trajectory as opposed to separate trajectories through its clustering procedure. Recall that we run cluster_cells(), each cell is assigned not only to a cluster but also to a partition. When you are learning trajectories, each partition will eventually become a separate trajectory. We run cluster_cells()as before. cds <- cluster_cells(cds) plot_cells(cds, color_cells_by = "partition") Learn the trajectory graph Next, we will fit a principal graph within each partition using the learn_graph() function: cds <- learn_graph(cds) plot_cells(cds, color_cells_by = "cell.type", label_groups_by_cluster=FALSE, label_leaves=FALSE, label_branch_points=FALSE) This graph will be used in many downstream steps, such as branch analysis and differential expression. Order the cells in pseudotime Once we've learned a graph, we are ready to order the cells according to their progress through the developmental program. Monocle measures this progress in pseudotime. The box below defines pseudotime. What is pseudotime? Pseudotime is a measure of how much progress an individual cell has made through a process such as cell differentiation. In many biological processes, cells do not progress in perfect synchrony. In single-cell expression studies of processes such as cell differentiation, captured cells might be widely distributed in terms of progress. That is, in a population of cells captured at exactly the same time, some cells might be far along, while others might not yet even have begun the process. This asynchrony creates major problems when you want to understand the sequence of regulatory changes that occur as cells transition from one state to the next. Tracking the expression across cells captured at the same time produces a very compressed sense of a gene's kinetics, and the apparent variability of that gene's expression will be very high. By ordering each cell according to its progress along a learned trajectory, Monocle alleviates the problems that arise due to asynchrony. Instead of tracking changes in expression as a function of time, Monocle tracks changes as a function of progress along the trajectory, which we term "pseudotime". Pseudotime is an abstract unit of progress: it's simply the distance between a cell and the start of the trajectory, measured along the shortest path. The trajectory's total length is defined in terms of the total amount of transcriptional change that a cell undergoes as it moves from the starting state to the end state. In order to place the cells in order, we need to tell Monocle where the "beginning" of the biological process is. We do so by choosing regions of the graph that we mark as "roots" of the trajectory. In time series experiments, this can usually be accomplished by finding spots in the UMAP space that are occupied by cells from early time points: plot_cells(cds, color_cells_by = "embryo.time.bin", label_cell_groups=FALSE, label_leaves=TRUE, label_branch_points=TRUE, graph_label_size=1.5) The black lines show the structure of the graph. Note that the graph is not fully connected: cells in different partitions are in distinct components of the graph. The circles with numbers in them denote special points within the graph. Each leaf, denoted by light gray circles, corresponds to a different outcome (i.e. cell fate) of the trajectory. Black circles indicate branch nodes, in which cells can travel to one of several outcomes. You can control whether or not these are shown in the plot with the label_leaves and label_branch_points arguments to plot_cells. Please note that numbers within the circles are provided for reference purposes only. Now that we have a sense of where the early cells fall, we can call order_cells(), which will calculate where each cell falls in pseudotime. In order to do so order_cells()needs you to specify the root nodes of the trajectory graph. If you don't provide them as an argument, it will launch a graphical user interface for selecting one or more root nodes. cds <- order_cells(cds) In the above example, we just chose one location, but you could pick as many as you want. Plotting the cells and coloring them by pseudotime shows how they were ordered: plot_cells(cds, color_cells_by = "pseudotime", label_cell_groups=FALSE, label_leaves=FALSE, label_branch_points=FALSE, graph_label_size=1.5) Note that some of the cells are gray. This means they have infinite pseudotime, because they were not reachable from the root nodes that were picked. In general, any cell on a partition that lacks a root node will be assigned an infinite pseudotime. In general, you should choose at least one root per partition. It's often desirable to specify the root of the trajectory programmatically, rather than manually picking it. The function below does so by first grouping the cells according to which trajectory graph node they are nearest to. Then, it calculates what fraction of the cells at each node come from the earliest time point. Then it picks the node that is most heavily occupied by early cells and returns that as the root. # a helper function to identify the root principal points: get_earliest_principal_node <- function(cds, time_bin="130-170"){ cell_ids <- which(colData(cds)[, "embryo.time.bin"] == time_bin) closest_vertex <- cds@principal_graph_aux[["UMAP"]]$pr_graph_cell_proj_closest_vertex closest_vertex <- as.matrix(closest_vertex[colnames(cds), ]) root_pr_nodes <- igraph::V(principal_graph(cds)[["UMAP"]])$name[as.numeric(names (which.max(table(closest_vertex[cell_ids,]))))] root_pr_nodes } cds <- order_cells(cds, root_pr_nodes=get_earliest_principal_node(cds)) Passing the programatically selected root node to order_cells() via the root_pr_nodeargument yields: plot_cells(cds, color_cells_by = "pseudotime", label_cell_groups=FALSE, label_leaves=FALSE, label_branch_points=FALSE, graph_label_size=1.5) Note that we could easily do this on a per-partition basis by first grouping the cells by partition using the partitions() function. This would result in all cells being assigned a finite pseudotime. Subset cells by branch It is often useful to subset cells based on their branch in the trajectory. The function choose_graph_segments allows you to do so interactively. cds_sub <- choose_graph_segments(cds) Working with 3D trajectories cds_3d <- reduce_dimension(cds, max_components = 3) cds_3d <- cluster_cells(cds_3d) cds_3d <- learn_graph(cds_3d) cds_3d <- order_cells(cds_3d, root_pr_nodes=get_earliest_principal_node(cds)) cds_3d_plot_obj <- plot_cells_3d(cds_3d, color_cells_by="partition") Previous Next

Next, we reduce the dimensionality of the data. However, unlike clustering, which works well with both UMAP and t-SNE, here we strongly urge you to use UMAP, the default method:

As you can see, despite the fact that we are only looking at a small slice of this dataset, Monocle reconstructs a trajectory with numerous branches. Overlaying the manual annotations on the UMAP reveals that these branches are principally occupied by one cell type.

As with clustering analysis, you can use plot_cells() to visualize how individual genes vary along the trajectory. Let's look at some genes with interesting patterns of expression in ciliated neurons:

We will learn how to identify the genes that are restricted to each outcome of the trajectory later on in the section Finding genes that change as a function of pseudotime.

Although cells may continuously transition from one state to the next with no discrete boundary between them, Monocle does not assume that all cells in the dataset descend from a common transcriptional "ancestor". In many experiments, there might in fact be multiple distinct trajectories. For example, in a tissue responding to an infection, tissue resident immune cells and stromal cells will have very different initial transcriptomes, and will respond to infection quite differently, so they should be a part of the same trajectory.

Monocle is able to learn when cells should be placed in the same trajectory as opposed to separate trajectories through its clustering procedure. Recall that we run cluster_cells(), each cell is assigned not only to a cluster but also to a partition. When you are learning trajectories, each partition will eventually become a separate trajectory. We run cluster_cells()as before.

Next, we will fit a principal graph within each partition using the learn_graph() function:

This graph will be used in many downstream steps, such as branch analysis and differential expression.

Once we've learned a graph, we are ready to order the cells according to their progress through the developmental program. Monocle measures this progress in pseudotime. The box below defines pseudotime.

Pseudotime is a measure of how much progress an individual cell has made through a process such as cell differentiation.

In many biological processes, cells do not progress in perfect synchrony. In single-cell expression studies of processes such as cell differentiation, captured cells might be widely distributed in terms of progress. That is, in a population of cells captured at exactly the same time, some cells might be far along, while others might not yet even have begun the process. This asynchrony creates major problems when you want to understand the sequence of regulatory changes that occur as cells transition from one state to the next. Tracking the expression across cells captured at the same time produces a very compressed sense of a gene's kinetics, and the apparent variability of that gene's expression will be very high.

By ordering each cell according to its progress along a learned trajectory, Monocle alleviates the problems that arise due to asynchrony. Instead of tracking changes in expression as a function of time, Monocle tracks changes as a function of progress along the trajectory, which we term "pseudotime". Pseudotime is an abstract unit of progress: it's simply the distance between a cell and the start of the trajectory, measured along the shortest path. The trajectory's total length is defined in terms of the total amount of transcriptional change that a cell undergoes as it moves from the starting state to the end state.

In order to place the cells in order, we need to tell Monocle where the "beginning" of the biological process is. We do so by choosing regions of the graph that we mark as "roots" of the trajectory. In time series experiments, this can usually be accomplished by finding spots in the UMAP space that are occupied by cells from early time points:

The black lines show the structure of the graph. Note that the graph is not fully connected: cells in different partitions are in distinct components of the graph. The circles with numbers in them denote special points within the graph. Each leaf, denoted by light gray circles, corresponds to a different outcome (i.e. cell fate) of the trajectory. Black circles indicate branch nodes, in which cells can travel to one of several outcomes. You can control whether or not these are shown in the plot with the label_leaves and label_branch_points arguments to plot_cells. Please note that numbers within the circles are provided for reference purposes only.

Now that we have a sense of where the early cells fall, we can call order_cells(), which will calculate where each cell falls in pseudotime. In order to do so order_cells()needs you to specify the root nodes of the trajectory graph. If you don't provide them as an argument, it will launch a graphical user interface for selecting one or more root nodes.

In the above example, we just chose one location, but you could pick as many as you want. Plotting the cells and coloring them by pseudotime shows how they were ordered:

Note that some of the cells are gray. This means they have infinite pseudotime, because they were not reachable from the root nodes that were picked. In general, any cell on a partition that lacks a root node will be assigned an infinite pseudotime. In general, you should choose at least one root per partition.

It's often desirable to specify the root of the trajectory programmatically, rather than manually picking it. The function below does so by first grouping the cells according to which trajectory graph node they are nearest to. Then, it calculates what fraction of the cells at each node come from the earliest time point. Then it picks the node that is most heavily occupied by early cells and returns that as the root.

Passing the programatically selected root node to order_cells() via the root_pr_nodeargument yields:

Note that we could easily do this on a per-partition basis by first grouping the cells by partition using the partitions() function. This would result in all cells being assigned a finite pseudotime.

It is often useful to subset cells based on their branch in the trajectory. The function choose_graph_segments allows you to do so interactively.

**Examples:**

Example 1 (python):
```python
expression_matrix <- readRDS(url("https://depts.washington.edu:/trapnell-lab/software/monocle3/celegans/data/packer_embryo_expression.rds"))
cell_metadata <- readRDS(url("https://depts.washington.edu:/trapnell-lab/software/monocle3/celegans/data/packer_embryo_colData.rds"))
gene_annotation <- readRDS(url("https://depts.washington.edu:/trapnell-lab/software/monocle3/celegans/data/packer_embryo_rowData.rds"))

cds <- new_cell_data_set(expression_matrix,
                         cell_metadata = cell_metadata,
                         gene_metadata = gene_annotation)
```

Example 2 (r):
```r
expression_matrix <- readRDS(url("https://depts.washington.edu:/trapnell-lab/software/monocle3/celegans/data/packer_embryo_expression.rds"))
cell_metadata <- readRDS(url("https://depts.washington.edu:/trapnell-lab/software/monocle3/celegans/data/packer_embryo_colData.rds"))
gene_annotation <- readRDS(url("https://depts.washington.edu:/trapnell-lab/software/monocle3/celegans/data/packer_embryo_rowData.rds"))

cds <- new_cell_data_set(expression_matrix,
                         cell_metadata = cell_metadata,
                         gene_metadata = gene_annotation)
```

Example 3 (unknown):
```unknown
cds <- preprocess_cds(cds, num_dim = 50)
cds <- align_cds(cds, alignment_group = "batch", residual_model_formula_str = "~ bg.300.loading + bg.400.loading + bg.500.1.loading + bg.500.2.loading + bg.r17.loading + bg.b01.loading + bg.b02.loading")
```

Example 4 (r):
```r
cds <- preprocess_cds(cds, num_dim = 50)
cds <- align_cds(cds, alignment_group = "batch", residual_model_formula_str = "~ bg.300.loading + bg.400.loading + bg.500.1.loading + bg.500.2.loading + bg.r17.loading + bg.b01.loading + bg.b02.loading")
```

Example 5 (unknown):
```unknown
alignment_group
```

Example 6 (unknown):
```unknown
align_cds()
```

Example 7 (unknown):
```unknown
residual_model_formula_str
```

Example 8 (unknown):
```unknown
bg.300.loading
```

Example 9 (unknown):
```unknown
bg.400.loading
```

Example 10 (unknown):
```unknown
residual_model_formula_str
```

Example 11 (unknown):
```unknown
align_cds()
```

Example 12 (unknown):
```unknown
align_cds()
```

Example 13 (unknown):
```unknown
alignment_group
```

Example 14 (unknown):
```unknown
residual_model_formula
```

Example 15 (unknown):
```unknown
cds <- reduce_dimension(cds)
plot_cells(cds, label_groups_by_cluster=FALSE,  color_cells_by = "cell.type")
```

Example 16 (r):
```r
cds <- reduce_dimension(cds)
plot_cells(cds, label_groups_by_cluster=FALSE,  color_cells_by = "cell.type")
```

Example 17 (unknown):
```unknown
plot_cells()
```

Example 18 (unknown):
```unknown
ciliated_genes <- c("che-1",
                    "hlh-17",
                    "nhr-6",
                    "dmd-6",
                    "ceh-36",
                    "ham-1")

plot_cells(cds,
           genes=ciliated_genes,
           label_cell_groups=FALSE,
           show_trajectory_graph=FALSE)
```

Example 19 (r):
```r
ciliated_genes <- c("che-1",
                    "hlh-17",
                    "nhr-6",
                    "dmd-6",
                    "ceh-36",
                    "ham-1")

plot_cells(cds,
           genes=ciliated_genes,
           label_cell_groups=FALSE,
           show_trajectory_graph=FALSE)
```

Example 20 (unknown):
```unknown
cluster_cells()
```

Example 21 (unknown):
```unknown
cluster_cells()
```

Example 22 (unknown):
```unknown
cds <- cluster_cells(cds)
plot_cells(cds, color_cells_by = "partition")
```

Example 23 (r):
```r
cds <- cluster_cells(cds)
plot_cells(cds, color_cells_by = "partition")
```

Example 24 (unknown):
```unknown
learn_graph()
```

Example 25 (unknown):
```unknown
cds <- learn_graph(cds)
plot_cells(cds,
           color_cells_by = "cell.type",
           label_groups_by_cluster=FALSE,
           label_leaves=FALSE,
           label_branch_points=FALSE)
```

Example 26 (r):
```r
cds <- learn_graph(cds)
plot_cells(cds,
           color_cells_by = "cell.type",
           label_groups_by_cluster=FALSE,
           label_leaves=FALSE,
           label_branch_points=FALSE)
```

Example 27 (unknown):
```unknown
plot_cells(cds,
           color_cells_by = "embryo.time.bin",
           label_cell_groups=FALSE,
           label_leaves=TRUE,
           label_branch_points=TRUE,
           graph_label_size=1.5)
```

Example 28 (r):
```r
plot_cells(cds,
           color_cells_by = "embryo.time.bin",
           label_cell_groups=FALSE,
           label_leaves=TRUE,
           label_branch_points=TRUE,
           graph_label_size=1.5)
```

Example 29 (unknown):
```unknown
label_leaves
```

Example 30 (unknown):
```unknown
label_branch_points
```

Example 31 (unknown):
```unknown
order_cells()
```

Example 32 (unknown):
```unknown
order_cells()
```

Example 33 (unknown):
```unknown
cds <- order_cells(cds)
```

Example 34 (r):
```r
cds <- order_cells(cds)
```

Example 35 (unknown):
```unknown
plot_cells(cds,
           color_cells_by = "pseudotime",
           label_cell_groups=FALSE,
           label_leaves=FALSE,
           label_branch_points=FALSE,
           graph_label_size=1.5)
```

Example 36 (r):
```r
plot_cells(cds,
           color_cells_by = "pseudotime",
           label_cell_groups=FALSE,
           label_leaves=FALSE,
           label_branch_points=FALSE,
           graph_label_size=1.5)
```

Example 37 (javascript):
```javascript
# a helper function to identify the root principal points:
get_earliest_principal_node <- function(cds, time_bin="130-170"){
  cell_ids <- which(colData(cds)[, "embryo.time.bin"] == time_bin)
  
  closest_vertex <-
  cds@principal_graph_aux[["UMAP"]]$pr_graph_cell_proj_closest_vertex
  closest_vertex <- as.matrix(closest_vertex[colnames(cds), ])
  root_pr_nodes <-
  igraph::V(principal_graph(cds)[["UMAP"]])$name[as.numeric(names
  (which.max(table(closest_vertex[cell_ids,]))))]
  
  root_pr_nodes
}
cds <- order_cells(cds, root_pr_nodes=get_earliest_principal_node(cds))
```

Example 38 (r):
```r
# a helper function to identify the root principal points:
get_earliest_principal_node <- function(cds, time_bin="130-170"){
  cell_ids <- which(colData(cds)[, "embryo.time.bin"] == time_bin)
  
  closest_vertex <-
  cds@principal_graph_aux[["UMAP"]]$pr_graph_cell_proj_closest_vertex
  closest_vertex <- as.matrix(closest_vertex[colnames(cds), ])
  root_pr_nodes <-
  igraph::V(principal_graph(cds)[["UMAP"]])$name[as.numeric(names
  (which.max(table(closest_vertex[cell_ids,]))))]
  
  root_pr_nodes
}
cds <- order_cells(cds, root_pr_nodes=get_earliest_principal_node(cds))
```

Example 39 (unknown):
```unknown
order_cells()
```

Example 40 (unknown):
```unknown
root_pr_node
```

Example 41 (unknown):
```unknown
plot_cells(cds,
           color_cells_by = "pseudotime",
           label_cell_groups=FALSE,
           label_leaves=FALSE,
           label_branch_points=FALSE,
           graph_label_size=1.5)
```

Example 42 (r):
```r
plot_cells(cds,
           color_cells_by = "pseudotime",
           label_cell_groups=FALSE,
           label_leaves=FALSE,
           label_branch_points=FALSE,
           graph_label_size=1.5)
```

Example 43 (unknown):
```unknown
partitions()
```

Example 44 (unknown):
```unknown
choose_graph_segments
```

Example 45 (unknown):
```unknown
cds_sub <- choose_graph_segments(cds)
```

Example 46 (r):
```r
cds_sub <- choose_graph_segments(cds)
```

Example 47 (unknown):
```unknown
cds_3d <- reduce_dimension(cds, max_components = 3)
cds_3d <- cluster_cells(cds_3d)
cds_3d <- learn_graph(cds_3d)
cds_3d <- order_cells(cds_3d, root_pr_nodes=get_earliest_principal_node(cds))

cds_3d_plot_obj <- plot_cells_3d(cds_3d, color_cells_by="partition")
```

Example 48 (r):
```r
cds_3d <- reduce_dimension(cds, max_components = 3)
cds_3d <- cluster_cells(cds_3d)
cds_3d <- learn_graph(cds_3d)
cds_3d <- order_cells(cds_3d, root_pr_nodes=get_earliest_principal_node(cds))

cds_3d_plot_obj <- plot_cells_3d(cds_3d, color_cells_by="partition")
```

---

## Monocle 3

**URL:** http://127.0.0.1:9130/monocle3/docs/citations/index.html

**Contents:**
- Citations and Acknowledgements
  - Cite your analysis using get_citations
  - Acknowledgements
- References

Monocle 3 utilizes methods published by other groups. Please be sure to cite those original methods papers when you use them in your analyses. To make this easier, we provide a function get_citations that will print a data frame with the methods and citations that you used in constructing your CDS object. As you use new methods, they will be added to your citation metadata.

Monocle was originally built by Cole Trapnell and Davide Cacchiarelli, with substantial design input from John Rinn and Tarjei Mikkelsen. We are grateful to Sharif Bordbar, Chris Zhu, Amy Wagers and the Broad RNAi platform for technical assistance, and Magali Soumillon for helpful discussions. Cole Trapnell was supported by a Damon Runyon Postdoctoral Fellowship. Davide Cacchiarelli was supported by a Human Frontier Science Program Fellowship. Cacchiarelli and Mikkelsen were also supported by the Harvard Stem Cell Institute. John Rinn was the Alvin and Esta Star Associate Professor. This work was supported by NIH grants 1DP2OD00667, P01GM099117, and P50HG006193-01. This work was also supported in part by the Single Cell Genomics initiative, a collaboration between the Broad Institute and Fluidigm Inc.

Monocle versions 2 and 3 were developed by Cole Trapnell's lab. Significant portions were written by Xiaojie Qiu and Hannah Pliner. The work was supported by NIH grant 1DP2HD088158, the W. M. Keck Foundation, as well as an Alfred P. Sloan Foundation Research Fellowship. Hannah Pliner is supported by the Brotman Baty Institute.

**Examples:**

Example 1 (unknown):
```unknown
get_citations
```

Example 2 (unknown):
```unknown
get_citations
```

Example 3 (python):
```python
get_citations(cds)

# Your analysis used methods from the following recent work. Please cite them wherever you are presenting your analyses.
#    method       citations
# 1 Monocle       Trapnell C. et. al. The dynamics and regulators of cell fate decisions are revealed by pseudotemporal ordering of single cells. Nat. Biotechnol. 32, 381–386 (2014). https://doi.org/10.1038/nbt.2859
# 2 Monocle       Qiu, X. et. al. Reversed graph embedding resolves complex single-cell trajectories. Nat. Methods 14, 979–982 (2017). https://doi.org/10.1038/nmeth.4402
# 3 Monocle       Cao, J. et. al. The single-cell transcriptional landscape of mammalian organogenesis. Nature 566, 496–502 (2019). https://doi.org/10.1038/s41586-019-0969-x
# 4    UMAP       McInnes, L., Healy, J. & Melville, J. UMAP: Uniform Manifold Approximation and Projection for dimension reduction. Preprint at https://arxiv.org/abs/1802.03426 (2018).
```

Example 4 (r):
```r
get_citations(cds)

# Your analysis used methods from the following recent work. Please cite them wherever you are presenting your analyses.
#    method       citations
# 1 Monocle       Trapnell C. et. al. The dynamics and regulators of cell fate decisions are revealed by pseudotemporal ordering of single cells. Nat. Biotechnol. 32, 381–386 (2014). https://doi.org/10.1038/nbt.2859
# 2 Monocle       Qiu, X. et. al. Reversed graph embedding resolves complex single-cell trajectories. Nat. Methods 14, 979–982 (2017). https://doi.org/10.1038/nmeth.4402
# 3 Monocle       Cao, J. et. al. The single-cell transcriptional landscape of mammalian organogenesis. Nature 566, 496–502 (2019). https://doi.org/10.1038/s41586-019-0969-x
# 4    UMAP       McInnes, L., Healy, J. & Melville, J. UMAP: Uniform Manifold Approximation and Projection for dimension reduction. Preprint at https://arxiv.org/abs/1802.03426 (2018).
```

---

## Monocle 3

**URL:** http://127.0.0.1:9130/monocle3/docs/store_monocle_objects/index.html

**Contents:**
- Save monocle objects
  - Save monocle objects
  - Load monocle objects

The save_monocle_objects() and load_monocle_objects() functions save and load complete cell_data_set objects. The Monocle3 cell_data_set can include UMAP models, nearest neighbor indexes, and BPCells matrix objects, which are not R objects, and cannot be written or read by the R saveRDS() and readRDS() functions. The UMAP models and nearest neighbor indexes are used for projecting data sets and the BPCells matrix objects are used to store count matrices on disk rather than in memory. For convenience, the load_monocle_objects() recognizes and reads cell_data_sets saved using saveRDS().

The save_monocle_objects() function saves all of the information in a cell_data_set to files that are stored in a directory with the name specified by the directory_path argument. The optional comment argument stores a memo string with the objects, which is reported when the cell_data_set is loaded with load_monocle_objects().

The load_monocle_objects() function loads the complete data set into R from the files in the directory specified by the directory_path argument.

By default, the save_monocle_objects() function makes the monocle objects directory and then makes a tar archive file of the directory so that the directory contents can be copied easily. If you decide to remove the directory, verify that the tar archive was made successfully, in case there was a problem such as running out of disk space. The save_monocle_objects() function has an archive_control parameter that gives some control over making the archive.

The monocle objects directory contains files that may include the following an RDS file of the R cell_data_set, excluding the non-R objects annoy nearest neighbor index files a BPcells counts matrix directory an RDS file of with a table of information about the files in the monocle objects directory

**Examples:**

Example 1 (unknown):
```unknown
save_monocle_objects()
```

Example 2 (unknown):
```unknown
load_monocle_objects()
```

Example 3 (unknown):
```unknown
load_monocle_objects()
```

Example 4 (unknown):
```unknown
save_monocle_objects()
```

Example 5 (unknown):
```unknown
directory_path
```

Example 6 (unknown):
```unknown
load_monocle_objects()
```

Example 7 (unknown):
```unknown
save_monocle_objects(cds=cds, directory_path='my_cds_objects', comment='This is my example cds. Stored 2022-04-18.')
```

Example 8 (r):
```r
save_monocle_objects(cds=cds, directory_path='my_cds_objects', comment='This is my example cds. Stored 2022-04-18.')
```

Example 9 (unknown):
```unknown
load_monocle_objects()
```

Example 10 (unknown):
```unknown
directory_path
```

Example 11 (unknown):
```unknown
cds <- load_monocle_objects(directory_path='my_cds_objects')
```

Example 12 (r):
```r
cds <- load_monocle_objects(directory_path='my_cds_objects')
```

Example 13 (unknown):
```unknown
save_monocle_objects()
```

Example 14 (unknown):
```unknown
save_monocle_objects()
```

Example 15 (unknown):
```unknown
archive_control
```

---

## Monocle 3

**URL:** http://127.0.0.1:9130/monocle3/docs/additional/index.html

**Contents:**
- Additional information

Monocle3 stores identifying information about certain objects and their sources, and includes matrix checksums and dimensions. Use the command identity_table(cds) to view this information. For example, > cds <- load_worm_embryo() > cds <- preprocess_cds(cds, build_nn_index=TRUE) > cds <- reduce_dimension(cds, build_nn_index=TRUE) No preprocess_method specified, using preprocess_method = 'PCA' > identity_table(cds) Count matrix identity matrix_id: 7f6a56c3933802a4631c15109e6501c5 dim: 20222 6188 matrix_type: URL: https://depts.washington.edu:/trapnell-lab/software/monocle3/celegans/data/packer_embryo_expression.rds Reduced dimension matrix identity PCA matrix_type matrix:PCA matrix_id 9fb8819fac058c01a6044a2235991588 dim: 6188 50 prev_matrix_type URL: https://depts.washington.edu:/trapnell-lab/software/monocle3/celegans/data/packer_embryo_expression.rds prev_matrix_id 7f6a56c3933802a4631c15109e6501c5 dim: 20222 6188 model_type matrix:PCA model_id 9fb8819fac058c01a6044a2235991588 dim: 6188 50 . . . UMAP matrix_type matrix:UMAP matrix_id 8a52b66ee33e4dad7c9c5310525821ec dim: 6188 2 prev_matrix_type matrix:PCA prev_matrix_id 9fb8819fac058c01a6044a2235991588 dim: 6188 50 model_type matrix:UMAP model_id 8a52b66ee33e4dad7c9c5310525821ec dim: 6188 2 On startup, Monocle3 runs commands in the file $HOME/.monoclerc, if it exists. You can customize Monocle3 behavior by setting global variables in it. For example, if you want Monocle3 to use BPCells matrices, GNU tar, and not tar monocle objects directories by default, create $HOME/.monoclerc with the following function calls # Use BPCells matrix_class for new matrices. monocle3:::set_global_variable('matrix_class_default', 'BPCells') # Don't tar monocle objects directories when running save_monocle_objects. monocle3:::set_global_variable('archive_control', list(archive_type='none', archive_compression='none')) # Use gnu tar for R tar. This affects the save_monocle_objects() function # when it makes a tar archive. Sys.setenv('tar' = paste(Sys.getenv("TAR"), "-H", "gnu")) The function .onLoad() in the file R/zzz.R runs the code in $HOME/.monoclerc on startup. Default global variable values are defined in .onLoad() before sourcing $HOME/.monoclerc, so you can change the defaults by setting them in $HOME/.monoclerc.

**Examples:**

Example 1 (unknown):
```unknown
identity_table(cds)
```

Example 2 (unknown):
```unknown
> cds <- load_worm_embryo()
 > cds <- preprocess_cds(cds, build_nn_index=TRUE)
 > cds <- reduce_dimension(cds, build_nn_index=TRUE)
 No preprocess_method specified, using preprocess_method = 'PCA'
 > identity_table(cds)
Count matrix identity
  matrix_id: 7f6a56c3933802a4631c15109e6501c5  dim: 20222 6188
  matrix_type: URL: https://depts.washington.edu:/trapnell-lab/software/monocle3/celegans/data/packer_embryo_expression.rds

Reduced dimension matrix identity
  PCA
    matrix_type matrix:PCA
    matrix_id   9fb8819fac058c01a6044a2235991588  dim: 6188 50
    prev_matrix_type    URL: https://depts.washington.edu:/trapnell-lab/software/monocle3/celegans/data/packer_embryo_expression.rds
    prev_matrix_id      7f6a56c3933802a4631c15109e6501c5  dim: 20222 6188
    model_type  matrix:PCA
    model_id    9fb8819fac058c01a6044a2235991588  dim: 6188 50

    .
    .
    .

  UMAP
    matrix_type matrix:UMAP
    matrix_id   8a52b66ee33e4dad7c9c5310525821ec  dim: 6188 2
    prev_matrix_type    matrix:PCA
    prev_matrix_id      9fb8819fac058c01a6044a2235991588  dim: 6188 50
    model_type  matrix:UMAP
    model_id    8a52b66ee33e4dad7c9c5310525821ec  dim: 6188 2
```

Example 3 (unknown):
```unknown
$HOME/.monoclerc
```

Example 4 (unknown):
```unknown
$HOME/.monoclerc
```

Example 5 (python):
```python
# Use BPCells matrix_class for new matrices.
monocle3:::set_global_variable('matrix_class_default', 'BPCells')
# Don't tar monocle objects directories when running save_monocle_objects.
monocle3:::set_global_variable('archive_control', list(archive_type='none', archive_compression='none'))
# Use gnu tar for R tar. This affects the save_monocle_objects() function
# when it makes a tar archive.
Sys.setenv('tar' = paste(Sys.getenv("TAR"), "-H", "gnu"))
```

Example 6 (unknown):
```unknown
$HOME/.monoclerc
```

Example 7 (unknown):
```unknown
$HOME/.monoclerc
```

Example 8 (unknown):
```unknown
$HOME/.monoclerc
```

---

## Monocle 3

**URL:** http://127.0.0.1:9130/monocle3/docs/disk_based_matrix/index.html

**Contents:**
- Disk-based count matrix storage
  - Make a cell_data_set with a disk-based matrix
  - Process a cell_data_set with disk-based matrix
  - Store a cell_data_set with a disk-based matrix
  - Temporary disk-based matrix working directory
  - Working with BPCells count matrices

Monocle3 can store the count matrix on disk rather than in memory in a way that is essentially transparent to the user. This reduces substantially the memory required to process a data set while using the familiar Monocle3 functions. This feature depends on Ben Parks' excellent BPCells R package.

Make a cell_data_set with a disk-based counts matrix using the matrix_control parameter with Monocle3 functions that make a cell_data_set; for example, load_mm_data(). In this example, the counts matrix is in a MatrixMarket file called counts.mtx, the gene names are in features.txt, and the cell names are in cells.txt.

Functions that have the matrix_control parameter include

You can convert a dgCMatrix sparse matrix in the cell_data_set to a disk-based matrix using the function convert_counts_matrix(). For example

where counts(matrix) is a dgCMatrix. convert_counts_matrix() makes and stores both the BPCells column-order matrix and the row-order matrix, in an effort to keep the two consistent.

The new_cell_data_set() function has no matrix_control parameter so it does not convert the input matrix to a disk-based matrix. However, if the input matrix is a BPCells matrix, it makes and stores the row-order copy of the input matrix.

After making the cell_data_set with a disk-based matrix, you process it using the same functions as for a cell_data_set with a dgCMatrix counts matrix. For example,

You must use the save_monocle_objects() function to store a cell_data_set that has a disk-based counts matrix, and the load_monocle_objects() function to reload the saved cell_data_set.

Monocle3 makes temporary working directories where the disk-based counts matrix files are kept until you quit the R session, at which time Monocle3 tries to remove them. By default, Monocle3 makes these directories in the directory where you are running R. The directories have names like monocle.bpcells.20240412.3106e35c0e4a2.tmp, which include the date on which the directory is made, a unique string, and the .tmp suffix. Do not delete these directories while the Monocle3 R session is running. If a temporary directory remains after you quit the R session for some reason, you may delete it, if you are certain that the session completed. If you delete such a directory before the session ends, you will lose the counts matrix, which will make the cell_data_set unusable.

You can tell Monocle3 where you want the disk-based working directories using the matrix_control parameter with the list element matrix_path. For example,

**Examples:**

Example 1 (unknown):
```unknown
matrix_control
```

Example 2 (unknown):
```unknown
load_mm_data()
```

Example 3 (unknown):
```unknown
features.txt
```

Example 4 (unknown):
```unknown
cds <- load_mm_data(mat_path='counts.mtx', feature_anno_path='features.txt', cell_anno_path='cells.txt', matrix_control=list(matrix_class='BPCells'))
```

Example 5 (r):
```r
cds <- load_mm_data(mat_path='counts.mtx', feature_anno_path='features.txt', cell_anno_path='cells.txt', matrix_control=list(matrix_class='BPCells'))
```

Example 6 (unknown):
```unknown
matrix_control
```

Example 7 (unknown):
```unknown
load_mm_data()
```

Example 8 (unknown):
```unknown
load_mtx_data()
```

Example 9 (unknown):
```unknown
load_worm_embryo()
```

Example 10 (unknown):
```unknown
load_worm_l2()
```

Example 11 (unknown):
```unknown
load_a549()
```

Example 12 (unknown):
```unknown
combine_cds()
```

Example 13 (unknown):
```unknown
convert_counts_matrix()
```

Example 14 (unknown):
```unknown
counts(cds_bpcells) <- convert_counts_matrix(counts(cds), matrix_control=list(matrix_class='BPCells'))
```

Example 15 (r):
```r
counts(cds_bpcells) <- convert_counts_matrix(counts(cds), matrix_control=list(matrix_class='BPCells'))
```

Example 16 (unknown):
```unknown
counts(matrix)
```

Example 17 (unknown):
```unknown
convert_counts_matrix()
```

Example 18 (unknown):
```unknown
new_cell_data_set()
```

Example 19 (unknown):
```unknown
matrix_control
```

Example 20 (unknown):
```unknown
cds <- load_mm_data(mat_path='counts.mtx', feature_anno_path='features.txt', cell_anno_path='cells.txt', matrix_control=list(matrix_class='BPCells'))
cds <- preprocess_cds(cds)
cds <- reduce_dimension(cds)
cds <- cluster_cells(cds)
```

Example 21 (r):
```r
cds <- load_mm_data(mat_path='counts.mtx', feature_anno_path='features.txt', cell_anno_path='cells.txt', matrix_control=list(matrix_class='BPCells'))
cds <- preprocess_cds(cds)
cds <- reduce_dimension(cds)
cds <- cluster_cells(cds)
```

Example 22 (unknown):
```unknown
save_monocle_objects()
```

Example 23 (unknown):
```unknown
load_monocle_objects()
```

Example 24 (unknown):
```unknown
monocle.bpcells.20240412.3106e35c0e4a2.tmp
```

Example 25 (unknown):
```unknown
matrix_control
```

Example 26 (unknown):
```unknown
matrix_path
```

Example 27 (unknown):
```unknown
cds <- load_worm_embryo(matrix_control=list(matrix_class='BPCells', matrix_path='/home/me/tmp_bpcells'))
```

Example 28 (r):
```r
cds <- load_worm_embryo(matrix_control=list(matrix_class='BPCells', matrix_path='/home/me/tmp_bpcells'))
```

Example 29 (unknown):
```unknown
preprocess_cds()
```

Example 30 (unknown):
```unknown
set_matrix_control()
```

---

## Monocle 3

**URL:** http://127.0.0.1:9130/monocle3/docs/help/index.html

**Contents:**
- Getting Help

Questions about Monocle 3 should be posted on our Google Group. Please do not email technical questions to Monocle contributors directly.

If you believe you have identified a bug in our code or in this website, please submit a bug report with all of the requested information on our Github Issues page.

---

## Monocle 3

**URL:** http://127.0.0.1:9130/monocle3/docs/introduction/index.html

**Contents:**
- Introduction
  - Under construction

Single-cell transcriptome sequencing (sc-RNA-seq) experiments allow us to discover new cell types and help us understand how they arise in development. The Monocle 3 package provides a toolkit for analyzing single-cell gene expression experiments.

Monocle 3 can help you perform three main types of analysis: Clustering, classifying, and counting cells. Single-cell RNA-Seq experiments allow you to discover new (and possibly rare) subtypes of cells. Monocle 3 helps you identify them. Constructing single-cell trajectories. In development, disease, and throughout life, cells transition from one state to another. Monocle 3 helps you discover these transitions. Differential expression analysis. Characterizing new cell types and states begins with comparisons to other, better understood cells. Monocle 3 includes a sophisticated, but easy-to-use system for differential expression.

Monocle 3 is currently in the beta phase of its development. This means there are likely bugs and performance issues that will need to be addressed. We are working hard towards a stable release, but please be patient while Monocle 3 is under construction.

The documentation on this page is also still under construction. Not all features currently implemented have been completely documented.

For more information on the algorithms at the core of Monocle, or to learn more about how to use single-cell RNA-Seq to study complex biological processes, explore our publications.

Before we look at Monocle 3's functions for each of these common analysis tasks, let's see how to install Monocle.

---

## Monocle 3

**URL:** http://127.0.0.1:9130/monocle3/contributors/index.html

**Contents:**
- Monocle Contributors
  - Current
  - Former

Associate ProfessorUniversity of Washington

Data ScientistBrotman Baty Institute

Software EngineerUniversity of Washington

Data AnalystSeattle Children's Research Institute

Graduate StudentUniversity of Washington

Currently: Post-doc at UCSF

Undergraduate StudentUniversity of Washington

---

## Monocle 3

**URL:** http://127.0.0.1:9130/monocle3/docs/clustering/index.html

**Contents:**
- Clustering and classifying your cells
  - Pre-process the data
  - Reduce dimensionality and visualize the cells
  - Faster clustering with UMAP
  - Check for and remove batch effects
  - Group cells into clusters
  - Find marker genes expressed by each cluster
  - Annotate your cells according to type
  - Automated annotation with Garnett
  - Garnett for Monocle 3

Single-cell experiments are often performed on tissues containing many cell types. Monocle 3 provides a simple set of functions you can use to group your cells according to their gene expression profiles into clusters. Often cells form clusters that correspond to one cell type or a set of highly related cell types. Monocle 3 uses techniques to do this that are widely accepted in single-cell RNA-seq analysis and similar to the approaches used by Seurat, scanpy, and other tools.

In this section, you will learn how to cluster cells using Monocle 3. We will demonstrate the main functions used for clustering with the C. elegans data from Cao & Packer et al. This study described how to do single-cell RNA-seq with combinatorial indexing in a protocol called "sci-RNA-seq". Cao & Packer et al. used sci-RNA-seq to produce the first single-cell RNA-seq analysis of a whole animal, so there are many cell types represented in the data. You can learn more about the dataset and see how the authors performed the original analysis at the UW Genome Sciences RNA Atlas of the Worm site.

You can load the data into Monocle 3 like this:

Now that the data's all loaded up, we need to pre-process it. This step is where you tell Monocle 3 how you want to normalize the data, whether to use Principal Components Analysis (the standard for RNA-seq) or Latent Semantic Indexing (common in ATAC-seq), and how to remove any batch effects. We will just use the standard PCA method in this demonstration. When using PCA, you should specify the number of principal components you want Monocle to compute.

It's a good idea to check that you're using enough PCs to capture most of the variation in gene expression across all the cells in the data set. You can look at the fraction of variation explained by each PC using plot_pc_variance_explained():

We can see that using more than 100 PCs would capture only a small amount of additional variation, and each additional PC makes downstream steps in Monocle slower.

Now we're ready to visualize the cells. To do so, you can use either t-SNE, which is very popular in single-cell RNA-seq, or UMAP, which is increasingly common. Monocle 3 uses UMAP by default, as we feel that it is both faster and better suited for clustering and trajectory analysis in RNA-seq. To reduce the dimensionality of the data down into the X, Y plane so we can plot it easily, call reduce_dimension():

To plot the data, use Monocle's main plotting function, plot_cells():

Each point in the plot above represents a different cell in the cell_data_set object cds. As you can see the cells form many groups, some with thousands of cells, some with only a few. Cao & Packer annotated each cell according to type manually by looking at which genes it expresses. We can color the cells in the UMAP plot by the authors' original annotations using the color_cells_by argument to plot_cells().

You can see that many of the cell types land very close to one another in the UMAP plot.

Except for a few cases described in a moment, color_cells_by can be the name of any column in colData(cds). Note that when color_cells_by is a categorical variable, labels are added to the plot, with each label positioned roughly in the middle of all the cells that have that label.

You can also color your cells according to how much of a gene or set of genes they express:

If you have a relatively large dataset (with >10,000 cells or more), you may want to take advantage of options that can accelerate UMAP. Passing umap.fast_sgd=TRUE to reduce_dimension() will use a fast stochastic gradient descent method inside of UMAP. If your computer has multiple cores, you can use the cores argument to make UMAP multithreaded. However, invoking reduce_dimension() with either of these options will make it produce slighly different output each time you run it. If this is acceptable to you, you could see signifant reductions in the running time of reduction_dimension().

If you want, you can also use t-SNE to visualize your data. First, call reduce_dimension with reduction_method="tSNE".

Then, when you call plot_cells(), pass reduction_method="tSNE" to it as well:

You can actually use UMAP and t-SNE on the same cds object - one won't overwrite the results of the other. But you must specify which one you want in downstream functions like plot_cells.

When performing gene expression analysis, it's important to check for batch effects, which are systematic differences in the transcriptome of cells measured in different experimental batches. These could be technical in nature, such as those introduced during the single-cell RNA-seq protocol, or biological, such as those that might arise from different litters of mice. How to recognize batch effects and account for them so that they don't confound your analysis can be a complex issue, but Monocle provides tools for dealing with them.

You should always check for batch effects when you perform dimensionality reduction. You should add a column to the colData that encodes which batch each cell is from. Then you can simply color the cells by batch. Cao & Packer et al included a "plate" annotation in their data, which specifies which sci-RNA-seq plate each cell originated from. Coloring the UMAP by plate reveals:

Dramatic batch effects are not evident in this data. If the data contained more substantial variation due to plate, we'd expect to see groups of cells that really only come from one plate. Nevertheless, we can try and remove what batch effect is by running the align_cds() function:

When run with the alignment_group argument, align_cds() tries to remove batch effects using mutual nearest neighbor alignment, a technique introduced by John Marioni's lab. Monocle 3 does so by calling Aaron Lun's excellent package batchelor. If you use align_cds(), be sure to call get_citations() to see how you should cite the software on which Monocle depends.

Grouping cells into clusters is an important step in identifying the cell types represented in your data. Monocle uses a technique called community detection to group cells. This approach was introduced by Levine et al as part of the phenoGraph algorithm. You can cluster your cells using the cluster_cells() function, like this:

Note that now when we call plot_cells() with no arguments, it colors the cells by cluster according to default.

The cluster_cells() also divides the cells into larger, more well separated groups called partitions, using a statistical test from Alex Wolf et al, introduced as part of their PAGA algorithm. You can visualize these partitions like this:

Once you run cluster_cells(), the plot_cells() function will label each cluster of cells is labeled separately according to how you want to color the cells. For example, the call below colors the cells according to their cell type annotation, and each cluster is labeled according the most common annotation within it:

You can choose to label whole partitions instead of clusters by passing group_cells_by="partition". You can also plot the top 2 labels per cluster by passing labels_per_group=2 to plot_cells(). Finally, you can disable this labeling policy, making plot_cells() behave like it did before we called cluster_cells(), like this:

Once cells have been clustered, we can ask what genes makes them different from one another. To do that, start by calling the top_markers() function:

The data frame marker_test_res contains a number of metrics for how specifically expressed each gene is in each partition. We could group the cells according to cluster, partition, or any categorical variable in colData(cds). You can rank the table according to one or more of the specificity metrics and take the top gene for each cluster. For example, pseudo_R2 is one such measure. We can rank markers according to pseudo_R2 like this:

Now, we can plot the expression and fraction of cells that express each marker in each group with the plot_genes_by_group function:

It's often informative to look at more than one marker, which you can do just by changing the first argument to top_n():

There are many ways to compare and contrast clusters (and other groupings) of cells. We will explore them in great detail in the differential expression analysis section a bit later.

Identifying the type of each cell in your dataset is critical for many downstream analyses. There are several ways of doing this. One commonly used approach is to first cluster the cells and then assign a cell type to each cluster based on its gene expression profile. We've already seen how to use top_markers(). Reviewing literature associated with a marker gene often give strong indications of the identity of clusters that express it. In Cao & Packer >et al, the authors consulted literature and gene expression databases for markers restricted to each cluster in order to assign the identities contained in colData(cds)$cao_cell_type.

To assign cell types based on clustering, we begin by creating a new column in colData(cds) and initialize it with the values of partitions(cds) (can also use clusters(cds) depending on your dataset):

Now, we can use the dplyrpackage's recode() function to remap each cluster to a different cell type:

Let's see how the new annotations look:

Partition 7 has some substructure, and it's not obvious just from looking at the output of top_markers() what cell type or types it corresponds to. So we can isolate it with the choose_cells() function for further analysis:

Now we have a smaller cell_data_set object that contains just the cells from the partition we'd like to drill into. We can use graph_test() to identify genes that are differentially expressed in different subsets of cells from this partition:

We will learn more about graph_test() in the differential expression analysis section later. We can take all the genes that vary across this set of cells and group those that have similar patterns of expression into modules:

Plotting these modules' aggregate expression values reveals which cells express which modues.

You can explore the genes in each module or conduct gene ontology enrichment analysis on them to glean insights about which cell types are present. Suppose after doing this we have a good idea of what the cell types in the partition are. Let's recluster the cells at finer resolution and then see how they overlap with the clusters in the partition:

Based on how the patterns line up, we'll make the following assignments:

Now we can transfer the annotations from the cds_subset object back to the full dataset. We'll also filter out low-quality cells at this stage

The above process for manually annotating cells by type can be laborious, and must be re-done if the underlying cluster changes. We recently developed Garnett, a software toolkit for automatically annotating cells. Garnett classifies cells based on marker genes. If you've gone through the trouble of annotated your cells manually, Monocle can generate a file of marker genes that can be used with Garnett. This will help you annotate other datasets in the future or reannotate this one if you refine your analysis and update your clustering in the future.

To generate a Garnett file, first find the top markers that each annotated cell type expresses:

Next, filter these markers according to how stringent you want to be:

Then call generate_garnett_marker_file:

generate_garnett_marker_file

The marker files produced by generate_garnett_marker_file() are just a starting point for classifying your cells with Garnett. You may want to edit this file to add or remove markers based on literature or other information. You also should consider defining subtypes of cells, which can greatly increase the usefulness and accuracy of Garnett. For example, the L2 data contains many different types of neurons. Making a "Neuron" cell type in the file above and then using the subtype of keyword to organize the various subtypes of neurons will make Garnett more able to recognize them and distinguish them from non-neuronal cell types. When two or more of your cell types share most of their top markers in plot_genes_by_group(), consider defining a broader cell type definition of which they are both subtypes. You might also want to define markers for the various subtypes of neurons by subsetting the cds object above and running top_markers() just on them. See the Garnett documentation for more on how you can enrich your marker files.

When you're ready run Garnett, load the package:

Garnett was originally written to work with Monocle 2. We have created a branch of Garnett that works with Monocle 3, which will eventually replace the main branch. In the meantime, you must install and load the Monocle 3 branch of Garnett!

Now train a Garnett classifier based on your marker file like this:

Now that we've trained a classifier worm_classifier, we can use it to annotate the L2 cells according to type:

Here's how Garnett annotated the cells:

Garnett classifiers can be applied to datasets other than the one they were trained on. We strongly encourage you to share your Garnett files and include them with your papers so that others can use them.

As part of writing a paper about Garnett, we trained a Garnett model to classify C. elegans cells based on the L2 data. You can classify cells with it by first downloading and then passing it to the classify_cells() function:

**Examples:**

Example 1 (python):
```python
library(monocle3)
library(dplyr) # imported for some downstream data manipulation

expression_matrix <- readRDS(url("https://depts.washington.edu:/trapnell-lab/software/monocle3/celegans/data/cao_l2_expression.rds"))
cell_metadata <- readRDS(url("https://depts.washington.edu:/trapnell-lab/software/monocle3/celegans/data/cao_l2_colData.rds"))
gene_annotation <- readRDS(url("https://depts.washington.edu:/trapnell-lab/software/monocle3/celegans/data/cao_l2_rowData.rds"))

cds <- new_cell_data_set(expression_matrix,
                         cell_metadata = cell_metadata,
                         gene_metadata = gene_annotation)
```

Example 2 (r):
```r
library(monocle3)
library(dplyr) # imported for some downstream data manipulation

expression_matrix <- readRDS(url("https://depts.washington.edu:/trapnell-lab/software/monocle3/celegans/data/cao_l2_expression.rds"))
cell_metadata <- readRDS(url("https://depts.washington.edu:/trapnell-lab/software/monocle3/celegans/data/cao_l2_colData.rds"))
gene_annotation <- readRDS(url("https://depts.washington.edu:/trapnell-lab/software/monocle3/celegans/data/cao_l2_rowData.rds"))

cds <- new_cell_data_set(expression_matrix,
                         cell_metadata = cell_metadata,
                         gene_metadata = gene_annotation)
```

Example 3 (unknown):
```unknown
cds <- preprocess_cds(cds, num_dim = 100)
```

Example 4 (r):
```r
cds <- preprocess_cds(cds, num_dim = 100)
```

Example 5 (unknown):
```unknown
plot_pc_variance_explained()
```

Example 6 (unknown):
```unknown
plot_pc_variance_explained(cds)
```

Example 7 (r):
```r
plot_pc_variance_explained(cds)
```

Example 8 (unknown):
```unknown
reduce_dimension()
```

Example 9 (unknown):
```unknown
cds <- reduce_dimension(cds)
```

Example 10 (r):
```r
cds <- reduce_dimension(cds)
```

Example 11 (unknown):
```unknown
plot_cells()
```

Example 12 (unknown):
```unknown
plot_cells(cds)
```

Example 13 (r):
```r
plot_cells(cds)
```

Example 14 (unknown):
```unknown
cell_data_set
```

Example 15 (unknown):
```unknown
color_cells_by
```

Example 16 (unknown):
```unknown
plot_cells()
```

Example 17 (unknown):
```unknown
plot_cells(cds, color_cells_by="cao_cell_type")
```

Example 18 (r):
```r
plot_cells(cds, color_cells_by="cao_cell_type")
```

Example 19 (unknown):
```unknown
color_cells_by
```

Example 20 (unknown):
```unknown
colData(cds)
```

Example 21 (unknown):
```unknown
color_cells_by
```

Example 22 (unknown):
```unknown
plot_cells(cds, genes=c("cpna-2", "egl-21", "ram-2", "inos-1"))
```

Example 23 (r):
```r
plot_cells(cds, genes=c("cpna-2", "egl-21", "ram-2", "inos-1"))
```

Example 24 (unknown):
```unknown
umap.fast_sgd=TRUE
```

Example 25 (unknown):
```unknown
reduce_dimension()
```

Example 26 (unknown):
```unknown
reduce_dimension()
```

Example 27 (unknown):
```unknown
reduction_dimension()
```

Example 28 (unknown):
```unknown
reduction_method="tSNE"
```

Example 29 (unknown):
```unknown
cds <- reduce_dimension(cds, reduction_method="tSNE")
```

Example 30 (r):
```r
cds <- reduce_dimension(cds, reduction_method="tSNE")
```

Example 31 (unknown):
```unknown
plot_cells()
```

Example 32 (unknown):
```unknown
reduction_method="tSNE"
```

Example 33 (unknown):
```unknown
plot_cells(cds, reduction_method="tSNE", color_cells_by="cao_cell_type")
```

Example 34 (r):
```r
plot_cells(cds, reduction_method="tSNE", color_cells_by="cao_cell_type")
```

Example 35 (unknown):
```unknown
plot_cells(cds, color_cells_by="plate", label_cell_groups=FALSE)
```

Example 36 (r):
```r
plot_cells(cds, color_cells_by="plate", label_cell_groups=FALSE)
```

Example 37 (unknown):
```unknown
align_cds()
```

Example 38 (unknown):
```unknown
cds <- align_cds(cds, num_dim = 100, alignment_group = "plate")
cds <- reduce_dimension(cds)
plot_cells(cds, color_cells_by="plate", label_cell_groups=FALSE)
```

Example 39 (r):
```r
cds <- align_cds(cds, num_dim = 100, alignment_group = "plate")
cds <- reduce_dimension(cds)
plot_cells(cds, color_cells_by="plate", label_cell_groups=FALSE)
```

Example 40 (unknown):
```unknown
alignment_group
```

Example 41 (unknown):
```unknown
align_cds()
```

Example 42 (unknown):
```unknown
align_cds()
```

Example 43 (unknown):
```unknown
get_citations()
```

Example 44 (unknown):
```unknown
cluster_cells()
```

Example 45 (unknown):
```unknown
cds <- cluster_cells(cds, resolution=1e-5)
plot_cells(cds)
```

Example 46 (r):
```r
cds <- cluster_cells(cds, resolution=1e-5)
plot_cells(cds)
```

Example 47 (unknown):
```unknown
plot_cells()
```

Example 48 (unknown):
```unknown
cluster_cells()
```

Example 49 (unknown):
```unknown
plot_cells(cds, color_cells_by="partition", group_cells_by="partition")
```

Example 50 (r):
```r
plot_cells(cds, color_cells_by="partition", group_cells_by="partition")
```

Example 51 (unknown):
```unknown
cluster_cells()
```

Example 52 (unknown):
```unknown
plot_cells()
```

Example 53 (unknown):
```unknown
plot_cells(cds, color_cells_by="cao_cell_type")
```

Example 54 (r):
```r
plot_cells(cds, color_cells_by="cao_cell_type")
```

Example 55 (unknown):
```unknown
group_cells_by="partition"
```

Example 56 (unknown):
```unknown
labels_per_group=2
```

Example 57 (unknown):
```unknown
plot_cells()
```

Example 58 (unknown):
```unknown
plot_cells()
```

Example 59 (unknown):
```unknown
cluster_cells()
```

Example 60 (unknown):
```unknown
plot_cells(cds, color_cells_by="cao_cell_type", label_groups_by_cluster=FALSE)
```

Example 61 (r):
```r
plot_cells(cds, color_cells_by="cao_cell_type", label_groups_by_cluster=FALSE)
```

Example 62 (unknown):
```unknown
marker_test_res <- top_markers(cds, group_cells_by="partition", 
                               reference_cells=1000, cores=8)
```

Example 63 (r):
```r
marker_test_res <- top_markers(cds, group_cells_by="partition", 
                               reference_cells=1000, cores=8)
```

Example 64 (unknown):
```unknown
marker_test_res
```

Example 65 (unknown):
```unknown
colData(cds)
```

Example 66 (unknown):
```unknown
top_specific_markers <- marker_test_res %>%
                            filter(fraction_expressing >= 0.10) %>%
                            group_by(cell_group) %>%
                            top_n(1, pseudo_R2)

top_specific_marker_ids <- unique(top_specific_markers %>% pull(gene_id))
```

Example 67 (r):
```r
top_specific_markers <- marker_test_res %>%
                            filter(fraction_expressing >= 0.10) %>%
                            group_by(cell_group) %>%
                            top_n(1, pseudo_R2)

top_specific_marker_ids <- unique(top_specific_markers %>% pull(gene_id))
```

Example 68 (unknown):
```unknown
plot_genes_by_group
```

Example 69 (unknown):
```unknown
plot_genes_by_group(cds,
                    top_specific_marker_ids,
                    group_cells_by="partition",
                    ordering_type="maximal_on_diag",
                    max.size=3)
```

Example 70 (r):
```r
plot_genes_by_group(cds,
                    top_specific_marker_ids,
                    group_cells_by="partition",
                    ordering_type="maximal_on_diag",
                    max.size=3)
```

Example 71 (unknown):
```unknown
top_specific_markers <- marker_test_res %>%
                            filter(fraction_expressing >= 0.10) %>%
                            group_by(cell_group) %>%
                            top_n(3, pseudo_R2)

top_specific_marker_ids <- unique(top_specific_markers %>% pull(gene_id))

plot_genes_by_group(cds,
                    top_specific_marker_ids,
                    group_cells_by="partition",
                    ordering_type="cluster_row_col",
                    max.size=3)
```

Example 72 (r):
```r
top_specific_markers <- marker_test_res %>%
                            filter(fraction_expressing >= 0.10) %>%
                            group_by(cell_group) %>%
                            top_n(3, pseudo_R2)

top_specific_marker_ids <- unique(top_specific_markers %>% pull(gene_id))

plot_genes_by_group(cds,
                    top_specific_marker_ids,
                    group_cells_by="partition",
                    ordering_type="cluster_row_col",
                    max.size=3)
```

Example 73 (unknown):
```unknown
top_markers()
```

Example 74 (unknown):
```unknown
colData(cds)$cao_cell_type
```

Example 75 (unknown):
```unknown
colData(cds)
```

Example 76 (unknown):
```unknown
partitions(cds)
```

Example 77 (unknown):
```unknown
colData(cds)$assigned_cell_type <- as.character(partitions(cds))
```

Example 78 (r):
```r
colData(cds)$assigned_cell_type <- as.character(partitions(cds))
```

Example 79 (unknown):
```unknown
colData(cds)$assigned_cell_type <- dplyr::recode(colData(cds)$assigned_cell_type,
                                                 "1"="Body wall muscle",
                                                 "2"="Germline",
                                                 "3"="Motor neurons",
                                                 "4"="Seam cells",
                                                 "5"="Sex myoblasts",
                                                 "6"="Socket cells",
                                                 "7"="Marginal_cell",
                                                 "8"="Coelomocyte",
                                                 "9"="Am/PH sheath cells",
                                                 "10"="Ciliated neurons",
                                                 "11"="Intestinal/rectal muscle",
                                                 "12"="Excretory gland",
                                                 "13"="Chemosensory neurons",
                                                 "14"="Interneurons",
                                                 "15"="Unclassified eurons",
                                                 "16"="Ciliated neurons",
                                                 "17"="Pharyngeal gland cells",
                                                 "18"="Unclassified neurons",
                                                 "19"="Chemosensory neurons",
                                                 "20"="Ciliated neurons",
                                                 "21"="Ciliated neurons",
                                                 "22"="Inner labial neuron",
                                                 "23"="Ciliated neurons",
                                                 "24"="Ciliated neurons",
                                                 "25"="Ciliated neurons",
                                                 "26"="Hypodermal cells",
                                                 "27"="Mesodermal cells",
                                                 "28"="Motor neurons",
                                                 "29"="Pharyngeal gland cells",
                                                 "30"="Ciliated neurons",
                                                 "31"="Excretory cells",
                                                 "32"="Amphid neuron",
                                                 "33"="Pharyngeal muscle")
```

Example 80 (r):
```r
colData(cds)$assigned_cell_type <- dplyr::recode(colData(cds)$assigned_cell_type,
                                                 "1"="Body wall muscle",
                                                 "2"="Germline",
                                                 "3"="Motor neurons",
                                                 "4"="Seam cells",
                                                 "5"="Sex myoblasts",
                                                 "6"="Socket cells",
                                                 "7"="Marginal_cell",
                                                 "8"="Coelomocyte",
                                                 "9"="Am/PH sheath cells",
                                                 "10"="Ciliated neurons",
                                                 "11"="Intestinal/rectal muscle",
                                                 "12"="Excretory gland",
                                                 "13"="Chemosensory neurons",
                                                 "14"="Interneurons",
                                                 "15"="Unclassified eurons",
                                                 "16"="Ciliated neurons",
                                                 "17"="Pharyngeal gland cells",
                                                 "18"="Unclassified neurons",
                                                 "19"="Chemosensory neurons",
                                                 "20"="Ciliated neurons",
                                                 "21"="Ciliated neurons",
                                                 "22"="Inner labial neuron",
                                                 "23"="Ciliated neurons",
                                                 "24"="Ciliated neurons",
                                                 "25"="Ciliated neurons",
                                                 "26"="Hypodermal cells",
                                                 "27"="Mesodermal cells",
                                                 "28"="Motor neurons",
                                                 "29"="Pharyngeal gland cells",
                                                 "30"="Ciliated neurons",
                                                 "31"="Excretory cells",
                                                 "32"="Amphid neuron",
                                                 "33"="Pharyngeal muscle")
```

Example 81 (unknown):
```unknown
plot_cells(cds, group_cells_by="partition", color_cells_by="assigned_cell_type")
```

Example 82 (r):
```r
plot_cells(cds, group_cells_by="partition", color_cells_by="assigned_cell_type")
```

Example 83 (unknown):
```unknown
top_markers()
```

Example 84 (unknown):
```unknown
choose_cells()
```

Example 85 (unknown):
```unknown
cds_subset <- choose_cells(cds)
```

Example 86 (r):
```r
cds_subset <- choose_cells(cds)
```

Example 87 (unknown):
```unknown
cell_data_set
```

Example 88 (unknown):
```unknown
graph_test()
```

Example 89 (unknown):
```unknown
pr_graph_test_res <- graph_test(cds_subset, neighbor_graph="knn", cores=8)
pr_deg_ids <- row.names(subset(pr_graph_test_res, morans_I > 0.01 & q_value < 0.05))
```

Example 90 (r):
```r
pr_graph_test_res <- graph_test(cds_subset, neighbor_graph="knn", cores=8)
pr_deg_ids <- row.names(subset(pr_graph_test_res, morans_I > 0.01 & q_value < 0.05))
```

Example 91 (unknown):
```unknown
graph_test()
```

Example 92 (unknown):
```unknown
gene_module_df <- find_gene_modules(cds_subset[pr_deg_ids,], resolution=1e-3)
```

Example 93 (r):
```r
gene_module_df <- find_gene_modules(cds_subset[pr_deg_ids,], resolution=1e-3)
```

Example 94 (unknown):
```unknown
plot_cells(cds_subset, genes=gene_module_df, 
           show_trajectory_graph=FALSE, 
           label_cell_groups=FALSE)
```

Example 95 (r):
```r
plot_cells(cds_subset, genes=gene_module_df, 
           show_trajectory_graph=FALSE, 
           label_cell_groups=FALSE)
```

Example 96 (unknown):
```unknown
cds_subset <- cluster_cells(cds_subset, resolution=1e-2)
plot_cells(cds_subset, color_cells_by="cluster")
```

Example 97 (r):
```r
cds_subset <- cluster_cells(cds_subset, resolution=1e-2)
plot_cells(cds_subset, color_cells_by="cluster")
```

Example 98 (unknown):
```unknown
colData(cds_subset)$assigned_cell_type <- as.character(clusters(cds_subset)[colnames(cds_subset)])
colData(cds_subset)$assigned_cell_type <- dplyr::recode(colData(cds_subset)$assigned_cell_type,
                                                        "1"="Sex myoblasts",
                                                        "2"="Somatic gonad precursors",
                                                        "3"="Vulval precursors",
                                                        "4"="Sex myoblasts",
                                                        "5"="Vulval precursors",
                                                        "6"="Somatic gonad precursors",
                                                        "7"="Sex myoblasts",
                                                        "8"="Sex myoblasts",
                                                        "9"="Ciliated neurons",
                                                        "10"="Vulval precursors",
                                                        "11"="Somatic gonad precursor",
                                                        "12"="Distal tip cells",
                                                        "13"="Somatic gonad precursor",
                                                        "14"="Sex myoblasts",
                                                        "15"="Vulval precursors")

plot_cells(cds_subset, group_cells_by="cluster", color_cells_by="assigned_cell_type")
```

Example 99 (r):
```r
colData(cds_subset)$assigned_cell_type <- as.character(clusters(cds_subset)[colnames(cds_subset)])
colData(cds_subset)$assigned_cell_type <- dplyr::recode(colData(cds_subset)$assigned_cell_type,
                                                        "1"="Sex myoblasts",
                                                        "2"="Somatic gonad precursors",
                                                        "3"="Vulval precursors",
                                                        "4"="Sex myoblasts",
                                                        "5"="Vulval precursors",
                                                        "6"="Somatic gonad precursors",
                                                        "7"="Sex myoblasts",
                                                        "8"="Sex myoblasts",
                                                        "9"="Ciliated neurons",
                                                        "10"="Vulval precursors",
                                                        "11"="Somatic gonad precursor",
                                                        "12"="Distal tip cells",
                                                        "13"="Somatic gonad precursor",
                                                        "14"="Sex myoblasts",
                                                        "15"="Vulval precursors")

plot_cells(cds_subset, group_cells_by="cluster", color_cells_by="assigned_cell_type")
```

Example 100 (unknown):
```unknown
colData(cds)[colnames(cds_subset),]$assigned_cell_type <- colData(cds_subset)$assigned_cell_type
cds <- cds[,colData(cds)$assigned_cell_type != "Failed QC" | is.na(colData(cds)$assigned_cell_type )]
plot_cells(cds, group_cells_by="partition", 
           color_cells_by="assigned_cell_type", 
           labels_per_group=5)
```

Example 101 (r):
```r
colData(cds)[colnames(cds_subset),]$assigned_cell_type <- colData(cds_subset)$assigned_cell_type
cds <- cds[,colData(cds)$assigned_cell_type != "Failed QC" | is.na(colData(cds)$assigned_cell_type )]
plot_cells(cds, group_cells_by="partition", 
           color_cells_by="assigned_cell_type", 
           labels_per_group=5)
```

Example 102 (unknown):
```unknown
assigned_type_marker_test_res <- top_markers(cds,
                                             group_cells_by="assigned_cell_type",
                                             reference_cells=1000,
                                             cores=8)
```

Example 103 (r):
```r
assigned_type_marker_test_res <- top_markers(cds,
                                             group_cells_by="assigned_cell_type",
                                             reference_cells=1000,
                                             cores=8)
```

Example 104 (unknown):
```unknown
# Require that markers have at least JS specificty score > 0.5 and
# be significant in the logistic test for identifying their cell type:
garnett_markers <- assigned_type_marker_test_res %>%
                        filter(marker_test_q_value < 0.01 & specificity >= 0.5) %>%
                        group_by(cell_group) %>%
                        top_n(5, marker_score)
# Exclude genes that are good markers for more than one cell type:
garnett_markers <- garnett_markers %>% 
                        group_by(gene_short_name) %>%
                        filter(n() == 1)
```

Example 105 (r):
```r
# Require that markers have at least JS specificty score > 0.5 and
# be significant in the logistic test for identifying their cell type:
garnett_markers <- assigned_type_marker_test_res %>%
                        filter(marker_test_q_value < 0.01 & specificity >= 0.5) %>%
                        group_by(cell_group) %>%
                        top_n(5, marker_score)
# Exclude genes that are good markers for more than one cell type:
garnett_markers <- garnett_markers %>% 
                        group_by(gene_short_name) %>%
                        filter(n() == 1)
```

Example 106 (unknown):
```unknown
generate_garnett_marker_file
```

Example 107 (unknown):
```unknown
generate_garnett_marker_file(garnett_markers, file="./marker_file.txt")
```

Example 108 (r):
```r
generate_garnett_marker_file(garnett_markers, file="./marker_file.txt")
```

Example 109 (unknown):
```unknown
generate_garnett_marker_file
```

Example 110 (unknown):
```unknown
> Cell type Ciliated sensory neurons
expressed: che-3, scd-2, C33A12.4, R102.2, F27C1.11

> Cell type Non-seam hypodermis
expressed: col-14, col-180, F11E6.3, grsp-1, C06A8.3

> Cell type Seam cells
expressed: col-65, col-77, col-107, ram-2, Y47D7A.13

> Cell type Vulval precursors
expressed: col-68, col-145, lin-31, osm-11, Y62E10A.19

> Cell type Body wall muscle
expressed: csq-1, hum-9, cpna-2, tag-278, F41C3.5

> Cell type Coelomocytes
expressed: cup-4, inos-1, Y73F4A.1, ZC116.3, aman-1

> Cell type flp-1 interneurons
expressed: daf-10, flp-1, nlp-10, zig-2, H05L03.3

> Cell type Sex myoblasts
expressed: egl-15, C04E12.2

> Cell type Intestinal/rectal muscle
expressed: egl-20, lbp-2, bgal-1, ttr-10, T23B12.8

> Cell type Am/PH sheath cells
expressed: far-8, F35B12.9, ZK822.4, F20A1.1, T02B11.3

> Cell type Oxygen sensory neurons
expressed: flp-17, gcy-9, gcy-33, ist-1, Y57G11B.97

> Cell type Pharyngeal neurons
expressed: flr-2, nlp-6, F14B6.2, degt-1, flp-28

> Cell type Unclassified neurons
expressed: gar-2, madd-4, twk-49

> Cell type Germline
expressed: gld-1, pgl-1, ppw-2, prg-2, cbd-1

> Cell type Somatic gonad precursors
expressed: inx-9, mnm-2, C36B7.4

> Cell type Touch receptor neurons
expressed: mec-1, mec-7, mec-12, mec-17, mec-18

> Cell type Pharyngeal epithelia
expressed: pgp-14, pqn-74, fipr-2, R03C1.1, Y73F4A.2

> Cell type Pharyngeal muscle
expressed: pqn-29, F31D4.5, R13H4.8, T01B7.8, T20B6.3

> Cell type Pharyngeal gland
expressed: F15A4.6, dod-6, C49G7.3, M04G7.1, phat-4

> Cell type Canal associated neurons
expressed: acbp-6, Y66D12A.14, ZC412.4, C32E8.6, C41A3.1
```

Example 111 (console):
```console
> Cell type Ciliated sensory neurons
expressed: che-3, scd-2, C33A12.4, R102.2, F27C1.11

> Cell type Non-seam hypodermis
expressed: col-14, col-180, F11E6.3, grsp-1, C06A8.3

> Cell type Seam cells
expressed: col-65, col-77, col-107, ram-2, Y47D7A.13

> Cell type Vulval precursors
expressed: col-68, col-145, lin-31, osm-11, Y62E10A.19

> Cell type Body wall muscle
expressed: csq-1, hum-9, cpna-2, tag-278, F41C3.5

> Cell type Coelomocytes
expressed: cup-4, inos-1, Y73F4A.1, ZC116.3, aman-1

> Cell type flp-1 interneurons
expressed: daf-10, flp-1, nlp-10, zig-2, H05L03.3

> Cell type Sex myoblasts
expressed: egl-15, C04E12.2

> Cell type Intestinal/rectal muscle
expressed: egl-20, lbp-2, bgal-1, ttr-10, T23B12.8

> Cell type Am/PH sheath cells
expressed: far-8, F35B12.9, ZK822.4, F20A1.1, T02B11.3

> Cell type Oxygen sensory neurons
expressed: flp-17, gcy-9, gcy-33, ist-1, Y57G11B.97

> Cell type Pharyngeal neurons
expressed: flr-2, nlp-6, F14B6.2, degt-1, flp-28

> Cell type Unclassified neurons
expressed: gar-2, madd-4, twk-49

> Cell type Germline
expressed: gld-1, pgl-1, ppw-2, prg-2, cbd-1

> Cell type Somatic gonad precursors
expressed: inx-9, mnm-2, C36B7.4

> Cell type Touch receptor neurons
expressed: mec-1, mec-7, mec-12, mec-17, mec-18

> Cell type Pharyngeal epithelia
expressed: pgp-14, pqn-74, fipr-2, R03C1.1, Y73F4A.2

> Cell type Pharyngeal muscle
expressed: pqn-29, F31D4.5, R13H4.8, T01B7.8, T20B6.3

> Cell type Pharyngeal gland
expressed: F15A4.6, dod-6, C49G7.3, M04G7.1, phat-4

> Cell type Canal associated neurons
expressed: acbp-6, Y66D12A.14, ZC412.4, C32E8.6, C41A3.1
```

Example 112 (unknown):
```unknown
generate_garnett_marker_file()
```

Example 113 (unknown):
```unknown
plot_genes_by_group()
```

Example 114 (unknown):
```unknown
top_markers()
```

Example 115 (unknown):
```unknown
## Install the monocle3 branch of garnett
BiocManager::install(c("org.Mm.eg.db", "org.Hs.eg.db"))
devtools::install_github("cole-trapnell-lab/garnett", ref="monocle3")
```

Example 116 (r):
```r
## Install the monocle3 branch of garnett
BiocManager::install(c("org.Mm.eg.db", "org.Hs.eg.db"))
devtools::install_github("cole-trapnell-lab/garnett", ref="monocle3")
```

Example 117 (unknown):
```unknown
library(garnett)
# install gene database for worm
BiocManager::install("org.Ce.eg.db")
```

Example 118 (r):
```r
library(garnett)
# install gene database for worm
BiocManager::install("org.Ce.eg.db")
```

Example 119 (unknown):
```unknown
colData(cds)$garnett_cluster <- clusters(cds)
worm_classifier <- train_cell_classifier(cds = cds,
                                         marker_file = "./marker_file.txt", 
                                         db=org.Ce.eg.db::org.Ce.eg.db,
                                         cds_gene_id_type = "ENSEMBL",
                                         num_unknown = 50,
                                         marker_file_gene_id_type = "SYMBOL",
                                         cores=8)
```

Example 120 (r):
```r
colData(cds)$garnett_cluster <- clusters(cds)
worm_classifier <- train_cell_classifier(cds = cds,
                                         marker_file = "./marker_file.txt", 
                                         db=org.Ce.eg.db::org.Ce.eg.db,
                                         cds_gene_id_type = "ENSEMBL",
                                         num_unknown = 50,
                                         marker_file_gene_id_type = "SYMBOL",
                                         cores=8)
```

Example 121 (unknown):
```unknown
worm_classifier
```

Example 122 (unknown):
```unknown
cds <- classify_cells(cds, worm_classifier,
                      db = org.Ce.eg.db::org.Ce.eg.db,
                      cluster_extend = TRUE,
                      cds_gene_id_type = "ENSEMBL")
```

Example 123 (r):
```r
cds <- classify_cells(cds, worm_classifier,
                      db = org.Ce.eg.db::org.Ce.eg.db,
                      cluster_extend = TRUE,
                      cds_gene_id_type = "ENSEMBL")
```

Example 124 (unknown):
```unknown
plot_cells(cds,
           group_cells_by="partition",
           color_cells_by="cluster_ext_type")
```

Example 125 (r):
```r
plot_cells(cds,
           group_cells_by="partition",
           color_cells_by="cluster_ext_type")
```

Example 126 (unknown):
```unknown
classify_cells()
```

Example 127 (unknown):
```unknown
ceWhole <- readRDS(url("https://cole-trapnell-lab.github.io/garnett/classifiers/ceWhole_20191017.RDS"))
cds <- classify_cells(cds, ceWhole,
                      db = org.Ce.eg.db,
                      cluster_extend = TRUE,
                      cds_gene_id_type = "ENSEMBL")
```

Example 128 (r):
```r
ceWhole <- readRDS(url("https://cole-trapnell-lab.github.io/garnett/classifiers/ceWhole_20191017.RDS"))
cds <- classify_cells(cds, ceWhole,
                      db = org.Ce.eg.db,
                      cluster_extend = TRUE,
                      cds_gene_id_type = "ENSEMBL")
```

---

## Monocle 3

**URL:** http://127.0.0.1:9130/monocle3/docs/getting_started/index.html

**Contents:**
- Getting started with Monocle 3
  - Workflow steps at a glance
    - Store data in a cell_data_set object
    - Optional Remove batch effects
    - Cluster your cells
    - Optional Order cells in pseudotime along a trajectory
    - Optional Perform differential expression analysis
- Get started
  - Load Monocle 3
  - Loading your data
  - The cell_data_set class
  - Required dimensions for input files
    - Generate a cell_data_set
  - Generate a cell_data_set from 10X output
  - Working with large data sets
  - Don't accidentally convert to a dense expression matrix
  - Combining CDS objects
    - Options

Below, you can see snippets of code that highlight the main steps of Monocle 3. Click on the section headers to jump to the detailed sections describing each one and allowing you to try the steps on example data.

expression_matrix, a numeric matrix of expression values, where rows are genes, and columns are cells cell_metadata, a data frame, where rows are cells, and columns are cell attributes (such as cell type, culture condition, day captured, etc.) gene_metadata, an data frame, where rows are features (e.g. genes), and columns are gene attributes, such as biotype, gc content, etc.

You can create a new cell_data_set (CDS) object as follows:

# Load the data expression_matrix <- readRDS(url("https://depts.washington.edu:/trapnell-lab/software/monocle3/celegans/data/cao_l2_expression.rds")) cell_metadata <- readRDS(url("https://depts.washington.edu:/trapnell-lab/software/monocle3/celegans/data/cao_l2_colData.rds")) gene_annotation <- readRDS(url("https://depts.washington.edu:/trapnell-lab/software/monocle3/celegans/data/cao_l2_rowData.rds")) # Make the CDS object cds <- new_cell_data_set(expression_matrix, cell_metadata = cell_metadata, gene_metadata = gene_annotation)

To input data from 10X Genomics Cell Ranger, you can use the load_cellranger_data function:

Note: load_cellranger_data takes an argument umi_cutoff that determines how many reads a cell must have to be included. By default, this is set to 100. If you would like to include all cells, set umi_cutoff to 0.

For load_cellranger_data to find the correct files, you must provide a path to the folder containing the un-modified Cell Ranger 'outs' folder. Your file structure should look like: 10x_data/outs/filtered_feature_bc_matrix/ where filtered_feature_bc_matrix contains files features.tsv.gz, barcodes.tsv.gz and matrix.mtx.gz. (load_cellranger_data can also handle Cell Ranger V2 data where "features" is substituted for "gene" and the files are not gzipped.)

Alternatively, you can use load_mm_data to load any data in MatrixMarket format by providing the matrix files and two metadata files (features information and cell information). For more details, run ?load_mm_data

Some single-cell RNA-Seq experiments report measurements from tens of thousands of cells or more. As instrumentation improves and costs drop, experiments will become ever larger and more complex, with many conditions, controls, and replicates. A matrix of expression data with 50,000 cells and a measurement for each of the 25,000+ genes in the human genome can take up a lot of memory. However, because current protocols typically don't capture all or even most of the mRNA molecules in each cell, many of the entries of expression matrices are zero. Using sparse matrices can help you work with huge datasets on a typical computer. We generally recommend the use of sparse matrices for most users, as it speeds up many computations even for more modestly sized datasets.

To work with your data in a sparse format, simply provide it to Monocle 3 as a sparse matrix from the Matrix package:

cds <- new_cell_data_set(as(umi_matrix, "sparseMatrix"), cell_metadata = cell_metadata, gene_metadata = gene_metadata)

Don't accidentally convert to a dense expression matrix The output from a number of RNA-Seq pipelines, including Cell Ranger, is already in a sparseMatrix format (e.g. MTX). If so, you should just pass it directly to new_cell_data_set without first converting it to a dense matrix (via as.matrix(), because that may exceed your available memeory.

If you have multiple CDS objects that you would like to analyze together, use our combine_cds. combine_cds takes a list of CDS objects and combines them into a single CDS object.

keep_all_genes: When TRUE (default), all genes are kept even if they don't match between the different CDSs. Cells that do not have a given gene in their CDS will be marked as having zero expression. When FALSE, only the genes in common among all CDSs will be kept.

cell_names_unique: When FALSE (default), the cell names in the CDSs are not assumed to be unique, and so a CDS specifier is appended to each cell name. When TRUE, no specifier is added.

**Examples:**

Example 1 (unknown):
```unknown
cell_data_set
```

Example 2 (python):
```python
cds <- new_cell_data_set(expression_matrix,
                         cell_metadata = cell_metadata,
                         gene_metadata = gene_annotation)

## Step 1: Normalize and pre-process the data
cds <- preprocess_cds(cds, num_dim = 100)
```

Example 3 (r):
```r
cds <- new_cell_data_set(expression_matrix,
                         cell_metadata = cell_metadata,
                         gene_metadata = gene_annotation)

## Step 1: Normalize and pre-process the data
cds <- preprocess_cds(cds, num_dim = 100)
```

Example 4 (unknown):
```unknown
## Step 2: Remove batch effects with cell alignment
cds <- align_cds(cds, alignment_group = "batch")
```

Example 5 (r):
```r
## Step 2: Remove batch effects with cell alignment
cds <- align_cds(cds, alignment_group = "batch")
```

Example 6 (unknown):
```unknown
## Step 3: Reduce the dimensions using UMAP
cds <- reduce_dimension(cds)

## Step 4: Cluster the cells
cds <- cluster_cells(cds)
```

Example 7 (r):
```r
## Step 3: Reduce the dimensions using UMAP
cds <- reduce_dimension(cds)

## Step 4: Cluster the cells
cds <- cluster_cells(cds)
```

Example 8 (unknown):
```unknown
## Step 5: Learn a graph
cds <- learn_graph(cds)

## Step 6: Order cells
cds <- order_cells(cds)

plot_cells(cds)
```

Example 9 (r):
```r
## Step 5: Learn a graph
cds <- learn_graph(cds)

## Step 6: Order cells
cds <- order_cells(cds)

plot_cells(cds)
```

Example 10 (unknown):
```unknown
# With regression:
gene_fits <- fit_models(cds, model_formula_str = "~embryo.time")
fit_coefs <- coefficient_table(gene_fits)
emb_time_terms <- fit_coefs %>% filter(term == "embryo.time")
emb_time_terms <- emb_time_terms %>% mutate(q_value = p.adjust(p_value))
sig_genes <- emb_time_terms %>% filter (q_value < 0.05) %>% pull(gene_short_name)

# With graph autocorrelation:
pr_test_res <- graph_test(cds,  neighbor_graph="principal_graph", cores=4)
pr_deg_ids <- row.names(subset(pr_test_res, q_value < 0.05))
```

Example 11 (r):
```r
# With regression:
gene_fits <- fit_models(cds, model_formula_str = "~embryo.time")
fit_coefs <- coefficient_table(gene_fits)
emb_time_terms <- fit_coefs %>% filter(term == "embryo.time")
emb_time_terms <- emb_time_terms %>% mutate(q_value = p.adjust(p_value))
sig_genes <- emb_time_terms %>% filter (q_value < 0.05) %>% pull(gene_short_name)

# With graph autocorrelation:
pr_test_res <- graph_test(cds,  neighbor_graph="principal_graph", cores=4)
pr_deg_ids <- row.names(subset(pr_test_res, q_value < 0.05))
```

Example 12 (unknown):
```unknown
library(monocle3)

# The tutorial shown below and on subsequent pages uses two additional packages:
library(ggplot2)
library(dplyr)
```

Example 13 (r):
```r
library(monocle3)

# The tutorial shown below and on subsequent pages uses two additional packages:
library(ggplot2)
library(dplyr)
```

Example 14 (unknown):
```unknown
cell_data_set
```

Example 15 (unknown):
```unknown
SingleCellExperiment
```

Example 16 (unknown):
```unknown
expression_matrix
```

Example 17 (python):
```python
cell_metadata
```

Example 18 (python):
```python
gene_metadata
```

Example 19 (python):
```python
cell_metadata
```

Example 20 (python):
```python
gene_metadata
```

Example 21 (python):
```python
cell_metadata
```

Example 22 (python):
```python
gene_metadata
```

Example 23 (python):
```python
gene_metadata
```

Example 24 (unknown):
```unknown
cell_data_set
```

Example 25 (python):
```python
# Load the data
expression_matrix <- readRDS(url("https://depts.washington.edu:/trapnell-lab/software/monocle3/celegans/data/cao_l2_expression.rds"))
cell_metadata <- readRDS(url("https://depts.washington.edu:/trapnell-lab/software/monocle3/celegans/data/cao_l2_colData.rds"))
gene_annotation <- readRDS(url("https://depts.washington.edu:/trapnell-lab/software/monocle3/celegans/data/cao_l2_rowData.rds"))


# Make the CDS object
cds <- new_cell_data_set(expression_matrix,
                         cell_metadata = cell_metadata,
                         gene_metadata = gene_annotation)
```

Example 26 (r):
```r
# Load the data
expression_matrix <- readRDS(url("https://depts.washington.edu:/trapnell-lab/software/monocle3/celegans/data/cao_l2_expression.rds"))
cell_metadata <- readRDS(url("https://depts.washington.edu:/trapnell-lab/software/monocle3/celegans/data/cao_l2_colData.rds"))
gene_annotation <- readRDS(url("https://depts.washington.edu:/trapnell-lab/software/monocle3/celegans/data/cao_l2_rowData.rds"))


# Make the CDS object
cds <- new_cell_data_set(expression_matrix,
                         cell_metadata = cell_metadata,
                         gene_metadata = gene_annotation)
```

Example 27 (unknown):
```unknown
load_cellranger_data
```

Example 28 (unknown):
```unknown
load_cellranger_data
```

Example 29 (unknown):
```unknown
load_cellranger_data
```

Example 30 (unknown):
```unknown
load_cellranger_data
```

Example 31 (unknown):
```unknown
# Provide the path to the Cell Ranger output.
cds <- load_cellranger_data("~/Downloads/10x_data")
```

Example 32 (r):
```r
# Provide the path to the Cell Ranger output.
cds <- load_cellranger_data("~/Downloads/10x_data")
```

Example 33 (unknown):
```unknown
load_mm_data
```

Example 34 (unknown):
```unknown
?load_mm_data
```

Example 35 (unknown):
```unknown
cds <- load_mm_data(mat_path = "~/Downloads/matrix.mtx", 
                    feature_anno_path = "~/Downloads/features.tsv", 
                    cell_anno_path = "~/Downloads/barcodes.tsv")
```

Example 36 (r):
```r
cds <- load_mm_data(mat_path = "~/Downloads/matrix.mtx", 
                    feature_anno_path = "~/Downloads/features.tsv", 
                    cell_anno_path = "~/Downloads/barcodes.tsv")
```

Example 37 (python):
```python
cds <- new_cell_data_set(as(umi_matrix, "sparseMatrix"),
cell_metadata = cell_metadata,
gene_metadata = gene_metadata)
```

Example 38 (r):
```r
cds <- new_cell_data_set(as(umi_matrix, "sparseMatrix"),
cell_metadata = cell_metadata,
gene_metadata = gene_metadata)
```

Example 39 (unknown):
```unknown
new_cell_data_set
```

Example 40 (unknown):
```unknown
as.matrix()
```

Example 41 (unknown):
```unknown
combine_cds
```

Example 42 (unknown):
```unknown
combine_cds
```

Example 43 (unknown):
```unknown
# make a fake second cds object for demonstration
cds2 <- cds[1:100,]

big_cds <- combine_cds(list(cds, cds2))
```

Example 44 (r):
```r
# make a fake second cds object for demonstration
cds2 <- cds[1:100,]

big_cds <- combine_cds(list(cds, cds2))
```

Example 45 (unknown):
```unknown
keep_all_genes
```

Example 46 (unknown):
```unknown
cell_names_unique
```

---

## Monocle 3

**URL:** http://127.0.0.1:9130/monocle3/papers/index.html

**Contents:**
  - Monocle is an ongoing research project as well as a toolkit. If you use Monocle, please cite these papers in your work!
  - The dynamics and regulators of cell fate decisions are revealed by pseudotemporal ordering of single cells
  - Single-cell mRNA quantification and differential analysis with Census
  - Reversed graph embedding resolves complex single-cell trajectories
  - The single-cell transcriptional landscape of mammalian organogenesis

Cole Trapnell*, Davide Cacchiarelli*, Jonna Grimsby, Prapti Pokharel, Shuqiang Li, Michael Morse, Niall J. Lennon, Kenneth J. Livak, Tarjei S. Mikkelsen, John L. Rinn. Nature Biotechnology 2014 Defining the transcriptional dynamics of a temporal process such as cell differentiation is challenging owing to the high variability in gene expression between individual cells. Time-series gene expression analyses of bulk cells have difficulty distinguishing early and late phases of a transcriptional cascade or identifying rare subpopulations of cells, and single-cell proteomic methods rely on a priori knowledge of key distinguishing markers. Here we describe Monocle, an unsupervised algorithm that increases the temporal resolution of transcriptome dynamics using single-cell RNA-Seq data collected at multiple time points. Applied to the differentiation of primary human myoblasts, Monocle revealed switch-like changes in expression of key regulatory factors, sequential waves of gene regulation, and expression of regulators that were not known to act in differentiation. We validated some of these predicted regulators in a loss-of function screen. Monocle can in principle be used to recover single-cell gene expression kinetics from a wide array of cellular processes, including differentiation, proliferation and oncogenic transformation This is the original Monocle paper, which introduced the concept of pseudotime ordering for single-cell analysis HTML PDF

Nature Biotechnology 2014 Defining the transcriptional dynamics of a temporal process such as cell differentiation is challenging owing to the high variability in gene expression between individual cells. Time-series gene expression analyses of bulk cells have difficulty distinguishing early and late phases of a transcriptional cascade or identifying rare subpopulations of cells, and single-cell proteomic methods rely on a priori knowledge of key distinguishing markers. Here we describe Monocle, an unsupervised algorithm that increases the temporal resolution of transcriptome dynamics using single-cell RNA-Seq data collected at multiple time points. Applied to the differentiation of primary human myoblasts, Monocle revealed switch-like changes in expression of key regulatory factors, sequential waves of gene regulation, and expression of regulators that were not known to act in differentiation. We validated some of these predicted regulators in a loss-of function screen. Monocle can in principle be used to recover single-cell gene expression kinetics from a wide array of cellular processes, including differentiation, proliferation and oncogenic transformation This is the original Monocle paper, which introduced the concept of pseudotime ordering for single-cell analysis HTML PDF

Defining the transcriptional dynamics of a temporal process such as cell differentiation is challenging owing to the high variability in gene expression between individual cells. Time-series gene expression analyses of bulk cells have difficulty distinguishing early and late phases of a transcriptional cascade or identifying rare subpopulations of cells, and single-cell proteomic methods rely on a priori knowledge of key distinguishing markers. Here we describe Monocle, an unsupervised algorithm that increases the temporal resolution of transcriptome dynamics using single-cell RNA-Seq data collected at multiple time points. Applied to the differentiation of primary human myoblasts, Monocle revealed switch-like changes in expression of key regulatory factors, sequential waves of gene regulation, and expression of regulators that were not known to act in differentiation. We validated some of these predicted regulators in a loss-of function screen. Monocle can in principle be used to recover single-cell gene expression kinetics from a wide array of cellular processes, including differentiation, proliferation and oncogenic transformation This is the original Monocle paper, which introduced the concept of pseudotime ordering for single-cell analysis HTML PDF

This is the original Monocle paper, which introduced the concept of pseudotime ordering for single-cell analysis HTML PDF

Xiaojie Qiu, Andrew Hill, Jonathan Packer, Dejun Lin, Yi-An Ma, Cole Trapnell Nature Methods 2017 Single-cell gene expression studies promise to reveal rare cell types and cryptic states, but the high variability of single-cell RNA-seq measurements frustrates efforts to assay transcriptional differences between cells. We introduce the Census algorithm to convert relative RNA-seq expression levels into relative transcript counts without the need for experimental spike-in controls. Analyzing changes in relative transcript counts led to dramatic improvements in accuracy compared to normalized read counts and enabled new statistical tests for identifying developmentally regulated genes. Census counts can be analyzed with widely used regression techniques to reveal changes in cell-fate-dependent gene expression, splicing patterns and allelic imbalances. We reanalyzed single-cell data from several developmental and disease studies, and demonstrate that Census enabled robust analysis at multiple layers of gene regulation. Census is freely available through our updated single-cell analysis toolkit, Monocle 2. This paper describes BEAM (used in branch analysis) and Census (the core of relative2abs) HTML PDF

Nature Methods 2017 Single-cell gene expression studies promise to reveal rare cell types and cryptic states, but the high variability of single-cell RNA-seq measurements frustrates efforts to assay transcriptional differences between cells. We introduce the Census algorithm to convert relative RNA-seq expression levels into relative transcript counts without the need for experimental spike-in controls. Analyzing changes in relative transcript counts led to dramatic improvements in accuracy compared to normalized read counts and enabled new statistical tests for identifying developmentally regulated genes. Census counts can be analyzed with widely used regression techniques to reveal changes in cell-fate-dependent gene expression, splicing patterns and allelic imbalances. We reanalyzed single-cell data from several developmental and disease studies, and demonstrate that Census enabled robust analysis at multiple layers of gene regulation. Census is freely available through our updated single-cell analysis toolkit, Monocle 2. This paper describes BEAM (used in branch analysis) and Census (the core of relative2abs) HTML PDF

Single-cell gene expression studies promise to reveal rare cell types and cryptic states, but the high variability of single-cell RNA-seq measurements frustrates efforts to assay transcriptional differences between cells. We introduce the Census algorithm to convert relative RNA-seq expression levels into relative transcript counts without the need for experimental spike-in controls. Analyzing changes in relative transcript counts led to dramatic improvements in accuracy compared to normalized read counts and enabled new statistical tests for identifying developmentally regulated genes. Census counts can be analyzed with widely used regression techniques to reveal changes in cell-fate-dependent gene expression, splicing patterns and allelic imbalances. We reanalyzed single-cell data from several developmental and disease studies, and demonstrate that Census enabled robust analysis at multiple layers of gene regulation. Census is freely available through our updated single-cell analysis toolkit, Monocle 2. This paper describes BEAM (used in branch analysis) and Census (the core of relative2abs) HTML PDF

This paper describes BEAM (used in branch analysis) and Census (the core of relative2abs) HTML PDF

Xiaojie Qiu, Qi Mao, Ying Tang, Li Wang, Raghav Chawla, Hannah Pliner, Cole Trapnell Nature Methods 2017 Single-cell trajectories can unveil how gene regulation governs cell fate decisions. However, learning the structure of complex trajectories with multiple branches remains a challenging computational problem. We present Monocle 2, an algorithm that uses reversed graph embedding to describe multiple fate decisions in a fully unsupervised manner. We applied Monocle 2 to two studies of blood development and found that mutations in the genes encoding key lineage transcription factors divert cells to alternative fates. This paper describes Monocle 2 and the use of Reversed Graph Embedding for single-cell analysis. HTML PDF

Nature Methods 2017 Single-cell trajectories can unveil how gene regulation governs cell fate decisions. However, learning the structure of complex trajectories with multiple branches remains a challenging computational problem. We present Monocle 2, an algorithm that uses reversed graph embedding to describe multiple fate decisions in a fully unsupervised manner. We applied Monocle 2 to two studies of blood development and found that mutations in the genes encoding key lineage transcription factors divert cells to alternative fates. This paper describes Monocle 2 and the use of Reversed Graph Embedding for single-cell analysis. HTML PDF

Single-cell trajectories can unveil how gene regulation governs cell fate decisions. However, learning the structure of complex trajectories with multiple branches remains a challenging computational problem. We present Monocle 2, an algorithm that uses reversed graph embedding to describe multiple fate decisions in a fully unsupervised manner. We applied Monocle 2 to two studies of blood development and found that mutations in the genes encoding key lineage transcription factors divert cells to alternative fates. This paper describes Monocle 2 and the use of Reversed Graph Embedding for single-cell analysis. HTML PDF

This paper describes Monocle 2 and the use of Reversed Graph Embedding for single-cell analysis. HTML PDF

Junyue Cao, Malte Spielmann, Xiaojie Qiu, Xingfan Huang, Daniel M. Ibrahim, Andrew J. Hill, Fan Zhang, Stefan Mundlos, Lena Christiansen, Frank J. Steemers, Cole Trapnell, and Jay Shendure Nature 2019 Mammalian organogenesis is a remarkable process. Within a short timeframe, the cells of the three germ layers transform into an embryo that includes most of the major internal and external organs. Here we investigate the transcriptional dynamics of mouse organogenesis at single-cell resolution. Using single-cell combinatorial indexing, we profiled the transcriptomes of around 2 million cells derived from 61 embryos staged between 9.5 and 13.5 days of gestation, in a single experiment. The resulting ‘mouse organogenesis cell atlas’ (MOCA) provides a global view of developmental processes during this critical window. We use Monocle 3 to identify hundreds of cell types and 56 trajectories, many of which are detected only because of the depth of cellular coverage, and collectively define thousands of corresponding marker genes. We explore the dynamics of gene expression within cell types and trajectories over time, including focused analyses of the apical ectodermal ridge, limb mesenchyme and skeletal muscle. HTML PDF

Nature 2019 Mammalian organogenesis is a remarkable process. Within a short timeframe, the cells of the three germ layers transform into an embryo that includes most of the major internal and external organs. Here we investigate the transcriptional dynamics of mouse organogenesis at single-cell resolution. Using single-cell combinatorial indexing, we profiled the transcriptomes of around 2 million cells derived from 61 embryos staged between 9.5 and 13.5 days of gestation, in a single experiment. The resulting ‘mouse organogenesis cell atlas’ (MOCA) provides a global view of developmental processes during this critical window. We use Monocle 3 to identify hundreds of cell types and 56 trajectories, many of which are detected only because of the depth of cellular coverage, and collectively define thousands of corresponding marker genes. We explore the dynamics of gene expression within cell types and trajectories over time, including focused analyses of the apical ectodermal ridge, limb mesenchyme and skeletal muscle. HTML PDF

Mammalian organogenesis is a remarkable process. Within a short timeframe, the cells of the three germ layers transform into an embryo that includes most of the major internal and external organs. Here we investigate the transcriptional dynamics of mouse organogenesis at single-cell resolution. Using single-cell combinatorial indexing, we profiled the transcriptomes of around 2 million cells derived from 61 embryos staged between 9.5 and 13.5 days of gestation, in a single experiment. The resulting ‘mouse organogenesis cell atlas’ (MOCA) provides a global view of developmental processes during this critical window. We use Monocle 3 to identify hundreds of cell types and 56 trajectories, many of which are detected only because of the depth of cellular coverage, and collectively define thousands of corresponding marker genes. We explore the dynamics of gene expression within cell types and trajectories over time, including focused analyses of the apical ectodermal ridge, limb mesenchyme and skeletal muscle. HTML PDF

**Examples:**

Example 1 (unknown):
```unknown
relative2abs
```

---

## Monocle 3

**URL:** http://127.0.0.1:9130/monocle3/index.html

**Contents:**
- Monocle 3
- Trajectories
- Clustering
- Differential expression
- Classify and count cells.
- Identify new marker genes.
- Robustly track changes over (pseudo) time.
- Dissect cellular decisions with branch analysis.

An analysis toolkit for single-cell RNA-seq.

Build single-cell trajectories with the software that introduced pseudotime. Find cell fate decisions and the genes regulated as they're made.

Group and classify your cells based on gene expression. Identify new cell types and states and the genes that distinguish them.

Find genes that vary between cell types and states, over trajectories, or in response to perturbations using statistically robust, flexible differential analysis.

Single-cell RNA-Seq experiments allow you to discover (and possibly rare) subtypes of cells. Monocle 3 helps you identify them.

Many researchers are using single-cell RNA-Seq to discover new cell types. Monocle 3 can help you purify them or characterize them further by identifying key marker genes that you can use in follow up experiments such as immunofluorescence or flow sorting.

In development, disease, and throughout life, cells transition from one state to another. Monocle introduced the concept of pseudotime, which is a measure of how far a cell has moved through biological progress.

Single-cell trajectory analysis how cells choose between one of several possible end states. The new reconstruction algorithms introduced in Monocle 3 can robustly reveal branching trajectories, along with the genes that cells use to navigate these decisions.

---

## Monocle 3

**URL:** http://127.0.0.1:9130/monocle3/docs/cicero/index.html

**Contents:**
- Monocle 3 and Cicero for single-cell ATAC-seq data

For users who would like to analyze single-cell ATAC-seq data, we have a companion R package called Cicero. Cicero adapts the analyses of Monocle 3 and also allows the prediction of cis-regulatory interactions from single-cell chromatin accessibility. Details about Cicero are available on the Cicero website.

---

## Monocle 3

**URL:** http://127.0.0.1:9130/monocle3/docs/updates/index.html

**Contents:**
- Major updates in Monocle 3

Monocle 3 has been re-engineered to analyze large, complex single-cell datasets. The algorithms at the core of Monocle 3 are highly scalable and can handle millions of cells. Monocle 3 adds some powerful new features that enable the analysis of organism- or embryo-scale experiments:

Most of the algorithmic details in Monocle 3 are described in Cao & Spielmann et al.

**Examples:**

Example 1 (unknown):
```unknown
differentialGeneTest()
```

Example 2 (unknown):
```unknown
$HOME/.monoclerc
```

---

## Monocle 3

**URL:** http://127.0.0.1:9130/monocle3/docs/differential/index.html

**Contents:**
- Differential expression analysis
  - Regression analysis
  - Controlling for batch effects and other factors
  - Evaluating models of gene expression
  - Choosing a distribution for modeling gene expression
  - Likelihood based analysis and quasipoisson
  - Graph-autocorrelation analysis for comparing clusters
  - Finding modules of co-regulated genes
  - Finding genes that change as a function of pseudotime
  - Analyzing branches in single-cell trajectories

Differential gene expression analysis is a common task in RNA-Seq experiments. Monocle can help you find genes that are differentially expressed between groups of cells and assesses the statistical signficance of those changes. Monocle 3 includes a powerful system for finding genes that vary across cells of different types, were collected at different developmental time points, or that have been perturbed in different ways.

There are two approaches for differential analysis in Monocle:

Monocle also comes with specialized functions for finding co-regulated modules of differentially expressed genes. Monocle also allows you to interactively interrogate specific clusters or regions of a trajectory (e.g. branch points) for genes that vary within them.

Let's examine these tools in turn.

In this section, we'll explore how to use Monocle to find genes that are differentially expressed according to several different criteria. Performing differential expression analysis on all genes in a cell_data_set object can take anywhere from minutes to hours, depending on how complex the analysis is. To keep the vignette simple and fast, we'll be working with small sets of genes. Rest assured, however, that Monocle can analyze several thousands of genes even in large experiments, making it useful for discovering dynamically regulated genes during the biological process you're studying.

Let's begin with a small set of genes that we know are important in ciliated neurons to demonstrate Monocle's capabilities:

The differential analysis tools in Monocle are extremely flexible. Monocle works by fitting a regression model to each gene. You can specify this model to account for various factors in your experiment (time, treatment, and so on). For example, In the embryo data, the cells were collected at different time points. We can test whether any of the genes above change over time in their expression by first fitting a generalized linear model to each one:

where $y_i$ is a random variable corresponding to the expression values of gene $i$, $x_t$ is the time each cell was collected (in minutes), and the $\beta_t$ capture the effect of time on expression, and $\beta_0$ is an intercept term. We can identify genes that vary over time by fitting this model to each one, and then testing whether its $\beta_t$ is significantly different from zero. To do so, we first call the fit_models() function:

gene_fits is a tibble that contains a row for each gene. The model column contains generalized linear model objects, each of which aims to explain the expression of a gene across the cells using the equation above. The parameter model_formula_str should be a string specifying the model formula. The model formulae you use in your tests can include any term that exists as a column in the colData table, including those columns that are added by Monocle in other analysis steps. For example, if you use cluster_cells, you can test for genes that differ between clusters and partitions by using ~cluster or ~partition (respectively) as your model formula. You can also include multiple variables, for example ~embryo.time + batch, which can be very helpful for subtracting unwanted effects.

Now let's see which of these genes have time-dependent expression. First, we extract a table of coefficients from each model using the coefficient_table() function:

fit_coefs looks like this:

Note that the table includes one row for each term of each gene's model. We generally don't care about the intercept term $\beta_0$, so we can easily just extract the time terms:

Now, let's pull out the genes that have a significant time component. coefficient_table() tests whether each coefficient differs significantly from zero under the Wald test. By default, coefficient_table() adjusts these p-values for multiple hypothesis testing using the method of Benjamini and Hochberg. These adjusted values can be found in the q_value column. We can filter the results and control the false discovery rate as follows:

We can see that five of the six genes significantly vary as a function of time.

Monocle also provides some easy ways to plot the expression of a small set of genes grouped by the factors you use during differential analysis. This helps you visualize the differences revealed by the tests above. One type of plot is a "violin" plot.

By default, the violin plot log-scales the expression, which drops cells with zero expression, resulting in potentially misleading figures. The Monocle3 develop branch has a hybrid plot where cells appear as red dots in a Sina plot and the cell distribution appears as a histogram with green bars and a blue median_qi interval.

How good are these models at "explaining" gene expression? We can evaluate the fits of each model using the evaluate_fits() function:

Should we include the batch term in our model of gene expression or not? Monocle provides a function compare_models() that can help you decide. Compare models takes two models and returns the result of a likelihood ratio test between them. Any time you add terms to a model, it will improve the fit. But we should always to use the simplest model we can to explain our data. The likelihood ratio test helps us decide whether the improvement in fit is large enough to justify the complexity our extra terms introduce. You run compare_models() like this:

The first of the two models is called the full model. This model is essentially a way of predicting the expression value of each gene in a given cell knowing both what time it was collected and which batch of cells it came from. The second model, called the reduced model, does the same thing, but it only knows about the time each cell was collected. Because the full model has more information about each cell, it will do a better job of predicting the expression of the gene in each cell. The question Monocle must answer for each gene is how much better the full model's prediction is than the reduced model's. The greater the improvement that comes from knowing the batch of each cell, the more significant the result of the likelihood ratio test.

As we can see, all of the genes' likelihood ratio tests are significant, indicating that there are substantial batch effects in the data. We are therefore justified in adding the batch term to our model.

Monocle uses generalized linear models to capture how a gene's expression depends on each variable in the experiment. These models require you to specify a distribution that describes gene expression values. Most studies that use this approach to analyze their gene expression data use the negative binomial distribution, which is often appropriate for sequencing read or UMI count data. The negative binomial is at the core of many packages for RNA-seq analysis, such as DESeq2.

Monocle's fit_models() supports the negative binomial distribution and several others listed in the table below. The default is the "quasipoisson", which is very similar to the negative binomial. Quasipoisson is a a bit less accurate than the negative binomial but much faster to fit, making it well suited to datasets with thousands of cells.

There are several allowed values for expression_family:

expression_family Distribution Accuracy Speed Notes quasipoisson Quasi-poisson ++ ++ Default for fit_models(). Recommended for most users. negbinomial Negative binomial +++ + Recommended for users with small datasets (fewer than 1,000 cells). poisson Poisson - +++ Not recommended. For debugging and testing only. binomial Binomial ++ ++ Recommended for single-cell ATAC-seq

Likelihood based analysis and quasipoisson The quasi-poisson distribution doesn't have a real likelihood function, so some of Monocle's methods won't work with it. Several of the columns in results tables from evaluate_fits() and compare_models() will be NA.

In the L2 worm data, we identified a number of clusters that were very distinct as neurons:

Subset just the neurons:

There are many subtypes of neurons, so perhaps the different neuron clusters correspond to different subtypes. To investigate which genes are expressed differentially across the clusters, we could use the regression analysis tools discussed above. However, Monocle provides an alternative way of finding genes that vary between groups of cells in UMAP space. The function graph_test() uses a statistic from spatial autocorrelation analysis called Moran's I, which Cao & Spielmann et al showed to be effective in finding genes that vary in single-cell RNA-seq datasets.

You can run graph_test() like this:

The data frame pr_graph_test_res has the Moran's I test results for each gene in the cell_data_set. If you'd like to rank the genes by effect size, sort this table by the morans_Icolumn, which ranges from -1 to +1. A value of 0 indicates no effect, while +1 indicates perfect positive autocorrelation and suggests that nearby cells have very similar values of a gene's expression. Significant values much less than zero are generally rare.

Positive values indicate a gene is expressed in a focal region of the UMAP space (e.g. specific to one or more clusters). But how do we associate genes with clusters? The next section explains how to collect genes into modules that have similar patterns of expression and associate them with clusters.

Once you have a set of genes that vary in some interesting way across the clusters, Monocle provides a means of grouping them into modules. You can call find_gene_modules(), which essentially runs UMAP on the genes (as opposed to the cells) and then groups them into modules using Louvain community analysis:

The data frame gene_module_df contains a row for each gene and identifies the module it belongs to. To see which modules are expressed in which clusters or partitions you can use two different approaches for visualization. The first is just to make a simple table that shows the aggregate expression of all genes in each module across all the clusters. Monocle provides a simple utility function called aggregate_gene_expression for this purpose:

Some modules are highly specific to certain partitions of cells, while others are shared across multiple partitions. Note that aggregate_gene_expression can work with arbitrary groupings of cells and genes. You're not limited to looking at modules from find_gene_modules(), clusters(), and partitions().

The second way of looking at modules and their expression is to pass gene_module_df directly to plot_cells(). If there are many modules, it can be hard to see where each one is expressed, so we'll just look at a subset of them:

Identifying the genes that change as cells progress along a trajectory is a core objective of this type of analysis. Knowing the order in which genes go on and off can inform new models of development. For example, Sharon and Chawla et al recently analyzed pseudotime-dependent genes to arrive at a whole new model of how islets form in the pancreas.

Let's return to the embryo data, which we processed using the commands

How do we find the genes that are differentially expressed on the different paths through the trajectory? How do we find the ones that are restricted to the beginning of the trajectory? Or excluded from it?

Once again, we turn to graph_test(), this time passing it neighbor_graph="principal_graph", which tells it to test whether cells at similar positions on the trajectory have correlated expression:

Here are a couple of interesting genes that score as highly significant according to graph_test():

As before, we can collect the trajectory-variable genes into modules:

Here we plot the aggregate module scores within each group of cell types as annotated by Packer & Zhu et al:

We can also pass gene_module_df to plot_cells() as we did when we compared clusters in the L2 data above.

Monocle offers another plotting function that can sometimes give a clearer view of a gene's dynamics along a single path. You can select a path with choose_cells() or by subsetting the cell data set by cluster, cell type, or other annotation that's restricted to the path. Let's pick one such path, the AFD cells:

The function plot_genes_in_pseudotime() takes a small set of genes and shows you their dynamics as a function of pseudotime:

You can see that dac-1 is activated before the other two genes.

Analyzing the genes that are regulated around trajectory branch points often provides insights into the genetic circuits that control cell fate decisions. Monocle can help you drill into a branch point that corresponds to a fate decision in your system. Doing so is as simple as selecting the cells (and branch point) of interest with choose_cells():

And then calling graph_test() on the subset. This will identify genes with interesting patterns of expression that fall only within the region of the trajectory you selected, giving you a more refined and relevant set of genes.

Grouping these genes into modules can reveal fate specific genes or those that are activate immediate prior to or following the branch point:

We will organize the modules by their similarity (using hclust) over the trajectory so it's a little easier to see which ones come on before others:

**Examples:**

Example 1 (unknown):
```unknown
fit_models()
```

Example 2 (unknown):
```unknown
graph_test()
```

Example 3 (unknown):
```unknown
ciliated_genes <- c("che-1",
                    "hlh-17",
                    "nhr-6",
                    "dmd-6",
                    "ceh-36",
                    "ham-1")
cds_subset <- cds[rowData(cds)$gene_short_name %in% ciliated_genes,]
```

Example 4 (r):
```r
ciliated_genes <- c("che-1",
                    "hlh-17",
                    "nhr-6",
                    "dmd-6",
                    "ceh-36",
                    "ham-1")
cds_subset <- cds[rowData(cds)$gene_short_name %in% ciliated_genes,]
```

Example 5 (unknown):
```unknown
fit_models()
```

Example 6 (unknown):
```unknown
gene_fits <- fit_models(cds_subset, model_formula_str = "~embryo.time")
```

Example 7 (r):
```r
gene_fits <- fit_models(cds_subset, model_formula_str = "~embryo.time")
```

Example 8 (unknown):
```unknown
model_formula_str
```

Example 9 (unknown):
```unknown
cluster_cells
```

Example 10 (unknown):
```unknown
~embryo.time + batch
```

Example 11 (unknown):
```unknown
coefficient_table()
```

Example 12 (unknown):
```unknown
fit_coefs <- coefficient_table(gene_fits)
```

Example 13 (r):
```r
fit_coefs <- coefficient_table(gene_fits)
```

Example 14 (unknown):
```unknown
emb_time_terms <- fit_coefs %>% filter(term == "embryo.time")
```

Example 15 (r):
```r
emb_time_terms <- fit_coefs %>% filter(term == "embryo.time")
```

Example 16 (unknown):
```unknown
coefficient_table()
```

Example 17 (unknown):
```unknown
coefficient_table()
```

Example 18 (unknown):
```unknown
emb_time_terms %>% filter (q_value < 0.05) %>%
         select(gene_short_name, term, q_value, estimate)
```

Example 19 (r):
```r
emb_time_terms %>% filter (q_value < 0.05) %>%
         select(gene_short_name, term, q_value, estimate)
```

Example 20 (unknown):
```unknown
plot_genes_violin(cds_subset, group_cells_by="embryo.time.bin", ncol=2) +
      theme(axis.text.x=element_text(angle=45, hjust=1))
```

Example 21 (r):
```r
plot_genes_violin(cds_subset, group_cells_by="embryo.time.bin", ncol=2) +
      theme(axis.text.x=element_text(angle=45, hjust=1))
```

Example 22 (unknown):
```unknown
plot_genes_hybrid(cds_subset, group_cells_by="embryo.time.bin", ncol=2) +
      theme(axis.text.x=element_text(angle=45, hjust=1))
```

Example 23 (r):
```r
plot_genes_hybrid(cds_subset, group_cells_by="embryo.time.bin", ncol=2) +
      theme(axis.text.x=element_text(angle=45, hjust=1))
```

Example 24 (unknown):
```unknown
gene_fits <- fit_models(cds_subset, model_formula_str = "~embryo.time + batch")
fit_coefs <- coefficient_table(gene_fits)
fit_coefs %>% filter(term != "(Intercept)") %>%
      select(gene_short_name, term, q_value, estimate)
```

Example 25 (r):
```r
gene_fits <- fit_models(cds_subset, model_formula_str = "~embryo.time + batch")
fit_coefs <- coefficient_table(gene_fits)
fit_coefs %>% filter(term != "(Intercept)") %>%
      select(gene_short_name, term, q_value, estimate)
```

Example 26 (unknown):
```unknown
evaluate_fits()
```

Example 27 (unknown):
```unknown
evaluate_fits(gene_fits)
```

Example 28 (r):
```r
evaluate_fits(gene_fits)
```

Example 29 (unknown):
```unknown
compare_models()
```

Example 30 (unknown):
```unknown
compare_models()
```

Example 31 (unknown):
```unknown
time_batch_models <- fit_models(cds_subset,
                                model_formula_str = "~embryo.time + batch",
                                expression_family="negbinomial")
time_models <- fit_models(cds_subset,
                          model_formula_str = "~embryo.time",
                          expression_family="negbinomial")
compare_models(time_batch_models, time_models) %>% select(gene_short_name, q_value)
```

Example 32 (r):
```r
time_batch_models <- fit_models(cds_subset,
                                model_formula_str = "~embryo.time + batch",
                                expression_family="negbinomial")
time_models <- fit_models(cds_subset,
                          model_formula_str = "~embryo.time",
                          expression_family="negbinomial")
compare_models(time_batch_models, time_models) %>% select(gene_short_name, q_value)
```

Example 33 (unknown):
```unknown
fit_models()
```

Example 34 (unknown):
```unknown
expression_family
```

Example 35 (unknown):
```unknown
quasipoisson
```

Example 36 (unknown):
```unknown
fit_models()
```

Example 37 (unknown):
```unknown
negbinomial
```

Example 38 (unknown):
```unknown
evaluate_fits()
```

Example 39 (unknown):
```unknown
compare_models()
```

Example 40 (python):
```python
# reload and reprocess the data as described in the 'Clustering and classifying your cells' section
expression_matrix <- readRDS(url("https://depts.washington.edu:/trapnell-lab/software/monocle3/celegans/data/cao_l2_expression.rds"))
cell_metadata <- readRDS(url("https://depts.washington.edu:/trapnell-lab/software/monocle3/celegans/data/cao_l2_colData.rds"))
gene_annotation <- readRDS(url("https://depts.washington.edu:/trapnell-lab/software/monocle3/celegans/data/cao_l2_rowData.rds"))

# Make the CDS object
cds <- new_cell_data_set(expression_matrix,
                         cell_metadata = cell_metadata,
                         gene_metadata = gene_annotation)
cds <- preprocess_cds(cds, num_dim = 100)
cds <- reduce_dimension(cds)
cds <- cluster_cells(cds, resolution=1e-5)

colData(cds)$assigned_cell_type <- as.character(partitions(cds))
colData(cds)$assigned_cell_type <- dplyr::recode(colData(cds)$assigned_cell_type,
                                                 "1"="Body wall muscle",
                                                 "2"="Germline",
                                                 "3"="Motor neurons",
                                                 "4"="Seam cells",
                                                 "5"="Sex myoblasts",
                                                 "6"="Socket cells",
                                                 "7"="Marginal_cell",
                                                 "8"="Coelomocyte",
                                                 "9"="Am/PH sheath cells",
                                                 "10"="Ciliated neurons",
                                                 "11"="Intestinal/rectal muscle",
                                                 "12"="Excretory gland",
                                                 "13"="Chemosensory neurons",
                                                 "14"="Interneurons",
                                                 "15"="Unclassified eurons",
                                                 "16"="Ciliated neurons",
                                                 "17"="Pharyngeal gland cells",
                                                 "18"="Unclassified neurons",
                                                 "19"="Chemosensory neurons",
                                                 "20"="Ciliated neurons",
                                                 "21"="Ciliated neurons",
                                                 "22"="Inner labial neuron",
                                                 "23"="Ciliated neurons",
                                                 "24"="Ciliated neurons",
                                                 "25"="Ciliated neurons",
                                                 "26"="Hypodermal cells",
                                                 "27"="Mesodermal cells",
                                                 "28"="Motor neurons",
                                                 "29"="Pharyngeal gland cells",
                                                 "30"="Ciliated neurons",
                                                 "31"="Excretory cells",
                                                 "32"="Amphid neuron",
                                                 "33"="Pharyngeal muscle")
```

Example 41 (r):
```r
# reload and reprocess the data as described in the 'Clustering and classifying your cells' section
expression_matrix <- readRDS(url("https://depts.washington.edu:/trapnell-lab/software/monocle3/celegans/data/cao_l2_expression.rds"))
cell_metadata <- readRDS(url("https://depts.washington.edu:/trapnell-lab/software/monocle3/celegans/data/cao_l2_colData.rds"))
gene_annotation <- readRDS(url("https://depts.washington.edu:/trapnell-lab/software/monocle3/celegans/data/cao_l2_rowData.rds"))

# Make the CDS object
cds <- new_cell_data_set(expression_matrix,
                         cell_metadata = cell_metadata,
                         gene_metadata = gene_annotation)
cds <- preprocess_cds(cds, num_dim = 100)
cds <- reduce_dimension(cds)
cds <- cluster_cells(cds, resolution=1e-5)

colData(cds)$assigned_cell_type <- as.character(partitions(cds))
colData(cds)$assigned_cell_type <- dplyr::recode(colData(cds)$assigned_cell_type,
                                                 "1"="Body wall muscle",
                                                 "2"="Germline",
                                                 "3"="Motor neurons",
                                                 "4"="Seam cells",
                                                 "5"="Sex myoblasts",
                                                 "6"="Socket cells",
                                                 "7"="Marginal_cell",
                                                 "8"="Coelomocyte",
                                                 "9"="Am/PH sheath cells",
                                                 "10"="Ciliated neurons",
                                                 "11"="Intestinal/rectal muscle",
                                                 "12"="Excretory gland",
                                                 "13"="Chemosensory neurons",
                                                 "14"="Interneurons",
                                                 "15"="Unclassified eurons",
                                                 "16"="Ciliated neurons",
                                                 "17"="Pharyngeal gland cells",
                                                 "18"="Unclassified neurons",
                                                 "19"="Chemosensory neurons",
                                                 "20"="Ciliated neurons",
                                                 "21"="Ciliated neurons",
                                                 "22"="Inner labial neuron",
                                                 "23"="Ciliated neurons",
                                                 "24"="Ciliated neurons",
                                                 "25"="Ciliated neurons",
                                                 "26"="Hypodermal cells",
                                                 "27"="Mesodermal cells",
                                                 "28"="Motor neurons",
                                                 "29"="Pharyngeal gland cells",
                                                 "30"="Ciliated neurons",
                                                 "31"="Excretory cells",
                                                 "32"="Amphid neuron",
                                                 "33"="Pharyngeal muscle")
```

Example 42 (unknown):
```unknown
neurons_cds <- cds[,grepl("neurons", colData(cds)$assigned_cell_type, ignore.case=TRUE)]
plot_cells(neurons_cds, color_cells_by="partition")
```

Example 43 (r):
```r
neurons_cds <- cds[,grepl("neurons", colData(cds)$assigned_cell_type, ignore.case=TRUE)]
plot_cells(neurons_cds, color_cells_by="partition")
```

Example 44 (unknown):
```unknown
graph_test()
```

Example 45 (unknown):
```unknown
graph_test()
```

Example 46 (unknown):
```unknown
pr_graph_test_res <- graph_test(neurons_cds, neighbor_graph="knn", cores=8)
pr_deg_ids <- row.names(subset(pr_graph_test_res, q_value < 0.05))
```

Example 47 (r):
```r
pr_graph_test_res <- graph_test(neurons_cds, neighbor_graph="knn", cores=8)
pr_deg_ids <- row.names(subset(pr_graph_test_res, q_value < 0.05))
```

Example 48 (unknown):
```unknown
pr_graph_test_res
```

Example 49 (unknown):
```unknown
cell_data_set
```

Example 50 (unknown):
```unknown
find_gene_modules()
```

Example 51 (unknown):
```unknown
gene_module_df <- find_gene_modules(neurons_cds[pr_deg_ids,], resolution=1e-2)
```

Example 52 (r):
```r
gene_module_df <- find_gene_modules(neurons_cds[pr_deg_ids,], resolution=1e-2)
```

Example 53 (unknown):
```unknown
gene_module_df
```

Example 54 (unknown):
```unknown
aggregate_gene_expression
```

Example 55 (unknown):
```unknown
cell_group_df <- tibble::tibble(cell=row.names(colData(neurons_cds)), 
                                cell_group=partitions(cds)[colnames(neurons_cds)])
agg_mat <- aggregate_gene_expression(neurons_cds, gene_module_df, cell_group_df)
row.names(agg_mat) <- stringr::str_c("Module ", row.names(agg_mat))
colnames(agg_mat) <- stringr::str_c("Partition ", colnames(agg_mat))

pheatmap::pheatmap(agg_mat, cluster_rows=TRUE, cluster_cols=TRUE,
                   scale="column", clustering_method="ward.D2",
                   fontsize=6)
```

Example 56 (r):
```r
cell_group_df <- tibble::tibble(cell=row.names(colData(neurons_cds)), 
                                cell_group=partitions(cds)[colnames(neurons_cds)])
agg_mat <- aggregate_gene_expression(neurons_cds, gene_module_df, cell_group_df)
row.names(agg_mat) <- stringr::str_c("Module ", row.names(agg_mat))
colnames(agg_mat) <- stringr::str_c("Partition ", colnames(agg_mat))

pheatmap::pheatmap(agg_mat, cluster_rows=TRUE, cluster_cols=TRUE,
                   scale="column", clustering_method="ward.D2",
                   fontsize=6)
```

Example 57 (unknown):
```unknown
aggregate_gene_expression
```

Example 58 (unknown):
```unknown
find_gene_modules()
```

Example 59 (unknown):
```unknown
partitions()
```

Example 60 (unknown):
```unknown
gene_module_df
```

Example 61 (unknown):
```unknown
plot_cells()
```

Example 62 (unknown):
```unknown
plot_cells(neurons_cds, 
           genes=gene_module_df %>% filter(module %in% c(8, 28, 33, 37)),
           group_cells_by="partition",
           color_cells_by="partition",
           show_trajectory_graph=FALSE)
```

Example 63 (r):
```r
plot_cells(neurons_cds, 
           genes=gene_module_df %>% filter(module %in% c(8, 28, 33, 37)),
           group_cells_by="partition",
           color_cells_by="partition",
           show_trajectory_graph=FALSE)
```

Example 64 (python):
```python
expression_matrix <- readRDS(url("https://depts.washington.edu:/trapnell-lab/software/monocle3/celegans/data/packer_embryo_expression.rds"))
cell_metadata <- readRDS(url("https://depts.washington.edu:/trapnell-lab/software/monocle3/celegans/data/packer_embryo_colData.rds"))
gene_annotation <- readRDS(url("https://depts.washington.edu:/trapnell-lab/software/monocle3/celegans/data/packer_embryo_rowData.rds"))
cds <- new_cell_data_set(expression_matrix,
                         cell_metadata = cell_metadata,
                         gene_metadata = gene_annotation)
cds <- preprocess_cds(cds, num_dim = 50)
cds <- align_cds(cds, alignment_group = "batch", residual_model_formula_str = "~ bg.300.loading + bg.400.loading + bg.500.1.loading + bg.500.2.loading + bg.r17.loading + bg.b01.loading + bg.b02.loading")
cds <- reduce_dimension(cds)
cds <- cluster_cells(cds)
cds <- learn_graph(cds)
cds <- order_cells(cds)
plot_cells(cds,
           color_cells_by = "cell.type",
           label_groups_by_cluster=FALSE,
           label_leaves=FALSE,
           label_branch_points=FALSE)
```

Example 65 (r):
```r
expression_matrix <- readRDS(url("https://depts.washington.edu:/trapnell-lab/software/monocle3/celegans/data/packer_embryo_expression.rds"))
cell_metadata <- readRDS(url("https://depts.washington.edu:/trapnell-lab/software/monocle3/celegans/data/packer_embryo_colData.rds"))
gene_annotation <- readRDS(url("https://depts.washington.edu:/trapnell-lab/software/monocle3/celegans/data/packer_embryo_rowData.rds"))
cds <- new_cell_data_set(expression_matrix,
                         cell_metadata = cell_metadata,
                         gene_metadata = gene_annotation)
cds <- preprocess_cds(cds, num_dim = 50)
cds <- align_cds(cds, alignment_group = "batch", residual_model_formula_str = "~ bg.300.loading + bg.400.loading + bg.500.1.loading + bg.500.2.loading + bg.r17.loading + bg.b01.loading + bg.b02.loading")
cds <- reduce_dimension(cds)
cds <- cluster_cells(cds)
cds <- learn_graph(cds)
cds <- order_cells(cds)
plot_cells(cds,
           color_cells_by = "cell.type",
           label_groups_by_cluster=FALSE,
           label_leaves=FALSE,
           label_branch_points=FALSE)
```

Example 66 (unknown):
```unknown
graph_test()
```

Example 67 (unknown):
```unknown
neighbor_graph="principal_graph"
```

Example 68 (unknown):
```unknown
ciliated_cds_pr_test_res <- graph_test(cds, neighbor_graph="principal_graph", cores=4)
pr_deg_ids <- row.names(subset(ciliated_cds_pr_test_res, q_value < 0.05))
```

Example 69 (r):
```r
ciliated_cds_pr_test_res <- graph_test(cds, neighbor_graph="principal_graph", cores=4)
pr_deg_ids <- row.names(subset(ciliated_cds_pr_test_res, q_value < 0.05))
```

Example 70 (unknown):
```unknown
graph_test()
```

Example 71 (unknown):
```unknown
plot_cells(cds, genes=c("hlh-4", "gcy-8", "dac-1", "oig-8"),
           show_trajectory_graph=FALSE,
           label_cell_groups=FALSE,
           label_leaves=FALSE)
```

Example 72 (r):
```r
plot_cells(cds, genes=c("hlh-4", "gcy-8", "dac-1", "oig-8"),
           show_trajectory_graph=FALSE,
           label_cell_groups=FALSE,
           label_leaves=FALSE)
```

Example 73 (unknown):
```unknown
gene_module_df <- find_gene_modules(cds[pr_deg_ids,], resolution=c(10^seq(-6,-1)))
```

Example 74 (r):
```r
gene_module_df <- find_gene_modules(cds[pr_deg_ids,], resolution=c(10^seq(-6,-1)))
```

Example 75 (unknown):
```unknown
cell_group_df <- tibble::tibble(cell=row.names(colData(cds)), 
                                cell_group=colData(cds)$cell.type)
agg_mat <- aggregate_gene_expression(cds, gene_module_df, cell_group_df)
row.names(agg_mat) <- stringr::str_c("Module ", row.names(agg_mat))
pheatmap::pheatmap(agg_mat,
                   scale="column", clustering_method="ward.D2")
```

Example 76 (r):
```r
cell_group_df <- tibble::tibble(cell=row.names(colData(cds)), 
                                cell_group=colData(cds)$cell.type)
agg_mat <- aggregate_gene_expression(cds, gene_module_df, cell_group_df)
row.names(agg_mat) <- stringr::str_c("Module ", row.names(agg_mat))
pheatmap::pheatmap(agg_mat,
                   scale="column", clustering_method="ward.D2")
```

Example 77 (unknown):
```unknown
gene_module_df
```

Example 78 (unknown):
```unknown
plot_cells()
```

Example 79 (unknown):
```unknown
plot_cells(cds,
           genes=gene_module_df %>% filter(module %in% c(27, 10, 7, 30)),
           label_cell_groups=FALSE,
           show_trajectory_graph=FALSE)
```

Example 80 (r):
```r
plot_cells(cds,
           genes=gene_module_df %>% filter(module %in% c(27, 10, 7, 30)),
           label_cell_groups=FALSE,
           show_trajectory_graph=FALSE)
```

Example 81 (unknown):
```unknown
choose_cells()
```

Example 82 (unknown):
```unknown
AFD_genes <- c("gcy-8", "dac-1", "oig-8")
AFD_lineage_cds <- cds[rowData(cds)$gene_short_name %in% AFD_genes,
                       colData(cds)$cell.type %in% c("AFD")]
AFD_lineage_cds <- order_cells(AFD_lineage_cds)
```

Example 83 (r):
```r
AFD_genes <- c("gcy-8", "dac-1", "oig-8")
AFD_lineage_cds <- cds[rowData(cds)$gene_short_name %in% AFD_genes,
                       colData(cds)$cell.type %in% c("AFD")]
AFD_lineage_cds <- order_cells(AFD_lineage_cds)
```

Example 84 (unknown):
```unknown
plot_genes_in_pseudotime()
```

Example 85 (unknown):
```unknown
plot_genes_in_pseudotime(AFD_lineage_cds,
                         color_cells_by="embryo.time.bin",
                         min_expr=0.5)
```

Example 86 (r):
```r
plot_genes_in_pseudotime(AFD_lineage_cds,
                         color_cells_by="embryo.time.bin",
                         min_expr=0.5)
```

Example 87 (unknown):
```unknown
choose_cells()
```

Example 88 (unknown):
```unknown
cds_subset <- choose_cells(cds)
```

Example 89 (r):
```r
cds_subset <- choose_cells(cds)
```

Example 90 (unknown):
```unknown
graph_test()
```

Example 91 (unknown):
```unknown
subset_pr_test_res <- graph_test(cds_subset, neighbor_graph="principal_graph", cores=4)
pr_deg_ids <- row.names(subset(subset_pr_test_res, q_value < 0.05))
```

Example 92 (r):
```r
subset_pr_test_res <- graph_test(cds_subset, neighbor_graph="principal_graph", cores=4)
pr_deg_ids <- row.names(subset(subset_pr_test_res, q_value < 0.05))
```

Example 93 (unknown):
```unknown
gene_module_df <- find_gene_modules(cds_subset[pr_deg_ids,], resolution=0.001)
```

Example 94 (r):
```r
gene_module_df <- find_gene_modules(cds_subset[pr_deg_ids,], resolution=0.001)
```

Example 95 (unknown):
```unknown
agg_mat <- aggregate_gene_expression(cds_subset, gene_module_df)
module_dendro <- hclust(dist(agg_mat))
gene_module_df$module <- factor(gene_module_df$module, 
                                levels = row.names(agg_mat)[module_dendro$order])

plot_cells(cds_subset,
           genes=gene_module_df,
           label_cell_groups=FALSE,
           show_trajectory_graph=FALSE)
```

Example 96 (r):
```r
agg_mat <- aggregate_gene_expression(cds_subset, gene_module_df)
module_dendro <- hclust(dist(agg_mat))
gene_module_df$module <- factor(gene_module_df$module, 
                                levels = row.names(agg_mat)[module_dendro$order])

plot_cells(cds_subset,
           genes=gene_module_df,
           label_cell_groups=FALSE,
           show_trajectory_graph=FALSE)
```

---
