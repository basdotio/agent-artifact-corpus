# Envi-Pkg-Local-Improved - Getting Started

**Pages:** 7

---

## ENVI Tutorial¶

**URL:** http://127.0.0.1:9162/docs/build/html/tutorial/MOp_MERFISH_tutorial.html

**Contents:**
- ENVI Tutorial¶
- What is COVET?¶
- What is ENVI?¶
  - Install ENVI¶
  - Importing¶
  - Utility Functions:¶
  - Data¶
- Plotting the Motor Cortex MERFISH¶
- Plotting the Motor Cortex scRNAseq¶
  - Running ENVI¶
- Plot UMAPs of ENVI latent¶
  - ENVI COVET analysis¶
- Calculating FDL and DC on COVET¶
- Reverse DC if needed¶
- Plot DC and Depth¶
  - Subtype Depth¶
  - Niche Cell Type Composition¶
- Plot as Stacked Bar Plots¶
  - ENVI imputation on Spatial Data¶

COVET is a method for representing and quantifying cellular niches based on their gene-gene covariance. COVET takes as input spatial data and returns the niche gene-gene covariance matrix of each cell.

ENVI integrates between paired scRNA-seq and spatial data. ENVI relies on COVET and predicts spatial context of dissociated scRNA-seq data & imputes missing genes for the spatial data. ENVI takes as input spatial data and scRNA_seq data, trains a VAE model and produces latent embeddings for each dataset, imputed values for the spatial data, and predicted COVET matrices for the scRNA-seq data.

ENVI can be installed directly with pip with the following command:

Some functions that are used in the analysis in this tutorial, feel free to switch to you own prefered versions

Downloading Motor Cortex scRNA-seq and MERFISH data from the Pe’er lab aws and loading in with scanpy

Defining cell type color palette

We first define and ENVI model which computes the COVET matrices of the spatial data and intializes the CVAE:

Training ENVI and run auxiliary function

Read ENVI predictions

Double Checking that cell types co-embed from the MERFISH and scRNA-seq datasets

Zooming on the Glutamatergic neuron, and using their COVET embedding for pseudo-depth prediction

Note that we are running FDL on COVET_SQRT, this is because the distance between COVET matrices is the L2 between their SQRT. We can simply run FDL (or DC, UMAP, PhenoGraph, etc.) on the COVET_SQRT to analyize COVET niche representation!

DC direction is arbitrary; so flip DC direction if it’s backwards

Should go from blue (shallow) to green (deep)

Box plot of cortical depth for each cell in every subtype

**Examples:**

Example 1 (python):
```python
import os

os.environ["CUDA_DEVICE_ORDER"]="PCI_BUS_ID"
os.environ["CUDA_VISIBLE_DEVICES"]="0" # Change to -1 if you want to use CPU!

import warnings
warnings.filterwarnings('ignore')
```

Example 2 (unknown):
```unknown
!pip install scenvi
```

Example 3 (python):
```python
import scenvi
```

Example 4 (unknown):
```unknown
2024-04-18 15:04:31.556441: W external/xla/xla/service/gpu/nvptx_compiler.cc:718] The NVIDIA driver's CUDA version is 12.2 which is older than the ptxas CUDA version (12.4.131). Because the driver is older than the ptxas version, XLA is disabling parallel compilation, which may slow down compilation. You should update your NVIDIA driver or use the NVIDIA-provided CUDA forward compatibility packages.
```

Example 5 (python):
```python
%matplotlib inline
import matplotlib
import matplotlib.pyplot as plt
import seaborn as sns

import numpy as np
import pandas as pd
import scanpy as sc
import colorcet
import sklearn.neighbors
import scipy.sparse
import umap.umap_ as umap
from fa2 import ForceAtlas2
```

Example 6 (python):
```python
def flatten(arr):
    return(np.reshape(arr, [arr.shape[0], -1]))

def force_directed_layout(affinity_matrix, cell_names=None, verbose=True, iterations=500, device='cpu'):
    """" Function to compute force directed layout from the affinity_matrix
    :param affinity_matrix: Sparse matrix representing affinities between cells
    :param cell_names: pandas Series object with cell names
    :param verbose: Verbosity for force directed layout computation
    :param iterations: Number of iterations used by ForceAtlas
    :return: Pandas data frame representing the force directed layout
    """

    init_coords = np.random.random((affinity_matrix.shape[0], 2))

    if device == 'cpu':
        forceatlas2 = ForceAtlas2(
            # Behavior alternatives
            outboundAttractionDistribution=False,
            linLogMode=False,
            adjustSizes=False,
            edgeWeightInfluence=1.0,
            # Performance
            jitterTolerance=1.0,
            barnesHutOptimize=True,
            barnesHutTheta=1.2,
            multiThreaded=False,
            # Tuning
            scalingRatio=2.0,
            strongGravityMode=False,
            gravity=1.0,
            # Log
            verbose=verbose)

        positions = forceatlas2.forceatlas2(
            affinity_matrix, pos=init_coords, iterations=iterations)
        positions = np.array(positions)


    positions = pd.DataFrame(positions,
                             index=np.arange(affinity_matrix.shape[0]), columns=['x', 'y'])
    return positions

def run_diffusion_maps(data_df, n_components=10, knn=30, alpha=0):
    """Run Diffusion maps using the adaptive anisotropic kernel
    :param data_df: PCA projections of the data or adjacency matrix
    :param n_components: Number of diffusion components
    :param knn: Number of nearest neighbors for graph construction
    :param alpha: Normalization parameter for the diffusion operator
    :return: Diffusion components, corresponding eigen values and the diffusion operator
    """

    # Determine the kernel
    N = data_df.shape[0]

    if(type(data_df).__module__ == np.__name__):
        data_df = pd.DataFrame(data_df)

    if not scipy.sparse.issparse(data_df):
        print("Determing nearest neighbor graph...")
        temp = sc.AnnData(data_df.values)
        sc.pp.neighbors(temp, n_pcs=0, n_neighbors=knn)
        kNN = temp.obsp['distances']

        # Adaptive k
        adaptive_k = int(np.floor(knn / 3))
        adaptive_std = np.zeros(N)

        for i in np.arange(len(adaptive_std)):
            adaptive_std[i] = np.sort(kNN.data[kNN.indptr[i] : kNN.indptr[i + 1]])[
                adaptive_k - 1
            ]

        # Kernel
        x, y, dists = scipy.sparse.find(kNN)

        # X, y specific stds
        dists = dists / adaptive_std[x]
        W = scipy.sparse.csr_matrix((np.exp(-dists), (x, y)), shape=[N, N])

        # Diffusion components
        kernel = W + W.T
    else:
        kernel = data_df

    # Markov
    D = np.ravel(kernel.sum(axis=1))

    if alpha > 0:
        # L_alpha
        D[D != 0] = D[D != 0] ** (-alpha)
        mat = scipy.sparse.csr_matrix((D, (range(N), range(N))), shape=[N, N])
        kernel = mat.dot(kernel).dot(mat)
        D = np.ravel(kernel.sum(axis=1))

    D[D != 0] = 1 / D[D != 0]
    T = scipy.sparse.csr_matrix((D, (range(N), range(N))), shape=[N, N]).dot(kernel)
    # Eigen value dcomposition
    D, V = scipy.sparse.linalg.eigs(T, n_components, tol=1e-4, maxiter=1000)
    D = np.real(D)
    V = np.real(V)
    inds = np.argsort(D)[::-1]
    D = D[inds]
    V = V[:, inds]

    # Normalize
    for i in range(V.shape[1]):
        V[:, i] = V[:, i] / np.linalg.norm(V[:, i])

    # Create are results dictionary
    res = {"T": T, "EigenVectors": V, "EigenValues": D}
    res["EigenVectors"] = pd.DataFrame(res["EigenVectors"])
    if not scipy.sparse.issparse(data_df):
        res["EigenVectors"].index = data_df.index
    res["EigenValues"] = pd.Series(res["EigenValues"])
    res["kernel"] = kernel

    return res


def FDL(data, k = 30):


    nbrs = sklearn.neighbors.NearestNeighbors(n_neighbors=int(k), metric='euclidean',
                               n_jobs=5).fit(data)
    kNN = nbrs.kneighbors_graph(data, mode='distance')
    # Adaptive k

    adaptive_k = int(np.floor(k / 3))
    nbrs = sklearn.neighbors.NearestNeighbors(n_neighbors=int(adaptive_k),
                           metric='euclidean', n_jobs=5).fit(data)
    adaptive_std = nbrs.kneighbors_graph(data, mode='distance').max(axis=1)
    adaptive_std = np.ravel(adaptive_std.todense())
    # Kernel
    x, y, dists = scipy.sparse.find(kNN)
    # X, y specific stds
    dists = dists / adaptive_std[x]
    N = data.shape[0]
    W = scipy.sparse.csr_matrix((np.exp(-dists), (x, y)), shape=[N, N])
    # Diffusion components
    kernel = W + W.T
    layout = force_directed_layout(kernel)
    return(layout)
```

Example 7 (unknown):
```unknown
!wget https://dp-lab-data-public.s3.amazonaws.com/ENVI/sc_data.h5ad
!wget https://dp-lab-data-public.s3.amazonaws.com/ENVI/st_data.h5ad
```

Example 8 (python):
```python
st_data = sc.read_h5ad('st_data.h5ad')
sc_data = sc.read_h5ad('sc_data.h5ad')
```

Example 9 (unknown):
```unknown
cell_type_palette = {'Astro': (0.843137, 0.0, 0.0, 1.0),
                     'Endo': (0.54902, 0.235294, 1.0, 1.0),
                     'L23_IT': (0.007843, 0.533333, 0.0, 1.0),
                     'L45_IT': (0.0, 0.67451, 0.780392, 1.0),
                     'L56_NP': (0.596078, 1.0, 0.0, 1.0),
                     'L5_ET': (1.0, 0.498039, 0.819608, 1.0),
                     'L5_IT': (0.423529, 0.0, 0.309804, 1.0),
                     'L5_PT': (1.0, 0.647059, 0.188235, 1.0),
                     'L6_CT': (0.345098, 0.231373, 0.0, 1.0),
                     'L6_IT': (0.0, 0.341176, 0.34902, 1.0),
                     'L6_IT_Car3': (0.0, 0.0, 0.866667, 1.0),
                     'L6b': (0.0, 0.992157, 0.811765, 1.0),
                     'Lamp5': (0.631373, 0.458824, 0.415686, 1.0),
                     'Microglia': (0.737255, 0.717647, 1.0, 1.0),
                     'OPC': (0.584314, 0.709804, 0.470588, 1.0),
                     'Oligo': (0.752941, 0.015686, 0.72549, 1.0),
                     'Pericytes': (0.392157, 0.329412, 0.454902, 1.0),
                     'Pvalb': (0.47451, 0.0, 0.0, 1.0),
                     'SMC': (0.027451, 0.454902, 0.847059, 1.0),
                     'Sncg': (0.996078, 0.960784, 0.564706, 1.0),
                     'Sst': (0.0, 0.294118, 0.0, 1.0),
                     'VLMC': (0.560784, 0.478431, 0.0, 1.0),
                     'Vip': (1.0, 0.447059, 0.4, 1.0)}

cell_label_palette = {'GABAergic': (0.843137, 0.0, 0.0, 1.0),
                      'Glutamatergic': (0.54902, 0.235294, 1.0, 1.0),
                      'Non-Neuronal': (0.007843, 0.533333, 0.0, 1.0)}
```

Example 10 (python):
```python
plt.figure(figsize=(10,10))

sns.scatterplot(x = st_data.obsm['spatial'][st_data.obs['batch'] == 'mouse1_slice10'][:, 1],
                y = -st_data.obsm['spatial'][st_data.obs['batch'] == 'mouse1_slice10'][:, 0], legend = True,
                hue = st_data.obs['cell_type'][st_data.obs['batch'] == 'mouse1_slice10'],
                s = 12, palette = cell_type_palette)
plt.axis('equal')
plt.axis('off')
plt.title("MERFISH Data")
plt.show()
```

Example 11 (python):
```python
fit = umap.UMAP(
    n_neighbors = 100,
    min_dist = 0.8,
    n_components = 2,
)

sc_data.layers['log'] = np.log(sc_data.X + 1)
sc.pp.highly_variable_genes(sc_data, layer = 'log', n_top_genes = 2048)
sc_data.obsm['UMAP_exp'] = fit.fit_transform(np.log(sc_data[:, sc_data.var['highly_variable']].X + 1))
```

Example 12 (python):
```python
fig = plt.figure(figsize = (10,10))
sns.scatterplot(x = sc_data.obsm['UMAP_exp'][:, 0], y = sc_data.obsm['UMAP_exp'][:, 1],  hue = sc_data.obs['cell_type'], s = 16,
                palette = cell_type_palette, legend = True)
plt.tight_layout()
plt.axis('off')
plt.title('scRNA-seq Data')
plt.show()
```

Example 13 (python):
```python
import scenvi
```

Example 14 (unknown):
```unknown
envi_model = scenvi.ENVI(spatial_data = st_data, sc_data = sc_data)
```

Example 15 (unknown):
```unknown
Computing Niche Covariance Matrices
Initializing VAE
Finished Initializing ENVI
```

Example 16 (unknown):
```unknown
envi_model.train()
envi_model.impute_genes()
envi_model.infer_niche_covet()
envi_model.infer_niche_celltype()
```

Example 17 (unknown):
```unknown
spatial: -6.339e-01 sc: -7.473e-01 cov: -5.431e-03 kl: 6.693e-01: 100%|██████████| 16000/16000 [02:11<00:00, 122.10it/s]
```

Example 18 (unknown):
```unknown
Finished imputing missing gene for spatial data! See 'imputation' in obsm of ENVI.spatial_data
```

Example 19 (unknown):
```unknown
st_data.obsm['envi_latent'] = envi_model.spatial_data.obsm['envi_latent']
st_data.obsm['COVET'] = envi_model.spatial_data.obsm['COVET']
st_data.obsm['COVET_SQRT'] = envi_model.spatial_data.obsm['COVET_SQRT']
st_data.uns['COVET_genes'] =  envi_model.CovGenes
st_data.obsm['imputation'] = envi_model.spatial_data.obsm['imputation']
st_data.obsm['cell_type_niche'] = envi_model.spatial_data.obsm['cell_type_niche']

sc_data.obsm['envi_latent'] = envi_model.sc_data.obsm['envi_latent']
sc_data.obsm['COVET'] = envi_model.sc_data.obsm['COVET']
sc_data.obsm['COVET_SQRT'] = envi_model.sc_data.obsm['COVET_SQRT']
sc_data.obsm['cell_type_niche'] = envi_model.sc_data.obsm['cell_type_niche']
sc_data.uns['COVET_genes'] =  envi_model.CovGenes
```

Example 20 (python):
```python
fit = umap.UMAP(
    n_neighbors = 100,
    min_dist = 0.3,
    n_components = 2,
)

latent_umap = fit.fit_transform(np.concatenate([st_data.obsm['envi_latent'], sc_data.obsm['envi_latent']], axis = 0))

st_data.obsm['latent_umap'] = latent_umap[:st_data.shape[0]]
sc_data.obsm['latent_umap'] = latent_umap[st_data.shape[0]:]
```

Example 21 (python):
```python
lim_arr = np.concatenate([st_data.obsm['latent_umap'], sc_data.obsm['latent_umap']], axis = 0)


delta = 1
pre = 0.1
xmin = np.percentile(lim_arr[:, 0], pre) - delta
xmax = np.percentile(lim_arr[:, 0], 100 - pre) + delta
ymin = np.percentile(lim_arr[:, 1], pre) - delta
ymax = np.percentile(lim_arr[:, 1], 100 - pre) + delta
```

Example 22 (python):
```python
fig = plt.figure(figsize = (13,5))
plt.subplot(121)
sns.scatterplot(x = sc_data.obsm['latent_umap'][:, 0],
                y = sc_data.obsm['latent_umap'][:, 1], hue = sc_data.obs['cell_type'], s = 8, palette = cell_type_palette,
                legend = False)
plt.title("scRNA-seq Latent")
plt.xlim([xmin, xmax])
plt.ylim([ymin, ymax])
plt.axis('off')

plt.subplot(122)
sns.scatterplot(x = st_data.obsm['latent_umap'][:, 0],
                y = st_data.obsm['latent_umap'][:, 1],  hue = st_data.obs['cell_type'], s = 8, palette = cell_type_palette, legend = True)


legend = plt.legend(title = 'Cell Type', prop={'size': 12}, fontsize = '12',  markerscale = 3, ncol = 2, bbox_to_anchor = (1, 1))#, loc = 'lower left')
plt.setp(legend.get_title(),fontsize='12')
plt.title("MERFISH Latent")
plt.axis('off')
plt.tight_layout()
plt.xlim([xmin, xmax])
plt.ylim([ymin, ymax])
plt.show()
```

Example 23 (unknown):
```unknown
st_data_sst = st_data[st_data.obs['cell_type'] == 'Sst']
sc_data_sst = sc_data[sc_data.obs['cell_type'] == 'Sst']
```

Example 24 (unknown):
```unknown
gran_sst_palette = {'Th': (0.0, 0.294118, 0.0, 1.0),
                    'Calb2': (0.560784, 0.478431, 0.0, 1.0),
                    'Chodl': (1.0, 0.447059, 0.4, 1.0),
                    'Myh8': (0.933333, 0.72549, 0.72549, 1.0),
                    'Crhr2': (0.368627, 0.494118, 0.4, 1.0),
                    'Hpse': (0.65098, 0.482353, 0.72549, 1.0),
                    'Hspe': (0.352941, 0.0, 0.643137, 1.0),
                    'Crh': (0.607843, 0.894118, 1.0, 1.0),
                    'Pvalb Etv1': (0.92549, 0.0, 0.466667, 1.0)}
```

Example 25 (python):
```python
FDL_COVET = np.asarray(FDL(np.concatenate([flatten(st_data_sst.obsm['COVET_SQRT']),
                                           flatten(sc_data_sst.obsm['COVET_SQRT'])], axis = 0), k = 30))

st_data_sst.obsm['FDL_COVET'] = FDL_COVET[:st_data_sst.shape[0]]
sc_data_sst.obsm['FDL_COVET'] = FDL_COVET[st_data_sst.shape[0]:]
```

Example 26 (unknown):
```unknown
100%|██████████| 500/500 [00:33<00:00, 15.03it/s]
```

Example 27 (unknown):
```unknown
BarnesHut Approximation  took  16.28  seconds
Repulsion forces  took  14.80  seconds
Gravitational forces  took  0.10  seconds
Attraction forces  took  0.94  seconds
AdjustSpeedAndApplyForces step  took  0.59  seconds
```

Example 28 (python):
```python
DC_COVET = np.asarray(run_diffusion_maps(np.concatenate([flatten(st_data_sst.obsm['COVET_SQRT']),
                                                         flatten(sc_data_sst.obsm['COVET_SQRT'])], axis = 0), knn = 30)['EigenVectors'])[:, 1:]
st_data_sst.obsm['DC_COVET'] = -DC_COVET[:st_data_sst.shape[0]]
sc_data_sst.obsm['DC_COVET'] = -DC_COVET[st_data_sst.shape[0]:]
```

Example 29 (unknown):
```unknown
Determing nearest neighbor graph...
```

Example 30 (python):
```python
st_data_sst.obsm['DC_COVET'] = -DC_COVET[:st_data_sst.shape[0]]
sc_data_sst.obsm['DC_COVET'] = -DC_COVET[st_data_sst.shape[0]:]
```

Example 31 (python):
```python
lim_arr = np.concatenate([st_data_sst.obsm['FDL_COVET'], sc_data_sst.obsm['FDL_COVET']], axis = 0)


delta = 1000
pre = 0.01
xmin = np.percentile(lim_arr[:, 0], pre) - delta
xmax = np.percentile(lim_arr[:, 0], 100 - pre) + delta
ymin = np.percentile(lim_arr[:, 1], pre) - delta
ymax = np.percentile(lim_arr[:, 1], 100 - pre) + delta
```

Example 32 (python):
```python
plt.figure(figsize=(10,5))

plt.subplot(121)
sns.scatterplot(x = sc_data_sst.obsm['FDL_COVET'][:, 0],
                y = sc_data_sst.obsm['FDL_COVET'][:, 1],
                hue = sc_data_sst.obs['cluster_label'], s = 16,  palette= gran_sst_palette, legend = True)
plt.tight_layout()
plt.xlim([xmin, xmax])
plt.ylim([ymin, ymax])
plt.title('scRNA-seq Sst, COVET FDL')
legend = plt.legend(title = 'Sst subtype', prop={'size': 8}, fontsize = '8',  markerscale = 1, ncol = 2)
plt.axis('off')

plt.subplot(122)
ax = sns.scatterplot(x = st_data_sst.obsm['FDL_COVET'][:, 0],
                y = st_data_sst.obsm['FDL_COVET'][:, 1],
                c = st_data_sst.obsm['DC_COVET'][:,0], s = 16,  cmap= 'cet_CET_D13', legend = False)
plt.tight_layout()
plt.xlim([xmin, xmax])
plt.ylim([ymin, ymax])
plt.axis('off')
plt.title('MERFISH Sst, COVET FDL')
plt.show()
```

Example 33 (python):
```python
fig = plt.figure(figsize=(25,5))

for ind, batch in enumerate(['mouse1_slice212', 'mouse1_slice162', 'mouse1_slice71', 'mouse2_slice270', 'mouse1_slice40']):
    st_dataBatch = st_data[st_data.obs['batch'] == batch]
    st_dataPlotBatch = st_data_sst[st_data_sst.obs['batch'] == batch]

    plt.subplot(1,5, 1+ ind)
    sns.scatterplot(x = st_dataBatch.obsm['spatial'][:, 0], y = st_dataBatch.obsm['spatial'][:, 1],  color = (207/255,185/255,151/255, 1))
    sns.scatterplot(x = st_dataPlotBatch.obsm['spatial'][:, 0], y = st_dataPlotBatch.obsm['spatial'][:, 1], marker = '^',
                        c = st_dataPlotBatch.obsm['DC_COVET'][:, 0], s = 256,  cmap= 'cet_CET_D13', legend = False)
    plt.title(batch)
    plt.axis('off')
    plt.tight_layout()

plt.show()
```

Example 34 (python):
```python
depth_df = pd.DataFrame()
depth_df['Subtype'] = sc_data_sst.obs['cluster_label']
depth_df['Depth'] = -sc_data_sst.obsm['DC_COVET'][:,0]
```

Example 35 (unknown):
```unknown
subtype_depth_order = depth_df.groupby(['Subtype']).mean().sort_values(by = 'Depth', ascending=False).index
```

Example 36 (python):
```python
plt.figure(figsize=(12,5))
sns.set(font_scale=1.7)
sns.set_style("whitegrid")
sns.boxenplot(depth_df, x = 'Subtype', y = 'Depth',# bw = 1, width = 0.9,
          order = subtype_depth_order,
          palette = gran_sst_palette)
plt.tight_layout()
plt.show()
```

Example 37 (python):
```python
subtype_canonical = pd.DataFrame([sc_data_sst[sc_data_sst.obs['cluster_label']==subtype].obsm['cell_type_niche'].mean(axis = 0) for subtype in subtype_depth_order],
                                     index = subtype_depth_order, columns = sc_data.obsm['cell_type_niche'].columns)
```

Example 38 (unknown):
```unknown
subtype_canonical[subtype_canonical<0.2] = 0
subtype_canonical.drop(labels=subtype_canonical.columns[(subtype_canonical == 0).all()], axis=1, inplace=True)
subtype_canonical = subtype_canonical.div(subtype_canonical.sum(axis=1), axis=0)
```

Example 39 (python):
```python
subtype_canonical.plot(kind = 'bar', stacked = 'True',
                       color = {col:cell_type_palette[col] for col in subtype_canonical.columns})
plt.legend(bbox_to_anchor = (1,1), ncols = 1, fontsize = 'x-small')
plt.title("Predicted Niche Composition")
plt.ylabel("Proportion")
plt.xlabel("Sst Subtype")
plt.show()
```

Example 40 (python):
```python
tick_genes = np.asarray(['Adamts18','Pamr1', 'Dkkl1', 'Hs6st2', 'Slit1', 'Ighm'])
```

Example 41 (python):
```python
plt.figure(figsize=(15,10))

for ind, gene in enumerate(tick_genes):
    plt.subplot(2,3,1+ind)

    cvec = np.log(st_data[st_data.obs['batch'] == 'mouse1_slice10'].obsm['imputation'][gene] + 0.1)
    sns.scatterplot(x = st_data.obsm['spatial'][st_data.obs['batch'] == 'mouse1_slice10'][:, 1],
                    y = -st_data.obsm['spatial'][st_data.obs['batch'] == 'mouse1_slice10'][:, 0], legend = False,
                    c = cvec, cmap = 'Reds',
                    vmax = np.percentile(cvec, 95), vmin = np.percentile(cvec, 30),
                    s = 24, edgecolor = 'k')#, palette = cell_type_palette)
    plt.title(gene)
    plt.axis('equal')
    plt.axis('off')
    plt.tight_layout()
plt.show()
```

---

## Index

**URL:** http://127.0.0.1:9162/docs/build/html/genindex.html

**Contents:**
- Index

---

## ENVI Tutorial¶

**URL:** http://127.0.0.1:9162/notebooks_html/MOp_MERFISH_tutorial.html

**Contents:**
- ENVI Tutorial¶
  - What is COVET?¶
  - What is ENVI?¶
- Install ENVI¶
- Importing¶
- Data¶
  - Plotting the Motor Cortex MERFISH¶
  - Plotting the Motor Cortex scRNAseq¶
- Running ENVI¶
  - Plot UMAPs of ENVI latent¶
- ENVI COVET analysis¶
  - Calculating FDL and DC on COVET¶
    - Some Helful Functions¶
    - Run Analysis¶
  - Reverse DC if needed¶
  - Plot DC and Depth¶
- Subtype Depth¶
- Niche Cell Type Composition¶
  - Plot as Stacked Bar Plots¶
- ENVI imputation on Spatial Data¶

COVET is a method for representing and quantifying cellular niches based on their gene-gene covariance. COVET takes as input spatial data and returns the niche gene-gene covariance matrix of each cell.

ENVI integrates between paired scRNA-seq and spatial data. ENVI relies on COVET and predicts spatial context of dissociated scRNA-seq data & imputes missing genes for the spatial data. ENVI takes as input spatial data and scRNA_seq data, trains a VAE model and produces latent embeddings for each dataset, imputed values for the spatial data, and predicted COVET matrices for the scRNA-seq data.

ENVI can be installed directly with pip with the following command:

Downloading Motor Cortex scRNA-seq and MERFISH data from the Pe'er lab aws and loading in with scanpy

Defining cell type color palette

We first define and ENVI model which computes the COVET matrices of the spatial data and intializes the CVAE:

Training ENVI and run auxiliary function

Read ENVI predictions

Double Checking that cell types co-embed from the MERFISH and scRNA-seq datasets

ENVI uses COVET to predict the niche cell type abundence for each scRNA-seq cell. For each Sst subtype, we will compute the canonical niche composition:

**Examples:**

Example 1 (unknown):
```unknown
%load_ext autoreload
%autoreload 2
```

Example 2 (python):
```python
import os

os.environ["CUDA_DEVICE_ORDER"]="PCI_BUS_ID"   
os.environ["CUDA_VISIBLE_DEVICES"]="0" # Change to -1 if you want to use CPU!

import warnings
warnings.filterwarnings('ignore')
```

Example 3 (unknown):
```unknown
!pip install scenvi
```

Example 4 (python):
```python
import scenvi
```

Example 5 (python):
```python
%matplotlib inline
import matplotlib
import matplotlib.pyplot as plt
import seaborn as sns

import numpy as np
import pandas as pd
import scanpy as sc
import colorcet
import umap.umap_ as umap
```

Example 6 (unknown):
```unknown
!wget https://dp-lab-data-public.s3.amazonaws.com/ENVI/sc_data.h5ad
!wget https://dp-lab-data-public.s3.amazonaws.com/ENVI/st_data.h5ad
```

Example 7 (python):
```python
st_data = sc.read_h5ad('st_data.h5ad')
sc_data = sc.read_h5ad('sc_data.h5ad')
```

Example 8 (unknown):
```unknown
cell_type_palette = {'Astro': (0.843137, 0.0, 0.0, 1.0),
                     'Endo': (0.54902, 0.235294, 1.0, 1.0),
                     'L23_IT': (0.007843, 0.533333, 0.0, 1.0),
                     'L45_IT': (0.0, 0.67451, 0.780392, 1.0),
                     'L56_NP': (0.596078, 1.0, 0.0, 1.0),
                     'L5_ET': (1.0, 0.498039, 0.819608, 1.0),
                     'L5_IT': (0.423529, 0.0, 0.309804, 1.0),
                     'L5_PT': (1.0, 0.647059, 0.188235, 1.0),
                     'L6_CT': (0.345098, 0.231373, 0.0, 1.0),
                     'L6_IT': (0.0, 0.341176, 0.34902, 1.0),
                     'L6_IT_Car3': (0.0, 0.0, 0.866667, 1.0),
                     'L6b': (0.0, 0.992157, 0.811765, 1.0),
                     'Lamp5': (0.631373, 0.458824, 0.415686, 1.0),
                     'Microglia': (0.737255, 0.717647, 1.0, 1.0),
                     'OPC': (0.584314, 0.709804, 0.470588, 1.0),
                     'Oligo': (0.752941, 0.015686, 0.72549, 1.0),
                     'Pericytes': (0.392157, 0.329412, 0.454902, 1.0),
                     'Pvalb': (0.47451, 0.0, 0.0, 1.0),
                     'SMC': (0.027451, 0.454902, 0.847059, 1.0),
                     'Sncg': (0.996078, 0.960784, 0.564706, 1.0),
                     'Sst': (0.0, 0.294118, 0.0, 1.0),
                     'VLMC': (0.560784, 0.478431, 0.0, 1.0),
                     'Vip': (1.0, 0.447059, 0.4, 1.0)}

cell_label_palette = {'GABAergic': (0.843137, 0.0, 0.0, 1.0),
                      'Glutamatergic': (0.54902, 0.235294, 1.0, 1.0),
                      'Non-Neuronal': (0.007843, 0.533333, 0.0, 1.0)}
```

Example 9 (python):
```python
plt.figure(figsize=(10,10))

sns.scatterplot(x = st_data.obsm['spatial'][st_data.obs['batch'] == 'mouse1_slice10'][:, 1], 
                y = -st_data.obsm['spatial'][st_data.obs['batch'] == 'mouse1_slice10'][:, 0], legend = True,
                hue = st_data.obs['cell_type'][st_data.obs['batch'] == 'mouse1_slice10'], 
                s = 12, palette = cell_type_palette)
plt.axis('equal')
plt.axis('off')
plt.title("MERFISH Data")
plt.show()
```

Example 10 (python):
```python
fit = umap.UMAP(
    n_neighbors = 100,
    min_dist = 0.8,
    n_components = 2,
)

sc_data.layers['log'] = np.log(sc_data.X + 1)
sc.pp.highly_variable_genes(sc_data, layer = 'log', n_top_genes = 2048)
sc_data.obsm['UMAP_exp'] = fit.fit_transform(np.log(sc_data[:, sc_data.var['highly_variable']].X + 1))
```

Example 11 (python):
```python
fig = plt.figure(figsize = (10,10))
sns.scatterplot(x = sc_data.obsm['UMAP_exp'][:, 0], y = sc_data.obsm['UMAP_exp'][:, 1],  hue = sc_data.obs['cell_type'], s = 16,
                palette = cell_type_palette, legend = True)
plt.tight_layout()
plt.axis('off')
plt.title('scRNA-seq Data')
plt.show()
```

Example 12 (unknown):
```unknown
envi_model = scenvi.ENVI(spatial_data = st_data, sc_data = sc_data, covet_batch_size = 256)
```

Example 13 (python):
```python
Preparing gene sets for ENVI analysis...
Using pre-computed highly variable genes from single-cell data
Gene selection: 254 shared genes, 1832 unique to single-cell
Computing Niche Covariance Matrices
Using 64 pre-calculated highly variable genes for COVET
```

Example 14 (unknown):
```unknown
Calculating covariance matrices: 100%|██████████| 1081/1081 [00:04<00:00, 235.14it/s]
Computing matrix square roots: 100%|██████████| 1081/1081 [01:51<00:00,  9.72it/s]
```

Example 15 (unknown):
```unknown
Finished Initializing ENVI
```

Example 16 (unknown):
```unknown
envi_model.train()
envi_model.impute_genes()
envi_model.infer_niche_covet()
envi_model.infer_niche_celltype()
```

Example 17 (unknown):
```unknown
spatial: -6.316e-01 sc: -7.364e-01 cov: -5.564e-03 kl: 6.691e-01: 100%|██████████| 16000/16000 [02:37<00:00, 101.30it/s]
```

Example 18 (unknown):
```unknown
Computing latent representations
```

Example 19 (unknown):
```unknown
Encoding: 100%|██████████| 4322/4322 [01:33<00:00, 46.20it/s]
Encoding: 100%|██████████| 1113/1113 [00:23<00:00, 48.21it/s]
```

Example 20 (unknown):
```unknown
Imputing missing genes for spatial data
```

Example 21 (unknown):
```unknown
Decoding expression: 100%|██████████| 4322/4322 [01:32<00:00, 46.55it/s]
```

Example 22 (unknown):
```unknown
Infering niche COVET representation for single-cell data
```

Example 23 (unknown):
```unknown
Decoding covet: 100%|██████████| 1113/1113 [00:26<00:00, 41.61it/s]
```

Example 24 (unknown):
```unknown
Infering cell type niche composition for single cell data
```

Example 25 (unknown):
```unknown
st_data.obsm['envi_latent'] = envi_model.spatial_data.obsm['envi_latent']
st_data.obsm['COVET'] = envi_model.spatial_data.obsm['COVET']
st_data.obsm['COVET_SQRT'] = envi_model.spatial_data.obsm['COVET_SQRT']
st_data.uns['COVET_genes'] =  envi_model.CovGenes
st_data.obsm['imputation'] = envi_model.spatial_data.obsm['imputation']
st_data.obsm['cell_type_niche'] = envi_model.spatial_data.obsm['cell_type_niche']

sc_data.obsm['envi_latent'] = envi_model.sc_data.obsm['envi_latent']
sc_data.obsm['COVET'] = envi_model.sc_data.obsm['COVET']
sc_data.obsm['COVET_SQRT'] = envi_model.sc_data.obsm['COVET_SQRT']
sc_data.obsm['cell_type_niche'] = envi_model.sc_data.obsm['cell_type_niche']
sc_data.uns['COVET_genes'] =  envi_model.CovGenes
```

Example 26 (python):
```python
fit = umap.UMAP(
    n_neighbors = 100,
    min_dist = 0.3,
    n_components = 2,
)

latent_umap = fit.fit_transform(np.concatenate([st_data.obsm['envi_latent'], sc_data.obsm['envi_latent']], axis = 0))

st_data.obsm['latent_umap'] = latent_umap[:st_data.shape[0]]
sc_data.obsm['latent_umap'] = latent_umap[st_data.shape[0]:]
```

Example 27 (python):
```python
lim_arr = np.concatenate([st_data.obsm['latent_umap'], sc_data.obsm['latent_umap']], axis = 0)


delta = 1
pre = 0.1
xmin = np.percentile(lim_arr[:, 0], pre) - delta 
xmax = np.percentile(lim_arr[:, 0], 100 - pre) + delta
ymin = np.percentile(lim_arr[:, 1], pre) - delta 
ymax = np.percentile(lim_arr[:, 1], 100 - pre) + delta
```

Example 28 (python):
```python
fig = plt.figure(figsize = (13,5))
plt.subplot(121)
sns.scatterplot(x = sc_data.obsm['latent_umap'][:, 0], 
                y = sc_data.obsm['latent_umap'][:, 1], hue = sc_data.obs['cell_type'], s = 8, palette = cell_type_palette, 
                legend = False)
plt.title("scRNA-seq Latent")
plt.xlim([xmin, xmax])
plt.ylim([ymin, ymax])
plt.axis('off')

plt.subplot(122)
sns.scatterplot(x = st_data.obsm['latent_umap'][:, 0], 
                y = st_data.obsm['latent_umap'][:, 1],  hue = st_data.obs['cell_type'], s = 8, palette = cell_type_palette, legend = True)


legend = plt.legend(title = 'Cell Type', prop={'size': 12}, fontsize = '12',  markerscale = 3, ncol = 2, bbox_to_anchor = (1, 1))#, loc = 'lower left')
plt.setp(legend.get_title(),fontsize='12')
plt.title("MERFISH Latent")
plt.axis('off')
plt.tight_layout()
plt.xlim([xmin, xmax])
plt.ylim([ymin, ymax])
plt.show()
```

Example 29 (unknown):
```unknown
st_data_sst = st_data[st_data.obs['cell_type'] == 'Sst']
sc_data_sst = sc_data[sc_data.obs['cell_type'] == 'Sst']
```

Example 30 (unknown):
```unknown
gran_sst_palette = {'Th': (0.0, 0.294118, 0.0, 1.0),
                    'Calb2': (0.560784, 0.478431, 0.0, 1.0),
                    'Chodl': (1.0, 0.447059, 0.4, 1.0),
                    'Myh8': (0.933333, 0.72549, 0.72549, 1.0),
                    'Crhr2': (0.368627, 0.494118, 0.4, 1.0),
                    'Hpse': (0.65098, 0.482353, 0.72549, 1.0),
                    'Hspe': (0.352941, 0.0, 0.643137, 1.0),
                    'Crh': (0.607843, 0.894118, 1.0, 1.0),
                    'Pvalb Etv1': (0.92549, 0.0, 0.466667, 1.0)}
```

Example 31 (python):
```python
import scipy.sparse
```

Example 32 (python):
```python
def flatten(x):
    return(x.reshape([x.shape[0], -1]))

def run_diffusion_maps(data_df, n_components=10, knn=30, alpha=0):
    """Run Diffusion maps using the adaptive anisotropic kernel
    :param data_df: PCA projections of the data or adjacency matrix
    :param n_components: Number of diffusion components
    :param knn: Number of nearest neighbors for graph construction
    :param alpha: Normalization parameter for the diffusion operator
    :return: Diffusion components, corresponding eigen values and the diffusion operator
    """

    # Determine the kernel
    N = data_df.shape[0]

    if(type(data_df).__module__ == np.__name__):
        data_df = pd.DataFrame(data_df)

    if not scipy.sparse.issparse(data_df):
        print("Determing nearest neighbor graph...")
        temp = sc.AnnData(data_df.values)
        sc.pp.neighbors(temp, n_pcs=0, n_neighbors=knn)
        kNN = temp.obsp['distances']

        # Adaptive k
        adaptive_k = int(np.floor(knn / 3))
        adaptive_std = np.zeros(N)

        for i in np.arange(len(adaptive_std)):
            adaptive_std[i] = np.sort(kNN.data[kNN.indptr[i] : kNN.indptr[i + 1]])[
                adaptive_k - 1
            ]

        # Kernel
        x, y, dists = scipy.sparse.find(kNN)

        # X, y specific stds
        dists = dists / adaptive_std[x]
        W = scipy.sparse.csr_matrix((np.exp(-dists), (x, y)), shape=[N, N])

        # Diffusion components
        kernel = W + W.T
    else:
        kernel = data_df

    # Markov
    D = np.ravel(kernel.sum(axis=1))

    if alpha > 0:
        # L_alpha
        D[D != 0] = D[D != 0] ** (-alpha)
        mat = scipy.sparse.csr_matrix((D, (range(N), range(N))), shape=[N, N])
        kernel = mat.dot(kernel).dot(mat)
        D = np.ravel(kernel.sum(axis=1))

    D[D != 0] = 1 / D[D != 0]
    T = scipy.sparse.csr_matrix((D, (range(N), range(N))), shape=[N, N]).dot(kernel)
    # Eigen value dcomposition
    D, V = scipy.sparse.linalg.eigs(T, n_components, tol=1e-4, maxiter=1000)
    D = np.real(D)
    V = np.real(V)
    inds = np.argsort(D)[::-1]
    D = D[inds]
    V = V[:, inds]

    # Normalize
    for i in range(V.shape[1]):
        V[:, i] = V[:, i] / np.linalg.norm(V[:, i])

    return V[:, 1:]
```

Example 33 (python):
```python
fit = umap.UMAP(
    n_neighbors = 30,
    min_dist = 0.1,
    n_components = 2,
)

UMAP_COVET = fit.fit_transform(np.concatenate([flatten(st_data_sst.obsm['COVET_SQRT']), 
                                               flatten(sc_data_sst.obsm['COVET_SQRT'])], axis = 0))

st_data_sst.obsm['UMAP_COVET'] = UMAP_COVET[:st_data_sst.shape[0]]
sc_data_sst.obsm['UMAP_COVET'] = UMAP_COVET[st_data_sst.shape[0]:]
```

Example 34 (python):
```python
DC_COVET = run_diffusion_maps(np.concatenate([flatten(st_data_sst.obsm['COVET_SQRT']), 
                                              flatten(sc_data_sst.obsm['COVET_SQRT'])], axis = 0))

st_data_sst.obsm['DC_COVET'] = DC_COVET[:st_data_sst.shape[0]]
sc_data_sst.obsm['DC_COVET'] = DC_COVET[st_data_sst.shape[0]:]
```

Example 35 (unknown):
```unknown
Determing nearest neighbor graph...
```

Example 36 (python):
```python
st_data_sst.obsm['DC_COVET'] = -DC_COVET[:st_data_sst.shape[0]]
sc_data_sst.obsm['DC_COVET'] = -DC_COVET[st_data_sst.shape[0]:]
```

Example 37 (python):
```python
lim_arr = np.concatenate([st_data_sst.obsm['UMAP_COVET'], sc_data_sst.obsm['UMAP_COVET']], axis = 0)


delta = 1
pre = 0.01
xmin = np.percentile(lim_arr[:, 0], pre) - delta 
xmax = np.percentile(lim_arr[:, 0], 100 - pre) + delta
ymin = np.percentile(lim_arr[:, 1], pre) - delta 
ymax = np.percentile(lim_arr[:, 1], 100 - pre) + delta
```

Example 38 (python):
```python
plt.figure(figsize=(10,5))

plt.subplot(121)
sns.scatterplot(x = sc_data_sst.obsm['UMAP_COVET'][:, 0], 
                y = sc_data_sst.obsm['UMAP_COVET'][:, 1],  
                hue = sc_data_sst.obs['cluster_label'], s = 16,  palette= gran_sst_palette, legend = True)
plt.tight_layout()
plt.xlim([xmin, xmax])
plt.ylim([ymin, ymax])
plt.title('scRNA-seq Sst, COVET FDL')
legend = plt.legend(title = 'Sst subtype', prop={'size': 8}, fontsize = '8',  markerscale = 1, ncol = 2)
plt.axis('off')

plt.subplot(122)
ax = sns.scatterplot(x = st_data_sst.obsm['UMAP_COVET'][:, 0], 
                y = st_data_sst.obsm['UMAP_COVET'][:, 1],  
                c = st_data_sst.obsm['DC_COVET'][:,0], s = 16,  cmap= 'cet_CET_D13', legend = False)
plt.tight_layout()
plt.xlim([xmin, xmax])
plt.ylim([ymin, ymax])
plt.axis('off')
plt.title('MERFISH Sst, COVET FDL')
plt.show()
```

Example 39 (python):
```python
fig = plt.figure(figsize=(25,5))

for ind, batch in enumerate(['mouse1_slice212', 'mouse1_slice162', 'mouse1_slice71', 'mouse2_slice270', 'mouse1_slice40']):
    st_dataBatch = st_data[st_data.obs['batch'] == batch]
    st_dataPlotBatch = st_data_sst[st_data_sst.obs['batch'] == batch]
    
    plt.subplot(1,5, 1+ ind)
    sns.scatterplot(x = st_dataBatch.obsm['spatial'][:, 0], y = st_dataBatch.obsm['spatial'][:, 1],  color = (207/255,185/255,151/255, 1))
    sns.scatterplot(x = st_dataPlotBatch.obsm['spatial'][:, 0], y = st_dataPlotBatch.obsm['spatial'][:, 1], marker = '^',
                        c = st_dataPlotBatch.obsm['DC_COVET'][:, 0], s = 256,  cmap= 'cet_CET_D13', legend = False)
    plt.title(batch)
    plt.axis('off')
    plt.tight_layout()
    
plt.show()
```

Example 40 (python):
```python
depth_df = pd.DataFrame()
depth_df['Subtype'] = sc_data_sst.obs['cluster_label']
depth_df['Depth'] = -sc_data_sst.obsm['DC_COVET'][:,0]
```

Example 41 (unknown):
```unknown
subtype_depth_order = depth_df.groupby(['Subtype']).mean().sort_values(by = 'Depth', ascending=False).index
```

Example 42 (python):
```python
plt.figure(figsize=(12,5))
sns.set(font_scale=1.7) 
sns.set_style("whitegrid")
sns.boxenplot(depth_df, x = 'Subtype', y = 'Depth',# bw = 1, width = 0.9,
          order = subtype_depth_order, 
          palette = gran_sst_palette)
plt.tight_layout()
plt.show()
```

Example 43 (python):
```python
subtype_canonical = pd.DataFrame([sc_data_sst[sc_data_sst.obs['cluster_label']==subtype].obsm['cell_type_niche'].mean(axis = 0) for subtype in subtype_depth_order],
                                     index = subtype_depth_order, columns = sc_data.obsm['cell_type_niche'].columns)
```

Example 44 (unknown):
```unknown
subtype_canonical[subtype_canonical<0.2] = 0
subtype_canonical.drop(labels=subtype_canonical.columns[(subtype_canonical == 0).all()], axis=1, inplace=True)
subtype_canonical = subtype_canonical.div(subtype_canonical.sum(axis=1), axis=0)
```

Example 45 (python):
```python
subtype_canonical.plot(kind = 'bar', stacked = 'True', 
                       color = {col:cell_type_palette[col] for col in subtype_canonical.columns})
plt.legend(bbox_to_anchor = (1,1), ncols = 1, fontsize = 'x-small')
plt.title("Predicted Niche Composition")
plt.ylabel("Proportion")
plt.xlabel("Sst Subtype")
plt.show()
```

Example 46 (python):
```python
tick_genes = np.asarray(['Adamts18','Pamr1', 'Dkkl1', 'Hs6st2', 'Slit1', 'Ighm'])
```

Example 47 (python):
```python
plt.figure(figsize=(15,10))

for ind, gene in enumerate(tick_genes):
    plt.subplot(2,3,1+ind)
    
    cvec = np.log(st_data[st_data.obs['batch'] == 'mouse1_slice10'].obsm['imputation'][gene] + 0.1)
    sns.scatterplot(x = st_data.obsm['spatial'][st_data.obs['batch'] == 'mouse1_slice10'][:, 1], 
                    y = -st_data.obsm['spatial'][st_data.obs['batch'] == 'mouse1_slice10'][:, 0], legend = False,
                    c = cvec, cmap = 'Reds',
                    vmax = np.percentile(cvec, 95), vmin = np.percentile(cvec, 30),
                    s = 24, edgecolor = 'k')#, palette = cell_type_palette)
    plt.title(gene)
    plt.axis('equal')
    plt.axis('off')
    plt.tight_layout()
plt.show()
```

---

## 

**URL:** http://127.0.0.1:9162/py_html/ENVI.html

**Examples:**

Example 1 (python):
```python
from functools import partial

import jax
import jax.numpy as jnp
import numpy as np
import optax
import pandas as pd
import scanpy as sc
import sklearn.neighbors
import tensorflow_probability.substrates.jax as jax_prob # type: ignore
from flax import linen as nn
from jax import jit, random
from tqdm import trange, tqdm

from scenvi._dists import (
    KL,
    AOT_Distance,
    log_nb_pdf,
    log_normal_pdf,
    log_pos_pdf,
    log_zinb_pdf,
)

from scenvi.utils import CVAE, Metrics, TrainState, compute_covet, niche_cell_type


class ENVI:
    """
    Initializes the ENVI model & computes COVET for spatial data

    :param spatial_data: (anndata) spatial transcriptomics data, with an obsm indicating spatial location of spot/segmented cell
    :param sc_data: (anndata) complementary sinlge cell data
    :param spatial_key: (str) obsm key name with physical location of spots/cells (default 'spatial')
    :param batch_key: (str) obs key name of batch/sample of spatial data (default 'batch' if in spatial_data.obs, else -1)
    :param num_layers: (int) number of neural network for decoders and encoders (default 3)
    :param num_neurons: (int) number of neurons in each layer (default 1024)
    :param latent_dim: (int) size of ENVI latent dimention (size 512)
    :param k_nearest: (int) number of physical neighbours to describe niche (default 8)
    :param covet_batch_size: (int) batch size for COVET computation (default 256)
    :param num_cov_genes: (int) number of HVGs to compute niche covariance with (default ֿ64), if -1 uses all genes
    :param cov_genes: (list of str) manual genes to compute niche with (default None)
    :param num_HVG: (int) number of HVGs to keep for single cell data (default 2048)
    :param sc_genes: (list of str) manual genes to keep for sinlge cell data (default None)
    :param spatial_dist: (str) distribution used to describe spatial data (default pois, could be 'pois', 'nb', 'zinb' or 'norm')
    :param sc_dist: (str) distribution used to describe sinlge cell data (default nb, could be 'pois', 'nb', 'zinb' or 'norm')
    :param spatial_coeff: (float) coefficient for spatial expression loss in total ELBO (default 1.0)
    :param sc_coeff: (float) coefficient for sinlge cell expression loss in total ELBO (default 1.0)
    :param cov_coeff: (float) coefficient for spatial niche loss in total ELBO (default 1.0)
    :param kl_coeff: (float) coefficient for latent prior loss in total ELBO (default 1.0)
    :param log_input: (float) if larger than zero, a log is applied to ENVI input with pseudocount of log_input (default 0.1)
    :param stable_eps: (float) added value to log probabilty calculations to avoid NaNs during training (default 1e-6)
    :param covet_use_obsm: (str) obsm key to use for COVET calculation instead of gene expression (default None)
    :param covet_use_layer: (str) layer to use for COVET calculation instead of log-transformed X (default None)

    :return: initialized ENVI model
    """

    def __init__(
        self,
        spatial_data,
        sc_data,
        spatial_key="spatial",
        batch_key="batch",
        num_layers=3,
        num_neurons=1024,
        latent_dim=512,
        k_nearest=8,
        covet_batch_size=256,
        num_cov_genes=64,
        cov_genes=None,
        num_HVG=2048,
        sc_genes=None,
        spatial_dist="pois",
        sc_dist="nb",
        spatial_coeff=1,
        sc_coeff=1,
        cov_coeff=1,
        kl_coeff=0.3,
        log_input=0.1,
        stable_eps=1e-6,
        covet_use_obsm=None,
        covet_use_layer=None,
    ):
        
        self.spatial_data, self.sc_data, self.overlap_genes, self.non_overlap_genes = self._prepare_gene_sets(
            spatial_data, sc_data, num_HVG, sc_genes
        )

        if batch_key not in spatial_data.obs.columns:
            batch_key = -1

        self.k_nearest = k_nearest
        self.spatial_key = spatial_key
        self.batch_key = batch_key
        self.cov_genes = cov_genes
        self.num_cov_genes = min(num_cov_genes, self.spatial_data.shape[1])
        self.covet_use_obsm = covet_use_obsm
        self.covet_use_layer = covet_use_layer

        print("Computing Niche Covariance Matrices")

        # Add information about which data source is being used for COVET
        if self.covet_use_obsm is not None:
            print(f"Using obsm '{self.covet_use_obsm}' for COVET calculation")
        elif self.covet_use_layer is not None:
            print(f"Using layer '{self.covet_use_layer}' for COVET calculation")
        else:
            print("Using log-transformed gene expression for COVET calculation")

        (
            self.spatial_data.obsm["COVET"],
            self.spatial_data.obsm["COVET_SQRT"],
            self.CovGenes,
        ) = compute_covet(
            spatial_data=self.spatial_data,
            k=self.k_nearest,
            g=self.num_cov_genes,
            genes=self.cov_genes,
            spatial_key=self.spatial_key,
            batch_key=self.batch_key,
            batch_size=covet_batch_size,
            use_obsm=self.covet_use_obsm,
            use_layer=self.covet_use_layer
        )

        self.overlap_num = self.overlap_genes.shape[0]
        self.cov_gene_num = self.spatial_data.obsm["COVET_SQRT"].shape[-1]
        self.full_trans_gene_num = self.sc_data.shape[-1]

        self.num_layers = num_layers
        self.num_neurons = num_neurons
        self.latent_dim = latent_dim

        self.spatial_dist = spatial_dist
        self.sc_dist = sc_dist

        self.dist_size_dict = {"pois": 1, "nb": 2, "zinb": 3, "norm": 1}

        self.exp_dec_size = (
            self.dist_size_dict[self.sc_dist] * self.sc_data.shape[-1]
            + (self.dist_size_dict[self.spatial_dist] - 1) * self.spatial_data.shape[-1]
        )

        self.spatial_coeff = spatial_coeff
        self.sc_coeff = sc_coeff
        self.cov_coeff = cov_coeff
        self.kl_coeff = kl_coeff

        if self.sc_dist == "norm" or self.spatial_dist == "norm" or self.spatial_data.X.min()<0 or self.sc_data.X.min()<0:
            self.log_input = -1
        else:
            self.log_input = log_input

        self.eps = stable_eps

        self.model = CVAE(
            n_layers=self.num_layers,
            n_neurons=self.num_neurons,
            n_latent=self.latent_dim,
            n_output_exp=self.exp_dec_size,
            n_output_cov=int(self.cov_gene_num * (self.cov_gene_num + 1) / 2),
        )

        print("Finished Initializing ENVI")

    def inp_log_fn(self, x):
        """
        :meta private:
        """

        if self.log_input > 0:
            return jnp.log(x + self.log_input)
        return x

    def _prepare_gene_sets(self, spatial_data, sc_data, num_HVG, user_provided_genes=None):
        """
        :meta private:
        """
        print("Preparing gene sets for ENVI analysis...")
        
        
        # Make copies to avoid modifying inputs
        spatial_obj = spatial_data.copy()
        sc_obj = sc_data.copy()
        
        # First restrict spatial data to genes also in single-cell data
        common_genes = np.intersect1d(spatial_obj.var_names, sc_obj.var_names)
        spatial_obj = spatial_obj[:, common_genes]
        
        # Identify highly variable genes if not already done
        if "highly_variable" not in sc_obj.var.columns:
            log_layer = None
            # Find or create appropriate log-transformed layer
            if 'log' in sc_obj.layers.keys():
                log_layer = "log"
            elif 'log1p' in sc_obj.layers.keys():
                log_layer = "log1p"
            elif sc_obj.X.min() < 0:
                # Data already log-transformed
                pass
            else:
                # Create log-transformed layer
                sc_obj.layers["log"] = np.log(sc_obj.X + 1)
                log_layer = "log"
                    
            # Identify highly variable genes
            if log_layer:
                sc.pp.highly_variable_genes(sc_obj, n_top_genes=num_HVG, layer=log_layer)
            else:
                sc.pp.highly_variable_genes(sc_obj, n_top_genes=num_HVG)
            
            print(f"Identified {num_HVG} highly variable genes from single-cell data")
        else:
            print("Using pre-computed highly variable genes from single-cell data")
        
        # Store raw data if not already s tored
        if sc_obj.raw is None:
            sc_obj.raw = sc_obj
                
        # Determine genes to keep in single-cell data
        hvg_genes = sc_obj.var_names[sc_obj.var.highly_variable]
        genes_to_keep = np.union1d(hvg_genes, spatial_obj.var_names)
        
        # Add user-provided genes if any
        if user_provided_genes and len(user_provided_genes) > 0:
            genes_to_keep = np.union1d(genes_to_keep, user_provided_genes)
                
        # Subset single-cell data to genes of interest
        sc_obj = sc_obj[:, genes_to_keep]
        
        # Identify overlap and non-overlap genes
        overlap_genes = np.intersect1d(spatial_obj.var_names, sc_obj.var_names)
        non_overlap_genes = np.setdiff1d(sc_obj.var_names, spatial_obj.var_names)
        
        print(f"Gene selection: {len(overlap_genes)} shared genes, {len(non_overlap_genes)} unique to single-cell")
        
        # Final filtering of both datasets
        spatial_obj = spatial_obj[:, overlap_genes]
        sc_obj = sc_obj[:, np.concatenate([overlap_genes, non_overlap_genes])]
        
        return spatial_obj, sc_obj, overlap_genes, non_overlap_genes
    
    def mean_sc(self, sc_inp):
        """
        :meta private:
        """

        sc_inp = sc_inp[:, : self.dist_size_dict[self.sc_dist] * self.sc_data.shape[-1]]
        if self.sc_dist == "zinb":
            sc_r, sc_p, sc_d = jnp.split(sc_inp, 3, axis=-1)
            return nn.softplus(sc_r) * jnp.exp(sc_p) * (1 - nn.sigmoid(sc_d))
        if self.sc_dist == "nb":
            sc_r, sc_p = jnp.split(sc_inp, 2, axis=-1)
            return nn.softplus(sc_r) * jnp.exp(sc_p)
        if self.sc_dist == "pois":
            sc_l = sc_inp
            return sc_l
        if self.sc_dist == "norm":
            sc_l = sc_inp
            return sc_l

    def mean_spatial(self, spatial_inp):
        """
        :meta private:
        """

        if self.spatial_dist == "zinb" or self.spatial_dist == "nb":
            spatial_inp = jnp.concatenate(
                [
                    spatial_inp[:, : self.spatial_data.shape[-1]],
                    spatial_inp[
                        :,
                        -(self.dist_size_dict[self.spatial_dist] - 1)
                        * self.spatial_data.shape[-1] :,
                    ],
                ],
                axis=-1,
            )
        else:
            spatial_inp = spatial_inp[:, : self.spatial_data.shape[-1]]

        if self.spatial_dist == "zinb":
            spatial_r, spatial_p, spatial_d = jnp.split(spatial_inp, 3, axis=-1)
            return (
                nn.softplus(spatial_r)
                * jnp.exp(spatial_p)
                * (1 - nn.sigmoid(spatial_d))
            )
        if self.spatial_dist == "nb":
            spatial_r, spatial_p = jnp.split(spatial_inp, 2, axis=-1)
            return nn.softplus(spatial_r) * jnp.exp(spatial_p)
        if self.spatial_dist == "pois":
            spatial_l = spatial_inp
            return spatial_l
        if self.spatial_dist == "norm":
            spatial_l = spatial_inp
            return spatial_l

    def factor_sc(self, sc_inp, dec_exp):
        """
        :meta private:
        """

        sc_neurons = dec_exp[
            :, : self.dist_size_dict[self.sc_dist] * self.sc_data.shape[-1]
        ]

        if self.sc_dist == "zinb":
            sc_r, sc_p, sc_d = jnp.split(sc_neurons, 3, axis=-1)
            sc_like = jnp.mean(
                log_zinb_pdf(sc_inp, nn.softplus(sc_r) + self.eps, sc_p, sc_d)
            )
        if self.sc_dist == "nb":
            sc_r, sc_p = jnp.split(sc_neurons, 2, axis=-1)
            sc_like = jnp.mean(log_nb_pdf(sc_inp, nn.softplus(sc_r) + self.eps, sc_p))
        if self.sc_dist == "pois":
            sc_l = sc_neurons
            sc_like = jnp.mean(log_pos_pdf(sc_inp, nn.softplus(sc_l) + self.eps))
        if self.sc_dist == "norm":
            sc_l = sc_neurons
            sc_like = jnp.mean(log_normal_pdf(sc_inp, sc_l))
        return sc_like

    def factor_spatial(self, spatial_inp, dec_exp):
        """
        :meta private:
        """

        if self.spatial_dist == "zinb" or self.spatial_dist == "nb":
            spatial_neurons = jnp.concatenate(
                [
                    dec_exp[:, : self.spatial_data.shape[-1]],
                    dec_exp[
                        :,
                        -(self.dist_size_dict[self.spatial_dist] - 1)
                        * self.spatial_data.shape[-1] :,
                    ],
                ],
                axis=-1,
            )
        else:
            spatial_neurons = dec_exp[:, : self.spatial_data.shape[-1]]

        if self.spatial_dist == "zinb":
            spatial_r, spatial_p, spatial_d = jnp.split(spatial_neurons, 3, axis=-1)
            spatial_like = jnp.mean(
                log_zinb_pdf(
                    spatial_inp, nn.softplus(spatial_r) + self.eps, spatial_p, spatial_d
                )
            )
        if self.spatial_dist == "nb":
            spatial_r, spatial_p = jnp.split(spatial_neurons, 2, axis=-1)
            spatial_like = jnp.mean(
                log_nb_pdf(spatial_inp, nn.softplus(spatial_r) + self.eps, spatial_p)
            )
        if self.spatial_dist == "pois":
            spatial_l = spatial_neurons
            spatial_like = jnp.mean(
                log_pos_pdf(spatial_inp, nn.softplus(spatial_l) + self.eps)
            )
        if self.spatial_dist == "norm":
            spatial_l = spatial_neurons
            spatial_like = jnp.mean(log_normal_pdf(spatial_inp, spatial_l))
        return spatial_like

    def grammian_cov(self, dec_cov):
        """
        :meta private:
        """

        dec_cov = jax_prob.math.fill_triangular(dec_cov)
        return jnp.matmul(dec_cov, dec_cov.transpose([0, 2, 1]))

    def create_train_state(self, key=random.key(0), init_lr=3e-4, decay_steps=100):
        """
        :meta private:
        """

        key, subkey1, subkey2 = random.split(key, num=3)
        params = self.model.init(
            rngs={"params": subkey1},
            x=self.inp_log_fn(self.spatial_data.X[0:1]),
            mode="spatial",
            key=subkey2,
        )["params"]

        lr_sched = optax.exponential_decay(init_lr, decay_steps, 0.99, staircase=False)
        tx = optax.adam(lr_sched)  #

        return TrainState.create(
            apply_fn=self.model.apply, params=params, tx=tx, metrics=Metrics.empty()
        )

    @partial(jit, static_argnums=(0,))
    def train_step(self, state, spatial_inp, spatial_COVET, sc_inp, key=random.key(0)):
        """
        :meta private:
        """

        key, subkey1, subkey2 = random.split(key, num=3)

        def loss_fn(params):
            spatial_enc_mu, spatial_enc_logstd, spatial_dec_exp, spatial_dec_cov = (
                state.apply_fn(
                    {"params": params},
                    x=self.inp_log_fn(spatial_inp),
                    mode="spatial",
                    key=subkey1,
                )
            )
            sc_enc_mu, sc_enc_logstd, sc_dec_exp = state.apply_fn(
                {"params": params},
                x=self.inp_log_fn(sc_inp[:, : spatial_inp.shape[-1]]),
                mode="sc",
                key=subkey2,
            )

            spatial_exp_like = self.factor_spatial(spatial_inp, spatial_dec_exp)
            sc_exp_like = self.factor_sc(sc_inp, sc_dec_exp)
            spatial_cov_like = jnp.mean(
                AOT_Distance(spatial_COVET, self.grammian_cov(spatial_dec_cov))
            )
            kl_div = jnp.mean(KL(spatial_enc_mu, spatial_enc_logstd)) + jnp.mean(
                KL(sc_enc_mu, sc_enc_logstd)
            )

            loss = (
                -self.spatial_coeff * spatial_exp_like
                - self.sc_coeff * sc_exp_like
                - self.cov_coeff * spatial_cov_like
                + self.kl_coeff * kl_div
            )

            return (
                loss,
                [sc_exp_like, spatial_exp_like, spatial_cov_like, kl_div * 0.5],
            )

        grad_fn = jax.value_and_grad(loss_fn, has_aux=True)
        loss, grads = grad_fn(state.params)
        state = state.apply_gradients(grads=grads)
        return (state, loss)

    def train(
        self,
        training_steps=10000,
        batch_size=128,
        verbose=16,
        init_lr=3e-4,
        decay_steps=100,
        key=random.key(0),
    ):
        """
        Set up optimization parameters and train the ENVI model


        :param training_steps: (int) number of gradient descent steps to train ENVI (default 16000)
        :param batch_size: (int) size of spatial and single-cell profiles sampled for each training step  (default 128)
        :param verbose: (int) amount of steps between each loss print statement (default 16)
        :param init_lr: (float) initial learning rate for ADAM optimizer with exponential decay (default 1e-4)
        :param decay_steps: (int) number of steps before each learning rate decay (default 4000)
        :param key: (jax.random.key) random seed (default jax.random.key(0))

        :return: nothing
        """

        batch_size = min(
            self.sc_data.shape[0], min(self.spatial_data.shape[0], batch_size)
        )

        key, subkey = random.split(key)
        state = self.create_train_state(
            subkey, init_lr=init_lr, decay_steps=decay_steps
        )
        self.params = state.params

        tq = trange(training_steps, leave=True, desc="")
        sc_loss_mean, spatial_loss_mean, cov_loss_mean, kl_loss_mean, count = (
            0,
            0,
            0,
            0,
            0,
        )

        sc_X = self.sc_data.X
        spatial_X = self.spatial_data.X
        spatial_COVET = self.spatial_data.obsm["COVET_SQRT"]

        for training_step in tq:
            key, subkey1, subkey2 = random.split(key, num=3)

            batch_spatial_ind = random.choice(
                key=subkey1,
                a=self.spatial_data.shape[0],
                shape=[batch_size],
                replace=False,
            )
            batch_sc_ind = random.choice(
                key=subkey2, a=self.sc_data.shape[0], shape=[batch_size], replace=False
            )

            batch_spatial_exp, batch_spatial_cov = (
                spatial_X[batch_spatial_ind],
                spatial_COVET[batch_spatial_ind],
            )
            batch_sc_exp = sc_X[batch_sc_ind]

            key, subkey = random.split(key)

            state, loss = self.train_step(
                state, batch_spatial_exp, batch_spatial_cov, batch_sc_exp, key=subkey
            )

            self.params = state.params

            sc_loss_mean, spatial_loss_mean, cov_loss_mean, kl_loss_mean, count = (
                sc_loss_mean + loss[1][0],
                spatial_loss_mean + loss[1][1],
                cov_loss_mean + loss[1][2],
                kl_loss_mean + loss[1][3],
                count + 1,
            )

            if training_step % verbose == 0:
                print_statement = ""
                for metric, value in zip(
                    ["spatial", "sc", "cov", "kl"],
                    [spatial_loss_mean, sc_loss_mean, cov_loss_mean, kl_loss_mean],
                ):
                    print_statement = (
                        print_statement
                        + " "
                        + metric
                        + ": {:.3e}".format(value / count)
                    )

                sc_loss_mean, spatial_loss_mean, cov_loss_mean, kl_loss_mean, count = (
                    0,
                    0,
                    0,
                    0,
                    0,
                )
                tq.set_description(print_statement)
                tq.refresh()  # to show

        self.latent_rep()

    # @partial(jit, static_argnums=(0,))
    def model_encoder(self, x):
        """
        :meta private:
        """

        return self.model.bind({"params": self.params}).encoder(x)

    # @partial(jit, static_argnums=(0,))
    def model_decoder_exp(self, x):
        """
        :meta private:
        """

        return self.model.bind({"params": self.params}).decoder_exp(x)

    # @partial(jit, static_argnums=(0,))
    def model_decoder_cov(self, x):
        """
        :meta private:
        """
        return self.model.bind({"params": self.params}).decoder_cov(x)

    def encode(self, x, mode="spatial", max_batch=64):
        """
        :meta private:
        """

        conf_const = 0 if mode == "spatial" else 1
        conf_neurons = jax.nn.one_hot(
            conf_const * jnp.ones(x.shape[0], dtype=jnp.int8), 2, dtype=jnp.float32
        )

        x_conf = jnp.concatenate([self.inp_log_fn(x), conf_neurons], axis=-1)

        if x_conf.shape[0] < max_batch:
            print("Encoding")
            enc = jnp.split(self.model_encoder(x_conf), 2, axis=-1)[0]
        else:  # For when the GPU can't pass all point-clouds at once
            num_split = int(x_conf.shape[0] / max_batch) + 1
            x_conf_split = np.array_split(x_conf, num_split)
            enc = np.concatenate(
                [
                    jnp.split(self.model_encoder(x_conf_split[split_ind]), 2, axis=-1)[
                        0
                    ]
                    for split_ind in tqdm(range(num_split), desc="Encoding", leave=True)
                ],
                axis=0,
            )
        return enc

    def decode_exp(self, x, mode="spatial", max_batch=64):
        """
        :meta private:
        """

        conf_const = 0 if mode == "spatial" else 1
        conf_neurons = jax.nn.one_hot(
            conf_const * jnp.ones(x.shape[0], dtype=jnp.int8), 2, dtype=jnp.float32
        )

        x_conf = jnp.concatenate([x, conf_neurons], axis=-1)

        if mode == "spatial":
            if x_conf.shape[0] < max_batch:
                print("Decoding expression")
                dec = self.mean_spatial(self.model_decoder_exp(x_conf))
            else:  # For when the GPU can't pass all point-clouds at once
                num_split = int(x_conf.shape[0] / max_batch) + 1
                x_conf_split = np.array_split(x_conf, num_split)
                dec = np.concatenate(
                    [
                        self.mean_spatial(
                            self.model_decoder_exp(x_conf_split[split_ind])
                        )
                        for split_ind in tqdm(range(num_split), desc="Decoding expression", leave=True)
                    ],
                    axis=0,
                ) 
        else:
            if x_conf.shape[0] < max_batch:
                print("Decoding expression")
                dec = self.mean_sc(
                    self.model.bind({"params": self.params}).decoder_exp(x_conf)
                )
            else:  # For when the GPU can't pass all point-clouds at once
                num_split = int(x_conf.shape[0] / max_batch) + 1
                x_conf_split = np.array_split(x_conf, num_split)
                dec = np.concatenate(
                    [
                        self.mean_sc(self.model_decoder_exp(x_conf_split[split_ind]))
                        for split_ind in tqdm(range(num_split), desc="Decoding expression", leave=True)
                    ],
                    axis=0,
                )
        return dec

    def decode_cov(self, x, max_batch=64):
        """
        :meta private:
        """

        if x.shape[0] < max_batch:
            print("Decoding covet")
            dec = self.grammian_cov(self.model_decoder_cov(x))
        else:  # For when the GPU can't pass all point-clouds at once
            num_split = int(x.shape[0] / max_batch) + 1
            x_split = np.array_split(x, num_split)
            dec = np.concatenate(
                [
                    self.grammian_cov(self.model_decoder_cov(x_split[split_ind]))
                    for split_ind in tqdm(range(num_split), desc="Decoding covet", leave=True)
                ],
                axis=0,
            )
        return dec

    def latent_rep(self):
        """
        Compute latent embeddings for spatial and single cell data, automatically performed after training

        :return: nothing, adds 'envi_latent' self.spatial_data.obsm and self.spatial_data.obsm
        """
        print("Computing latent representations")
        self.spatial_data.obsm["envi_latent"] = np.asarray(self.encode(
            self.spatial_data.X, mode="spatial"
        ))
        self.sc_data.obsm["envi_latent"] = np.asarray(self.encode(
            self.sc_data[:, self.spatial_data.var_names].X, mode="sc"
        ))

    def impute_genes(self):
        """
        Impute full transcriptome for spatial data

        :return: nothing, adds 'imputation' to self.spatial_data.obsm
        """
        print("Imputing missing genes for spatial data")
        self.spatial_data.obsm["imputation"] = pd.DataFrame(
            self.decode_exp(self.spatial_data.obsm["envi_latent"], mode="sc"),
            columns=self.sc_data.var_names,
            index=self.spatial_data.obs_names,
        )


    def infer_niche_covet(self):
        """
        Predict COVET representation for single-cell data

        :return: nothing, adds 'COVET_SQRT' and 'COVET' to self.sc_data.obsm
        """
        print("Infering niche COVET representation for single-cell data")
        self.sc_data.obsm["COVET_SQRT"] = np.asarray(self.decode_cov(
            self.sc_data.obsm["envi_latent"]
        ))
        self.sc_data.obsm["COVET"] = np.matmul(
            self.sc_data.obsm["COVET_SQRT"], self.sc_data.obsm["COVET_SQRT"]
        )

    def infer_niche_celltype(self, cell_type_key="cell_type"):
        """
        Predict cell type abundence based one ENVI-inferred COVET representations

        :param cell_type_key: (string) key in spatial_data.obs where cell types are stored for environment composition (default 'cell_type')

        :return: nothing, adds 'niche_cell_type' to self.sc_data.obsm & self.spatial_data.obsm
        """
        print("Infering cell type niche composition for single cell data")
        self.spatial_data.obsm["cell_type_niche"] = niche_cell_type(
            self.spatial_data,
            self.k_nearest,
            spatial_key=self.spatial_key,
            cell_type_key=cell_type_key,
            batch_key=self.batch_key,
        )

        regression_model = sklearn.neighbors.KNeighborsRegressor(n_neighbors=5).fit(
            self.spatial_data.obsm["COVET_SQRT"].reshape(
                [self.spatial_data.shape[0], -1]
            ),
            self.spatial_data.obsm["cell_type_niche"],
        )

        sc_cell_type = regression_model.predict(
            self.sc_data.obsm["COVET_SQRT"].reshape([self.sc_data.shape[0], -1])
        )

        self.sc_data.obsm["cell_type_niche"] = pd.DataFrame(
            sc_cell_type,
            index=self.sc_data.obs_names,
            columns=self.spatial_data.obsm["cell_type_niche"].columns,
        )
```

---

## ENVI¶

**URL:** http://127.0.0.1:9162/docs/build/html/ENVI.html

**Contents:**
- ENVI¶

---

## 

**URL:** http://127.0.0.1:9162/py_html/test_ENVI.html

**Examples:**

Example 1 (python):
```python
import pytest # type: ignore

import anndata
import numpy as np

import scenvi

@pytest.fixture
def example_model():
    st_data = anndata.AnnData(X=np.random.uniform(low=0, high=100, size=(16, 4)), 
                             obsm={'spatial': np.random.normal(size=[16, 2])})
    sc_data = anndata.AnnData(X=np.random.uniform(low=0, high=100, size=(16, 8)))
    
    envi_model = scenvi.ENVI(spatial_data=st_data, sc_data=sc_data, batch_key=-1)
    return envi_model

@pytest.fixture
def example_model_with_hvg():
    # Create data with pre-computed HVGs
    st_data = anndata.AnnData(X=np.random.uniform(low=0, high=100, size=(16, 4)), 
                             obsm={'spatial': np.random.normal(size=[16, 2])})
    sc_data = anndata.AnnData(X=np.random.uniform(low=0, high=100, size=(16, 8)))
    
    # Add highly_variable column
    sc_data.var['highly_variable'] = [True, False, True, False, True, False, True, False]
    
    envi_model = scenvi.ENVI(spatial_data=st_data, sc_data=sc_data, batch_key=-1)
    return envi_model

@pytest.fixture
def example_model_with_user_genes():
    st_data = anndata.AnnData(X=np.random.uniform(low=0, high=100, size=(16, 4)), 
                             obsm={'spatial': np.random.normal(size=[16, 2])})
    st_data.var_names = [f"gene{i}" for i in range(4)]
    
    sc_data = anndata.AnnData(X=np.random.uniform(low=0, high=100, size=(16, 8)))
    sc_data.var_names = [f"gene{i}" for i in range(8)]
    
    # Specify user genes to include
    user_genes = ["gene1", "gene3", "gene5"]
    
    envi_model = scenvi.ENVI(spatial_data=st_data, sc_data=sc_data, batch_key=-1, sc_genes=user_genes)
    return envi_model

@pytest.fixture
def large_example_model():
    # Create larger dataset to test batch processing
    st_data = anndata.AnnData(X=np.random.uniform(low=0, high=100, size=(100, 32)), 
                             obsm={'spatial': np.random.normal(size=[100, 2])})
    sc_data = anndata.AnnData(X=np.random.uniform(low=0, high=100, size=(100, 64)))
    
    envi_model = scenvi.ENVI(spatial_data=st_data, sc_data=sc_data, batch_key=-1, num_cov_genes = 16)
    return envi_model

def test_train(example_model):
    example_model.train(training_steps=1)
    
    assert 'COVET' in example_model.spatial_data.obsm
    assert 'COVET_SQRT' in example_model.spatial_data.obsm
    
    assert 'envi_latent' in example_model.spatial_data.obsm
    assert example_model.spatial_data.obsm['envi_latent'].shape == (example_model.spatial_data.shape[0], example_model.latent_dim)
        
    assert 'envi_latent' in example_model.sc_data.obsm
    assert example_model.sc_data.obsm['envi_latent'].shape == (example_model.sc_data.shape[0], example_model.latent_dim)
    
def test_impute(example_model):
    example_model.train(training_steps=1)
    example_model.impute_genes()

    assert 'imputation' in example_model.spatial_data.obsm
        
def test_infer_niche(example_model):
    example_model.train(training_steps=1)
    example_model.infer_niche_covet()
    
    assert 'COVET_SQRT' in example_model.sc_data.obsm
    assert 'COVET' in example_model.sc_data.obsm

def test_precomputed_hvg(example_model_with_hvg):
    """Test that pre-computed highly variable genes are correctly used"""
    # Check that the HVGs from input were maintained
    hvg_count = sum(example_model_with_hvg.sc_data.var['highly_variable'])
    assert hvg_count > 0
    
    # Train and verify
    example_model_with_hvg.train(training_steps=1)
    assert 'envi_latent' in example_model_with_hvg.spatial_data.obsm
    assert 'envi_latent' in example_model_with_hvg.sc_data.obsm

def test_user_specified_genes(example_model_with_user_genes):
    """Test that user-specified genes are correctly included"""
    # Check that user-specified genes are included
    for gene in ["gene1", "gene3", "gene5"]:
        if gene in example_model_with_user_genes.sc_data.var_names:
            assert gene in example_model_with_user_genes.sc_data.var_names
    
    # Train and verify
    example_model_with_user_genes.train(training_steps=1)
    example_model_with_user_genes.impute_genes()
    
    # Check that imputation includes these genes
    assert 'imputation' in example_model_with_user_genes.spatial_data.obsm
    imputed_genes = example_model_with_user_genes.spatial_data.obsm['imputation'].columns
    
    for gene in ["gene1", "gene3", "gene5"]:
        if gene in example_model_with_user_genes.sc_data.var_names:
            assert gene in imputed_genes

def test_all_genes_covet():
    """Test using all genes for COVET calculation"""
    # Create a new model using all genes for COVET
    st_data = anndata.AnnData(X=np.random.uniform(low=0, high=100, size=(16, 4)), 
                             obsm={'spatial': np.random.normal(size=[16, 2])})
    sc_data = anndata.AnnData(X=np.random.uniform(low=0, high=100, size=(16, 8)))
    
    # Set num_cov_genes=-1 to use all genes
    envi_model = scenvi.ENVI(spatial_data=st_data, sc_data=sc_data, batch_key=-1, num_cov_genes=-1)
    
    # Verify all genes are used
    assert len(envi_model.CovGenes) == st_data.shape[1]
    
    # Train and verify
    envi_model.train(training_steps=1)
    assert 'COVET' in envi_model.spatial_data.obsm

def test_covet_with_batches(large_example_model):
    """Test COVET calculation with batch processing"""
    # Calculate COVET matrices using batch processing



    (covet, covet_sqrt, cov_genes) = scenvi.compute_covet(
        large_example_model.spatial_data,
        k=5,
        g=6,
        batch_size=20  # Process in batches of 20
    )
    # Verify the results
    assert covet.shape[0] == large_example_model.spatial_data.shape[0]
    assert covet_sqrt.shape[0] == large_example_model.spatial_data.shape[0]
    assert len(cov_genes) >= 6
    
    # Verify shapes match expected dimensions
    assert covet.shape[1] == covet.shape[2]  # Square matrices
    assert covet_sqrt.shape[1] == covet_sqrt.shape[2]  # Square matrices
    assert covet.shape[1] == len(cov_genes)  # Matrix size matches gene count

def test_niche_cell_type(example_model):
    """Test niche cell type inference"""
    # Add cell type information
    example_model.spatial_data.obs['cell_type'] = np.random.choice(
        ['Type1', 'Type2', 'Type3'], size=example_model.spatial_data.shape[0]
    )
    
    # Train model
    example_model.train(training_steps=1)
    example_model.infer_niche_covet()
    # Infer niche cell types
    
    example_model.infer_niche_celltype(cell_type_key='cell_type')
    
    # Verify results
    assert 'cell_type_niche' in example_model.spatial_data.obsm
    assert 'cell_type_niche' in example_model.sc_data.obsm
    
    # Check the columns of the cell_type_niche match the unique cell types
    unique_cell_types = sorted(example_model.spatial_data.obs['cell_type'].unique())
    niche_columns = sorted(example_model.sc_data.obsm['cell_type_niche'].columns)
    assert unique_cell_types == niche_columns
```

---

## ENVI & COVET¶

**URL:** http://127.0.0.1:9162/docs/build/html/index.html

**Contents:**
- ENVI & COVET¶
- Index¶

ENVI is a deep learnining based variational inference method to integrate scRNA-seq with spatial transcriptomics data. ENVI learns to reconstruct spatial onto for dissociated scRNA-seq data and impute unimagd genes onto spatial data.

This implementation is written in Python3 and relies on jax, flax, sklearn, scipy and scanpy.

To install JAX, simply run the command:

And to install ENVI along with the rest of the requirements:

And to just compute COVET for spatial data:

Please read our documentation and see a full tutorial at https://scenvi.readthedocs.io/.

**Examples:**

Example 1 (unknown):
```unknown
pip install -U "jax[cuda12_pip]" -f https://storage.googleapis.com/jax-releases/jax_cuda_releases.html
```

Example 2 (unknown):
```unknown
pip install scenvi
```

Example 3 (python):
```python
import scenvi

envi_model = scenvi.ENVI(spatial_data = st_data, sc_data = sc_data)

envi_model.train()
envi_model.impute_genes()
envi_model.infer_niche_covet()
envi_model.infer_niche_celltype()

st_data.obsm['envi_latent'] = envi_model.spatial_data.obsm['envi_latent']
st_data.uns['COVET_genes'] =  envi_model.CovGenes
st_data.obsm['COVET'] = envi_model.spatial_data.obsm['COVET']
st_data.obsm['COVET_SQRT'] = envi_model.spatial_data.obsm['COVET_SQRT']
st_data.obsm['cell_type_niche'] = envi_model.spatial_data.obsm['cell_type_niche']
st_data.obsm['imputation'] = envi_model.spatial_data.obsm['imputation']


sc_data.obsm['envi_latent'] = envi_model.sc_data.obsm['envi_latent']
sc_data.uns['COVET_genes'] =  envi_model.CovGenes
sc_data.obsm['COVET'] = envi_model.sc_data.obsm['COVET']
sc_data.obsm['COVET_SQRT'] = envi_model.sc_data.obsm['COVET_SQRT']
sc_data.obsm['cell_type_niche'] = envi_model.sc_data.obsm['cell_type_niche']
```

Example 4 (unknown):
```unknown
st_data.obsm['COVET'], st_data.obsm['COVET_SQRT'], st_data.uns['CovGenes'] = scenvi.compute_covet(st_data)
```

---
